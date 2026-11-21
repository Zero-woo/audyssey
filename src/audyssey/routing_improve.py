import json
import re
from collections.abc import Callable
from pathlib import Path

import httpx2

from audyssey.contracts import Job
from audyssey.routing_eval import (
    DESCRIPTIONS,
    Case,
    adopt,
    load_fixture,
    run_eval,
)
from audyssey.settings import LLMEndpoint
from audyssey.tools.planning.llm import chat_client
from audyssey.tools.routing import Routed, summarize

NEGATIVE = re.compile(r"하지\s*마|마세요|마십시오|말\s*것|않도록")
FIELDS = {"when", "instead", "params", "examples"}
MAX_LEN = 400


def overlaps(text: str, requests: list[str], n: int = 6) -> bool:
    """True if `text` shares any length-n substring (spaces count) with a request."""
    grams = {r[i : i + n] for r in requests for i in range(len(r) - n + 1)}
    return any(g in text for g in grams)


def validate(candidate: dict, current: dict, failed_requests: list[str]) -> list[str]:
    """Problems with a candidate descriptions dict; empty means valid.

    Only "commands" is read; "version" is not required.
    """
    problems = []
    got, want = candidate.get("commands"), current["commands"]
    if not isinstance(got, dict) or set(got) != set(want):
        return ["commands must be exactly " + ", ".join(want)]
    for name, d in got.items():
        if not isinstance(d, dict) or set(d) != FIELDS:
            problems.append(f"{name}: fields must be exactly {sorted(FIELDS)}")
            continue
        ex = d["examples"]
        if not all(
            isinstance(d[f], str) for f in ("when", "instead", "params")
        ) or not (isinstance(ex, list) and all(isinstance(e, str) for e in ex)):
            problems.append(
                f"{name}: when/instead/params must be str, examples list[str]"
            )
            continue
        size = (
            len(d["when"])
            + len(d["instead"])
            + len(d["params"])
            + sum(len(e) for e in ex)
        )
        if size > MAX_LEN:
            problems.append(f"{name}: {size} characters, limit {MAX_LEN}")
        if NEGATIVE.search(d["instead"]):
            problems.append(f"{name}: instead contains a prohibition")
        for f in FIELDS:
            for text in ex if f == "examples" else [d[f]]:
                if overlaps(text, failed_requests):
                    problems.append(f"{name}.{f}: copies a failed request")
    return problems


SYSTEM_PROMPT = """\
당신은 라우팅 모델이 읽는 명령 설명을 다듬는 편집자입니다.
작은 모델이 아래 실패 요청을 올바른 명령으로 라우팅하도록 설명을 다시 쓰십시오.
입력은 현재 설명(descriptions)과 실패 사례(failures)입니다.
각 실패는 요청(request), 작업 상태(job), 기대한 답(expected), 실제 답(got)을 담고 있습니다.

규칙:
- 모든 명령과 모든 필드(when, instead, params, examples)를 그대로 유지하십시오.
- 명령마다 when, instead, params, examples를 모두 합쳐 400자를 넘기지 마십시오.
- 실패 요청의 표현을 그대로 옮기지 마십시오. 6글자 이상 같은 문장 조각이 겹치면 안 됩니다.
- instead는 부정 명령(~하지 마세요)으로 쓰지 말고, 대신 해야 할 일을 긍정문으로 쓰십시오.
- 명령의 의미를 유지하십시오. 새로운 동작을 추가하지 마십시오.

출력은 스키마에 맞는 JSON 하나입니다.
"""

_COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "when": {"type": "string"},
        "instead": {"type": "string"},
        "params": {"type": "string"},
        "examples": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["when", "instead", "params", "examples"],
    "additionalProperties": False,
}


def _schema(names: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "commands": {
                "type": "object",
                "properties": {n: _COMMAND_SCHEMA for n in names},
                "required": names,
                "additionalProperties": False,
            }
        },
        "required": ["commands"],
        "additionalProperties": False,
    }


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def improve(
    route_with: Callable[[dict], Callable[[str, Job], Routed]],
    model: str,
    improver: LLMEndpoint,
    train: list[Case],
    dev: list[Case],
    fixtures: Path,
    cache: Path,
    out: Path,
    rounds: int = 5,
    transport: httpx2.BaseTransport | None = None,
) -> dict:
    """Rewrite descriptions from train failures; adopt a candidate only on dev."""
    out.mkdir(parents=True)
    client = chat_client(improver, transport)
    jobs = {c.fixture: load_fixture(fixtures, c.fixture) for c in train}

    def evaluate(d: dict, cases: list[Case], where: Path) -> dict:
        return run_eval(
            route_with(d),
            model,
            "real",
            cases,
            fixtures,
            1,
            where,
            cache,
            descriptions=d,
        )

    base = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    original = base
    best_metrics = evaluate(base, dev, out / "round-0" / "dev")
    best_round: int | None = None
    log: list[dict] = []
    for n in range(1, rounds + 1):
        rd = out / f"round-{n}"
        train_metrics_dir = rd / "train"
        run_eval(
            route_with(base),
            model,
            "real",
            train,
            fixtures,
            1,
            train_metrics_dir,
            cache,
            descriptions=base,
        )
        failures = [
            json.loads(line)
            for line in (train_metrics_dir / "cases.jsonl").read_text().splitlines()
            if not json.loads(line)["correct"]
        ]
        if not failures:
            break
        by_id = {c.id: c for c in train}
        sent = [
            {
                "request": f["request"],
                "job": summarize(jobs[by_id[f["id"]].fixture]),
                "expected": f["expected"],
                "got": f["decision"],
            }
            for f in failures
        ]
        (rd / "failures.jsonl").write_text(
            "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in sent)
        )
        user = json.dumps(
            {"descriptions": base["commands"], "failures": sent}, ensure_ascii=False
        )
        reply = client.chat.completions.create(
            model=improver.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=1.0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "descriptions",
                    "strict": True,
                    "schema": _schema(list(base["commands"])),
                },
            },
        )
        text = reply.choices[0].message.content or ""
        entry: dict = {"round": n}
        log.append(entry)
        verdict: dict
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if not isinstance(parsed, dict) or "commands" not in parsed:
            (rd / "candidate.json").write_text(text)
            problems = ["improver output is not a JSON object with commands"]
        else:
            candidate = {"version": base["version"], "commands": parsed["commands"]}
            _write(rd / "candidate.json", candidate)
            problems = validate(candidate, base, [f["request"] for f in failures])
        if problems:
            verdict = {"verdict": "rejected", "problems": problems}
            entry |= verdict
            _write(rd / "verdict.json", verdict)
            continue
        new = evaluate(candidate, dev, rd / "dev")
        problems = adopt(new, best_metrics)
        verdict = {
            "verdict": "not_adopted" if problems else "adopted",
            "problems": problems,
            "macro_f1": new["macro_f1"],
        }
        entry |= verdict
        _write(rd / "verdict.json", verdict)
        if not problems:
            base, best_metrics, best_round = candidate, new, n
    result = {"best_round": best_round, "rounds": log}
    _write(out / "summary.json", result)
    _write(out / "best.json", base if best_round is not None else original)
    return result | {"best": base}
