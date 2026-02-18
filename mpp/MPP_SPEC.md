# MPP — Mandatory Process Pipeline
**Version:** 1.0.0
**Status:** LOCKED (self-validated — see META/META_VALIDATION.md)
**Authority:** This document governs all code that passes through MPP.

---

## What MPP Is

MPP is a 7-stage fail-closed pipeline designed to produce code that is:

- **Correct** — does exactly what it claims to do, provably
- **Complete** — no missing middle, no silent assumptions
- **Clear** — a competent reader understands any function in under 30 seconds
- **Beautiful** — structure, naming, and output are locked in before a line is written
- **Resilient** — edge cases and failure modes are enumerated before implementation
- **Verified** — tests exist for every stated behavior
- **Self-improving** — every failure re-routes to the earliest broken stage

No stage may be skipped. No gate may be soft-failed. Any bypass is illegal execution.

---

## The Pipeline

```
PRVE → SEE → MMD → CDR → ECL → TEST → GOVERNED RECURSION
  ↑___________________________________|
        (loop back to earliest failing stage)
```

---

## Stage 1 — PRVE: Pre-Build Research & Validation Engine

**Purpose:** Force understanding before action. Research-first is non-negotiable.

**Required artifacts (turn-local):**
- `research_dossier.json` — problem statement, known prior solutions, constraints
- `constraint_register.json` — hard constraints (must-haves and must-nots)
- `readiness_decision.json` — explicit go/no-go with justification

**Fast path (TRIVIAL_CLASSIFICATION):**
A change may claim `"complexity": "TRIVIAL"` in `readiness_decision.json`. If claimed:
- It must justify why (one sentence minimum)
- It skips SEE, MMD depth checks, and the full CDR aesthetic contract
- It cannot claim TRIVIAL if it touches more than one file or any public interface

**Gate rule:** `readiness_decision.json` must have `"authorized": true`. Else: BLOCK.

---

## Stage 2 — SEE: Sandcrawler Evidence Engine

**Purpose:** No claim is accepted without evidence. Every external fact is cited.

**Required artifacts:**
- `see/SEE_QUERIES.json` — exact queries run
- `see/SEE_SOURCES.md` — sources consulted (docs, tests, prior art)
- `see/SEE_CITATION_MAP.json` — maps each claim to its source
- `see/SEE_EVIDENCE_SUMMARY.md` — synthesized evidence brief
- `see/SEE_ANTI_PATTERNS.md` — what to avoid and why (with evidence)

**Gate rule:** Every claim in `research_dossier.json` must appear in `SEE_CITATION_MAP.json`. Uncited claims = BLOCK.

---

## Stage 3 — MMD: Missing Middle Detector

**Purpose:** Explicitly hunt for what isn't said. The missing middle is where all errors hide.

**Five required sub-checks (all mandatory):**

1. **Gap Detection** — What is assumed but not stated? Stated assumptions must be enumerated.
2. **Dependency Audit** — What does this need that isn't yet declared? All dependencies must be explicit.
3. **Edge Case Enumeration** — What inputs can break this? Minimum 3 edge cases for any non-trivial function.
4. **Failure Mode Catalog** — How can this fail? Each failure mode must have a named response.
5. **Integration Audit** — How does this connect to what already exists? Every touch point must be mapped.

**Required artifact:** `mmd/MMD_REPORT.json`

```json
{
  "gaps": [{"id": "G1", "severity": "HIGH|MEDIUM|LOW", "description": "...", "resolution": "..."}],
  "dependencies": [...],
  "edge_cases": [...],
  "failure_modes": [...],
  "integration_points": [...]
}
```

**Gate rule:** Any `"severity": "HIGH"` unresolved gap = BLOCK.

---

## Stage 4 — CDR: Code Delta Review

**Purpose:** Propose and lock the change before writing production code. Beauty is decided here, not after.

**Required artifacts:**
- `cdr/DELTA_PROPOSAL.md` — exactly what will change, line by line if needed
- `cdr/IMPACT_ANALYSIS.md` — what else will be affected, including downstream
- `cdr/AESTHETIC_CONTRACT.json` — locked aesthetic rules for this change
- `cdr/REVIEW_DECISION.json` — `"verdict": "APPROVED" | "BLOCKED"` with reasons

**AESTHETIC_CONTRACT.json schema:**
```json
{
  "naming_style": "snake_case | camelCase | ...",
  "max_function_lines": 40,
  "max_nesting_depth": 3,
  "line_length_limit": 100,
  "required_blank_lines_between_sections": 2,
  "output_format": "description of what produced output should look and feel like",
  "expressiveness_rule": "names must say what a thing IS, not how it works",
  "banned_patterns": ["..."]
}
```

**Gate rule:** `REVIEW_DECISION.json` must have `"verdict": "APPROVED"`. Else: BLOCK.
The aesthetic contract is binding for all subsequent stages. Any code that violates it fails ECL.

---

## Stage 5 — ECL: Extraordinary Code Law

**Purpose:** Make every module idiot-proof to any reader — human or machine.

**Required for every `.py` file:** ECL YAML header at top of file.

```yaml
# ECL:
#   id: <UNIQUE_STABLE_ID>
#   role: entrypoint | orchestrator | gate | validator | adapter | schema | io | tool | library
#   owns: [what this module is solely responsible for]
#   does_not: [explicit non-goals — what looks like it might be here but isn't]
#   inputs: [name: type pairs]
#   outputs: [name: type pairs]
#   side_effects: [filesystem | ledger | network | none]
#   failure_modes: [named failure modes with exit behavior]
#   invariants: [conditions that must hold before, during, and after]
#   evidence: [what artifact proves this worked]
#   aesthetic: [reference to CDR AESTHETIC_CONTRACT]
#   last_reviewed: YYYY-MM-DD
```

**Beauty audit (enforced by ECL validator):**
- Names: Every name must be expressive and precise. No `x`, `tmp`, `data`, `result` except in tightly scoped loops.
- Structure: Every file tells a story. Top = purpose, middle = logic, bottom = entry. No surprise order.
- Density: No function does two things. If you feel the urge to use "and" in a function name, split it.
- Readability: The ECL validator runs a simulated "cold read" — can the module be understood without context?

**Gate rule:** ECL validator passes at 100% for all critical-path modules (role = entrypoint | gate | orchestrator). Else: BLOCK.

---

## Stage 6 — TEST: Explicit Test Gate

**Purpose:** Evidence that the code does what it claims. No claim survives without a test.

**Required artifacts:**
- `tests/` — test suite with coverage ≥ 90% of critical path functions
- `tests/edge_cases/` — tests for every edge case enumerated in MMD
- `tests/benchmarks/` — performance baseline (even a single timing test counts)
- `tests/OUTPUT_QUALITY_REPORT.md` — does output meet the CDR aesthetic contract?

**Output quality test:** Every function that produces user-visible output must have a test that asserts
the output matches the aesthetic contract (format, structure, naming, density).

**Gate rule:** All tests pass. Coverage ≥ threshold. No regressions from prior certified run. Else: BLOCK.

---

## Stage 7 — GOVERNED RECURSION: Bounded Loop Controller

**Purpose:** Iterate toward correctness without runaway loops or silent giving-up.

**Rules:**
- Maximum iterations: 3 (configurable, must be explicit)
- On any stage failure, **loop back to the earliest failing stage** — not just the last one
- Each iteration must produce a `loop/ITERATION_{N}_RECEIPT.json` proving progress
- Regression tracker runs between iterations — if no progress in an iteration, escalate immediately
- On max iterations reached: **ESCALATE** — emit a full diagnostic report, never silently fail

**Loop-back routing:**
| Failing Stage | Loop Back To |
|---|---|
| TEST fails | MMD (maybe there's a gap you missed) |
| ECL fails | CDR (aesthetic contract needs adjustment) |
| CDR blocked | SEE (gather more evidence, re-propose) |
| MMD HIGH gap | SEE (research the gap) |
| SEE uncited claim | PRVE (problem statement may be wrong) |
| PRVE blocked | STOP — escalate to human |

**Gate rule:** Loop certifies only when all prior stages pass in the same iteration. Partial passes don't count.

---

## Certification

A run is **CERTIFIED** when:
1. All 7 stages pass in sequence, in a single iteration
2. A `MPP_CERTIFICATE.json` is written with SHA-256 of all artifacts
3. The certificate is append-only (never overwritten, only new entries added)

```json
{
  "certified_at": "ISO8601",
  "iteration": 1,
  "sha256_manifest": {"file": "hash"},
  "pipeline_version": "1.0.0",
  "verdict": "CERTIFIED"
}
```

---

## What This Pipeline Produces

Code that exits MPP is:
- Proven correct (tests pass, evidence cited)
- Gap-free (MMD cleared all 5 sub-checks)
- Aesthetically locked (CDR contract enforced end-to-end)
- Self-describing (ECL headers on every module)
- Output-verified (output quality tested, not just logic)
- Failure-safe (every failure mode named and handled)
- Traceable (certificate + full artifact chain)

This is not a style guide. It is a mechanical gate. The code either passes or it doesn't.
