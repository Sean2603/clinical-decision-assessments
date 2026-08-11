#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

COLLECTIONS = {
    "assessment": {
        "directory": ROOT / "assessments",
        "schema": ROOT / "schema" / "assessment-schema.json",
        "versionField": "version",
    },
    "guideline": {
        "directory": ROOT / "guidelines",
        "schema": ROOT / "schema" / "guideline-schema.json",
        "versionField": "contentVersion",
    },
    "scoring-tool": {
        "directory": ROOT / "scoring_tools",
        "schema": ROOT / "schema" / "scoring-tool-schema.json",
        "versionField": "version",
    },
    "blood-panel": {
        "directory": ROOT / "blood_panels",
        "schema": ROOT / "schema" / "blood-panel-schema.json",
        "versionField": "version",
    },
    "medication": {
        "directory": ROOT / "medications",
        "schema": ROOT / "schema" / "medication-schema.json",
        "versionField": "version",
        "allowEmpty": True,
    },
    "prescribing": {
        "directory": ROOT / "prescribing",
        "schema": ROOT / "schema" / "prescribing-schema.json",
        "versionField": "version",
        "allowEmpty": True,
    },
}


def load_json(path: Path, errors: list[str]) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"Missing required file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        )
    return None


def version_parts(value: str) -> tuple[int, int, int]:
    if not SEMVER.fullmatch(value):
        raise ValueError(f"Invalid semantic version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def changed_files(base_ref: str) -> set[str]:
    merge_base = git_output("merge-base", base_ref, "HEAD").strip()
    output = git_output(
        "diff",
        "--name-only",
        "--diff-filter=ACMRTD",
        f"{merge_base}...HEAD",
    )
    return {
        line.strip().replace("\\", "/")
        for line in output.splitlines()
        if line.strip()
    }


def load_json_from_git(ref: str, relative_path: str) -> dict | None:
    try:
        return json.loads(git_output("show", f"{ref}:{relative_path}"))
    except subprocess.CalledProcessError:
        return None


def assessment_reference_ids(value: dict) -> set[str]:
    reference_ids = set(value.get("references", []))
    for section in value.get("sections", []):
        for item in section.get("items", []):
            reference_ids.update(item.get("references", []))
            imaging = item.get("imagingGuidance")
            if isinstance(imaging, dict):
                reference_ids.update(imaging.get("references", []))
    return reference_ids


def document_reference_ids(kind: str, value: dict) -> set[str]:
    if kind == "assessment":
        return assessment_reference_ids(value)
    if kind in {"guideline", "medication", "prescribing"}:
        return set(value.get("references", []))
    return set(value.get("referenceIds", []))


def validate_collection(
    kind: str,
    settings: dict,
    known_reference_ids: set[str],
    known_category_ids: set[str],
    errors: list[str],
) -> dict[str, dict]:
    schema = load_json(settings["schema"], errors)
    if schema is None:
        return {}

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    paths = sorted(settings["directory"].glob("*.json"))
    if not paths:
        if settings.get("allowEmpty", False):
            return {}
        errors.append(
            f"No JSON files found in {settings['directory'].relative_to(ROOT)}."
        )
        return {}

    documents: dict[str, dict] = {}
    for path in paths:
        value = load_json(path, errors)
        if value is None:
            continue

        item_id = value.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{path}: missing valid id.")
            continue
        if item_id in documents:
            errors.append(f"Duplicate {kind} id: {item_id}.")
        documents[item_id] = value

        for validation_error in sorted(
            validator.iter_errors(value),
            key=lambda item: [str(part) for part in item.absolute_path],
        ):
            location = ".".join(
                str(part) for part in validation_error.absolute_path
            )
            suffix = f":{location}" if location else ""
            errors.append(f"{path}{suffix}: {validation_error.message}")

        if kind == "assessment":
            category_ids = value.get("categoryIds", ["uncategorised"])
            unknown_categories = sorted(set(category_ids) - known_category_ids)
            if unknown_categories:
                errors.append(f"{path}: unknown category IDs: {', '.join(unknown_categories)}.")

        missing = sorted(
            document_reference_ids(kind, value) - known_reference_ids
        )
        if missing:
            errors.append(
                f"{path}: unknown reference IDs: {', '.join(missing)}."
            )

    return documents



def validate_assessment_categories(errors: list[str]) -> set[str]:
    document = load_json(ROOT / "categories" / "assessment-categories.json", errors)
    schema = load_json(ROOT / "schema" / "assessment-categories-schema.json", errors)
    if document is None or schema is None:
        return set()
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for validation_error in validator.iter_errors(document):
        errors.append(f"assessment categories: {validation_error.message}")
    ids = [item.get("id") for item in document.get("categories", []) if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate assessment category IDs exist.")
    if "uncategorised" not in ids:
        errors.append("Assessment categories must include uncategorised.")
    return {item for item in ids if isinstance(item, str)}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref",
        help="Base Git ref used to enforce content version increases.",
    )
    args = parser.parse_args()
    errors: list[str] = []
    known_category_ids = validate_assessment_categories(errors)

    references_document = load_json(
        ROOT / "references" / "references.json",
        errors,
    )
    if references_document is None:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    reference_ids = [
        item.get("id")
        for item in references_document.get("references", [])
        if isinstance(item, dict)
    ]
    if any(not isinstance(item, str) or not item for item in reference_ids):
        errors.append("Every reference must have a non-empty string id.")
    if len(reference_ids) != len(set(reference_ids)):
        errors.append("Duplicate reference IDs exist.")
    known_reference_ids = {
        item for item in reference_ids if isinstance(item, str) and item
    }

    documents_by_kind: dict[str, dict[str, dict]] = {}
    for kind, settings in COLLECTIONS.items():
        documents_by_kind[kind] = validate_collection(
            kind,
            settings,
            known_reference_ids,
            known_category_ids,
            errors,
        )

    if args.base_ref:
        changed = changed_files(args.base_ref)
        folder_to_kind = {
            "assessments": "assessment",
            "guidelines": "guideline",
            "scoring_tools": "scoring-tool",
            "blood_panels": "blood-panel",
            "medications": "medication",
            "prescribing": "prescribing",
        }
        for relative_path in sorted(changed):
            folder = relative_path.split("/", 1)[0]
            kind = folder_to_kind.get(folder)
            if kind is None or not relative_path.endswith(".json"):
                continue
            current_path = ROOT / relative_path
            if not current_path.exists():
                continue
            current = load_json(current_path, errors)
            previous = load_json_from_git(args.base_ref, relative_path)
            if current is None or previous is None:
                continue
            version_field = COLLECTIONS[kind]["versionField"]
            try:
                if version_parts(current[version_field]) <= version_parts(
                    previous[version_field]
                ):
                    errors.append(
                        f"{relative_path} changed, but {version_field} was "
                        f"not increased ({previous[version_field]} -> "
                        f"{current[version_field]})."
                    )
            except (KeyError, ValueError) as exc:
                errors.append(f"{relative_path}: {exc}")

    if errors:
        print("\nClinical content validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Clinical content validation passed: "
        f"{len(documents_by_kind['assessment'])} assessments, "
        f"{len(documents_by_kind['guideline'])} guidelines, "
        f"{len(documents_by_kind['scoring-tool'])} scoring tools, "
        f"{len(documents_by_kind['blood-panel'])} blood panels, "
        f"{len(documents_by_kind['medication'])} medications, "
        f"{len(documents_by_kind['prescribing'])} prescribing pathways."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
