from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class AnkiClientError(RuntimeError):
    pass


class AnkiClient:
    def __init__(self, url: str, timeout: int = 60) -> None:
        self.url = url
        self.timeout = timeout

    def _invoke(self, action: str, **params: Any) -> Any:
        try:
            response = requests.post(
                self.url,
                json={"action": action, "version": 6, "params": params},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AnkiClientError("AnkiConnect request failed") from exc

        data = response.json()
        if data.get("error"):
            raise AnkiClientError(data["error"])

        return data["result"]

    def find_notes(self, query: str) -> List[int]:
        return self._invoke("findNotes", query=query)

    def get_notes(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        if not note_ids:
            return []
        return self._invoke("notesInfo", notes=note_ids)

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        if not notes:
            return []
        return self._invoke("addNotes", notes=notes)

    def add_tags(self, note_ids: List[int], tag: str) -> None:
        if note_ids:
            self._invoke("addTags", notes=note_ids, tags=tag)

    def create_deck(self, deck_name: str) -> None:
        self._invoke("createDeck", deck=deck_name)
