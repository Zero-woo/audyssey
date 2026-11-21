import re

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
