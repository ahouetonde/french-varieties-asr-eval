# French Varieties ASR Evaluation

A reproducible protocol for measuring speech recognition on regional varieties of French, using
two West African French pilot datasets (Beninese French and Senegalese French) against a
metropolitan French control.

## Data

| Test set | Source | Clips | Duration | Speakers |
|---|---|---|---|---|
| Beninese French pilot, `fr_bj` | [`labari-voice/fr-bj-speech-pilot`](https://huggingface.co/datasets/labari-voice/fr-bj-speech-pilot) | 209 | 25.0 min | 2 |
| Senegalese French pilot, `fr_sn` | [`labari-voice/fr-sn-speech-pilot`](https://huggingface.co/datasets/labari-voice/fr-sn-speech-pilot) | 210 | 19.3 min | 5 |
| Both pilots together, `fr_bj+fr_sn` | the two above | 419 | 44.3 min | 7 |
| Control, `fr_fr_control` | `google/fleurs`, config `fr_fr`, split `test` | 210 sampled, seed 17 | 35.7 min | mixed |

Both pilots are CC-BY-4.0, in the FLEURS file schema: read speech, WAV PCM 16-bit, 16 kHz mono.
Sentences were written in advance, about everyday life across ten domains, then sent to the
readers, who are speakers of each variety. Recordings were made in studio, one speaker at a
time, with a median signal-to-noise ratio of 22.9 dB for the Beninese pilot and 24.1 dB for the
Senegalese pilot.

## Protocol

1. Each model transcribes the control and both pilots at 16 kHz.
2. Optionally, the same audio is re-encoded through G.711 mu-law at 8 kHz and decoded, with no
   upsampling back to 16 kHz, then transcribed again.
3. Language is forced to `fr`. Automatic language detection is disabled.
4. The model identifier is pinned to a dated version wherever one exists, and the date of the
   run is recorded.
5. Scores are computed on both pilots together and on each pilot on its own, always against the
   control run with the same model.

## Metrics

### Normalisation

Reference and hypothesis go through the same normalisation before any score: lower case,
punctuation removed, hyphens split, apostrophes unified, and numbers, times and ordinals
expanded to words with `num2words`, including roman numerals such as `XIXe`. A hypothesis
`7h30` and a reference `sept heures trente` therefore compare as equal.

### Word and character error rate

Computed with `jiwer` on the normalised text, per test set, with the gap to the control reported
as a relative difference.

### Local name error rate (LNER)

The share of proper-noun occurrences in the references that the transcript gets wrong.

- A proper noun is a word of at least four letters capitalised mid-sentence in the raw
  reference. The two pilots together hold 155 occurrences of 63 distinct names.
- An occurrence counts as correct only if its exact normalised form appears in the transcript
  of the same clip. A near miss, such as `Kaolak` for `Kaolack`, counts as an error.
- LNER is reported twice: strict, and accent-insensitive.
- Foreign names that appear in a reference are counted like any other proper noun.

### Local-term recall

For every local term in a reference, whether it appears in the transcript of the same clip.

- A local term is a word of at least four characters that is either a proper noun as defined
  above, or absent from a French vocabulary of 9,885 forms built from the three FLEURS `fr_fr`
  splits.
- Inflected forms of known words are excluded by a suffix rule, and a short manual exclusion
  list in `bench/entities.py` catches the residue.
- The lexicon holds 340 occurrences in the Beninese pilot and 361 in the Senegalese pilot.

## Running it

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp bench/adapters/example.py bench/adapters/my_vendor.py   # implement transcribe() for your API
cp .env.example .env                                         # add the key your adapter declares

./.venv/bin/python bench/fetch.py            # pilots, control, French vocabulary
./.venv/bin/python bench/telephony.py        # optional: 8 kHz G.711 variants

./.venv/bin/python bench/run.py <adapter> fr_bj - 6
./.venv/bin/python bench/run.py <adapter> fr_sn - 6
./.venv/bin/python bench/run.py <adapter> fr_fr_control - 6
# optional, telephone band: the same three commands with fr_bj_tel8k, fr_sn_tel8k, fr_fr_control_tel8k

./.venv/bin/python bench/score.py            # WER, CER, gap to control: per pilot and fr_bj+fr_sn
./.venv/bin/python bench/entities.py         # LNER and local-term recall, same breakdown
```

The fourth argument of `run.py` is the number of parallel requests. Runs resume where they
stopped, and clips that failed are retried on the next run. Raw transcripts are kept in
`results/` as JSON lines, one per clip.

To measure a model, write an adapter: one Python file in `bench/adapters/` declaring a name, a
dated model identifier, the environment variable that holds the key, and a `transcribe()`
function that posts the audio and returns the text. The template is
`bench/adapters/example.py`.

Report results with the table shapes in `RESULTS_TEMPLATE.md`, the exact model identifier and
the date of the run.

## Licence

Code under MIT. The two pilot datasets are CC-BY-4.0, published by
[Labari Voice](https://labari.dev). FLEURS belongs to its authors.
