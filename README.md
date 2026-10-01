# French Varieties ASR Evaluation

*How well does speech recognition handle French as it is spoken outside France?*

An evaluation harness for French as it is actually spoken. Most French speakers live outside
France, yet no commercial speech-to-text vendor ships a French variant beyond France, Belgium,
Switzerland and Canada. This repository measures what that costs, on two corpora recorded in
Benin and Senegal, against a metropolitan French control.

Everything here is reproducible in an afternoon with your own API key. We publish the protocol,
not a ranking: run it on your own model and you get your own numbers.

## Data

| Corpus | Source | Clips | Duration | Speakers |
|---|---|---|---|---|
| Beninese French | [`labari-voice/fr-bj-speech-pilot`](https://huggingface.co/datasets/labari-voice/fr-bj-speech-pilot) | 209 | 25.0 min | 2 |
| Senegalese French | [`labari-voice/fr-sn-speech-pilot`](https://huggingface.co/datasets/labari-voice/fr-sn-speech-pilot) | 210 | 19.3 min | 5 |
| Control | `google/fleurs`, config `fr_fr`, split `test` | 210 sampled, seed 17 | 35.7 min | mixed |

Both pilots are CC-BY-4.0, in the FLEURS file schema, read speech, WAV PCM 16-bit, 16 kHz mono.
Sentences were written locally, about local realities, and read by local speakers.

Recording conditions are deliberately favourable: median signal-to-noise ratio of 22.9 dB in
Benin and 24.1 dB in Senegal, one speaker at a time, no overlap. Results obtained here are a
floor, not an average.

## Protocol

Four conditions per model, so that the accent effect and the narrowband effect can be separated
on the same voice:

- control and both corpora at studio 16 kHz
- the same audio re-encoded through G.711 mu-law at 8 kHz, then decoded, with no upsampling
  back to 16 kHz since that regenerates nothing

Language is always forced to `fr`. Automatic language detection is disabled, otherwise a
code-switched segment can flip the detected language and inflate the error rate for reasons
that have nothing to do with the model's French.

Model identifiers are pinned to a dated version wherever the vendor offers one, so that a
measurement run today can be compared with one run in six months.

## Metrics

**Word error rate and character error rate**, computed with `jiwer`, after an identical
normalisation of reference and hypothesis: lower case, punctuation removed, hyphens split,
apostrophes unified, and numbers, times and ordinals expanded to words with `num2words`,
including roman numerals such as `XIXe`.

That last step matters more than it looks. A model writing `7h30` where the reference says
`sept heures trente` is saying the same thing. Before we expanded numbers on both sides, our
Beninese gap read twice as large as it really is.

**Local-term recall**, which is the metric that matters most here. For every local term in the
reference, we check whether it appears in the transcript. Same word, same sentence, so the
measure is immune to differences in corpus difficulty, unlike an aggregate error rate.

A local term is a word of at least four characters that is either capitalised mid-sentence in
the raw reference, so a proper noun, or absent from a French vocabulary of 9,885 forms built
from the three FLEURS `fr_fr` splits. Inflected forms of known words are excluded by a suffix
rule, and a short manual exclusion list in `bench/entities.py` catches the residue. The lexicon
holds 340 occurrences in Benin and 361 in Senegal.

**Local name error rate (LNER)**, the sharpest of the three. It is the share of proper nouns in
the references that the transcript gets wrong: towns, districts, utilities, people. A model can
score a single-digit word error rate and still miss most of them, because they are a small
fraction of the words and the fraction that carries the meaning. LNER is reported strict and
accent-insensitive; the two are usually within a point, so a dropped accent never explains the
figure. Foreign names that happen to appear in a reference count too, which makes the rate
conservative.

## Running it

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp bench/adapters/example.py bench/adapters/my_vendor.py   # implement transcribe() for your API
cp .env.example .env                                         # add the key your adapter declares

./.venv/bin/python bench/fetch.py            # corpora, control, French vocabulary
./.venv/bin/python bench/telephony.py        # 8 kHz G.711 variants

./.venv/bin/python bench/run.py <adapter> fr_bj - 6
./.venv/bin/python bench/run.py <adapter> fr_sn - 6
./.venv/bin/python bench/run.py <adapter> fr_fr_control - 6

./.venv/bin/python bench/score.py            # WER, CER, gap to control
./.venv/bin/python bench/entities.py         # local-term recall
```

The fourth argument is the number of parallel requests. Runs resume where they stopped, and
clips that failed, usually on a timeout, are retried on the next run, so an interrupted pass
costs nothing. Raw transcripts are kept in `results/` as JSON lines, one per
clip, which is what you want when a number looks suspicious.

The harness is vendor-neutral. To measure a model, write an adapter: one Python file in
`bench/adapters/` declaring a name, a dated model identifier, the environment variable that
holds the key, and a `transcribe()` function that posts the audio and returns the text. The
template in `bench/adapters/example.py` is about twenty lines. Force the language to French and
pin the model version, otherwise your figures will not be comparable with anyone else's.

## Limits we know about

Read speech only. Nothing here says anything about spontaneous conversation, background noise,
overlapping speakers, or code-switching into Fon or Wolof, which are the conditions where an
actual contact centre operates.

Two speakers in Benin and five in Senegal, so a country figure partly measures individuals. In
our own runs the spread between the five Senegalese speakers reached eight points on the same
model.

Clips last a few seconds, so a one-point difference between two close systems is not
distinguishable.

## Licence

Code under MIT. The two pilot corpora are CC-BY-4.0. FLEURS belongs to its authors.

Built by [Labari Voice](https://huggingface.co/labari-voice), which records speech corpora in
African francophone countries. If you measure your own model with this and get a result worth
discussing, we are interested either way.
