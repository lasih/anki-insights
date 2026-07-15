from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

from anki_insights.core.anki import AnkiClient
from anki_insights.core.utils import ensure_dir, now_ts, save_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvertConfig:
    anki_url: str
    source_deck: str
    target_deck: str
    source_tag: str = "copied_source"
    target_tag: str = "copied_inverted"
    model_name: str = "Basic"
    front_field: str = "Front"
    back_field: str = "Back"
    backup_root: str = "backup"


class Inverter:
    def __init__(self, config: InvertConfig) -> None:
        self.config = config
        self.client = AnkiClient(config.anki_url)

    def _find_source_notes(self) -> List[int]:
        query = f'deck:"{self.config.source_deck}" -tag:{self.config.source_tag}'
        return self.client.find_notes(query)

    def _normalize_field(self, fields: Dict[str, Any], field_name: str) -> str:
        return str(fields.get(field_name, {}).get("value", "")).strip()

    def _build_notes(
        self, notes: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[int]]:
        payload: List[Dict[str, Any]] = []
        source_ids: List[int] = []

        for note in notes:
            note_id = note["noteId"]
            fields = note.get("fields", {})
            front = self._normalize_field(fields, self.config.front_field)
            back = self._normalize_field(fields, self.config.back_field)

            if not front or not back:
                continue

            payload.append(
                {
                    "deckName": self.config.target_deck,
                    "modelName": self.config.model_name,
                    "fields": {
                        self.config.front_field: back,
                        self.config.back_field: front,
                    },
                    "tags": [],
                    "options": {"allowDuplicate": True},
                }
            )
            source_ids.append(note_id)

        return payload, source_ids

    def _tag_notes(
        self, source_ids: List[int], created_ids: List[Optional[int]]
    ) -> None:
        for source_id, target_id in zip(source_ids, created_ids, strict=False):
            if target_id is None:
                continue
            self.client.add_tags([source_id], self.config.source_tag)
            self.client.add_tags([target_id], self.config.target_tag)

    def _backup_notes(self, notes: List[Dict[str, Any]]) -> str:
        backup_dir = os.path.join(self.config.backup_root, now_ts())
        ensure_dir(backup_dir)
        save_json(os.path.join(backup_dir, "snapshot.json"), notes)
        return backup_dir

    def run(self) -> dict[str, int | str]:
        self.client.create_deck(self.config.target_deck)

        source_ids = self._find_source_notes()
        source_notes = self.client.get_notes(source_ids)
        backup_dir = self._backup_notes(source_notes)

        if not source_notes:
            logger.info("No new notes found. Backup: %s", backup_dir)
            return cast(
                Dict[str, int | str],
                {
                    "found": 0,
                    "created": 0,
                    "backup": backup_dir,
                },
            )

        payload, valid_ids = self._build_notes(source_notes)

        if not payload:
            logger.info("No valid notes to create. Found: %d", len(source_notes))
            return cast(
                Dict[str, int | str],
                {
                    "found": len(source_notes),
                    "created": 0,
                    "backup": backup_dir,
                },
            )

        created_ids = self.client.add_notes(payload)
        self._tag_notes(valid_ids, created_ids)

        summary: Dict[str, int | str] = {
            "found": len(source_notes),
            "created": sum(1 for item in created_ids if item is not None),
            "backup": backup_dir,
        }
        save_json(os.path.join(backup_dir, "run_summary.json"), summary)
        logger.info(
            "Found: %d Created: %d Backup: %s",
            summary["found"],
            summary["created"],
            backup_dir,
        )
        return summary
