from anki_insights.deduplicate import Deduplicator, dedup_texts


class DummyTokenizer:
    def tokenize(self, text: str):
        return set(text.lower().split())


def test_deduplicator_empty_note():
    dedup = Deduplicator(DummyTokenizer(), "Front")
    notes = [{"noteId": 1, "fields": {"Front": {"value": ""}}}]
    result = dedup.analyze(notes)
    assert result.keep_ids == []
    assert result.duplicate_ids == [1]
    assert result.rows[0]["status"] == "EMPTY"


def test_deduplicator_detects_duplicates():
    dedup = Deduplicator(DummyTokenizer(), "Front")
    notes = [
        {"noteId": 1, "fields": {"Front": {"value": "apple banana"}}},
        {"noteId": 2, "fields": {"Front": {"value": "banana apple"}}},
    ]
    result = dedup.analyze(notes)
    assert result.keep_ids == [1]
    assert result.duplicate_ids == [2]
    assert "banana" in result.seen_tokens
    assert "apple" in result.seen_tokens


def test_deduplicator_keeps_unique_note():
    dedup = Deduplicator(DummyTokenizer(), "Front")
    notes = [
        {"noteId": 1, "fields": {"Front": {"value": "apple"}}},
        {"noteId": 2, "fields": {"Front": {"value": "banana"}}},
    ]
    result = dedup.analyze(notes)
    assert result.keep_ids == [1, 2]
    assert result.duplicate_ids == []


def test_dedup_texts_returns_a_simple_result():
    result = dedup_texts(["apple banana", "banana apple"], tokenizer=DummyTokenizer())
    assert result.keep_ids == [1]
    assert result.duplicate_ids == [2]
