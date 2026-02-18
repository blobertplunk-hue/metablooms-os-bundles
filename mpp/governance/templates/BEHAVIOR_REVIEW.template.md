# Behavior Review
**Turn:** [turn identifier]
**Reviewer:** [name or role — must not be the person who wrote the tests]
**Date:** [YYYY-MM-DD]

---

> Your job is not to check that tests pass.
> Your job is to check that tests prove the right things.
> A test that passes while the core logic is completely wrong is worse than no test.

---

## Question 1: The Costly Bug Test

**Which test would catch the most expensive production failure?**

Look at the test suite. Find the test that, if removed, would let the worst
possible production bug through undetected.

**That test is:** [test name and file]

**It catches:** [what failure mode it prevents]

**If it doesn't exist yet:** [describe what test should be added]

---

## Question 2: Hollow Tests

**Which tests would still pass if the core logic were completely wrong?**

A hollow test is one that:
- Only asserts that no exception was raised
- Asserts the wrong output (tests the mock, not the code)
- Tests implementation details instead of behavior
- Would pass with a stub that returns a hardcoded value

**Hollow tests found:**

| Test name | Why it's hollow | How to fix it |
|---|---|---|
| [test_name] | [reason] | [fix] |

If none found: explain why each test asserts a specific, meaningful behavior.

---

## Question 3: User Behavior Gap

**What behavior that matters to a real user is not covered by any test?**

Go back to the Context Brief's Definition of Done.
For each acceptance criterion: is there a test that would fail if it were violated?

**Untested user-facing behaviors:**

| Behavior from DoD | Test that covers it | Missing? |
|---|---|---|
| [criterion 1] | [test name or "none"] | yes/no |
| [criterion 2] | [test name or "none"] | yes/no |

---

## Question 4: Assertion Quality

**Are tests asserting specific values and behaviors, or just "no exception"?**

Count:
- Tests that assert a specific return value or output shape: [N]
- Tests that assert a specific error message on failure: [N]
- Tests that assert only `is not None` or `is True` without specifics: [N]
- Tests that only check `no exception raised`: [N]

**Verdict:** [is assertion quality sufficient for the failure modes in MMD_REPORT?]

---

## Question 5: Edge Case Match

**Is there a test for every edge case in the MMD report?**

| MMD Edge Case ID | Test file | Test name | Covered? |
|---|---|---|---|
| EC1 | [file] | [test] | yes/no |
| EC2 | [file] | [test] | yes/no |
| EC3 | [file] | [test] | yes/no |

**Uncovered edge cases:** [list any EC IDs with no test]

---

## Verdict

**Overall assessment:** SUFFICIENT | INSUFFICIENT

**If INSUFFICIENT — what must change before TEST gate can run:**

1. [Required change 1]
2. [Required change 2]

**Tests added or changed as a result of this review:** [count and names]
