import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import typer
import uvicorn

from audyssey.api import create_app
from audyssey.routing_eval import (
    INPUT_TOKENS_PER_CALL,
    git_sha,
    load_cases,
    run_eval,
    uncached_calls,
)
from audyssey.settings import Settings
from audyssey.tools.routing import load_router
from audyssey.toolserver import create_tool_app


class Tool(str, Enum):
    separation = "separation"
    filtering = "filtering"
    grounding = "grounding"
    generation = "generation"


app = typer.Typer()


@app.callback()
def callback() -> None:
    """Audyssey audio editing skeleton."""


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8600) -> None:
    uvicorn.run(create_app(), host=host, port=port)


@app.command()
def tool_server(
    tool: Annotated[list[Tool], typer.Option()],
    impl: Annotated[Literal["stub", "real"], typer.Option()] = "stub",
    host: str = "127.0.0.1",
    port: int = 8700,
) -> None:
    token = Settings().tool_token
    if host not in {"127.0.0.1", "localhost", "::1"} and not token:
        typer.echo(
            "AUDYSSEY_TOOL_TOKEN is required when binding to a non-loopback host"
        )
        raise typer.Exit(1)
    uvicorn.run(
        create_tool_app([item.value for item in tool], impl, token),
        host=host,
        port=port,
    )


MAX_TEST_OPENS = 3


@app.command()
def eval_routing(
    out: Annotated[Path, typer.Option()],
    split: Annotated[Literal["train", "dev", "test"], typer.Option()],
    router: Annotated[Literal["stub", "real"], typer.Option()] = "stub",
    k: int = 5,
    yes: bool = False,
    cases: Path = Path("evals/routing/cases.jsonl"),
    fixtures: Path = Path("evals/routing/fixtures"),
) -> None:
    """Route each labeled case k times without executing commands."""

    def fail(message: str) -> typer.Exit:
        typer.echo(message)
        return typer.Exit(1)

    if out.exists():
        raise fail(f"{out} already exists; results are never overwritten")
    all_cases = load_cases(cases)
    if any(c.split is None for c in all_cases):
        raise fail("some cases have no split; run assign_splits first")
    selected = [c for c in all_cases if c.split == split]
    if not selected:
        raise fail(f"no cases in split {split}")
    settings = Settings().model_copy(update={"router": router})
    model = "stub" if router == "stub" else settings.router_endpoint().model
    cache = cases.parent / "cache"
    if router == "real":
        calls = uncached_calls(model, selected, k, cache)
        if not yes:
            raise fail(
                f"{calls} uncached calls, about {calls * INPUT_TOKENS_PER_CALL} "
                "input tokens; rerun with --yes to pay for them"
            )
        if split == "test":
            log = cases.parent / "test_opens.jsonl"
            opens = log.read_text().splitlines() if log.exists() else []
            if len(opens) >= MAX_TEST_OPENS:
                raise fail(f"the test split was already opened {MAX_TEST_OPENS} times")
            entry = {
                "date": datetime.now(UTC).isoformat(),
                "model": model,
                "git_sha": git_sha(),
                "out": str(out),
            }
            log.write_text(
                "".join(f"{line}\n" for line in opens) + json.dumps(entry) + "\n"
            )
    run_eval(load_router(settings), model, selected, fixtures, k, out, cache)
    typer.echo(f"wrote {out}")


def main() -> None:
    app()
