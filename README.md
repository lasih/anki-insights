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

Run a language-specific script or call the shared library.

```bash
python deduplicate/anki_deduplicate_spanish.py
```

### Inversion

```bash
python invert/anki_invert_notes_from_src_deck_to_tgt_deck.py
```

## Testing

```bash
python -m pytest tests
```

