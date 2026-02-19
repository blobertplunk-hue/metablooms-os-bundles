# G1 — Adversarial MMD
## Turn: 003_waiver_accuracy
## Date: 2026-02-19
## Reviewer: adversarial (different perspective from researcher)

---

### Q1. What malicious or careless input breaks this?

**Timestamp injection:** A caller passes a `timestamp` that is far in the past
(`1970-01-01`) to make their waiver appear before all incidents, inflating their
accuracy score. The system does not validate that timestamps are recent or
monotonically increasing.

*Resolution:* `record_waiver()` and `record_incident()` warn (but do not reject)
if the provided timestamp is more than 7 days in the past. This is advisory — the
primary protection is that the log is append-only and auditable.

**Pattern ID that doesn't exist in the registry:** `record_waiver(pattern_id="MADE_UP")`
succeeds silently. Accuracy queries on that ID return `None` (below min_sample).
No corruption, just silent no-ops.

*Resolution:* Accept this. WaiverTracker deliberately does not take a registry
dependency. It is a log, not a validator. The MMD gate that calls it has the
registry and performs the validation.

**team=None or team='':** Would create entries under a blank team key. Queries
would work but the team name would be meaningless.

*Resolution:* Guard: raise `ValueError` if `team` is falsy in `record_waiver()`
and `record_incident()`.

---

### Q2. What breaks at 10x load, data size, or concurrency?

**10,000 waiver entries:** `accuracy()` reads the entire log file and filters in
memory. At 10,000 entries this is milliseconds — not a concern. At 1,000,000
entries it may become slow. Out of scope for this turn; add an index if needed
when it's actually slow.

**Concurrent writes from two pipeline runs:** Both processes append to the same
file. POSIX `open(mode='a')` and `write()` are atomic for writes smaller than
PIPE_BUF (~4096 bytes) on Linux. Each log entry is well under that. In practice,
concurrent MPP runs are extremely rare. If they occur, the worst outcome is
interleaved bytes in a single line — one unreadable entry, rest of log intact.

*Resolution:* Log reader skips lines that fail `json.loads()` with a warning.
This is already the correct pattern for any append-only log.

---

### Q3. What does a distracted junior engineer do wrong on first use?

**Call `accuracy()` without first calling `record_incident()` after a known
incident:** Gets `None` (below min_sample) or an inflated score. Thinks the team
is doing well. The system cannot detect unreported incidents — this is a fundamental
limitation that must be documented prominently.

**Forget to pass `team=` kwarg:** Python positional-argument mistake. Passes the
description as team. `record_waiver(pattern_id, run_id, "We use idempotency keys")`
instead of `record_waiver(pattern_id, run_id, team=..., reason=...)`.

*Resolution:* Make all parameters keyword-only after the first (path) argument.

**Use the accuracy score as a hard gate:** "Team accuracy < 0.8 means we block
the deploy." Wrong use of this data — sample sizes are small and the score is a
signal, not a SLA.

*Resolution:* Docstring must say: "This score is advisory. Do not use it as a
hard gate. Use it as a conversation starter."

---

### Q4. Which research claim is most likely false? What happens if it is?

**Claim:** "POSIX append writes are atomic under PIPE_BUF for concurrent processes."

*If false:* Two concurrent runs could interleave bytes mid-line. The reader would
get a malformed JSON line, log a warning, and skip it — one entry lost. The log
is not corrupted, but the lost entry means a waiver is not counted.

*Probability:* Low. The claim is well-established for Linux/ext4. Concurrent MPP
runs are also rare in practice.

*Mitigation already in place:* Skip-on-parse-error means the log remains usable
even if the claim fails.

---

### Q5. What existing system will this touch that isn't mentioned?

**s3_mmd.py pattern_checks:** This is the natural caller of `record_waiver()`.
When sub-check 6 processes `pattern_checks` from MMD_REPORT.json, it already has
`pattern_id`, `addressed`, `waiver_reason`, and `run_id` available. The integration
point exists but is explicitly out of scope for this turn.

**gov/GOVERNOR_LOG.md:** G3 Governor currently tracks per-run pipeline health.
Waiver accuracy is a *cross-run* signal. G3 should eventually read waiver accuracy
scores as an additional gaming signal: "waiver accuracy for team X fell below 0.5
in the last 30 days." Not implemented this turn.

---

### Q6. What is so obvious the author forgot to state it?

**The waiver_log.json file location is not specified.** The G0 acceptance test
uses a `tempfile` — fine for testing. Production needs a canonical path.

*Resolution:* Default to `gov/waiver_log.jsonl` relative to the repo root.
Constructor accepts an override. The `.jsonl` extension signals JSONL format.

**There is no way to list all teams or all patterns with waivers.** `accuracy()`
requires knowing the team and pattern in advance. A dashboard query
("show me all teams with accuracy < 0.7") requires iterating the full log.

*Resolution:* Add `all_teams()` and `all_patterns()` methods that return the set
of distinct teams/patterns in the log. Trivial to implement; essential for use.
