# G0 — Context Brief
## Turn: 003_waiver_accuracy
## Date: 2026-02-19

---

### 1. Who specifically needs this, and what frustration does it remove?

**Who:** Engineering leads and reliability teams who run the MPP/GVN pipeline
on their teams' work.

**The frustration:** After every post-mortem, someone says "we should have caught
this." They're right — the pattern was in the library, and a waiver was filed six
weeks ago saying "doesn't apply to us." Nobody ever checked whether the waivers
were accurate. The pre-mortem and post-mortem live in different documents, different
meetings, different states of mind.

Waivers accumulate. Teams learn that filing a waiver is how you get the gate to
pass. Pattern compliance becomes a checkbox. The pattern library becomes decoration.

**What it removes:** The disconnect between "we waived this risk" and "this risk
materialized." A team with a history of accurate waivers earns credibility. A team
with a pattern of waiving NONIDEMPOTENT_RETRY right before double-charge incidents
gets flagged — before the next feature ships.

---

### 2. What does done look like — specifically enough to test right now?

**Acceptance test (runnable today):**

```python
from mpp.patterns.waiver_tracker import WaiverTracker
import tempfile, pathlib, datetime

store = pathlib.Path(tempfile.mkdtemp()) / "waivers.json"
tracker = WaiverTracker(store)

# Record a waiver
tracker.record_waiver(
    run_id="run-001",
    pattern_id="NONIDEMPOTENT_RETRY",
    team="payments",
    reason="We use Stripe idempotency keys on all charge calls.",
    timestamp=datetime.datetime(2026, 1, 1),
)

# Record an incident that matched the same pattern
tracker.record_incident(
    pattern_id="NONIDEMPOTENT_RETRY",
    team="payments",
    description="Double charge on retry after network timeout.",
    timestamp=datetime.datetime(2026, 1, 30),
)

# Accuracy: payments team waived NONIDEMPOTENT_RETRY once, incident followed → score < 1.0
score = tracker.accuracy("payments", "NONIDEMPOTENT_RETRY")
assert score < 1.0, f"Expected < 1.0, got {score}"

# Query: was this pattern waived within 90 days before the incident?
matches = tracker.waivers_before_incident(
    pattern_id="NONIDEMPOTENT_RETRY",
    team="payments",
    incident_timestamp=datetime.datetime(2026, 1, 30),
    window_days=90,
)
assert len(matches) == 1
assert matches[0]["run_id"] == "run-001"

print("DONE — all assertions passed")
```

**Done means:** that script runs without error.

---

### 3. What constraint would I never infer from the code alone?

1. **Waivers are keyed by `run_id`, not timestamp.** The same team can have
   multiple runs on the same day. A waiver links to a specific MPP run, not a
   wall-clock moment.

2. **Accuracy is undefined below a minimum sample size.** Three waivers is not
   enough data to call a team "unreliable." `accuracy()` must return `None` (not
   a float) when waiver count < `MIN_SAMPLE = 5`.

3. **A waiver with no subsequent incident is a TRUE ACCURATE waiver — not a gap.**
   The system must not penalise teams for filing correct waivers on risks that
   genuinely don't materialise.

4. **The incident-matching window is configurable and defaults to 90 days.**
   Some patterns (NONIDEMPOTENT_RETRY) show impact in minutes; others
   (CACHE_INVALIDATION_RACE) may take months to surface. Teams can override
   per-pattern window in config.

5. **Incident data entry is manual for now.** No PagerDuty/OpsGenie integration.
   `record_incident()` is the API surface; how incidents reach it is out of scope.

6. **Storage is append-only JSON — never mutated after write.** Same invariant as
   `gov/GOVERNOR_LOG.md`. If you need to correct a record, you append a
   `{type: "correction", ...}` entry, not edit the original.
