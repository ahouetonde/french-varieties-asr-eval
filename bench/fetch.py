"""Download the two pilot corpora, the FLEURS fr_fr control, and build the French vocabulary.

Output:
    data/fr_bj/, data/fr_sn/      pilot audio and refs.tsv (clip id, reference sentence)
    data/fr_fr_control/            210 FLEURS fr_fr test clips, sampled with a fixed seed
    data/vocab_fr_fleurs.txt       French vocabulary used to tell local terms from ordinary French

Usage:
    python bench/fetch.py              everything
    python bench/fetch.py pilots       pilots only
    python bench/fetch.py control      control and vocabulary only
"""

import csv
import pathlib
import random
import sys
import tarfile

from huggingface_hub import hf_hub_download, snapshot_download

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import DATA, normalise  # noqa: E402

PILOTS = {"fr_bj": "labari-voice/fr-bj-speech-pilot", "fr_sn": "labari-voice/fr-sn-speech-pilot"}
CONTROL_SIZE = 210
CONTROL_SEED = 17


def read_fleurs_tsv(path) -> dict:
    """FLEURS schema, no header: id, file name, raw transcription, normalised transcription, ..."""
    rows = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if len(r) > 3:
                rows[r[1]] = r[2] if r[2].strip() else r[3]
    return rows


def get_pilots():
    for name, repo in PILOTS.items():
        out = DATA / name
        print(f"[{name}] downloading {repo}")
        snapshot_download(repo_id=repo, repo_type="dataset", local_dir=str(out))
        tsv = out / "test.tsv"
        if not tsv.exists():
            sys.exit(f"[{name}] test.tsv missing from {repo}")
        refs = []
        with open(tsv, encoding="utf-8") as f:
            for r in csv.reader(f, delimiter="\t"):
                if len(r) >= 3:
                    sentence = r[3] if len(r) > 3 and r[3].strip() else r[2]
                    refs.append((pathlib.Path(r[1]).stem, sentence))
        with open(out / "refs.tsv", "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerows(refs)
        print(f"[{name}] {len(refs)} references")


def get_control():
    """Sample the control from the original FLEURS archive.

    The datasets-server rows API refuses FLEURS fr_fr because its parquet row groups exceed
    the scan limit, so we read the tar archive directly. Sorting before sampling makes the
    selection identical on every machine.
    """
    out = DATA / "fr_fr_control" / "audio" / "test"
    out.mkdir(parents=True, exist_ok=True)
    tsv = hf_hub_download("google/fleurs", "data/fr_fr/test.tsv", repo_type="dataset")
    tar = hf_hub_download("google/fleurs", "data/fr_fr/audio/test.tar.gz", repo_type="dataset")
    rows = read_fleurs_tsv(tsv)
    random.seed(CONTROL_SEED)
    keep = set(random.sample(sorted(rows), min(CONTROL_SIZE, len(rows))))
    refs = []
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            name = pathlib.Path(m.name).name
            if m.isfile() and name in keep:
                (out / name).write_bytes(t.extractfile(m).read())
                refs.append((pathlib.Path(name).stem, rows[name]))
    with open(DATA / "fr_fr_control" / "refs.tsv", "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t").writerows(sorted(refs))
    print(f"[control] {len(refs)} clips sampled from {len(rows)}, seed {CONTROL_SEED}")


def build_vocabulary():
    """Every word form found in the three FLEURS fr_fr splits, after normalisation."""
    vocab = set()
    for split in ("train", "dev", "test"):
        path = hf_hub_download("google/fleurs", f"data/fr_fr/{split}.tsv", repo_type="dataset")
        with open(path, encoding="utf-8") as f:
            for r in csv.reader(f, delimiter="\t"):
                if len(r) > 3:
                    vocab.update(normalise(r[2]).split())
                    vocab.update(normalise(r[3]).split())
    (DATA / "vocab_fr_fleurs.txt").write_text("\n".join(sorted(vocab)), encoding="utf-8")
    print(f"[vocabulary] {len(vocab)} French word forms")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "pilots"):
        get_pilots()
    if what in ("all", "control"):
        get_control()
        build_vocabulary()
