## 0.0.17 - 2026-08-28

### Individual blood-test navigation metadata

- Added optional navigation metadata to individual blood-test rows.
- Each test can independently opt into the App jump menu and provide an optional navigation label.
- Existing blood rows default to `showInJumpTo: false`; section-level navigation is unchanged.

## 0.0.16 - 2026-08-28

### Blood-panel navigation, calculator input constraints and U&E AKI

- Added section navigation metadata (`showInJumpTo` and optional label) to the blood-panel contract and all governed blood sections.
- Added numeric calculator input constraints: minimum, maximum, decimal precision, unit and validation message.
- Added broad plausibility guardrails to existing executable blood calculators, including pH input validation.
- Added a creatinine-based AKI warning-stage calculator within Urea & Electrolytes, with executable parity cases.
- U&E, ABG/VBG, calcium/minerals and serum osmolality now require App 0.57.0 where new calculator behaviour is clinically relevant.
- The AKI implementation is creatinine-only and explicitly does not replace urine-output criteria, RRT criteria or clinical assessment.

## 0.0.14 - 2026-08-28

### Native CDA scoring and blood catalogue

- Added governed definitions for the ten scoring/reference tools that previously existed only as hard-coded Flutter screens: CRB-65, Canadian C-spine rule, ADD-RS, HEART, DECAF, NICE head-injury pathway, Canadian CT Head Rule, EDACS, Glasgow-Blatchford and Canadian Syncope Risk Score.
- The scoring catalogue now contains 22 governed definitions.
- Added executable parity cases for the five newly governed calculators.
- Marked scoring and blood migration metadata as native/matched now that the Flutter app renders them directly from CDA.
- Added explicit optional calculation input metadata for governed blood calculations while retaining existing engine/parity definitions.
- Completed ABG/VBG text-result coverage for every executable acid-base engine outcome and added parity cases for compensated and mixed patterns.
- CDA remains authoritative for the scoring-tool and blood-panel catalogues.

## 0.0.11 - Nullable reference publication dates

- Reference schema now permits `published: null` for continuously updated online resources that have no discrete publication date.
- Supplied publication dates remain ISO date validated.
- Minimum compatible app version is 0.52.0.

## 2026-08-28 – Native structured medication interactions and side effects

- Expanded `schema/medication-schema.json` so medication interactions are governed objects with `drug`, `description`, `severity` and `evidence`.
- Added required grouped `sideEffects` with `frequency` and one or more `effects`.
- Added empty `sideEffects` arrays to existing medication monographs as a schema migration without changing their clinical meaning.
- Raised `minimumAppVersion` to `0.51.0` because newly published medication content can use structures not understood by earlier app releases.
- Regenerated the manifest as contentVersion `0.0.10` with updated medication-schema hashes.
- Coordinated with CDM 0.41.0 native publication and Flutter app 0.51.0+78 parsing/rendering.

## Attachment model cleanup

- Retired the legacy `images` schema field and image-specific attachment definitions.
- Generic `attachments` is now the only clinical attachment field.
- Removed legacy image validation while retaining generic attachment path/hash/governance validation.

## Inline attachment references

- Added repository validation for `{{attachment:id}}` and `{{attachment:id|Custom label}}`.
- Publication fails if an inline token does not resolve to an attachment on the same content item.

## Clinical Attachments v2

- Added governed `attachments` metadata for images, PDF, DOCX, XLSX, CSV, PPTX, TXT and Markdown files.
- Added attachment path/hash/reference/replacement-governance validation.
- Retained legacy `images` support during migration.

## Clinical image attachments v1

- Added optional governed image attachments to assessments, guidelines, scoring tools, blood panels, medications, prescribing pathways and clinical notices.
- Added versioned image metadata including SHA-256, MIME type, dimensions, source/reference linkage and upload attribution.
- Added replacement-governance metadata and validation.
- Clinically meaningful replacements now require revalidation and cannot be published while the parent content remains validated.
- Image replacements must use a new path and retain the previous image in the repository.

## 2026-08-11 – Medication / prescribing split
- Split medicine monographs into `medications/` and reserved `prescribing/` for condition-based treatment pathways.
- Added separate JSON schemas and manifest collections for both content types.
- Prescribing regimens can reference medication monographs by stable medication ID.

# Changelog

## 1.2.22 — 2026-08-11

### Added
- Added first-class `prescribing/` repository support for APUC medicine monographs.
- Added `schema/prescribing-schema.json` aligned with app 0.33.0 and CDM prescribing content.
- Extended manifest generation, content validation, embedded clinical-validation checks, reference validation and reference-usage generation to prescribing content.
- Added prescribing files to GitHub Actions validation and read-only source-integrity checks.
- Added review-due reference handling for prescribing medicine monographs.

### Changed
- Manifest generation now emits a deterministic `prescribing` collection.
- `minimumAppVersion` rises to at least `0.33.0` only when one or more prescribing monographs are actually published, and the generator will never lower an existing higher minimum app version.


## Lifecycle schema migration - 2026-08-08

- Add explicit `status` lifecycle support to assessments so normal withdrawal no longer depends on `emergencyRevocations`.
- Add optional `unitless` metadata to blood-panel rows; unitless rows retain a blank `unit` string.
- Add `tool/migrate_content_lifecycle_v2.py` to migrate existing assessment status, legacy unitless rows, duplicate withdrawal revocations and minimum app compatibility without overwriting unrelated schema fields.
- Require app 0.32.0 or later for packs using assessment lifecycle status.
- Keep GitHub Actions read-only: the exact PR head is validated before merge and `main` is validated again after publication.
## 1.1.26 - 2026-08-05

### Changed
- Standardised all five Frailty guides to the established assessment layout.
- Separated history prompts, acute deterioration and red flags, focused examination, common clinical patterns, management and disposition, and focused safety-netting.
- Removed standalone documentation sections from the main visual flow and incorporated documentation prompts into management and disposition.
- Updated Frailty Assessment to version 0.3.0 and the four focused Frailty guides to version 0.2.0.

## 1.1.23 - 2026-08-04


## 1.1.24 - 2026-08-04

### Added
- Added the first complete Frailty clinical package.
- Added Falls in Older Adults.
- Added Acute Confusion and Delirium.
- Added Comprehensive Geriatric Assessment.
- Added Polypharmacy and Medicines-Related Harm.
- Added NICE NG5 and British Geriatrics Society CGA references.

### Changed
- Updated the umbrella Frailty Assessment to version 0.2.0 and aligned its emergency safety-netting wording.
- Marked all new Frailty package guides as requiring clinical validation.

- Added assessment category schema and manifest metadata.
- Assigned Frailty Assessment to the Frailty subsection.
- Added validation for category identifiers and an Uncategorised fallback.

# Changelog

## 1.1.15 — 2026-08-01

- Added 22 remote scoring-tool shadow definitions migrated from the current
  Flutter screens.
- Added 15 remote blood-panel shadow definitions migrated from the current
  Flutter screens.
- Added JSON schemas for scoring tools and blood panels.
- Extended the shared manifest, checksum publication and reference-usage
  report to include scoring tools and blood panels.
- Added cross-validation between remote definitions and clinical reliability
  metadata.
- Set the minimum app version for the expanded pack to `0.18.0`.
- Retained `parityStatus: pending` for all migrated definitions until formal
  comparison against the current Dart behaviour is complete.

## 1.1.0 — 2026-07-27

- Added the initial Back Pain clinician prompt.
- Added history and serious-pathology prompts.
- Added examination technique, normal findings, abnormal findings and implications.
- Added common examination patterns and NICE-linked imaging guidance.
- Added focused Back Pain safety-netting.
- Added shared references, schema validation and manifest checksums.

## Reference review-due publication handling

- Allow cited references with `reviewStatus: review-due` to publish with warnings.
- Continue blocking cited references that are superseded, withdrawn, unavailable, or unverified.
- Automatically mark affected assessments, scoring tools, and blood panels as clinically unvalidated before publication.
- Clear prior reviewer metadata, add a review-due note, and bump the affected content item version.

## Medication, prescribing and notice metadata (2026-08-12)
- Medication monographs now support aliases and update metadata for search and Updates & Notices.
- Prescribing pathways now declare a clinical system separately from the condition/category and can cross-link regimen medication IDs.
- Clinical notices are managed in `clinical_notices/clinical-notices.json` and are included in the generated manifest.
- The APUC 17-medicine starter formulary is present as clinically unvalidated medication content where a validated monograph has not yet been completed.
