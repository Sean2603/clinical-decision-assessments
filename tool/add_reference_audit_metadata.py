#!/usr/bin/env python3
"""Add audit metadata to every existing reference without replacing content."""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "references" / "references.json"

DEFAULTS = {
    "lastUpdated": None,
    "lastReviewed": None,
    "reviewStatus": "unverified",
    "reviewedBy": None,
    "reviewerRole": None,
    "nextReviewDue": None,
    "supersededBy": None,
    "notes": None,
}


def main() -> None:
    document = json.loads(PATH.read_text(encoding="utf-8"))
    references = document.get("references", [])

    changed = 0
    for reference in references:
        was_changed = False
        for key, value in DEFAULTS.items():
            if key not in reference:
                reference[key] = value
                was_changed = True
        if was_changed:
            changed += 1

    document["schemaVersion"] = max(int(document.get("schemaVersion", 1)), 2)
    document["lastChecked"] = date.today().isoformat()

    PATH.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Added audit metadata to {changed} reference(s).")
    print("Migrated references remain unverified until manually audited.")


if __name__ == "__main__":
    main()
