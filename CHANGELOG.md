## 1.1.23 - 2026-08-04

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
