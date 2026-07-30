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
    references = manifest["references"]
    references["sha256"] = sha256(ROOT / references["file"])
    for assessment in manifest["assessments"]:
        assessment["sha256"] = sha256(ROOT / assessment["file"])
        assessment["schemaSha256"] = sha256(ROOT / assessment["schema"])
    manifest["updatedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("manifest.json updated successfully")


if __name__ == "__main__":
    main()
