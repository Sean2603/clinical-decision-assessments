# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **CDA** (Clinical Decision Assessments) — the governed clinical-content repository for the Clinical Decision Support platform. It is a data/schema/tooling repo, not an application: it holds structured JSON clinical content (assessments, guidelines, procedures, scoring tools, blood panels, medications, prescribing pathways, shared learning), the JSON Schemas that validate it, the shared reference/glossary registries, generated publication metadata, and Python validation tooling under `tool/`.

It has two sibling repos in the same platform: **CDM Content Manager** (`cdm-content-manager`, the Next.js authoring/governance app clinical editors use to draft/review/publish content into this repo) and **Clinical Decision App** (`clinical-decision-app`, the Flutter mobile client that downloads and renders the published content pack).

**Routine clinical content editing should go through CDM, not this repo directly.** Direct repository editing here is reserved for repository maintenance, tooling/schema changes, recovery, or exceptional administrative work.

## Local validation environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip      # .venv/Scripts/python.exe on Windows
.venv/bin/python -m pip install jsonschema
```

The venv does not need activating — call its Python executable directly (on Windows: `.venv/Scripts/python.exe`).

## Validation commands

Full local sequence (mirrors CI):

```bash
.venv/bin/python tool/validate_content.py
.venv/bin/python tool/validate_references.py
.venv/bin/python tool/validate_references.py --strict
.venv/bin/python tool/validate_remote_engines.py
.venv/bin/python tool/generate_reference_usage.py
.venv/bin/python tool/sync_manifest.py --write
.venv/bin/python tool/validate_manifest_safety.py
.venv/bin/python tool/sync_manifest.py --check
```

- `validate_content.py` — validates every content collection against its JSON Schema, plus cross-cutting checks (attachment integrity/paths/SHA-256, inline `{{attachment:...}}`/`{{image:...}}`/`{{no-definition:...}}`/`@stable-id` token resolution, category IDs, cross-links between medications and prescribing pathways). Pass `--base-ref origin/main` on a review branch to enforce that any changed content item's version field was actually incremented.
- `validate_references.py` — validates the shared reference registry (`references/references.json`) and checks that every reference cited by content actually exists. It scans **both** the `references` field (assessments/guidelines/procedures/medications/prescribing/shared-learning) and the `referenceIds` field (scoring tools/blood panels) — these are different field names for the same concept, so a new content collection must be added to *both* `generate_reference_usage.py`'s folder list and `validate_references.py`'s folder list, and its reference-array field name must be added to `collect_reference_ids`'s key set. `--strict` additionally fails if any cited-by-validated-content reference is not `current` (blocks a validated item from shipping with a withdrawn/superseded/unverified source).
- `validate_remote_engines.py` — executes the scoring-tool and blood-calculation evaluation engines against every embedded `parityCases`/`calculationCases` fixture. This is the parity check that keeps the JSON-declared calculators consistent with the app's own remote-engine implementation.
- `validate_manifest_safety.py` — validates `manifest.json`'s `updatePolicy` and `emergencyRevocations` safety controls.
- `sync_manifest.py --write` / `--check` — deterministically regenerates `manifest.json` (schema/content hashes, sizes, minimum-app-version computation, category assignments) from the current repository state. **Any change to a schema file or any content file requires regenerating the manifest** (it embeds a SHA-256 of every schema and content file) — `--check` fails otherwise. `--write` is the only thing that should ever change `manifest.json`; never hand-edit it.
- `generate_reference_usage.py` — regenerates `reference-usage.json`, the reverse index of which content items cite which references. Also a generated artefact; never hand-edit.

CI (`assessments.yml`) runs this same sequence read-only and fails if validation leaves any working-tree diff. A separate manually-dispatched workflow (`generate-manifest.yml`) is the only supported write path for regenerating and committing `manifest.json`/`reference-usage.json` on GitHub.

## Architecture

**Content collections** each live in their own top-level folder (`assessments/`, `guidelines/`, `procedures/`, `scoring_tools/`, `blood_panels/`, `medications/`, `prescribing/`, `shared_learning/`), one JSON file per item, validated against the matching `schema/*-schema.json`. Managed collections may legitimately be empty (e.g. `guidelines/` and `procedures/` currently have zero items — this is expected, not a bug). `tool/sync_manifest.py`'s `COLLECTIONS` dict and `tool/validate_content.py`'s `COLLECTIONS` dict are the two authoritative maps of folder → schema → version field; keep them in sync when adding a collection.

**`manifest.json`** is the generated content-pack manifest the Flutter app downloads: per-item file path, schema path, SHA-256 hashes, sizes, and a computed `minimumAppVersion` (bumped automatically when content uses a feature — inline images, inline-only media, procedures, shared learning — that requires a newer app build). `contentVersion` auto-bumps on any semantic change (anything other than `contentVersion`/`updatedAt` themselves).

**`references/references.json`** is the single shared reference registry (source of truth for all citable references across every content type); `reference-usage.json` is its generated reverse index. A reference's `reviewStatus` (`current`/`review-due`/`superseded`/`withdrawn`/`unavailable`/`unverified`) plus `nextReviewDue` drive the `--strict` clinical-currency gate.

**`categories/assessment-categories.json`** defines the assessment taxonomy, including semantic `iconKey` values consumed by the app. Schema v3 categories can carry an `assignments` map (assessment stable ID → governed category IDs); when present, this is authoritative for manifest `categoryIds` generation, with the assessment JSON's own embedded `categoryIds` field retained only as a backwards-compatible fallback for older schema versions. Category IDs referenced by any assessment must exist in the registry even if `assignments` overrides them.

**Attachments** (`attachments/`) are governed files referenced by content via structured metadata (`path`, `sha256`, `type`, etc.); validation checks the path exists inside `attachments/<expected-folder-for-content-kind>/`, extension is allowed, and the SHA-256 matches. Inline assessment images use `{{image:attachment-id}}` tokens resolved against the assessment's own `attachments` array (image tokens are assessment-only). `__inline_only__`-labelled image attachments are hidden from the app's generic Attachments card but must still be referenced by an image token.

**Governance model** (enforced by CDM, not this repo): Draft → Awaiting review → Awaiting clinical validation → Ready to publish → Repository-confirmed Published. `main` is the authoritative publication branch; `content-review/clinical-review` is CDM's reusable review branch. An item is only "Published" once its exact governed version is on `main` — internal CDM snapshots, local commits, or open PRs don't count.

## Gotchas worth remembering

- Windows checkouts show `warning: ... CRLF will be replaced by LF` on `manifest.json` — harmless; `sync_manifest.py` canonicalises line endings before hashing, so this doesn't affect determinism.
- `$id` in every `schema/*.json` file should point to `https://raw.githubusercontent.com/Sean2603/clinical-decision-assessments/main/schema/<file>` — keep this consistent when adding a new schema.
- Scoring tools and blood panels cite references via `referenceIds`; every other content type uses `references`. Don't assume one field name across collections.
