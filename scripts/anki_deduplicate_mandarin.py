from __future__ import annotations

import csv
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Protocol, Set, TypedDict

import requests
import jieba

try:
    from opencc import OpenCC  # type: ignore
except ImportError:
    OpenCC = None


# =========================
# CONFIG
# =========================
@dataclass(frozen=True)
class Config:
    anki_url: str
    deck_name: str
    front_field: str
    export_csv_path: str
    tag_duplicates: bool
    duplicate_tag: str


# =========================
# TYPES
# =========================
class AnkiField(TypedDict):
    value: str


class AnkiNote(TypedDict, total=False):
    noteId: int
    fields: Dict[str, AnkiField]


class ReportRow(TypedDict):
    order: int
    note_id: int
    status: str
    text: str
    chinese_tokens: str
    latin_tokens: str
    new_tokens: str


@dataclass(frozen=True)
class AnalysisResult:
    keep_ids: List[int]
    duplicate_ids: List[int]
    rows: List[ReportRow]
    seen_tokens: Set[str]


# =========================
# ANKI CLIENT
# =========================
class AnkiClient:
    def __init__(self, url: str) -> None:
        self._url: str = url

    def _invoke(self, action: str, **params: Any) -> Any:
        r = requests.post(
            self._url,
            json={"action": action, "version": 6, "params": params},
            timeout=60,
        )
        r.raise_for_status()

        data: Dict[str, Any] = r.json()
        if data.get("error"):
            raise RuntimeError(data["error"])

        return data["result"]

    def find_notes(self, deck: str) -> List[int]:
        return self._invoke("findNotes", query=f'deck:"{deck}"')

    def get_notes(self, note_ids: List[int]) -> List[AnkiNote]:
        if not note_ids:
            return []
        return self._invoke("notesInfo", notes=note_ids)

    def add_tags(self, note_ids: List[int], tag: str) -> None:
        if note_ids:
            self._invoke("addTags", notes=note_ids, tags=tag)


# =========================
# CLEANING
# =========================
class HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_data(self) -> str:
        return "".join(self._parts)


def strip_html(text: str) -> str:
    unescaped: str = html.unescape(text)
    s = HTMLStripper()
    s.feed(unescaped)
    return s.get_data()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# =========================
# TOKENIZER PROTOCOL
# =========================
class Tokenizer(Protocol):
    def tokenize(self, text: str) -> Set[str]:
        ...


# =========================
# MANDARIN TOKENIZER
# =========================
class MandarinTokenizer:
    """
    Tokenizer para mandarim:
    - normaliza Tradicional → Simplificado (opcional)
    - usa jieba para segmentação
    - fallback para caracteres individuais
    - não filtra frequência (todo conteúdo é considerado útil)
    """

    _chinese_re = re.compile(r"[\u4e00-\u9fff]")

    def __init__(
        self,
        *,
        use_opencc: bool = True,
        opencc_config: str = "t2s",
        char_fallback: bool = True,
    ) -> None:
        self._char_fallback: bool = char_fallback

        if use_opencc and OpenCC is not None:
            self._cc = OpenCC(opencc_config)
        else:
            self._cc = None

    def _normalize_script(self, text: str) -> str:
        if self._cc:
            return self._cc.convert(text)
        return text

    def _has_chinese(self, text: str) -> bool:
        return bool(self._chinese_re.search(text))

    def tokenize(self, text: str) -> Set[str]:
        normalized: str = self._normalize_script(text)
        tokens: Set[str] = set()

        for word in jieba.lcut(normalized, cut_all=False):
            w: str = word.strip()

            if not w:
                continue

            if self._has_chinese(w):
                tokens.add(w)
                continue

            if self._char_fallback:
                for ch in w:
                    if self._has_chinese(ch):
                        tokens.add(ch)

        return tokens


def extract_latin(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


# =========================
# DEDUPLICATION
# =========================
class Deduplicator:
    def __init__(self, tokenizer: Tokenizer, front_field: str) -> None:
        self._tokenizer: Tokenizer = tokenizer
        self._front_field: str = front_field

    def _extract_text(self, note: AnkiNote) -> str:
        fields: Dict[str, AnkiField] = note.get("fields", {})
        raw: str = fields.get(self._front_field, {}).get("value", "")
        return normalize_whitespace(strip_html(raw))

    def analyze(self, notes: List[AnkiNote]) -> AnalysisResult:
        seen: Set[str] = set()

        keep: List[int] = []
        dup: List[int] = []
        rows: List[ReportRow] = []

        for i, note in enumerate(notes, start=1):
            nid: int = note["noteId"]
            text: str = self._extract_text(note)

            if not text:
                dup.append(nid)
                rows.append({
                    "order": i,
                    "note_id": nid,
                    "status": "EMPTY",
                    "text": text,
                    "chinese_tokens": "",
                    "latin_tokens": "",
                    "new_tokens": "",
                })
                continue

            tokens: Set[str] = self._tokenizer.tokenize(text)
            new_tokens: Set[str] = tokens - seen

            latin: List[str] = extract_latin(text)

            if new_tokens:
                keep.append(nid)
                seen.update(tokens)
                status: str = "KEEP"
            else:
                dup.append(nid)
                status = "DUPLICATE"

            rows.append({
                "order": i,
                "note_id": nid,
                "status": status,
                "text": text,
                "chinese_tokens": " | ".join(sorted(tokens)),
                "latin_tokens": " | ".join(latin),
                "new_tokens": " | ".join(sorted(new_tokens)),
            })

        return AnalysisResult(keep, dup, rows, seen)


# =========================
# EXPORT
# =========================
def export_csv(rows: List[ReportRow], path: str) -> None:
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
                "new_tokens",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


# =========================
# RUNNER
# =========================
def run(config: Config) -> None:
    client: AnkiClient = AnkiClient(config.anki_url)

    tokenizer: Tokenizer = MandarinTokenizer(
        use_opencc=True,
        char_fallback=True,
    )

    dedup: Deduplicator = Deduplicator(
        tokenizer=tokenizer,
        front_field=config.front_field,
    )

    note_ids: List[int] = client.find_notes(config.deck_name)
    notes: List[AnkiNote] = client.get_notes(note_ids)

    result: AnalysisResult = dedup.analyze(notes)

    export_csv(result.rows, config.export_csv_path)

    print(f"Deck: {config.deck_name}")
    print(f"Total: {len(notes)}")
    print(f"Keep: {len(result.keep_ids)}")
    print(f"Duplicate: {len(result.duplicate_ids)}")
    print(f"Unique tokens: {len(result.seen_tokens)}")
    print(f"CSV: {config.export_csv_path}")

    if config.tag_duplicates and result.duplicate_ids:
        client.add_tags(result.duplicate_ids, config.duplicate_tag)


# =========================
# ENTRYPOINT
# =========================
def main() -> None:
    config = Config(
        anki_url="http://localhost:8765",
        deck_name="🇨🇳",
        front_field="Front",
        export_csv_path="anki_mandarin_dedup_report.csv",
        tag_duplicates=True,
        duplicate_tag="token_duplicate",
    )

    run(config)


if __name__ == "__main__":
    main()