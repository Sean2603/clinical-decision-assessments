#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_assessment_references(value):
    result = set(value.get("references", []))
    for section in value.get("sections", []):
        for item in section.get("items", []):
            result.update(item.get("references", []))
            imaging = item.get("imagingGuidance")
            if isinstance(imaging, dict):
                result.update(imaging.get("references", []))
    return result


registry = load(ROOT / "references" / "references.json")
usage = {reference["id"]: [] for reference in registry["references"]}

for path in sorted((ROOT / "assessments").glob("*.json")):
    document = load(path)
    for reference_id in collect_assessment_references(document):
        usage.setdefault(reference_id, []).append({
            "type": "assessment",
            "id": document["id"],
            "title": document["title"],
        })

for path in sorted((ROOT / "guidelines").glob("*.json")):
    document = load(path)
    for reference_id in document.get("references", []):
        usage.setdefault(reference_id, []).append({
            "type": "guideline",
            "id": document["id"],
            "title": document["title"],
        })

for folder, content_type in (
    ("scoring_tools", "scoring-tool"),
    ("blood_panels", "blood-panel"),
):
    for path in sorted((ROOT / folder).glob("*.json")):
        document = load(path)
        for reference_id in document.get("referenceIds", []):
            usage.setdefault(reference_id, []).append({
                "type": content_type,
                "id": document["id"],
                "title": document["title"],
            })

for item in load(
    ROOT / "clinical_reliability" / "clinical-reliability.json"
)["items"]:
    for reference_id in item.get("referenceIds", []):
        usage.setdefault(reference_id, []).append({
            "type": f"{item['category']}-reliability",
            "id": item["id"],
            "title": item["displayName"],
        })

output = {
    "generated": True,
    "references": [
        {
            "referenceId": reference_id,
            "usedBy": items,
        }
        for reference_id, items in sorted(usage.items())
    ],
}
path = ROOT / "reference-usage.json"
path.write_text(
    json.dumps(output, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(f"Generated {path.name} for {len(usage)} references.")
