# Error Ledger

Use this ledger for failures, near-misses, and diagnostic evidence.

````markdown
## [ERR-YYYYMMDD-XXX] incident_title

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: open | investigated | resolved | archived
**Primary Capability**: research | planning | tool-use | verification | synthesis | communication | coding | execution discipline | memory retrieval | long-horizon task handling

### Summary
Short description of the failure.

### Error
```text
Exact error text or concise failure output.
```

### Context
- Task:
- Command or action:
- Environment:

### Diagnostic Hypothesis
Initial best guess at root cause.

### Recurrence Signal
first_time | similar_before | recurring_pattern

### Suggested Next Step
log_only | diagnose | create_training_unit | evaluate

### Linked Records
- LRN-...
- CAP-...
- TRN-...
- AGD-...

---
````
