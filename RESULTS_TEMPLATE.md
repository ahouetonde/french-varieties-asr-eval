# Results template

Fill this in with your own run. We keep the table shape identical so that figures produced by
different people stay comparable.

| Model | Control fr_fr | Benin | Senegal | Gap to control, Benin | Gap to control, Senegal |
|---|---|---|---|---|---|
| `<model-id>` | x.x % | x.x % | x.x % | +x % | +x % |

Local-term recall, the metric that is immune to corpus difficulty:

| Model | Benin, 340 terms | Senegal, 361 terms |
|---|---|---|
| `<model-id>` | xx.x % | xx.x % |

Narrowband, same audio through G.711 at 8 kHz:

| Model | Control | Benin | Senegal |
|---|---|---|---|
| `<model-id>` | x.x % | x.x % | x.x % |

Always state the date of the run and the exact model identifier. Vendors ship new versions
without renaming the endpoint, so an undated figure ages badly.
