# Pattern Studies — Research Queue

These are pre-scoped research briefs for patterns that have been identified as
important but not yet researched and committed as ACTIVE cards.

Each study document does the work of Phase 1 (naming, hypothesis, existing-card check)
and gives targeted research directions for Phase 2, so a researcher can pick one up
and start immediately without having to frame the problem from scratch.

**To run a study:** read the study document, then follow `mpp/patterns/STUDY_PROTOCOL.md`.

---

## Open Studies

| Pattern ID | Class | Key failure | Hardest part to research |
|---|---|---|---|
| [CONNECTION_POOL_EXHAUSTION](CONNECTION_POOL_EXHAUSTION.md) | operational | DB connections drained; new requests queue/fail; health checks pass | Why pool exhaustion looks like a DB error, not a pool error |
| [DISTRIBUTED_TRANSACTION_ROLLBACK_GAP](DISTRIBUTED_TRANSACTION_ROLLBACK_GAP.md) | data | Multi-service write partially commits; rollback fails; silent data divergence | Finding a postmortem where this was the actual root cause |
| [RATE_LIMITER_THUNDERING_HERD](RATE_LIMITER_THUNDERING_HERD.md) | architectural | Rate limiter blocks clients; all retry at window reset; spike exceeds original load | Quantifying the jitter required to desynchronize N clients |
| [LEADER_ELECTION_SPLIT_BRAIN](LEADER_ELECTION_SPLIT_BRAIN.md) | architectural | Two nodes both believe they are leader; both write; state diverges | Finding real incidents in systems that claim split-brain immunity |
| [BATCH_JOB_MEMORY_PRESSURE](BATCH_JOB_MEMORY_PRESSURE.md) | operational | Batch job OOMed; restarts; OOMs again; silent restart loop; no progress | Detecting OOM restart loops before they've been running for hours |
| [FAN_OUT_AMPLIFICATION](FAN_OUT_AMPLIFICATION.md) | architectural | Fan-out to N services; compound error rate and tail latency grow with N | Distinguishing this from normal intermittent failures in monitoring |

---

## How Studies Become Cards

1. Researcher picks a study and runs `STUDY_PROTOCOL.md` Phases 2–5
2. Card is written with status `DRAFT` in `mpp/patterns/cards/`
3. Adversarial check (Phase 3) is completed by a different reviewer
4. Card goes through full MPP review (G0 → TEST)
5. G2 passes → status changes to `ACTIVE`
6. Study document is deleted (the card is the artifact, not the study)

---

## Suggesting a New Study

If you encounter a code shape with no pattern card and no study:
1. Check the registry: `registry.find_by_trigger("<your code description>")`
2. If no match, create a new study document in this directory using the format above
3. Fill in Phase 1 and as much of the Phase 2 research directions as you know
4. The study document does not go through MPP — it is just a research brief
5. The resulting card does go through MPP
