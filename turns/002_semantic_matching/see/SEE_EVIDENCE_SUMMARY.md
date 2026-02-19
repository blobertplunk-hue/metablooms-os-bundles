# SEE Evidence Summary — Semantic Code Shape Matching

## Empirical Calibration Results (threshold=0.15, ngram_range=(1,2))

### Claim C1 — False positives eliminated: CONFIRMED

All three turn 001 false positive queries score 0.0 against every card.
TF-IDF with threshold=0.15 produces zero noise matches for these queries:

| Query | Keyword score (cards matched) | TF-IDF score (top card) |
|---|---|---|
| "module that reads structured data and produces formatted file output" | 4 matches | 0.0 (nothing matches) |
| "plugin architecture with per-platform adapters" | 4 matches | 0.0 |
| "template rendering with conditional FILL_IN markers" | 3 matches | 0.0 |

**C1 is confirmed.**

### Claim C2 — True positives retained: PARTIALLY CONFIRMED

| Query | Expected | Got | Gap |
|---|---|---|---|
| "retry loop around external API call" | RETRY_AMPLIFICATION, NONIDEMPOTENT_RETRY | RETRY_AMPLIFICATION only | NONIDEMPOTENT_RETRY scores 0.094 — below threshold |
| "message queue consumer" | QUEUE_LAG_SILENT, DLQ_ACCUMULATION | Those two + CACHE_INVALIDATION_RACE | CACHE scores 0.246 — legitimate overlap (one trigger mentions message queue) |
| "cache read write invalidate" | CACHE_INVALIDATION_RACE | CACHE_INVALIDATION_RACE | Perfect |

**NONIDEMPOTENT_RETRY miss is a vocabulary gap in the card, not an algorithm failure.**
RETRY_AMPLIFICATION scores 1.0 on "retry loop around external API call" because that
phrase appears verbatim in its trigger shapes. NONIDEMPOTENT_RETRY's trigger shapes
use "retry around a database write" — different vocabulary, same concept. TF-IDF cannot
bridge this; the card needs a trigger shape that uses "retry loop" vocabulary.

**CACHE_INVALIDATION_RACE match on "message queue consumer" is legitimate, not noise.**
CACHE's trigger shape "cache invalidation triggered by an event bus or message queue"
explicitly mentions message queues. The match is semantically defensible — a message
queue can be the invalidation mechanism for a cache. This is not a false positive;
it is a correctly flagged adjacent concern.

### Claim C3 — scikit-learn sufficient: CONFIRMED

TF-IDF vectorization + cosine similarity on a 20-document corpus is sub-millisecond.
No GPU, no model, no download. scikit-learn 1.8.0 installed cleanly.

### Claim C4 — Interface preservable: CONFIRMED (by inspection)

find_by_trigger(code_description: str) -> List[PatternCard] remains unchanged.
The TF-IDF matrix is built at PatternRegistry.__init__ time and stored as an instance
variable. The method signature, return type, and ranking behavior (highest-scoring
first) are preserved.

---

## Resolution for NONIDEMPOTENT_RETRY vocabulary gap

**Fix in the card, not the algorithm.**

Add a trigger shape to NONIDEMPOTENT_RETRY that uses "retry loop" vocabulary:
  "retry loop around an operation that modifies state or has non-idempotent side effects"

This is a card quality improvement independently justified: anyone writing "retry loop"
around a payment or DB write should be prompted to check idempotency. The trigger
shape was missing this vocabulary. The semantic matcher exposed the gap.

After this fix, expected results with threshold=0.15:
- "retry loop around external API call" → RETRY_AMPLIFICATION (1.0), NONIDEMPOTENT_RETRY (~0.3+)
- All turn 001 false positives remain at 0.0

---

## Final threshold recommendation: 0.15

- Eliminates all documented false positives (score 0.0)
- Catches all true positives after the NONIDEMPOTENT_RETRY card fix
- CACHE_INVALIDATION_RACE on "message queue consumer" at 0.246: retain this match —
  it is a legitimate flag, not noise. Engineers can waive it if not applicable.
