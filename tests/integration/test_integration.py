import json
from pathlib import Path

from anki_insights import Deduplicator
from anki_insights.tokenizers import build_tokenizer


def test_offline_dedup_fixture(tmp_path: Path):
    fixture = Path(__file__).parents[2] / "examples" / "fixtures" / "sample_notes.json"
    notes = json.loads(fixture.read_text(encoding="utf-8"))

    tokenizer = build_tokenizer("en")
    dedup = Deduplicator(tokenizer, "Front")
    res = dedup.analyze(notes)

    assert res.keep_ids
    assert isinstance(res.rows, list)
