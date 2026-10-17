from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "fixtures" / "scenarios"
GENERATED = ROOT / "generated"
KNOWN_SCENARIOS = {"portfolio", "provider-failure", "uncertain-write"}


def scenario_paths(name: str) -> tuple[Path, Path, Path, Path]:
    if name not in KNOWN_SCENARIOS:
        raise ValueError(f"unknown scenario: {name}")
    base = SCENARIOS / name
    return (
        base / "source_events.json",
        base / "provider_state.json",
        GENERATED / f"{name}-state.json",
        GENERATED / f"{name}-report.json",
    )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: Any) -> None:
    GENERATED.mkdir(exist_ok=True)
    _assert_generated_file(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def reset_generated() -> list[str]:
    removed: list[str] = []
    for scenario in sorted(KNOWN_SCENARIOS):
        for suffix in ("state", "report"):
            path = GENERATED / f"{scenario}-{suffix}.json"
            _assert_generated_file(path)
            if path.exists():
                path.unlink()
                try:
                    removed.append(str(path.relative_to(ROOT)))
                except ValueError:
                    removed.append(str(path))
    return removed


def _assert_generated_file(path: Path) -> None:
    resolved = path.resolve()
    generated = GENERATED.resolve()
    if resolved.parent != generated or resolved.suffix != ".json":
        raise ValueError("refusing to modify a path outside the demo's generated JSON files")
