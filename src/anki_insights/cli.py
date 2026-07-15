"""Command-line interface for anki-insights.

Provides a minimal Typer app so the package entrypoint works after `src/` layout.
"""

from __future__ import annotations

import sys
from typing import Optional

import typer

from .deduplicate import Deduplicator
from .tokenizers import IndonesianTokenizer, MandarinTokenizer, SpacyTokenizer

app = typer.Typer(name="anki-insights", add_completion=False)


@app.command()
def version() -> None:
    """Print package version."""
    # Import locally to avoid importing heavy deps at CLI startup
    try:
        from importlib.metadata import version as _version

        v = _version("anki-insights")
    except Exception:
        v = "0.0.0"
    typer.echo(v)


@app.command()
def dedup(language: str = "en", field: str = "Front") -> None:
    """Run a basic offline deduplication demo using the bundled fixture."""
    import json
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "fixtures"
        / "sample_notes.json"
    )
    notes = json.loads(fixture.read_text(encoding="utf-8"))

    if language == "zh":
        tokenizer = MandarinTokenizer()
    elif language == "id":
        tokenizer = IndonesianTokenizer()
    else:
        try:
            tokenizer = SpacyTokenizer("en_core_web_sm")
        except OSError:
            tokenizer = IndonesianTokenizer()

    result = Deduplicator(tokenizer, field).analyze(notes)
    typer.echo(f"kept={len(result.keep_ids)} duplicates={len(result.duplicate_ids)}")


def main(argv: Optional[list[str]] | None = None) -> None:
    """Entrypoint for setuptools/script console.

    This function is referenced by `pyproject.toml` under `project.scripts`.
    """
    if argv is not None:
        sys.argv[1:] = argv
    app()


if __name__ == "__main__":
    main()
