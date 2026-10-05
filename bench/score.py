"""Word and character error rates, computed from the raw transcripts in results/.

Usage:
    python bench/score.py             every run found in results/
    python bench/score.py my_vendor   one adapter only

Both pilots are also scored together, as one West African French test set (fr_bj+fr_sn):
419 clips and seven speakers, which is the headline figure.

Reference and hypothesis go through the same normalisation: lower case, punctuation removed,
hyphens split, apostrophes unified, numbers, times and ordinals spelled out. Without it you
measure typography, not recognition.
"""

import json
import pathlib
import re
import sys
import unicodedata

import jiwer
from num2words import num2words

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

# the two pilots scored together, at studio quality and through the telephone band
COMBINED = {"fr_bj+fr_sn": ("fr_bj", "fr_sn"), "fr_bj+fr_sn_tel8k": ("fr_bj_tel8k", "fr_sn_tel8k")}

TIME = re.compile(r"\b(\d{1,2})\s*h\s*(\d{1,2})?\b")
ORDINAL = re.compile(r"\b(\d+)\s*(?:e|è|ème|eme)\b")
FIRST = re.compile(r"\b1\s*(?:er|re|ère)\b")
ROMAN_ORDINAL = re.compile(r"\b([IVXLC]{2,6})(?:e|ème|eme)\b")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _words(n: int, ordinal: bool = False) -> str:
    try:
        return num2words(n, lang="fr", to="ordinal" if ordinal else "cardinal")
    except Exception:
        return str(n)


def _roman_to_int(s: str) -> int | None:
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    # reject sequences that are not well-formed roman numerals
    return total if _int_to_roman(total) == s else None


def _int_to_roman(n: int) -> str:
    out = ""
    for v, s in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
                 (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def expand_numbers(text: str) -> str:
    """Spell out numbers, times and ordinals on both sides of the comparison.

    A model writing "7h30" or "XIXe" and a reference saying "sept heures trente" or
    "dix-neuvième" say the same thing.
    """
    def roman(m):
        n = _roman_to_int(m.group(1))
        return f" {_words(n, ordinal=True)} " if n else m.group(0)

    def time(m):
        out = f"{_words(int(m.group(1)))} heures"
        if m.group(2):
            out += f" {_words(int(m.group(2)))}"
        return f" {out} "

    text = ROMAN_ORDINAL.sub(roman, text)  # before lower-casing: roman numerals are upper case
    text = FIRST.sub(" premier ", text)
    text = ORDINAL.sub(lambda m: f" {_words(int(m.group(1)), ordinal=True)} ", text)
    text = TIME.sub(time, text)
    text = re.sub(r"\d+", lambda m: f" {_words(int(m.group()))} ", text)
    return text


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = expand_numbers(text)
    text = text.lower().replace("’", "'").replace("œ", "oe").replace("æ", "ae")
    text = re.sub(r"[^\w\s'-]", " ", text)
    text = text.replace("-", " ")
    return " ".join(text.split())


def load_refs(corpus: str) -> dict:
    path = DATA / corpus / "refs.tsv"
    if not path.exists():
        return {}
    refs = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            k, v = line.split("\t", 1)
            refs[k] = v
    return refs


def score(vendor: str, corpus: str, pairs: list, errors: int) -> dict:
    words = jiwer.process_words([p[0] for p in pairs], [p[1] for p in pairs])
    chars = jiwer.process_characters([p[0] for p in pairs], [p[1] for p in pairs])
    return {
        "vendor": vendor, "corpus": corpus, "n": len(pairs), "failed": errors,
        "wer": words.wer * 100, "cer": chars.cer * 100,
        "sub": words.substitutions, "del": words.deletions, "ins": words.insertions,
    }


def main(only: str | None):
    rows, runs = [], {}
    for f in sorted(RESULTS.glob("*.jsonl")):
        vendor, corpus = f.stem.split("__", 1)
        if only and vendor != only:
            continue
        refs = load_refs(corpus)
        pairs, errors = [], 0
        for line in f.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "error" in rec:
                errors += 1
                continue
            ref = refs.get(rec["id"])
            if not ref:
                continue
            r, h = normalise(ref), normalise(rec["text"])
            if r:
                pairs.append((r, h))
        if not pairs:
            print(f"{f.name}: nothing to score ({errors} failed clips)")
            continue
        runs[(vendor, corpus)] = (pairs, errors)
        rows.append(score(vendor, corpus, pairs, errors))

    for vendor in sorted({v for v, _ in runs}):
        for name, parts in COMBINED.items():
            if all((vendor, c) in runs for c in parts):
                pairs = [p for c in parts for p in runs[(vendor, c)][0]]
                errors = sum(runs[(vendor, c)][1] for c in parts)
                rows.append(score(vendor, name, pairs, errors))

    if not rows:
        sys.exit("nothing to score: run bench/run.py first")

    print(f"\n{'vendor':<22}{'corpus':<22}{'n':>5}{'WER %':>8}{'CER %':>8}{'failed':>8}")
    for r in sorted(rows, key=lambda r: (r["vendor"], r["corpus"])):
        print(f"{r['vendor']:<22}{r['corpus']:<22}{r['n']:>5}"
              f"{r['wer']:>8.1f}{r['cer']:>8.1f}{r['failed']:>8}")

    print("\ngap to the metropolitan French control")
    by = {(r["vendor"], r["corpus"]): r["wer"] for r in rows}
    for (vendor, corpus), wer in sorted(by.items()):
        if "control" in corpus:
            continue
        suffix = "_tel8k" if corpus.endswith("_tel8k") else ""
        ctrl = by.get((vendor, f"fr_fr_control{suffix}"))
        if ctrl:
            print(f"  {vendor:<22}{corpus:<22}{wer - ctrl:+6.1f} pt  "
                  f"({(wer / ctrl - 1) * 100:+.0f} %, {wer:.1f} vs {ctrl:.1f})")

    (RESULTS / "scores.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\ndetails written to {RESULTS / 'scores.json'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
