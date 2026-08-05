#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
REFERENCES_PATH = ROOT / "references" / "references.json"
SCHEMA_PATH = ROOT / "schema" / "reference-schema.json"

NON_CURRENT = {
    "superseded",
    "withdrawn",
    "unavailable",
    "unverified",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value):
    return None if value is None else date.fromisoformat(value)


def collect_reference_ids(value):
    found = set()

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "references" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            else:
                found.update(collect_reference_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_reference_ids(child))

    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Block publication when cited references are not current.",
    )
    args = parser.parse_args()

    errors = []
    warnings = []
    today = date.today()

    document = load_json(REFERENCES_PATH)
    schema = load_json(SCHEMA_PATH)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    for error in sorted(
        validator.iter_errors(document),
        key=lambda item: [str(part) for part in item.absolute_path],
    ):
        location = ".".join(str(part) for part in error.absolute_path)
        errors.append(f"{location or 'references.json'}: {error.message}")

    references = document.get("references", [])
    by_id = {}

    for reference in references:
        reference_id = reference.get("id")
        if reference_id in by_id:
            errors.append(f"Duplicate reference ID: {reference_id}")
        by_id[reference_id] = reference

    for reference in references:
        reference_id = reference.get("id", "<missing-id>")
        status = reference.get("reviewStatus")
        reviewed = parse_date(reference.get("lastReviewed"))
        due = parse_date(reference.get("nextReviewDue"))
        replacement = reference.get("supersededBy")

        if status == "current":
            for field in (
                "lastReviewed",
                "reviewedBy",
                "reviewerRole",
                "nextReviewDue",
            ):
                if reference.get(field) in (None, ""):
                    errors.append(
                        f"{reference_id}: current reference requires {field}."
                    )

            if due is not None and due < today:
                message = (
                    f"{reference_id}: review overdue since {due.isoformat()}."
                )
                if args.strict:
                    errors.append(message)
                else:
                    warnings.append(message)
            elif due is not None and due <= today + timedelta(days=30):
                warnings.append(
                    f"{reference_id}: review due on {due.isoformat()}."
                )

        if reviewed is not None and due is not None and due < reviewed:
            errors.append(
                f"{reference_id}: nextReviewDue is before lastReviewed."
            )

        if status == "superseded":
            if not replacement:
                errors.append(
                    f"{reference_id}: superseded reference requires supersededBy."
                )
            elif replacement not in by_id:
                errors.append(
                    f"{reference_id}: supersededBy {replacement!r} does not exist."
                )
        elif replacement is not None:
            errors.append(
                f"{reference_id}: supersededBy is only valid for superseded status."
            )

    cited_ids = set()
    strict_cited_ids = set()
    for folder in ("assessments", "guidelines", "scoring_tools", "blood_panels"):
        for content_path in sorted((ROOT / folder).glob("*.json")):
            document = load_json(content_path)
            item_ids = collect_reference_ids(document)
            cited_ids.update(item_ids)
            validation = document.get("clinicalValidation", {})
            if validation.get("validated") is True:
                strict_cited_ids.update(item_ids)

    missing = sorted(cited_ids - set(by_id))
    if missing:
        errors.append(f"Unknown cited reference IDs: {', '.join(missing)}")

    if args.strict:
        for reference_id in sorted(strict_cited_ids):
            reference = by_id.get(reference_id)
            if reference is None:
                continue

            status = reference.get("reviewStatus")
            due = parse_date(reference.get("nextReviewDue"))

            if status == "review-due":
                warnings.append(
                    f"{reference_id}: cited reference review is due; "
                    "publication is allowed but affected content must be "
                    "marked as requiring clinical validation."
                )
            elif status in NON_CURRENT:
                errors.append(
                    f"{reference_id}: cited reference status is {status!r}; "
                    "only current or review-due references may be published."
                )
            elif due is not None and due < today:
                warnings.append(
                    f"{reference_id}: cited reference review is overdue; "
                    "publication is allowed but affected content must be "
                    "marked as requiring clinical validation."
                )

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        print("\nReference validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Reference validation passed: {len(references)} reference(s), "
        f"{len(cited_ids)} cited."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
