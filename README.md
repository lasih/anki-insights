# anki-insights

Utilities for deduplicating and transforming Anki note collections with a simple, production-friendly API.

## Features

- Deduplicate notes using language-aware tokenizers for English, French, Spanish, Indonesian, and Mandarin
- Run deduplication from the CLI or directly from Python
- Export CSV reports and optional duplicate-tagging for Anki workflows
- Invert notes between decks with backup snapshots

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[testing]
```

Optional spaCy models:

```bash
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
python -m spacy download es_core_news_sm
```

## Quick start

### CLI deduplication

```bash
anki-insights dedup --language en
anki-insights dedup --deck "My Deck" --language fr --output-dir reports
```

### Python API

```python
from anki_insights.deduplicate import dedup_texts
from anki_insights.tokenizers import SpacyTokenizer

result = dedup_texts(
    ["Bonjour le monde", "Bonjour monde"],
    tokenizer=SpacyTokenizer("fr_core_news_sm"),
)
print(result.keep_ids, result.duplicate_ids)
```

## Documentation

See the docs folder for MkDocs-based documentation.

## Testing

```bash
python -m pytest tests
```

