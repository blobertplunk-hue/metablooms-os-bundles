# G2 — Behavior Reviewer Checklist

Complete after writing BEHAVIOR_REVIEW.md. Check each item honestly.
You must not be the person who wrote the tests being reviewed.

## Independence

- [ ] I did NOT write the tests I am reviewing
- [ ] I approached this as a QA engineer or end user, not as the implementer

## Coverage

- [ ] I identified the test that catches the most expensive production failure
- [ ] I found and listed any hollow tests (or confirmed none exist with reasoning)
- [ ] I checked every DoD acceptance criterion against the test suite
- [ ] I assessed assertion quality across the entire test suite
- [ ] I verified every MMD edge case has a corresponding test

## Quality bar

- [ ] Every user-facing behavior from the Context Brief has at least one test
- [ ] No test only asserts "no exception was raised" without further assertion
- [ ] At least one test would fail if the core logic returned a hardcoded stub value
- [ ] Tests cover the happy path AND the documented failure modes

## Verdict

- [ ] **SUFFICIENT** — all items above checked, no unresolved gaps
- [ ] **INSUFFICIENT** — at least one item unchecked; tests must be improved before TEST gate runs

**Changes required (if INSUFFICIENT):**
- [change 1]
- [change 2]
