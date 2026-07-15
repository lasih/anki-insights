import json
from pathlib import Path

import spacy

from anki_insights import Deduplicator
from anki_insights.tokenizers import IndonesianTokenizer, SpacyTokenizer


def test_offline_dedup_fixture(tmp_path: Path):
    fixture = Path(__file__).parents[2] / "examples" / "fixtures" / "sample_notes.json"
    notes = json.loads(fixture.read_text(encoding="utf-8"))

    try:
        tokenizer = SpacyTokenizer("en_core_web_sm")
    except OSError:
        tokenizer = IndonesianTokenizer()

    dedup = Deduplicator(tokenizer, "Front")
    res = dedup.analyze(notes)

    assert res.keep_ids
    assert isinstance(res.rows, list)
