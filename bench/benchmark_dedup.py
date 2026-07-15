"""Simple benchmark harness for tokenization/dedup over a synthetic large dataset."""

import time
from typing import List

from anki_insights import Deduplicator, SpacyTokenizer


def make_notes(n: int) -> List[dict]:
    notes = []
    for i in range(n):
        notes.append(
            {"noteId": i, "fields": {"Front": {"value": f"word{i} word{i+1}"}}}
        )
    return notes


def benchmark(n: int = 100_000) -> None:
    tokenizer = SpacyTokenizer("en_core_web_sm")
    dedup = Deduplicator(tokenizer, "Front")
    notes = make_notes(n)
    t0 = time.perf_counter()
    res = dedup.analyze(notes)
    t1 = time.perf_counter()
    print("Processed", n, "notes in", t1 - t0, "seconds")
    print("Unique tokens:", len(res.seen_tokens))


if __name__ == "__main__":
    benchmark(10000)
