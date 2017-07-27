#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from teras.app import App, arg
from teras.framework.pytorch import config as pytorch_config
import teras.logging as Log
from teras.training import Trainer, TrainEvent as Event
import teras.utils
import torch

from model import DeepBiaffine, BiaffineParser, DataLoader, Evaluator


def train(
        train_file,
        test_file=None,
        embed_file=None,
        embed_size=100,
        n_epoch=20,
        batch_size=32,
        lr=0.002,
        model_params={},
        gpu=-1,
        save_to=None):
    context = locals()

    # Load files
    Log.i('initialize DataLoader with embed_file={} and embed_size={}'
          .format(embed_file, embed_size))
    loader = DataLoader(word_embed_file=embed_file,
                        word_embed_size=embed_size,
                        pos_embed_size=embed_size)
    Log.i('load train dataset from {}'.format(train_file))
    train_dataset = loader.load(train_file, train=True)
    if test_file:
        Log.i('load test dataset from {}'.format(test_file))
        test_dataset = loader.load(test_file, train=False)
    else:
        test_dataset = None

    model_cls = DeepBiaffine

    Log.v('')
    Log.v("initialize ...")
    Log.v('--------------------------------')
    Log.i('# Minibatch-size: {}'.format(batch_size))
    Log.i('# epoch: {}'.format(n_epoch))
    Log.i('# gpu: {}'.format(gpu))
    Log.i('# model: {}'.format(model_cls))
    Log.i('# model params: {}'.format(model_params))
    Log.v('--------------------------------')
    Log.v('')

    # Set up a neural network model
    model = model_cls(
        embeddings=(loader.get_embeddings('word'),
                    loader.get_embeddings('pos')),
        n_labels=len(loader.label_map),
        **model_params,
    )
    if gpu >= 0:
        model.cuda(gpu)

    # Setup an optimizer
    optimizer = torch.optim.Adam(model.parameters(),
                                 lr=lr, betas=(0.9, 0.9), eps=1e-08)
    torch.nn.utils.clip_grad_norm(model.parameters(), max_norm=5.0)
    Log.i('optimizer: Adam(alpha={}, beta1=0.9, '
          'beta2=0.9, eps=1e-08), grad_clip=5.0'.format(lr))

    def annealing(data):
        decay, decay_step = 0.75, 5000
        decay_rate = decay ** (data['epoch'] / decay_step)
        for param_group in optimizer.param_groups:
            param_group['lr'] *= decay_rate

    # Setup a trainer
    parser = BiaffineParser(model)

    trainer = Trainer(optimizer, parser, loss_func=parser.compute_loss,
                      accuracy_func=parser.compute_accuracy)
    trainer.configure(pytorch_config)
    trainer.add_hook(Event.EPOCH_TRAIN_BEGIN, lambda data: model.train())
    trainer.add_hook(Event.EPOCH_VALIDATE_BEGIN, lambda data: model.eval())
    trainer.add_hook(Event.EPOCH_END, annealing)
    if test_dataset:
        trainer.attach_callback(
            Evaluator(parser, pos_map=loader.get_processor('pos').vocabulary,
                      ignore_punct=True))

    if save_to is not None:
        accessid = Log.getLogger().accessid
        date = Log.getLogger().accesstime.strftime('%Y%m%d')

        def _save(data):
            epoch = data['epoch']
            model_file = os.path.join(save_to, "{}-{}.{}.mdl"
                                      .format(date, accessid, epoch))
            Log.i("saving the model to {} ...".format(model_file))
            torch.save(model.state_dict(), model_file)
        context['model_cls'] = model_cls
        context['loader'] = loader
        context_file = os.path.join(save_to, "{}-{}.context"
                                    .format(date, accessid))
        with open(context_file, 'wb') as f:
            teras.utils.dump(context, f)
        trainer.add_hook(Event.EPOCH_END, _save)

    # Start training
    trainer.fit(train_dataset, None,
                batch_size=batch_size,
                epochs=n_epoch,
                validation_data=test_dataset,
                verbose=App.verbose)


def test(
        model_file,
        target_file,
        decode=False,
        gpu=-1):

    # Load context
    context = teras.utils.load_context(model_file)

    # Load files
    Log.i('load dataset from {}'.format(target_file))
    loader = context.loader
    dataset = loader.load(target_file, train=False)

    Log.v('')
    Log.v("initialize ...")
    Log.v('--------------------------------')
    Log.i('# gpu: {}'.format(gpu))
    Log.i('# model: {}'.format(context.model_cls))
    Log.i('# context: {}'.format(context))
    Log.v('--------------------------------')
    Log.v('')

    # Set up a neural network model
    model = context.model_cls(
        embeddings=(loader.get_embeddings('word'),
                    loader.get_embeddings('pos')),
        n_labels=len(loader.label_map),
        **context.model_params,
    )
    model.load_state_dict(torch.load(model_file))
    if gpu >= 0:
        model.cuda(gpu)

    parser = BiaffineParser(model)
    pos_map = loader.get_processor('pos').vocabulary
    label_map = loader.label_map
    evaluator = Evaluator(parser, pos_map, ignore_punct=True)

    # Start testing
    model.eval()
    UAS, LAS, count = 0.0, 0.0, 0.0
    for batch_index, batch in enumerate(
            dataset.batch(context.batch_size, shuffle=False)):
        word_tokens, pos_tokens = batch[:-1]
        true_arcs, true_labels = batch[-1].T
        arcs_batch, labels_batch = parser.parse(word_tokens, pos_tokens)
        for i, (p_arcs, p_labels, t_arcs, t_labels) in enumerate(
                zip(arcs_batch, labels_batch, true_arcs, true_labels)):
            mask = evaluator.create_ignore_mask(word_tokens[i], pos_tokens[i])
            _uas, _las, _count = evaluator.evaluate(
                p_arcs, p_labels, t_arcs, t_labels, mask)
            if decode:
                words = loader.get_sentence(word_tokens[i])
                for word, pos_id, arc, label_id in zip(
                        words[1:], pos_tokens[i][1:],
                        p_arcs[1:], p_labels[1:]):
                    print("\t".join([word, pos_map.lookup(pos_id),
                                     str(arc), label_map.lookup(label_id)]))
                print()
            UAS, LAS, count = UAS + _uas, LAS + _las, count + _count
    Log.i("[evaluation] UAS: {:.8f}, LAS: {:.8f}"
          .format(UAS / count * 100, LAS / count * 100))


if __name__ == "__main__":
    Log.AppLogger.configure(mkdir=True)

    App.add_command('train', train, {
        'batch_size':
        arg('--batchsize', '-b', type=int, default=32,
            help='Number of examples in each mini-batch'),
        'embed_file':
        arg('--embedfile', type=str, default=None,
            help='Pretrained word embedding file'),
        'embed_size':
        arg('--embedsize', type=int, default=100,
            help='Size of embeddings'),
        'gpu':
        arg('--gpu', '-g', type=int, default=-1,
            help='GPU ID (negative value indicates CPU)'),
        'lr':
        arg('--lr', type=float, default=0.002,
            help='Learning Rate'),
        'model_params':
        arg('--model', action='store_dict', default={},
            help='Model hyperparameter'),
        'n_epoch':
        arg('--epoch', '-e', type=int, default=20,
            help='Number of sweeps over the dataset to train'),
        'save_to':
        arg('--out', type=str, default=None,
            help='Save model to the specified directory'),
        'test_file':
        arg('--validfile', type=str, default=None,
            help='validation data file'),
        'train_file':
        arg('--trainfile', type=str, required=True,
            help='training data file'),
    })

    App.add_command('test', test, {
        'decode':
        arg('--decode', action='store_true', default=False,
            help='Print decoded results'),
        'gpu':
        arg('--gpu', '-g', type=int, default=-1,
            help='GPU ID (negative value indicates CPU)'),
        'model_file':
        arg('--modelfile', type=str, required=True,
            help='Trained model archive file'),
        'target_file':
        arg('--targetfile', type=str, required=True,
            help='Decoding target data file'),
    })

    App.run()
