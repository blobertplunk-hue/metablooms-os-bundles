# G1 — Adversarial MMD
**Feature:** Semantic Code Shape Matching

---

## adversarial_input
A card author writes a trigger shape that is a very long, generic sentence containing
common English words ("this pattern applies when a system processes data from any source
and produces any output"). This inflates the TF-IDF vocabulary with noise terms and
could match unrelated queries.

**Gap found:** none. TF-IDF stop-word filtering and IDF weighting suppress common
words. A long generic trigger shape would have near-zero IDF weight for its common
terms and would score low against any focused query. The algorithm handles this
correctly without special casing.

---

## scale_failure
At 50 cards with 5 trigger shapes each (250 documents), TF-IDF vectorization remains
sub-second. At 500 cards, it may reach tens of milliseconds but is still built once at
__init__ time. Not a scaling concern for this use case.

**Gap found:** The TF-IDF matrix is rebuilt on every PatternRegistry instantiation.
If the registry is instantiated repeatedly in a hot path (e.g., once per MMD request
in a hypothetical API), rebuild cost accumulates. **Resolution:** this is not a current
concern — the registry is instantiated once per pipeline run, not per request. Document
as a known limitation in the module docstring if it ever becomes a service.

---

## api_misuse
An engineer passes a very short query: `find_by_trigger("retry")`. Single-token query.
TF-IDF handles single tokens — the IDF weight of "retry" is high (it's specific),
so RETRY_AMPLIFICATION and NONIDEMPOTENT_RETRY will score well. QUEUE cards will score
low. This is correct behavior.

**Gap found:** none. Single-token queries work correctly with TF-IDF.

A second misuse: engineer passes an empty string `find_by_trigger("")`. The vectorizer
will produce a zero vector. Cosine similarity with a zero vector is undefined (or NaN).

**Gap found:** `find_by_trigger("")` must be guarded. If the query is empty or
whitespace-only after stripping, return `[]` immediately without calling the vectorizer.

---

## false_assumption
**Claim C2 is partially false** — already found in SEE. NONIDEMPOTENT_RETRY misses on
"retry loop around external API call" without the card fix. The SEE resolution
(add trigger shape to the card) is correct.

**Second assumption to challenge:** threshold=0.15 is stable as the card library grows.
As more cards are added, IDF weights shift (terms that were rare become less rare).
A term like "retry" that currently has high IDF weight will decrease in IDF weight as
more retry-related cards are added. This could push scores for existing queries below
the threshold over time.

**Gap found:** the threshold may need recalibration as the library grows. Document this
in the module: "threshold=0.15 is calibrated against 5 cards as of 2026-02-19. Recalibrate
after every 10 new cards by re-running the SEE calibration test."

---

## missing_integration
`s3_mmd.py` instantiates PatternRegistry inline: `registry = PatternRegistry()`. If
scikit-learn is not installed, this now raises an ImportError inside the MMD gate —
causing the entire pipeline to fail with a cryptic error rather than a clear message.

**Gap found:** the TF-IDF import must be guarded. If scikit-learn is unavailable,
fall back to the keyword matcher with a warning, not a hard failure. The gate should
degrade gracefully, not crash.

---

## obvious_unstated
The TF-IDF matrix is built from the trigger_shapes field only. The `name` and
`activation` fields also contain vocabulary that describes when a pattern applies.
A query like "retry amplification" would score well against the card name but not
necessarily against the trigger shapes alone.

**Gap found:** worth noting but not a blocker. Trigger shapes were designed to be
the matching surface — they are written specifically for this purpose. Including name
or activation would require reweighting and is a future enhancement, not a gap in
the current design.
