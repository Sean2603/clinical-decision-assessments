#!/usr/bin/env python3
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
ASSESSMENTS_DIRECTORY = ROOT / "assessments"
REFERENCES_PATH = ROOT / "references" / "references.json"
SCHEMA_PATH = ROOT / "schema" / "assessment-schema.json"

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
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def bump_patch(value: str) -> str:
    major, minor, patch = semver_parts(value)
    return f"{major}.{minor}.{patch + 1}"


def max_version(values: list[str]) -> str:
    if not values:
        raise SystemExit("No assessment versions were found.")
    return max(values, key=semver_parts)


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    references = load_json(REFERENCES_PATH)
    schema = load_json(SCHEMA_PATH)

    if not isinstance(references.get("references"), list):
        raise SystemExit(
            "references/references.json must contain a references array."
        )

    if not isinstance(schema, dict):
        raise SystemExit("schema/assessment-schema.json must be an object.")

    existing_entries = {
        entry.get("id"): entry
        for entry in manifest.get("assessments", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }

    generated_entries: list[dict] = []
    assessment_versions: list[str] = []

    assessment_paths = sorted(ASSESSMENTS_DIRECTORY.glob("*.json"))
    if not assessment_paths:
        raise SystemExit("No assessment JSON files were found.")

    for assessment_path in assessment_paths:
        assessment = load_json(assessment_path)

        assessment_id = assessment.get("id")
        title = assessment.get("title")
        version = assessment.get("version")

        if not isinstance(assessment_id, str) or not assessment_id:
            raise SystemExit(f"{assessment_path} has no valid id.")
        if not isinstance(title, str) or not title:
            raise SystemExit(f"{assessment_path} has no valid title.")
        if not isinstance(version, str):
            raise SystemExit(f"{assessment_path} has no valid version.")

        semver_parts(version)
        assessment_versions.append(version)

        relative_assessment_path = assessment_path.relative_to(ROOT).as_posix()
        previous_entry = existing_entries.get(assessment_id, {})

        generated_entries.append(
            {
                "id": assessment_id,
                "title": title,
                "version": version,
                "file": relative_assessment_path,
                "schema": "schema/assessment-schema.json",
                "sha256": sha256(assessment_path),
                "schemaSha256": sha256(SCHEMA_PATH),
                **{
                    key: value
                    for key, value in previous_entry.items()
                    if key
                    not in {
                        "id",
                        "title",
                        "version",
                        "file",
                        "schema",
                        "sha256",
                        "schemaSha256",
                    }
                },
            }
        )

    highest_assessment_version = max_version(assessment_versions)
    previous_content_version = manifest.get("contentVersion", "0.0.0")
    semver_parts(previous_content_version)

    previous_manifest_without_generated = {
        key: value
        for key, value in manifest.items()
        if key not in {"updatedAt", "references", "assessments"}
    }

    generated_manifest_core = {
        **previous_manifest_without_generated,
        "contentVersion": highest_assessment_version,
        "minimumAppVersion": manifest.get("minimumAppVersion", "0.11.0"),
        "references": {
            "file": "references/references.json",
            "sha256": sha256(REFERENCES_PATH),
        },
        "assessments": generated_entries,
    }

    # If only references/schema changed and no assessment version increased,
    # ensure the pack version still advances.
    previous_core = {
        key: value
        for key, value in manifest.items()
        if key != "updatedAt"
    }

    if generated_manifest_core != previous_core:
        if semver_parts(highest_assessment_version) <= semver_parts(
            previous_content_version
        ):
            generated_manifest_core["contentVersion"] = bump_patch(
                previous_content_version
            )

    generated_manifest = {
        "schemaVersion": manifest.get("schemaVersion", 1),
        "contentVersion": generated_manifest_core["contentVersion"],
        "updatedAt": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "minimumAppVersion": generated_manifest_core["minimumAppVersion"],
        "references": generated_manifest_core["references"],
        "assessments": generated_manifest_core["assessments"],
    }

    write_json(MANIFEST_PATH, generated_manifest)

    print(
        "manifest.json synchronised: "
        f"contentVersion={generated_manifest['contentVersion']}"
    )


if __name__ == "__main__":
    main()
