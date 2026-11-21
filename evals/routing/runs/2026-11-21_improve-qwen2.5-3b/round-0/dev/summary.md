# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.628 (95% CI 0.563 to 0.817) |
| none suppression | 77.8% |
| over-call | 11.1% |
| clarify hit | 11.1% |
| unnecessary clarify | 0.0% |
| param error | 14.0% |
| invalid rate | 9.6% |
| pass^k | 58.9% |
| latency p50 / p95 (ms) | 216 / 337 |
| input / output tokens | 254110 / 1919 |
| runs / cases | 73 / 73 |
| guard fired | 0.0% |
| guard broke | 0 |

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
| add_source | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 1 | 1 | 4 | 0 | 0 | 0 | 0 | 2 | 8 | 2 |
| drop | 0 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 2 | 0 |
| none | 0 | 0 | 0 | 1 | 0 | 7 | 0 | 0 | 1 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 |

## Failed examples

- c-007 (rep 0): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-008 (rep 0): request 'birds 소리 없애줘 제발'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"drop","source_id":"residual"}
- c-052 (rep 0): request 'rest 소리 volume 절반으로 해줘요'; expected [{"type": "set_gain", "source_id": "residual", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"set_gain","source_id":"s4","gain":0.5}
- c-063 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-064 (rep 0): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-065 (rep 0): request '멍멍이 소리 절반으로 해주세요'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s2","gain":0.5}
- c-069 (rep 0): request '남자 목소리 너무 시끄러워'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-070 (rep 0): request '목소리 살짝만 줄여주세요'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"set_gain","source_id":"s3","gain":0.9}
- c-071 (rep 0): request '남자 목소리 좀 줄여줘'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"set_gain","source_id":"s3","gain":0.8}
- c-072 (rep 0): request '여자 목소리 새로 만들어서 바꿔줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"generate","source_id":"s3","description":"새로운 여자 목소리 생성"}
