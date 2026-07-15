from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, TypedDict, cast

from anki_insights.core.anki import AnkiClient
from anki_insights.io.html_utils import normalize_whitespace, strip_html
from anki_insights.tokenizers import Tokenizer

logger = logging.getLogger(__name__)


class AnkiField(TypedDict):
    value: str


class AnkiNote(TypedDict, total=False):
    noteId: int
    fields: Dict[str, AnkiField]


class ReportRow(TypedDict):
    order: int
    note_id: int
    status: str
    text: str
    tokens: str
    new_tokens: str


@dataclass(frozen=True)
class DedupConfig:
    anki_url: str
    deck_name: str
    front_field: str
    export_csv_path: str
    tag_duplicates: bool = True
    duplicate_tag: str = "token_duplicate"
    token_cache_path: str | None = None


@dataclass(frozen=True)
class AnalysisResult:
    keep_ids: List[int]
    duplicate_ids: List[int]
    rows: List[ReportRow]
    seen_tokens: Set[str]


class Deduplicator:
    def __init__(self, tokenizer: Tokenizer, front_field: str) -> None:
        self._tokenizer = tokenizer
        self._front_field = front_field

    def _extract_text(self, note: AnkiNote) -> str:
        fields = note.get("fields")
        if not fields or not isinstance(fields, dict):
            raw = ""
        else:
            anki_field = fields.get(self._front_field)
            if anki_field and isinstance(anki_field, dict):
                raw = anki_field.get("value", "")
            else:
                raw = ""

        return normalize_whitespace(strip_html(str(raw)))

    def analyze(
        self, notes: List[AnkiNote], initial_seen: Set[str] | None = None
    ) -> AnalysisResult:
        seen: Set[str] = set(initial_seen or set())
        keep_ids: List[int] = []
        duplicate_ids: List[int] = []
        rows: List[ReportRow] = []

        for order, note in enumerate(notes, start=1):
            note_id = note["noteId"]
            text = self._extract_text(note)

            if not text:
                duplicate_ids.append(note_id)
                rows.append(
                    {
                        "order": order,
                        "note_id": note_id,
                        "status": "EMPTY",
                        "text": text,
                        "tokens": "",
                        "new_tokens": "",
                    }
                )
                continue

            tokens = self._tokenizer.tokenize(text)
            new_tokens = tokens - seen

            if new_tokens:
                keep_ids.append(note_id)
                seen.update(tokens)
                status = "KEEP"
            else:
                duplicate_ids.append(note_id)
                status = "DUPLICATE"

            rows.append(
                {
                    "order": order,
                    "note_id": note_id,
                    "status": status,
                    "text": text,
                    "tokens": " | ".join(sorted(tokens)),
                    "new_tokens": " | ".join(sorted(new_tokens)),
                }
            )

        return AnalysisResult(keep_ids, duplicate_ids, rows, seen)


def export_csv(rows: List[ReportRow], path: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["order", "note_id", "status", "text", "tokens", "new_tokens"],
        )
        writer.writeheader()
        writer.writerows(rows)


def run_deduplication(config: DedupConfig, tokenizer: Tokenizer) -> AnalysisResult:
    client = AnkiClient(config.anki_url)
    deduplicator = Deduplicator(tokenizer, config.front_field)

    # optional persistent token cache (useful for incremental runs)
    cache_path = config.token_cache_path
    initial_seen: Set[str] = set()
    if cache_path:
        try:
            import json

            p = Path(cache_path)
            if p.exists():
                with p.open("r", encoding="utf-8") as fh:
                    initial_seen = set(json.load(fh))
        except Exception:
            initial_seen = set()

    note_ids = client.find_notes(f'deck:"{config.deck_name}"')
    notes = client.get_notes(note_ids)
    if not note_ids:
        result = AnalysisResult([], [], [], set())
        export_csv(result.rows, config.export_csv_path)
        logger.info("Deck: %s", config.deck_name)
        logger.info("Total: %d", 0)
        logger.info("Keep: %d", 0)
        logger.info("Duplicate: %d", 0)
        logger.info("Unique tokens: %d", 0)
        logger.info("CSV: %s", config.export_csv_path)
        return result
    # `client.get_notes` returns untyped dicts from AnkiConnect; cast for analysis
    notes_typed = cast(List[AnkiNote], notes)
    result = deduplicator.analyze(notes_typed, initial_seen=initial_seen)

    # persist seen tokens back to cache if requested
    if cache_path:
        try:
            import json

            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", encoding="utf-8") as fh:
                json.dump(sorted(result.seen_tokens), fh, ensure_ascii=False)
        except Exception:
            pass

    export_csv(result.rows, config.export_csv_path)

    logger.info("Deck: %s", config.deck_name)
    logger.info("Total: %d", len(notes))
    logger.info("Keep: %d", len(result.keep_ids))
    logger.info("Duplicate: %d", len(result.duplicate_ids))
    logger.info("Unique tokens: %d", len(result.seen_tokens))
    logger.info("CSV: %s", config.export_csv_path)

    if config.tag_duplicates and result.duplicate_ids:
        client.add_tags(result.duplicate_ids, config.duplicate_tag)

    return result
