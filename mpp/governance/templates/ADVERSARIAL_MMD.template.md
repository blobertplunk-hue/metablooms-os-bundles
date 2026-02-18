# Adversarial MMD Review
**Turn:** [turn identifier]
**Adversarial Reviewer:** [name or role — must differ from research operator]
**Date:** [YYYY-MM-DD]
**Time spent:** [minimum 15 minutes — if less, explain why that's sufficient]

---

> Your job is not to confirm the research is complete.
> Your job is to break it. Find what the author missed.
> Answer every question below. "Not applicable" requires a specific reason.

---

## Question 1: Adversarial Input

**What does a malicious or careless actor send to break this?**

Think: crafted inputs, boundary values, encoding tricks, null bytes, empty strings,
maximum lengths, unexpected types, concurrent calls, out-of-order events.

**Answer:**

[What specific input would break this? If none found, explain why not — be specific.]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Question 2: Scale Failure

**What breaks at 10× the expected load, data size, or concurrency?**

Think: memory growth, O(n²) algorithms hidden in loops, lock contention,
queue backup, database connection exhaustion, cache invalidation storms.

**Answer:**

[What breaks at 10×? What's the bottleneck you'd hit first?]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Question 3: API Misuse

**What does a distracted junior engineer do wrong with this interface on their first use?**

Think: argument order confusion, forgetting to call cleanup, assuming defaults that aren't there,
passing the wrong type, calling in wrong order, ignoring return values.

**Answer:**

[What's the most likely misuse? What happens when they do it?]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Question 4: False Assumption

**Which claim in the research dossier is most likely to be wrong? What happens if it is?**

Read every claim in research_dossier.json. Pick the one you'd bet against.
What breaks if that claim is false?

**The claim most at risk:** [quote it]

**Why it might be wrong:** [reasoning]

**What breaks if it is:** [consequence]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Question 5: Missing Integration

**What existing system will this touch that isn't mentioned anywhere?**

Think: shared config files, global state, database schemas, auth middleware,
logging pipelines, monitoring hooks, CI systems, deploy scripts.

**Answer:**

[What's the unmentioned integration point? What's the contract with it?]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Question 6: The Obvious Unstated

**What is so obvious the author forgot to say it?**

This is the gap that everyone in the room already knows but never wrote down.
The thing that "goes without saying" — until it doesn't.

**Answer:**

[What's the unstated obvious thing? Say it explicitly.]

**New gaps to add to MMD_REPORT:**
- [ ] [Gap description if any]

---

## Summary

**Total new gaps found:** [count]
**Gaps added to MMD_REPORT.json:** [yes/no — if yes, list them]
**Biggest risk in this plan:** [one sentence]
