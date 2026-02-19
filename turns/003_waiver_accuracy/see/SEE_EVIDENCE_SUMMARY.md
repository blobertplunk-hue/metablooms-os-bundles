# SEE Evidence Summary
## Turn: 003_waiver_accuracy
## Date: 2026-02-19

---

## What We Verified Empirically Before Writing Production Code

### 1. Accuracy Algorithm Correctness

Ran the accuracy calculation logic against 4 calibration scenarios:

| Scenario | Waivers | Incidents | Expected | Got |
|---|---|---|---|---|
| 1 waiver, below MIN_SAMPLE | 1 | 1 | `None` | `None` ✓ |
| 5 waivers, 1 incident within window | 5 | 1 | `0.0` | `0.0` ✓ |
| 1 waiver, no incident, below MIN_SAMPLE | 1 | 0 | `None` | `None` ✓ |
| `waivers_before_incident` query | 1 | 1 | `['run-001']` | `['run-001']` ✓ |

All 4 scenarios pass.

### 2. Key Algorithm Design Confirmed

**Accuracy definition:** `accurate_waivers / total_waivers`
where `accurate` = no incident of the same pattern within `window_days` *after* the waiver.

**Window direction:** The window runs *forward* from the waiver timestamp.
A waiver is a claim: "this pattern won't cause an incident in the next N days."
Accuracy measures whether that claim held.

`waivers_before_incident` runs *backward* from the incident — useful for post-mortem
queries: "did anyone waive this pattern before the incident occurred?"

These are two different queries answering two different questions:
- `accuracy()`: ongoing team health score
- `waivers_before_incident()`: retrospective incident analysis

### 3. Storage Format Confirmed

Append-only JSONL (one JSON object per line) chosen over a JSON array:
- Appending a line is O(1) and does not require reading + rewriting the file
- Crash during append leaves prior entries intact
- Consistent with the GOVERNOR_LOG.md append-only contract

Entry schema:
```json
{"type": "waiver", "run_id": "...", "pattern_id": "...", "team": "...", "reason": "...", "timestamp": "ISO8601"}
{"type": "incident", "pattern_id": "...", "team": "...", "description": "...", "timestamp": "ISO8601"}
{"type": "correction", "corrects_run_id": "...", "field": "...", "old_value": "...", "new_value": "...", "reason": "...", "timestamp": "ISO8601"}
```

### 4. No Unexpected Dependencies

stdlib only: `json`, `datetime`, `pathlib`. No third-party imports required.

### 5. One Design Risk Noted

**Clock skew:** If a waiver and incident have the same timestamp (e.g., both
recorded in a test), the `waivers_before_incident` boundary condition
(`cutoff <= ts <= incident_ts`) includes the waiver. This is correct for
the real-world case (waiver was filed before or at the moment of incident
confirmation) and is the intended behavior.
