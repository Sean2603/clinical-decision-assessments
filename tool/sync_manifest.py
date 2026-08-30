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
GLOSSARY_PATH = ROOT / "glossary" / "glossary.json"
CATEGORIES_PATH = ROOT / "categories" / "assessment-categories.json"
CATEGORIES_SCHEMA_PATH = ROOT / "schema" / "assessment-categories-schema.json"

COLLECTIONS = {
    "assessments": {"directory": ROOT / "assessments", "schema": ROOT / "schema" / "assessment-schema.json", "versionField": "version", "allowEmpty": True},
    "guidelines": {"directory": ROOT / "guidelines", "schema": ROOT / "schema" / "guideline-schema.json", "versionField": "contentVersion", "allowEmpty": True},
    "scoringTools": {"directory": ROOT / "scoring_tools", "schema": ROOT / "schema" / "scoring-tool-schema.json", "versionField": "version", "allowEmpty": True},
    "bloodPanels": {"directory": ROOT / "blood_panels", "schema": ROOT / "schema" / "blood-panel-schema.json", "versionField": "version", "allowEmpty": True},
    "medications": {"directory": ROOT / "medications", "schema": ROOT / "schema" / "medication-schema.json", "versionField": "version", "allowEmpty": True},
    "prescribing": {"directory": ROOT / "prescribing", "schema": ROOT / "schema" / "prescribing-schema.json", "versionField": "version", "allowEmpty": True},
    "sharedLearning": {"directory": ROOT / "shared_learning", "schema": ROOT / "schema" / "shared-learning-schema.json", "versionField": "version", "allowEmpty": True},
}
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
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


def canonical_text_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(canonical_text_bytes(path)).hexdigest()


def text_size_bytes(path: Path) -> int:
    return len(canonical_text_bytes(path))


def download_size_bytes(path: Path) -> int:
    if path.suffix.lower() in {".json", ".md", ".txt", ".csv"}:
        return text_size_bytes(path)
    return path.stat().st_size


def attachment_paths(document: dict) -> list[Path]:
    paths: list[Path] = []
    attachments = document.get("attachments", [])
    if not isinstance(attachments, list):
        return paths
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        relative = attachment.get("path")
        if not isinstance(relative, str) or not relative:
            continue
        path = ROOT / relative
        if not path.exists() or not path.is_file():
            raise SystemExit(f"Manifest size generation cannot find attachment: {relative}")
        paths.append(path)
    return paths


def semver_parts(value: str) -> tuple[int, int, int]:
    if not SEMVER_PATTERN.fullmatch(value):
        raise SystemExit(f"Invalid semantic version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def bump_patch(value: str) -> str:
    major, minor, patch = semver_parts(value)
    return f"{major}.{minor}.{patch + 1}"


def max_semver(*values: str) -> str:
    for value in values:
        semver_parts(value)
    return max(values, key=semver_parts)


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
    allow_empty: bool = False,
) -> list[dict]:
    paths = sorted(directory.glob("*.json"), key=lambda item: item.name.casefold())
    if not paths:
        if allow_empty:
            return []
        raise SystemExit(f"No JSON files found in {directory.relative_to(ROOT)}.")

    entries = []
    schema_size = text_size_bytes(schema_path)
    for item_path in paths:
        item = load_json(item_path)
        item_id, title, version = item.get("id"), item.get("title"), item.get(version_field)
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

        item_attachments = attachment_paths(item)
        entries.append({
            "id": item_id,
            "title": title,
            "version": version,
            "file": item_path.relative_to(ROOT).as_posix(),
            "schema": schema_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(item_path),
            "schemaSha256": sha256(schema_path),
            "sizeBytes": text_size_bytes(item_path),
            "schemaSizeBytes": schema_size,
            "attachmentsSizeBytes": sum(download_size_bytes(path) for path in item_attachments),
            **generated_metadata,
            **{
                k: v
                for k, v in previous.items()
                if k not in {
                    "id", "title", "version", "file", "schema", "sha256",
                    "schemaSha256", "sizeBytes", "schemaSizeBytes",
                    "attachmentsSizeBytes", "categoryIds",
                }
            },
        })
    return entries


def payload_paths(generated_collections: dict[str, list[dict]]) -> set[Path]:
    paths: set[Path] = {REFERENCES_PATH, GLOSSARY_PATH}
    for entries in generated_collections.values():
        for entry in entries:
            paths.add(ROOT / entry["file"])
            paths.add(ROOT / entry["schema"])
            document = load_json(ROOT / entry["file"])
            paths.update(attachment_paths(document))
    return paths


def build_manifest(current: dict) -> tuple[dict, bool]:
    load_json(REFERENCES_PATH)
    load_json(GLOSSARY_PATH)
    categories = load_json(CATEGORIES_PATH)
    load_json(CATEGORIES_SCHEMA_PATH)

    generated_collections = {}
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
            bool(settings.get("allowEmpty", False)),
        )

    previous_version = current.get("contentVersion", "0.0.0")
    semver_parts(previous_version)

    generated_keys = {
        "schemaVersion", "contentVersion", "minimumAppVersion", "downloadSizeBytes",
        "references", "glossary", "assessmentCategories", "assessments", "guidelines",
        "scoringTools", "bloodPanels", "medications", "prescribing", "sharedLearning",
    }
    preserved = {
        k: v for k, v in current.items()
        if k not in generated_keys and k != "updatedAt"
    }
    if "emergencyRevocations" in preserved:
        preserved["emergencyRevocations"] = canonical_revocations(
            preserved["emergencyRevocations"]
        )

    payload = payload_paths(generated_collections)
    total_payload_bytes = sum(download_size_bytes(path) for path in payload)

    candidate = {
        **preserved,
        "schemaVersion": 4,
        "contentVersion": previous_version,
        "minimumAppVersion": max_semver(
            str(current.get("minimumAppVersion", "0.32.0")),
            "0.60.0" if generated_collections["sharedLearning"] else "0.49.0"
        ),
        # Bytes downloaded after manifest.json itself. The Flutter client adds
        # the actual manifest response length to this value for the full total.
        "downloadSizeBytes": total_payload_bytes,
        "references": {
            "file": "references/references.json",
            "sha256": sha256(REFERENCES_PATH),
            "sizeBytes": text_size_bytes(REFERENCES_PATH),
        },
        "glossary": {
            "file": "glossary/glossary.json",
            "sha256": sha256(GLOSSARY_PATH),
            "sizeBytes": text_size_bytes(GLOSSARY_PATH),
        },
        "assessmentCategories": {
            "file": "categories/assessment-categories.json",
            "schema": "schema/assessment-categories-schema.json",
            "sha256": sha256(CATEGORIES_PATH),
            "schemaSha256": sha256(CATEGORIES_SCHEMA_PATH),
            "sizeBytes": text_size_bytes(CATEGORIES_PATH),
            "schemaSizeBytes": text_size_bytes(CATEGORIES_SCHEMA_PATH),
            "items": categories["categories"],
        },
        "assessments": generated_collections["assessments"],
        "guidelines": generated_collections["guidelines"],
        "scoringTools": generated_collections["scoringTools"],
        "bloodPanels": generated_collections["bloodPanels"],
        "medications": generated_collections["medications"],
        "prescribing": generated_collections["prescribing"],
        "sharedLearning": generated_collections["sharedLearning"],
    }

    current_semantic = {
        k: v for k, v in current.items() if k not in {"contentVersion", "updatedAt"}
    }
    candidate_semantic = {
        k: v for k, v in candidate.items() if k != "contentVersion"
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
            k: v
            for k, v in candidate.items()
            if k not in {"schemaVersion", "contentVersion"}
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
        f"downloadSizeBytes={generated['downloadSizeBytes']}, "
        f"assessments={len(generated['assessments'])}, "
        f"guidelines={len(generated['guidelines'])}, "
        f"scoringTools={len(generated['scoringTools'])}, "
        f"bloodPanels={len(generated['bloodPanels'])}, "
        f"medications={len(generated['medications'])}, "
        f"prescribing={len(generated['prescribing'])}"
    )


if __name__ == "__main__":
    main()
