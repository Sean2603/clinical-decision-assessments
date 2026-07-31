# Clinical Decision Assessments

Version-controlled clinical assessment guidance for the Clinical Decision Support app.

## Structure

- `assessments/` — individual assessment guides
- `references/` — shared guideline references
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
