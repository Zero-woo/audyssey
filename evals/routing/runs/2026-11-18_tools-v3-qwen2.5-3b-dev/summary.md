# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.627 (95% CI 0.563 to 0.816) |
| none suppression | 77.8% |
| over-call | 11.1% |
| clarify hit | 11.1% |
| unnecessary clarify | 1.5% |
| param error | 14.0% |
| invalid rate | 8.5% |
| pass^k | 58.9% |
| latency p50 / p95 (ms) | 218 / 312 |
| input / output tokens | 1270550 / 9555 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 33.3% |
| reseparate|generate | 100.0% |
| residual|source | 50.0% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | clarify | drop | generate | invalid | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 5 | 5 | 20 | 0 | 0 | 0 | 0 | 10 | 40 | 10 |
| drop | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 25 | 0 | 0 | 0 | 10 | 0 |
| none | 4 | 0 | 0 | 1 | 0 | 35 | 0 | 0 | 5 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- c-007 (rep 0): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 1): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 2): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 3): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 4): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 0): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 1): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 2): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 3): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 4): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
