# anki-insights

Utilities to analyze and manipulate Anki note collections: deduplication, inversion, and reporting.

Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[testing]
anki-insights --help
```

Docs: see `docs/` (mkdocs)
# Anki Insights

Utilities for Anki note deduplication and inversion.

## Features

- Deduplicate notes by token overlaps using language-specific tokenizers
- Export deduplication reports to CSV
- Invert source deck notes into a target deck with backup snapshots
- Shared Anki client and utilities for consistent behavior

## Installation

```bash
python -m pip install -e .
python -m spacy download fr_core_news_sm
python -m spacy download es_core_news_sm
```

## Usage

### Deduplication

Use the package API directly or the simple CLI entrypoint:

```bash
anki-insights dedup --language en
anki-insights dedup --language id
anki-insights dedup --language zh
```

### Inversion

```python
from anki_insights import Inverter, InvertConfig

config = InvertConfig(
    anki_url="http://localhost:8765",
    src_deck="Source",
    tgt_deck="Target",
)
Inverter(config).run()
```

## Testing

```bash
python -m pytest tests
```

