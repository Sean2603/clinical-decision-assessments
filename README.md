## CDA content version 0.0.22

Scoring tools and blood panels are now native governed CDA content rather than shadow copies of Flutter clinical screens.

- **22 scoring tools/pathway references** are governed in `scoring_tools/`.
- **15 blood panels** are governed in `blood_panels/`.
- Calculator evaluation and parity cases remain executable through the shared remote engine contract.
- Blood calculations may declare explicit `inputs[]` IDs/labels for generic App rendering.
- The Flutter App catalogue is derived from the manifest; adding or withdrawing supported CDA items no longer requires a Dart catalogue edit.


### Shared Learning content contract

CDA 0.0.22 adds an optional governed `sharedLearning` manifest collection backed by `shared_learning/` and `schema/shared-learning-schema.json`. Approved resources can contain learning points, references, governed attachments and embedded clinical-validation metadata. Quarantined App submissions remain in CDM and are not CDA content until they complete governance and repository publication. The medication schema also supports optional `bnfLookupName` for external BNF source-name differences.

# Clinical Decision Assessments

Governed clinical-content repository for the **Clinical Decision Support** platform.

This repository is the source-controlled publication target for clinical content managed through the **CDM Content Manager**. It contains the structured JSON delivered to the clinical application, the schemas used to validate that content, the shared reference registry, generated publication metadata, and repository-level validation tooling.

> **Clinical content should normally be authored, reviewed, validated and prepared for publication through CDM.** Direct repository editing is reserved for repository maintenance, tooling, schema changes, recovery, or exceptional administrative work.


## Medication safety content contract

Medication monographs use structured safety content for newly governed publications:

- `interactions[]` contains `drug`, `description`, nullable `severity` and nullable `evidence`;
- `sideEffects[]` groups individual `effects` under a required `frequency`; and
- each published side-effect group must contain at least one effect.

This contract is supported by CDM 0.41.0 and Flutter app 0.51.0+78. The manifest therefore declares `minimumAppVersion: 0.51.0`. Existing medication files were migrated with empty `sideEffects` arrays so the schema change does not invent clinical content.

## Repository role

The repository has two distinct responsibilities:

1. **Clinical source of truth** — version-controlled clinical content and references.
2. **Publication boundary** — the Git state used to determine whether a governed item is actually published.

CDM owns the governance workflow. GitHub provides source control, review history, branch protection and the final repository-confirmed publication state.

An item is not considered **Published** merely because CDM has created an internal publication snapshot. It becomes Published when the exact governed version is present on the protected `main` branch.

## Branch model

### `main`

`main` is the authoritative governed publication branch.

Normal clinical editing should not occur directly on `main`.

### `content-review/clinical-review`

CDM uses a reusable review branch:

```text
content-review/clinical-review
```

Typical publication flow:

```text
CDM governed content
        ↓
Ready to publish
        ↓
Prepare review branch
        ↓
content-review/clinical-review
        ↓
Repository validation
        ↓
Pull request / controlled merge
        ↓
main
        ↓
Repository-confirmed Published
```

## CDM governance workflow

The active workflow is:

```text
Draft
  ↓
Awaiting review
  ↓
Awaiting clinical validation
  ↓
Ready to publish
  ↓
Repository publication preparation
  ↓
Repository-confirmed Published
```

### Draft

Content can be created or revised by an authorised author/editor.

### Awaiting review

An independent reviewer assesses the content and either progresses it or requests field-specific changes. Requested changes must be actioned before resubmission.

### Awaiting clinical validation

Clinical validation confirms that the content is clinically suitable for publication. The current validation state is stored with each item using embedded `clinicalValidation` metadata. The former standalone Clinical Reliability registry is no longer part of the active governance model.

### Ready to publish

The item has completed internal governance but is not yet considered live.

### Published

Published means the exact governed content version is present on `main`. Internal CDM snapshots, local commits, review branches or open pull requests are intermediate states only.

## Separation of duties

The intended governance model separates:

- **Author** — creates the original content;
- **Revision author** — intentionally starts a substantive new revision cycle;
- **Editor** — changes content within an active cycle;
- **Reviewer** — independently reviews content;
- **Clinical validator** — provides clinical validation;
- **Publisher/governance authority** — performs repository publication actions.

The original author remains part of the permanent content history. Professional role is captured separately from application permissions so historical actions retain the role held at the time.

## Content versioning

Individual governed content uses semantic versions:

```text
major.minor.patch
```

Patch increments represent iterative review/edit rounds within a cycle, minor increments represent normal post-publication revision cycles, and major increments are used for major rewrites or explicitly promoted final-major publications.

Examples:

```text
0.1.0 → 0.1.1 → 0.1.2
0.1.x → 0.2.0
0.4.13 → 1.0.0
```

## Repository structure

```text
assessments/        Clinical assessment guides
attachments/        Governed clinical attachments
blood_panels/       Blood-test interpretation content
categories/         Assessment category definitions
glossary/           Shared governed clinical glossary
guidelines/         Clinical guideline content
medications/        Medication monographs
prescribing/        Condition-based prescribing pathways
references/         Shared reference registry
scoring_tools/      Structured clinical scoring tools
schema/             JSON schemas
tool/               Repository validation/generation tools
manifest.json       Generated content-pack manifest
reference-usage.json
                    Generated reverse-reference index
```

Managed content collections may legitimately contain zero items.

## Shared references

The authoritative reference registry is:

```text
references/references.json
```

Clinical content references sources using stable reference IDs. The generated reverse-reference index is:

```text
reference-usage.json
```

Reference verification and publication are separate governance concepts. A newly verified reference is not fully publication-ready until the governed registry has itself completed publication.

## Glossary

The repository contains a governed shared clinical glossary under `glossary/`. Terms can contain canonical wording, aliases, definitions, examples, related terms and reference IDs.

## Attachments

Governed files are stored under `attachments/`. Supported content can reference attachments using structured metadata including repository path and SHA-256 hash. Clinically meaningful replacements should use controlled replacement governance and return the parent content to the required review/validation state.

## Manifest

`manifest.json` describes the publishable content pack and includes schema version, overall content-pack version, minimum supported app version, content entries, paths, schemas, hashes and safety controls.

### `schemaVersion`

Describes the manifest structure itself.

### `contentVersion`

Describes the overall generated content pack. Individual items retain their own semantic versions.

## Generated artefacts

The main generated artefacts are:

```text
manifest.json
reference-usage.json
```

These should be produced by controlled tooling rather than maintained manually.

## Repository tooling

Maintained tools:

```text
tool/generate_reference_usage.py
tool/parity_case_baseline.json
tool/sync_manifest.py
tool/validate_content.py
tool/validate_manifest_safety.py
tool/validate_references.py
tool/validate_remote_engines.py
```

### Local Python environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install jsonschema
```

The virtual environment does not need to be activated if its Python executable is called directly.

### Local validation sequence

```bash
.venv/bin/python tool/generate_reference_usage.py
.venv/bin/python tool/sync_manifest.py --write
.venv/bin/python tool/validate_references.py
.venv/bin/python tool/validate_content.py
.venv/bin/python tool/validate_manifest_safety.py
.venv/bin/python tool/sync_manifest.py --check
```

For a review branch where version progression must be checked against the current published baseline:

```bash
.venv/bin/python tool/validate_content.py --base-ref origin/main
```

## GitHub Actions

GitHub Actions provides repository-level technical validation in addition to CDM governance. It should validate clinical JSON and references, verify generated artefacts, enforce version progression against `main` for review pull requests, and remain read-only during ordinary validation.

Technical validation does not replace clinical review or clinical validation in CDM.

## Publication workflow in detail

1. **Author/edit in CDM** — content is created or revised and user identity/professional role are recorded.
2. **Submit for review** — content moves from Draft to Awaiting review.
3. **Independent review** — reviewer progresses the item or requests structured changes.
4. **Clinical validation** — authorised validator completes clinical validation.
5. **Ready to publish** — the governed version becomes repository-publication eligible.
6. **Prepare repository publication** — CDM writes the exact governed files to `content-review/clinical-review` and regenerates controlled artefacts.
7. **Validate and commit** — repository validation runs and the prepared changes are committed.
8. **Repository review / pull request** — the review branch is compared with `main` and GitHub validation must pass.
9. **Merge to `main`** — controlled changes enter the authoritative publication branch.
10. **Repository confirmation** — CDM verifies the exact governed version exists on `main`; only then is it Published.

## Permanent deletion

Permanent deletion is a separately audited governance action rather than a normal content edit. It should verify dependencies, remove the governed file, regenerate generated artefacts, validate the repository, create a dedicated deletion commit on the review branch, pass through repository publication and record actor/reason/commit metadata.

Failed deletion transactions should roll back rather than leaving unexplained dirty working-tree state.

## Superseding, withdrawing and emergency safety controls

Published content should normally be withdrawn or superseded through governance rather than physically deleted. Superseding should explicitly identify the governed replacement.

Emergency disable/revocation is separate from routine lifecycle governance and is intended for urgent clinical-safety action. Emergency actions should remain explicit, attributable and auditable.

## Repository integrity and recovery

CDM repository operations should:

- begin from a known branch and clean state;
- preserve unrelated local changes;
- treat generated artefacts as CDM-controlled;
- restore CDM-touched generated artefacts after failed preparation;
- verify cleanliness after rollback;
- report exact recovery paths when automatic cleanup fails;
- never mark content Published until repository state is confirmed.

## Direct Git editing

Direct Git editing should generally be limited to repository tooling, schemas, workflows, documentation, controlled recovery and exceptional administration. Routine clinical content editing should occur through CDM so authorship, review, validation, versioning and audit history remain intact.

## Responsibilities

### CDM Content Manager

CDM is responsible for authentication, permissions, professional-role snapshots, authorship, editing, requested changes, review, clinical validation, versioning, reference/glossary governance, publication readiness, controlled repository preparation, audit history and publication-state reconciliation.

### This repository

The repository is responsible for version-controlled clinical JSON, schemas, references, attachments, deterministic generated metadata, repository validation, Git history, branch comparison and the final repository-confirmed publication state.

### Clinical Decision Support application

The consuming application is responsible for retrieving the published pack, validating expected hashes/schema compatibility, caching/activating content safely, enforcing minimum app versions and respecting applicable safety controls.

## Fresh baseline

The repository has been deliberately rebaselined to establish a clean governance starting point. Historical development versions should not be used to infer current CDM governance state.

From this baseline onward:

```text
main = authoritative governed publication branch
```

Normal governed changes should progress through CDM and the controlled review branch before reaching `main`.


## Nullable reference publication dates

A reference with no discrete publication date may use `published: null`. This is intended for continuously updated online resources. `accessed` remains mandatory and `lastUpdated` should be used when a reliable source update date is available.
