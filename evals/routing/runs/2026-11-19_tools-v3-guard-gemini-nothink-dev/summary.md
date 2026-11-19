# Routing eval

| metric | value |
|---|---|
| macro-F1 | 1.000 (95% CI 1.000 to 1.000) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 100.0% |
| unnecessary clarify | 0.0% |
| param error | 0.0% |
| invalid rate | 0.0% |
| pass^k | 100.0% |
| latency p50 / p95 (ms) | 2481 / 7185 |
| input / output tokens | 1080740 / 8700 |
| runs / cases | 365 / 73 |
| guard fired | 0.0% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 100.0% |
| reseparate|generate | 100.0% |
| residual|source | 100.0% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 94 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drop | 0 | 0 | 56 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 45 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

