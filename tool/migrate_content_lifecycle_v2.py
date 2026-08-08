#!/usr/bin/env python3
"""One-off coordinated migration for lifecycle status and unitless blood rows.

- Adds explicit assessment lifecycle status to the assessment schema and files.
- Adds optional `unitless` boolean support to blood-panel rows.
- Converts legacy unit="unitless" rows to unit="" + unitless=true.
- Removes assessment emergency revocations that duplicate a normal withdrawn status.
- Raises manifest minimumAppVersion to 0.32.0 because older apps do not hide
  withdrawn assessments by explicit lifecycle status.

The script preserves unrelated schema/content fields and writes LF line endings.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = ROOT / "assessments"
BLOOD_PANELS = ROOT / "blood_panels"
ASSESSMENT_SCHEMA = ROOT / "schema" / "assessment-schema.json"
BLOOD_SCHEMA = ROOT / "schema" / "blood-panel-schema.json"
MANIFEST = ROOT / "manifest.json"
WITHDRAWAL_PREFIX = "withdrawn from clinical use:"
MIN_APP = "0.32.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def version_tuple(value: str) -> tuple[int, int, int]:
    try:
        parts = tuple(int(part) for part in value.split("."))
    except ValueError:
        return (0, 0, 0)
    return parts if len(parts) == 3 else (0, 0, 0)


def migrate_assessment_schema() -> bool:
    data = load(ASSESSMENT_SCHEMA)
    changed = False
    required = data.setdefault("required", [])
    if "status" not in required:
        # Keep status close to summary/version metadata where possible.
        insert_at = required.index("clinicalValidation") if "clinicalValidation" in required else len(required)
        required.insert(insert_at, "status")
        changed = True
    props = data.setdefault("properties", {})
    desired = {"type": "string", "enum": ["active", "withdrawn", "superseded"]}
    if props.get("status") != desired:
        props["status"] = desired
        changed = True
    if changed:
        save(ASSESSMENT_SCHEMA, data)
    return changed


def migrate_blood_schema() -> bool:
    data = load(BLOOD_SCHEMA)
    row = data.setdefault("$defs", {}).setdefault("row", {})
    props = row.setdefault("properties", {})
    desired = {"type": "boolean"}
    if props.get("unitless") == desired:
        return False
    props["unitless"] = desired
    save(BLOOD_SCHEMA, data)
    return True


def migrate_assessments() -> tuple[int, set[str]]:
    changed_count = 0
    withdrawn_ids: set[str] = set()
    for path in sorted(ASSESSMENTS.glob("*.json")):
        data = load(path)
        validation = data.get("clinicalValidation") or {}
        notes = str(validation.get("reviewNotes") or "").strip().lower()
        existing = str(data.get("status") or "").strip().lower()
        desired = existing if existing in {"active", "withdrawn", "superseded"} else (
            "withdrawn" if notes.startswith(WITHDRAWAL_PREFIX) else "active"
        )
        if data.get("status") != desired:
            data["status"] = desired
            save(path, data)
            changed_count += 1
        if desired == "withdrawn" and isinstance(data.get("id"), str):
            withdrawn_ids.add(data["id"])
    return changed_count, withdrawn_ids


def migrate_blood_rows() -> int:
    changed_files = 0
    for path in sorted(BLOOD_PANELS.glob("*.json")):
        data = load(path)
        changed = False
        for section in data.get("sections") or []:
            if not isinstance(section, dict):
                continue
            for row in section.get("rows") or []:
                if not isinstance(row, dict):
                    continue
                unit = row.get("unit")
                if isinstance(unit, str) and unit.strip().lower() == "unitless":
                    row["unit"] = ""
                    row["unitless"] = True
                    changed = True
        if changed:
            save(path, data)
            changed_files += 1
    return changed_files


def migrate_manifest(withdrawn_ids: set[str]) -> bool:
    if not MANIFEST.exists():
        return False
    data = load(MANIFEST)
    changed = False
    revocations = data.get("emergencyRevocations") or []
    kept = [
        entry for entry in revocations
        if not (
            isinstance(entry, dict)
            and entry.get("contentType") == "assessment"
            and entry.get("contentId") in withdrawn_ids
        )
    ]
    if kept != revocations:
        data["emergencyRevocations"] = kept
        changed = True
    current_min = str(data.get("minimumAppVersion") or "0.0.0")
    if version_tuple(current_min) < version_tuple(MIN_APP):
        data["minimumAppVersion"] = MIN_APP
        changed = True
    if changed:
        save(MANIFEST, data)
    return changed


def main() -> int:
    assessment_schema_changed = migrate_assessment_schema()
    blood_schema_changed = migrate_blood_schema()
    assessment_files, withdrawn_ids = migrate_assessments()
    blood_files = migrate_blood_rows()
    manifest_changed = migrate_manifest(withdrawn_ids)
    print(
        "Lifecycle/unitless migration complete: "
        f"assessmentSchema={assessment_schema_changed}, "
        f"bloodSchema={blood_schema_changed}, "
        f"assessmentFiles={assessment_files}, "
        f"withdrawnAssessments={len(withdrawn_ids)}, "
        f"bloodFiles={blood_files}, "
        f"manifestChanged={manifest_changed}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
