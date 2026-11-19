# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.803 (95% CI 0.706 to 0.859) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 36.4% |
| unnecessary clarify | 0.0% |
| param error | 2.7% |
| invalid rate | 11.6% |
| pass^k | 75.8% |
| latency p50 / p95 (ms) | 167 / 335 |
| input / output tokens | 1071945 / 7319 |
| runs / cases | 475 / 95 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| add_source_separate|add_source_generate | 77.8% |
| drop|set_gain | 100.0% |
| render|none | 100.0% |
| residual|source | 100.0% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 55 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 5 | 15 | 10 | 0 | 0 | 0 | 10 | 40 | 20 |
| drop | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 60 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 45 |

## Failed examples

- c-028 (rep 0): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":null}
- c-028 (rep 1): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":null}
- c-028 (rep 2): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":null}
- c-028 (rep 3): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":null}
- c-028 (rep 4): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":null}
- c-074 (rep 0): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-074 (rep 1): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-074 (rep 2): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-074 (rep 3): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-074 (rep 4): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
