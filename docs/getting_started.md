# Getting Started

Install in editable mode and run tests:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[testing]
pytest -q
```

Quick CLI examples:

```bash
anki-insights dedup --deck-name "Default" --front-field "Front" --export-csv report.csv
anki-insights invert --source-deck "SRC" --target-deck "TGT"
```
