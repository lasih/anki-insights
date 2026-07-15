from __future__ import annotations

import logging
from typing import Optional

import typer

from anki_insights.core.deduplicate import DedupConfig, run_deduplication
from anki_insights.core.invert import InvertConfig, Inverter
from anki_insights.tokenizers import SpacyTokenizer

app = typer.Typer()
logger = logging.getLogger(__name__)


@app.command()
def dedup(
    anki_url: str = "http://localhost:8765",
    deck_name: str = typer.Option(..., help="Deck name to analyze"),
    front_field: str = "Front",
    export_csv_path: str = "deduplicate/csv/anki_dedup_report.csv",
    model: str = "",
    tag_duplicates: bool = True,
    duplicate_tag: str = "token_duplicate",
) -> None:
    """Run deduplication for a deck."""
    if model:
        tokenizer = SpacyTokenizer(model)
    else:
        # default behavior: let caller pass language-specific tokenizer
        tokenizer = SpacyTokenizer("en_core_web_sm")

    cfg = DedupConfig(
        anki_url=anki_url,
        deck_name=deck_name,
        front_field=front_field,
        export_csv_path=export_csv_path,
        tag_duplicates=tag_duplicates,
        duplicate_tag=duplicate_tag,
    )

    run_deduplication(cfg, tokenizer)


@app.command()
def invert(
    anki_url: str = "http://localhost:8765",
    source_deck: str = typer.Option(..., help="Source deck to copy from"),
    target_deck: str = typer.Option(..., help="Target deck to create"),
    backup_root: str = "backup",
) -> None:
    """Invert notes from source deck into target deck."""
    cfg = InvertConfig(
        anki_url=anki_url,
        source_deck=source_deck,
        target_deck=target_deck,
        backup_root=backup_root,
    )

    res = Inverter(cfg).run()
    logger.info("Inversion summary: %s", res)


def main() -> None:
    app()
