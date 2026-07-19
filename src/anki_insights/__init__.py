"""Public package exports for anki_insights (src layout).

This module re-exports the high-level API for convenience.
"""

from .core.anki import AnkiClient, AnkiClientError
from .core.deduplicate import (
    AnalysisResult,
    DedupConfig,
    Deduplicator,
    export_csv,
    run_deduplication,
)
from .core.invert import InvertConfig, Inverter
from .io.html_utils import normalize_whitespace, strip_html
from .tokenizers import (
    IndonesianTokenizer,
    JapaneseTokenizer,
    MandarinTokenizer,
    SpacyTokenizer,
    Tokenizer,
)

__all__ = [
    "AnkiClient",
    "AnkiClientError",
    "DedupConfig",
    "Deduplicator",
    "AnalysisResult",
    "export_csv",
    "run_deduplication",
    "normalize_whitespace",
    "strip_html",
    "InvertConfig",
    "Inverter",
    "IndonesianTokenizer",
    "MandarinTokenizer",
    "JapaneseTokenizer",
    "SpacyTokenizer",
    "Tokenizer",
]
