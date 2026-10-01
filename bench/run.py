"""Transcribe a corpus with one speech-to-text adapter and keep the raw output.

Usage:
    python bench/run.py <adapter> <corpus> [limit|-] [parallel requests]
    python bench/run.py my_vendor fr_bj - 6

An adapter is a Python file in bench/adapters/. It declares four things:

    NAME = "my_vendor"              the name used on the command line
    MODEL = "model-2026-09"         a dated model identifier, so that runs stay comparable
    KEY_ENV = "MY_VENDOR_API_KEY"   the variable holding the key in .env
    def transcribe(wav, model, key) -> str

See bench/adapters/example.py. Keys are read from .env at the repository root, never from the
command line. Output goes to results/<adapter>__<corpus>.jsonl, one JSON line per clip.

A run resumes where it stopped, and clips that failed are retried on the next run.
"""

import concurrent.futures as futures
import importlib.util
import json
import os
import pathlib
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "results"
ADAPTERS_DIR = pathlib.Path(__file__).resolve().parent / "adapters"
REQUIRED = ("NAME", "MODEL", "KEY_ENV", "transcribe")


def load_adapters() -> dict:
    adapters = {}
    for path in sorted(ADAPTERS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"adapter_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        missing = [a for a in REQUIRED if not hasattr(module, a)]
        if missing:
            print(f"skipping {path.name}: missing {', '.join(missing)}")
            continue
        adapters[module.NAME] = module
    return adapters


def env(name: str) -> str:
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    val = os.environ.get(name)
    if not val:
        sys.exit(f"missing key: add {name} to {path}")
    return val


def main(name: str, corpus: str, limit: int | None, workers: int = 1):
    adapters = load_adapters()
    if name not in adapters:
        available = ", ".join(adapters) or "none, add one to bench/adapters/"
        sys.exit(f"unknown adapter: {name}. Available: {available}")
    adapter = adapters[name]
    key = env(adapter.KEY_ENV)  # fail before the first request, not inside a worker thread

    base = DATA / corpus
    wavs = sorted(p for p in base.rglob("*.wav") if ".mulaw" not in p.name)
    if limit:
        wavs = wavs[:limit]
    if not wavs:
        sys.exit(f"no wav files in {base}: run bench/fetch.py first")
    OUT.mkdir(exist_ok=True)
    dest = OUT / f"{name}__{corpus}.jsonl"

    # keep successful clips, drop failed ones so that they are retried on this run
    kept = []
    if dest.exists():
        for line in dest.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "error" not in rec:
                kept.append(line)
        dest.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
    seen = {json.loads(line)["id"] for line in kept}

    todo = [w for w in wavs if w.stem not in seen]
    if not todo:
        print(f"[{name}/{corpus}] already complete, {len(seen)} clips")
        return
    lock = threading.Lock()
    state = {"done": 0, "failed": 0}

    def one(w: pathlib.Path) -> dict:
        rec = {"id": w.stem, "adapter": name, "model": adapter.MODEL, "corpus": corpus}
        try:
            rec["text"] = adapter.transcribe(w, adapter.MODEL, key)
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return rec

    with open(dest, "a", encoding="utf-8") as out:
        def write(rec):
            with lock:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                state["done"] += 1
                state["failed"] += "error" in rec
                if state["done"] % 25 == 0:
                    print(f"  {state['done']}/{len(todo)} ({state['failed']} failed)", flush=True)

        if workers > 1:
            with futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for rec in pool.map(one, todo):
                    write(rec)
        else:
            for w in todo:
                write(one(w))
    tail = " Run again to retry them." if state["failed"] else ""
    print(f"[{name}/{corpus}] done, {state['failed']} failed out of {len(todo)}.{tail}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    lim = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    wrk = int(sys.argv[4]) if len(sys.argv) > 4 else int(os.environ.get("BENCH_WORKERS", "1"))
    main(sys.argv[1], sys.argv[2], lim, wrk)
