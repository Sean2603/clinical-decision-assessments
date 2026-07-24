import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    references = manifest.get("references", {})
    references_file = references.get("file")

    if not references_file:
        raise ValueError("Manifest references.file is missing.")

    references_path = ROOT / references_file
    if not references_path.exists():
        raise FileNotFoundError(references_path)

    references["sha256"] = sha256(references_path)

    for assessment in manifest.get("assessments", []):
        assessment_file = assessment.get("file")
        schema_file = assessment.get("schema")

        if not assessment_file:
            raise ValueError(
                f"Assessment {assessment.get('id')} has no file path."
            )

        assessment_path = ROOT / assessment_file
        if not assessment_path.exists():
            raise FileNotFoundError(assessment_path)

        assessment["sha256"] = sha256(assessment_path)

        if schema_file:
            schema_path = ROOT / schema_file
            if not schema_path.exists():
                raise FileNotFoundError(schema_path)

            assessment["schemaSha256"] = sha256(schema_path)

    manifest["updatedAt"] = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("manifest.json updated successfully.")


if __name__ == "__main__":
    main()
