from __future__ import annotations

from typing import Iterable

from anki_insights.core.deduplicate import (
    AnalysisResult,
    AnkiField,
    AnkiNote,
    DedupConfig,
    Deduplicator,
    ReportRow,
    export_csv,
    run_deduplication,
)
from anki_insights.tokenizers import IndonesianTokenizer, Tokenizer


def dedup_texts(
    texts: Iterable[str],
    *,
    tokenizer: Tokenizer | None = None,
    field: str = "Front",
) -> AnalysisResult:
    """Deduplicate a plain iterable of text strings in one simple call."""
    notes = [
        {"noteId": index, "fields": {field: {"value": text}}}
        for index, text in enumerate(texts, start=1)
    ]
    deduplicator = Deduplicator(tokenizer or IndonesianTokenizer(), field)
    return deduplicator.analyze(notes)


__all__ = [
    "AnkiField",
    "AnkiNote",
    "AnalysisResult",
    "DedupConfig",
    "Deduplicator",
    "ReportRow",
    "dedup_texts",
    "export_csv",
    "run_deduplication",
]
