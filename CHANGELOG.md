## 1.2.1

- Removed the duplicate `clinical_reliability/clinical-reliability.json` catalogue and schema.
- Made embedded `clinicalValidation` authoritative for every clinical content type.
- Added `nextReviewDue` to clinical-validation metadata.
- Set review intervals to one year for guidelines and two years for assessments, scoring tools and blood panels.
- Raised the minimum compatible app version to 0.31.0.

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
