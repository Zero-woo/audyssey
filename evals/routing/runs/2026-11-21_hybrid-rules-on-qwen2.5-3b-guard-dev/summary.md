# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.919 (95% CI 0.861 to 0.971) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 44.4% |
| unnecessary clarify | 4.4% |
| param error | 6.1% |
| invalid rate | 0.0% |
| pass^k | 83.6% |
| latency p50 / p95 (ms) | 90 / 348 |
| input / output tokens | 598270 / 2905 |
| runs / cases | 365 / 73 |
| guard fired | 1.4% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 66.7% |
| reseparate|generate | 100.0% |
| residual|source | 66.7% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 60 | 15 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| drop | 0 | 0 | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 10 | 0 | 0 | 25 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 45 | 0 | 0 | 0 | 0 |
| render | 0 | 2 | 0 | 0 | 0 | 0 | 18 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- c-063 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"clarify","question":"한 번에 하나씩 요청해 주시겠어요?","reason":"composite"}
- c-063 (rep 1): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"clarify","question":"한 번에 하나씩 요청해 주시겠어요?","reason":"composite"}
- c-063 (rep 2): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"clarify","question":"한 번에 하나씩 요청해 주시겠어요?","reason":"composite"}
- c-063 (rep 3): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"clarify","question":"한 번에 하나씩 요청해 주시겠어요?","reason":"composite"}
- c-063 (rep 4): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"clarify","question":"한 번에 하나씩 요청해 주시겠어요?","reason":"composite"}
- c-064 (rep 0): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-064 (rep 1): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-064 (rep 2): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-064 (rep 3): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
- c-064 (rep 4): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"set_gain","source_id":"s1","gain":0.5}
