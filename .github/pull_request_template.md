## Summary

Brief description of schema/content changes.

## Type of Change

- [ ] Schema update
- [ ] Content addition/modification
- [ ] Validation/governance rule
- [ ] Documentation

## Cross-Repo Coordination

**If this touches schema:**

- [ ] CDM templates updated for new schema fields
  - [ ] Generation validated against new schema
  
- [ ] App parsers updated for new fields
  - [ ] Test fixtures include new structure
  - [ ] Parity cases pass
  
- [ ] minimumAppVersion incremented (if breaking change)?

- [ ] All 3 repo CHANGELOGs updated with coordination note?

**Example coordination note:**
```
### Cross-Repo Impact (v0.X.0)
- **CDA**: Added `newField` to scoring-tool-schema.json
- **CDM**: Updated tool generation templates to capture field
- **App**: RemoteScoringEvaluation.fromJson handles new field
- **Tested**: Parity cases pass with latest CDM output
```

## Checklist

- [ ] Schema is valid JSON
- [ ] All required fields documented
- [ ] Parity cases defined (scoring/blood tools)
- [ ] CHANGELOG.md updated (with coordination details)
