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
| latency p50 / p95 (ms) | 2712 / 6715 |
| input / output tokens | 721500 / 6402 |
| runs / cases | 350 / 70 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 100.0% |
| render|none | 100.0% |
| reseparate|generate | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain |
|---|---|---|---|---|---|---|---|---|---|
| add_source | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 70 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drop | 0 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 45 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 55 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 |

## Failed examples

