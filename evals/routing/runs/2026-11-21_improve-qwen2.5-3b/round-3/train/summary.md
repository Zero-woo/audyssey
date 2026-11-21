# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.700 (95% CI 0.577 to 0.762) |
| none suppression | 58.3% |
| over-call | 8.3% |
| clarify hit | 27.3% |
| unnecessary clarify | 4.2% |
| param error | 6.5% |
| invalid rate | 15.8% |
| pass^k | 61.1% |
| latency p50 / p95 (ms) | 230 / 353 |
| input / output tokens | 331334 / 2730 |
| runs / cases | 95 / 95 |
| guard fired | 0.0% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| add_source_separate|add_source_generate | 33.3% |
| drop|set_gain | 100.0% |
| render|none | 100.0% |
| residual|source | 100.0% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | invalid | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 4 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| clarify | 0 | 1 | 4 | 2 | 0 | 0 | 0 | 0 | 2 | 7 | 4 |
| drop | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 3 | 0 | 0 | 1 | 0 | 7 | 0 | 0 | 1 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |

## Failed examples

- c-016 (rep 0): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":2.0}
- c-028 (rep 0): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"비 오는 분위기 소리"}
- c-046 (rep 0): request '폭죽 터지는 소리 만들어서 넣어줘요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "sfx"}}]; got {"type":"generate","source_id":"s4","description":"firecracker explosion sound"}
- c-047 (rep 0): request '문 닫히는 소리 하나 새로 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "sfx"}}]; got {"type":"generate","source_id":"s4","description":"door close sound"}
- c-060 (rep 0): request '영상 배속 두 배로 빨리 돌려줘'; expected [{"type": "none"}]; got {"type":"set_gain","source_id":"residual","gain":0.5}
- c-074 (rep 0): request '발소리 원본에서 다시 뽑아줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-075 (rep 0): request '발소리 다시 분리해주세요'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"reseparate","source_id":"s1","description":null,"spans":null}
- c-079 (rep 0): request '자동차 반으로 줄이고 나서 새소리도 넣어줘요'; expected [{"type": "clarify", "reason": "composite"}]; got {"type":"set_gain","source_id":"s2","gain":0.5}
- x-017 (rep 0): request '새 지저귀는 소리 원본에서 다시 분리해줘'; expected [{"type": "reseparate", "source_id": "s3"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
- x-018 (rep 0): request '새소리 추출을 원래 오디오로 다시 해주세요'; expected [{"type": "reseparate", "source_id": "s3"}]; got {"type":"reseparate","source_id":"residual","description":null,"spans":null}
