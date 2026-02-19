# G0 — Context Brief
**Feature:** Semantic Code Shape Matching
**Turn:** turns/002_semantic_matching
**Date:** 2026-02-19
**Context Owner:** MetaBlooms engineering

---

## 1. The Real User Story

The MMD pattern compliance gate (sub-check 6) is supposed to catch unaddressed
failure patterns before code is written. An operator declares their code shapes
in `research_dossier.json` and the gate matches them against the pattern library.

But in turn 001's own MMD report, every single pattern match was a false positive.
Five patterns matched three innocuous code shapes ("reads structured data and produces
formatted file output") and all five required waivers documenting that they didn't apply.

The specific engineer: anyone writing `code_shapes` in a research dossier. They
currently get noise — patterns that matched because the words overlapped, not because
the pattern is relevant to their code. They have to read each matched card, verify it
doesn't apply, and write a specific waiver. For five false positives on a three-entry
list, that's wasted work. Worse: engineers learn that the gate cries wolf, and their
waivers become less careful. The gate's credibility degrades with every false positive.

The frustration it removes: an engineer writing `"retry loop around external API call"`
should match `RETRY_AMPLIFICATION` and `NONIDEMPOTENT_RETRY` — not also
`DLQ_ACCUMULATION` and `CACHE_INVALIDATION_RACE` because "retry" and "call" appear
somewhere in those cards' trigger shapes.

---

## 2. Definition of Done

Done means: `registry.find_by_trigger("retry loop around external API call")` returns
`[RETRY_AMPLIFICATION, NONIDEMPOTENT_RETRY]` with no spurious matches.

And: `registry.find_by_trigger("reads structured data and produces formatted file output")`
returns `[]` — the same three code shapes that produced 5 false positives in turn 001's
MMD report produce zero matches after this feature ships.

**Testable right now:** run both queries against the new implementation and check
the results against these expected outputs. If the test passes, the feature is done.
The false positive waivers in `turns/001_monitoring_alert_gen/mmd/MMD_REPORT.json`
are the ground truth for what "noise" looks like — they must be eliminated.

---

## 3. Hidden Constraints

- **The pattern library is small.** Five cards, 3–5 trigger shapes each, totaling
  ~20 short sentences. TF-IDF with cosine similarity is sufficient and appropriate.
  Do not introduce a vector database, an embedding API call, or a neural model.
  The corpus will grow to maybe 50 cards. NumPy + scikit-learn is the right tool.

- **The existing `find_by_trigger()` API must not change.** `s3_mmd.py` calls it.
  `CLAUDE.md` documents it. External callers depend on it returning a ranked list of
  `PatternCard` objects. The implementation changes; the interface does not.

- **No internet access at match time.** The similarity computation must be local.
  TF-IDF vectors are computed from the pattern library at registry load time.
  No API calls, no model downloads, no network dependency.

- **scikit-learn is already the right dependency to add.** It is the standard Python
  ML toolkit, well-maintained, no GPU required, installs in seconds. If scikit-learn
  is not already in the environment, it should be added to requirements. It is not
  "overkill" — it is the minimum adequate tool for this job.

- **The threshold matters more than the algorithm.** TF-IDF cosine similarity returns
  a score between 0 and 1. The cutoff below which a match is discarded will determine
  recall vs. precision. Turn 001's false positives are the calibration dataset.
  The threshold must be validated against them before shipping.

---

## 4. Failure Cost

If the semantic matcher has a false negative (misses a real pattern match), an engineer
ships code with an unaddressed failure pattern that the gate was supposed to catch.
That's the same outcome as not having the gate at all for that pattern.

If the threshold is too permissive, we reproduce the false positive problem and
waiver credibility continues to degrade.

The calibration step (testing against turn 001's ground truth) is not optional.

---

## 5. Prior Attempts

The current keyword implementation in `find_by_trigger()` uses set intersection of
words. It was built knowing it was a placeholder — the five false positives in turn 001
are its documented failure cases. This is a direct replacement, not a new feature.
