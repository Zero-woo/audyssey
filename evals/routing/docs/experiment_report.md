# 자연어 편집 라우터 실험 보고서 (2026-11-18 ~ 19)

요청 문장 하나를 편집 명령 하나(또는 되묻기, 명령 아님)로 바꾸는 라우터를 만들었습니다. 같은 평가셋으로 여러 방식을 비교했습니다. 숫자는 모두 `evals/routing/runs/` 결과에서 가져왔습니다.

---

## 기존 문제

- 편집기를 쓰려면 슬라이더, 토글, 메뉴를 직접 찾아야 했습니다. "개 소리 반으로 줄여줘" 같은 말을 명령으로 바꿔 줄 라우터가 필요했습니다.
- 라우터는 **명령을 고르는 것**뿐 아니라 **행동하지 않아야 할 때**도 알아야 합니다.
  - 대상이 모호하면 되묻기
  - 값이 없으면 되묻기
  - 할 수 없는 편집이면 거절
  - 편집과 무관한 질문이면 아무것도 하지 않음
- 가장 정확한 Gemini는 응답에 약 2.5초가 걸립니다. 작은 로컬 모델은 빠르지만 정확도가 낮습니다.

---

## 핵심

### 1. 구조

```
요청 + 작업 요약 ─▶ 라우터 ─▶ (가드레일) ─▶ 확인 카드 ─▶ [실행] ─▶ 기존 /commands
```

- **라우터 종류**
  - `stub`: 키워드 규칙
  - `real`: LLM 한 번 호출
  - `hybrid`: 결정 모델이 종류와 대상을 고르고, LLM은 값만 채움
- **LLM 호출 방식:** function calling이 기본입니다. 명령 8개, 되묻기, 명령 아님을 tool 10개로 넘기고, 각 tool의 description에 `descriptions.json` 내용을 넣습니다. `tool_choice: required`로 둡니다. json_schema 방식은 비교용 선택지로 남겼습니다.
- **가드레일 (선택, 기본 꺼짐):** `check_command`가 실행 불가로 판정하면 정해 둔 되묻기 문장으로 바꿉니다.
- **실행 시점:** 라우터는 제안만 합니다. 사용자가 카드에서 [실행]을 눌러야 작업 상태가 바뀝니다.

### 2. 평가셋 v1 (238문제)

- **만든 방법**
  - Claude, Codex, Gemini가 같은 생성 가이드로 81문제씩 썼습니다.
  - 다른 모델이 정답을 보지 않고 풀어서 238개 모두 일치했습니다.
  - 사람이 표본 30개를 검수했고, 그중 1개를 고쳤습니다.
- **분할:** template 단위로 train 95 / dev 73 / test 70입니다.
- **범주:** positive, near_miss(헷갈리는 쌍 7종), none, clarify, constraint(실행 불가), composite(복합)
- **정답 규칙**
  - 값이 없거나 모호하면 `clarify(missing_value)`
  - 범위를 넘으면 `clarify(unsupported)`
  - 오디오가 아닌 기능(자막, 배속 등)은 `none`

### 3. 결과 (dev, macro-F1, k=5)

| # | 구성 | macro-F1 | 응답 시간 p50 | 무엇을 바꿨나 |
|---|---|---|---|---|
| 0 | stub (키워드) | 0.185 | 0 ms | 바닥 기준선 |
| 1 | Qwen2.5-3B, json_schema, 설명 v2 | 0.553 | 0.12 s | 기준선 |
| 2 | Qwen2.5-3B, json_schema, 설명 **v3** | 0.625 | 0.12 s | train 실패를 보고 설명을 수동 수정 |
| 3 | Qwen2.5-3B, **tools**, v3 | 0.627 | 0.22 s | 호출 방식 |
| 4 | Qwen2.5-3B, tools, v3, **가드레일** | 0.715 | 0.22 s | 규칙 안전장치 |
| 5 | Qwen2.5-**7B**, tools, v3 | 0.781 | 0.26 s | 모델 크기 |
| 6 | Qwen2.5-7B, tools, v3, 가드레일 | 0.877 | 0.26 s | |
| 7 | **H2O-4B + Qwen2.5-3B** (hybrid) | 0.892 | **81 ms** | 결정 모델 |
| 8 | H2O-4B + Qwen2.5-3B + 가드레일 | **0.906** | 81 ms | 작은 모델 최고 |
| 9 | Gemini 3.8 Flash (thinking 끔), json_schema, v2 | 0.975 | 2.7 s | 상한 참고 |
| 10 | Gemini 3.8 Flash (thinking 끔), tools, v3 | **1.000** | 2.5 s | 시연에 쓰는 구성 |

- test는 기준선만 열었습니다(모델당 1회). Gemini(#9 구성)는 1.000, Qwen2.5-3B(#1 구성)는 0.706입니다.
- 결정 모델 단독(값 없이 종류만)은 H2O-4B 0.636, Gemma-4-31B 0.629입니다. 이 둘은 다른 세션에서 측정했고, 결과는 `runs/2026-11-18_h2o-lightning-4b-dev`와 `runs/2026-11-18_decisio-gemma4-31b-dev`에 있습니다.

### 4. 알게 된 것

1. **작은 모델의 약점은 "고르기"가 아니라 "행동하지 않기"입니다.**
   - 음량, 피치, 켜기, 끄기는 3B도 recall 0.9–1.0입니다.
   - 실행 불가, 되묻기, 복합 요청에서는 동사에 맞는 명령을 일단 실행합니다.
2. **설명의 모순이 상위 모델 점수도 깎습니다.**
   - v2의 `none` 설명에 "지원하지 않는 편집은 clarify"라는 문장이 있었습니다. 이 문장이 "자막·배속은 none"이라는 정답 기준과 충돌했고, Gemini가 dev에서 틀린 3개 중 2개의 원인이었습니다. v3에서 고쳤습니다.
   - 설명 예시에 쓴 숫자(한 키 → 3)를 작은 모델이 그대로 따라 쓰기도 했습니다.
3. **가드레일:** 규칙으로 판정할 수 있는 실패(실행 불가)를 확실히 막습니다. 3B는 +0.09, 7B는 +0.10이 올랐고, 맞던 답을 망친 경우는 0건입니다.
4. **결정 모델 조합 (hybrid)**
   - 결정 모델은 선택지 14개(되묻기 이유 5개 포함)를 나란히 놓고 확률로 비교합니다. 그래서 실행 불가 요청을 되묻기로 잘 고릅니다(dev 6/6).
   - 종류를 고정하면 값 채우기가 쉬워서 3B와 7B의 점수가 같습니다.
   - 응답 시간은 81 ms로 Gemini의 약 30분의 1입니다.
5. **2단계 "비상구"(값 없음 되묻기 tool)는 해롭습니다.** 3B가 필요 없는 상황에서도 남용해 0.892에서 0.809로 떨어졌습니다.
6. **호출 방식(tools 대 json_schema):** 7B는 +0.026, 3B는 차이가 없습니다. 3B는 tool 목록을 받으면 "명령 아님"을 덜 고르는 경향이 있습니다.

### 5. 아직 틀리는 것 (hybrid + 가드레일, dev 13문제)

| 유형 | 개수 | 예 |
|---|---|---|
| 복합 요청 | 4 | "개 소리 끄고 남자 목소리 두 배로" → 하나만 처리 (4개 모두) |
| 대상 모호 | 4 | F2(개 두 마리)에서 "개 짖는 소리 반으로" → 한 마리를 고름 |
| 대상 오인 | 4 | "나머지 소리" → 거리 소음, "원본 개" → 생성 개 |
| 값 없음 | 1 | "남자 목소리 너무 시끄러워" → 끄기 |

이 문제들은 지금은 확인 카드가 마지막 안전장치입니다. 엉뚱한 대상이나 일부만 담긴 카드가 뜨고, 사용자가 [취소]해야 합니다.

---

## 주의

- **평가셋 천장 효과:** Gemini가 dev와 test 모두 만점입니다. 이 평가셋은 생성 모델과 풀이 모델이 같은 규칙을 받아 만들어서 문제가 깔끔한 편입니다. 상위 모델끼리 비교하려면 사람이 쓴 어려운 문제를 더해야 합니다.
- **신뢰구간이 넓습니다:** dev의 template이 31개뿐이라 macro-F1의 95% CI 폭이 0.15 안팎입니다. 0.892와 0.906 같은 작은 차이는 통계적으로 구분되지 않습니다.
- **test는 기준선만 열었습니다.** 지금까지의 개선(#2–#8)은 모두 dev 수치입니다. 최종 비교는 구성마다 test를 한 번씩 엽니다(모델당 최대 3회).
- **가드레일 점수는 "시스템 점수"입니다.** 모델 자체 실력은 가드레일을 끈 점수로 봅니다. 설명 자동 개선도 끈 점수로 합니다.
- **Gemini는 평가 대상이면서 문제 생성자이기도 합니다.** 출처별 정확도에서 자기가 만든 문제의 점수가 더 높지는 않았습니다(dev, json_schema v2 기준 g 0.92).
- **H2O 실행 환경:** vLLM 0.30 전용 venv와 CUDA 호환 라이브러리가 필요합니다. 지금은 임시 폴더에 있어서 지워질 수 있으니, 계속 쓰려면 영구 위치로 옮겨야 합니다.

---

## 참고

### 재현

```bash
# stub (무료)
uv run audyssey eval-routing --router stub --split dev --k 5 --out evals/routing/runs/<날짜>_<이름>
# LLM 라우터 (OpenAI 호환: vLLM 또는 Gemini 호환 주소)
AUDYSSEY_ROUTER_BASE_URL=... AUDYSSEY_ROUTER_MODEL=... AUDYSSEY_ROUTER_API_KEY=... \
uv run audyssey eval-routing --router real --split dev --k 5 --yes --out ...
# hybrid (결정 모델 서버 + 값 채우는 LLM)
AUDYSSEY_ROUTER_DECISION_URL=http://127.0.0.1:8741 AUDYSSEY_ROUTER_BASE_URL=... AUDYSSEY_ROUTER_MODEL=... \
uv run audyssey eval-routing --router hybrid --split dev --k 5 --yes --out ...
# 가드레일 켬: 캐시를 다시 쓰므로 추가 호출 없음
... --guard
```

- **`--yes`:** 없으면 예상 호출 수만 출력하고 아무것도 부르지 않습니다.
- **test 상한:** 모델마다 3회까지 열 수 있습니다. 기록은 `evals/routing/test_opens.jsonl`에 남습니다.
- **로컬 모델 서빙:** vLLM에 `--enable-auto-tool-choice --tool-call-parser hermes`를 줍니다. Qwen2.5-7B처럼 공용 캐시에 `refs/main`이 없는 모델은 snapshot 경로를 `--model`로 직접 넘깁니다.

### 설정 (환경변수)

| 변수 | 값 |
|---|---|
| `AUDYSSEY_ROUTER` | `stub` / `real` / `hybrid` |
| `AUDYSSEY_ROUTER_FORMAT` | `tools` (기본) / `json_schema` |
| `AUDYSSEY_ROUTER_REASONING_EFFORT` | Gemini에서 `none`이면 thinking을 끔 (지연 4.0초 → 2.6초) |
| `AUDYSSEY_ROUTER_GUARD` | 가드레일 (기본 꺼짐) |
| `AUDYSSEY_ROUTER_DECISION_URL`, `_DECISION_MODEL`, `_HYBRID_ESCAPE` | hybrid 설정 |

### 관련 문서

- `generation_guide.md`, `generation_report.md`: 평가셋 만드는 법과 생성 기록
- `error_taxonomy.md`: 기준선 실패 분류
- `manual_edits.md`: 설명 v2 → v3 수동 수정 기록
- `review_sample.md`: 사람 검수 표본

### 다음 실험

1. **E4 결정 모델 보완**
   - 대상 선택에서 1위와 2위 확률이 비슷하면 되묻기로 보냅니다(저장된 확률로 바로 계산할 수 있음).
   - 복합 요청과 대상 설명 문장을 개선합니다.
2. **E3 설명 자동 개선 루프:** LLM이 train 실패를 보고 수정안을 내고, dev로 채택합니다. 수동 수정(v3)이 비교군입니다.
3. **E5 최종 test 비교:** dev 최고 구성 2–3개를 test에서 한 번씩 엽니다.
4. **이후:** 연속 질의(최근 대화를 context로), 복합 요청 분해, 구간 지정 생성
