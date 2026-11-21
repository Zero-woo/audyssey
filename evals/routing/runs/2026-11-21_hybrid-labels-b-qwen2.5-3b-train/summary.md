# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.886 (95% CI 0.795 to 0.939) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 63.6% |
| unnecessary clarify | 0.0% |
| param error | 7.3% |
| invalid rate | 5.3% |
| pass^k | 80.0% |
| latency p50 / p95 (ms) | 96 / 448 |
| input / output tokens | 170437 / 1492 |
| runs / cases | 95 / 95 |
| guard fired | 0.0% |
| guard broke | 0 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| add_source_separate|add_source_generate | 66.7% |
| drop|set_gain | 100.0% |
| render|none | 100.0% |
| residual|source | 100.0% |
| set_gain|set_pitch | 66.7% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 11 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 10 | 2 | 0 | 0 | 0 | 0 | 0 | 5 | 3 |
| drop | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 |

## Failed examples

- c-001 (rep 0): request '원래 개 짖는 소리 다시 켜줘'; expected [{"type": "keep", "source_id": "s1"}]; got {"type":"keep","source_id":"s2"}
- c-002 (rep 0): request '처음 개 소리 살려줘요'; expected [{"type": "keep", "source_id": "s1"}]; got {"type":"keep","source_id":"s2"}
- c-079 (rep 0): request '자동차 반으로 줄이고 나서 새소리도 넣어줘요'; expected [{"type": "clarify", "reason": "composite"}]; got {"type":"set_gain","source_id":"s2","gain":0.5}
- x-025 (rep 0): request '원본에 있는 사이렌 소리를 분리해서 새 트랙으로 추가해줘'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"add_source","plan":{"name":"ambience_siren","kind":"ambience","description":"ambience_siren","spans":[{"start":0.0,"end":10.0},{"start":10.0,"end":20.0},{"start":20.0,"end":30.0},{"start":30.0,"end":40.0},{"start":40.0,"end":50.0},{"start":50.0,"end":60.0},{"start":60.0,"end":70.0},{"start":70.0,"end":80.0},{"start":80.0,"end":90.0},{"start":90.0,"end":100.0}],"visual_hint":null},"method":"separate"}
- x-026 (rep 0): request '아직 따로 안 뽑은 사이렌이 원래 녹음에 있어요. 그걸 추출해서 추가해주세요'; expected [{"type": "add_source", "method": "separate", "plan": {"kind": "sfx"}}]; got {"type":"keep","source_id":"residual"}
- x-068 (rep 0): request '왼쪽 개 있잖아, 걔 소리만 음소거해'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got {"type":"drop","source_id":"s1"}
- x-074 (rep 0): request '나머지 소리의 피치를 한 키 올려줘'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"set_pitch","source_id":"residual","semitones":1.0}
- x-075 (rep 0): request '분리하고 남은 잔여 오디오를 반음 높여주세요'; expected [{"type": "clarify", "reason": "unsupported"}]; got {"type":"set_pitch","source_id":"residual","semitones":1.0}
- x-080 (rep 0): request '경적 볼륨을 지금의 두 배로 올리고 결과 내보내줘'; expected [{"type": "clarify", "reason": "composite"}]; got {"type":"set_gain","source_id":"s2","gain":0.6}
- x-081 (rep 0): request '자동차 경적은 현재 음량의 2배로 맞춘 다음 최종본 렌더링해주세요'; expected [{"type": "clarify", "reason": "composite"}]; got {"type":"set_gain","source_id":"s2","gain":0.6}
