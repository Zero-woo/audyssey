# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.975 (95% CI 0.917 to 1.000) |
| none suppression | 77.8% |
| over-call | 0.0% |
| clarify hit | 100.0% |
| unnecessary clarify | 5.6% |
| param error | 0.0% |
| invalid rate | 0.0% |
| pass^k | 95.9% |
| latency p50 / p95 (ms) | 2739 / 7275 |
| input / output tokens | 751145 / 7308 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 100.0% |
| reseparate|generate | 100.0% |
| residual|source | 83.3% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | add_source | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 92 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drop | 0 | 5 | 53 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 10 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- x-052 (rep 0): request '따로 있는 street ambience는 두고, 나머지 소리 트랙만 빼주세요'; expected [{"type": "drop", "source_id": "residual"}]; got {"type":"clarify","question":"한 번에 여러 소리를 제거할 수 없습니다. 어떤 소리를 먼저 뺄까요?","reason":"composite"}
- x-052 (rep 1): request '따로 있는 street ambience는 두고, 나머지 소리 트랙만 빼주세요'; expected [{"type": "drop", "source_id": "residual"}]; got {"type":"clarify","question":"여러 소리를 한 번에 뺄 수 없습니다. 어떤 소리를 먼저 뺄까요?","reason":"composite"}
- x-052 (rep 2): request '따로 있는 street ambience는 두고, 나머지 소리 트랙만 빼주세요'; expected [{"type": "drop", "source_id": "residual"}]; got {"type":"clarify","question":"여러 소리를 한 번에 빼는 작업은 한 번에 하나씩 처리해야 합니다. 어떤 소리부터 뺄까요?","reason":"composite"}
- x-052 (rep 3): request '따로 있는 street ambience는 두고, 나머지 소리 트랙만 빼주세요'; expected [{"type": "drop", "source_id": "residual"}]; got {"type":"clarify","question":"여러 소리를 한 번에 뺄 수 없습니다. 어떤 소리부터 뺄까요?","reason":"composite"}
- x-052 (rep 4): request '따로 있는 street ambience는 두고, 나머지 소리 트랙만 빼주세요'; expected [{"type": "drop", "source_id": "residual"}]; got {"type":"clarify","question":"여러 소리를 한 번에 제외하는 작업입니다. 어느 소리부터 먼저 제외할까요?","reason":"composite"}
- g-060 (rep 0): request '영상 앞부분 3초 잘라내줘'; expected [{"type": "none"}]; got {"type":"clarify","question":"영상 길이 편집이나 자르기는 지원하지 않습니다. 오디오 소스 편집 요청만 처리할 수 있습니다.","reason":"unsupported"}
- g-060 (rep 1): request '영상 앞부분 3초 잘라내줘'; expected [{"type": "none"}]; got {"type":"clarify","question":"영상의 구간을 자르는 편집 기능은 지원하지 않습니다.","reason":"unsupported"}
- g-060 (rep 2): request '영상 앞부분 3초 잘라내줘'; expected [{"type": "none"}]; got {"type":"clarify","question":"영상 자르기(트리밍) 기능은 지원하지 않습니다. 오디오 편집과 관련된 요청을 해주세요.","reason":"unsupported"}
- g-060 (rep 3): request '영상 앞부분 3초 잘라내줘'; expected [{"type": "none"}]; got {"type":"clarify","question":"영상 자르기(트리밍) 기능은 지원하지 않습니다. 오디오 편집 관련 요청을 해주시겠어요?","reason":"unsupported"}
- g-060 (rep 4): request '영상 앞부분 3초 잘라내줘'; expected [{"type": "none"}]; got {"type":"clarify","question":"영상 구간 자르기는 지원하지 않습니다.","reason":"unsupported"}
