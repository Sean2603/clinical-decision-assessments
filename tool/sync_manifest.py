#!/usr/bin/env python3
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
REFERENCES_PATH = ROOT / "references" / "references.json"
RELIABILITY_PATH = ROOT / "clinical_reliability" / "clinical-reliability.json"

COLLECTIONS = {
    "assessments": {
        "directory": ROOT / "assessments",
        "schema": ROOT / "schema" / "assessment-schema.json",
        "versionField": "version",
    },
    "guidelines": {
        "directory": ROOT / "guidelines",
        "schema": ROOT / "schema" / "guideline-schema.json",
        "versionField": "contentVersion",
    },
    "scoringTools": {
        "directory": ROOT / "scoring_tools",
        "schema": ROOT / "schema" / "scoring-tool-schema.json",
        "versionField": "version",
    },
    "bloodPanels": {
        "directory": ROOT / "blood_panels",
        "schema": ROOT / "schema" / "blood-panel-schema.json",
        "versionField": "version",
    },
}

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
    schema_path: Path,
    version_field: str,
    existing_entries: dict[str, dict],
) -> list[dict]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise SystemExit(f"No JSON files found in {directory.relative_to(ROOT)}.")

    entries: list[dict] = []
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
                    "sha256", "schemaSha256",
                }
            },
        })
    return entries


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    load_json(REFERENCES_PATH)
    load_json(RELIABILITY_PATH)

    generated_collections: dict[str, list[dict]] = {}
    for key, settings in COLLECTIONS.items():
        schema_path = settings["schema"]
        load_json(schema_path)
        existing = {
            entry.get("id"): entry
            for entry in manifest.get(key, [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        generated_collections[key] = build_entries(
            settings["directory"],
            schema_path,
            settings["versionField"],
            existing,
        )

    previous_version = manifest.get("contentVersion", "0.0.0")
    semver_parts(previous_version)

    generated_core = {
        "schemaVersion": 3,
        "contentVersion": previous_version,
        "minimumAppVersion": "0.18.0",
        "references": {
            "file": "references/references.json",
            "sha256": sha256(REFERENCES_PATH),
        },
        "clinicalReliability": {
            "file": "clinical_reliability/clinical-reliability.json",
            "schema": "schema/clinical-reliability-schema.json",
            "sha256": sha256(RELIABILITY_PATH),
            "schemaSha256": sha256(
                ROOT / "schema" / "clinical-reliability-schema.json"
            ),
        },
        **generated_collections,
    }

    previous_core = {
        key: value for key, value in manifest.items() if key != "updatedAt"
    }
    if generated_core != previous_core:
        generated_core["contentVersion"] = bump_patch(previous_version)

    generated = {
        "schemaVersion": generated_core["schemaVersion"],
        "contentVersion": generated_core["contentVersion"],
        "updatedAt": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "minimumAppVersion": generated_core["minimumAppVersion"],
        "references": generated_core["references"],
        "clinicalReliability": generated_core["clinicalReliability"],
        "assessments": generated_core["assessments"],
        "guidelines": generated_core["guidelines"],
        "scoringTools": generated_core["scoringTools"],
        "bloodPanels": generated_core["bloodPanels"],
    }
    write_json(MANIFEST_PATH, generated)
    print(
        "manifest.json synchronised: "
        f"contentVersion={generated['contentVersion']}, "
        f"assessments={len(generated['assessments'])}, "
        f"guidelines={len(generated['guidelines'])}, "
        f"scoringTools={len(generated['scoringTools'])}, "
        f"bloodPanels={len(generated['bloodPanels'])}"
    )


if __name__ == "__main__":
    main()
