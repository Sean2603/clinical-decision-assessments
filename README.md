# Clinical Decision Assessments

Version-controlled clinical assessment guidance for the Clinical Decision Support app.

## Structure

- `assessments/` — individual assessment guides
- `references/` — shared guideline references
- `scoring_tools/` — remote scoring-tool shadow definitions
- `blood_panels/` — remote blood-panel shadow definitions
- `schema/` — JSON schema
- `manifest.json` — published pack metadata and checksums
- `tool/build_manifest.py` — rebuilds checksums and publication date
- `.github/workflows/` — validation and manifest publication

## Editing workflow

1. Create a branch.
2. Edit the relevant assessment JSON.
3. Increase the assessment version and pack `contentVersion`.
4. Open a pull request.
5. Confirm the validation workflow passes.
6. Complete clinical review.
7. Merge to `main`.
8. The manifest workflow recalculates checksums.

The app checks the raw GitHub manifest in the background no more than once every
24 hours. Manual checks are available in Settings.


## Shared references

`references/references.json` is the authoritative registry for assessments, scoring tools and blood panels. `clinical_reliability/clinical-reliability.json` stores clinical review metadata and stable `referenceIds`; it does not duplicate source records.


## Clinical guidelines

Guidelines are stored in `guidelines/*.json`, validated against
`schema/guideline-schema.json`, and published through the same `manifest.json`
as assessments, references and clinical-reliability metadata.

Run before committing:

```powershell
python tool/validate_content.py
python tool/validate_clinical_reliability.py
python tool/validate_references.py
python tool/generate_reference_usage.py
python tool/sync_manifest.py
```


## Remote scoring tools and blood panels

`scoring_tools/*.json` and `blood_panels/*.json` now contain shadow copies of
the clinical definitions currently implemented in Flutter. The app downloads,
checksums, parses and caches these files as part of the same atomic content
pack, but version `0.18.0` continues to render the existing Dart screens.

Each migrated definition includes a `migration` block:

```json
{
  "state": "shadow",
  "sourceFile": "lib/screens/phase_one_tools.dart",
  "currentScreen": "Crb65Screen",
  "parityStatus": "pending",
  "migratedOn": "2026-08-01"
}
```

Do not mark `parityStatus` as `matched` until the remote definition has been
compared with the current Dart implementation and its tests.

The shared reference registry and clinical reliability file remain
authoritative. Every scoring-tool and blood-panel definition must have a
matching reliability item with the same stable ID and display title.

### Review-due references

A cited reference with `reviewStatus: review-due` no longer blocks publication. During publishing, `tool/mark_review_due_content.py` marks each affected assessment, scoring tool, or blood panel with `clinicalValidation.validated: false`, clears previous reviewer metadata, records the affected reference IDs in `reviewNotes`, and bumps the item patch version. Superseded, withdrawn, unavailable, and unverified cited references still block publication.
