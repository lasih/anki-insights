import csv
import html
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Set

import requests
import jieba


# =========================
# CONFIG
# =========================
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "🇨🇳"
FRONT_FIELD = "Front"

TAG_DUPLICATES = True
DUPLICATE_TAG = "token_duplicate"

EXPORT_CSV_PATH = "anki_mandarin_dedup_report.csv"


# =========================
# ANKICONNECT
# =========================
def invoke(action: str, **params) -> Any:
    r = requests.post(
        ANKI_CONNECT_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data["result"]


def find_notes(deck: str) -> List[int]:
    return invoke("findNotes", query=f'deck:"{deck}"')


def notes_info(note_ids: List[int]) -> List[Dict[str, Any]]:
    if not note_ids:
        return []
    return invoke("notesInfo", notes=note_ids)


def add_tags(note_ids: List[int], tag: str) -> None:
    if note_ids:
        invoke("addTags", notes=note_ids, tags=tag)


# =========================
# CLEANING
# =========================
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data: str):
        self.parts.append(data)

    def get_data(self):
        return "".join(self.parts)


def strip_html(text: str) -> str:
    text = html.unescape(text)
    s = MLStripper()
    s.feed(text)
    return s.get_data()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# =========================
# TOKENIZATION
# =========================
def has_chinese(text: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def tokenize_chinese(text: str) -> Set[str]:
    tokens = set()

    for w in jieba.lcut(text, cut_all=False):
        w = w.strip()
        if not w:
            continue

        if not has_chinese(w):
            continue

        tokens.add(w)

    return tokens


def extract_latin(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


# =========================
# CORE LOGIC
# =========================
def extract_text(note: Dict[str, Any]) -> str:
    fields = note.get("fields", {})
    raw = fields.get(FRONT_FIELD, {}).get("value", "")
    return normalize(strip_html(raw))


def analyze(notes: List[Dict[str, Any]]):
    seen_words: Set[str] = set()

    keep_ids = []
    dup_ids = []
    rows = []

    for i, note in enumerate(notes, start=1):
        nid = note["noteId"]
        text = extract_text(note)

        if not text:
            dup_ids.append(nid)
            rows.append({
                "order": i,
                "note_id": nid,
                "status": "EMPTY",
                "text": text,
                "chinese_tokens": "",
                "latin_tokens": "",
                "new_words": "",
            })
            continue

        # Chinese vocabulary layer (dedup logic)
        words = tokenize_chinese(text)
        new_words = words - seen_words

        # Latin pass-through (ignored for logic)
        latin = extract_latin(text)

        if new_words:
            status = "KEEP"
            keep_ids.append(nid)
            seen_words.update(new_words)
        else:
            status = "DUPLICATE"
            dup_ids.append(nid)

        rows.append({
            "order": i,
            "note_id": nid,
            "status": status,
            "text": text,
            "chinese_tokens": " | ".join(sorted(words)),
            "latin_tokens": " | ".join(latin),
            "new_words": " | ".join(sorted(new_words)),
        })

    return keep_ids, dup_ids, rows, seen_words


# =========================
# EXPORT
# =========================
def export_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "order",
                "note_id",
                "status",
                "text",
                "chinese_tokens",
                "latin_tokens",
                "new_words",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


# =========================
# MAIN
# =========================
def main():
    note_ids = find_notes(DECK_NAME)
    notes = notes_info(note_ids)

    keep, dup, rows, seen = analyze(notes)

    export_csv(rows, EXPORT_CSV_PATH)

    print(f"Deck: {DECK_NAME}")
    print(f"Total: {len(notes)}")
    print(f"Keep: {len(keep)}")
    print(f"Duplicate: {len(dup)}")
    print(f"Unique Chinese words: {len(seen)}")
    print(f"CSV: {EXPORT_CSV_PATH}")

    if TAG_DUPLICATES and dup:
        add_tags(dup, DUPLICATE_TAG)
        print(f"Tagged duplicates: {DUPLICATE_TAG}")

    print("Done.")


if __name__ == "__main__":
    main()