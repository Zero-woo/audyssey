# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.127 (95% CI 0.077 to 0.192) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 33.3% |
| unnecessary clarify | 28.6% |
| param error | 10.5% |
| invalid rate | 0.0% |
| pass^k | 24.3% |
| latency p50 / p95 (ms) | 0 / 0 |
| input / output tokens | 0 / 0 |
| runs / cases | 350 / 70 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 0.0% |
| keep|set_gain | 0.0% |
| render|none | 50.0% |
| reseparate|generate | 0.0% |

## Confusion (rows gold, columns predicted)

| gold | clarify | drop | none | render |
|---|---|---|---|---|
| add_source | 10 | 0 | 20 | 0 |
| clarify | 40 | 0 | 30 | 0 |
| drop | 20 | 0 | 5 | 0 |
| generate | 5 | 0 | 5 | 0 |
| keep | 25 | 5 | 10 | 0 |
| none | 0 | 0 | 40 | 5 |
| render | 0 | 0 | 40 | 15 |
| reseparate | 5 | 0 | 35 | 0 |
| set_gain | 15 | 0 | 20 | 0 |

## Failed examples

- c-009 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-009 (rep 1): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-009 (rep 2): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-009 (rep 3): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-009 (rep 4): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-010 (rep 0): request 'dog volume 반으로 해주세요'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"none"}
- c-010 (rep 1): request 'dog volume 반으로 해주세요'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"none"}
- c-010 (rep 2): request 'dog volume 반으로 해주세요'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"none"}
- c-010 (rep 3): request 'dog volume 반으로 해주세요'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"none"}
- c-010 (rep 4): request 'dog volume 반으로 해주세요'; expected [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}]; got {"type":"none"}
