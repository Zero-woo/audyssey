"""Routing evaluation set: case format, fixtures, splits and labeler agreement."""

import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from audyssey.contracts import Job, Model


class Case(Model):
    id: str
    fixture: Literal["F1", "F2", "F3", "F4", "F5"]
    request: str
    category: Literal[
        "positive", "none", "near_miss", "clarify", "constraint", "composite"
    ]
    pair: str | None = None
    template: str
    expected: list[dict]
    split: Literal["train", "dev", "test"] | None = None


def load_cases(path: Path) -> list[Case]:
    return [
        Case.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def load_fixture(root: Path, name: str) -> Job:
    return Job.model_validate_json((root / f"{name}.json").read_text())


def assign_splits(cases: list[Case], seed: int = 0) -> list[Case]:
    """Split by template (never by case) within each category, about 40/30/30."""
    templates: dict[str, set[str]] = defaultdict(set)
    category_of: dict[str, str] = {}
    for c in cases:
        if category_of.setdefault(c.template, c.category) != c.category:
            raise ValueError(
                f"template {c.template!r} appears under more than one category"
            )
        templates[c.category].add(c.template)
    split_of: dict[tuple[str, str], Literal["train", "dev", "test"]] = {}
    rng = random.Random(seed)
    for category in sorted(templates):
        names = sorted(templates[category])
        rng.shuffle(names)
        n_train = round(len(names) * 0.4)
        n_dev = round(len(names) * 0.3)
        for i, t in enumerate(names):
            split_of[category, t] = (
                "train" if i < n_train else "dev" if i < n_train + n_dev else "test"
            )
    return [
        c.model_copy(update={"split": split_of[c.category, c.template]}) for c in cases
    ]


def blank_labels(cases: list[Case]) -> list[dict]:
    return [{"id": c.id, "fixture": c.fixture, "request": c.request} for c in cases]


def kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two labelers' category labels."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    chance = sum(ca[k] * cb[k] for k in ca) / n**2
    if chance == 1:
        return 1.0
    return (observed - chance) / (1 - chance)
