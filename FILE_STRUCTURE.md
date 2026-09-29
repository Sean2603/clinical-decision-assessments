# Clinical Decision Assessments (CDA) - File Structure & Responsibilities

This document maps major files and directories in the Clinical Decision Assessments repository to their responsibilities and purpose.

## Repository Overview

CDA is the governed clinical-content repository for the Clinical Decision Support platform. It contains:
- **Structured JSON clinical content** (assessments, guidelines, procedures, scoring tools, blood panels, medications, prescribing pathways, shared learning)
- **JSON Schemas** that validate all content
- **Reference registry** (shared bibliography)
- **Generated artifacts** (manifest.json, reference-usage.json)
- **Python validation tooling** to ensure clinical correctness and consistency

**Important**: This is a data/schema/tooling repository, not an application. Routine clinical editing goes through CDM; direct repository edits are for maintenance, schema changes, or exceptions.

## Directory Structure

### `/assessments`
Clinical assessment guides (diagnostic algorithms, clinical examination guides, risk calculators).

Each file is a single assessment JSON object with:
- `id` – Unique stable identifier (never changes)
- `title` – Human-readable title
- `summary` – Brief description
- `sections` – Expandable sections with items (how-to-test, normal, abnormal, commonFindings, implications, urgentFeatures, safetyNetting)
- `references` – Citations by reference ID
- `attachments` – Embedded images and documents
- `version` – Semantic version (incremented on clinical change)
- `clinicalValidation` – Validation status and review metadata
- `categoryIds` – Taxonomy category assignments

**Files**: One JSON file per assessment. Currently ~100+ items.

**Schema**: `schema/assessment-schema.json` (v3)

### `/guidelines`
Clinical guidelines (evidence-based recommendations for management).

Similar structure to assessments but includes:
- `recommendations` – Step-by-step clinical recommendations
- `contraindications` – When not to use this approach
- `evidence` – Evidence strength ratings per recommendation

**Files**: Currently empty (expected to be populated in future).

**Schema**: `schema/guideline-schema.json` (v1)

### `/procedures`
Clinical procedures and practical skills guides.

Includes:
- `steps` – Numbered procedure steps
- `indications` – When to use this procedure
- `complications` – Potential adverse events
- `preparation` – Equipment and patient preparation

**Files**: Currently empty (expected to be populated in future).

**Schema**: `schema/procedure-schema.json` (v1)

### `/scoring_tools`
Automated scoring calculators (CURB-65, qSOFA, Wells score, etc.).

Each tool includes:
- `criteria` – Scoring input fields (text, numeric, select)
- `calculation` – Scoring algorithm (evaluated by app's remote engine)
- `interpretation` – Result ranges with clinical meaning
- `parityCases` – Test fixtures proving calculation matches app's implementation
- `references` – Source citations

**Files**: ~50+ scoring tools

**Schema**: `schema/scoring-tool-schema.json` (v1)

**Validation**: `tool/validate_remote_engines.py` executes every parity case to confirm app calculation parity.

### `/blood_panels`
Blood result interpretation tools (U&Es, FBC, LFTs, etc.).

Each panel includes:
- `specimens` – Specimen types (serum, plasma, CSF, etc.)
- `tests` – Individual tests with reference ranges
- `interpretation` – Normal/abnormal interpretation logic
- `calculationCases` – Fixtures proving app calculates correctly
- `referenceIds` – Citations by ID (note: uses referenceIds not references)

**Files**: ~30+ panels

**Schema**: `schema/blood-panel-schema.json` (v1)

**Validation**: `tool/validate_remote_engines.py` executes all calculation cases.

### `/medications`
Medication monographs (dosing, interactions, contraindications, etc.).

Each medication includes:
- `drugName` – Generic name
- `indications` – Approved uses
- `dosing` – Dose, frequency, route
- `sideEffects` – Common and serious adverse effects
- `interactions` – Drug-drug and food interactions
- `contraindications` – Absolute contraindications
- `references` – Source citations

**Files**: ~200+ medications

**Schema**: `schema/medication-schema.json` (v1)

### `/prescribing`
Prescribing pathways and decision trees.

Each pathway includes:
- `decision` – Root decision node
- `branches` – Alternative management paths with clinical criteria
- `actions` – End-state actions (prescribe medication, refer, monitor)
- `references` – Evidence citations

**Files**: ~50+ pathways

**Schema**: `schema/prescribing-schema.json` (v1)

### `/shared_learning`
Shared Learning case-based learning content (anonymized patient scenarios with learning outcomes).

Each item includes:
- `scenario` – Patient presentation
- `learningOutcomes` – Key learning points
- `clinicalKeys` – Diagnostic clues
- `references` – Educational sources

**Files**: ~20+ shared learning items

**Schema**: `schema/shared-learning-schema.json` (v1)

### `/schema`
JSON Schema definitions for all content types.

- **`assessment-schema.json`** (v3) – Validation rules for assessments; includes optional governed `assignments` map for category overrides
- **`guideline-schema.json`** (v1) – Guideline validation
- **`procedure-schema.json`** (v1) – Procedure validation
- **`scoring-tool-schema.json`** (v1) – Scoring tool validation with parity case fixtures
- **`blood-panel-schema.json`** (v1) – Blood panel validation with calculation case fixtures
- **`medication-schema.json`** (v1) – Medication validation
- **`prescribing-schema.json`** (v1) – Prescribing pathway validation
- **`shared-learning-schema.json`** (v1) – Shared Learning validation

Each schema has:
- `$id` pointing to raw.githubusercontent.com GitHub URL (for external validation tools)
- `title` – Human-readable name
- `description` – Purpose and usage notes
- `properties` – Field definitions with types and constraints
- `required` – Mandatory fields

**Important**: Each schema version is immutable. Schema changes create new versions (v2, v3, etc.).

### `/categories`
Taxonomy and category definitions.

- **`assessment-categories.json`** – Assessment taxonomy with semantic icon keys
  - `name` – Category display name
  - `iconKey` – Semantic icon identifier (e.g., `cardiology`, `neurology`)
  - `systemCode` – Optional medical coding system reference
  - `assignments` (optional) – Governed category assignments mapping assessment IDs to category IDs (overrides assessment JSON `categoryIds`)

Categories serve dual purposes:
1. **App grouping** – How assessments are organized in the app by category
2. **Icon/display** – Semantic icon meanings across CDM and the app

### `/references`
Central reference/citation registry.

- **`references.json`** – Single JSON object with:
  - Each key is a reference ID (GUID)
  - Each value has:
    - `title` – Citation title
    - `url` – DOI/URL to source
    - `organisation` – Publisher/journal name
    - `reviewStatus` – `current`, `review-due`, `superseded`, `withdrawn`, `unavailable`, `unverified`
    - `nextReviewDue` – Date for re-evaluation

**Important**: This is the source of truth for all citable references. Content must cite by ID; validation checks every reference exists.

**Usage**: `tool/validate_references.py` verifies that:
1. Every cited reference ID exists in this registry
2. (With `--strict`) Every cited reference has `reviewStatus: current` (blocks content shipping with withdrawn/unverified sources)

### `/glossary`
Shared clinical terminology dictionary.

- **`glossary.json`** – Definitions of clinical terms used in assessments and guidelines
  - `term` – Medical term or abbreviation
  - `definition` – Plain-language explanation
  - `relatedTerms` – Links to similar concepts

Used by inline glossary expansion in the app (`{{no-definition:...}}` tokens).

### `/attachments`
Governed binary files (images, PDFs, decision trees) referenced by content.

- **`assessments/`** – Images and documents used by assessment content (screenshots, diagrams)
- **`guidelines/`** – Guideline-specific attachments
- **`medications/`** – Drug structure images, interaction matrices
- **`scoring_tools/`** – Calculator visualizations
- **`blood_panels/`** – Lab result interpretation charts
- **`procedures/`** – Procedural diagrams, ultrasound images, video stills
- **`shared_learning/`** – Case study images, exam findings

Each file has:
- `path` – Relative path (e.g., `assessments/chest-pain/ekg.png`)
- `type` – Media type (image, pdf, video)
- `sha256` – File hash for integrity verification
- Used in content via structured metadata: `{"path": "assessments/...png", "sha256": "abc123...", "type": "image"}`

**Validation**: `tool/validate_content.py` checks:
1. File exists at declared path
2. SHA-256 matches (detects corruption)
3. File extension is allowed for type

### `/publication_reports`
Generated reports from the last publication cycle.

- **`manifest-report.json`** – Summary of content pack manifest generation
- **`validation-report.json`** – Results of full validation suite
- **`change-log.txt`** – Human-readable list of changes in this release

These are informational artifacts; never edited directly.

### `/tool`
Python validation and tooling scripts.

#### Core Validation
- **`validate_content.py`** – Validates all content JSON against schemas
  - Checks structure compliance
  - Verifies attachment integrity (SHA-256, path, type)
  - Resolves inline `{{attachment:...}}`, `{{image:...}}`, `{{no-definition:...}}` tokens
  - Cross-checks category IDs exist
  - Detects circular references
  - Reports content version incrementing (if `--base-ref origin/main` passed)

- **`validate_references.py`** – Validates reference registry and citation usage
  - Checks all references.json entries are well-formed
  - Verifies every cited reference ID exists
  - `--strict` mode: fails if any cited reference is not `current` (blocks shipping with withdrawn sources)

- **`validate_remote_engines.py`** – Tests scoring tool and blood panel calculations
  - Executes every `parityCases` and `calculationCases` fixture
  - Confirms app's remote-engine results match expected outputs
  - Catches calculation mismatches before publication

#### Generated Artifacts
- **`sync_manifest.py`** – Regenerates manifest.json deterministically
  - Computes SHA-256 of every schema and content file
  - Auto-bumps contentVersion on semantic changes
  - Computes minimum-app-version based on content features
  - Regenerates category assignments from `categories/assessment-categories.json`
  - `--write` commits changes; `--check` fails if uncommitted diffs exist
  - **Must be run before every publish** (canonical source of truth for file hashes)

- **`generate_reference_usage.py`** – Regenerates reference-usage.json (reverse index)
  - Maps reference IDs → which content items cite them
  - Used for impact analysis (e.g., "if I withdraw this reference, which assessments are affected?")
  - `--write` commits; `--check` fails if diffs exist

#### Safety & Governance
- **`validate_manifest_safety.py`** – Validates manifest.json safety controls
  - Checks `updatePolicy` (mandatory/optional update flags)
  - Checks `emergencyRevocations` (can block specific content versions)
  - Ensures no conflicting revocation rules

### `/app_config`
App-level configuration and feature flags.

- **`app-features.json`** – Feature Availability flags controlling which screens/features are visible in the Flutter app
  - Example: `medications_prescribing_beta` could gate a new prescribing pathway feature
  - Gated features are published to the app at install-time; not runtime-toggled

### `/.github/workflows`
GitHub Actions automation for CI/CD.

- **`assessments.yml`** – Main CI workflow
  - Triggered on push to main, PRs, and manual trigger
  - Runs validation suite read-only: `validate_content.py`, `validate_references.py --strict`, `validate_remote_engines.py`, `sync_manifest.py --check`
  - Fails if any validation fails or if working tree has uncommitted diffs
  - Enforces that `manifest.json` and `reference-usage.json` are always in sync

- **`generate-manifest.yml`** – Manual workflow for regenerating artifacts
  - Regenerates both `manifest.json` and `reference-usage.json`
  - Runs full validation on regenerated state
  - Commits only if validation passes and tree is clean
  - Pushes to default branch (only safe path for generated artifacts)

### Root-Level Configuration & Documentation

- **`manifest.json`** – Generated content-pack manifest (do NOT hand-edit)
  - Published to app at install-time
  - Contains per-item file path, SHA-256, size, minimum app version, category assignments
  - Enables app to verify downloaded content before activation
  - Regenerated by `sync_manifest.py --write`

- **`reference-usage.json`** – Generated reverse index (do NOT hand-edit)
  - Maps each reference ID → list of content items citing it
  - Used for impact analysis and workflow planning
  - Regenerated by `generate_reference_usage.py --write`

- **`CHANGELOG.md`** – Version history with feature notes
  - Entries are dated (e.g., 2026-09-15) not versioned
  - Documents schema changes, content additions, workflow improvements
  - Coordinated with CDM and app changelog entries

- **`README.md`** – Project overview, local setup, validation commands
  - Describes the repository's role in the platform
  - Lists all validation commands
  - Explains governance model

- **`CLAUDE.md`** – Development guidance for Claude Code
  - Architecture overview
  - Validation command reference
  - Schema structure explanation
  - Gotchas and edge cases

- **`.gitignore`** – Excludes generated files, caches, and temporary artifacts

---

## Publication & Governance Workflow

### Draft → Published Lifecycle
1. **Author (CDM)** creates/edits content draft
2. **Reviewer (CDM)** approves clinical content
3. **Clinical Validator (CDM)** confirms evidence and recommendations
4. **Publisher (CDM)** triggers publication:
   - Prepares JSON on `content-review/clinical-review` branch
   - Runs `validate_content.py` and `validate_references.py --strict`
   - Stages only expected content files
   - Commits to `content-review` branch
   - Creates GitHub PR; merges when checks pass
5. **CDA Repository** receives published commit on `main`
6. **CI (assessments.yml)** validates on push to main:
   - Full validation suite passes
   - Manifest/reference-usage are in sync (enforced by `sync_manifest.py --check`)
7. **Manual Workflow** (optional):
   - If manifest needs regeneration, run `generate-manifest.yml`
   - Regenerates, validates, commits atomically

### Emergency Revocation
If a published content item is found to be unsafe:
1. Publisher adds item ID to `manifest.json`'s `emergencyRevocations` map
2. Specifies revocation reason and effective version
3. App checks `emergencyRevocations` on startup; blocks revoked content versions
4. Content stays in repository (historical record); not deleted

---

## Important Implementation Patterns

### Content Addressing
- All content addressed by stable **ID** (primary key)
- Titles, summaries, versions are mutable; IDs never change
- Safe internal linking uses IDs: `@assessment:chest-pain`
- App navigation always by ID, never by version or title

### Version Semantics
- `version` field is semantic (e.g., `3.2.1`)
- Incremented only on **clinical change** (new section, different guidance)
- Not incremented on: metadata changes, attachment updates (those use separate attachment versioning)
- Tracked in manifest for app update policies

### Inline Content Tokens
- **`{{image:attachment-id}}`** – Assessment-only image inclusion (resolved to attachment metadata)
- **`{{attachment:attachment-id}}`** – Generic downloadable attachment link
- **`{{no-definition:term}}`** – Inline glossary expansion
- Token resolution fails validation if ID doesn't exist

### Reference Citation Patterns
- **Assessments/Guidelines**: use `references` array (reference IDs)
- **Scoring tools/Blood panels**: use `referenceIds` array (same concept, different field name)
- **Validation** checks both field names in both collections

### Cross-Schema Consistency
- All schemas use `$id` pointing to raw.githubusercontent.com for external tool validation
- All use consistent metadata patterns (id, title, version, clinicalValidation, attachments)
- Category assignments centralized in `categories/assessment-categories.json` (not per-item)

---

## Development Entry Points

| Goal | Start Here |
|------|-----------|
| Add a new assessment | Create new JSON file in `/assessments/`; follow existing schema; add version, clinicalValidation |
| Modify assessment schema | Edit `/schema/assessment-schema.json` version; bump version number (v4, v5); update validation tools if needed |
| Add assessment to category | Edit `/categories/assessment-categories.json` `assignments` map (governs which categories it appears in) |
| Create new content type | Create new schema in `/schema/*-schema.json`; create content directory; update `validate_content.py` + `sync_manifest.py` |
| Add blood panel | Create new JSON in `/blood_panels/`; include calculation cases for validation |
| Add scoring tool | Create new JSON in `/scoring_tools/`; include parity cases matching app's calculation engine |
| Update reference | Edit `/references/references.json`; update review status if needed; validation re-checks all citations |
| Run validation locally | Set up Python venv; run `tool/validate_content.py`, `tool/validate_references.py --strict`, `tool/validate_remote_engines.py` |
| Regenerate manifest | Run `.github/workflows/generate-manifest.yml` manually (only safe way to update manifest.json) |
| Publish content | In CDM, save draft → review → validate → publish; CDA CI will automatically validate on merge |
| Check schema compatibility | Run CI workflow locally or push to branch; validation will fail if schema changes break existing content |

