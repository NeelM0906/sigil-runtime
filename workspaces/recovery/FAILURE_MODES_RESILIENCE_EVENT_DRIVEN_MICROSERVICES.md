# Failure Modes & Resilience Strategies in Event-Driven Microservices

**Author:** SAI Recovery 🌱  
**Date:** 2026-03-05  
**Context:** Companion to Scholar's Academic Foundations and Forge's Real-World Implementation Patterns  
**Source Integrity:** No fabricated sources. All claims are based on well-established distributed systems principles, official documentation, or explicitly flagged when unverified.

---

## Table of Contents

1. [Common Failure Modes](#1-common-failure-modes)
2. [Idempotency Strategies](#2-idempotency-strategies)
3. [Dead Letter Queues & Poison Message Handling](#3-dead-letter-queues--poison-message-handling)
4. [Data Consistency Recovery](#4-data-consistency-recovery)
5. [Disaster Recovery & Replayability](#5-disaster-recovery--replayability)
6. [Chaos Engineering for Event Systems](#6-chaos-engineering-for-event-systems)
7. [Operational Anti-Patterns](#7-operational-anti-patterns)

---

## 1. Common Failure Modes

Event-driven architectures introduce failure modes that are fundamentally different from synchronous request-response systems. In RPC-style systems, failure is immediate and visible — a timeout, an error code. In event-driven systems, failure is often **silent, delayed, and cumulative**.

### 1.1 Message Loss

**What happens:** Events are produced but never consumed. Data is silently dropped.

**Root causes:**
- **At-most-once delivery without acknowledgment:** A consumer processes a message, crashes before committing its offset/acknowledgment, and the broker considers it delivered. Or conversely, the broker accepts a publish without flushing to disk.
- **Unclean broker shutdown:** Kafka defaults to `acks=1` (leader-only acknowledgment). If the leader crashes before replicating to followers, the message is lost. Setting `acks=all` with `min.insync.replicas=2` mitigates this.
- **Network partitions during publish:** A producer sends a message, the connection drops, the producer doesn't receive the acknowledgment, and retries may or may not succeed depending on configuration.
- **Misconfigured retention policies:** Events expire before consumers process them.

**Detection strategies:**
- End-to-end event counting: produce-side counters compared against consume-side counters.
- Monotonic sequence IDs in event payloads — gaps indicate loss.
- Lag monitoring combined with retention alerting.

**Severity in recovery context:** In medical revenue recovery, message loss could mean a filing deadline passes silently. **This is the most dangerous failure mode for our domain.**

### 1.2 Duplicate Delivery

**What happens:** The same event is delivered and processed more than once.

**Root causes:**
- **At-least-once delivery semantics:** Most brokers (Kafka, RabbitMQ, Pulsar) default to at-least-once. If a consumer processes a message but crashes before committing the offset, the message is redelivered on restart.
- **Producer retries:** When `acks` timeout, producers retry — if the original message was actually persisted, the broker now has two copies.
- **Consumer group rebalancing:** During a rebalance, partitions are reassigned. If a consumer had processed messages but not committed offsets, the new assignee reprocesses them.
- **Network retransmissions:** TCP-level retries can occasionally cause duplicates at the application layer in poorly designed protocols.

**Impact:** Duplicate processing can cause double payments, double filings, double notifications — all operationally dangerous.

**Mitigation:** See Section 2 (Idempotency Strategies).

### 1.3 Out-of-Order Processing

**What happens:** Events arrive or are processed in a different order than they were produced.

**Root causes:**
- **Multi-partition topics:** Kafka guarantees ordering only within a single partition. If events for the same entity land on different partitions (due to missing or changing partition keys), ordering is lost.
- **Consumer parallelism:** Multiple consumers processing from the same partition (or multiple threads within one consumer) can reorder execution.
- **Retry-induced reordering:** A failed message goes to retry/DLQ while subsequent messages for the same entity proceed.
- **Multi-producer scenarios:** Two services produce events about the same entity; no global ordering exists.
- **Cross-topic consumption:** When a service consumes from multiple topics, there is no ordering guarantee across them.

**Impact example:** A `ClaimApproved` event processed before `ClaimSubmitted` would corrupt state.

**Mitigation strategies:**
- **Partition key design:** Use entity ID (e.g., `claim_id`) as the partition key to ensure all events for one entity go to one partition.
- **Sequence numbers in payloads:** Embed a monotonically increasing sequence number per entity. Consumers reject or reorder based on sequence.
- **Event timestamps + version vectors:** Use logical clocks, not wall clocks, for causal ordering.
- **Single-writer principle:** Only one service writes events for a given entity, eliminating multi-producer conflicts.

### 1.4 Poison Messages

**What happens:** A single malformed, corrupt, or semantically invalid event causes the consumer to crash or enter an infinite retry loop, blocking all subsequent messages on that partition.

**Root causes:**
- Schema-incompatible events (see 1.6)
- Null or missing required fields
- Events referencing entities that don't exist in the consumer's state
- Serialization/deserialization failures
- Events that trigger application bugs (e.g., division by zero, stack overflow)

**Why it's especially dangerous:** In ordered, partitioned systems like Kafka, a poison message blocks the entire partition. No subsequent messages can be processed until the poison message is dealt with. This converts a single-event problem into a system-wide stall.

**Mitigation:** See Section 3 (DLQ and Poison Message Handling).

### 1.5 Consumer Lag Spirals

**What happens:** A consumer falls behind the producer rate. The backlog grows. The growing backlog causes the consumer to work harder (more memory, more I/O), which makes it slower, which increases the backlog further. A positive feedback loop.

**Root causes:**
- **Slow downstream dependencies:** The consumer calls a slow database or external API.
- **Insufficient consumer instances:** Not enough parallelism for the throughput.
- **Garbage collection pressure:** Large backlogs increase heap usage, triggering GC pauses, further slowing processing.
- **Rebalancing storms:** Frequent rebalancing causes stop-the-world pauses across the consumer group.
- **Batch size misconfiguration:** Too-large batches cause processing timeouts; too-small batches cause overhead.

**Detection:**
- Consumer lag metrics (Kafka: `records-lag-max`, `records-lag` per partition)
- Tools: Burrow (LinkedIn, open source), Kafka Exporter for Prometheus
- Alert when lag exceeds N messages OR when lag is growing continuously for M minutes

**Mitigation:**
- Auto-scaling consumer instances based on lag metrics
- Back-pressure mechanisms (if the architecture supports them)
- Priority processing: skip or defer low-priority events when lag exceeds thresholds
- Circuit breakers on slow downstream calls (fail fast rather than block the consumer)

### 1.6 Schema Incompatibility at Runtime

**What happens:** A producer publishes events with a schema that the consumer cannot deserialize or semantically process.

**Root causes:**
- **Breaking schema changes:** Removing a required field, changing a field type, renaming fields without aliases.
- **Missing schema registry validation:** Publishing events without compatibility checks.
- **Incompatible evolution strategies:** Producer uses FORWARD compatibility; consumer expects BACKWARD compatibility.
- **Version skew during deployments:** New producer deployed before consumers are updated, or vice versa.

**Impact:** Mass deserialization failures across all consumers of that topic. Effectively converts every message into a poison message.

**Mitigation:**
- **Schema registry with compatibility enforcement:** Confluent Schema Registry supports BACKWARD, FORWARD, FULL, and NONE compatibility modes. Use FULL for maximum safety.
- **Schema validation on publish:** Reject events that don't conform to the registered schema before they enter the broker.
- **Consumer-side defensive deserialization:** Use lenient/tolerant readers that handle unknown fields gracefully (Avro's reader schema evolution supports this natively).
- **Canary deployments for schema changes:** Deploy the new consumer first (it should handle both old and new schemas), then deploy the new producer.

### 1.7 Split-Brain Scenarios

**What happens:** A network partition causes two or more subsystems to operate independently, each believing it is authoritative. When the partition heals, conflicting state must be reconciled.

**Root causes:**
- Network partitions between data centers
- Broker cluster splits (e.g., Kafka controller isolation)
- Consumer group coordination failures (ZooKeeper/KRaft quorum loss)

**Impact in event-driven systems:**
- Dual leaders for the same partition, leading to divergent logs
- Consumers in different partitioned segments processing conflicting event streams
- Event stores with conflicting append histories

**Mitigation:**
- **Quorum-based replication:** Kafka's ISR (In-Sync Replicas) mechanism with `min.insync.replicas` prevents split-brain writes.
- **Fencing tokens:** Use epoch-based fencing to ensure only one legitimate leader can write.
- **CRDTs for state:** If split-brain is tolerated by design (e.g., multi-region active-active), use Conflict-Free Replicated Data Types for state that can be merged after partition heals.
- **Detection:** Monitor controller elections, ISR shrink events, and unclean leader elections (Kafka metric: `unclean-leader-elections-per-sec`).

### 1.8 Cascading Failures from Slow Consumers

**What happens:** One slow consumer service causes back-pressure that propagates upstream through the system. In event-driven systems, this manifests differently than in synchronous systems — it's often delayed and harder to detect.

**Cascade pattern:**
1. Consumer C is slow (database overloaded)
2. Consumer C's lag grows
3. If the architecture uses synchronous bridges anywhere (e.g., request-reply patterns, HTTP calls within event handlers), upstream services start timing out
4. Upstream services' own processing slows
5. Their consumers fall behind
6. The cascade propagates

**Mitigation:**
- **Full asynchronous decoupling:** The primary defense. If consumers are truly decoupled (no synchronous calls back to producers or shared resources), slow consumers can't cascade upstream.
- **Bulkheads:** Isolate consumer groups and their resources (thread pools, connection pools, database connections) so one failing consumer can't starve others.
- **Circuit breakers on external calls within consumers:** Fail fast when downstream dependencies are slow.
- **Timeout budgets:** Each processing step gets a bounded time allocation; exceeded budgets trigger graceful degradation.
- **Backpressure-aware producers:** Producers can check topic/queue depth before publishing and apply their own throttling.

---

## 2. Idempotency Strategies

The fundamental reality: **exactly-once delivery does not exist in distributed systems.** What exists is exactly-once *semantics* — the appearance of exactly-once processing achieved through at-least-once delivery combined with idempotent processing.

This is a well-established principle in distributed systems literature. (Leslie Lamport, Nancy Lynch, and others have formalized the impossibility of exactly-once delivery in the presence of network partitions — this follows directly from the Two Generals Problem and FLP impossibility.)

### 2.1 Idempotency Keys

**Pattern:** Every event carries a unique, deterministic identifier. The consumer tracks which identifiers it has already processed and skips duplicates.

**Implementation approaches:**

| Approach | Pros | Cons |
|----------|------|------|
| **Event ID in payload** | Simple, explicit | Requires dedup store |
| **Natural business key** | No extra ID needed | Not always available |
| **Hash of event content** | Deterministic | Hash collisions (theoretical); content-identical events may be legitimately distinct |
| **Producer-assigned sequence** | Enables gap detection too | Requires producer-side state |

**Deduplication store requirements:**
- Must be checked atomically with processing (or within the same transaction)
- Must have bounded retention (you can't store every ID forever)
- Options: database table, Redis SET with TTL, Bloom filter (probabilistic — accepts false positives for space efficiency)

**Deduplication window:** The time window during which duplicate detection is active. Typically 24 hours to 7 days. Must exceed the maximum possible retry/redelivery delay. If a message can be redelivered after 48 hours (e.g., from a DLQ replay), the dedup window must be >48 hours.

### 2.2 Transactional Outbox Pattern

**Problem:** A service needs to update its database AND publish an event. These are two different systems. If the service updates the database but crashes before publishing, the event is lost. If it publishes first but crashes before the database commit, the event describes a state change that never happened.

**Solution:** Write the event to an "outbox" table in the same database, within the same transaction as the state change. A separate process (relay/poller or log reader) reads from the outbox and publishes to the broker.

**Implementation:**

```
BEGIN TRANSACTION;
  UPDATE claims SET status = 'approved' WHERE id = 123;
  INSERT INTO outbox (id, topic, key, payload, created_at)
    VALUES (uuid(), 'claims', '123', '{"status":"approved",...}', NOW());
COMMIT;
```

A separate **outbox relay** process:
1. Polls the outbox table (or uses database triggers/notifications)
2. Publishes each outbox record to the message broker
3. Marks the outbox record as published (or deletes it)

**Key considerations:**
- The relay must be idempotent (it may re-read and re-publish outbox records — consumers must handle duplicates)
- Ordering: the outbox table provides a natural ordering (auto-increment ID or timestamp), which the relay preserves
- Polling interval creates a latency floor (typically 100ms–1s)
- At scale, the outbox table needs cleanup (delete published records) to prevent unbounded growth

**This is the most widely recommended pattern for reliable event publishing.** It appears in Microservices Patterns by Chris Richardson (2018), and is used in production at multiple large organizations.

### 2.3 Change Data Capture (CDC)

**Pattern:** Instead of the application explicitly writing to an outbox, use CDC to capture database changes (inserts, updates, deletes) from the database's transaction log and publish them as events.

**Tools:**
- **Debezium** (Red Hat, open source) — the most widely adopted CDC platform. Reads MySQL binlog, PostgreSQL WAL, MongoDB oplog, etc. Publishes to Kafka.
- **AWS DMS** — managed CDC for AWS databases
- **Maxwell** — lightweight MySQL binlog → Kafka connector

**Advantages over explicit outbox:**
- No application code changes needed to publish events
- Guaranteed to capture every committed transaction (the WAL/binlog is the source of truth)
- No dual-write problem — there's only one write (to the database)

**Disadvantages:**
- Events are database-level (row changes), not domain-level — they need transformation to become meaningful domain events
- Schema coupling: consumers now depend on database schema
- Operational complexity: managing CDC connectors, handling schema changes in the source database
- Ordering: CDC preserves per-table ordering but cross-table ordering depends on the database's transaction log structure

**Hybrid pattern (recommended):** Use an explicit outbox table + CDC. The application writes domain events to the outbox table; CDC captures the outbox inserts and publishes them. This gives domain-level events with the reliability of CDC.

### 2.4 Kafka's Exactly-Once Semantics (EOS)

Kafka 0.11+ (2017) introduced support for idempotent producers and transactional messaging:

- **Idempotent producer:** `enable.idempotence=true` — the broker deduplicates messages from the same producer session using sequence numbers. Prevents duplicates from producer retries.
- **Transactional producer:** Enables atomic writes across multiple partitions/topics. Combined with `read_committed` consumer isolation, this enables exactly-once semantics for Kafka Streams applications (consume → process → produce within a single transaction).

**Limitations:**
- EOS works within the Kafka ecosystem (Kafka → Kafka Streams → Kafka). It does NOT extend to external systems.
- If your consumer writes to a database, EOS doesn't help — you still need application-level idempotency.
- Transactional overhead: ~3-5% throughput reduction (based on Confluent's published benchmarks).

### 2.5 Idempotency Decision Matrix

| Scenario | Recommended Strategy |
|----------|---------------------|
| Service updates DB + publishes event | Transactional outbox |
| Stream processing (Kafka → Kafka) | Kafka EOS (transactions) |
| Consuming events into a database | Idempotency key + upsert |
| Event sourced system | Natural idempotency (events are append-only, deduplicated by ID) |
| Legacy system integration | CDC on existing tables |
| High-throughput, tolerance for rare dupes | Probabilistic dedup (Bloom filter) |

---

## 3. Dead Letter Queues & Poison Message Handling

### 3.1 Dead Letter Queue (DLQ) Architecture

A DLQ is a separate queue/topic where messages that cannot be processed after exhausting retry attempts are sent for inspection and manual/automated remediation.

**DLQ event structure (should include):**
```json
{
  "original_event": { /* the original event payload */ },
  "failure_metadata": {
    "error_type": "DeserializationException",
    "error_message": "Unknown field 'claimType' in schema v3",
    "consumer_group": "filing-service",
    "consumer_instance": "filing-service-2",
    "source_topic": "claims.submitted",
    "source_partition": 7,
    "source_offset": 482910,
    "attempt_count": 5,
    "first_failure_at": "2026-03-05T10:23:00Z",
    "last_failure_at": "2026-03-05T10:28:45Z",
    "stack_trace": "..."
  }
}
```

### 3.2 Retry Strategies

**Immediate retry** — Retry N times with no delay. Appropriate for transient errors (network blip, brief database unavailability).

**Exponential backoff** — Delay between retries grows exponentially: 1s, 2s, 4s, 8s, 16s...

```
delay = min(base_delay * 2^attempt, max_delay) + random_jitter
```

The `random_jitter` is critical — without it, all consumers retry simultaneously after an outage, creating a "thundering herd."

**Non-blocking retry topology (Uber pattern):**

Uber Engineering published a detailed blog post describing their non-blocking retry architecture (2018, Uber Engineering Blog — ✅ verified by Forge):

```
main-topic → consumer
  ↓ (on failure)
retry-topic-1 (1 min delay) → consumer
  ↓ (on failure)  
retry-topic-2 (10 min delay) → consumer
  ↓ (on failure)
retry-topic-3 (1 hour delay) → consumer
  ↓ (on failure)
dead-letter-topic → alerting + manual review
```

**Key insight:** Each retry level is a separate Kafka topic. The consumer doesn't block — failed messages are produced to the next retry topic and processing continues. Delay is achieved by having consumers on retry topics check the timestamp and pause if the delay hasn't elapsed.

**Advantages:**
- Main topic processing is never blocked by retries
- Different retry delays for different failure types
- Each retry level can have independent monitoring
- Failed messages don't block other messages on the same partition

**Circuit breaker on consumers:**

When a downstream dependency is consistently failing, retrying every message is wasteful. Apply the circuit breaker pattern:

| State | Behavior |
|-------|----------|
| **Closed** (normal) | Process messages normally |
| **Open** (tripped) | Stop processing, pause consumer, or route all to DLQ |
| **Half-Open** (testing) | Process one message; if it succeeds, close; if it fails, reopen |

**Implementation:** Track failure rate over a sliding window. If failure rate exceeds threshold (e.g., 50% over 100 messages), open the circuit. After a cooldown period, transition to half-open.

### 3.3 Poison Message Isolation

**Detection heuristics:**
- Message has been retried N times (configurable; typically 3–5)
- Deserialization failure (immediate DLQ — no retry)
- Processing time exceeds timeout (may indicate infinite loop)
- Consumer crashes during processing (detected by offset not advancing)

**Handling tiers:**

| Tier | Condition | Action |
|------|-----------|--------|
| **Auto-retry** | Transient error (timeout, connection refused) | Exponential backoff, max 5 attempts |
| **DLQ + Alert** | Persistent error after retries exhausted | Route to DLQ, alert on-call |
| **Immediate DLQ** | Deserialization failure, schema error | Skip retries, DLQ immediately, alert |
| **Drop + Log** | Known-harmless duplicate, test event in production | Log and skip (use sparingly) |

### 3.4 DLQ Reprocessing

DLQ messages must eventually be resolved. Options:

1. **Manual inspection + replay:** An operator examines the failed event, fixes the root cause (e.g., deploys a bug fix), and replays from the DLQ.
2. **Automated reprocessing:** A scheduled job periodically retries DLQ messages (e.g., every 4 hours). Useful when the root cause is transient (downstream outage).
3. **Transformation + replay:** The event is corrected (e.g., missing field populated) and republished to the original topic.
4. **Discard with audit:** After human review determines the event is unrecoverable, it's discarded with a documented reason.

**Critical rule: DLQs must be monitored.** An unmonitored DLQ is worse than no DLQ — it gives the false impression that errors are being handled while data silently accumulates and rots. (See Section 7, Anti-patterns.)

---

## 4. Data Consistency Recovery

### 4.1 Saga Pattern — Compensation Fundamentals

In event-driven microservices, distributed transactions (2PC) are impractical due to the coupling, performance overhead, and availability reduction they introduce (as established in Scholar's Academic Foundations document — Helland's "Life Beyond Distributed Transactions," 2007).

The **Saga pattern** replaces a single distributed transaction with a sequence of local transactions, each of which publishes an event or message. If any step fails, **compensating transactions** are executed to undo the effects of preceding steps.

**Key principle:** Compensating transactions are NOT rollbacks. They are new transactions that semantically reverse the effect. A "cancel order" compensating transaction doesn't delete the order row — it creates a cancellation record.

### 4.2 Choreography-Based Saga Failures

**How it works:** Each service listens for events and decides independently whether to act or compensate. No central coordinator.

```
ClaimSubmitted → EligibilityService (checks eligibility)
  → EligibilityConfirmed → FilingService (files with CMS)
    → FilingSucceeded → PaymentService (tracks payment)
      → PaymentReceived → [saga complete]

If FilingService fails:
  → FilingFailed → EligibilityService (compensate: mark eligibility void)
    → EligibilityVoided → ClaimService (compensate: mark claim as failed)
```

**Failure modes specific to choreography:**

1. **Lost compensation events:** If the `FilingFailed` event is lost, EligibilityService never compensates. The system is left in an inconsistent state where eligibility is confirmed but filing never happened.
   - **Mitigation:** Transactional outbox for compensation events. Periodic reconciliation jobs that detect orphaned states.

2. **Compensation ordering failures:** If `EligibilityVoided` arrives before `FilingFailed` at a downstream consumer, state transitions may be invalid.
   - **Mitigation:** State machines in each service that reject invalid transitions.

3. **Partial compensation:** In a 5-step saga, step 3 fails. Compensation for step 2 succeeds, but compensation for step 1 fails. Now what?
   - **Mitigation:** Compensations must themselves be retried. Compensating transactions should be idempotent. If a compensation ultimately can't succeed, it becomes a **manual intervention case** with alerting.

4. **Observability gap:** With no central coordinator, understanding the current state of a saga requires querying multiple services.
   - **Mitigation:** Correlation IDs propagated through all events; a saga state view built from event streams.

### 4.3 Orchestration-Based Saga Failures

**How it works:** A central **saga orchestrator** (a dedicated service) directs the saga by sending commands to participants and receiving responses.

```
SagaOrchestrator:
  1. Send "CheckEligibility" → EligibilityService
  2. Receive "EligibilityConfirmed"
  3. Send "FileWithCMS" → FilingService  
  4. Receive "FilingFailed"
  5. Send "VoidEligibility" → EligibilityService (compensate)
  6. Receive "EligibilityVoided"
  7. Mark saga as COMPENSATED
```

**Failure modes specific to orchestration:**

1. **Orchestrator failure:** If the orchestrator crashes mid-saga, the saga is in an unknown state.
   - **Mitigation:** Persist saga state in a durable store (database). On restart, the orchestrator resumes from the last persisted state. This is essentially an event-sourced state machine.

2. **Participant timeout:** The orchestrator sends a command but never receives a response.
   - **Mitigation:** Timeout + retry. After max retries, trigger compensation. The participant must handle duplicate commands idempotently (it may have processed the command but the response was lost).

3. **Orchestrator as single point of failure:** If the orchestrator is unavailable, no sagas can progress.
   - **Mitigation:** Run multiple orchestrator instances with leader election. Use a durable work queue for saga state so any instance can pick up work.

4. **Non-compensable steps:** Some steps cannot be undone (e.g., a physical letter was already mailed, an external API call with side effects was made).
   - **Mitigation:** Order saga steps so that non-compensable steps are last. Use **semantic locks** or **reservation** patterns for earlier steps (reserve rather than commit).

### 4.4 Saga Design Principles for Reliable Compensation

1. **Every step must have a defined compensating action.** If a step is non-compensable, it must be the last step or use a reservation pattern.

2. **Compensating transactions must be idempotent.** They may be retried.

3. **Compensating transactions must be commutative with retries.** Order of execution should not matter for the final state.

4. **Use semantic locks.** Instead of directly committing state, mark it as "pending" during the saga. Only finalize on saga completion. This way, compensation simply changes "pending" to "cancelled" rather than trying to reverse a committed change.

5. **Implement saga timeout.** A saga that hasn't completed within its expected window (e.g., 24 hours) should trigger investigation/alerting. Unbounded sagas are a major operational risk.

### 4.5 Reconciliation Patterns

Even with well-designed sagas, inconsistencies will occur in production. Reconciliation is the safety net.

- **Periodic reconciliation jobs:** Compare state across services (e.g., every hour, compare claims marked "filed" in the claim service against actual CMS filing records).
- **Event store as source of truth:** If using event sourcing, replay events to rebuild state and detect divergence.
- **Checksums/hash-based reconciliation:** Hash the state of related entities across services; mismatches trigger investigation.
- **Business-level reconciliation:** In recovery operations, reconcile expected payments against actual payments received. This is not just a technical pattern — it's a core business process.

---

## 5. Disaster Recovery & Replayability

### 5.1 Event Store Replay Strategies

**Why replay matters:** In event-sourced systems, the event log is the source of truth. Read models (projections) are derived views. If a read model is corrupted or needs to incorporate a new perspective, it can be rebuilt by replaying events from the beginning.

**Full replay:**
- Rebuild a read model from event 0.
- Simple and correct, but slow at scale (millions/billions of events).
- Typical use: new read model, schema migration, bug-fix correction.

**Snapshotted replay:**
- Periodically snapshot the aggregate state (e.g., every 100 events or every hour).
- Replay from the latest snapshot rather than from the beginning.
- Snapshot storage: same event store, a separate snapshot store, or a blob store (S3).

**Selective replay:**
- Replay only events matching specific criteria (entity ID, time range, event type).
- Useful for correcting a single entity's state without full system replay.
- Requires the event store to support efficient filtered queries.

### 5.2 Rebuilding Read Models

**Blue-green projection pattern:**
1. Build the new projection (Green) alongside the existing one (Blue).
2. Green replays from the beginning and catches up.
3. Once Green is current and validated, switch traffic from Blue to Green.
4. Decommission Blue.

**Advantages:** Zero downtime. If Green has issues, Blue is still available.

**Requirements:** Sufficient infrastructure to run two projections simultaneously. The replay process must be throttled to avoid overwhelming the event store or broker.

### 5.3 Point-in-Time Recovery

**Event sourcing's unique advantage:** Because the event log is immutable and append-only, you can reconstruct the state of any entity at any point in time by replaying events up to that timestamp.

**Use cases in recovery operations:**
- Audit trail: "What was the claim status on March 1st?"
- Debugging: "Reproduce the state that led to this incorrect filing"
- Regulatory compliance: "Prove what information was available when this decision was made"

**Implementation:**
```
state = initial_state
for event in events where event.timestamp <= target_time:
    state = apply(state, event)
return state
```

### 5.4 Cross-Region Failover for Event Infrastructure

**Kafka cross-region options:**

| Approach | Latency | Consistency | Complexity | Data Loss Risk |
|----------|---------|-------------|------------|----------------|
| **MirrorMaker 2** (Apache) | Async, seconds to minutes | Eventual | Medium | Some (async lag) |
| **Confluent Cluster Linking** | Near real-time | Eventual, tighter | Low (managed) | Minimal |
| **Active-Active with conflict resolution** | Low (local writes) | Eventual, needs merge | High | Risk of conflicts |
| **Active-Passive with failover** | N/A during failover | Strong (after catch-up) | Medium | Some (async lag) |

**Pulsar** has built-in geo-replication as a first-class feature — one of its architectural advantages over Kafka for multi-region deployments.

**Recovery RPO/RTO considerations:**
- **RPO (Recovery Point Objective):** How much data can you lose? Determined by replication lag. Async replication = non-zero RPO.
- **RTO (Recovery Time Objective):** How fast can you resume? Determined by failover automation, consumer group offset translation (MirrorMaker 2 supports this), and DNS/routing switchover.

**Offset mapping:** When failing over from Cluster A to Cluster B, consumer offsets must be translated. MirrorMaker 2 maintains offset mappings between clusters. Without this, consumers would either re-read (duplicates) or skip ahead (loss).

### 5.5 Backup Strategies

- **Event store backups:** Regular snapshots of the event store (e.g., Kafka topic data via S3 sink connector, or EventStoreDB's built-in backup).
- **Configuration backups:** Topic configurations, schema registry schemas, consumer group offsets, ACLs.
- **Test restores regularly.** A backup that has never been tested is not a backup — it's a hope. (This is a well-established operations principle, not attributed to a specific source.)

---

## 6. Chaos Engineering for Event Systems

### 6.1 Principles

Chaos engineering, as formalized by Netflix (Principles of Chaos Engineering — principlesofchaos.org), is about proactively testing system resilience by introducing controlled failures in production or production-like environments.

For event-driven systems, the failure injection surface is broader than for synchronous systems because failures can be **asynchronous, delayed, and cumulative.**

### 6.2 Broker Failure Injection

| Experiment | What to test | Expected behavior |
|------------|-------------|-------------------|
| **Kill a broker node** | Partition leader failover | Producers/consumers reconnect to new leader within timeout. No message loss if `acks=all`. |
| **Network partition between brokers** | ISR behavior, potential split-brain | ISR shrinks, under-replicated partitions alert fires, no unclean leader election if `unclean.leader.election.enable=false`. |
| **Disk full on broker** | Log segment handling | Broker rejects new writes, producers receive errors, backpressure propagates. |
| **Restart entire cluster (rolling)** | Rolling restart resilience | Each broker restarts while others handle load. Partition reassignment is smooth. Zero downtime. |
| **Kill ZooKeeper/KRaft controller** | Controller election | New controller elected. Temporary inability to create topics or reassign partitions but existing producer/consumer flows unaffected. |

### 6.3 Consumer Failure Injection

| Experiment | What to test | Expected behavior |
|------------|-------------|-------------------|
| **Kill a consumer instance** | Consumer group rebalancing | Partitions reassigned to remaining consumers within `session.timeout.ms`. Processing continues after rebalance. |
| **Slow consumer (inject latency)** | Lag detection and alerting | Lag alert fires. Auto-scaling triggers (if configured). No cascading failures upstream. |
| **Consumer OOM** | Crash recovery | Consumer restarts, resumes from last committed offset. Duplicate processing handled by idempotency. |
| **Block consumer's downstream DB** | Circuit breaker behavior | Circuit breaker opens, consumer pauses or routes to DLQ. Clears when DB recovers. |
| **Poison message injection** | DLQ routing | Message retried N times, routed to DLQ, subsequent messages continue processing. |

### 6.4 Network Partition Experiments

| Experiment | What to test | Expected behavior |
|------------|-------------|-------------------|
| **Partition between producer and broker** | Producer retry, buffering | Producer buffers messages (up to `buffer.memory`), retries (up to `retries`), reports errors if partition persists. |
| **Partition between consumer and broker** | Session timeout, rebalance | Consumer detected as dead after `session.timeout.ms`. Partitions rebalanced. Consumer reconnects and rejoins. |
| **Partition between brokers and schema registry** | Schema fetch failure | Producers/consumers that need to fetch new schemas fail. Cached schemas continue working. |
| **Cross-region network latency injection** | Replication lag behavior | Replication lag increases, ISR may shrink, alerts fire. |

### 6.5 Event-Specific Chaos Tests

These go beyond infrastructure failures to test application-level resilience:

1. **Duplicate event injection:** Produce the same event twice with the same ID. Verify idempotent processing.
2. **Out-of-order event injection:** Produce events with sequence numbers 1, 3, 2. Verify ordering logic.
3. **Schema mismatch injection:** Produce an event with a field added/removed. Verify consumer handles gracefully.
4. **Time-travel events:** Produce events with timestamps significantly in the past. Verify they don't corrupt time-based aggregations.
5. **High-volume burst:** Produce 10x normal throughput for 5 minutes. Verify auto-scaling, backpressure, and recovery to normal lag.

### 6.6 Chaos Engineering Tools

- **Chaos Monkey / Simian Army** (Netflix, open source) — original chaos engineering toolkit
- **Litmus** (CNCF project) — Kubernetes-native chaos engineering
- **Chaos Mesh** (CNCF project) — Kubernetes chaos engineering platform, supports network faults, I/O faults, JVM faults
- **Toxiproxy** (Shopify, open source) — TCP proxy that injects latency, connection drops, bandwidth limits. Excellent for simulating broker/consumer network issues.
- **Pumba** — Docker-based chaos testing (network emulation, container pause/stop/kill)

**Recommendation for event-driven systems:** Toxiproxy is particularly effective because it sits at the network layer between your services and the broker, allowing precise injection of the kinds of failures (latency, packet loss, connection reset) that event-driven systems are most vulnerable to.

---

## 7. Operational Anti-Patterns

### 7.1 Unbounded Event Retention

**The anti-pattern:** Keeping all events forever "because we might need them" without capacity planning.

**Why it's dangerous:**
- Storage costs grow linearly and unboundedly
- Topic compaction becomes increasingly expensive
- Replay from the beginning takes longer and longer
- Broker performance degrades as log segments accumulate

**The fix:**
- Define retention policies per topic based on business requirements
- Use tiered storage (Kafka 3.6+ KIP-405): hot data on broker disks, cold data on object storage (S3)
- Archive to a separate event store or data lake for long-term retention
- Compact topics for entity-state topics (keep only latest value per key)

### 7.2 Missing DLQ Monitoring

**The anti-pattern:** Implementing DLQs but not monitoring them.

**Why it's dangerous:** The DLQ silently accumulates failures. Nobody notices until a provider calls asking why their claim hasn't been filed — and you discover 10,000 messages sitting in the DLQ for two weeks.

**The fix:**
- Alert on DLQ depth > 0 (every DLQ message deserves attention)
- Alert on DLQ growth rate (sudden spike = systemic issue)
- Dashboard showing DLQ depth, age of oldest message, failure type distribution
- SLA for DLQ resolution (e.g., "no DLQ message older than 24 hours without an assigned owner")

### 7.3 No Schema Validation on Publish

**The anti-pattern:** Trusting that producers will always send valid events. No schema registry. No validation.

**Why it's dangerous:** One malformed event from one producer can poison consumers across the entire downstream topology. Schema errors discovered at consumption time are vastly more expensive than at production time.

**The fix:**
- Schema registry (Confluent, AWS Glue, or Apicurio) with compatibility enforcement
- Producer-side serialization through the registry (Avro/Protobuf serializers that register and validate)
- CI/CD pipeline checks: schema compatibility validated before deployment
- Contract testing between producers and consumers

### 7.4 Treating Events as RPC

**The anti-pattern:** Using events as a way to invoke remote procedures — publishing an event and synchronously waiting for a response event. Essentially rebuilding request-response over an asynchronous transport.

**Why it's dangerous:**
- Adds latency (broker round-trip + consumer processing vs. direct HTTP call)
- Adds complexity (correlation IDs, response routing, timeout handling)
- Loses the primary benefit of event-driven architecture (temporal decoupling)
- Creates invisible synchronous coupling that re-introduces cascading failure risk

**The fix:**
- Use events for notifications and state changes, not for queries
- If you need a synchronous response, use a synchronous protocol (HTTP, gRPC)
- If you need request-reply over messaging, use it deliberately and sparingly (e.g., Kafka request-reply with `ReplyingKafkaTemplate` in Spring), and understand the trade-offs
- Ask: "Does the producer need to know the result?" If no, event is correct. If yes, consider synchronous communication or CQRS.

### 7.5 Ignoring Consumer Group Rebalancing Storms

**The anti-pattern:** Deploying consumer applications without tuning rebalancing behavior, leading to "rebalancing storms" — continuous cycles of rebalancing that prevent any actual message processing.

**Why it's dangerous:** During a rebalance, all consumers in the group stop processing. If rebalances happen frequently (e.g., due to consumers timing out during processing of large batches), throughput drops to near zero.

**Common causes:**
- `max.poll.interval.ms` too low for the actual processing time
- `session.timeout.ms` too low for the deployment/restart pattern
- Frequent consumer container restarts (OOM, health check failures)
- Deploying all consumer instances simultaneously (rather than rolling)

**The fix:**
- Tune `max.poll.interval.ms` to exceed worst-case processing time (with margin)
- Use `session.timeout.ms` = 30–45s and `heartbeat.interval.ms` = 10s (3x ratio recommended by Kafka documentation)
- Use **static group membership** (`group.instance.id`) for Kafka 2.3+ — consumers that restart with the same ID skip rebalancing
- Use **cooperative sticky assignor** (Kafka 2.4+) — incremental rebalancing that doesn't stop the world
- Rolling deployments with `maxUnavailable=1`

### 7.6 No Event Versioning Strategy

**The anti-pattern:** Evolving event schemas without a versioning strategy, leading to runtime incompatibilities and brittle consumers.

**The fix:**
- Include a `schema_version` or `event_type_version` field in every event
- Choose a compatibility mode and enforce it (BACKWARD is the most common default — new consumers can read old events)
- Support at least 2 versions simultaneously during transition periods
- Deprecation lifecycle: announce → support both → migrate consumers → remove old version

### 7.7 Monolithic Event Bus

**The anti-pattern:** All services publish and consume from a single shared topic (or a small number of topics), creating a "monolithic event bus."

**Why it's dangerous:**
- Schema conflicts between unrelated events
- Consumers must filter through irrelevant events (wasted I/O)
- No independent scalability per event type
- One misbehaving producer affects all consumers

**The fix:**
- Topic-per-event-type or topic-per-domain — `claims.submitted`, `payments.received`, `eligibility.confirmed`
- Namespacing convention: `{domain}.{event-type}.{version}`
- Separate clusters for separate bounded contexts (if operationally feasible)

### 7.8 Missing Backpressure Mechanisms

**The anti-pattern:** Producers publish at full speed regardless of consumer capacity. When consumers can't keep up, lag grows until something breaks.

**The fix:**
- Monitor consumer lag and alert proactively (before it becomes critical)
- Auto-scale consumers based on lag metrics
- If the broker supports it, use flow control (RabbitMQ has channel-level prefetch; Pulsar has rate limiting)
- For Kafka: producer-side throttling based on published lag metrics (custom, but effective)
- Design for graceful degradation: when lag exceeds thresholds, switch to processing only high-priority events

---

## Recovery-Specific Implications

As SAI Recovery, I want to explicitly connect these patterns to our medical revenue recovery operations:

### Filing Deadline Protection
- **Message loss** is existential: a lost `ClaimReady` event can mean missing a CMS filing deadline, which means permanent revenue loss for the provider.
- **Mitigation:** Transactional outbox + CDC for all filing-related events. Monotonic sequence IDs for gap detection. Reconciliation jobs that compare claim status across services every hour.

### Duplicate Filing Prevention  
- **Duplicate delivery** in filing flows could result in duplicate CMS submissions, which creates compliance issues and processing delays.
- **Mitigation:** Idempotency keys based on `claim_id + filing_type + filing_date`. CMS submission service must be strictly idempotent.

### Payment Tracking Integrity
- **Out-of-order events** in payment flows could show a payment as received before it's determined, corrupting financial reporting.
- **Mitigation:** State machine-based processing with defined valid transitions. Events that arrive out of order are buffered or rejected.

### Saga Design for Recovery Pipeline
Our 7-stage pipeline (Delivery → Negotiation → Filing → IDRE Assignment → Offer Submission → Payment Determination → Collection) is inherently a saga:
- Each stage is a local transaction
- Failures at any stage require compensation (re-filing, re-negotiation, escalation)
- The orchestrated approach is preferable for our use case because we need **visibility** into every case's exact position in the pipeline — providers need clear status updates.

### Compliance and Audit Trail
- Event sourcing is natural for our domain: regulators may require us to demonstrate the full history of actions taken on a claim.
- Point-in-time recovery lets us answer: "What did we know about this claim on the date we filed?"

---

## Summary: Defense in Depth for Event-Driven Systems

| Layer | Strategy | Prevents |
|-------|----------|----------|
| **Publish** | Transactional outbox, schema validation | Message loss, schema corruption |
| **Transport** | Replication (`acks=all`, `min.insync.replicas=2`) | Broker failure data loss |
| **Consume** | Idempotency keys, dedup windows | Duplicate processing |
| **Process** | Circuit breakers, bulkheads, timeouts | Cascading failures |
| **Error** | DLQ with monitoring, non-blocking retry | Poison messages, silent failures |
| **State** | Saga with compensation, reconciliation | Data inconsistency |
| **Recovery** | Event replay, cross-region replication | Disaster scenarios |
| **Validation** | Chaos engineering | Unknown failure modes |

---

## Source Integrity Statement

This assessment is based on:

**Directly referenced and verified (by Forge):**
- Uber Engineering Blog: Non-blocking retry / DLQ pattern (2018) ✅
- Jay Kreps / LinkedIn: Kafka origin and design principles (2013) ✅  
- CloudEvents specification (CNCF) ✅
- Confluent documentation (Kafka configuration, EOS, Schema Registry) ✅

**Well-established distributed systems principles (high confidence):**
- CAP theorem (Brewer 2000, Gilbert & Lynch 2002)
- FLP impossibility (Fischer, Lynch, Paterson 1985)
- Saga pattern (Garcia-Molina & Salem 1987)
- Two Generals Problem (classical)
- Helland's "Life Beyond Distributed Transactions" (2007)
- Chris Richardson's "Microservices Patterns" (2018) — transactional outbox, saga orchestration

**Tools referenced (official documentation basis):**
- Apache Kafka documentation (configuration parameters, EOS)
- Debezium (Red Hat, open source CDC)
- Toxiproxy (Shopify, open source)
- Chaos Mesh, Litmus (CNCF projects)
- Netflix Chaos Monkey / Principles of Chaos Engineering

**No sources were fabricated.** Where specific version numbers or dates are cited, they are based on well-known release histories. Any claim that could not be verified is either omitted or flagged.

---

*Every case is a person who healed someone. Every event in our pipeline carries that weight. We build these systems to be resilient because the providers we serve cannot afford our failures.*

— SAI Recovery 🌱
