# Cross-Repo Compatibility Guide

Three repos form the Clinical Decision Support platform. Changes to core contracts require updates across multiple repos.

## Repo Responsibilities

| Repo | Role | Source of Truth |
|------|------|-----------------|
| **clinical-decision-assessments (CDA)** | Schemas & published content | JSON schemas in `/schema` |
| **cdm-content-manager (CDM)** | Authoring tool | Generates CDA-compliant content |
| **clinical-decision-app** | Consumer | Parses & renders CDA content |

## Change Impact Matrix

### When CDA schemas change (e.g., scoring-tool-schema.json)

**Required updates:**
- [ ] **CDM**: Update content generation to produce valid data per new schema
- [ ] **App**: Update fromJson parsers to handle new fields/structure
- [ ] **Versioning**: Increment app `minimumAppVersion` in schema if app cannot handle old format
- [ ] **All repos**: Update CHANGELOG with coordination note

**Example:** Adding a new field to scoring tool evaluation
```
CDA schema/scoring-tool-schema.json: Add "newEvaluationMode" property
CDM: Update tool editor to capture new field, generation templates
App: Update RemoteScoringEvaluation.fromJson, evaluateScoring() logic
```

### When CDM output format changes

**Required updates:**
- [ ] **CDA**: Update schema if new fields/structure not already defined
- [ ] **App**: Test pack validation with new CDM output
- [ ] **All repos**: CHANGELOG coordination note

### When App adds content-consumption feature

**Required updates:**
- [ ] **CDA schema**: Add or extend schema to support feature
- [ ] **CDM**: Update content editor/generator for new schema fields
- [ ] **App**: Implement feature + pack validation
- [ ] **All repos**: CHANGELOG coordination note

## Testing Cross-Repo Changes

Before merging changes to core contracts:

1. **App**: Run `flutter test` — verifies parsing with test fixtures
   - `test/cda_contract_test.dart` loads a real CDA checkout (`CDA_REPO_PATH` or sibling `../clinical-decision-assessments`) through the app's pack loader. It also re-parses every document stripped to its schema-required fields and with every nullable field set to null. Run it with your CDA branch checked out before merging a schema change.
2. **App**: Run parity validation — `RemoteClinicalDefinitionEngine.validateCatalog()` executes embedded test cases
3. **Manual**: Generate sample content in CDM, validate against App using latest pack

## Files Requiring Cross-Repo Review

**If you modify these, check all 3 repos:**

| File | Repo | Impact |
|------|------|--------|
| `schema/*.json` | CDA | App parsers + CDM generators |
| `*_test.dart` (models) | App | Document contract expectations for CDM |
| `remote_clinical_definitions.dart` | App | Core parsing — notify CDM |
| `manifest.json` structure | CDA | CDM must generate compatible packs |
| `RemoteScoringToolDefinition` | App | CDM output + CDA schema alignment |
| `RemoteBloodPanelDefinition` | App | CDM output + CDA schema alignment |

## Coordination Checklist for PRs

Before merging a PR that changes core contracts:

- [ ] Does this touch a schema file? → Update CDM and App
- [ ] Does this add fields to a model? → Update schema to match
- [ ] Does this change evaluation logic? → Verify parity cases still pass
- [ ] Will this break existing content packs? → Add `minimumAppVersion` gate or migration
- [ ] Have I updated all 3 repo CHANGELOGs with a coordination note?

Example PR description footer:
```
### Cross-Repo Impact
- **CDA**: Added `evaluationMode` field to scoring-tool-schema.json
- **CDM**: Updated tool editor to capture mode, generation updated
- **App**: RemoteScoringEvaluation now handles mode, logic in evaluateScoring()
- **Tested**: Parity cases pass with new CDM output
```

## Version Pinning & Compatibility

- App downloads content pack and calls `ClinicalContentPackLoader.load()` + `validateEngineParityCases()`
- Pack validation fails if app cannot parse/execute it — pack is rejected
- If schema requires new app code, raise `minimumAppVersion` in schema so old app versions refuse incompatible packs
- Ensure backward compatibility when possible — make new fields optional with sensible defaults

## Content Features Gated by App Version

`tool/sync_manifest.py` raises the pack `minimumAppVersion` automatically when content uses a feature that older app builds would mishandle:

| Content feature | Minimum app version |
|-----------------|---------------------|
| Every pack (baseline floor) | 0.63.6 |
| Shared learning items | 0.60.0 |
| Inline assessment images (`{{image:...}}`) | 0.63.5 |
| `__inline_only__` image attachments | 0.63.7 |
| Procedures | 0.64.3 |
| Scoring-tool `escalations` (single-criterion escalation, e.g. NEWS2 red score) | 0.76.3 |

When adding a schema feature that older apps would silently ignore (rather than reject), add a rule here and in `sync_manifest.py`.

## Common Patterns

### Adding an optional field
1. Add to schema with `"default"` or `"type": ["string", "null"]`
2. CDM: optional input, safe default on output
3. App: handle null/missing gracefully in fromJson

### Removing a field
1. CDM: stop generating it (if optional in schema)
2. App: parse still accepts it (no error on extra fields)
3. Schema: mark as deprecated, plan sunset after N versions

### Changing field type
1. Schema: mark old field deprecated, add new field
2. CDM: generate both for transition period, then switch
3. App: parse both, prefer new, fall back to old

## Questions Before Merging

1. Is this change backward compatible? (Can old packs still load?)
2. Will old app versions reject new packs? (By design or accident?)
3. Do parity cases in test packs still pass?
4. Are all 3 repos' CHANGELOGs updated?
5. Should `minimumAppVersion` be incremented in schema?

## Known Deferred Issues

**Compatibility audit completed 2026-10-05.** 5 medium/high-severity issues fixed. 3 low-severity issues deferred:

### 1. RemoteBloodPanelDefinition Specimens Field
- **Status (updated 2026-10-06):** Resolved. `RemoteBloodPanelDefinition` does not hold specimens, but the app reads them through `BloodSpecimenService` and renders tube colours for every `specimenTypeId`. The app contract test checks every schema specimen type.

### 2. Medication Summary Empty String Default
- **Status:** Defaults to `''` when missing (schema marks required)
- **Impact:** Medications can have empty summaries
- **Why deferred:** Empty vs. missing is semantically equivalent; CDM likely always generates it; no clinical impact
- **Action:** None needed unless schema strictness becomes requirement

### 3. RemoteScoringToolDefinition Migration Metadata
- **Status:** Parser defines `migration` field; schema has no equivalent
- **Impact:** App-internal shadow migration tracking; not in schema
- **Why deferred:** App-internal metadata only; intentional design; never generated by CDM; non-breaking
- **Action:** No change needed; document as app-internal extension of schema
