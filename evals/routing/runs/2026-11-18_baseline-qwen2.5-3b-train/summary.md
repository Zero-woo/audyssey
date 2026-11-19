# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.627 (95% CI 0.492 to 0.705) |
| none suppression | 25.0% |
| over-call | 8.3% |
| clarify hit | 18.2% |
| unnecessary clarify | 11.1% |
| param error | 23.2% |
| invalid rate | 13.7% |
| pass^k | 45.3% |
| latency p50 / p95 (ms) | 289 / 587 |
| input / output tokens | 1093320 / 8281 |
| runs / cases | 475 / 95 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| add_source_separate|add_source_generate | 11.1% |
| drop|set_gain | 100.0% |
| render|none | 66.7% |
| residual|source | 33.3% |
| set_gain|set_pitch | 66.7% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 35 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 0 | 20 | 10 | 0 | 0 | 0 | 10 | 45 | 20 |
| drop | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 40 | 0 | 0 | 0 | 15 | 0 | 0 | 5 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 5 | 10 | 0 | 0 | 0 |
| reseparate | 5 | 0 | 0 | 5 | 5 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 45 |

## Failed examples

- c-016 (rep 0): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":3.0}
- c-016 (rep 1): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":3.0}
- c-016 (rep 2): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":3.0}
- c-016 (rep 3): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":3.0}
- c-016 (rep 4): request 'dog barking 피치 2키 낮춰줘요'; expected [{"type": "set_pitch", "source_id": "s1", "semitones": -2}]; got {"type":"set_pitch","source_id":"s1","semitones":3.0}
- c-028 (rep 0): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rainy atmosphere"}
- c-028 (rep 1): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rainy atmosphere"}
- c-028 (rep 2): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rainy atmosphere"}
- c-028 (rep 3): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rainy atmosphere"}
- c-028 (rep 4): request '비 오는 분위기 소리 만들어서 넣어주세요'; expected [{"type": "add_source", "method": "generate", "plan": {"kind": "ambience"}}]; got {"type":"generate","source_id":"residual","description":"rainy atmosphere"}
