#!/usr/bin/env python3
"""Mark publishable content as clinically unvalidated when it cites review-due references.

This deliberately does not restore validation automatically when references later become
current. A clinician must explicitly review and revalidate the affected content.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCES_PATH = ROOT / "references" / "references.json"
CONTENT_FOLDERS = ("assessments", "scoring_tools", "blood_panels", "prescribing")
NOTE_PREFIX = "Clinical validation required: cited reference review is due"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def collect_reference_ids(value):
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"references", "referenceIds"} and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            else:
                found.update(collect_reference_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_reference_ids(child))
    return found


def bump_patch(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    registry = load_json(REFERENCES_PATH)
    review_due = {
        reference["id"]
        for reference in registry.get("references", [])
        if reference.get("reviewStatus") == "review-due"
    }

    changed_paths = []
    for folder in CONTENT_FOLDERS:
        for path in sorted((ROOT / folder).glob("*.json")):
            document = load_json(path)
            affected = sorted(collect_reference_ids(document) & review_due)
            if not affected:
                continue

            validation = document.get("clinicalValidation")
            if not isinstance(validation, dict):
                raise SystemExit(
                    f"{path.relative_to(ROOT)} has no clinicalValidation object."
                )

            note = f"{NOTE_PREFIX}: {', '.join(affected)}."
            changed = False

            if validation.get("validated") is not False:
                validation["validated"] = False
                changed = True

            for field in ("reviewedBy", "reviewedOn", "reviewerRole"):
                if validation.get(field) is not None:
                    validation[field] = None
                    changed = True

            existing_note = validation.get("reviewNotes")
            if existing_note != note:
                validation["reviewNotes"] = note
                changed = True

            if changed:
                old_version = document.get("version")
                if not isinstance(old_version, str):
                    raise SystemExit(
                        f"{path.relative_to(ROOT)} has no valid version to bump."
                    )
                document["version"] = bump_patch(old_version)
                write_json(path, document)
                changed_paths.append(path.relative_to(ROOT))
                print(
                    f"Marked {path.relative_to(ROOT)} as requiring clinical "
                    f"validation ({old_version} -> {document['version']})."
                )

    if not changed_paths:
        print("No content changes required for review-due references.")
    else:
        print(f"Updated {len(changed_paths)} content file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
