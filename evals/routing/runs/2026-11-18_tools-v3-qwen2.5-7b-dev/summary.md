# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.781 (95% CI 0.709 to 0.903) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 44.4% |
| unnecessary clarify | 1.9% |
| param error | 3.5% |
| invalid rate | 8.2% |
| pass^k | 75.3% |
| latency p50 / p95 (ms) | 264 / 505 |
| input / output tokens | 1270550 / 9126 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 100.0% |
| reseparate|generate | 100.0% |
| residual|source | 66.7% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 25 | 0 | 20 | 0 | 0 | 0 | 10 | 30 | 5 |
| drop | 0 | 0 | 55 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 5 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 45 | 0 | 0 | 0 | 0 |
| render | 0 | 5 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- c-007 (rep 0): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 1): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 2): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 3): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-007 (rep 4): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-063 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-063 (rep 1): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-063 (rep 2): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-063 (rep 3): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-063 (rep 4): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
