# 사람 검수용 표본 30개 (범주별 무작위, seed 0)

맞으면 ✓, 아니면 고칠 정답을 적어 주세요.

| # | id | 상태 | 범주 | 요청 | 정답 | 검수 |
|---|---|---|---|---|---|---|
| 1 | x-020 | F1 | positive | 자동차 소리는 원본 음원에서 한 번 더 추출해주세요 | `{"type": "reseparate", "source_id": "s2"}` | |
| 2 | x-024 | F5 | positive | 현재 자동차 경적 대신 짧은 빵 소리를 AI로 만들어 넣어주세요 | `{"type": "generate", "source_id": "s2"}` | |
| 3 | c-006 | F1 | positive | 자동차 소리 빼주세요 | `{"type": "drop", "source_id": "s2"}` | |
| 4 | x-002 | F5 | positive | 강아지 짖는 소리도 다시 들리게 살려주세요 | `{"type": "keep", "source_id": "s1"}` | |
| 5 | g-004 | F3 | positive | 첫 번째 원본 개소리 음소거 해제해줘 | `{"type": "keep", "source_id": "s1"}` | |
| 6 | g-001 | F5 | positive | 꺼져있는 개 짖는 소리 다시 켜줘 | `{"type": "keep", "source_id": "s1"}` | |
| 7 | x-022 | F1 | positive | 지금 강아지 소리 대신 AI로 만든 낮고 굵은 짖는 소리를 써주세요 | `{"type": "generate", "source_id": "s1"}` | |
| 8 | x-007 | F4 | positive | 바람 소리 안 들리게 해줘 | `{"type": "drop", "source_id": "s2"}` | |
| 9 | g-052 | F1 | near_miss | residual 트랙 게인 50%로 낮춰줘 | `{"type": "set_gain", "source_id": "residual", "gain": {"ge": 0.4, "le": 0.6}}` | |
| 10 | x-042 | F1 | near_miss | 개 소리 새로 만들지 말고 원본에서 다시 뽑아줘 | `{"type": "reseparate", "source_id": "s1"}` | |
| 11 | x-034 | F1 | near_miss | 남성 음성의 톤을 2반음 위로 올려주세요 | `{"type": "set_pitch", "source_id": "s3", "semitones": 2}` | |
| 12 | x-049 | F1 | near_miss | 현재 설정으로 출력할 경우 어떤 트랙이 들리는지 궁금해요 | `{"type": "none"}` | |
| 13 | g-048 | F1 | near_miss | 지금 상태로 영상 최종 출력해줘 | `{"type": "render"}` | |
| 14 | c-046 | F1 | near_miss | 폭죽 터지는 소리 만들어서 넣어줘요 | `{"type": "add_source", "method": "generate", "plan": {"kind": "sfx"}}` | |
| 15 | x-044 | F1 | near_miss | 강아지 소리 다시 해줘. 합성 말고 원래 오디오 재분리로 | `{"type": "reseparate", "source_id": "s1"}` | |
| 16 | c-041 | F3 | near_miss | 원본 개 짖음 다시 들리게 켜주세요 | `{"type": "keep", "source_id": "s1"}` | |
| 17 | x-054 | F1 | none | 이 영상 길이가 몇 초야? | `{"type": "none"}` | |
| 18 | c-058 | F1 | none | 고마워 수고했어 | `{"type": "none"}` | |
| 19 | g-060 | F4 | none | 영상 앞부분 3초 잘라내줘 | `{"type": "none"}` | |
| 20 | c-066 | F1 | clarify | 왼쪽에서 짖는 개 반으로 줄여줘 | `{"type": "clarify", "reason": "ambiguous_target"}` | |
| 21 | g-065 | F2 | clarify | dog barking 트랙 음소거해줘 | `{"type": "clarify", "reason": "ambiguous_target"}` | |
| 22 | g-071 | F1 | clarify | 남자 목소리 살짝만 키워줄래? | `{"type": "clarify", "reason": "missing_value"}` | |
| 23 | c-071 | F1 | clarify | 남자 목소리 좀 줄여줘 | `{"type": "clarify", "reason": "missing_value"}` | |
| 24 | g-077 | F1 | constraint | 대사 트랙 새로운 목소리로 생성해서 교체해줘 | `{"type": "clarify", "reason": "unsupported"}` | |
| 25 | c-076 | F1 | constraint | 남자 목소리 20키 올려줘 | `{"type": "clarify", "reason": "unsupported"}` | |
| 26 | x-075 | F1 | constraint | 분리하고 남은 잔여 오디오를 반음 높여주세요 | `{"type": "clarify", "reason": "unsupported"}` | |
| 27 | c-073 | F3 | constraint | woman speaking 생성본으로 교체해주세요 | `{"type": "clarify", "reason": "unsupported"}` | |
| 28 | g-081 | F1 | composite | 개 짖는 소리 두 키 낮추고 배경음악 새로 추가해줘 | `{"type": "clarify", "reason": "composite"}` | |
| 29 | c-079 | F1 | composite | 자동차 반으로 줄이고 나서 새소리도 넣어줘요 | `{"type": "clarify", "reason": "composite"}` | |
| 30 | x-079 | F1 | composite | 강아지 짖는 건 빼주시고, 남성 음성은 반음 높여주세요 | `{"type": "clarify", "reason": "composite"}` | |
