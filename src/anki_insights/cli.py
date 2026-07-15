"""Command-line interface for anki-insights.

Provides a minimal Typer app so the package entrypoint works after `src/` layout.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from .deduplicate import Deduplicator
from .tokenizers import build_tokenizer

app = typer.Typer(name="anki-insights", add_completion=False)


def _resolve_tokenizer(language: str):
    try:
        return build_tokenizer(language)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(
            f"Unable to configure tokenizer for language '{language}': {exc}"
        ) from exc


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
def dedup(
    language: str = "en",
    field: str = "Front",
    deck: str = "",
    anki_url: str = "http://localhost:8765",
    tag_duplicates: bool = True,
    output_dir: str = "reports",
    cache_path: str | None = None,
) -> None:
    """Deduplicate a deck from AnkiConnect or run the bundled offline demo."""
    import json

    if deck:
        from .core.deduplicate import DedupConfig, run_deduplication

        tokenizer = _resolve_tokenizer(language)

        report_path = (
            Path(output_dir) / f"dedup_{deck.replace(' ', '_').lower()}_report.csv"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)

        config = DedupConfig(
            anki_url=anki_url,
            deck_name=deck,
            front_field=field,
            export_csv_path=str(report_path),
            tag_duplicates=tag_duplicates,
            token_cache_path=cache_path,
        )
        result = run_deduplication(config, tokenizer)
        typer.echo(
            f"kept={len(result.keep_ids)} duplicates={len(result.duplicate_ids)}"
        )
        return

    fixture = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "fixtures"
        / "sample_notes.json"
    )
    notes = json.loads(fixture.read_text(encoding="utf-8"))

    tokenizer = _resolve_tokenizer(language)
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
