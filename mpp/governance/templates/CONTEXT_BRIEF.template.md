# Context Brief
**Turn:** [turn identifier]
**Context Owner:** [name or role — must be the person who knows the domain]
**Date:** [YYYY-MM-DD]

---

## Real User Story

> Not "implement X." The story of a specific person with a specific need.

**Who:** [describe the actual user — role, context, what they're doing when they need this]

**Needs to:** [the action they need to complete, in their language not yours]

**Without:** [the specific friction or failure they currently experience]

**Example:** A payments engineer who just got paged at 2am needs to find which transaction
ID caused a payment loop without reading 40,000 log lines manually.

---

## Definition of Done (with example)

> Testable. Specific. Observable. "Works correctly" is not this.

Done looks like:

```
[Paste an example of what correct output looks like, or describe it precisely enough
that two engineers would independently agree the output is correct.]
```

**Acceptance criteria:**
1. [Specific, observable criterion — not "it works"]
2. [Another one]
3. [...]

**How to verify done:**
[The exact steps someone would follow to confirm the output is correct.]

---

## Hidden Constraints

> What does the pipeline operator not know that would change the approach?

- [Constraint 1 — e.g. "This code runs on Python 3.8 in production, not 3.11"]
- [Constraint 2 — e.g. "The output of this function is consumed by a mobile client that can't handle null values"]
- [Constraint 3 — e.g. "This path is called 10,000 times per second at peak — allocation matters"]

If none: write "No hidden constraints — justification: [reason]"

---

## Failure Cost

> If this is wrong in production, what breaks? For whom? How fast?

**Immediate impact:** [what breaks the moment the bug is hit]
**Downstream impact:** [what breaks next — other systems, users, data]
**Time to detect:** [how long before someone notices]
**Severity:** LOW / MEDIUM / HIGH / CRITICAL

---

## Prior Attempts

> What has been tried before and why it didn't work?

| Approach | Why it failed or was rejected |
|---|---|
| [approach 1] | [reason] |
| [approach 2] | [reason] |

If nothing was tried before: "First attempt — no prior history."

---

## Notes for the Research Operator

> Anything else the person building this should know.

[Free text. Anything that would change how you'd approach this if you knew it from the start.]
