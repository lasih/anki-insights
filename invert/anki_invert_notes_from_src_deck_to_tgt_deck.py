from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


# =========================
# CONFIG
# =========================
@dataclass(frozen=True)
class Config:
    anki_url: str
    source_deck: str
    target_deck: str
    source_tag: str = "copied_source"
    target_tag: str = "copied_inverted"
    model_name: str = "Basic"
    front_field: str = "Front"
    back_field: str = "Back"
    backup_root: str = "backup"


# =========================
# ANKI CLIENT
# =========================
class AnkiClient:
    def __init__(self, url: str) -> None:
        self.url = url

    def invoke(self, action: str, **params: Any) -> Any:
        payload = json.dumps(
            {"action": action, "version": 6, "params": params}
        ).encode("utf-8")

        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError("AnkiConnect not reachable") from exc

        if data.get("error"):
            raise RuntimeError(data["error"])

        return data["result"]

    def find_notes(self, query: str) -> List[int]:
        return self.invoke("findNotes", query=query)

    def get_notes(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        if not note_ids:
            return []
        return self.invoke("notesInfo", notes=note_ids)

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        return self.invoke("addNotes", notes=notes)

    def add_tags(self, note_ids: List[int], tag: str) -> None:
        if note_ids:
            self.invoke("addTags", notes=note_ids, tags=tag)

    def create_deck(self, deck: str) -> None:
        self.invoke("createDeck", deck=deck)


# =========================
# UTIL
# =========================
def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# =========================
# CORE ENGINE
# =========================
class Inverter:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.client = AnkiClient(cfg.anki_url)

    # -------------------------
    # QUERY
    # -------------------------
    def _find_source_notes(self) -> List[int]:
        query = (
            f'deck:"{self.cfg.source_deck}" '
            f'-tag:{self.cfg.source_tag}'
        )
        return self.client.find_notes(query)

    # -------------------------
    # TRANSFORM
    # -------------------------
    def _build_notes(
        self, notes: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[int]]:
        payload: List[Dict[str, Any]] = []
        source_ids: List[int] = []

        for note in notes:
            nid = note["noteId"]
            fields = note.get("fields", {})

            front = fields.get(self.cfg.front_field, {}).get("value", "").strip()
            back = fields.get(self.cfg.back_field, {}).get("value", "").strip()

            if not front or not back:
                continue

            payload.append(
                {
                    "deckName": self.cfg.target_deck,
                    "modelName": self.cfg.model_name,
                    "fields": {
                        self.cfg.front_field: back,
                        self.cfg.back_field: front,
                    },
                    "tags": [],
                    "options": {
                        "allowDuplicate": True
                    },
                }
            )

            source_ids.append(nid)

        return payload, source_ids

    # -------------------------
    # TAGGING
    # -------------------------
    def _tag(self, source_ids: List[int], created_ids: List[Optional[int]]) -> None:
        for sid, tid in zip(source_ids, created_ids):
            if tid is None:
                continue

            self.client.add_tags([sid], self.cfg.source_tag)
            self.client.add_tags([tid], self.cfg.target_tag)

    # -------------------------
    # BACKUP
    # -------------------------
    def _backup(self, notes: List[Dict[str, Any]]) -> str:
        path = os.path.join(self.cfg.backup_root, now_ts())
        ensure_dir(path)
        save_json(os.path.join(path, "snapshot.json"), notes)
        return path

    # -------------------------
    # RUN
    # -------------------------
    def run(self) -> None:
        self.client.create_deck(self.cfg.target_deck)

        source_ids = self._find_source_notes()
        source_notes = self.client.get_notes(source_ids)

        backup_dir = self._backup(source_notes)

        if not source_notes:
            print("No new notes found.")
            print(f"Backup: {backup_dir}")
            return

        payload, valid_ids = self._build_notes(source_notes)

        if not payload:
            print("No valid notes.")
            return

        created_ids = self.client.add_notes(payload)

        self._tag(valid_ids, created_ids)

        summary = {
            "source_deck": self.cfg.source_deck,
            "target_deck": self.cfg.target_deck,
            "found": len(source_notes),
            "created": sum(x is not None for x in created_ids),
            "backup": backup_dir,
        }

        save_json(os.path.join(backup_dir, "run_summary.json"), summary)

        print(f"Found: {len(source_notes)}")
        print(f"Created: {summary['created']}")
        print(f"Backup: {backup_dir}")


# =========================
# ENTRYPOINT
# =========================
def main() -> None:
    cfg = Config(
        anki_url="http://127.0.0.1:8765",
        source_deck="🇮🇩",
        target_deck="🇦🇺",
    )

    Inverter(cfg).run()


if __name__ == "__main__":
    main()