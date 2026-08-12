#!/usr/bin/env python3
"""One-off migration for legacy Medication/Prescribing metadata.

Run from the root of clinical-decision-assessments:
    python tool/migrate_legacy_prescribing_metadata.py

The script only adds missing metadata fields. It does not rewrite existing
clinical wording, doses, cautions, references, validation data, or other fields.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "medications/co-codamol.json": {
        "aliases": [],
        "updatedOn": None,
        "changeSummary": "Legacy medication metadata normalised for the current schema.",
        "effectiveFrom": None,
    },
    "prescribing/lower-uti-in-pregnancy-asymptomatic.json": {
        "aliases": ["UTI", "lower UTI"],
        "system": "Genitourinary",
        "updatedOn": None,
        "changeSummary": "Legacy prescribing pathway metadata normalised for the current schema.",
        "effectiveFrom": None,
    },
    "prescribing/lower-uti-non-pregnant-women-16-and-over.json": {
        "aliases": ["UTI", "lower UTI"],
        "system": "Genitourinary",
        "updatedOn": None,
        "changeSummary": "Legacy prescribing pathway metadata normalised for the current schema.",
        "effectiveFrom": None,
    },
    "prescribing/lower-uti-pregnancy-asymptomatic.json": {
        "aliases": ["UTI", "lower UTI"],
        "system": "Genitourinary",
        "updatedOn": None,
        "changeSummary": "Legacy prescribing pathway metadata normalised for the current schema.",
        "effectiveFrom": None,
    },
}


def main() -> int:
    changed = 0
    found = 0

    for relative_path, defaults in TARGETS.items():
        path = ROOT / relative_path
        if not path.exists():
            continue

        found += 1
        document = json.loads(path.read_text(encoding="utf-8"))
        added: list[str] = []

        for key, value in defaults.items():
            if key not in document:
                document[key] = value
                added.append(key)

        if added:
            path.write_text(
                json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            changed += 1
            print(f"Updated {relative_path}: added {', '.join(added)}")
        else:
            print(f"No change {relative_path}: metadata already present")

    if found == 0:
        print("No target legacy files were found.")
        return 1

    print(f"\nCompleted: {changed} file(s) changed.")
    print("Next run:")
    print("  python tool/validate_content.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
