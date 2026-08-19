#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
errors = []
policy = manifest.get("updatePolicy", {})
mode = policy.get("mode", "optional")
if mode not in {"optional", "required", "revocation-only"}: errors.append(f"updatePolicy.mode is invalid: {mode}")
if policy.get("blockClinicalContentUntilUpdated") and mode != "required": errors.append("blockClinicalContentUntilUpdated may only be true when mode is required")
if mode == "required" and not str(policy.get("message", "")).strip(): errors.append("required update policy must include a message")
for i, item in enumerate(manifest.get("emergencyRevocations", [])):
    prefix=f"emergencyRevocations[{i}]"
    for key in ("contentType", "contentId", "action", "reason"):
        if not str(item.get(key, "")).strip(): errors.append(f"{prefix}.{key} is required")
    if item.get("action") not in {"block", "disable", "warn"}: errors.append(f"{prefix}.action is invalid")
    versions=item.get("affectedVersions", {})
    if versions is not None and not isinstance(versions, dict): errors.append(f"{prefix}.affectedVersions must be an object")
if errors:
    print("Manifest safety validation failed:")
    for error in errors: print(f"- {error}")
    sys.exit(1)
print(f"Manifest safety validation passed: mode={mode}, revocations={len(manifest.get('emergencyRevocations', []))}.")
