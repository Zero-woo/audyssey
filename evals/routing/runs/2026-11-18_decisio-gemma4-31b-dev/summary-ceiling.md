# Routing eval

| metric | value |
|---|---|
| macro-F1 | 0.929 (95% CI 0.825 to 0.988) |
| none suppression | 77.8% |
| over-call | 0.0% |
| clarify hit | 66.7% |
| unnecessary clarify | 3.7% |
| param error | 1.5% |
| invalid rate | 2.7% |
| pass^k | 87.7% |
| latency p50 / p95 (ms) | 554 / 601 |
| input / output tokens | 533385 / 0 |
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

| gold | add_source | clarify | drop | generate | invalid | keep | none | render | reseparate | set_gain | set_pitch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| add_source | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| clarify | 0 | 60 | 0 | 0 | 15 | 0 | 0 | 0 | 10 | 0 | 0 |
| drop | 0 | 0 | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| generate | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keep | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 5 | 0 | 0 | 0 |
| none | 0 | 10 | 0 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 0 |
| render | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| reseparate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 0 | 0 |
| set_gain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| set_pitch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |

## Failed examples

- c-063 (rep 0): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-063 (rep 1): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-063 (rep 2): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-063 (rep 3): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-063 (rep 4): request '개 짖는 소리 반으로 줄여줘'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-064 (rep 0): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-064 (rep 1): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-064 (rep 2): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-064 (rep 3): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
- c-064 (rep 4): request 'dog volume 반으로'; expected [{"type": "clarify", "reason": "ambiguous_target"}]; got invalid
