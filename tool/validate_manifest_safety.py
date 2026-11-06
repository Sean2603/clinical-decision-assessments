#!/usr/bin/env python3
"""Validate manifest.json safety controls against the app's parsing contract.

The app (lib/models/assessment_content/manifest.dart) hard-casts these fields,
so any wrong type here would throw while parsing the whole manifest and stop
the app from applying updates or revocations. Every check mirrors one of those
casts, or a value the app actually understands.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Revocation contentType values the app passes to revocationFor(); these mirror
# ClinicalDestinationType.supported in the app, which is the vocabulary it can
# actually revoke. contentId is deliberately not required to exist: an emergency
# revocation may target an item already removed from this repository but still
# installed on devices.
CONTENT_TYPES = frozenset({
    "assessment",
    "guideline",
    "procedure",
    "scoring-tool",
    "blood-panel",
    "medication",
    "prescribing",
})
ACTIONS = {"block", "disable", "warn"}
MODES = {"optional", "required", "revocation-only"}
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
# Dart DateTime.parse grammar (ASCII digits only); ranges checked separately.
DART_DATE_TIME = re.compile(
    r"([+-]?[0-9]{4,6})-?([0-9]{2})-?([0-9]{2})"
    r"(?:[ T]([0-9]{2})(?::?([0-9]{2})(?::?([0-9]{2})(?:[.,]([0-9]+))?)?)?"
    r"( ?[zZ]| ?([-+])([0-9]{2})(?::?([0-9]{2}))?)?)?\Z"
)


def check_date_time(value, label, errors):
    """Dart: json[key] == null ? null : DateTime.parse(json[key] as String)."""
    if value is None:
        return
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO-8601 string or null")
        return
    match = DART_DATE_TIME.match(value)
    if not match:
        errors.append(f"{label} is not a valid ISO-8601 date-time: {value!r}")
        return
    year, month, day, hour, minute, second = (
        int(part) if part else 0 for part in match.groups()[:6]
    )
    try:
        datetime(year, month, day, hour, minute, second)
    except ValueError:
        errors.append(f"{label} is out of range: {value!r}")


manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
errors = []

policy = manifest.get("updatePolicy")
if not isinstance(policy, dict):
    if policy is not None:
        errors.append("updatePolicy must be an object or null")
    policy = {}
for key in ("mode", "severity", "message"):
    if key in policy and not isinstance(policy[key], str):
        errors.append(f"updatePolicy.{key} must be a string")
mode = policy.get("mode", "optional")
if isinstance(mode, str) and mode not in MODES:
    errors.append(f"updatePolicy.mode is invalid: {mode}")
block = policy.get("blockClinicalContentUntilUpdated")
if block is not None and not isinstance(block, bool):
    errors.append("updatePolicy.blockClinicalContentUntilUpdated must be a boolean")
if block is True and mode != "required":
    errors.append("blockClinicalContentUntilUpdated may only be true when mode is required")
message = policy.get("message", "")
if mode == "required" and not (isinstance(message, str) and message.strip()):
    errors.append("required update policy must include a message")
check_date_time(policy.get("effectiveFrom"), "updatePolicy.effectiveFrom", errors)

revocations = manifest.get("emergencyRevocations")
if not isinstance(revocations, list):
    if revocations is not None:
        errors.append("emergencyRevocations must be an array")
    revocations = []
for i, item in enumerate(revocations):
    prefix = f"emergencyRevocations[{i}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix} must be an object")
        continue
    for key in ("contentType", "contentId", "action", "reason"):
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{prefix}.{key} must be a non-empty string")
    content_type = item.get("contentType")
    if isinstance(content_type, str) and content_type.strip():
        if content_type not in CONTENT_TYPES:
            errors.append(
                f"{prefix}.contentType is invalid: {content_type!r} "
                f"(expected one of {', '.join(sorted(CONTENT_TYPES))})"
            )
    if isinstance(item.get("action"), str) and item["action"] not in ACTIONS:
        errors.append(f"{prefix}.action is invalid")
    versions = item.get("affectedVersions")
    if versions is not None and not isinstance(versions, dict):
        errors.append(f"{prefix}.affectedVersions must be an object")
    elif versions is not None:
        for key in ("minimum", "maximum"):
            value = versions.get(key)
            if value is not None and not (isinstance(value, str) and VERSION.fullmatch(value)):
                errors.append(
                    f"{prefix}.affectedVersions.{key} must be an X.Y.Z string or null"
                )
    check_date_time(item.get("effectiveFrom"), f"{prefix}.effectiveFrom", errors)

if errors:
    print("Manifest safety validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print(f"Manifest safety validation passed: mode={mode}, revocations={len(revocations)}.")
