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
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


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


def collect_reference_ids(assessment: dict) -> set[str]:
    reference_ids = set(assessment.get("references", []))

    for section in assessment.get("sections", []):
        for item in section.get("items", []):
            reference_ids.update(item.get("references", []))
            imaging = item.get("imagingGuidance")
            if isinstance(imaging, dict):
                reference_ids.update(imaging.get("references", []))

    return reference_ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref",
        help="Base Git ref used to enforce assessment version increases.",
    )
    args = parser.parse_args()

    errors: list[str] = []

    schema = load_json(
        ROOT / "schema" / "assessment-schema.json",
        errors,
    )
    guideline_schema = load_json(
        ROOT / "schema" / "guideline-schema.json",
        errors,
    )
    references_document = load_json(
        ROOT / "references" / "references.json",
        errors,
    )

    if schema is None or guideline_schema is None or references_document is None:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    reference_items = references_document.get("references", [])
    reference_ids = [
        item.get("id")
        for item in reference_items
        if isinstance(item, dict)
    ]

    if any(not isinstance(item, str) or not item for item in reference_ids):
        errors.append("Every reference must have a non-empty string id.")

    if len(reference_ids) != len(set(reference_ids)):
        errors.append("Duplicate reference IDs exist.")

    known_reference_ids = set(reference_ids)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    assessment_paths = sorted((ROOT / "assessments").glob("*.json"))
    if not assessment_paths:
        errors.append("No assessment JSON files were found.")

    current_assessments: dict[str, dict] = {}

    for assessment_path in assessment_paths:
        assessment = load_json(assessment_path, errors)
        if assessment is None:
            continue

        assessment_id = assessment.get("id")
        if not isinstance(assessment_id, str) or not assessment_id:
            errors.append(f"{assessment_path}: missing valid id.")
            continue

        if assessment_id in current_assessments:
            errors.append(f"Duplicate assessment id: {assessment_id}.")
        current_assessments[assessment_id] = assessment

        try:
            version_parts(assessment["version"])
        except (KeyError, ValueError) as exc:
            errors.append(f"{assessment_path}: {exc}")

        for validation_error in sorted(
            validator.iter_errors(assessment),
            key=lambda item: [str(part) for part in item.absolute_path],
        ):
            location = ".".join(
                str(part) for part in validation_error.absolute_path
            )
            suffix = f":{location}" if location else ""
            errors.append(
                f"{assessment_path}{suffix}: "
                f"{validation_error.message}"
            )

        missing_references = sorted(
            collect_reference_ids(assessment) - known_reference_ids
        )
        if missing_references:
            errors.append(
                f"{assessment_path}: unknown reference IDs: "
                f"{', '.join(missing_references)}."
            )


    guideline_validator = Draft202012Validator(
        guideline_schema,
        format_checker=FormatChecker(),
    )
    guideline_paths = sorted((ROOT / "guidelines").glob("*.json"))
    if not guideline_paths:
        errors.append("No guideline JSON files were found.")

    current_guidelines: dict[str, dict] = {}
    for guideline_path in guideline_paths:
        guideline = load_json(guideline_path, errors)
        if guideline is None:
            continue
        guideline_id = guideline.get("id")
        if not isinstance(guideline_id, str) or not guideline_id:
            errors.append(f"{guideline_path}: missing valid id.")
            continue
        if guideline_id in current_guidelines:
            errors.append(f"Duplicate guideline id: {guideline_id}.")
        current_guidelines[guideline_id] = guideline

        try:
            version_parts(guideline["contentVersion"])
        except (KeyError, ValueError) as exc:
            errors.append(f"{guideline_path}: {exc}")

        for validation_error in sorted(
            guideline_validator.iter_errors(guideline),
            key=lambda item: [str(part) for part in item.absolute_path],
        ):
            location = ".".join(
                str(part) for part in validation_error.absolute_path
            )
            suffix = f":{location}" if location else ""
            errors.append(
                f"{guideline_path}{suffix}: {validation_error.message}"
            )

        missing_references = sorted(
            set(guideline.get("references", [])) - known_reference_ids
        )
        if missing_references:
            errors.append(
                f"{guideline_path}: unknown reference IDs: "
                f"{', '.join(missing_references)}."
            )

    if args.base_ref:
        changed = changed_files(args.base_ref)

        for relative_path in sorted(changed):
            is_assessment = (
                relative_path.startswith("assessments/")
                and relative_path.endswith(".json")
            )
            is_guideline = (
                relative_path.startswith("guidelines/")
                and relative_path.endswith(".json")
            )
            if not (is_assessment or is_guideline):
                continue

            current_path = ROOT / relative_path
            if not current_path.exists():
                continue

            current = load_json(current_path, errors)
            previous = load_json_from_git(args.base_ref, relative_path)

            if current is None or previous is None:
                continue

            try:
                version_key = "version" if is_assessment else "contentVersion"
                if version_parts(current[version_key]) <= version_parts(
                    previous[version_key]
                ):
                    errors.append(
                        f"{relative_path} changed, but its {version_key} was "
                        f"not increased ({previous[version_key]} -> "
                        f"{current[version_key]})."
                    )
            except (KeyError, ValueError) as exc:
                errors.append(f"{relative_path}: {exc}")

    if errors:
        print("\nValidation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Assessment and guideline content validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
