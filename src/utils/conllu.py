import sys
from conllu import parse_incr
from utils import eval


def read_conll(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for tokenlist in parse_incr(f):
            yield from parse_conll(tokenlist)


def parse_conll(tokenlist):
    def _create_root():
        token = {
            "id": 0,
            "form": "<ROOT>",
            "lemma": "<ROOT>",
            "upos": "ROOT",
            "xpos": "ROOT",
            "feats": "_",
            "head": 0,
            "deprel": "root",
            "deps": "_",
            "misc": "_"
        }
        return token

    tokens = [_create_root()]

    for token in tokenlist:
        if(type(token['id']) is int):
            tokens.append(token)
    if len(tokens) > 1:
        yield tokens

def write_conll(file, docs):
    with open(file, "w") as f:
        dump_conll(docs, f)

def dump_conll(docs, writer=sys.stdout):
    attrs = ["id", "form", "lemma", "upos", "xpos", "feats", "head", "deprel", "deps", "misc"]
    for tokens in docs:
        for token in tokens:
            if token["id"] == 0:
                continue
            cols = map(lambda v: str(v) if v is not None else "_", (token.get(k) for k in attrs))
            writer.write("\t".join(cols) + "\n")
        writer.write("\n")
    writer.flush()

def evaluate(gold_file, system_file):
    with open(gold_file) as gf, open(system_file) as sf:
        scores = eval.evaluate(eval.load_conllu(gf), eval.load_conllu(sf))
        return dict(LAS=scores['LAS'].f1, UAS=scores['UAS'].f1, raw="")
