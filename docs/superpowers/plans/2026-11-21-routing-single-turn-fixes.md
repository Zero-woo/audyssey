# 라우터 single-turn 오답 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hybrid 라우터(H2O-4B + Qwen2.5-3B)의 dev 오답 13개를 다음 네 가지로 줄입니다.
- 복합 요청 질문
- 대상 확률 차이 규칙
- 소스 이름표 보강
- 설명 자동 개선 루프

**Architecture:**
- 1–3단계는 `hybrid.py` 안에서 해결합니다. 결정 서버에 질문 하나를 추가하고, 서버가 이미 주는 확률을 버리지 않고 씁니다.
- 기준값은 저장된 확률로 오프라인에서 고릅니다.
- 4단계는 새 모듈 `routing_improve.py`로 만듭니다. 기존 `run_eval`/`metrics`를 그대로 쓰고, 설명을 인자로 받게 고칩니다.

**Tech Stack:** Python 3.12, pydantic, typer, httpx2, openai SDK (OpenAI 호환), unittest, uv

**Spec:** `docs/superpowers/specs/2026-11-21-routing-single-turn-fixes-design.md`

## Global Constraints

- 핵심 파일 `src/audyssey/contracts.py`, `graph.py`, `api.py`, `settings.py`는 고치지 않습니다.
- 기준값과 문구 후보는 train으로만 고릅니다. dev는 채택 판단에만 씁니다.
- 채택 규칙(실행 전에 고정): 아래를 모두 만족해야 채택합니다.
  - dev macro-F1이 기준보다 올라야 합니다.
  - 어느 label의 dev recall도 기준보다 0.03 넘게 떨어지면 안 됩니다.
  - `none_suppression`이 떨어지면 안 됩니다.
- 1–3단계는 가드레일 켠 점수로 채택하고, 끈 점수도 기록합니다. 4단계는 가드레일 끈 점수로 채택합니다.
- 자동 개선 금지 규칙은 코드 검사로 지킵니다.
  - 개선용 LLM에 dev·test 문제를 보이지 않습니다.
  - train 오답 요청과 6글자 이상 연속으로 겹치면 안 됩니다.
  - 명령당 400자를 넘으면 안 됩니다. `when`, `instead`, `params`, `examples`를 합친 길이입니다.
  - `instead`에 부정 명령문이 있으면 안 됩니다.
- 루프는 최대 5회 돌고, 루프 안에서는 k=1입니다. 최종 보고는 k=5입니다.
- test는 최종 구성마다 한 번만 엽니다. `test_opens.jsonl`이 모델당 3회까지 허용합니다.
- `src/`에만 `ruff format`을 씁니다. `tests/`에는 쓰지 않습니다.
- 검사: `uv run ruff check src/`, `uv run ruff format --check src/`, `uv run ty check --error-on-warning src/`, `uv run python -m unittest discover tests`
- GPU 규칙
  - 시작 전에 `nvidia-smi`로 확인합니다.
  - 다른 사용자 프로세스가 있는 GPU는 쓰지 않습니다.
  - GPU당 70 GB 이하로 쓰고, 한 장은 비워 둡니다.
  - 측정이 끝나면 서버를 내립니다.
- 모델 가중치는 `/home/common/huggingface`에서만 읽습니다.
- 키는 `~/audyssey/.env`에서 환경변수로만 넘깁니다. 출력하거나 argv에 넣지 않습니다.
- 유료 호출(Gemini)은 사용자 승인 뒤에만 합니다. Task 7과 Task 8이 해당됩니다.
- push, PR, merge도 사용자 승인 뒤에만 합니다.

## Review Focus

1. **Task 2:** "A는 두고 B만 빼줘"(x-052) 같은 편집 하나짜리 요청이 복합 요청으로 막히면 안 됩니다. `override`는 기준값 아래의 `composite` 확률에서 아무것도 하지 않아야 합니다.
2. **Task 2:** 대상이 없는 명령(`render`, `add_source`, `none`, `clarify_*`)에 대상 확률 규칙이 걸리면 안 됩니다.
3. **Task 1:** 캐시 키 호환. salt가 비어 있으면 키가 지금과 같아야 합니다. 달라지면 Gemini 캐시를 다시 사야 합니다.
4. **Task 6:** 개선용 LLM 요청 본문에 dev 문제의 요청 문장이 하나도 없어야 합니다.
5. **Task 5:** 설명 후보가 검사를 통과하지 못하면 채택되지 않고, 다음 회차의 기준도 바뀌지 않아야 합니다.

---

### Task 1: 결정 서버 응답 보존과 hybrid 캐시 salt

**Files:**
- Modify: `src/audyssey/tools/routing/__init__.py`
  - `Routed`
  - 새 함수 `cache_salt`
- Modify: `src/audyssey/tools/routing/hybrid.py`
  - `_ask`, `route`
- Modify: `src/audyssey/routing_eval.py`
  - `Run`, `_cache_file`, `uncached_calls`, `_run_one`, `run_eval`
- Modify: `src/audyssey/cli.py` (`eval_routing`)
- Test: `tests/test_audyssey_routing.py`, `tests/test_audyssey_routing_eval.py`

**Interfaces:**
- Produces:
  - `Routed.raw: dict | None = None`: hybrid가 받은 서버의 `answers` 전체
  - `Run.raw: dict | None = None`
  - `cases.jsonl` 각 줄의 `"raw"` 키
  - `routing.cache_salt(router: str) -> str`: `router == "hybrid"`이면 `hybrid.py` 파일 바이트의 sha256 앞 12자, 아니면 `""`
  - `_cache_file(cache, model, case_id, rep, fmt, effort=None, salt="")`. `uncached_calls`, `_run_one`, `run_eval`도 같은 이름의 `salt=""` 인자를 받습니다.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_hybrid_keeps_raw_answers`: 가짜 결정 서버의 `answers`가 `routed.raw`와 같은지 봅니다.
  - `test_cache_key_unchanged_without_salt`: `_cache_file(..., salt="")` 경로가 지금 공식과 같은지 봅니다. 지금 공식은 `sha256(json.dumps([model, fmt, effort, desc_sha, case_id, rep]))`입니다.
  - `test_salt_changes_cache_file`: salt가 다르면 경로가 달라지는지 봅니다.
  - `test_run_eval_writes_raw`: `raw`를 돌려주는 가짜 라우터로 돌렸을 때, `cases.jsonl` 줄과 캐시 파일 모두에 `raw`가 있는지 봅니다.
- [ ] **Step 2:** `uv run python -m unittest tests.test_audyssey_routing tests.test_audyssey_routing_eval`을 실행합니다. 새 테스트가 실패해야 합니다.
- [ ] **Step 3: 구현**
  - salt가 `""`이면 key 리스트를 지금과 똑같이 만듭니다. salt가 있을 때만 `case_id` 앞에 넣습니다.
  - 캐시 hit의 `raw`는 `hit.get("raw")`로 읽습니다. 예전 캐시에는 이 키가 없습니다.
  - `Routed`의 위치 인자 순서는 바꾸지 않습니다. `raw`는 `guarded` 뒤에 둡니다. `_run_one`이 `Routed(decision, *(hit[f] for f in _CACHED_FIELDS))`로 만들기 때문입니다.
  - `cli.eval_routing`은 `salt = cache_salt(router)`를 `uncached_calls`와 `run_eval`에 넘깁니다.
- [ ] **Step 4:** 테스트가 모두 통과하는지 확인합니다. Global Constraints의 검사 4종도 돌립니다.
- [ ] **Step 5:** 커밋합니다. `feat(routing): keep decision-server answers and salt the hybrid cache`

### Task 2: 복합 요청 질문과 대상 확률 차이 규칙 (기본 꺼짐)

**Files:**
- Modify: `src/audyssey/tools/routing/hybrid.py`
- Test: `tests/test_audyssey_routing.py`
  - hybrid 테스트 클래스의 가짜 `decide()`가 `composite` noul과 target `probabilities`도 돌려주게 고칩니다.

**Interfaces:**
- Consumes: Task 1의 `Routed.raw`
- Produces:
  - `COMPOSITE_MIN: float | None = None`
  - `TARGET_MARGIN: float | None = None`
  - `TARGETED_KINDS = {"keep", "drop", "set_gain", "set_pitch", "reseparate", "generate"}`
  - `override(kind: str, answers: dict, composite_min: float | None, target_margin: float | None) -> Literal["composite", "ambiguous_target"] | None`
  - `route(..., composite_min: float | None = COMPOSITE_MIN, target_margin: float | None = TARGET_MARGIN)`

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_decision_request_wire_format`을 고칩니다. `questions`의 키가 `decision`, `target`, `residual_stem`, `composite` 4개이고, `questions["composite"]`가 `{"type": "noul", "instructions": "요청(request)에 서로 다른 편집이 둘 이상 들어 있나요?"}`인지 봅니다.
  - `test_override_table`은 subTest 표로 다음을 확인합니다. `answers`는 `composite.noul`과 `target.probabilities`만 채웁니다.

    | kind | composite noul | 대상 확률 | composite_min | target_margin | 기대 |
    |---|---|---|---|---|---|
    | `set_gain` | 0.9 | `{s1: .9, s2: .1}` | 0.5 | None | `"composite"` |
    | `set_gain` | 0.4 | `{s1: .9, s2: .1}` | 0.5 | None | `None` |
    | `none` | 0.9 | | 0.5 | | `None` |
    | `clarify_missing_value` | 0.9 | | 0.5 | | `None` |
    | `drop` | 0.1 | `{s1: .48, s2: .45, s3: .07}` | None | 0.2 | `"ambiguous_target"` |
    | `drop` | 0.1 | `{s1: .8, s2: .1}` | None | 0.2 | `None` |
    | `render` | 0.1 | `{s1: .5, s2: .5}` | None | 0.2 | `None` |
    | `add_source` | 0.1 | `{s1: .5, s2: .5}` | None | 0.2 | `None` |
    | `drop` | 0.9 | `{s1: .5, s2: .5}` | 0.5 | 0.2 | `"composite"` (복합이 우선) |
    | `drop` | 0.9 | `{s1: .5, s2: .5}` | None | None | `None` (둘 다 꺼짐) |

  - `test_override_turns_into_clarify_without_llm`: `route(..., composite_min=0.5)`에서 noul이 0.9이면 결과가 `Clarify(reason="composite", question=QUESTIONS["composite"])`이고, `llm_requests == []`인지 봅니다.
  - `test_rules_off_by_default`: 기본 인자로는 지금과 같은 결정이 나오는지 봅니다.
- [ ] **Step 2:** 새 테스트가 실패하는지 확인합니다.
- [ ] **Step 3: 구현**
  - `override`
    - `kind`가 `none`이거나 `clarify_`로 시작하면 `None`입니다.
    - composite 규칙을 먼저 봅니다.
    - 대상 확률 차이는 1위 − 2위입니다. 선택지가 하나면 1.0으로 봅니다.
  - `_ask`는 `answers` 전체도 돌려줍니다.
  - `route`는 `override` 결과가 있으면 `_fill`을 부르지 않고 `Clarify`를 만듭니다.
- [ ] **Step 4:** 전체 테스트와 검사 4종을 돌립니다.
- [ ] **Step 5:** 커밋합니다. `feat(routing): composite question and target-margin rule, off by default`

### Task 3: 실행 기록 읽기, 기준값 탐색, 채택 규칙

**Files:**
- Create: `src/audyssey/routing_tune.py`
- Modify: `src/audyssey/routing_eval.py` (`adopt` 추가)
- Test: `tests/test_audyssey_routing_tune.py`, `tests/test_audyssey_routing_eval.py`

**Interfaces:**
- Consumes:
  - Task 1: `cases.jsonl`의 `raw`
  - Task 2: `hybrid.override`
- Produces:
  - `routing_eval.adopt(new: dict, old: dict) -> list[str]`: `metrics()` 결과 두 개를 받아, 지키지 못한 규칙의 설명 목록을 돌려줍니다. 빈 목록이면 채택입니다.
  - `routing_tune.load_runs(run_dir: Path, cases: dict[str, Case]) -> list[Run]`: `cases.jsonl`을 `Run`으로 되살립니다. `raw`도 함께 읽습니다.
  - `routing_tune.sweep(runs: list[Run], reason: Literal["composite", "ambiguous_target"], grid: list[float]) -> list[dict]`: τ마다 `{"tau", "tp", "fp", "fn", "f1", "fixes", "breaks"}`를 냅니다.
  - `routing_tune.pick(results: list[dict]) -> float | None`
  - `python -m audyssey.routing_tune <run_dir>`: 두 규칙의 표와 `pick` 결과를 출력합니다.
    - composite grid: 0.3–0.9, 0.1 간격
    - ambiguous_target grid: 0.05–0.5, 0.05 간격

- [ ] **Step 1: 실패하는 테스트 작성**
  - `adopt` 테스트
    - F1이 같으면 `["macro-F1 did not rise"]`가 나옵니다.
    - recall이 0.04 떨어진 label이 있으면 그 label 이름이 들어간 항목이 나옵니다.
    - recall이 0.03 떨어지면 통과합니다.
    - `none_suppression`이 떨어지면 해당 항목이 나옵니다.
    - old나 new에서 recall이 `None`인 label은 건너뜁니다.
  - `sweep` 테스트: 합성 `Run` 4개로 tp/fp/fn/fixes/breaks를 직접 셉니다.
    - 양성: 정답에 `{"type": "clarify", "reason": reason}`이 있는 case
    - fixes: 원래 틀렸는데 규칙을 적용하니 맞은 경우
    - breaks: 원래 맞았는데 규칙을 적용하니 틀린 경우
    - 맞고 틀림은 `routing_eval.correct`로 판정합니다.
  - `pick` 테스트
    - F1이 가장 높은 τ를 고릅니다.
    - F1이 같으면 fp가 적은 τ를, 그것도 같으면 큰 τ를 고릅니다.
    - 고른 τ의 `fixes - breaks <= 0`이면 `None`입니다.
  - `load_runs` 테스트: `run_eval`이 쓴 폴더를 다시 읽어 `metrics()`를 계산하면, 원래 결과와 같은지 봅니다.
- [ ] **Step 2:** 새 테스트가 실패하는지 확인합니다.
- [ ] **Step 3: 구현**
  - `sweep`은 `hybrid.override(kind, raw, τ 또는 None, τ 또는 None)`으로 해당 규칙만 켭니다.
  - `kind`는 `raw["decision"]["choice"]`입니다.
  - 규칙이 걸리면 결정을 `Clarify(reason=reason, question=QUESTIONS[reason])`로 바꿔 채점합니다.
- [ ] **Step 4:** 전체 테스트와 검사 4종을 돌립니다.
- [ ] **Step 5:** 커밋합니다. `feat(evals): offline threshold sweep and the adoption rule`

### Task 4: 실험 — 1·2단계 기준값 정하기와 dev 채택

코드는 상수 두 줄만 바뀝니다. 나머지는 실행과 기록입니다.

- [ ] **Step 1: 서버 띄우기**
  - `nvidia-smi`로 빈 GPU 한 장을 고릅니다.
  - **결정 서버:** decisio 환경을 씁니다. vLLM 0.30 전용 venv이고, 2026-11-19에 썼던 것이 `/tmp/claude-1016/-home-gwpark0741/30099169-5d96-4b52-aa0c-bca9e4970623/scratchpad/src/decisio/.venv`에 있습니다.
    - 그 폴더의 문서대로 `h2o-lightning-4b`를 포트 8741에 띄웁니다.
    - 가중치는 `/home/common/huggingface`에서 읽습니다.
    - 폴더가 없으면 멈추고 사용자에게 알립니다.
  - **Qwen2.5-3B-Instruct:** vLLM으로 띄웁니다. `--enable-auto-tool-choice --tool-call-parser hermes`를 줍니다.
  - 두 서버 모두 health를 확인합니다.
- [ ] **Step 2: 규칙을 끈 상태로 돌리기**
  - 환경: `AUDYSSEY_ROUTER_DECISION_URL`, `AUDYSSEY_ROUTER_BASE_URL`, `AUDYSSEY_ROUTER_MODEL`, `AUDYSSEY_ROUTER_API_KEY=dummy`
  - 실행할 것 3개
    - `eval-routing --router hybrid --split train --k 1 --yes --out evals/routing/runs/<날짜>_hybrid-rules-off-qwen2.5-3b-train`
    - 같은 설정으로 `--split dev --k 5 ... -dev`
    - 같은 설정으로 `--split dev --k 5 --guard ... -guard-dev`
  - 기대 결과: 새 질문이 추가됐으므로 dev 점수가 0.892 / 0.906 근처인지 기록합니다.
- [ ] **Step 3: 기준값 고르기**
  - `uv run python -m audyssey.routing_tune <train 실행 폴더>`를 돌립니다.
  - 출력된 표를 `evals/routing/docs/experiment_report.md`에 붙이기 위해 저장합니다.
  - `pick`이 낸 값을 `COMPOSITE_MIN`과 `TARGET_MARGIN`에 넣습니다. `None`이면 그 규칙은 꺼진 채로 둡니다.
- [ ] **Step 4: 규칙을 켠 상태로 확인**
  - dev k=5를 가드레일 켬과 끔으로 다시 돌립니다. 코드가 바뀌어 salt가 새로 생깁니다.
  - `adopt(new=규칙 켬 guard dev, old=Step 2 guard dev)`를 계산합니다.
  - 빈 목록이 아니면 상수를 `None`으로 되돌리고, 그 결과만 기록합니다.
- [ ] **Step 5: 커밋**
  - 상수 변경과 실행 폴더 5개를 커밋합니다. `exp(routing): tune composite and target-margin thresholds on train`
  - 서버는 Task 5에서 계속 쓰므로 아직 내리지 않습니다.

### Task 5: 소스 이름표와 residual 문구

**Files:**
- Modify: `src/audyssey/tools/routing/hybrid.py` (`_questions`의 target criteria)
- Test: `tests/test_audyssey_routing.py`

**Interfaces:**
- Produces:
  - `_target_label(source: Source) -> str`
  - `RESIDUAL_LABEL: str`

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_decision_request_wire_format`의 target 기대값을 바꿉니다.
    - `"s1": "dog (sfx, 원본 분리, 켜짐)"`
    - `"s2": "car (sfx, 원본 분리, 켜짐)"`
    - `"residual": RESIDUAL_LABEL`
  - `test_generated_source_label`: `origin="generated", replaces="s1"`인 소스가 `"... (sfx, 생성: s1 대체, 켜짐)"`이 되는지 봅니다. `replaces`가 없으면 `"... (sfx, 생성, 켜짐)"`입니다.
- [ ] **Step 2:** 새 테스트가 실패하는지 확인합니다.
- [ ] **Step 3: 구현**
  - `RESIDUAL_LABEL`은 `"residual: 분리되지 않고 남은 나머지 소리"` 뒤에 사용자 표현 예시를 덧붙인 문장입니다.
  - 붙이기 전에 Task 4 train 실행의 오답 요청들과 6글자 연속으로 겹치지 않는지 확인합니다. Task 6의 `overlaps` 함수가 아직 없으면 같은 계산을 한 줄로 합니다.
- [ ] **Step 4: 문구 후보 고르기**
  - 후보 두 개로 train k=1을 돌립니다.
    - A: 위 문구
    - B: 출처를 `원본`/`생성`으로만 쓴 짧은 문구
  - train macro-F1이 높은 쪽을 고릅니다. 같으면 짧은 쪽입니다.
  - 고른 문구로 dev k=5를 가드레일 켬과 끔으로 돌리고, `adopt(new, old=Task 4의 최종 guard dev)`를 계산합니다.
  - 통과하지 못하면 문구를 원래대로 되돌리고 결과만 기록합니다.
- [ ] **Step 5:** 전체 테스트와 검사 4종을 돌립니다. 코드, 테스트, 실행 폴더를 커밋합니다. `feat(routing): origin-aware source labels for the decision model`
- [ ] **Step 6:** 서버 두 개를 내리고, `nvidia-smi`로 GPU가 비었는지 확인합니다.

### Task 6: 설명을 인자로 받기와 후보 검사

**Files:**
- Modify: `src/audyssey/tools/routing/real.py`
  - `_commands`, `route`
- Modify: `src/audyssey/tools/routing/hybrid.py`
  - `_questions`, `_fill`, `route`
- Modify: `src/audyssey/routing_eval.py`
  - `_cache_file`, `uncached_calls`, `_run_one`, `run_eval`
- Create: `src/audyssey/routing_improve.py` (검사 함수까지만)
- Test: `tests/test_audyssey_routing.py`, `tests/test_audyssey_routing_eval.py`, `tests/test_audyssey_routing_improve.py`

**Interfaces:**
- Produces:
  - `real._commands(descriptions: dict | None = None) -> dict`: 인자가 있으면 `descriptions["commands"]`, 없으면 파일을 읽습니다.
  - `real.route(..., descriptions: dict | None = None)`, `hybrid.route(..., descriptions: dict | None = None)`
  - `routing_eval.descriptions_sha(descriptions: dict | None) -> str`: `None`이면 지금 `_descriptions()[0]`을 씁니다. 아니면 `json.dumps(descriptions, sort_keys=True, ensure_ascii=False)`의 sha256입니다.
  - `run_eval(..., descriptions: dict | None = None)`: 캐시 키와 `config.json`의 `descriptions_sha256`/`descriptions_version`에 반영합니다.
  - `routing_improve.overlaps(text: str, requests: list[str], n: int = 6) -> bool`
  - `routing_improve.NEGATIVE = re.compile(r"하지\s*마|마세요|마십시오|말\s*것|않도록")`
  - `routing_improve.validate(candidate: dict, current: dict, failed_requests: list[str]) -> list[str]`

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_real_route_uses_descriptions_override`: 덮어쓴 `when` 문장이 tool description에 들어가는지 봅니다.
  - `test_hybrid_questions_use_descriptions_override`: 덮어쓴 문장이 decision criteria에 들어가는지 봅니다.
  - `test_cache_key_follows_descriptions`: 설명 dict가 다르면 캐시 경로가 다르고, `None`이면 지금 경로와 같은지 봅니다.
  - `validate` 표 테스트
    - 지금 `descriptions.json`을 그대로 넣으면 `[]`입니다.
    - 명령 하나가 빠지면 오류가 납니다.
    - 필드 하나가 빠지면 오류가 납니다.
    - `examples`가 문자열이면 오류가 납니다.
    - 한 명령이 401자면 오류가 납니다. 400자는 통과합니다.
    - 실패 요청 `"개 짖는 소리 반으로 줄여줘"`와 `"짖는 소리 반"`(6글자)이 겹치면 오류가 납니다. 5글자 겹침은 통과합니다.
    - `instead`에 `"…는 고르지 마세요"`가 있으면 오류가 납니다.
- [ ] **Step 2:** 새 테스트가 실패하는지 확인합니다.
- [ ] **Step 3: 구현**
  - 겹침 검사는 실패 요청마다 길이 6 부분 문자열 집합을 만들고, 후보의 각 필드에 그중 하나라도 들어 있는지 봅니다. 공백도 글자로 셉니다.
  - 길이는 `when`, `instead`, `params`, 그리고 `examples` 각 항목의 `len` 합입니다.
- [ ] **Step 4:** 전체 테스트와 검사 4종을 돌립니다.
- [ ] **Step 5:** 커밋합니다. `feat(routing): descriptions as an argument and candidate checks`

### Task 7: 자동 개선 루프와 CLI

**Files:**
- Modify: `src/audyssey/routing_improve.py`
- Modify: `src/audyssey/cli.py` (`improve_routing` 명령)
- Test: `tests/test_audyssey_routing_improve.py`

**Interfaces:**
- Consumes:
  - Task 3: `adopt`
  - Task 6: `validate`, `run_eval(..., descriptions=)`, `real.route(..., descriptions=)`
- Produces:
  - `improve(route_with: Callable[[dict], Callable[[str, Job], Routed]], model: str, improver: LLMEndpoint, train: list[Case], dev: list[Case], fixtures: Path, cache: Path, out: Path, rounds: int = 5, transport: httpx2.BaseTransport | None = None) -> dict`
    - `route_with(descriptions)`는 그 설명을 쓰는 라우터를 돌려줍니다.
    - 반환값: `{"best_round": int | None, "best": dict, "rounds": [...]}`
  - CLI `audyssey improve-routing --out <dir> [--rounds 5] [--yes]`
    - 대상 라우터는 `real`(설정의 `AUDYSSEY_ROUTER_*`)입니다.
    - 개선용 LLM은 `AUDYSSEY_IMPROVER_BASE_URL`, `AUDYSSEY_IMPROVER_MODEL`, `AUDYSSEY_IMPROVER_API_KEY`를 씁니다. `Settings().planner_endpoint().model_copy(update=...)`에 `api="openai"`로 만듭니다.
    - `--yes`가 없으면 예상 호출 수만 출력하고 아무것도 부르지 않습니다.
- 개선용 LLM 호출
  - `chat.completions.create`를 씁니다.
  - `response_format={"type": "json_schema", ...}`로 받습니다. 스키마는 명령 10개가 모두 required이고, 각 명령은 `when`/`instead`/`params`(str)와 `examples`(list[str])가 required이며 `additionalProperties: false`입니다.
  - system 메시지에 Global Constraints의 금지 규칙을 적습니다.
  - user 메시지는 다음 JSON입니다.

    ```
    {
      "descriptions": 현재 commands,
      "failures": [{request, job: summarize(job), expected, got}]
    }
    ```

  - `temperature=1.0`으로 둡니다. 거절된 회차 다음에도 같은 입력이 들어가므로, 같은 답이 반복되지 않게 하기 위해서입니다.

- [ ] **Step 1: 실패하는 테스트 작성**
  - 가짜 개선 LLM(MockTransport)과 가짜 라우터 팩토리를 씁니다.
  - `test_dev_requests_never_reach_improver`: 캡처한 개선 LLM 요청 본문에 dev case의 `request` 문자열이 하나도 없는지 봅니다.
  - `test_invalid_candidate_is_skipped`
    - 1회차 후보가 401자입니다.
    - 기대: `rounds[0]["verdict"] == "rejected"`, dev를 돌리지 않음, 2회차 입력의 descriptions는 원본 그대로
  - `test_adopted_candidate_becomes_base`
    - 1회차 후보는 dev F1을 올립니다.
    - 기대: 2회차 입력이 1회차 후보이고, `best_round == 1`
  - `test_round_logs_written`: `out/round-1/`에 `candidate.json`, `failures.jsonl`, `verdict.json`이 있고, dev를 돌린 회차에는 `dev/summary.md`도 있는지 봅니다.
  - `test_stops_when_train_has_no_failures`: train 오답이 0개면 개선 LLM을 부르지 않고 끝나는지 봅니다.
- [ ] **Step 2:** 새 테스트가 실패하는지 확인합니다.
- [ ] **Step 3: 구현**
  - 0회차에서 현재 설명으로 dev를 돌려 기준을 잡습니다.
  - 회차마다 다음 순서로 진행합니다.
    1. train k=1을 돌립니다. 출력 폴더는 `out/round-N/train`입니다.
    2. 오답이 있으면 개선 LLM을 한 번 부릅니다.
    3. `validate`를 통과하지 못하면 그 회차의 후보를 버립니다.
    4. 통과하면 dev k=1을 돌립니다.
    5. `adopt` 결과가 빈 목록일 때만 기준을 바꿉니다.
  - `run_eval`의 out 폴더는 회차 아래에 둡니다. 덮어쓰지 않습니다.
- [ ] **Step 4:** 전체 테스트와 검사 4종을 돌립니다.
- [ ] **Step 5:** 커밋합니다. `feat(routing): description auto-improve loop`

### Task 8: 실험 — 자동 개선 실행과 반영 (사용자 승인 필요)

- [ ] **Step 1: 승인 받기**
  - `improve-routing`을 `--yes` 없이 돌려 예상 호출 수를 확인합니다.
  - Gemini 호출 수(최대 5회 + 최종 확인 dev 73회)를 사용자에게 알리고 승인을 받습니다.
- [ ] **Step 2: 루프 실행**
  - Qwen2.5-3B vLLM을 띄웁니다(GPU 규칙).
  - `improve-routing --out evals/routing/runs/<날짜>_improve-qwen2.5-3b --rounds 5 --yes`를 돌립니다.
- [ ] **Step 3: 반영 조건 확인**
  - `best_round`가 있으면 그 설명으로 아래 세 가지를 확인합니다.
    - Qwen2.5-3B `real` dev k=5
    - hybrid + 가드레일 dev k=5 (결정 서버 필요)
    - Gemini tools dev k=1. 이전 결과에서 5회 답이 모두 같았으므로 k=1이면 충분합니다.
  - 기준은 각각의 지금 dev 결과이고, `adopt`를 적용합니다.
  - 모두 통과해야 `descriptions.json`에 쓰고 `version`을 4로 올립니다. 하나라도 통과하지 못하면 결과만 기록합니다.
- [ ] **Step 4: 기록과 정리**
  - 수동 v3(dev 0.553 → 0.625)와 비교한 표를 남깁니다.
  - 서버를 내리고, `nvidia-smi`로 GPU가 비었는지 확인합니다.
  - 커밋합니다. `exp(routing): auto-improve descriptions for Qwen2.5-3B`

### Task 9: test 한 번 열기와 보고서

- [ ] **Step 1: test 열기**
  - 최종 구성마다 test를 k=5로 한 번씩 엽니다.
    - hybrid + 가드레일
    - Qwen2.5-3B `real` (Task 8에서 반영했을 때만)
  - `test_opens.jsonl`에 기록되는지 확인합니다.
- [ ] **Step 2: `evals/routing/docs/experiment_report.md` 갱신**
  - 결과표에 새 행을 추가합니다.
  - "아직 틀리는 것" 표를 새로 씁니다.
  - "저장된 확률로 바로 계산할 수 있음" 문장을 바로잡습니다. 확률은 서버가 주지만 이전 코드가 버렸고, Task 1부터 저장한다는 내용입니다.
  - 기준값 탐색 표와 dev CI 폭에 대한 주의 문장을 넣습니다.
- [ ] **Step 3:** 커밋합니다. `docs(evals): single-turn fix results`
  - PR은 사용자 승인 뒤에 만듭니다.
