from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
