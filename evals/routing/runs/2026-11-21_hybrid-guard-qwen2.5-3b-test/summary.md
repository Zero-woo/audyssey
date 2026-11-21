# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.846 (95% CI 0.729 to 0.926) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 33.3% |
| unnecessary clarify | 0.0% |
| param error | 12.3% |
| invalid rate | 1.4% |
| pass^k | 71.4% |
| latency p50 / p95 (ms) | 94 / 440 |
| input / output tokens | 582460 / 3180 |
| runs / cases | 350 / 70 |
| guard fired | 0.0% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 50.0% |
| render|none | 83.3% |
| reseparate|generate | 83.3% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | invalid | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 25 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 20 | 20 | 0 | 5 | 0 | 0 | 0 | 0 | 15 | 10 |
| drop | 0 | 0 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 5 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 35 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 |

## Failed examples

- c-012 (rep 0): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 1): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 2): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 3): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-012 (rep 4): request '사람 말소리 2배로 해줘요'; expected [{"type": "set_gain", "source_id": "s3", "gain": 2.0}]; got {"type":"set_gain","source_id":"s3","gain":0.5}
- c-025 (rep 0): request '영상에 나오는 박수 소리 따로 뽑아서 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"clap","kind":"sfx","description":"clap","spans":[],"visual_hint":null},"method":"generate"}
- c-025 (rep 1): request '영상에 나오는 박수 소리 따로 뽑아서 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"clap","kind":"sfx","description":"clap","spans":[],"visual_hint":null},"method":"generate"}
- c-025 (rep 2): request '영상에 나오는 박수 소리 따로 뽑아서 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"clap","kind":"sfx","description":"clap","spans":[],"visual_hint":null},"method":"generate"}
- c-025 (rep 3): request '영상에 나오는 박수 소리 따로 뽑아서 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"clap","kind":"sfx","description":"clap","spans":[],"visual_hint":null},"method":"generate"}
- c-025 (rep 4): request '영상에 나오는 박수 소리 따로 뽑아서 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"clap","kind":"sfx","description":"clap","spans":[],"visual_hint":null},"method":"generate"}
