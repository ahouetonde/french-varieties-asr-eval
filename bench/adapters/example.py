"""Template adapter. Copy this file, rename it, and fill in the request for your API.

The harness calls transcribe() once per clip, in parallel if asked, and stores whatever string
it returns. Raise an exception on failure: the clip is recorded as failed and retried on the
next run.

Two rules keep results comparable with everyone else's:
    - force the language to French; automatic detection lets a code-switched clip flip to
      another language and inflates the error rate for reasons unrelated to French
    - pin MODEL to a dated identifier rather than an alias such as "latest"
"""

import pathlib

import requests  # noqa: F401  (most adapters need it)

NAME = "example"
MODEL = "your-model-2026-09-01"
KEY_ENV = "EXAMPLE_API_KEY"


def transcribe(wav: pathlib.Path, model: str, key: str) -> str:
    # with open(wav, "rb") as f:
    #     r = requests.post(
    #         "https://api.example.com/v1/transcriptions",
    #         headers={"Authorization": f"Bearer {key}"},
    #         files={"file": (wav.name, f, "audio/wav")},
    #         data={"model": model, "language": "fr"},
    #         timeout=180,
    #     )
    # r.raise_for_status()
    # return r.json()["text"]
    raise NotImplementedError("copy this template and implement the call to your API")
