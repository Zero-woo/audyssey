# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.625 (95% CI 0.569 to 0.804) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 22.2% |
| unnecessary clarify | 0.0% |
| param error | 7.8% |
| invalid rate | 9.6% |
| pass^k | 64.4% |
| latency p50 / p95 (ms) | 261 / 393 |
| input / output tokens | 821235 / 5100 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 33.3% |
| reseparate|generate | 100.0% |
| residual|source | 66.7% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|
| add_source | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 20 | 0 | 0 | 0 | 10 | 50 | 5 |
| drop | 60 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 25 | 0 | 0 | 0 | 10 | 0 |
| none | 0 | 0 | 0 | 45 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

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
