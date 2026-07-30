#!/usr/bin/env python3
"""Add clinicalValidation metadata to the schema and all assessments.

Run from the root of clinical-decision-assessments:
    python tool/add_clinical_validation.py

This script does not alter manifest.json. The publishing workflow will rebuild it.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "assessment-schema.json"
ASSESSMENTS_DIR = ROOT / "assessments"


VALIDATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["validated"],
    "properties": {
        "validated": {"type": "boolean"},
        "reviewedBy": {
            "type": ["string", "null"],
            "minLength": 1,
        },
        "reviewedOn": {
            "type": ["string", "null"],
            "format": "date",
        },
        "reviewerRole": {
            "type": ["string", "null"],
            "minLength": 1,
        },
        "reviewNotes": {
            "type": ["string", "null"],
            "minLength": 1,
        },
    },
}


DEFAULT_VALIDATION = {
    "validated": False,
    "reviewedBy": None,
    "reviewedOn": None,
    "reviewerRole": None,
    "reviewNotes": None,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def bump_patch(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def update_schema() -> None:
    schema = load_json(SCHEMA_PATH)

    properties = schema.setdefault("properties", {})
    properties["clinicalValidation"] = VALIDATION_SCHEMA

    required = schema.setdefault("required", [])
    if "clinicalValidation" not in required:
        insert_at = required.index("sections") if "sections" in required else len(required)
        required.insert(insert_at, "clinicalValidation")

    write_json(SCHEMA_PATH, schema)
    print(f"Updated {SCHEMA_PATH.relative_to(ROOT)}")


def update_assessments() -> None:
    assessment_paths = sorted(ASSESSMENTS_DIR.glob("*.json"))

    if not assessment_paths:
        raise SystemExit("No assessments/*.json files were found.")

    for path in assessment_paths:
        assessment = load_json(path)
        existing = assessment.get("clinicalValidation")

        if isinstance(existing, dict):
            merged = {**DEFAULT_VALIDATION, **existing}
            merged["validated"] = existing.get("validated") is True
            assessment["clinicalValidation"] = merged
            changed = merged != existing
        else:
            assessment["clinicalValidation"] = dict(DEFAULT_VALIDATION)
            changed = True

        if changed:
            old_version = assessment["version"]
            assessment["version"] = bump_patch(old_version)
            write_json(path, assessment)
            print(
                f"Updated {path.relative_to(ROOT)} "
                f"({old_version} -> {assessment['version']})"
            )
        else:
            print(f"No change required: {path.relative_to(ROOT)}")


def main() -> None:
    update_schema()
    update_assessments()
    print(
        "\nDone. Commit the schema and assessment changes. "
        "The assessment workflow will regenerate manifest.json."
    )


if __name__ == "__main__":
    main()
