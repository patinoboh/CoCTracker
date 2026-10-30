from collections.abc import Mapping
from typing import Any


def extract_level_records(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Keep useful level-shaped records while preserving the original payload."""
    records: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        level = value.get("level")
        if isinstance(level, int) and not isinstance(level, bool):
            name = value.get("name") or value.get("id") or value.get("type")
            records.append({"path": ".".join(path), "name": name, "level": level})
        for key, child in value.items():
            records.extend(extract_level_records(child, (*path, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            records.extend(extract_level_records(child, (*path, str(index))))
    return records
