# Pattern Study: LEADER_ELECTION_SPLIT_BRAIN
**Status:** NEEDS_RESEARCH
**Assigned:** unassigned
**Protocol:** `mpp/patterns/STUDY_PROTOCOL.md`
**Target card:** `mpp/patterns/cards/LEADER_ELECTION_SPLIT_BRAIN.json`

---

## Phase 1 — Pattern Identity

**Code shape:**
Any system where one node (or a small set) is elected as the authoritative writer,
scheduler, or coordinator — and all other nodes defer to it. Includes: distributed
lock holders, Kafka partition leaders, database primary nodes, job scheduler
singletons, leader-elected microservices. The pattern activates when the election
mechanism fails to converge on a single leader.

**Failure hypothesis:**
A network partition or heartbeat delay causes the existing leader to appear dead to
part of the cluster. That partition elects a new leader. The original leader, which
is still alive but cannot see the rest of the cluster, continues operating. Both
leaders now accept writes. The system has split-brain: two authoritative nodes
writing independently to (potentially) the same state, with no conflict detection.

**Likely pattern class:** `architectural`

**Working name:** `LEADER_ELECTION_SPLIT_BRAIN`

**Is this covered by an existing card?**
No existing card covers distributed consensus failures. This pattern requires its own
card because the signal sequence is unique (both leaders appear healthy from their
own perspective) and the countermeasures involve fencing tokens and quorum, which
are distinct from retry or queue countermeasures.

---

## Phase 2 — Targeted Research Directions

### Q1 — Activation condition
The activation is not the network partition itself — it is the *election of a second
leader before the first one steps down*. Research: what is the specific timing window
in which split-brain can occur? This depends on:
- Heartbeat interval
- Election timeout
- Whether the old leader has a mechanism to detect its own isolation

**Key distinction:** Raft and Paxos are designed to prevent split-brain. Research
what actually *causes* split-brain in systems that claim to use these protocols —
typically it is misconfiguration, not a fundamental algorithm failure.

### Q2 — Causal mechanism
Two distinct paths:
1. **GC pause / process freeze path:** The leader is alive but unresponsive for longer
   than the election timeout (GC pause, disk flush, swapping). The cluster elects a
   new leader. The paused leader resumes, does not know it was replaced, continues
   writing.
2. **Network partition path:** True network split. Each partition has a quorum
   (possible in even-node clusters without a tiebreaker). Both partitions elect a leader.

Research: which path is more common in real incidents? The GC pause path is more
common in JVM-based systems (ZooKeeper, old Kafka versions).

### Q3 — Signal sequence
The invisible phase is the most dangerous aspect of this pattern: both leaders
report healthy. Both are processing requests. Metrics show normal throughput on
both sides of the partition. The divergence accumulates silently.

**Find:** what is the first observable signal that split-brain has occurred?
Is it data divergence (detected by reconciliation), client errors (when a client
switches from one leader to another and sees inconsistent state), or a protocol-level
alert (ZooKeeper session expiry, Raft term mismatch)?

### Q4 — Why it's invisible
Each leader's health check passes — it can still accept writes and reads. The cluster
health check may show a degraded state (reduced replica count) but many systems are
designed to continue operating in a degraded state. Operators see "reduced redundancy"
not "split-brain." The divergence is only detected when the partition heals and the
two state histories must be reconciled.

**Find a postmortem** where split-brain caused data corruption or data loss.
Candidates: MongoDB split-brain incidents (pre-4.0), Elasticsearch split-brain
(well-documented), Redis Sentinel split-brain, etcd misconfiguration incidents.

### Q5 — Threshold
Split-brain risk is not a function of load — it is a function of cluster topology.
Research: what cluster sizes and topologies make split-brain more likely?
- Even number of nodes without a tiebreaker
- Three nodes where the single follower can reach neither of the other two
- Clusters that span availability zones with asymmetric network reliability

**Find:** the specific node count and topology where the probability of split-brain
on a random network partition is highest.

### Q6 — Diagnostic
The diagnostic must detect that two nodes believe they are the leader simultaneously.
Research: does every major distributed system expose a "current term" or "current epoch"
metric that would surface a divergence? Specific systems to check:
- Kafka: `kafka.controller:type=KafkaController,name=ActiveControllerCount`
  should be exactly 1 — what does it show during split-brain?
- etcd: leader election metrics
- ZooKeeper: `ruok` and `stat` commands and what they reveal

**The diagnostic should be a single command** that returns a clear split-brain signal.

### Q7 — Countermeasures
Research direction: fencing tokens are the canonical defense — every write includes
a monotonically increasing token issued by the lock/election service; the storage
layer rejects writes with a lower token than the last seen. Research which storage
systems support this natively and which require application-level implementation.

Also research:
- **STONITH (Shoot The Other Node In The Head):** when the new leader is elected,
  it takes an action to definitively terminate the old leader before accepting writes
- **Lease-based leadership:** leader leases expire after a fixed time; the leader
  must renew; if it cannot renew (network partition), it steps down before the lease expires
- **Quorum reads:** reading from a quorum before accepting writes (Raft's approach)

### Q8 — Trigger shapes
Draft trigger shapes:
- "Distributed lock holder that does not check its lock lease before each write"
- "Leader-elected service where the leader is the only writer to a shared resource"
- "Cluster of even node count without an explicit tiebreaker or arbiter"
- "System that uses heartbeat-based failure detection with a timeout shorter than possible GC pause"
- "Database replication setup where the replica can be promoted without the primary's participation"

---

## Known Incidents to Search

- Elasticsearch split-brain incidents (pre-7.0 "minimum_master_nodes" misconfiguration) —
  extensively documented in the community
- MongoDB split-brain (pre-4.0 writeConcern behavior) — multiple postmortems exist
- Aphyr's "Jepsen" series — tests distributed systems for split-brain and documents failures
  in real databases (etcd, Redis, Cassandra, Riak) — best source in the field
- AWS RDS Multi-AZ failover edge cases — AWS has documented split-brain edge cases
- Martin Kleppmann's "Designing Data-Intensive Applications" Chapter 8 — foundational

## Open Questions for Adversarial Phase

1. Does a Raft-based system (etcd, CockroachDB) actually prevent split-brain, or does
   it prevent split-brain *with data loss* while still allowing brief periods of two
   leaders if the old leader has an uncommitted GC pause?
2. If fencing tokens are used, what happens when the storage layer that validates the
   token is itself partitioned? Does the token validation become the new single point
   of failure?
3. Is STONITH actually reliable, or does the STONITH action itself fail in the same
   network conditions that caused the election?

---

## Ready to Run?

When you pick this up:
1. Read `mpp/patterns/STUDY_PROTOCOL.md` — full protocol
2. Answer all 8 research questions with cited sources
3. Have a different reviewer run the adversarial check (Phase 3)
4. Write `mpp/patterns/cards/LEADER_ELECTION_SPLIT_BRAIN.json` using the template
5. Run the registry to validate: `python -c "from mpp.patterns import PatternRegistry; r = PatternRegistry(); print(r.render_index())"`
