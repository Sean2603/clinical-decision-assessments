#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
REFERENCES_PATH = ROOT / "references" / "references.json"
CATEGORIES_PATH = ROOT / "categories" / "assessment-categories.json"
CATEGORIES_SCHEMA_PATH = ROOT / "schema" / "assessment-categories-schema.json"

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


def render_json(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write_json_if_changed(path: Path, value: dict) -> bool:
    rendered = render_json(value)
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == rendered:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semver_parts(value: str) -> tuple[int, int, int]:
    if not SEMVER_PATTERN.fullmatch(value):
        raise SystemExit(f"Invalid semantic version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def bump_patch(value: str) -> str:
    major, minor, patch = semver_parts(value)
    return f"{major}.{minor}.{patch + 1}"


def canonical_revocations(value: object) -> object:
    if not isinstance(value, list):
        return value

    def key(entry: object) -> tuple[str, str, str, str, str, str]:
        if not isinstance(entry, dict):
            return ("", "", "", "", "", json.dumps(entry, sort_keys=True))
        affected = entry.get("affectedVersions")
        affected = affected if isinstance(affected, dict) else {}
        return (
            str(entry.get("contentType", "")),
            str(entry.get("contentId", "")),
            str(entry.get("action", "")),
            str(affected.get("minimum", "")),
            str(affected.get("maximum", "")),
            str(entry.get("reason", "")),
        )

    return sorted(value, key=key)


def build_entries(
    directory: Path,
    schema_path: Path,
    version_field: str,
    existing_entries: dict[str, dict],
) -> list[dict]:
    paths = sorted(directory.glob("*.json"), key=lambda item: item.name.casefold())
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
        generated_metadata = {}
        if directory.name == "assessments":
            generated_metadata["categoryIds"] = item.get("categoryIds", ["uncategorised"])
        entries.append({
            "id": item_id,
            "title": title,
            "version": version,
            "file": item_path.relative_to(ROOT).as_posix(),
            "schema": schema_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(item_path),
            "schemaSha256": sha256(schema_path),
            **generated_metadata,
            **{
                key: value
                for key, value in previous.items()
                if key not in {
                    "id", "title", "version", "file", "schema",
                    "sha256", "schemaSha256", "categoryIds",
                }
            },
        })
    return entries


def build_manifest(current: dict) -> tuple[dict, bool]:
    load_json(REFERENCES_PATH)
    categories = load_json(CATEGORIES_PATH)
    load_json(CATEGORIES_SCHEMA_PATH)

    generated_collections: dict[str, list[dict]] = {}
    for key, settings in COLLECTIONS.items():
        schema_path = settings["schema"]
        load_json(schema_path)
        existing = {
            entry.get("id"): entry
            for entry in current.get(key, [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        generated_collections[key] = build_entries(
            settings["directory"],
            schema_path,
            settings["versionField"],
            existing,
        )

    previous_version = current.get("contentVersion", "0.0.0")
    semver_parts(previous_version)

    generated_keys = {
        "schemaVersion", "contentVersion", "minimumAppVersion", "references",
        "assessmentCategories", "assessments", "guidelines", "scoringTools",
        "bloodPanels",
    }
    preserved = {
        key: value
        for key, value in current.items()
        if key not in generated_keys and key != "updatedAt"
    }
    if "emergencyRevocations" in preserved:
        preserved["emergencyRevocations"] = canonical_revocations(
            preserved["emergencyRevocations"]
        )

    candidate = {
        **preserved,
        "schemaVersion": 3,
        "contentVersion": previous_version,
        "minimumAppVersion": "0.31.0",
        "references": {
            "file": "references/references.json",
            "sha256": sha256(REFERENCES_PATH),
        },
        "assessmentCategories": {
            "file": "categories/assessment-categories.json",
            "schema": "schema/assessment-categories-schema.json",
            "sha256": sha256(CATEGORIES_PATH),
            "schemaSha256": sha256(CATEGORIES_SCHEMA_PATH),
            "items": categories["categories"],
        },
        "assessments": generated_collections["assessments"],
        "guidelines": generated_collections["guidelines"],
        "scoringTools": generated_collections["scoringTools"],
        "bloodPanels": generated_collections["bloodPanels"],
    }

    current_semantic = {
        key: value
        for key, value in current.items()
        if key not in {"contentVersion", "updatedAt"}
    }
    candidate_semantic = {
        key: value
        for key, value in candidate.items()
        if key != "contentVersion"
    }
    semantic_changed = candidate_semantic != current_semantic

    if semantic_changed:
        candidate["contentVersion"] = bump_patch(previous_version)
        updated_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    else:
        updated_at = current.get("updatedAt")
        if not isinstance(updated_at, str) or not updated_at:
            updated_at = (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

    generated = {
        "schemaVersion": candidate["schemaVersion"],
        "contentVersion": candidate["contentVersion"],
        "updatedAt": updated_at,
        **{
            key: value
            for key, value in candidate.items()
            if key not in {"schemaVersion", "contentVersion"}
        },
    }
    return generated, semantic_changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically generate or verify manifest.json."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="Write manifest.json. Intended for the CDM Content Manager batch publisher.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify manifest.json is already synchronised without writing it.",
    )
    args = parser.parse_args()

    current = load_json(MANIFEST_PATH)
    generated, semantic_changed = build_manifest(current)
    expected = render_json(generated)
    actual = MANIFEST_PATH.read_text(encoding="utf-8")

    # Default to read-only verification. A write must be explicitly requested.
    if not args.write:
        if actual != expected:
            raise SystemExit(
                "manifest.json is not synchronised. Publish through the CDM Content "
                "Manager so the manifest is generated once in the controlled batch."
            )
        print(
            "manifest.json verified: deterministic and synchronised; "
            f"contentVersion={generated['contentVersion']}"
        )
        return

    changed = write_json_if_changed(MANIFEST_PATH, generated)
    print(
        "manifest.json synchronised by controlled writer: "
        f"contentVersion={generated['contentVersion']}, "
        f"semanticChanged={str(semantic_changed).lower()}, "
        f"fileChanged={str(changed).lower()}, "
        f"assessments={len(generated['assessments'])}, "
        f"guidelines={len(generated['guidelines'])}, "
        f"scoringTools={len(generated['scoringTools'])}, "
        f"bloodPanels={len(generated['bloodPanels'])}"
    )


if __name__ == "__main__":
    main()
