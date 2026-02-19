# mpp-patterns

Failure pattern library for software engineers. Structured knowledge cards describing
how distributed systems fail, with semantic code-shape matching, Prometheus alert
generation, and waiver accuracy tracking.

## Install

```bash
pip install mpp-patterns           # core (keyword matching)
pip install mpp-patterns[semantic] # + TF-IDF semantic matching (recommended)
pip install mpp-patterns[server]   # + shared waiver log HTTP server
```

## Use in any Python project

```python
from mpp.patterns import PatternRegistry

registry = PatternRegistry()

# Describe what your code does — get the failure patterns that apply
matches = registry.find_by_trigger("retry loop around an external API call")
for card in matches:
    print(registry.render_card(card))

# Generate Prometheus alerts for all patterns
from mpp.patterns.alert_gen import generate_all
generate_all(output_dir="./alerts/", platform="prometheus")
```

## CLI

```bash
# Generate all Prometheus alert files
mpp-alerts --all --platform prometheus

# Check a diff for pattern matches (CI / pre-push)
git diff HEAD | mpp-check

# Run the shared waiver log server
mpp-server --host 0.0.0.0 --port 8765

# Check a PR diff and output a markdown comment
git diff origin/main...HEAD | mpp-pr
```

## Patterns (11 active cards)

| ID | Name | Class |
|---|---|---|
| RETRY_AMPLIFICATION | Retry amplification in call chains | architectural |
| NONIDEMPOTENT_RETRY | Non-idempotent retry on stateful operations | operational |
| QUEUE_LAG_SILENT | Sustained queue lag without a traffic spike | architectural |
| DLQ_ACCUMULATION | Dead letter queue accumulation | operational |
| CACHE_INVALIDATION_RACE | Cache invalidation race without versioning | data |
| CONNECTION_POOL_EXHAUSTION | Connection pool exhaustion from slow consumers | operational |
| DISTRIBUTED_TRANSACTION_ROLLBACK_GAP | Distributed transaction rollback gap | data |
| RATE_LIMITER_THUNDERING_HERD | Rate limiter thundering herd on window reset | architectural |
| LEADER_ELECTION_SPLIT_BRAIN | Leader election split-brain from network partition | architectural |
| BATCH_JOB_MEMORY_PRESSURE | Batch job memory pressure from unbounded result sets | operational |
| FAN_OUT_AMPLIFICATION | Fan-out amplification on high-cardinality events | architectural |

## Works in ChatGPT code interpreter

scikit-learn is pre-installed in ChatGPT's sandbox. After `!pip install mpp-patterns[semantic]`,
the full library works including semantic matching.
