from anki_insights.invert import InvertConfig, Inverter


class FakeAnkiClient:
    def __init__(self):
        self.notes = [
            {
                "noteId": 1,
                "fields": {
                    "Front": {"value": "uno"},
                    "Back": {"value": "one"},
                },
            },
            {
                "noteId": 2,
                "fields": {
                    "Front": {"value": "dos"},
                    "Back": {"value": "two"},
                },
            },
        ]
        self.created = []

    def find_notes(self, query):
        return [note["noteId"] for note in self.notes]

    def get_notes(self, note_ids):
        return [note for note in self.notes if note["noteId"] in note_ids]

    def create_deck(self, deck_name):
        self.deck = deck_name

    def add_notes(self, notes):
        self.created = notes
        return [101, 102]

    def add_tags(self, note_ids, tag):
        self.tags = (note_ids, tag)


def test_inverter_builds_notes_and_summary(monkeypatch, tmp_path):
    cfg = InvertConfig(
        anki_url="http://localhost:8765",
        source_deck="source",
        target_deck="target",
        backup_root=str(tmp_path),
    )

    inverter = Inverter(cfg)
    monkeypatch.setattr(inverter, "client", FakeAnkiClient())

    summary = inverter.run()

    assert summary["found"] == 2
    assert summary["created"] == 2
    assert summary["backup"].startswith(str(tmp_path))
