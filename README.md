# biaffineparser: Deep Biaffine Attention Dependency Parser

biaffineparser is a chainer implementation of "[Deep Biaffine Attention for Neural Dependency Parsing](https://arxiv.org/abs/1611.01734)."

## Installation

biaffineparser works on Python3 and requires chainer, chainer\_nn, numpy, and teras.

```sh
$ git clone https://github.com/chantera/biaffineparser
$ cd biaffineparser
$ pip install -r requirements.txt
```

## Usage

### Training

```sh
usage: main.py train [-h] [--batchsize NUM] [--cachedir DIR] [--devfile FILE]
                     [--device ID] [--embedfile FILE] [--epoch NUM]
                     [--lr VALUE] [--model KEY=VALUE] [--refresh]
                     [--savedir DIR] [--seed VALUE] --trainfile FILE

optional arguments:
  -h, --help         show this help message and exit
  --batchsize NUM    Number of tokens in each mini-batch (default: 5000)
  --cachedir DIR     Cache directory (default: /root/work/host-work/repos/gith
                     ub.com/chantera/biaffineparser/src/../cache)
  --devfile FILE     Development data file (default: None)
  --device ID        Device ID (negative value indicates CPU) (default: -1)
  --embedfile FILE   Pretrained word embedding file (default: None)
  --epoch NUM        Number of sweeps over the dataset to train (default: 300)
  --lr VALUE         Learning rate (default: 0.002)
  --model KEY=VALUE  Model configuration (default: None)
  --refresh, -r      Refresh cache. (default: False)
  --savedir DIR      Directory to save the model (default: None)
  --seed VALUE       Random seed (default: None)
  --trainfile FILE   Training data file. (default: None)
```

### Testing

```sh
usage: main.py test [-h] [--device ID] --modelfile FILE --testfile FILE

optional arguments:
  -h, --help        show this help message and exit
  --device ID       Device ID (negative value indicates CPU) (default: -1)
  --modelfile FILE  Trained model file (default: None)
  --testfile FILE   Test data file (default: None)
```

## Example

```sh
mkdir models
python3 src/main.py train --trainfile=$DATA/train.conll --devfile=$DATA/dev.conll --embedfile=$DATA/glove.6B.100d.txt --device=0 --savedir=./models --seed=2016
python3 src/main.py test --testfile=$DATA/test.conll --modelfile=./models/[yyyymmdd]-[id].npz --device=0
```

### Performance

The model achieves **UAS: 95.80** and **LAS: 94.13** in wsj 23 (test set) in PTB-SD 3.3.0 with the reported hyperparameters.

## References

  - Dozat, T., Manning, C. D., 2016. Deep Biaffine Attention for Neural Dependency Parsing. arXiv preprint arXiv:1611.01734. <https://arxiv.org/abs/1611.01734>

License
----
Apache License Version 2.0

&copy; Copyright 2019 Teranishi Hiroki

