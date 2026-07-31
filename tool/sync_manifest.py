#!/usr/bin/env python3
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
ASSESSMENTS_DIRECTORY = ROOT / "assessments"
GUIDELINES_DIRECTORY = ROOT / "guidelines"
REFERENCES_PATH = ROOT / "references" / "references.json"
ASSESSMENT_SCHEMA_PATH = ROOT / "schema" / "assessment-schema.json"
GUIDELINE_SCHEMA_PATH = ROOT / "schema" / "guideline-schema.json"
RELIABILITY_PATH = ROOT / "clinical_reliability" / "clinical-reliability.json"
RELIABILITY_SCHEMA_PATH = ROOT / "schema" / "clinical-reliability-schema.json"

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semver_parts(value: str) -> tuple[int, int, int]:
    if not SEMVER_PATTERN.fullmatch(value):
        raise SystemExit(f"Invalid semantic version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def bump_patch(value: str) -> str:
    major, minor, patch = semver_parts(value)
    return f"{major}.{minor}.{patch + 1}"


def build_entries(
    directory: Path,
    existing_entries: dict[str, dict],
    schema_path: Path,
    version_field: str,
) -> tuple[list[dict], list[str]]:
    entries = []
    versions = []
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise SystemExit(f"No JSON files found in {directory.relative_to(ROOT)}.")

    for item_path in paths:
        item = load_json(item_path)
        item_id = item.get("id")
        title = item.get("title")
        version = item.get(version_field)
        if not isinstance(item_id, str) or not item_id:
            raise SystemExit(f"{item_path} has no valid id.")
        if not isinstance(title, str) or not title:
            raise SystemExit(f"{item_path} has no valid title.")
        if not isinstance(version, str):
            raise SystemExit(f"{item_path} has no valid {version_field}.")
        semver_parts(version)
        versions.append(version)
        previous = existing_entries.get(item_id, {})
        entries.append({
            "id": item_id,
            "title": title,
            "version": version,
            "file": item_path.relative_to(ROOT).as_posix(),
            "schema": schema_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(item_path),
            "schemaSha256": sha256(schema_path),
            **{
                key: value
                for key, value in previous.items()
                if key not in {
                    "id", "title", "version", "file", "schema",
                    "sha256", "schemaSha256"
                }
            },
        })
    return entries, versions


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    load_json(REFERENCES_PATH)
    load_json(ASSESSMENT_SCHEMA_PATH)
    load_json(GUIDELINE_SCHEMA_PATH)
    load_json(RELIABILITY_PATH)
    load_json(RELIABILITY_SCHEMA_PATH)

    existing_assessments = {
        entry.get("id"): entry
        for entry in manifest.get("assessments", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    existing_guidelines = {
        entry.get("id"): entry
        for entry in manifest.get("guidelines", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }

    assessments, assessment_versions = build_entries(
        ASSESSMENTS_DIRECTORY,
        existing_assessments,
        ASSESSMENT_SCHEMA_PATH,
        "version",
    )
    guidelines, guideline_versions = build_entries(
        GUIDELINES_DIRECTORY,
        existing_guidelines,
        GUIDELINE_SCHEMA_PATH,
        "contentVersion",
    )

    previous_version = manifest.get("contentVersion", "0.0.0")
    semver_parts(previous_version)
    highest_item_version = max(
        assessment_versions + guideline_versions,
        key=semver_parts,
    )

    generated_core = {
        "schemaVersion": manifest.get("schemaVersion", 1),
        "contentVersion": highest_item_version,
        "minimumAppVersion": "0.17.0",
        "references": {
            "file": "references/references.json",
            "sha256": sha256(REFERENCES_PATH),
        },
        "clinicalReliability": {
            "file": "clinical_reliability/clinical-reliability.json",
            "schema": "schema/clinical-reliability-schema.json",
            "sha256": sha256(RELIABILITY_PATH),
            "schemaSha256": sha256(RELIABILITY_SCHEMA_PATH),
        },
        "assessments": assessments,
        "guidelines": guidelines,
    }

    previous_core = {
        key: value for key, value in manifest.items() if key != "updatedAt"
    }
    if generated_core != previous_core:
        if semver_parts(highest_item_version) <= semver_parts(previous_version):
            generated_core["contentVersion"] = bump_patch(previous_version)

    generated = {
        **generated_core,
        "updatedAt": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    # Preserve stable key order.
    generated = {
        "schemaVersion": generated["schemaVersion"],
        "contentVersion": generated["contentVersion"],
        "updatedAt": generated["updatedAt"],
        "minimumAppVersion": generated["minimumAppVersion"],
        "references": generated["references"],
        "clinicalReliability": generated["clinicalReliability"],
        "assessments": generated["assessments"],
        "guidelines": generated["guidelines"],
    }
    write_json(MANIFEST_PATH, generated)
    print(
        "manifest.json synchronised: "
        f"contentVersion={generated['contentVersion']}, "
        f"assessments={len(assessments)}, guidelines={len(guidelines)}"
    )


if __name__ == "__main__":
    main()
