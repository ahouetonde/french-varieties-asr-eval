# Results template

Fill this in with your own run. We keep the table shape identical so that figures produced by
different people stay comparable.

Word error rate, studio audio:

| Model | Control fr_fr | Both pilots, fr_bj+fr_sn | Gap to control | Beninese pilot | Senegalese pilot |
|---|---|---|---|---|---|
| `<model-id>` | x.x % | x.x % | +x % | x.x % | x.x % |

Local name error rate (LNER), the share of local proper nouns transcribed wrongly:

| Model | Both pilots, 155 names | Accent-insensitive | Beninese pilot, 61 names | Senegalese pilot, 94 names |
|---|---|---|---|---|
| `<model-id>` | xx.x % | xx.x % | xx.x % | xx.x % |

Local-term recall:

| Model | Both pilots, 701 terms | Beninese pilot, 340 terms | Senegalese pilot, 361 terms |
|---|---|---|---|
| `<model-id>` | xx.x % | xx.x % | xx.x % |

Optional, same audio through G.711 at 8 kHz:

| Model | Control | Both pilots |
|---|---|---|
| `<model-id>` | x.x % | x.x % |

Always state the date of the run and the exact model identifier. Vendors ship new versions
without renaming the endpoint, so an undated figure ages badly.
