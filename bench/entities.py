"""Local-term recall: for every local term in a reference, is it in the transcript?

An aggregate error rate compares corpora whose content differs: our sentences are about
everyday life, FLEURS sentences come from encyclopedic articles. This metric avoids that bias,
because it only asks whether a given word in a given sentence survived. Same word, same
sentence, fair comparison.

A local term is a word of at least four characters that is either capitalised mid-sentence in
the raw reference, so a proper noun, or absent from the French vocabulary built by fetch.py
from the three FLEURS fr_fr splits.

Usage:
    python bench/entities.py           every vendor
    python bench/entities.py my_vendor one adapter
"""

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import DATA, RESULTS, load_refs, normalise  # noqa: E402

MIN_LEN = 4
VOCAB_FILE = DATA / "vocab_fr_fleurs.txt"
SUFFIXES = ("s", "es", "ons", "ez", "ent", "e", "é", "és", "ée", "ées", "ait", "aient",
            "er", "ir", "re", "nt")

# Ordinary French words absent from the FLEURS vocabulary, hence wrongly flagged as local.
# Checked by hand on the two pilot corpora; extend it if you add a corpus.
NOT_LOCAL = {"descends", "soldates", "dormez", "neuvième", "gombo", "pagnes", "mets",
             "tousse", "revient", "prépare"}


def vocabulary() -> set:
    if not VOCAB_FILE.exists():
        sys.exit(f"{VOCAB_FILE} is missing: run `python bench/fetch.py control` first")
    return set(VOCAB_FILE.read_text(encoding="utf-8").split())


def ordinary_french(word: str, vocab: set) -> bool:
    """True for a known word or an inflected form of one, so that « dormez » is not local."""
    if word in vocab:
        return True
    for suf in SUFFIXES:
        if word.endswith(suf):
            base = word[: -len(suf)]
            if len(base) >= 3 and (base in vocab or base + "e" in vocab
                                   or base + "er" in vocab or base + "re" in vocab):
                return True
    return False


def proper_nouns(corpus: str) -> set:
    """Words capitalised in the raw reference, sentence-initial position excluded."""
    tsv = DATA / corpus / "test.tsv"
    found = set()
    if not tsv.exists():
        return found
    for line in tsv.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        for i, w in enumerate(cols[2].split()):
            bare = w.strip(".,;:!?«»\"'()")
            if i > 0 and bare[:1].isupper() and len(bare) >= MIN_LEN:
                found.add(normalise(bare))
    return found


def local_lexicon(corpus: str) -> collections.Counter:
    corpus = corpus.replace("_tel8k", "")
    vocab, nouns = vocabulary(), proper_nouns(corpus)
    counts = collections.Counter()
    for sentence in load_refs(corpus).values():
        for w in normalise(sentence).split():
            if len(w) < MIN_LEN:
                continue
            if w in nouns or (w not in NOT_LOCAL and not ordinary_french(w, vocab)):
                counts[w] += 1
    return counts


def main(only: str | None):
    rows, missed_by = [], {}
    for f in sorted(RESULTS.glob("*.jsonl")):
        vendor, corpus = f.stem.split("__", 1)
        if (only and vendor != only) or "control" in corpus:
            continue
        refs, lex = load_refs(corpus), local_lexicon(corpus)
        total = hits = 0
        missed = collections.Counter()
        for line in f.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "error" in rec or rec["id"] not in refs:
                continue
            hyp = set(normalise(rec["text"]).split())
            for w in normalise(refs[rec["id"]]).split():
                if w in lex:
                    total += 1
                    if w in hyp:
                        hits += 1
                    else:
                        missed[w] += 1
        if total:
            rows.append((vendor, corpus, total, hits, 100 * hits / total))
            missed_by[(vendor, corpus)] = missed

    if not rows:
        sys.exit("nothing to measure: run bench/run.py first")

    print(f"\n{'vendor':<22}{'corpus':<18}{'local terms':>12}{'recovered':>11}{'recall':>9}")
    for vendor, corpus, total, hits, pct in sorted(rows):
        print(f"{vendor:<22}{corpus:<18}{total:>12}{hits:>11}{pct:>8.1f}%")

    print("\nmost frequently lost terms")
    for key in sorted(missed_by):
        top = ", ".join(f"{w} ({n})" for w, n in missed_by[key].most_common(8))
        if top:
            print(f"  {key[0]}/{key[1]}: {top}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
