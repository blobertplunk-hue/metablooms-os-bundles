# MetaBlooms OS — ChatGPT Boot Prompt

## How to Use This System

### First Session (Fresh Boot)
1. Upload `MetaBlooms_OS.zip` to ChatGPT
2. Run this code:
```python
import zipfile, os, sys

# Extract
with zipfile.ZipFile("/mnt/data/MetaBlooms_OS.zip", "r") as z:
    z.extractall("/mnt/data/")

# Boot
sys.path.insert(0, "/mnt/data/MetaBlooms_OS")
os.chdir("/mnt/data/MetaBlooms_OS")
from boot import boot
mpp, state, os_root = boot()
```

3. The system will print its intelligence summary (level 0 on first boot)
4. Give it a task using the task template below

### Continuing Sessions (With Prior State)
1. Upload BOTH `MetaBlooms_OS.zip` AND your saved `MB_STATE.json`
2. Run:
```python
import zipfile, os, sys, shutil

# Extract
with zipfile.ZipFile("/mnt/data/MetaBlooms_OS.zip", "r") as z:
    z.extractall("/mnt/data/")

# Restore prior state
shutil.copy("/mnt/data/MB_STATE.json", "/mnt/data/MetaBlooms_OS/state/MB_STATE.json")

# Boot
sys.path.insert(0, "/mnt/data/MetaBlooms_OS")
os.chdir("/mnt/data/MetaBlooms_OS")
from boot import boot
mpp, state, os_root = boot()
```

3. The system will load your prior intelligence and show accumulated knowledge

### Saving State After a Session
At the end of EVERY session, download `MB_STATE.json`:
```python
# Save state
state.save()
print("Download this file to preserve intelligence:")
print(f"  {os.path.join(os_root, 'state', 'MB_STATE.json')}")
```

---

## Task Template

After booting, give your task using this format:

```python
# Step 1: Prepare (Phases -1 through 0.5)
ready, ctx = mpp.run_preparation_phases(
    task_type="CODE_GENERATION",  # or STRUCTURAL_ANALYSIS, RESEARCH, POLICY
    task_description="Build a web scraper that extracts product prices from e-commerce sites",
    domain="web_scraping"
)
```

The system will:
1. Declare enforcement capabilities (EVIDENCE_ONLY mode)
2. Declare environment (ChatGPT sandbox)
3. Initialize claim registry
4. Check for prior mastery definitions in this domain

Then YOU (the human) need to populate claims and mastery definition before execution:

```python
# Step 2: Populate claims (you + the LLM collaborate on this)
claims = [
    {"claim_id": "CLM-001", "text": "BeautifulSoup is the best library for this task", "type": "ARCHITECTURAL", "evidence_required": True},
    {"claim_id": "CLM-002", "text": "Rate limiting at 1 req/sec is sufficient", "type": "PRESCRIPTIVE", "evidence_required": True},
]

# Step 3: Create mastery definition
mastery, errors = mpp.mastery_engine.create_mastery_definition(
    task_description="Build a web scraper that extracts product prices",
    domain="web_scraping",
    best_practitioners=[
        {"name": "Scrapy project", "why_relevant": "Most popular Python scraping framework"}
    ],
    standards=[
        {"standard": "Respect robots.txt", "claim_strength": "SUPPORTED"}
    ],
    world_class_standard="A world-class web scraper handles pagination, rate limiting, error recovery, and respects site policies. It extracts structured data with >99% accuracy.",
    success_criteria=[
        {"criterion_id": "SC-001", "description": "Extracts prices with >99% accuracy", "measurable": True, "required": True, "measurement_method": "Compare extracted vs manual count on 100 products"},
        {"criterion_id": "SC-002", "description": "Handles pagination automatically", "measurable": True, "required": True, "measurement_method": "Test on site with 10+ pages"},
    ],
    knowledge_gaps=[
        {"gap_id": "KG-001", "description": "Which parsing library handles dynamic JS content?", "see_query": "best python library for dynamic web scraping", "status": "OPEN"},
    ],
    constraints={
        "environmental": ["ChatGPT sandbox has no network access — must generate code, not run it"],
        "domain_specific": ["Must respect robots.txt"],
        "governance": ["All architectural choices need DECISION_RECORD"]
    },
    see_queries_used=["python web scraping best practices 2026"]
)

# Step 4: Execute (Phases 1 through 7.5)
receipt = mpp.run_execution_phases(
    claims=claims,
    mastery_definition=mastery,
    build_artifacts=[],  # Populated by BUILD phase
    execution_results={}  # Populated after execution
)
```

---

## What This System Does

MetaBlooms OS is a **meta-competence engine**. For ANY task:

1. **SURFACE** (Phase 0): What claims am I making? Enumerate them.
2. **DEFINE** (Phase 0.5): What does world-class look like? Define success criteria.
3. **RESEARCH** (Phase 1): What evidence exists? Gather it honestly.
4. **DETECT** (Phase 2): What's missing? Find every gap.
5. **GATE** (Phase 2.5-2.75): Can we actually do this? Validate reality.
6. **BUILD** (Phase 3): Now execute — with full knowledge.
7. **REFINE** (Phase 4-5): Evaluate. Fix only what's enumerated. Max 2 iterations.
8. **VERIFY** (Phase 6): Did we meet mastery criteria?
9. **RECORD** (Phase 7): Receipt with SHA-256 hashes of every artifact.
10. **LEARN** (Phase 7.5): Extract lessons. Promote observations to invariants over time.

### Cross-Session Intelligence

The MB_STATE.json file accumulates:
- **Mastery Definitions**: What "world-class" means for each domain you've worked in
- **Decision Records**: Every architectural choice with constraints, candidates, and rejections
- **Lesson Promotions**: OBSERVATION → HYPOTHESIS → CONSTRAINT → INVARIANT lifecycle
- **Source Reputation**: Which sources proved reliable across sessions
- **Query Patterns**: Which research queries produced useful results

Intelligence level is computed as:
```
mastery_definitions * 3 + decision_records * 2 + lessons * 1
+ promoted_constraints * 5 + promoted_invariants * 10
```

Every session makes the system measurably smarter.

### Key Engines

| Engine | Purpose | File |
|--------|---------|------|
| **MasteryEngine** | Defines what world-class looks like | `engines/mastery_engine.py` |
| **SEEEngine** | Gathers evidence for claims | `engines/see_engine.py` |
| **MMDEngine** | Detects missing middles and gaps | `engines/mmd_engine.py` |
| **DecisionEngine** | Constraint-driven architectural decisions | `engines/decision_engine.py` |
| **RRPEngine** | Recursive refinement with convergence | `engines/rrp_engine.py` |
| **AssimilationEngine** | Extracts and promotes lessons | `engines/assimilation_engine.py` |

### Making Architectural Decisions

Instead of guessing, use the Decision Engine:

```python
record, errors = mpp.decision_engine.make_decision(
    decision_type="TOOL_SELECTION",
    context="Need a Python library for HTML parsing",
    mastery_definition=mastery,
    additional_constraints=[
        {"constraint": "Must handle malformed HTML", "source": "domain_requirement", "hard": True},
        {"constraint": "Prefer libraries with active maintenance", "source": "best_practice", "hard": False}
    ],
    additional_candidates=[
        {"name": "BeautifulSoup", "description": "Lenient HTML parser", "source": "common_knowledge"},
        {"name": "lxml", "description": "Fast XML/HTML parser", "source": "common_knowledge"},
        {"name": "html5lib", "description": "Standards-compliant parser", "source": "common_knowledge"},
    ]
)
```

The engine will:
1. Extract constraints from mastery definition + R2.5 + your additions
2. Enumerate candidates from pattern catalog + your additions + prior decisions
3. Eliminate candidates violating hard constraints
4. Score survivors against soft constraints
5. Select with evidence and reject with reasons
6. Store the decision for cross-session learning

---

## The Manifesto

> MetaBlooms is a jack of all trades and a master of all — not by knowing
> everything upfront, but by being able to determine, for any task, what
> mastery requires; define what "world-class" means for that task; identify
> what is missing; acquire the necessary knowledge, constraints, and
> structure; and refuse execution when mastery cannot be responsibly achieved.

This system implements that manifesto mechanically.
