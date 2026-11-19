# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.706 (95% CI 0.596 to 0.814) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 0.0% |
| unnecessary clarify | 0.0% |
| param error | 13.7% |
| invalid rate | 8.6% |
| pass^k | 62.9% |
| latency p50 / p95 (ms) | 118 / 168 |
| input / output tokens | 804355 / 4858 |
| runs / cases | 350 / 70 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 83.3% |
| render|none | 100.0% |
| reseparate|generate | 83.3% |

## Confusion (rows gold, columns predicted)

| gold | add_source | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|
| add_source | 15 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 15 | 0 | 0 | 0 | 0 | 10 | 30 | 15 |
| drop | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 5 | 0 | 35 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 45 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 55 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 5 | 0 | 0 | 35 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 |

## Failed examples

- c-011 (rep 0): request '남자 목소리 두 배로 키워줘'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-011 (rep 1): request '남자 목소리 두 배로 키워줘'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-011 (rep 2): request '남자 목소리 두 배로 키워줘'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-011 (rep 3): request '남자 목소리 두 배로 키워줘'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-011 (rep 4): request '남자 목소리 두 배로 키워줘'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 0): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 1): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 2): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 3): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 4): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
