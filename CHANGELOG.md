## 2026-10-06 – Governed single-criterion escalation for scoring tools

- `schema/scoring-tool-schema.json`: new optional top-level `escalations` array (default `[]`). Each item (`additionalProperties: false`) requires `id`, `whenAnyCriterionScoresAtLeast` (number), `fromResultIds` (unique result IDs, at least one) and `toResultId`. It expresses rules that score bands cannot, such as the NEWS2 single-parameter "red score": an aggregate of 1–4 is low, but any single parameter scoring 3 needs an urgent ward-based (low–medium) response.
- Semantics, identical in `tool/validate_remote_engines.py` (`evaluate_scoring`) and the app engine:
  - Applies only to `sum` and `required-sum` evaluations, never to a required-sum prerequisite-failure result.
  - Triggers when any single scored criterion contributes at least the threshold. Scored criteria are taken after the NEWS2 SpO2-scale filter, and omitted optional criteria are skipped.
  - Applies only when the band selected by score is in `fromResultIds`. The first matching escalation in array order wins.
  - The score is unchanged; only the result changes. `toResultId` is resolved within the active alternate mode's results first, then the tool's `results`.
  - Bands are still chosen first-match in array order, so an escalation-only band (e.g. NEWS2 `low-medium`) can carry a score range shadowed by an earlier band.
- `tool/validate_content.py` rejects an escalation whose `toResultId` or `fromResultIds` does not resolve to a result on the tool or one of its alternate modes. It also rejects escalations on an evaluation kind that ignores them (anything but `sum`/`required-sum`). This mirrors the app's `ClinicalContentValidator.validateScoringTool`. The parity engine also fails an unresolved escalation target.
- `tool/sync_manifest.py`: any scoring tool with a non-empty `escalations` array raises the pack `minimumAppVersion` to at least 0.76.3. Older builds ignore the field and would under-triage. No current content uses escalations, so the manifest `minimumAppVersion` is unchanged (0.64.3); `manifest.json` was regenerated only for the new schema hash.
- `tool/sync_manifest.py` again publishes clinical notices. The 2026-08-12 entry says notices in `clinical_notices/clinical-notices.json` are included in the generated manifest, but the generator had stopped emitting them, so authored notices could never reach the app (which reads `manifest.clinicalNotices`). `clinicalNotices` is now a generated key: the file's `notices` array, or `[]` when there is no file. The current manifest gains an empty `clinicalNotices`, which bumps `contentVersion` to 0.0.66.
- No content changed. `scoring_tools/news2.json` is deliberately untouched: the NEWS2 low–medium band and red-score escalation are to be authored and clinically validated through CDM.
- Coordinated with Flutter app 0.76.3. That release parses and applies `escalations`, shows the escalated band in the scoring panel and copied summary, and validates escalation result IDs on pack load. In the same release the app reports the true maximum score (e.g. PE Wells 12.5, not 20) and shows a required-sum prerequisite failure (PERC "not yet applicable") in a neutral tone without its sentinel score. Those app-only fixes need no CDA change.

## 2026-10-06 – Scoring/blood engine schema contract and app-parity validation

- Differential-fuzzing follow-up (2026-10-06): closed gaps where CDA validation diverged from, or was looser than, the Flutter app:
  - `tool/validate_remote_engines.py`: calculation `precision` rounding now mirrors the app's `(value * 10^p).roundToDouble() / 10^p` (half away from zero after scaling) instead of Python's `round()`, which disagreed on values such as corrected calcium 4.0/14.75 (app 4.51), osmolality 131/15.15/63 (app 340.2) and osmolal gap 208.95/464.2 (app -255.3). The expression tokenizer now skips whitespace anywhere (trailing whitespace was wrongly rejected), accepts only ASCII digits (non-ASCII digits such as `٣` were accepted), and pathologically deep nesting fails as a validation error instead of crashing.
  - `schema/scoring-tool-schema.json`: a `between` rule must have a numeric `upperValue` (the app cannot evaluate it otherwise). `schema/blood-panel-schema.json`: calculation `precision` is capped at 6.
  - `tool/validate_manifest_safety.py` now type-checks `updatePolicy` and `emergencyRevocations` against the app's hard casts: string fields, boolean `blockClinicalContentUntilUpdated`, `X.Y.Z` string or null `affectedVersions.minimum`/`maximum`, and Dart-parseable ISO-8601 or null `effectiveFrom`. A revocation `contentType` must be one the app uses (`assessment`, `guideline`, `procedure`, `scoring-tool`, `blood-panel`, `medication`, `prescribing`). `contentId` is not required to exist, so an item already removed from CDA can still be revoked on devices.
  - `tool/validate_content.py` fails if any repository `*.json` file contains a carriage return byte. The app hashes the raw bytes, but `sync_manifest.py` hashes LF-normalised text.
  - No content changed. `manifest.json` was regenerated for the new schema hashes.
- Coordinated with Flutter app 0.76.1+133, which adds a contract test that loads this repository through the app's own parsers, validators and engines.
- `schema/scoring-tool-schema.json`: `evaluation` is now a defined `$defs/evaluation` object instead of an unconstrained `object`. It requires `kind` (`none`, `sum`, `required-sum`, `group-count`, `decision`), `scoreCriteria`, `requiredTrue`, `failureResultId`, `failureScore`, `groups` and `decisionRules`, and `required-sum` must carry a failure result and score. Previously `"evaluation": {}` was schema-valid but would have made the app reject the whole pack.
- `schema/blood-panel-schema.json`: calculation `engine` is now a defined `$defs/calculationEngine` object. It requires `kind` (`expression`, `acid-base-basic`, `aki-creatinine-stage`), `expression`, `precision` and numeric `parameters`, with optional string `textResults`. An `expression` engine must have an expression.
- All existing content already conforms; no content file changed. `manifest.json` was regenerated for the new schema hashes.
- `tool/validate_content.py` now rejects conditions that previously passed CDA validation but would make the app reject the pack or drop content:
  - a medication regimen linking to a `withdrawn` prescribing pathway;
  - a `url` prominent resource that is not an absolute http(s) URL;
  - a procedure step `imageAttachmentId` that does not resolve to an image attachment on the same procedure.
- `tool/validate_content.py --base-ref` now also enforces version increases for `shared_learning/`.
- `tool/validate_remote_engines.py` now mirrors the app scoring engine so parity cases test the same semantics:
  - `alternateModes` (e.g. CRB-65 when urea is omitted);
  - optional (`required: false`) criteria;
  - rejection of a missing answer to a required criterion, where it previously scored 0;
  - NEWS2 `o2-scale-selector` scoring only the selected SpO2 scale;
  - unknown result IDs.
- Updated `COMPATIBILITY.md`: specimens are rendered by the app, and the app contract test is documented.

## 2026-09-29 – Repository documentation and developer guidance

- Added FILE_STRUCTURE.md documenting directory structure, file responsibilities, validation workflows, and publication governance.
- Consolidated documentation patterns across the three-repo platform for consistency and clarity.
- Enhanced developer onboarding materials with detailed entry points and architecture explanations.
- No clinical content, validation, or schema changes in this documentation update.

## 2026-09-15 – Expanded assessment clinical-system taxonomy icons

- Added semantic icon keys for `ent`, `eye`, `genitourinary`, `womens-health` and `musculoskeletal` while retaining legacy `bone` compatibility.
- ENT now publishes `iconKey: ent` instead of the generic fallback.
- Added governed category definitions for `cardiology`, `neurology` and `musculoskeletal`, which are already referenced by assessment source metadata and therefore must remain resolvable during repository validation even when v3 taxonomy assignments override app grouping.
- Empty future systems such as eye, genitourinary and women's health remain available as icon keys and can be created through CDM when first required; the app hides empty assessment categories.
- Coordinated with CDM 0.57.11 and Flutter app 0.64.9+112.
- `manifest.json` remains generated; from the current 0.0.40 pack these taxonomy/schema changes are expected to produce contentVersion 0.0.41 when CDM performs the controlled publication generation.

## 2026-09-15 – GitHub Actions validation and generation alignment

- Expanded the main validation workflow trigger paths to cover all current governed CDA content/configuration families, attachments, generated artefacts and both workflow definitions.
- Added `tool/validate_remote_engines.py` to ordinary validation so scoring-tool and blood-calculation parity cases are enforced in CI.
- Replaced the partial source-directory mutation check with a whole-working-tree read-only assertion after generated reference-usage verification.
- Upgraded the manual generated-artefact workflow to regenerate both `manifest.json` and `reference-usage.json`, run strict references and remote-engine validation, stage only controlled generated artefacts, and reject unexpected source mutations.
- The manual workflow now commits generated artefacts locally, reruns the complete validation set against that committed state, verifies a clean/reproducible tree, and only then pushes the generated commit.
- No clinical content contract or Flutter compatibility change is introduced by this workflow-only update.

## 2026-09-15 – Governed assessment category assignments

- Extended the assessment category document with an optional governed `assignments` map keyed by assessment stable ID.
- `tool/sync_manifest.py` now uses taxonomy assignments for manifest assessment `categoryIds` when the map is present, with the existing assessment JSON field retained as the backwards-compatible fallback.
- Manifest generation rejects unknown category IDs and assignment entries for assessments that do not exist.
- Category-only publications can therefore update app grouping without rewriting or re-versioning otherwise unchanged clinical assessment JSON.
- Coordinated with CDM 0.57.9. Existing app manifest structure is unchanged, so no new Flutter release is required for this fix.

## 2026-09-15 – Governed assessment category icons

- Raised `categories/assessment-categories.json` to category document schema version 2.
- Added required semantic `iconKey` metadata to assessment categories so CDM and the Flutter app can render the same governed category meaning without framework-specific icon names in CDA.
- Added the supported semantic icon-key enum to `schema/assessment-categories-schema.json`.
- Existing Frailty, ENT and Uncategorised categories retain their IDs/order/description; this is presentation metadata only and does not change assessment assignments or clinical content.
- Coordinated with CDM 0.57.8 and Flutter app 0.64.8+111.
- `manifest.json` remains generated; regenerate it through the normal controlled writer after applying these files.

## 2026-09-10 – Inline-only assessment media compatibility

- Reserved attachment label `__inline_only__` for governed assessment image attachments inserted directly into clinical text by CDM.
- Repository validation requires inline-only assets to be images, limits them to assessments, and requires each one to be referenced by an assessment `{{image:...}}` token.
- Manifest generation raises `minimumAppVersion` to at least `0.63.7` when published assessment content contains inline-only media so older builds cannot expose those images again in the generic Attachments card.


## App feature availability

Production/tester feature visibility is governed by `app_config/feature-availability.json` and `schema/app-feature-availability-schema.json`. The known feature IDs are assessments, bloods, scoring-tools, guidelines, medications, prescribing, cpd-hub, notes and todo. `enabled` and `hidden` are the currently valid states. CDM publication updates the manifest descriptor; malformed, duplicate or unknown feature definitions fail validation. Development builds continue to expose all features by default.

## 2026-09-09 – Inline assessment image token tooling

- Added repository validation for assessment `{{image:attachment-id}}` and `{{image:attachment-id|Caption override}}` tokens.
- Image tokens must resolve to an attachment on the same assessment and that attachment must have `type: "image"`.
- Image tokens are currently rejected outside assessment content so unsupported content types cannot publish tokens the App does not render.
- Manifest generation now raises `minimumAppVersion` to at least `0.63.5` whenever published assessments contain an inline image token, preventing older App builds from receiving unsupported token syntax.
- The assessment JSON schema is unchanged because the token is embedded in existing governed string fields and resolves through the existing `attachments` model.

## 0.0.22 - 2026-08-30

- Added optional `sharedLearning` manifest collection and `shared_learning/` repository directory.
- Added Shared Learning schema with learning points, references, governed attachments and clinical validation.
- Extended content/reference/reference-usage validation tooling for Shared Learning.
- Added optional medication `bnfLookupName` for BNF source-name differences.
- Retained manifest SHA-256 hashes as the authority for selective App download/reuse decisions.

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
