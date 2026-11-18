# Jev 라우터 검토: 세 번째 라우터 후보

**현재 상태:** 이 문서의 혼합 구조는 `AUDYSSEY_ROUTER=hybrid`로 구현되어 있습니다. 결정 서버는 H2O 모델이며 Jev가 아닙니다. 아래 `AUDYSSEY_ROUTER=jev`는 채택하지 않은 초기 제안이고, Jev는 여전히 보류입니다.

2026-11-18 기준 웹 조사입니다. Jev와 Eden AI 엔드포인트는 alpha 단계라 요청 형식, 모델 id, 가격이 예고 없이 바뀔 수 있습니다. 쓰기 전에 [참고](#참고)의 원문을 다시 확인합니다.

**결론: 지금은 보류(no-go)합니다.** 무료로 쓸 방법이 없고 이 서버에 키도 없어 Jev 프로토타입은 만들지 않았습니다. 아래 설계는 계정 생성과 충전이 승인되면 바로 구현할 수 있는 수준으로 적었습니다.

## 기존 문제

- 지금 라우터(`real.py`)는 LLM을 한 번 호출해 `RouteDecision` 하나를 받습니다. Gemini 3.8 Flash(thinking off)는 약 2.6초가 걸리고, 로컬 Qwen2.5-3B는 빠르지만 정확도가 떨어집니다.
- 명령 종류를 고르는 일 자체는 분류 문제입니다. 그래서 분류 전용 모델이 더 빠르고 싸게 같은 결정을 낼 수 있는지 보려는 것입니다.

## 핵심

**Jev가 무엇인가**
- TypeSafe AI의 결정(분류) 모델이고 2026-09-15에 공개됐습니다. 텍스트를 생성하지 않습니다. `state`(텍스트나 JSON)와 이름 붙인 질문들을 받아 질문마다 타입이 정해진 답과 확률을 돌려줍니다.
- 질문 타입은 세 가지입니다.
  - `choice`: 선택지 1~255개 중 하나를 고르고 `choice`, `confidence`, `probabilities`를 돌려줍니다.
  - `score`: 2~10단계 서열 척도입니다.
  - `noul`: 예/아니오 확률 하나만 돌려주고 `confidence`는 없습니다.
- 선택지는 `criteria`에 `{"키": "설명"}` 형태로 요청마다 정의합니다. 학습이나 미세조정은 필요 없습니다.

**접근 방법, 비용, 속도**

| 항목 | 내용 |
|---|---|
| 접근 | 호스팅 API만 있습니다. 가중치 공개나 온프렘 설치는 없습니다. TypeSafe 직접 API는 early-access 대기 명단이고, Eden AI(`POST /v3/alpha/decisions`), AI/ML API, Requesty 같은 게이트웨이는 계정만 있으면 바로 쓸 수 있습니다. |
| SDK | 공식 SDK(`typesafe-sdk`)가 있다는 2차 자료가 있지만 확인하지 못했습니다. Eden AI 예시는 일반 HTTP 호출입니다. |
| 가격 | 입력 100만 토큰당 $0.042이고 출력은 무료입니다(Eden AI 기준). 평가 세트 238건을 건당 약 2천 토큰으로 잡으면 약 $0.02입니다. |
| 무료 사용 | TypeSafe가 공개한 무료 티어나 체험 크레딧은 없습니다. 게이트웨이는 모두 계정 생성이 필요하고, Eden AI는 크레딧이 부족하면 402를 돌려줍니다. |
| 속도 | 회사 발표로 70~500ms이고, Eden AI 문서에는 "보통 1초 미만"이라고 적혀 있습니다. 직접 측정한 값은 없습니다. |
| 정확도 | TypeSafe 자체 벤치마크(4개 워크플로)에서 약 68%로, 중간급 LLM과 비슷한 수준이라고 합니다. |

**우리 계약에 맞추는 방법(설계)**

Jev는 고르기만 하므로 숫자와 자유 텍스트는 만들 수 없습니다. 평가 세트 238건을 기대값으로 나누면 다음과 같습니다.

| 구분 | 건수 | 해당 명령 |
|---|---|---|
| 선택만으로 답할 수 있음 | 181 (76%) | keep, drop, render, none, clarify, 설명 없는 reseparate·generate |
| 숫자가 필요함 | 36 | set_gain의 `gain`, set_pitch의 `semitones` |
| 자유 텍스트가 필요함 | 21 | add_source의 `plan` |

그래서 Jev를 1차 분류기로 쓰고, 값이 필요한 경우만 기존 LLM 라우터로 넘기는 혼합 구조로 설계했습니다.

1. Jev를 한 번 호출합니다. `state`는 `summarize(job)`에 요청을 더한 JSON이고, 질문은 다음 셋입니다.
   - `decision` (`choice`, 선택지 14개): 명령 8개, `clarify_<reason>` 5개, `none`입니다. 설명은 `descriptions.json`의 `when`과 `instead`를 씁니다.
   - `target` (`choice`): job의 소스 id와 `residual`입니다. 설명은 소스의 `name`과 `kind`이고, 요청마다 job에서 만듭니다.
   - `residual_stem` (`noul`): render의 `include_residual_stem`에 씁니다.
2. 고른 답을 `RouteDecision`으로 바꿉니다.
   - keep, drop, reseparate, generate는 `{type, source_id: target}`이 됩니다.
   - render는 `noul`이 0.5 이상이면 `include_residual_stem`을 켭니다.
   - clarify는 `reason`별 고정 문장으로 `question`을 채웁니다. 평가기는 `question` 문구를 채점하지 않습니다.
3. `set_gain`, `set_pitch`, `add_source`이면 `real.route`를 그대로 호출해 값을 채웁니다. 이 경우(약 24%)는 지연과 비용이 오히려 늘어납니다.

**낮은 확신도를 clarify로 바꾸는 규칙**
- `decision` 1위 확률이 τ보다 낮으면 `clarify(other)`로 보냅니다.
- `target` 1위와 2위의 확률 차가 δ보다 작으면 `clarify(ambiguous_target)`로 보내고, 질문에 두 소스의 이름을 넣습니다.
- `confidence` 필드는 분포가 얼마나 몰렸는지를 나타낼 뿐 정답 확률이 아닙니다. 그래서 `probabilities`의 1위 값과 1·2위 차이를 씁니다.
- τ와 δ는 train과 dev split에서 정하고 test에서만 보고합니다. 확률은 반올림되어 합이 1이 아닐 수 있습니다.

**구현 형태(승인 시)**
- 새 파일은 `src/audyssey/tools/routing/jev.py`의 `route(request, job, endpoint, transport=None) -> Routed`입니다. `real.py`처럼 `httpx2` 전송을 주입받고, 테스트는 가짜 transport로 응답 JSON을 돌려줍니다.
- 설정은 `AUDYSSEY_ROUTER=jev`를 추가하고, 키·URL·모델은 기존 `AUDYSSEY_ROUTER_*` 엔드포인트 필드를 다시 씁니다. `settings.py`는 핵심 파일이라 PR에서 승인을 받아야 합니다.
- `Routed.input_tokens`에는 Eden AI 응답의 `usage`를 넣습니다.

## 주의

- **계정과 결제가 필요합니다.** 쓸 수 있는 경로는 모두 가입과 충전이 필요하고, TypeSafe 직접 API는 승인을 기다려야 합니다. 이 작업에서는 사용자 승인이 없어 가입하지 않았습니다.
- **한국어 성능은 확인되지 않았습니다.** 조사한 자료 어디에도 다국어 평가가 없습니다. 우리 요청은 모두 한국어라 이 부분이 가장 큰 미지수입니다.
- **사용자 문장이 외부로 나갑니다.** `real.py`는 요청 문장을 LangSmith에 보내지 않도록 막아 두었습니다. Jev를 쓰면 요청이 TypeSafe와 게이트웨이로 갑니다. Eden AI는 `routing.zero_data_retention` 옵션이 있으니 켜서 씁니다.
- **프롬프트 주입에 약합니다.** TypeSafe 문서에 따르면 `state` 안의 지시문이 답을 움직일 수 있습니다. 소스 이름도 `state`에 들어갑니다.
- **절반만 빨라집니다.** 숫자나 텍스트가 필요한 24%는 LLM을 한 번 더 부르므로, 그 경우는 지금보다 느립니다.
- **Gemini 기준 평가와는 관계없습니다.** Gemini의 test macro-F1 ≥ 0.8 기준은 Jev 없이 판단합니다.

**다시 볼 조건:** Eden AI 계정과 소액 충전(약 $1 이하면 평가 세트 수십 회분)이 승인되면 다음 순서로 진행합니다.
1. `decision` 질문 하나만 평가 세트 train/dev에 돌려 한국어 분류 정확도와 지연을 잽니다.
2. 결과가 Gemini보다 크게 떨어지지 않을 때만 위 혼합 구조를 구현합니다.

## 참고

모두 2026-11-18에 확인했습니다.

- Eden AI 블로그, "Jev: a new kind of AI model built for decisions, not conversation" (최종 수정 2026-10-22): 공개일, 가격, 70~500ms, 약 68% 정확도, 가중치 비공개. https://www.edenai.co/post/jev-a-new-kind-of-ai-model-built-for-decisions-not-conversation
- Eden AI 문서, Decisions API (날짜 표기 없음): 요청·응답 형식, 질문 타입, 402·429 코드, alpha 경고. https://www.edenai.co/docs/v3/llms/decisions.md
- AI/ML API 문서, `typesafe/jev` (날짜 표기 없음): `noul`·`choice`·`score`·`box` 형식, 선택지 1~255개, 척도 2~10단계. https://docs.aimlapi.com/api-references/decision-models/typesafe/jev.md
- Layer3 Labs, "Is Jev free?" (2026-11-02): 무료 티어 없음, 대기 명단, 자체 호스팅 불가. https://www.layer3labs.io/guides/is-jev-free
- `confidence`가 분포의 집중도라는 해석과 TypeSafe의 한계 문서 요약은 2차 자료입니다(검색 요약, 원문은 확인하지 못함). https://www.noze.it/en/insights/jev-system-one-typed-decisions/
- 평가 세트 건수는 `evals/routing/cases.jsonl`의 `expected` 첫 항목으로 셌습니다.
