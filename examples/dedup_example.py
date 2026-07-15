"""Example: run deduplication against an offline fixture and write CSV."""

import json
from pathlib import Path

from anki_insights import Deduplicator
from anki_insights.tokenizers import SpacyTokenizer


def main() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_notes.json"
    notes = json.loads(fixture.read_text(encoding="utf-8"))

    tokenizer = SpacyTokenizer("en_core_web_sm")
    dedup = Deduplicator(tokenizer, "Front")
    res = dedup.analyze(notes)
    out = Path(__file__).parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "anki_dedup_example.csv").open("w", encoding="utf-8") as fh:
        fh.write("order,note_id,status,text,tokens,new_tokens\n")
        for r in res.rows:
            fh.write(
                f"{r['order']},{r['note_id']},{r['status']},\"{r['text']}\",\"{r['tokens']}\",\"{r['new_tokens']}\"\n"
            )


if __name__ == "__main__":
    main()
