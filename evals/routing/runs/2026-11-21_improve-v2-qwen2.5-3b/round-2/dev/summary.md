# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.637 (95% CI 0.565 to 0.814) |
| none suppression | 88.9% |
| over-call | 0.0% |
| clarify hit | 11.1% |
| unnecessary clarify | 5.6% |
| param error | 14.3% |
| invalid rate | 12.3% |
| pass^k | 57.5% |
| latency p50 / p95 (ms) | 191 / 379 |
| input / output tokens | 209945 / 2003 |
| runs / cases | 73 / 73 |
| guard fired | 0.0% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 66.7% |
| reseparate|generate | 100.0% |
| residual|source | 66.7% |
| set_gain|set_pitch | 33.3% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 2 | 3 | 1 | 2 | 3 | 0 | 0 | 2 | 5 | 1 |
| drop | 0 | 1 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 1 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 1 | 0 | 0 | 3 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| set_pitch | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 |

## Failed examples

- c-013 (rep 0): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_gain","source_id":"s3","gain":1.2}
- c-021 (rep 0): request '차 지나가는 소리 새로 만든 걸로 바꿔줘'; expected [{"type": "generate", "source_id": "s2"}]; got {"type":"add_source","plan":{"name":"car passing","kind":"sfx","description":"new synthesized car passing sound","spans":[],"visual_hint":null},"method":"generate"}
- c-022 (rep 0): request '자동차 소리 생성해서 교체해주세요'; expected [{"type": "generate", "source_id": "s2"}]; got {"type":"add_source","plan":{"name":"car passing","kind":"sfx","description":"car passing","spans":[],"visual_hint":null},"method":"generate"}
- c-063 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_pitch","source_id":"s1","semitones":-2.0}
- c-064 (rep 0): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-065 (rep 0): request '멍멍이 소리 절반으로 해주세요'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s2","gain":0.5}
- c-069 (rep 0): request '남자 목소리 너무 시끄러워'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"clarify","question":"남자 목소리가 너무 시끄러워서 어떻게 할까요?","reason":"ambiguous_target"}
- c-070 (rep 0): request '목소리 살짝만 줄여주세요'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"set_gain","source_id":"s3","gain":0.9}
- c-071 (rep 0): request '남자 목소리 좀 줄여줘'; expected [{"type": "clarify", "reason": "missing_value"}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-072 (rep 0): request '여자 목소리 새로 만들어서 바꿔줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"add_source","plan":{"name":"woman speaking (new)","kind":"dialogue","description":"new synthesized voice","spans":[],"visual_hint":null},"method":"generate"}
