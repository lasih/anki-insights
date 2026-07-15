from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_data(self) -> str:
        return "".join(self._parts)


def strip_html(text: str) -> str:
    stripper = HTMLStripper()
    stripper.feed(html.unescape(text or ""))
    return stripper.get_data()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()
