# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.763 (95% CI 0.688 to 0.963) |
| none suppression | 77.8% |
| over-call | 0.0% |
| clarify hit | 66.7% |
| unnecessary clarify | 3.7% |
| param error | 15.9% |
| invalid rate | 4.1% |
| pass^k | 72.6% |
| latency p50 / p95 (ms) | 557 / 720 |
| input / output tokens | 533385 / 0 |
| runs / cases | 365 / 73 |

## Near-miss pair accuracy

| pair | accuracy |
|---|---|
| drop|set_gain | 100.0% |
| keep|set_gain | 100.0% |
| reseparate|generate | 100.0% |
| residual|source | 33.3% |
| set_gain|set_pitch | 100.0% |

## Confusion (rows gold, columns predicted)

| gold | clarify | drop | generate | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|
| add_source | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 60 | 0 | 0 | 0 | 0 | 0 | 10 | 15 | 0 |
| drop | 0 | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 30 | 0 | 5 | 0 | 0 | 0 |
| none | 10 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- c-013 (rep 0): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-013 (rep 1): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-013 (rep 2): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-013 (rep 3): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-013 (rep 4): request '남자 목소리 한 키 올려줘'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-014 (rep 0): request '목소리 피치 한 키만 높여주세요'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-014 (rep 1): request '목소리 피치 한 키만 높여주세요'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-014 (rep 2): request '목소리 피치 한 키만 높여주세요'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-014 (rep 3): request '목소리 피치 한 키만 높여주세요'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
- c-014 (rep 4): request '목소리 피치 한 키만 높여주세요'; expected [{"type": "set_pitch", "source_id": "s3", "semitones": 1}]; got {"type":"set_pitch","source_id":"s3","semitones":3.0}
