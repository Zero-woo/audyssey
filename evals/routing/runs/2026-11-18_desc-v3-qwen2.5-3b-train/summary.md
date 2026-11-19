# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.686 (95% CI 0.568 to 0.743) |
| none suppression | 58.3% |
| over-call | 0.0% |
| clarify hit | 18.2% |
| unnecessary clarify | 6.9% |
| param error | 8.2% |
| invalid rate | 14.7% |
| pass^k | 58.9% |
| latency p50 / p95 (ms) | 262 / 538 |
| input / output tokens | 1071945 / 7465 |
| runs / cases | 475 / 95 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| add_source_separate|add_source_generate | 22.2% |
| drop|set_gain | 100.0% |
| render|none | 100.0% |
| residual|source | 100.0% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 20 | 0 | 0 | 25 | 0 | 0 | 0 | 20 | 0 | 0 |
| clarify | 5 | 0 | 20 | 10 | 0 | 0 | 0 | 10 | 40 | 20 |
| drop | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 25 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 45 |

## Failed examples

- c-018 (rep 0): request '개소리 원본에서 한번 더 뽑아줘요'; expected [{"type": "reseparate", "source_id": "s1"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- c-018 (rep 1): request '개소리 원본에서 한번 더 뽑아줘요'; expected [{"type": "reseparate", "source_id": "s1"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- c-018 (rep 2): request '개소리 원본에서 한번 더 뽑아줘요'; expected [{"type": "reseparate", "source_id": "s1"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- c-018 (rep 3): request '개소리 원본에서 한번 더 뽑아줘요'; expected [{"type": "reseparate", "source_id": "s1"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- c-018 (rep 4): request '개소리 원본에서 한번 더 뽑아줘요'; expected [{"type": "reseparate", "source_id": "s1"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- c-028 (rep 0): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rain sounds"}
- c-028 (rep 1): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rain sounds"}
- c-028 (rep 2): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rain sounds"}
- c-028 (rep 3): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rain sounds"}
- c-028 (rep 4): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rain sounds"}
