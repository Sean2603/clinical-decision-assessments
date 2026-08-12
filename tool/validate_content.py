#!/usr/bin/env python3
import argparse
import hashlib
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




IMAGE_KIND_FOLDERS = {
    "assessment": "assessments",
    "guideline": "guidelines",
    "scoring-tool": "scoring_tools",
    "blood-panel": "blood_panels",
    "medication": "medications",
    "prescribing": "prescribing",
    "clinical-notice": "clinical_notices",
}

def _binary_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _validate_attachments(kind: str, value: dict, source_path: Path, known_reference_ids: set[str], errors: list[str]) -> None:
    attachments = value.get("attachments", [])
    if not isinstance(attachments, list):
        return
    expected_folder = IMAGE_KIND_FOLDERS.get(kind)
    seen_ids: set[str] = set()
    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".xlsx", ".csv", ".pptx", ".txt", ".md"}
    for index, attachment in enumerate(attachments):
        prefix = f"{source_path}:attachments[{index}]"
        if not isinstance(attachment, dict):
            continue
        attachment_id = attachment.get("id")
        if isinstance(attachment_id, str):
            if attachment_id in seen_ids:
                errors.append(f"{prefix}: duplicate attachment id {attachment_id}.")
            seen_ids.add(attachment_id)
        rel = attachment.get("path")
        if not isinstance(rel, str):
            continue
        normalized = rel.replace("\\\\", "/")
        if normalized.startswith("/") or ".." in Path(normalized).parts:
            errors.append(f"{prefix}: attachment path must stay inside the repository attachments directory.")
            continue
        parts = normalized.split("/")
        if len(parts) < 3 or parts[0] != "attachments":
            errors.append(f"{prefix}: attachment path must start with attachments/.")
            continue
        if expected_folder and parts[1] != expected_folder:
            errors.append(f"{prefix}: attachment path must use attachments/{expected_folder}/ for {kind} content.")
        attachment_path = ROOT / normalized
        if attachment_path.suffix.lower() not in allowed_extensions:
            errors.append(f"{prefix}: unsupported attachment extension {attachment_path.suffix}.")
        if not attachment_path.exists():
            errors.append(f"{prefix}: referenced attachment does not exist: {normalized}.")
        elif not attachment_path.is_file():
            errors.append(f"{prefix}: referenced attachment is not a file: {normalized}.")
        else:
            expected_hash = attachment.get("sha256")
            if isinstance(expected_hash, str) and _binary_sha256(attachment_path) != expected_hash.lower():
                errors.append(f"{prefix}: sha256 does not match {normalized}.")
        reference_id = attachment.get("referenceId")
        if isinstance(reference_id, str) and reference_id and reference_id not in known_reference_ids:
            errors.append(f"{prefix}: unknown referenceId {reference_id}.")
        governance = attachment.get("replacementGovernance")
        if isinstance(governance, dict):
            previous_path = governance.get("previousPath")
            if previous_path == rel:
                errors.append(f"{prefix}: replacement must use a new versioned attachment path.")
            if isinstance(previous_path, str):
                previous_file = ROOT / previous_path
                if not previous_file.exists():
                    errors.append(f"{prefix}: previous attachment must remain in the repository: {previous_path}.")
                elif isinstance(governance.get("previousSha256"), str) and _binary_sha256(previous_file) != governance["previousSha256"].lower():
                    errors.append(f"{prefix}: previousSha256 does not match {previous_path}.")
            if governance.get("clinicalMeaningChanged") is True and governance.get("requiresRevalidation") is not True:
                errors.append(f"{prefix}: clinicalMeaningChanged=true requires requiresRevalidation=true.")
            if governance.get("sourceChecked") is not True:
                errors.append(f"{prefix}: replacement source/reference must be confirmed.")
            validation = value.get("clinicalValidation")
            if governance.get("clinicalMeaningChanged") is True and isinstance(validation, dict) and validation.get("validated") is True:
                errors.append(f"{prefix}: clinically meaningful attachment replacement requires parent content to return to unvalidated status.")

def _validate_image_attachments(kind: str, value: dict, source_path: Path, known_reference_ids: set[str], errors: list[str]) -> None:
    images = value.get("images", [])
    if not isinstance(images, list):
        return
    expected_folder = IMAGE_KIND_FOLDERS.get(kind)
    seen_ids: set[str] = set()
    for index, image in enumerate(images):
        prefix = f"{source_path}:images[{index}]"
        if not isinstance(image, dict):
            continue
        image_id = image.get("id")
        if isinstance(image_id, str):
            if image_id in seen_ids:
                errors.append(f"{prefix}: duplicate image id {image_id}.")
            seen_ids.add(image_id)
        rel = image.get("path")
        if not isinstance(rel, str):
            continue
        normalized = rel.replace("\\", "/")
        if normalized.startswith("/") or ".." in Path(normalized).parts:
            errors.append(f"{prefix}: image path must stay inside the repository images directory.")
            continue
        parts = normalized.split("/")
        if len(parts) < 3 or parts[0] != "images":
            errors.append(f"{prefix}: image path must start with images/.")
            continue
        if expected_folder and parts[1] != expected_folder:
            errors.append(f"{prefix}: image path must use images/{expected_folder}/ for {kind} content.")
        image_path = ROOT / normalized
        if not image_path.exists():
            errors.append(f"{prefix}: referenced image does not exist: {normalized}.")
        elif not image_path.is_file():
            errors.append(f"{prefix}: referenced image is not a file: {normalized}.")
        else:
            expected_hash = image.get("sha256")
            if isinstance(expected_hash, str) and _binary_sha256(image_path) != expected_hash.lower():
                errors.append(f"{prefix}: sha256 does not match {normalized}.")
        reference_id = image.get("referenceId")
        if isinstance(reference_id, str) and reference_id and reference_id not in known_reference_ids:
            errors.append(f"{prefix}: unknown referenceId {reference_id}.")
        governance = image.get("replacementGovernance")
        if isinstance(governance, dict):
            previous_path = governance.get("previousPath")
            if previous_path == rel:
                errors.append(f"{prefix}: a replacement must use a new versioned image path; previousPath cannot equal path.")
            if isinstance(previous_path, str):
                previous_file = ROOT / previous_path
                if not previous_file.exists():
                    errors.append(f"{prefix}: previous image must remain in the repository: {previous_path}.")
                elif isinstance(governance.get("previousSha256"), str) and _binary_sha256(previous_file) != governance["previousSha256"].lower():
                    errors.append(f"{prefix}: previousSha256 does not match {previous_path}.")
            if governance.get("clinicalMeaningChanged") is True and governance.get("requiresRevalidation") is not True:
                errors.append(f"{prefix}: clinicalMeaningChanged=true requires requiresRevalidation=true.")
            if governance.get("sourceChecked") is not True:
                errors.append(f"{prefix}: replacement source/reference must be confirmed with sourceChecked=true.")
            validation = value.get("clinicalValidation")
            if governance.get("clinicalMeaningChanged") is True and isinstance(validation, dict) and validation.get("validated") is True:
                errors.append(f"{prefix}: clinically meaningful image replacement requires parent content to return to unvalidated status before publication.")

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

        _validate_attachments(kind, value, path, known_reference_ids, errors)
        _validate_image_attachments(kind, value, path, known_reference_ids, errors)

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

    # Validate centrally managed clinical notices.
    notices_path = ROOT / "clinical_notices" / "clinical-notices.json"
    notices_schema_path = ROOT / "schema" / "clinical-notices-schema.json"
    if notices_path.exists() and notices_schema_path.exists():
        notices_document = load_json(notices_path, errors)
        notices_schema = load_json(notices_schema_path, errors)
        if notices_document is not None and notices_schema is not None:
            validator = Draft202012Validator(notices_schema, format_checker=FormatChecker())
            for validation_error in sorted(
                validator.iter_errors(notices_document),
                key=lambda item: [str(part) for part in item.absolute_path],
            ):
                location = ".".join(str(part) for part in validation_error.absolute_path)
                suffix = f":{location}" if location else ""
                errors.append(f"{notices_path}{suffix}: {validation_error.message}")
            for notice in notices_document.get("notices", []):
                if isinstance(notice, dict):
                    _validate_image_attachments("clinical-notice", notice, notices_path, known_reference_ids, errors)

    # Prescribing medication links must resolve when a medicationId is supplied.
    medication_ids = set(documents_by_kind["medication"].keys())
    for pathway_id, pathway in documents_by_kind["prescribing"].items():
        for regimen in pathway.get("regimens", []):
            medication_id = regimen.get("medicationId")
            if medication_id and medication_id not in medication_ids:
                errors.append(
                    f"prescribing/{pathway_id}: regimen medicationId {medication_id!r} does not resolve to medications/{medication_id}.json"
                )
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
