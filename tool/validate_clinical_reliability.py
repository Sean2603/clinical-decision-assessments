#!/usr/bin/env python3
"""Validate embedded clinicalValidation metadata across all clinical content."""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = {
    "assessments": ("assessment", "version"),
    "guidelines": ("guideline", "contentVersion"),
    "scoring_tools": ("scoring-tool", "version"),
    "blood_panels": ("blood-panel", "version"),
    "prescribing": ("prescribing", "version"),
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    errors=[]; warnings=[]; count=0
    for folder,(kind,version_field) in COLLECTIONS.items():
        for path in sorted((ROOT/folder).glob("*.json")):
            count += 1
            doc=load(path); cv=doc.get("clinicalValidation")
            label=f"{folder}/{path.name}"
            if not isinstance(cv,dict):
                errors.append(f"{label}: clinicalValidation is required."); continue
            required=("validated","reviewedBy","reviewedOn","reviewerRole","nextReviewDue","reviewNotes")
            missing=[x for x in required if x not in cv]
            if missing: errors.append(f"{label}: missing clinicalValidation fields: {', '.join(missing)}")
            if cv.get("validated") is True:
                for field in ("reviewedBy","reviewedOn","reviewerRole","nextReviewDue"):
                    if cv.get(field) in (None,""):
                        errors.append(f"{label}: validated content requires {field}.")
                try:
                    reviewed=date.fromisoformat(cv["reviewedOn"]); due=date.fromisoformat(cv["nextReviewDue"])
                    if due <= reviewed: errors.append(f"{label}: nextReviewDue must be after reviewedOn.")
                    if due < date.today(): warnings.append(f"{label}: clinical review overdue since {due.isoformat()}.")
                except (TypeError,ValueError,KeyError):
                    errors.append(f"{label}: review dates must use YYYY-MM-DD.")
            if not isinstance(doc.get(version_field),str):
                errors.append(f"{label}: missing {version_field}.")
    if warnings:
        print("Clinical validation warnings:")
        for item in warnings: print(f"- {item}")
    if errors:
        print("Clinical validation failed:")
        for item in errors: print(f"- {item}")
        raise SystemExit(1)
    print(f"Clinical validation passed: {count} embedded content record(s).")

if __name__ == "__main__": main()
