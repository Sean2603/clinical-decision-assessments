#!/usr/bin/env python3
"""Restore missing remote-engine parityCases without changing clinical rules."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = Path(__file__).resolve().with_name("parity_case_baseline.json")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def write_object(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    baseline = load_object(BASELINE_PATH)
    scoring_baseline = baseline.get("scoringTools", {})
    blood_baseline = baseline.get("bloodCalculations", {})

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path(tempfile.gettempdir()) / f"cdm-parity-repair-{timestamp}"
    changed: list[Path] = []
    unresolved: list[str] = []

    for path in sorted((ROOT / "scoring_tools").glob("*.json")):
        definition = load_object(path)
        tool_id = definition.get("id")
        if not isinstance(tool_id, str):
            unresolved.append(f"{path}: missing string id")
            continue

        if "parityCases" not in definition:
            if tool_id not in scoring_baseline:
                unresolved.append(
                    f"{path}: no known-good parity baseline for {tool_id!r}"
                )
                continue
            backup = backup_root / path.relative_to(ROOT)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
            definition["parityCases"] = scoring_baseline[tool_id]
            write_object(path, definition)
            changed.append(path)

    for path in sorted((ROOT / "blood_panels").glob("*.json")):
        definition = load_object(path)
        panel_id = definition.get("id")
        if not isinstance(panel_id, str):
            unresolved.append(f"{path}: missing string id")
            continue

        panel_baseline = blood_baseline.get(panel_id, {})
        calculations = definition.get("calculations", [])
        if not isinstance(calculations, list):
            unresolved.append(f"{path}: calculations must be an array")
            continue

        file_changed = False
        for calculation in calculations:
            if not isinstance(calculation, dict):
                unresolved.append(f"{path}: invalid calculation entry")
                continue
            calculation_id = calculation.get("id")
            if not isinstance(calculation_id, str):
                unresolved.append(f"{path}: calculation missing string id")
                continue
            if "parityCases" not in calculation:
                if calculation_id not in panel_baseline:
                    unresolved.append(
                        f"{path}: no known-good parity baseline for "
                        f"{panel_id}/{calculation_id}"
                    )
                    continue
                if not file_changed:
                    backup = backup_root / path.relative_to(ROOT)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, backup)
                calculation["parityCases"] = panel_baseline[calculation_id]
                file_changed = True

        if file_changed:
            write_object(path, definition)
            changed.append(path)

    if changed:
        print("Restored missing parity cases in:")
        for path in changed:
            print(f"- {path.relative_to(ROOT)}")
        print(f"Backups stored outside the repository at: {backup_root}")
    else:
        print("No missing parityCases fields required repair.")

    if unresolved:
        print("\nUnresolved items:")
        for item in unresolved:
            print(f"- {item}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
