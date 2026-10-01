"""Build the telephony version of every clip.

Chain: resample to 8 kHz, encode as G.711 mu-law, decode back to 16-bit PCM. The signal goes
through the 4 kHz ceiling and the codec artefacts, which is what a contact centre receives.

The output stays at 8 kHz with no upsampling back to 16 kHz: upsampling regenerates nothing
and would only mislead the models about the nature of the signal.

Requires ffmpeg on the PATH.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def convert(src: pathlib.Path, dest: pathlib.Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".mulaw.wav")
    steps = [
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-ar", "8000", "-ac", "1", "-c:a", "pcm_mulaw", str(tmp)],
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
         "-ar", "8000", "-ac", "1", "-c:a", "pcm_s16le", str(dest)],
    ]
    for cmd in steps:
        if subprocess.run(cmd, capture_output=True).returncode != 0:
            return False
    tmp.unlink(missing_ok=True)
    return True


def main(corpora):
    for name in corpora:
        base = DATA / name
        wavs = sorted(p for p in base.rglob("*.wav") if "_tel8k" not in str(p))
        out_root = DATA / f"{name}_tel8k"
        done = fail = 0
        for w in wavs:
            dest = out_root / w.relative_to(base)
            if dest.exists():
                done += 1
                continue
            if convert(w, dest):
                done += 1
            else:
                fail += 1
        refs = base / "refs.tsv"
        if refs.exists():
            (out_root / "refs.tsv").write_bytes(refs.read_bytes())
        print(f"[{name}] {done} converted, {fail} failed, output {out_root.name}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["fr_bj", "fr_sn", "fr_fr_control"])
