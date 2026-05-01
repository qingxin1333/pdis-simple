from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def load_env_file(path: str | Path) -> Dict[str, str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}

    loaded: Dict[str, str] = {}
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = v.strip().strip('"').strip("'")
        if not key:
            continue
        loaded[key] = value
        if key not in os.environ:
            os.environ[key] = value

    return loaded

