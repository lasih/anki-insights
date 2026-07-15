# Contributing to anki-insights

Thanks for your interest! Please read these guidelines before submitting issues or pull requests.

1. Run tests and linters locally:

```bash
pip install -e .[testing]
pre-commit install
pre-commit run --all-files
pytest -q
```

2. Follow the coding style: `ruff` (see `ruff.toml`).

3. Add tests for new features and ensure mypy passes.

4. Use small, focused PRs with clear descriptions and include screenshots or sample output when relevant.
