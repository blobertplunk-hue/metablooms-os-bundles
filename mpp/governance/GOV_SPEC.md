# GVN — Governance Layer for MPP
**Version:** 1.0.0
**Status:** ACTIVE
**Relationship:** Wraps MPP. MPP enforces process. GVN enforces quality.

---

## The Core Problem GVN Solves

MPP gates on *presence and structure*. A disciplined-but-mediocre operator can pass
every MPP stage with vague research, rubber-stamped reviews, and tests that cover lines
without asserting behavior. MPP prevents the worst outcomes. GVN raises the ceiling.

The distinction:

| MPP asks | GVN asks |
|---|---|
| Does research_dossier.json exist? | Is the problem stated precisely enough to know when it's solved? |
| Are claims cited? | Are the citations actually authoritative for this domain? |
| Are there 3 edge cases? | Are these the edge cases that would actually cause production failures? |
| Is CDR approved? | Did the reviewer actively try to break the proposal before approving it? |
| Do tests pass? | Do the tests assert the behaviors that matter to real users? |

GVN cannot be automated. Every GVN stage requires a human judgment recorded
in a signed receipt. No governance receipt = pipeline does not run.

---

## The Full Stack

```
┌─────────────────────────────────────────────────────┐
│  GVN — Governance Layer                             │
│                                                     │
│  G0: Context Brief ──────────────────────────────┐  │
│      (domain truth injected before PRVE runs)    │  │
│                                                  ▼  │
│  ┌──────────────────────────────────────────────┐   │
│  │  MPP — Mandatory Process Pipeline            │   │
│  │  PRVE → SEE → MMD → CDR → ECL → TEST        │   │
│  │                    ↑                         │   │
│  │         G1: Adversarial MMD Pass             │   │
│  │         (active gap hunting at MMD stage)    │   │
│  │                              ↑               │   │
│  │              G2: Behavior Review             │   │
│  │              (test quality at TEST stage)    │   │
│  └──────────────────────────────────────────────┘   │
│                                  │                  │
│  G3: Governor Loop ◄─────────────┘                  │
│      (tracks pipeline health across runs)           │
└─────────────────────────────────────────────────────┘
```

---

## G0 — Context Brief: Domain Truth Injection

**When:** Before PRVE runs.
**Who:** The person who knows what problem is actually being solved (product owner, lead engineer, or the operator who initiated the turn).
**What:** A structured document that gives the pipeline access to knowledge that cannot be inferred from code alone.

**The Context Brief must answer:**

1. **The real user story** — not "implement X" but "a [specific person] needs to [do what] without [what frustration]"
2. **The definition of done with examples** — what does good output actually look like? Show one.
3. **The hidden constraints** — what does the pipeline operator not know that would change the approach?
4. **The failure cost** — if this is wrong in production, what breaks? For whom?
5. **Prior attempts** — what has been tried before and why it didn't work

**Quality test for a Context Brief:**
> Can a competent engineer who has never seen your codebase read this brief and write a correct implementation without asking a single clarifying question?

If no: the brief is not done.

**Required artifact:** `gov/CONTEXT_BRIEF.md`

**GVN G0 receipt:** `gov/receipts/g0_context_brief_receipt.json`
```json
{
  "stage": "G0_CONTEXT_BRIEF",
  "reviewer": "name or role",
  "quality_verdict": "SUFFICIENT | INSUFFICIENT",
  "gaps_found": ["any gaps in context the reviewer spotted"],
  "definition_of_done_is_testable": true,
  "signed_at": "ISO8601"
}
```

---

## G1 — Adversarial MMD: Active Gap Hunting

**When:** At the MMD stage, before CDR begins.
**Who:** Someone who did NOT write the research artifacts. Ideally someone whose job is to break things.
**What:** An active attempt to find gaps the author missed. Not a review of the MMD report — an independent gap hunt.

**The adversarial reviewer asks these questions (not optional):**

1. **Adversarial input:** "What does a malicious or careless actor send to break this? What's the worst-case input?"
2. **Scale failure:** "What breaks at 10× the expected load, data size, or concurrency?"
3. **API misuse:** "What does a distracted junior engineer do wrong with this interface on their first use?"
4. **False assumption:** "Which claim in the research dossier is most likely to be wrong? What happens if it is?"
5. **Missing integration:** "What existing system will this touch that isn't mentioned anywhere?"
6. **The obvious thing nobody said:** "What is so obvious the author forgot to state it?"

**Required artifact:** `gov/ADVERSARIAL_MMD.md`
Each of the 6 questions must be explicitly answered, even if the answer is "not applicable — because [reason]."

**Quality test for Adversarial MMD:**
> Did the adversarial reviewer find at least one gap the author did not?

If yes: that gap is added to `MMD_REPORT.json` and the pipeline continues.
If no: the reviewer must sign that they genuinely tried and found none (not just that they looked).

**GVN G1 receipt:**
```json
{
  "stage": "G1_ADVERSARIAL_MMD",
  "reviewer": "name or role (must differ from research artifact author)",
  "new_gaps_found": ["list of gaps added to MMD_REPORT by this review"],
  "all_six_questions_answered": true,
  "signed_at": "ISO8601"
}
```

---

## G2 — Behavior Review: Test Quality Gate

**When:** After tests are written, before S6_TEST runs.
**Who:** Someone who thinks like a QA engineer or end user — not the person who wrote the tests.
**What:** A review of what behaviors the tests actually assert, not just whether they pass.

**The behavior reviewer asks:**

1. **The costly bug test:** "Point to the test that would catch the most expensive production failure. Does it exist?"
2. **The hollow test:** "Which test would still pass if the core logic were completely wrong?"
3. **The user-behavior gap:** "What behavior that matters to a real user is not covered by any test?"
4. **The assertion quality:** "Are tests asserting specific values/behaviors, or just that no exception was raised?"
5. **The edge case match:** "Is there a test for every edge case in the MMD report?"

**Required artifact:** `gov/BEHAVIOR_REVIEW.md`
Must include answers to all 5 questions and a list of tests added or changed as a result.

**Quality test for Behavior Review:**
> After this review, can the reviewer say "if all tests pass, the code does what users need"?

If no: tests are insufficient regardless of coverage percentage.

**GVN G2 receipt:**
```json
{
  "stage": "G2_BEHAVIOR_REVIEW",
  "reviewer": "name or role",
  "hollow_tests_found": ["test names"],
  "user_behavior_gaps": ["behaviors not tested"],
  "tests_added_or_changed": 0,
  "verdict": "SUFFICIENT | INSUFFICIENT",
  "signed_at": "ISO8601"
}
```

---

## G3 — Governor Loop: Pipeline Health Tracking

**When:** After every certified run (and after every escalation).
**Who:** The Governor — whoever owns the pipeline's quality over time.
**What:** Cross-run analysis to detect gaming, threshold drift, and systemic failure patterns.

**The Governor reviews:**

1. **Stage failure rates** — which stages fail most often? Is it the same operator? The same type of change?
2. **Certification → production quality** — did certified outputs actually work in production?
3. **Artifact quality drift** — are research dossiers getting vaguer over time? Are edge cases getting more trivial?
4. **Gaming signals** — are MMD reports listing the same 3 boilerplate edge cases on every run? Are CDR proposals getting shorter?
5. **Threshold calibration** — is 90% coverage the right threshold for this codebase? Should max_function_lines be tighter?

**Required artifact:** `gov/GOVERNOR_LOG.md` (append-only)
One entry per certified run + one entry per escalation.

**Governor has authority to:**
- Raise or lower thresholds in `mpp_config.json`
- Require additional adversarial passes
- Invalidate a prior certification if post-production evidence shows it was wrong
- Declare a class of changes as always-STANDARD (never TRIVIAL)

**Governor does NOT have authority to:**
- Skip a stage
- Approve a CDR that MPP blocked
- Override a test failure

---

## Roles Summary

| Role | Owns | Cannot |
|---|---|---|
| **Context Owner** | Domain truth, definition of done | Write research artifacts (conflict of interest) |
| **Research Operator** | PRVE, SEE, MMD artifacts | Self-approve CDR |
| **Adversarial Reviewer** | G1 Adversarial MMD | Be the same person as Research Operator |
| **CDR Reviewer** | REVIEW_DECISION.json | Be the same person as the proposer |
| **Behavior Reviewer** | G2 test quality | Write the tests being reviewed |
| **Governor** | G3 pipeline health | Override MPP gates |

**Minimum viable governance team:** 2 people.
- Person A: Context Owner + CDR Reviewer + Behavior Reviewer
- Person B: Research Operator + (implicitly) Adversarial Reviewer

**Solo operation:**
Possible, but requires explicit role-switching: complete one role fully before switching.
A solo operator may not write research artifacts and immediately approve CDR in the same session.
Minimum gap: start a new session for the CDR review.

---

## What Governance Produces

Code that exits GVN + MPP certified has:

- **Real context** (not inferred — explicitly stated by someone who knows)
- **Adversarially-reviewed gaps** (not just the obvious ones)
- **Behaviors proven to users** (not just lines covered)
- **A health record** (every run is traceable; gaming is detectable)
- **A live quality threshold** (calibrated to this codebase, not defaults)

This is the stack that can produce world-class code at scale.
MPP enforces the floor. Governance raises the ceiling.
