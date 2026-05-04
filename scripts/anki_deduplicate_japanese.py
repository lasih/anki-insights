import csv
import html
import re
from html.parser import HTMLParser
from typing import List, Set, Dict, Any

import requests
from fugashi import Tagger

# =========================
# CONFIG
# =========================
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "🇯🇵"
FRONT_FIELD = "Front"

TAG_DUPLICATES = True
DUPLICATE_TAG = "jp_token_duplicate"

EXPORT_CSV_PATH = "anki_japanese_token_dedup_report.csv"

# =========================
# JAPANESE TOKENIZATION
# =========================
# Using fugashi, a MeCab wrapper, to tokenize Japanese text.
# Japanese requires morphological analysis because words are not separated by spaces. 
# We filter out common particles (stopwords)
tagger = Tagger()

# Stopwords: Japanese particles that are usually not useful for vocab analysis
STOPWORDS = {"は", "が", "を", "に", "の", "と", "で", "も", "へ", "や", "ね", "よ"}

# Allowed POS: focus on nouns, verbs, adjectives for meaningful vocab
ALLOWED_POS = {"名詞", "動詞", "形容詞"}

# =========================
# ANKICONNECT
# =========================
def invoke(action: str, **params) -> Any:
    response = requests.post(
        ANKI_CONNECT_URL,
        json={
            "action": action,
            "version": 6,
            "params": params,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(
            f"AnkiConnect error for action '{action}': {payload['error']}"
        )
    return payload["result"]


def find_notes_in_deck(deck_name: str) -> List[int]:
    query = f'deck:"{deck_name}"'
    return invoke("findNotes", query=query)


def notes_info(note_ids: List[int]) -> List[Dict[str, Any]]:
    if not note_ids:
        return []
    return invoke("notesInfo", notes=note_ids)


def add_tags(note_ids: List[int], tag: str) -> None:
    if note_ids:
        invoke("addTags", notes=note_ids, tags=tag)


# =========================
# HTML CLEANING
# =========================
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_data(self) -> str:
        return "".join(self.parts)


def strip_html(text: str) -> str:
    text = html.unescape(text)
    stripper = MLStripper()
    stripper.feed(text)
    return stripper.get_data()


# =========================
# JAPANESE TOKENIZATION
# =========================
def normalize_japanese_token(token_text: str) -> str:
    if not token_text:
        return ""

    token_text = str(token_text).strip()

    if not token_text:
        return ""

    if token_text.isdigit():
        return ""

    return token_text


def tokenize_japanese(text: str) -> Set[str]:
    out: Set[str] = set()

    for word in tagger(text):
        pos = word.feature.pos1
        if pos not in ALLOWED_POS:
            continue

        lemma = word.feature.lemma
        if not lemma or lemma == "*":
            lemma = word.surface

        norm = normalize_japanese_token(lemma)

        if not norm:
            continue

        if norm in STOPWORDS:
            continue

        out.add(norm)

    return out


# =========================
# CORE LOGIC
# =========================
def extract_front_text(note: Dict[str, Any], front_field: str) -> str:
    fields = note.get("fields", {})
    if front_field not in fields:
        return ""
    raw = fields[front_field].get("value", "")
    return strip_html(raw).strip()


def analyze_notes(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    seen_tokens: Set[str] = set()
    keep_note_ids: List[int] = []
    duplicate_note_ids: List[int] = []
    rows: List[Dict[str, Any]] = []

    for idx, note in enumerate(notes, start=1):
        note_id = note["noteId"]
        front_text = extract_front_text(note, FRONT_FIELD)

        if not front_text:
            duplicate_note_ids.append(note_id)
            rows.append(
                {
                    "order": idx,
                    "note_id": note_id,
                    "status": "DUPLICATE_EMPTY",
                    "front_text": front_text,
                    "tokens": "",
                    "new_tokens": "",
                }
            )
            continue

        tokens = tokenize_japanese(front_text)

        new_tokens = tokens - seen_tokens

        if new_tokens:
            keep_note_ids.append(note_id)
            seen_tokens.update(tokens)
            status = "KEEP"
        else:
            duplicate_note_ids.append(note_id)
            status = "DUPLICATE"

        rows.append(
            {
                "order": idx,
                "note_id": note_id,
                "status": status,
                "front_text": front_text,
                "tokens": " | ".join(sorted(tokens)),
                "new_tokens": " | ".join(sorted(new_tokens)),
            }
        )

    return {
        "keep_note_ids": keep_note_ids,
        "duplicate_note_ids": duplicate_note_ids,
        "rows": rows,
        "seen_tokens": seen_tokens,
    }


def export_csv(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "order",
                "note_id",
                "status",
                "front_text",
                "tokens",
                "new_tokens",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    note_ids = find_notes_in_deck(DECK_NAME)
    notes = notes_info(note_ids)

    result = analyze_notes(notes)

    keep_note_ids = result["keep_note_ids"]
    duplicate_note_ids = result["duplicate_note_ids"]
    rows = result["rows"]
    seen_tokens = result["seen_tokens"]

    export_csv(rows, EXPORT_CSV_PATH)

    print(f"Deck: {DECK_NAME}")
    print(f"Total notes: {len(notes)}")
    print(f"Keep: {len(keep_note_ids)}")
    print(f"Duplicates: {len(duplicate_note_ids)}")
    print(f"Unique tokens: {len(seen_tokens)}")
    print(f"CSV report: {EXPORT_CSV_PATH}")

    if TAG_DUPLICATES and duplicate_note_ids:
        add_tags(duplicate_note_ids, DUPLICATE_TAG)
        print(f"Tagged duplicates with: {DUPLICATE_TAG}")

    print("\nDone.")


if __name__ == "__main__":
    main()