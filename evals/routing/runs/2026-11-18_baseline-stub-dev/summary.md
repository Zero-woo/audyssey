# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.185 (95% CI 0.113 to 0.311) |
| none suppression | 100.0% |
| over-call | 0.0% |
| clarify hit | 33.3% |
| unnecessary clarify | 35.2% |
| param error | 12.5% |
| invalid rate | 1.4% |
| pass^k | 28.8% |
| latency p50 / p95 (ms) | 0 / 0 |
| input / output tokens | 0 / 0 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 0.0% |
| keep|set_gain | 0.0% |
| reseparate|generate | 0.0% |
| residual|source | 0.0% |
| set_gain|set_pitch | 0.0% |

## Confusion (rows gold, columns predicted)

| gold | clarify | drop | generate | keep | none | render | set_pitch |
|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 45 | 5 | 5 | 0 | 40 | 0 | 0 |
| drop | 25 | 20 | 0 | 5 | 5 | 0 | 0 |
| generate | 5 | 0 | 0 | 0 | 5 | 0 | 0 |
| keep | 20 | 0 | 0 | 0 | 15 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 45 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 15 | 5 | 0 |
| reseparate | 15 | 0 | 0 | 0 | 10 | 0 | 0 |
| set_gain | 5 | 0 | 0 | 0 | 10 | 0 | 0 |
| set_pitch | 15 | 0 | 0 | 0 | 35 | 0 | 5 |

## Failed examples

- c-007 (rep 0): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-007 (rep 1): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-007 (rep 2): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-007 (rep 3): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-007 (rep 4): request '새소리 안 들리게 해줘'; expected [{"type": "drop", "source_id": "s3"}]; got {"type":"clarify","question":"어느 소리를 말씀하시나요?","reason":"ambiguous_target"}
- c-013 (rep 0): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"none"}
- c-013 (rep 1): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"none"}
- c-013 (rep 2): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"none"}
- c-013 (rep 3): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"none"}
- c-013 (rep 4): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"none"}
