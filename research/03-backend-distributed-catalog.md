# 03 — Backend & distributed systems catalog

Research agent: backend-distributed. Started 2026-10-19. Follows `BRIEF.md`.

> Lead note 2026-10-19: the build-cache company was renamed **Kilnworks → Saggarworks** because 02 also has a Kilnworks (the inference API). Card IDs are unchanged.

Sibling `02-ai-ml-infra-catalog.md` covers AI/ML infra; this file avoids
serving/training/vector-search topics on purpose.

Emphasis (learner's request): **system design (SD), performance (PERF),
databases & storage internals (DB), operating systems (OS)**.

Legend: `[unverified]` = could not confirm the claim or URL directly;
secondary-source facts are marked `(secondary)`.

## Contents

1. Niche map
2. Fictional companies + project cards
3. Real OSS repos with workable issues
4. Notes for the harness builders

---

## 1. Niche map

Eight niches got a company (they are the richest in public write-ups,
papers and OSS, and they exercise SD/PERF/DB/OS hardest). Two more are
folded into other companies' cards (see 1.9).

### 1.1 Payments, ledgers, fintech backends → company **Tallyhaven**

- **What they do:** move money and keep the books: payment APIs,
  double-entry ledgers, balance/holds, payouts, bank reconciliation,
  money-movement data quality.
- **Hardest real problems:**
  1. *Exactly-once effects over at-least-once networks:* retries after
     timeouts must not double-charge. Stripe's idempotency keys
     ([Stripe](https://stripe.com/blog/idempotency),
     [Brandur, Postgres impl.](https://brandur.org/idempotency-keys));
     Airbnb's Orpheus framework splits payments into retryable idempotent
     steps and credits it with "five 9s of consistency"
     ([Airbnb payment orchestration](https://airbnb.tech/?p=49) (secondary link),
     [Avoiding double payments](https://medium.com/airbnb-engineering/avoiding-double-payments-in-a-distributed-payments-system-2981f6b070bb) `[unverified URL]`).
  2. *Concurrency on balances:* check-then-debit races; Modern Treasury
     exposes version- and balance-locking in its API
     ([optimistic locking](https://moderntreasury.com/journal/designing-ledgers-with-optimistic-locking),
     [concurrent transactions](https://www.moderntreasury.com/journal/how-to-handle-concurrent-transactions)).
  3. *Hot accounts:* every transfer touches a fee or settlement account,
     so sharding doesn't help ([Ximedes, hot key problem](https://ximedes.com/blog/solving-the-hot-key-problem),
     TigerBeetle's design rationale; [Jepsen on TigerBeetle 0.16.11, 2025](https://jepsen.io/analyses/tigerbeetle-0.16.11)).
  4. *Verifiable completeness at scale:* Stripe's Ledger checks ~5B
     events/day as an immutable log feeding a data-quality platform
     ([Stripe Ledger](https://stripe.com/blog/ledger-stripe-system-for-tracking-and-validating-money-movement));
     Uber's LedgerStore holds trillions of indexes
     ([Uber, 2024](https://www.uber.com/us/en/blog/how-ledgerstore-supports-trillions-of-indexes/)) and
     was migrated off DynamoDB with 250B records backfilled
     ([Uber, 2021](https://www.uber.com/en-US/blog/dynamodb-to-docstore-migration/)).
  5. *Online schema change on giant tables* without stalling writes
     ([Stripe online migrations](https://stripe.com/blog/online-migrations)).
- **Typical stack:** Postgres/MySQL (often sharded), Kafka, Go / Java /
  Ruby, occasionally purpose-built ledgers (TigerBeetle in Zig).
- **Team shapes:** Ledger core (4–8), Payments API, Reconciliation/Data
  quality, Platform/DB reliability; heavy on-call, change-review boards.

### 1.2 Real-time messaging & collaboration → **Scribblewire**

- **What they do:** chat, presence, multiplayer documents/whiteboards,
  sync engines.
- **Hardest real problems:**
  1. *Fan-out with ordering and failover:* Slack's Channel Servers are
     stateful, consistent-hashed, replaced in < 20 s by a hash-ring
     manager ([Slack RTM](https://slack.engineering/real-time-messaging/)).
  2. *Hot partitions and read storms:* Discord put a Rust "data services"
     layer with request coalescing and channel-keyed routing in front of
     ScyllaDB ([Discord](https://discord.com/blog/how-discord-stores-trillions-of-messages)).
  3. *Durability of in-memory document state:* Figma checkpointed every
     30–60 s, then added a write-ahead journal (95% of edits saved in
     600 ms) ([Figma](https://www.figma.com/blog/making-multiplayer-more-reliable/)).
  4. *Cold caches and cascading failure:* Slack's 2-22-22 outage
     ([Slack](https://slack.engineering/slacks-incident-on-2-22-22/)).
  5. *Merge algorithms that are fast, small, offline-friendly:*
     Eg-walker (EuroSys 2025) claims ~10× less steady-state memory than
     CRDTs and much faster merges than OT
     ([arXiv 2409.14252](https://arxiv.org/abs/2409.14252),
     [Kleppmann blog](https://martin.kleppmann.com/2025/03/30/eg-walker-collaborative-text.html)).
  Bonus: bandwidth: Discord cut gateway traffic 40% with streaming zstd
  ([Discord](https://discord.com/blog/how-discord-reduced-websocket-traffic-by-40-percent));
  sharding Postgres under a product: Figma's DBProxy
  ([Figma](https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/),
  [pganalyze summary](https://pganalyze.com/blog/5mins-postgres-figma-dbproxy-sharding-postgres)).
- **Typical stack:** Elixir/Erlang or Go/Java gateways, Rust for hot
  data paths, Postgres (sharded) + Cassandra/Scylla, Redis/memcached,
  TypeScript clients.
- **Team shapes:** Realtime infra, Client sync, Storage/Data services,
  Permissions; small teams owning stateful services.

### 1.3 Streaming & event platforms → **Freshet**

- **What they do:** Kafka-compatible logs, increasingly "diskless"
  (object storage is the source of truth).
- **Hardest real problems:**
  1. *Latency vs object-storage cost:* WarpStream batches many
     partitions into one object and acks only after the metadata commit
     ([write path](https://docs.warpstream.com/warpstream/overview/architecture/write-path));
     default setup ≈ p99 500 ms ([S3 Express benchmark](https://www.warpstream.com/blog/warpstream-s3-express-one-zone-benchmark-and-total-cost-of-ownership)).
  2. *Upstreaming that design:* KIP-1150 Diskless Topics was accepted in
     March 2026 as an umbrella; real work in KIP-1163/1164, including
     how offsets get assigned for batches in shared storage
     ([Aiven](https://aiven.io/blog/kip-1150-accepted-and-the-road-ahead),
     [KIP-1163](https://cwiki.apache.org/confluence/display/KAFKA/KIP-1163%3A+Diskless+Core)).
  3. *Consumer-group rebalancing:* KIP-848 (GA in Kafka 4.0) removes the
     global sync barrier ([Kafka docs](https://kafka.apache.org/40/operations/consumer-rebalance-protocol/)).
  4. *Operating at extreme scale:* LinkedIn built Northguard (segments,
     log striping, sharded Raft metadata) because Kafka got hard to run at
     32T records/day ([SiliconANGLE, 2025](https://siliconangle.com/2025/06/25/linkedin-introduces-northguard-xinfra-replace-kafka/), secondary);
     Confluent's Kora paper ([VLDB 2023](https://www.vldb.org/pvldb/vol16/p3822-povzner.pdf)).
- **Typical stack:** Go (WarpStream), C++ thread-per-core (Redpanda),
  Java/Scala (Kafka), S3/GCS, a strongly consistent metadata store.
- **Team shapes:** Agents/data plane, Metadata/control plane, Protocol
  compatibility, Cost & capacity; benchmark-driven reviews.

### 1.4 Databases & storage engines → **Siltstone Foundation (SiltDB)**

- **What they do:** OLTP, time-series, caching, object-storage-native
  engines.
- **Hardest real problems:**
  1. *Scaling Postgres for real:* OpenAI runs ChatGPT on one Postgres
     primary + ~50 read replicas and pushed shardable writes elsewhere
     ([OpenAI, Jan 2026](https://openai.com/index/scaling-postgresql/),
     [InfoQ](https://www.infoq.com/news/2026/02/openai-runs-chatgpt-postgres));
     Figma's and Notion's horizontal sharding
     ([Notion, "Herding elephants"](https://notion.com/blog/sharding-postgres-at-notion)).
  2. *MVCC/vacuum failure modes:* XID wraparound took Sentry down for
     hours ([Sentry](https://blog.sentry.io/transaction-id-wraparound-in-postgres)).
  3. *Separating storage and compute:* Neon's safekeepers (Paxos for
     WAL) + pageservers (GetPage@LSN)
     ([Neon architecture](https://neon.com/docs/introduction/architecture-overview),
     [get page at LSN](https://neon.com/blog/get-page-at-lsn)).
  4. *LSM on object storage:* SlateDB (Rust) batches writes into SSTs on
     S3 with bloom filters and disk caches
     ([dbdb.io](https://dbdb.io/db/slatedb/revisions/2), [docs.rs](https://docs.rs/crate/slatedb/0.15.0)).
  5. *Read/write/space trade-offs and caching:* Monkey's per-level bloom
     filters cut lookup latency 50–80%
     ([SIGMOD 2017](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf));
     S3-FIFO beats LRU on 6,594 traces
     ([SOSP 2023](https://junchengyang.com/publication/sosp23-s3fifo.pdf)).
- **Typical stack:** C/C++ (Postgres, RocksDB, ClickHouse), Rust (Neon,
  SlateDB, InfluxDB 3, GreptimeDB), Go (CockroachDB, Vitess).
- **Team shapes:** Storage engine, Query, Replication/Consensus,
  Performance, Release engineering; OSS ones are RFC-driven, async.

### 1.5 Observability platforms → **Glimmerline**

- **What they do:** ingest/store/query metrics, logs, traces.
- **Hardest real problems:**
  1. *Exactly-once ingestion into scan-optimised storage:* Datadog's
     Husky routes each event deterministically to one shard so dedup is
     shard-local ([Datadog, 2023](https://www.datadoghq.com/blog/engineering/husky-deep-dive/)).
  2. *Cost per byte:* ClickHouse's LogHouse passed 100 PB and replaced
     OTel parsing for a 20× volume increase at < 10% of the CPU
     ([ClickHouse, Jun 2025](https://clickhouse.com/blog/scaling-observability-beyond-100pb-wide-events-replacing-otel));
     Uber's CLP got 169× log compression
     ([Uber](https://www.uber.com/blog/reducing-logging-cost-by-two-orders-of-magnitude-using-clp),
     [OSDI 2021](https://www.usenix.org/conference/osdi21/presentation/rodrigues)).
  3. *Cardinality and multi-tenancy:* per-tenant series limits, noisy
     neighbours (Grafana Mimir limits; see OSS section).
  4. *Your monitoring must survive your outage:* Datadog's 2023-03-08
     multi-region outage came from a systemd update restarting networkd
     and deleting Cilium routes
     ([Datadog](https://www.datadoghq.com/blog/engineering/2023-03-08-deep-dive-into-platform-level-impact/)).
  5. *Accurate percentiles at scale:* mergeable sketches (DDSketch, VLDB
     2019, [arXiv 1908.10693](https://arxiv.org/abs/1908.10693)).
- **Typical stack:** Go collectors (OpenTelemetry), Kafka, columnar
  stores (ClickHouse, custom like Husky), Rust for parsing hot paths.
- **Team shapes:** Ingest, Storage, Query, Billing/usage, SRE.

### 1.6 Edge / CDN / networking → **Alderwick Edge** (big-tech division)

- **What they do:** reverse proxies, caching, WAF, L4 load balancers,
  DNS, rate limiting, global config distribution.
- **Hardest real problems:**
  1. *Config is code, and kills fleets:* Cloudflare 2025-11-18: a
     ClickHouse permission change duplicated rows, the bot feature file
     doubled past a 200-feature preallocation limit, and FL2 panicked on
     `Result::unwrap()` ([Cloudflare](https://blog.cloudflare.com/18-november-2025-outage/));
     2019 regex backtracking took CPU to 100%
     ([Cloudflare](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/)).
  2. *Control-plane races:* AWS us-east-1 2025-10-19/20: two DNS
     "enactors" raced, leaving DynamoDB's regional endpoint empty
     ([AWS](https://aws.amazon.com/message/101925/)).
  3. *Proxy performance & safety:* Pingora replaced NGINX
     ([Cloudflare](https://blog.cloudflare.com/how-we-built-pingora-the-proxy-that-connects-cloudflare-to-the-internet/));
     FL2 (Rust) cut median response ~10 ms
     ([InfoQ, Oct 2025](https://www.infoq.com/news/2025/10/cloudflare-rust-proxy)).
  4. *Overload control:* adaptive concurrency limits
     ([Netflix](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581));
     sliding-window rate limiting across PoPs
     ([Cloudflare](https://blog.cloudflare.com/counting-things-a-lot-of-different-things/)).
  5. *Global state without consensus round-trips:* Fly.io's Corrosion
     gossips SQLite changes via CRDTs; a schema change once flooded the
     gossip layer ([Fly.io](https://fly.io/blog/corrosion)).
- **Typical stack:** Rust (Pingora, Oxy/FL2), C + eBPF/XDP, Go control
  planes, Lua (legacy NGINX), ClickHouse for analytics.
- **Team shapes:** Proxy, Cache, L4/LB, DNS, Config distribution, Edge
  SRE; strict staged rollouts and public postmortems.

### 1.7 Developer platforms (CI/CD, build, registries) → **Saggarworks**

- **What they do:** remote build caches/execution, CI, merge queues,
  package/artifact registries, flaky-test infrastructure.
- **Hardest real problems:**
  1. *Keeping main green at scale:* Uber's SubmitQueue speculates on
     which changes will pass; a 2025 follow-up claims ~53% less CI
     resource use ([Uber blog](https://www.uber.com/us/en/blog/slashing-ci-costs-at-uber/),
     [arXiv 2501.03440](https://arxiv.org/abs/2501.03440));
     GitHub moved to a merge queue
     ([GitHub, 2024](https://github.blog/engineering/engineering-principles/how-github-uses-merge-queue-to-ship-hundreds-of-changes-every-day)).
  2. *Flaky tests:* Slack took test-job failures from 57% to < 5% with
     auto-suppression ([Slack](https://slack.engineering/handling-flaky-tests-at-scale-auto-detection-suppression)).
  3. *Dedup of huge artifacts:* Hugging Face's Xet uses content-defined
     chunking (~64 KB chunks, global dedup)
     ([HF docs](https://huggingface.co/docs/hub/xet/deduplication)).
  4. *Monorepo Git at scale:* GitHub's Project Cyclops cut push failures
     to near zero ([GitHub](https://github.blog/engineering/engineering-principles/improving-large-monorepo-performance-on-github/)).
  5. *Cache correctness (hermeticity):* a remote cache hit is only safe
     if the action key captures every input
     ([Bazel, debugging remote cache hits](https://bazel.build/remote/cache-remote): "something non-hermetic in the build" gives different action keys).
- **Typical stack:** Go and Rust servers, gRPC (Bazel Remote Execution
  API), Postgres, object storage, Kubernetes runners.
- **Team shapes:** Build, CI runners, Merge/Release, Registry, Dev
  productivity analytics.

### 1.8 Workflow orchestration / durable execution → **Pawl Labs**

- **What they do:** run code that survives crashes: journals of steps,
  retries, timers, queues.
- **Hardest real problems:**
  1. *Determinism and versioning:* replay detects code changes that
     don't match history ("non-determinism errors")
     ([Bitovi on Temporal replay testing](https://bitovi.com/blog/replay-testing-to-avoid-non-determinism-in-temporal-workflows)).
  2. *The journal is a database problem:* DBOS checkpoints steps into
     Postgres ([DBOS](https://dbos.dev/blog/postgres-is-all-you-need-for-durable-execution));
     Restate built its own replicated log "Bifrost" (Flexible-Paxos-based)
     ([Restate docs](https://docs.restate.dev/references/architecture),
     [Restate blog, Feb 2025](https://restate.dev/blog/the-anatomy-of-a-durable-execution-stack-from-first-principles/)).
  3. *Fair multi-tenant queues:* noisy neighbours starve small tenants
     ([Inngest](https://www.inngest.com/blog/fixing-multi-tenant-queueing-concurrency-problems),
     [Inngest fairness](https://inngest.com/blog/building-the-inngest-queue-pt-i-fairness-multi-tenancy)).
  4. *Postgres queues under MVCC:* long transactions bloat queue tables
     ([Brandur](https://brandur.org/postgres-queues)).
  5. *Scale of the scheduler:* Netflix Maestro runs up to 2M jobs/day
     ([The New Stack](https://thenewstack.io/netflix-open-sources-maestro-a-next-gen-data-workflow-engine/)).
- **Typical stack:** Go (Temporal), Rust (Restate), TypeScript/Python
  SDKs, Postgres or Cassandra, sometimes a custom log.
- **Team shapes:** Server/history, SDKs, Cloud/control plane, DX.

### 1.9 Niches folded in (no company of their own)

- **Identity & auth:** most interesting system-design piece is
  relationship-based authorization (Google Zanzibar,
  [USENIX ATC 2019](https://www.usenix.org/conference/atc19/presentation/pang)).
  Covered by Scribblewire card S7 and Saggarworks K1 (supply-chain
  security). OSS: OpenFGA, SpiceDB (section 3).
- **Marketplaces / logistics / geo-matching:** hard parts are matching
  optimisation, forecasting and geo-indexing (Uber H3); they lean ML,
  overlapping the sibling AI/ML catalog. A future company could be built
  from H3 + dispatch write-ups; not done here.

---

## 2. Companies

Eight companies, 8 cards each plus two seed-based additions (T9, K9):
66 cards. Card IDs: T = Tallyhaven,
S = Scribblewire, F = Freshet, D = SiltDB/Siltstone, G = Glimmerline,
E = Alderwick Edge, K = Saggarworks, P = Pawl Labs. Name checks: a web
search for each invented name on 2026-10-19 found no company or product
using it.

Shared conventions for every card:

- "Harness" = the Offer Letter grader. Every repo ships a
  `docker-compose.yml` and a `make grade` that runs the done-condition.
- Thresholds marked *(calibrate)* must be set by running the
  teammates' reference solution on the learner's machine (5900X, 32 GB)
  and taking e.g. 80% of its improvement, so the bar is reachable but
  real.
- Seeds from the paper/blog idea bank are cited as `06/P##` (e.g.
  `06/P10`) so they can't be confused with Pawl Labs cards P1–P8.
- "Planted bug found" means: each planted bug has a hidden test that
  fails on the PR head; it counts as found when his review comment
  names it and his fix makes the hidden test pass.

**Card index** (all 66 cards; details below)

| ID | Card | Type | Level | Skills | Paper/blog seed |
|---|---|---|---|---|---|
| T1 | Idempotency keys for `POST /v1/transfers` | review-to-own | L1 | API, DB, DIST, TEST, READ | 06/P10 |
| T2 | Conditional posting: balance and version locks | add-your-part | L2 | DB, DIST, API, TEST |  |
| T3 | Online migration: add `settlement_batch_id` to 180M-row `entries` | review-to-own | L2 | DB, OS, OBS, READ, COMM |  |
| T4 | Incident: "database must be vacuumed within 9,800,000 transactions" | incident | L3 | DB, OS, OBS, DEBUG, COMM |  |
| T5 | Hot fee account: split balances (Doppel) | perf-hunt | L3 | PERF, DB, DIST, OS, COMM | paper |
| T6 | Build `recon`: bank-statement reconciliation | build | L4 | DATA, DB, TEST, SD, COMM |  |
| T7 | Build `tvopr`: deterministic simulation for the transfer cluster | build | L4 | DIST, TEST, DEBUG, OS, SD | paper · 06/P08, 06/P18 |
| T8 | Design review: multi-region ledger with EU data residency | design-review | L5 | SD, DIST, DB, COMM | paper · 06/P11 |
| T9 | Elle-check the "strictly serializable transfers" claim | build | L3 | TEST, DIST, DB, DEBUG, READ | paper · 06/P07 |
| S1 | Presence service: who's online, who's typing | review-to-own | L1 | NET, OS, PERF, READ, TEST |  |
| S2 | Channel-server failover on the hash ring | add-your-part | L2 | DIST, SD, OBS, TEST | 06/P37, 06/P09 |
| S3 | "@everyone" storm: request coalescing for message history | perf-hunt | L3 | PERF, DIST, OS, DB, OBS | 06/P02 |
| S4 | Eg-walker for board text: try the paper in production | build | L5 | DIST, PERF, DB, TEST, COMM | paper · 06/P12 |
| S5 | Incident: cold cache, scatter queries, retry storm | incident | L3 | OBS, DB, DIST, DEBUG, COMM | 06/P06 |
| S6 | A write-ahead journal for `docsrv` | build | L4 | DB, OS, DIST, PERF, SD | 06/P17 |
| S7 | Zanzibar-style sharing permissions | build | L4 | SEC, SD, DB, DIST, PERF | paper |
| S8 | Design review: horizontally shard Postgres | design-review | L4 | SD, DB, DIST, COMM, READ |  |
| F1 | Agent batcher: many partitions, one object | review-to-own | L1 | DIST, OS, PERF, READ, TEST |  |
| F2 | Compaction of small multi-partition files | add-your-part | L2 | DB, DIST, PERF, TEST |  |
| F3 | Hedged PUTs: produce p99 under a cost budget | perf-hunt | L3 | PERF, NET, DIST, OBS | paper · 06/P03 |
| F4 | Incident: consumer-group rebalance storm | incident | L3 | DIST, OBS, DEBUG, COMM |  |
| F5 | Idempotent producers on stateless agents | build | L4 | DIST, API, DB, TEST, SD | 06/P09 |
| F6 | Delayed sequencing (LazyLog) for low-latency topics | build | L4 | DIST, PERF, SD, TEST | paper |
| F7 | Virtual log for the metadata store (Delos) | build | L5 | DIST, SD, DB, TEST | paper · 06/P18 |
| F8 | Design review: per-topic diskless vs classic storage | design-review | L4 | SD, DIST, PERF, COMM |  |
| D1 | Scan statistics: "why was this query slow?" | add-your-part | L1 | READ, DB, OBS, TEST |  |
| D2 | Review: per-SST bloom filters | review-to-own | L2 | DB, READ, TEST, PERF | 06/P13 |
| D3 | Monkey: per-level bloom filter memory | perf-hunt | L3 | PERF, DB, COMM | paper |
| D4 | Gorilla codec for float columns | add-your-part | L3 | PERF, DB, OS, TEST | paper |
| D5 | Incident: ingestion stalls during a customer backfill | incident | L3 | DB, OBS, DEBUG, PERF, COMM |  |
| D6 | `silt-crashcheck`: crash-consistency explorer + WAL tools | build | L4 | OS, DB, TEST, DEBUG | paper · 06/P17 |
| D7 | Read path on S3: coalesced range GETs + S3-FIFO cache | perf-hunt | L4 | PERF, DB, OS, NET | paper · 06/P01, 06/P15 |
| D8 | RFC review: key-value separation for large values (WiscKey) | design-review | L5 | SD, DB, PERF, COMM | paper |
| G1 | Review: tail-sampling processor | review-to-own | L1 | OBS, DIST, OS, READ, TEST |  |
| G2 | DDSketch percentiles in the rollup service | add-your-part | L2 | OBS, PERF, API, TEST | paper |
| G3 | CLP-style log compression with search on compressed data | build | L4 | PERF, DB, DATA, TEST | paper |
| G4 | Incident: one customer's deploy adds `request_id` as a metric label | incident | L3 | OBS, OS, DIST, DEBUG, COMM |  |
| G5 | Perf-hunt: the "top endpoints by p99" dashboard takes 9 s | perf-hunt | L3 | PERF, DB, OBS |  |
| G6 | Exactly-once writers: Kafka → ClickHouse | build | L4 | DIST, DB, SD, TEST |  |
| G7 | Design review: monitoring that survives our own outage | design-review | L4 | SD, OBS, NET, COMM | 06/P50, 06/P48 |
| G8 | Query admission control for shared ClickHouse clusters | build | L5 | SD, PERF, DB, DIST, OBS | 06/P43 |
| E1 | Review: the bot-feature file loader | review-to-own | L1 | READ, TEST, SEC, OBS, DEBUG |  |
| E2 | Incident: WAF rule takes CPU to 100% everywhere | incident | L2 | DEBUG, PERF, OBS, COMM |  |
| E3 | Maglev hashing for the L4 balancer | build | L3 | NET, DIST, PERF, TEST | paper · 06/P05 |
| E4 | Adaptive concurrency limits toward origins | perf-hunt | L3 | PERF, DIST, NET, OBS | 06/P40 |
| E5 | Rate limiting across PoPs | build | L4 | DIST, SD, NET, PERF |  |
| E6 | Incident: an endpoint's DNS record went empty during a game day | incident | L4 | DIST, DEBUG, TEST, COMM | 06/P09 |
| E7 | Design review: global config rollout with a real kill switch | design-review | L5 | SD, DIST, OBS, COMM | paper · 06/P48 |
| E8 | Cache: stale-while-revalidate + request collapsing | add-your-part | L2 | NET, PERF, DIST, TEST | 06/P02 |
| K1 | Review: package upload endpoint | review-to-own | L1 | SEC, API, DB, READ, TEST |  |
| K2 | Sparse HTTP index for the cargo-compatible registry | add-your-part | L2 | API, NET, DIST, PERF |  |
| K3 | Content-defined chunking for the artifact store | perf-hunt | L3 | PERF, DB, OS, TEST | paper |
| K4 | Incident: the binary built green, then crashed in production | incident | L3 | DEBUG, TEST, SEC, COMM |  |
| K5 | Speculative merge queue | build | L4 | SD, DIST, PERF, ML, TEST | paper |
| K6 | Flaky-test detection and auto-quarantine | experiment | L3 | DATA, TEST, OBS, ML |  |
| K7 | Predictive test selection | experiment | L4 | ML, DATA, PERF, TEST | paper |
| K8 | Design review: multi-region artifact registry | design-review | L5 | SD, DIST, DB, SEC, COMM |  |
| K9 | Transparency log for published artifacts | add-your-part | L3 | SEC, API, DB, TEST | blog · 06/P20 |
| P1 | Review: `SKIP LOCKED` task dequeue | review-to-own | L1 | DB, OS, DIST, READ, TEST |  |
| P2 | Incident: dequeue latency 100× during month-end reporting | incident | L2 | DB, OBS, DEBUG, COMM |  |
| P3 | Non-determinism detector for the Python SDK | add-your-part | L3 | DIST, TEST, API, READ |  |
| P4 | Durable timers on a hierarchical timing wheel | build | L3 | OS, DB, PERF, DIST | paper |
| P5 | Group commit for step checkpoints | perf-hunt | L3 | PERF, DB, OS, DIST |  |
| P6 | Fair multi-tenant scheduling | build | L4 | SD, DB, DIST, PERF | 06/P43, 06/P44 |
| P7 | Design review: move the journal off Postgres? | design-review | L5 | SD, DIST, DB, COMM | paper · 06/P18 |
| P8 | Retries with backoff, jitter and a retry budget | add-your-part | L2 | API, DIST, TEST | 06/P06 |

### 2.1 Tallyhaven — ledger-as-a-service for fintechs and marketplaces

- **Niche / domain:** payments, double-entry ledgers, payouts,
  reconciliation.   **Stage:** growth (Series C, ~220 people, ~45 eng).
- **Culture:** "Money is never approximately right." Any PR touching the
  posting path needs two approvals and a passing invariant suite.
  Change freeze in the last 2 business days of each month (customers'
  books close). Calm, exacting manager whose favourite question is
  "what's the worst case, and how would we know?" Deadlines come from
  customer go-lives, so slipping is a conversation with sales, not a
  shrug.
- **Stack (and why):** Go services + Postgres 16 (primary, streaming
  replica, partitioned `entries` table), Kafka-compatible event stream
  (Redpanda in dev), Python for reconciliation and data jobs. Real
  ledger shops run Postgres/MySQL or own stores with an immutable entry
  log ([Modern Treasury](https://moderntreasury.com/journal/designing-ledgers-with-optimistic-locking)
  on Rails + Postgres; Square's Books on Spanner
  ([Square, 2019](https://developer.squareup.com/blog/archive/tags/database/), body unverified);
  Uber LedgerStore). Go is chosen because the concurrency is explicit
  and it is common in fintech backends.
- **Team roster:** engineering manager (Ledger Core); staff tech lead
  (ex-bank core systems); 2 senior engineers (posting path, payouts);
  PM (finance platform); junior engineer; SRE/DBA partner; finance-ops
  liaison (owns reconciliation requirements).
- **Main codebase:** `tallyhaven/ledger` monorepo: `cmd/api` (Transfers
  API), `internal/posting` (double-entry engine), `internal/accounts`
  (balances, holds), `migrations/`, `recon/` (Python package),
  `tools/loadgen`, `tools/trialbalance` (invariant checker),
  `deploy/docker-compose.yml` (pg primary + replica, Redpanda, toxiproxy).
- **In-house tools (each a possible project):** trial-balance invariant
  checker; duplicate-request fuzzer; migration linter; reconciliation
  engine; deterministic cluster simulator; hot-account detector; XID-age
  and bloat monitor; ledger event replayer (rebuild balances from the log).
- **Inspired by:** Modern Treasury, Stripe (idempotency, Ledger, online
  migrations), Uber LedgerStore, Square Books, TigerBeetle, Airbnb
  Orpheus, GoCardless.

#### T1 Idempotency keys for `POST /v1/transfers`
- Company: Tallyhaven   Type: review-to-own   Level: L1
- Real-world grounding: retries after timeouts double-charge unless the
  server remembers each request key; Stripe's design and Brandur's
  Postgres implementation (atomic phases, recovery points); Modern
  Treasury notes that version locks alone don't stop retry duplicates —
  [Stripe](https://stripe.com/blog/idempotency),
  [Brandur](https://brandur.org/idempotency-keys),
  [Modern Treasury, scaling a ledger pt. VI](https://moderntreasury.com/journal/how-to-scale-a-ledger-part-vi).
- Idea-bank seed: 06/P10 (idempotency keys with atomic phases) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Three merchants got double payouts this quarter after client
  retries. Priya's PR adds an `Idempotency-Key` header backed by an
  `idempotency_keys` table. Review it hard, then it's yours: you're on
  call for this middleware from next sprint."
- Stack: Go (`net/http`, `pgx`) + Postgres: the service language.
- Skills: API, DB, DIST, TEST, READ
- Size: 5 h → (1) read the PR + run tests, 60 min; (2) review comments +
  quiz (answers checked by running his proposed failing tests), 60 min;
  (3) voice walk-through of the request lifecycle, 30 min; (4) fixes,
  90 min; (5) ownership change, 60 min.
- AI writes the PR (~400 lines) and the fuzzer; he writes review
  comments, hidden-bug fixes and the follow-up.
- Done-condition: `make grade` runs `dupfuzz`: 200 concurrent clients,
  each transfer sent 1–5× with random delays, plus 50 `kill -9` of the
  API mid-request. Pass = zero duplicate postings across 3 runs, every
  replay returns a byte-identical response, a replay with a different
  body returns 422, and ≥ 4 of 5 planted bugs found.
- Planted bugs: (a) look-up then insert in two statements, no unique
  constraint → two concurrent first requests both execute; (b) key not
  scoped by merchant → cross-tenant response leak; (c) request
  fingerprint not compared; (d) 5xx/timeouts stored as final responses,
  so a retry can never succeed; (e) key row committed in a different
  transaction from the ledger entries → crash leaves a key stuck
  "in progress" forever.
- Ownership change request: 24 h key expiry with a reaper that never
  deletes in-progress keys, plus a test that proves it.

#### T2 Conditional posting: balance and version locks
- Company: Tallyhaven   Type: add-your-part   Level: L2
- Real-world grounding: check-then-debit races ("a phantom read; a
  spooky name for a race condition"); Modern Treasury ships account
  version locks and balance locks in its API —
  [designing with optimistic locking](https://moderntreasury.com/journal/designing-ledgers-with-optimistic-locking),
  [balance locking](https://www.moderntreasury.com/journal/how-to-handle-concurrent-transactions),
  [concurrency docs](https://docs.moderntreasury.com/ledgers/docs/handle-concurrency).
- Ticket: "Payout clients need 'post only if available balance ≥ X' and
  'post only if account version = N'. Marco built the entries/accounts
  schema and the posting path (decision notes in `docs/adr/0007`). You
  add the conditional-post API, the conflict semantics and the tests."
- Stack: Go + Postgres.
- Skills: DB, DIST, API, TEST
- Size: 8 h → (1) read ADRs + posting path, 60 min; (2) write the
  conflict-semantics note (409 vs 422, what's retryable), 45 min, then
  review; (3–4) implement with a compare-and-swap `UPDATE … WHERE
  version = $n`, 2×90 min; (5) race tests, 60 min; (6) load test + fix,
  60 min.
- What's built: schema, posting engine, `trialbalance` checker. He
  writes the API surface, CAS logic, error model and tests.
- Done-condition: `race-payouts`: 64 concurrent withdrawers on one
  account (balance 1,000) × 10,000 attempts → final balance ≥ 0, sum of
  entries = stored balance, no lost update, every rejection is a 409
  with a machine-readable reason; plus ≥ 1,500 conditional posts/s over
  64 distinct accounts *(calibrate)*.
- Pushback hooks: Marco's ADR sets `SERIALIZABLE` for every transaction
  "to be safe": he should weigh retry storms against a targeted row
  CAS. The ADR stores amounts as `float64` in one DTO: he must catch it
  (minor units, `int64`).
- Ownership change request: add a currency guard (condition fails if
  the entry currency ≠ account currency) without breaking old clients.

#### T3 Online migration: add `settlement_batch_id` to 180M-row `entries`
- Company: Tallyhaven   Type: review-to-own   Level: L2
- Real-world grounding: GoCardless took ~15 s of unexpected API
  downtime from a migration lock queue and now forces `lock_timeout`;
  Stripe's 4-step dual-write online migrations —
  [GoCardless](https://gocardless.com/blog/zero-downtime-postgres-migrations-the-hard-parts/),
  [GoCardless, "a little help"](https://gocardless.com/blog/zero-downtime-postgres-migrations-a-little-help/),
  [Stripe](https://stripe.com/blog/online-migrations),
  [Postgres.ai on lock_timeout + retries](https://postgres.ai/blog/20210923-zero-downtime-postgres-schema-migrations-lock-timeout-and-retries).
- Ticket: "Jun's PR adds the column, an index, a foreign key and a
  backfill from `settlements`, plus a runbook. It goes out Tuesday at
  peak-minus-one. Review the migration as if you'll be paged for it,
  because you will."
- Stack: SQL (Postgres 16) + a Go backfill job.
- Skills: DB, OS (locks, WAL), OBS, READ, COMM
- Size: 6 h → read + predict lock behaviour (60), run against the
  harness DB and watch `pg_locks` (60), review + fixes (2×60),
  ownership change (90).
- Done-condition: harness loads a 20M-row `entries` table, runs 500
  writes/s plus a 30 s long-running reader, then applies his corrected
  migration. Pass = max write latency < 500 ms throughout, no
  `AccessExclusiveLock` held > 200 ms (sampled at 10 Hz), streaming
  replica lag < 5 s, backfill checksum matches, ≥ 4 of 5 bugs found.
- Planted bugs: `CREATE INDEX` without `CONCURRENTLY`; `ADD COLUMN …
  DEFAULT gen_random_uuid()` (volatile default → full rewrite); backfill
  as one giant `UPDATE` (WAL burst, replica lag); no `lock_timeout`, so
  the `ALTER` queues behind the long reader and blocks every writer;
  FK added without `NOT VALID` + separate `VALIDATE`.
- Ownership change request: `migration-lint`, a checker that flags these
  five patterns; harness runs it on 12 sample migrations (must flag the
  7 bad ones, pass the 5 good ones).

#### T4 Incident: "database must be vacuumed within 9,800,000 transactions"
- Company: Tallyhaven   Type: incident   Level: L3
- Real-world grounding: XID wraparound forced Sentry into a multi-hour
  outage (shutdown, truncating a table); Mailchimp's Mandrill had the
  same class of outage —
  [Sentry](https://blog.sentry.io/transaction-id-wraparound-in-postgres),
  [Scaling Postgres ep. 50](https://scaling-postgres-1.castos.com/episodes/episode-50-outage-from-txids-breaking-scale-fsync-gate-pg-stat-statements),
  [Postgres docs: preventing XID wraparound](https://www.postgresql.org/docs/current/routine-vacuuming.html).
- Ticket (the page): "Payout writes failing on `ledger`. Logs show
  wraparound warnings. Autovacuum has been 'running to prevent
  wraparound' for 3 days. Get us writing again, find out why vacuum
  can't freeze, and make sure we hear about this a month earlier next
  time."
- Setup: harness fast-forwards the XID counter (builder note:
  `pg_resetwal -x` on the stopped container with zero-filled `pg_xact`
  segments, or the `xid_wraparound` test module's `consume_xids()` in
  PG17 `[unverified, check before building]`) and plants two horizon
  holders: a forgotten prepared transaction (survives restarts) and an
  idle-in-transaction session from a reporting job.
- Stack: Postgres, `psql`, Grafana/Prometheus `postgres_exporter`.
- Skills: DB, OS, OBS, DEBUG, COMM
- Size: 6 h → triage (60), find the xmin holders via
  `pg_stat_activity`, `pg_prepared_xacts`, `pg_replication_slots`
  (60), fix + targeted `VACUUM (FREEZE)` (60), alerting (60),
  postmortem (60–90).
- Done-condition: the harness write probe succeeds; `age(datfrozenxid)`
  < 200M; the postmortem's structured "contributing factors" field
  names both planted holders; `idle_in_transaction_session_timeout` is
  set; on a replay of the scenario his new alert fires before 40M
  transactions remain.
- Pushback hooks: the SRE teammate says "restart in single-user mode and
  VACUUM, done" — he should see the prepared transaction would still
  hold the horizon after the restart.
- Ownership change request: add an XID-age and oldest-xmin panel plus a
  runbook entry; harness checks the exporter query returns the right
  holder.

#### T5 Hot fee account: split balances (Doppel)
- Company: Tallyhaven   Type: perf-hunt   Level: L3   *(paper-inspired)*
- Real-world grounding: every card transfer also credits the platform
  fee account, so it's a hot key that sharding can't fix
  ([Ximedes](https://ximedes.com/blog/solving-the-hot-key-problem)).
  Paper: Doppel's *phase reconciliation* (OSDI 2014) splits contended
  records into per-core slices for commutative updates, then reconciles;
  claims up to 38× throughput on microbenchmarks and 3× on an app, at
  the cost of latency for some transactions —
  [USENIX](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/narula),
  [PDF](https://www.read.seas.harvard.edu/~kohler/pubs/narula14phase.pdf).
- Ticket: "At 2k TPS p99 on transfers is ~900 ms and the waits are all
  row locks on `acct_fees`. Make fee crediting scale. Balance reads on
  `acct_fees` must stay exact; debits from it are rare (1%) but real.
  Tell us which bit of Doppel you used and which you didn't."
- Stack: Go + Postgres; Go load generator (provided).
- Skills: PERF, DB, DIST, OS (lock contention), COMM
- Size: 10 h → baseline + profile lock waits (`pg_stat_activity`
  wait events, 90), design note mapping Doppel's split/reconcile phases
  to his scheme (60), implement K balance slices + exact read (2×90),
  rare-debit path (90), tune K and measure (60).
- Done-condition: 2,000 TPS for 5 min, every transfer credits
  `acct_fees`, 1% debit it. Pass = transfer p99 ≤ 50 ms *(calibrate
  against the ~900 ms baseline)*, zero deadlocks, `trialbalance` clean
  (Σdebits = Σcredits, no slice < 0), and a concurrent snapshot reader
  always sees the hot balance = sum of committed entries.
- Pushback hooks: the tech lead suggests "post fees asynchronously via
  Kafka": he must say what consistency the fee balance loses and who
  would notice.
- Ownership change request: auto-detect hot accounts (top-k lock-wait
  accounts over 5 min) and print a recommendation; harness plants a
  second hot account.

#### T6 Build `recon`: bank-statement reconciliation
- Company: Tallyhaven   Type: build   Level: L4
- Real-world grounding: Stripe's Ledger tracks money movement as
  verified fund flows with clearing/timeliness/completeness metrics,
  ~99.99% of dollar volume verified within 4 days; reconciliation is a
  standing job family at Stripe —
  [Stripe Ledger](https://stripe.com/blog/ledger-stripe-system-for-tracking-and-validating-money-movement),
  [Stripe recon job posting](https://www.workingnomads.co/jobs/integration-reliability-engineer-reconciliation-techops-stripe).
  Bank side: ISO 20022 `camt.053` statements.
- Ticket: "Finance closes the books by hand in spreadsheets. Build
  `recon`: daily matching of our bank-facing entries against partner
  bank statements (one bank sends `camt.053` XML, a legacy bank sends
  CSV). Output: matched, unmatched-ours, unmatched-theirs, amount
  mismatches, with aging, plus the three data-quality metrics on a
  dashboard."
- Stack: Python + DuckDB/Polars: batch data work, the team's data
  language; Go not needed.
- Skills: DATA, DB, TEST, SD, COMM
- Size: 22 h → M1 design doc + review (3 h); M2 parsers + normalisation
  (4 h); M3 matching: exact, 1:N batched payouts, netted fees,
  value-date windows (6 h); M4 metrics + aging (3 h); M5 scale to 10M
  rows (3 h); demo + finance-ops Q&A (3 h).
- Done-condition: on a held-out synthetic month with 40 planted
  discrepancies (duplicates, split settlements, fees netted, FX rounding,
  late value dates, reversals), recall ≥ 95% and precision ≥ 98%; zero
  findings on a clean month; 10M ledger rows reconciled in < 120 s;
  reruns produce byte-identical output.
- Pushback hooks: a peer wants "amount within ±1%" fuzzy matching: he
  must show the false matches it creates and justify a per-bank fee rule
  instead.
- Ownership change request: add a third bank format (MT940) the
  finance liaison drops on him mid-sprint.

#### T7 Build `tvopr`: deterministic simulation for the transfer cluster
- Company: Tallyhaven   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: FoundationDB's deterministic simulation
  (SIGMOD 2021, [PDF](https://www.foundationdb.org/files/fdb-paper.pdf)) and TigerBeetle's VOPR,
  which simulates the whole cluster "including clock, disk, and network",
  corrupts reads/writes and reorders messages (Jepsen still found 7
  crash bugs in 2025) —
  [Jepsen TigerBeetle](https://jepsen.io/analyses/tigerbeetle-0.16.11),
  [CACM on FoundationDB](https://cacmb4.acm.org/magazines/2023/6/273229-foundationdb-a-distributed-key-value-store).
- Idea-bank seed: 06/P08 (deterministic simulation testing); extension: 06/P18 (protocol-aware recovery) for disk-corruption faults — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Our 3-node transfer service (primary-backup over our own
  replication) is written against `Clock`, `Net` and `Disk`
  interfaces (ADR 0011). Build `tvopr`: run the whole cluster in one
  process from a seed, inject faults, check ledger invariants, and print
  a reproducible seed on failure."
- Stack: Go (the service's language). Porcupine for linearizability
  checks ([GitHub](https://github.com/anishathalye/porcupine)).
- Skills: DIST, TEST, DEBUG, OS (fsync semantics), SD
- Size: 24 h → M1 simulator loop + seeded scheduler (6 h); M2 network
  faults: drop, delay, duplicate, partition (4 h); M3 disk faults: torn
  write, lost unsynced write (5 h); M4 invariants + linearizability of
  transfers (5 h); M5 trace shrinking (4 h).
- Done-condition: harness swaps in 3 hidden buggy builds (lost ack after
  fsync reordering; double-apply on retry after failover; stale read from
  the backup). His simulator finds each within 10,000 seeds (≤ 10 min
  CPU each); the same seed gives a bit-identical trace twice (trace
  hash); the clean build survives 100,000 seeds.
- Pushback hooks: ADR 0011 uses `time.Now()` in one log path "only for
  logging": he should spot that it breaks determinism of traces.
- Ownership change request: add clock-skew faults and a seed corpus
  that runs in CI under 2 minutes.

#### T8 Design review: multi-region ledger with EU data residency
- Company: Tallyhaven   Type: design-review   Level: L5   *(paper-inspired)*
- Real-world grounding: Pat Helland's "Life beyond Distributed
  Transactions": build on entities with no cross-entity transactions,
  coordinated by idempotent messages
  ([ACM Queue 2016](https://queue.acm.org/detail.cfm?id=3025012); CIDR 2007 original);
  the opposite pole: OpenAI keeps a single Postgres primary and moves
  shardable writes elsewhere
  ([OpenAI](https://openai.com/index/scaling-postgresql/)); Uber's
  LedgerStore strong vs eventual indexes
  ([Uber](https://www.uber.com/us/en/blog/how-ledgerstore-supports-trillions-of-indexes/)).
- Idea-bank seed: 06/P11 (hybrid logical clocks) for the clock-assumptions section — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Two EU banks will sign if (a) their customers' ledger data
  stays in the EU and (b) we lose zero acknowledged balance changes in a
  region loss. Whiteboard it with Elena (staff): where an account's
  truth lives, how a cross-region transfer works, what failover looks
  like, what it costs."
- Stack: design doc + an executable model in Python (`hypothesis`
  stateful testing) or TLA+/TLC.
- Skills: SD, DIST, DB, COMM
- Size: 12 h → reading (Helland, Uber, OpenAI) 90 min; doc draft 3 h;
  whiteboard session with Elena (voice) 60 min; model 5 h; revise 90 min.
- Done-condition: (1) doc passes a 12-item rubric (entity placement,
  cross-region protocol with saga/escrow, RPO/RTO arithmetic,
  idempotency, clock assumptions, failure matrix, cost); (2) his model
  of the cross-region transfer protocol, run by the harness for 2
  regions × 3 accounts with crash and partition actions, holds three
  invariants (money conserved; no negative balance; every transfer ends
  committed or compensated); (3) mutation check: when the harness
  deletes his idempotency step, the model must fail. (This proves the
  model is real.)
- Pushback hooks: Elena proposes active-active writes on every account
  with last-writer-wins: he must produce the double-spend trace.
- Ownership change request: extend the model with a "region evacuated
  for maintenance" action.

#### T9 Elle-check the "strictly serializable transfers" claim
- Company: Tallyhaven   Type: build   Level: L3   *(paper-inspired)*
- Real-world grounding: Elle (Kingsbury & Alvaro, PVLDB 2020) infers
  isolation anomalies (G0…G2, lost update) from client-observed
  histories in polynomial time; Jepsen's 2025 TigerBeetle analysis still
  found a safety issue (missing results for multi-predicate queries) in a
  database built for ledgers —
  [Elle, arXiv 2003.10554](https://arxiv.org/abs/2003.10554),
  [jepsen-io/elle](https://github.com/jepsen-io/elle),
  [Jepsen TigerBeetle](https://jepsen.io/analyses/tigerbeetle-0.16.11).
- Idea-bank seed: 06/P07 (Elle isolation check) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "The sales deck says 'strictly serializable transfers'. Before
  the bank's security review, prove it or change the deck: run
  transfer + list-append workloads against the 3-node transfer service
  with partitions and pauses, check the histories with Elle, fix what it
  finds, and write the guarantees page."
- Stack: Python workload client + Elle (JVM tool); the service is Go.
- Skills: TEST, DIST, DB, DEBUG, READ
- Size: 10 h → Elle paper §2–4 (90), workload + history recorder
  (2×90), nemesis schedule with `docker pause` / network partitions
  (60), interpret Elle's cycles + fix (90), guarantees page (30).
- What's built: the service, with an isolation bug behind a config flag
  (balance reads served from the backup without a read barrier). He
  writes the workload, history encoder, nemesis, the fix, the doc.
- Done-condition: with the flag on, Elle reports the anomaly in ≥ 9/10
  60-second runs; on his fixed build, 0 anomalies over 10 runs; the
  guarantees page states exactly what the runs cover (rubric).
- Pushback hooks: the tech lead wants to skip partitions "because prod
  never partitions": he should answer with the AWS 2025 and Cloudflare
  incidents from this catalog (E6, E1).
- Ownership change request: a 5-minute Elle job in nightly CI that
  fails the build on any anomaly.

### 2.2 Scribblewire — multiplayer whiteboards with threaded chat for engineering teams

- **Niche / domain:** real-time messaging, presence, multiplayer
  documents.   **Stage:** seed (9 people, $4M raised, 300 paying teams).
- **Culture:** ship daily, Friday demo, founders review every PR within
  hours. Priorities change mid-week when a big prospect asks for
  something. The CTO is obsessed with latency ("if a cursor lags, the
  product feels broken") and allergic to process: design docs are one
  page, max. Everyone is on call; the pager goes to a shared channel.
- **Stack (and why):** Go WebSocket gateway, presence and channel
  servers (cheap goroutine-per-connection); Rust for the document server
  and message-history data service (Figma's multiplayer server and
  Discord's data services are Rust:
  [Figma, Rust in production](https://www.figma.com/blog/rust-in-production-at-figma/) `[unverified URL]`,
  [Discord](https://discord.com/blog/how-discord-stores-trillions-of-messages));
  TypeScript client; Postgres (accounts, boards, permissions),
  ScyllaDB (messages), Redis (presence), memcached, NATS (pub/sub).
- **Team roster:** CTO (acts as tech lead); senior backend engineer
  (realtime); senior full-stack engineer; mid-level client-sync engineer;
  CEO acting as PM; junior engineer (first hire); part-time contract SRE.
- **Main codebase:** `scribblewire/` monorepo: `gateway/`, `presence/`,
  `channels/` (Go); `docsrv/`, `datasvc/` (Rust); `web/` (TS);
  `deploy/compose.yml`; `tools/swarm` (WebSocket load generator),
  `tools/chaos` (process killer + toxiproxy scripts).
- **In-house tools:** WebSocket swarm load generator with slow-consumer
  profiles; chaos killer; edit-trace replayer; permission test-vector
  runner; cache warmer; hash-ring visualiser.
- **Inspired by:** Slack (RTM architecture, 2-22-22 incident), Discord
  (data services, zstd), Figma (multiplayer journal, DBProxy sharding),
  Notion (sharding), Airbnb Himeji and Google Zanzibar (permissions),
  Eg-walker (Gentle & Kleppmann).

#### S1 Presence service: who's online, who's typing
- Company: Scribblewire   Type: review-to-own   Level: L1
- Real-world grounding: Slack's Gateway Servers hold user WebSocket
  subscriptions and fan out from Channel Servers; presence and slow
  consumers are the classic way such gateways fall over —
  [Slack RTM](https://slack.engineering/real-time-messaging/),
  [InfoQ summary](https://www.infoq.com/news/2023/04/real-time-messaging-slack/).
- Ticket: "Dana's PR moves presence from polling to heartbeats over the
  WebSocket with Redis TTL keys and fan-out to board members. Review it.
  You'll own presence after this; the CTO wants typing indicators on it
  next."
- Stack: Go (`gorilla/websocket` or `nhooyr.io/websocket`) + Redis.
- Skills: NET, OS (goroutines, buffers), PERF, READ, TEST
- Size: 5 h → read + run with `tools/swarm` (60), review + quiz (60),
  voice explanation of one heartbeat's path (30), fixes (90),
  ownership change (60).
- Done-condition: swarm of 5,000 clients, 5% slow consumers (read
  1 msg/s), 2%/s churn for 10 min. Pass = gateway RSS < 400 MB
  *(calibrate)*, presence accuracy ≥ 99% against ground truth, goroutine
  count back to baseline within 30 s of disconnect, ≥ 4 of 5 bugs found.
- Planted bugs: TTL shorter than heartbeat interval + jitter → users
  flap offline; fan-out writes done while holding the board mutex;
  unbounded per-connection send buffer (slow consumer → OOM); no
  close-on-backpressure policy; presence keyed by user, not
  (user, device), so closing one tab marks you offline everywhere.
- Ownership change request: typing indicators with server-side
  coalescing (max 1 update per user per 3 s per board).

#### S2 Channel-server failover on the hash ring
- Company: Scribblewire   Type: add-your-part   Level: L2
- Real-world grounding: Slack's Channel Servers are stateful,
  consistent-hashed, and a hash-ring manager (CHARM) replaces a failed
  one in under 20 s —
  [Slack RTM](https://slack.engineering/real-time-messaging/).
- Idea-bank seed: 06/P37 (SWIM + Lifeguard) for the failure detector; 06/P09 (fencing tokens) for ring epochs — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Channel servers and the gateway exist, ring config lives in
  etcd (ADR 0004). When a channel server dies, its channels go dark
  until someone restarts it. Build the ring manager: detect, reassign,
  replay recent messages so there's no gap, keep per-channel order."
- Stack: Go + etcd + ScyllaDB (message store).
- Skills: DIST, SD, OBS, TEST
- Size: 9 h → read ADR + code (60), failure detector (90), reassignment
  with virtual nodes (90), gap replay from the store using per-channel
  sequence numbers (2×90), chaos test (60).
- What's built: gateway, channel servers, ring library. He writes the
  manager, the replay path and the test.
- Done-condition: `kill -9` one of 4 channel servers during 2,000 msg/s
  over 10,000 channels. Pass = all channels served again within 20 s;
  per-channel order preserved; zero acknowledged messages lost; zero
  duplicates after client dedup by sequence; keys moved ≤ 1.2× the
  ideal 1/N.
- Pushback hooks: ADR 0004 uses a 1 s heartbeat timeout: he should ask
  what a 2 s GC pause or network blip does (false failover, split
  ownership) and propose fencing by ring epoch.
- Ownership change request: graceful drain (planned deploy moves
  channels with zero gap and no client reconnect).

#### S3 "@everyone" storm: request coalescing for message history
- Company: Scribblewire   Type: perf-hunt   Level: L3
- Real-world grounding: Discord's Rust data-services layer sits between
  the API and ScyllaDB; "if multiple users are requesting the same row
  at the same time, we'll only query the database once", with
  channel-keyed consistent routing so coalescing actually hits —
  [Discord](https://discord.com/blog/how-discord-stores-trillions-of-messages),
  [InfoQ](https://www.infoq.com/news/2023/06/discord-cassandra-scylladb/).
- Idea-bank seed: 06/P02 (coalescing + XFetch early refresh) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Big customer announced a launch in a 50k-member board chat.
  Everyone opened it at once, ScyllaDB read latency went to seconds,
  then everything timed out. Make `datasvc` survive that, without serving
  history that is more than 1 s stale."
- Stack: Rust (`tokio`, `scylla` driver): the service's language; the
  learner has Rust from his inference engine, the async/concurrency
  part is new.
- Skills: PERF, DIST, OS (async runtimes), DB, OBS
- Size: 10 h → reproduce + flamegraph (90), coalescing map with
  in-flight futures (2×90), channel-keyed routing in the gateway (90),
  measure + tune (60), write-up (30).
- Done-condition: burst replay (30,000 history reads in 5 s on one
  channel + background load on 1,000 others). Pass = ScyllaDB read QPS
  drops ≥ 10× vs baseline, p99 history read < 80 ms *(calibrate)*,
  freshness check: no read returns history missing a message
  acknowledged > 1 s earlier.
- Pushback hooks: the senior engineer suggests a 30 s Redis cache
  instead: he should show it breaks the freshness bar and doubles the
  stale-read window on edits/deletes.
- Ownership change request: export a `coalesced_requests_total` metric
  and a dashboard panel showing coalescing ratio per channel.

#### S4 Eg-walker for board text: try the paper in production
- Company: Scribblewire   Type: build   Level: L5   *(paper-inspired)*
- Real-world grounding: Eg-walker (EuroSys 2025, best artifact award)
  stores the edit event graph and builds CRDT state only while merging;
  it claims ~10× lower steady-state memory than CRDTs, much faster
  loading, and much faster merges of long offline branches than OT —
  [arXiv 2409.14252](https://arxiv.org/abs/2409.14252),
  [Kleppmann](https://martin.kleppmann.com/2025/03/30/eg-walker-collaborative-text.html);
  public real-world traces in
  [josephg/editing-traces](https://raw.githubusercontent.com/josephg/editing-traces/master/sequential_traces/README.md)
  (e.g. `automerge-paper`: 182,315 inserts, 77,463 deletes).
- Idea-bank seed: 06/P12 (Eg-walker; the bank's L3 "adopt + benchmark" variant is a lighter version of this card) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Our sticky-note and doc text uses an RGA CRDT. Big boards
  take 4 s to load and the server's RSS is mostly tombstones. Implement
  Eg-walker in `docsrv` behind a flag and show us whether the paper's
  claims hold on our traces."
- Stack: Rust (server; the reference `diamond-types` is Rust, the
  paper's reference implementation is TypeScript).
- Skills: DIST, PERF, DB (on-disk format), TEST, COMM
- Size: 35 h → M1 read the paper + a 1-page design note (4 h); M2 event
  graph + causal-graph storage (6 h); M3 the walker's
  retreat/advance/apply with a temporary CRDT (10 h); M4 convergence
  fuzzing (5 h); M5 on-disk format + load path (5 h); M6 benchmark
  report vs RGA (5 h).
- Done-condition: (1) convergence fuzz: 3 replicas, random concurrent
  edits, random merge orders, 10,000 seeds → all converge and match the
  reference implementation's output on the concurrent traces; (2) on
  `automerge-paper`, load time and steady-state memory each ≤ 1/5 of the
  RGA baseline *(calibrate; paper claims ~10×)*; (3) merging two branches
  that diverged by 20k ops each < 1 s.
- Pushback hooks: the CTO asks "why not just use Yjs?": he must answer
  with his own numbers, including where Eg-walker loses (the paper says
  worst-case merge ≈ CRDT).
- Ownership change request: add undo of a user's last N ops as new
  events.

#### S5 Incident: cold cache, scatter queries, retry storm
- Company: Scribblewire   Type: incident   Level: L3
- Real-world grounding: Slack 2-22-22: a rolling Consul agent upgrade
  made the cache control plane swap in empty memcached nodes; a client
  boot query cached by channel but sharded by user became a scatter
  query to every shard; "read load increased superlinearly in relation
  to the percentage of cache misses"; retries made recovery less likely;
  fixed by throttling boots and querying only missing keys from
  replicas —
  [Slack](https://slack.engineering/slacks-incident-on-2-22-22/).
- Idea-bank seed: 06/P06 (retry budgets vs. metastable failure) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket (the page): "Nobody can open the app. Postgres shards at 100%
  CPU, cache hit rate 30% and falling, clients reconnecting in a loop.
  Ops was doing a rolling restart of the cache fleet."
- Setup: compose with 4 Postgres shards, 3 memcached, the app, and a
  load generator with real client boot + retry behaviour.
- Stack: Go app, Postgres, memcached, Prometheus/Grafana.
- Skills: OBS, DB, DIST, DEBUG, COMM
- Size: 7 h → triage dashboards (60), find the scatter query via
  `pg_stat_statements` (60), stop the bleeding with admission control on
  boots (60), fix the query (90), postmortem (90).
- Done-condition: harness replays "rolling cache restart at peak". Pass
  = Postgres CPU < 80% throughout, boot success ≥ 99% within 3 min,
  cache hit rate back to 90% within 2 min, and the postmortem names the
  scatter query and retry amplification in its structured fields.
- Pushback hooks: the contract SRE wants to "just add two more shards":
  he should show the scatter makes load grow with shard count.
- Ownership change request: a retry budget in the client SDK (retries ≤
  10% of requests per client per minute).

#### S6 A write-ahead journal for `docsrv`
- Company: Scribblewire   Type: build   Level: L4
- Real-world grounding: Figma's multiplayer service keeps file state in
  memory and checkpointed every 30–60 s; they added a write-ahead log so
  that 95% of edits are saved within 600 ms —
  [Figma](https://www.figma.com/blog/making-multiplayer-more-reliable/),
  [How Figma's multiplayer works](https://madebyevan.com/figma/how-figmas-multiplayer-technology-works/).
- Idea-bank seed: 06/P17 (WAL crash consistency under LazyFS) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "A `docsrv` crash loses up to a minute of everyone's edits on
  that board. Design and build a journal so an acknowledged edit is never
  lost and restart is fast. Design doc first (one page, the CTO's rule)."
- Stack: Rust; journal backend his choice (local fsync'd segments +
  replica, or Redpanda), justified in the doc.
- Skills: DB, OS (fsync, page cache), DIST, PERF, SD
- Size: 22 h → M1 design doc + review (3 h); M2 journal append + group
  commit (5 h); M3 recovery: checkpoint + replay (5 h); M4 truncation /
  compaction after checkpoint (4 h); M5 chaos + latency tuning (5 h).
- Done-condition: 200 random `kill -9`s while 50 clients edit (clients
  log acknowledged sequence numbers). Pass = zero acknowledged edits
  lost, recovery of a 50 MB board < 2 s, p95 edit-ack latency ≤ 600 ms
  (Figma's own number), journal disk usage bounded after checkpoints.
- Pushback hooks: the senior engineer proposes acknowledging before
  fsync "because NVMe is reliable": he must state the loss window on
  power failure and measure what group commit buys instead.
- Ownership change request: a `docsrv journal inspect` CLI that
  verifies checksums and prints the last good offset.

#### S7 Zanzibar-style sharing permissions
- Company: Scribblewire   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: Zanzibar (USENIX ATC 2019) stores relation
  tuples and answers checks in < 10 ms p95; "zookies" make a check at
  least as fresh as the content it guards, solving the "new enemy"
  problem —
  [USENIX](https://www.usenix.org/conference/atc19/presentation/pang).
  Airbnb's Zanzibar-inspired Himeji reached 99.999% availability and
  12 ms p99 ([InfoQ](https://www.infoq.com/news/2021/05/airbnb-himeji)).
- Ticket: "Enterprise prospects need folder-level sharing, groups of
  groups, and guest links. Our `can_view()` is 40 lines of SQL joins
  that time out on big orgs. Build `permsvc`: tuples, a check API,
  consistency tokens on writes, and a cache that doesn't leak."
- Stack: Go + Postgres (what the team runs); OpenFGA/SpiceDB are allowed
  as reading, not as dependencies.
- Skills: SEC, SD, DB, DIST, PERF
- Size: 24 h → M1 data model + doc (4 h); M2 check with userset
  rewrites and nested groups (6 h); M3 consistency tokens (snapshot LSN
  or commit timestamp) (5 h); M4 cache + invalidation (5 h); M5 load
  test (4 h).
- Done-condition: 300 ACL test vectors pass (nested groups, folder
  inheritance, guest links, revocation); the new-enemy scenario (remove a
  user, then add secret content; a check with the content's token must
  deny) passes under replica lag injected by the harness; p99 check
  < 5 ms at 5,000 checks/s over 1M tuples *(calibrate)*.
- Pushback hooks: the CTO wants to cache check results for 60 s: he
  must show the revocation window and what tokens fix.
- Ownership change request: an `expand` API for "who can see this
  board?" used by the admin panel.

#### S8 Design review: horizontally shard Postgres
- Company: Scribblewire   Type: design-review   Level: L4
- Real-world grounding: Figma went vertical-partitioning → logical
  sharding (views, queries routed as if sharded on one DB) → physical
  sharding, with DBProxy (Go) parsing SQL to an AST to route and
  scatter-gather; FKs and global unique indexes are lost, the first table
  took ~9 months —
  [Figma](https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/),
  [pganalyze](https://pganalyze.com/blog/5mins-postgres-figma-dbproxy-sharding-postgres);
  Notion split one Postgres into many shards with ~5 min of downtime
  ([Notion](https://notion.com/blog/sharding-postgres-at-notion)).
- Ticket: "We're at 1.4 TB on one primary and vacuum can't keep up on
  `board_events`. Whiteboard a sharding plan with the CTO: shard key,
  what breaks, migration path, how we'd roll back. Then spike the query
  router so we can see which of our queries would break."
- Stack: Go spike using `pg_query_go` for parsing.
- Skills: SD, DB, DIST, COMM, READ
- Size: 12 h → read Figma + Notion (90), doc (3 h), whiteboard (60),
  router spike (5 h), revise (60).
- Done-condition: rubric (shard key choice vs access patterns,
  cross-shard queries list, logical-then-physical plan, rollback,
  ID generation, ops cost) + the spike passes a routing suite over the
  app's 220 real queries: single-shard queries routed correctly,
  allowed scatter-gathers merged correctly, cross-shard transactions and
  unsafe queries rejected with a reason.
- Pushback hooks: the CTO suggests sharding by `user_id`: he should find
  the board queries that become scatter (S5 is the cautionary tale).
- Ownership change request: a "logical sharding" dry-run mode that logs
  every production query that would be rejected.

### 2.3 Freshet — Kafka-compatible streaming that keeps data only in your object storage

- **Niche / domain:** streaming / event platforms, "diskless" Kafka.
  **Stage:** growth (Series B, ~70 people, ~30 eng, remote-first).
- **Culture:** benchmark-driven: "no perf claim without a flamegraph and
  a dollar number." RFCs live in the repo; weekly cost review where every
  merged PR's effect on object-storage PUT/GET counts is on a slide. The
  manager is an ex-Kafka committer: blunt, fast, fair. Customers are
  infra teams, so support escalations arrive as packet captures.
- **Stack (and why):** Go for stateless agents and the control plane
  (WarpStream is Go; `franz-go` speaks the Kafka protocol); S3-compatible
  object storage (MinIO in dev); Postgres-backed metadata log; toxiproxy
  for faults; Java Kafka clients only in the compatibility suite.
- **Team roster:** EM (data plane); staff engineer (control plane /
  metadata); 2 senior engineers (agents, protocol compatibility);
  technical PM (ex-SRE); junior engineer; solutions engineer who brings
  customer incidents.
- **Main codebase:** `freshet/` monorepo: `agent/` (Kafka protocol
  front-end, batcher, read cache), `control/` (metadata, sequencer,
  compaction scheduler), `pkg/objstore`, `compat/` (client compatibility
  suite), `bench/` (produce/consume benchmark with cost accounting),
  `deploy/compose.yml` (MinIO, Postgres, toxiproxy, Apache Kafka for
  comparison).
- **In-house tools:** cost-accounting benchmark (PUT/GET/bytes → $);
  compatibility-matrix runner; offset-consistency checker; object-store
  fault proxy; partition-skew analyser; metadata-log inspector.
- **Inspired by:** WarpStream (write path, Lightning Topics,
  delayed sequencing), Aiven/KIP-1150, Confluent Kora, AutoMQ, LinkedIn
  Northguard, Apache Kafka KIPs 98/848.

#### F1 Agent batcher: many partitions, one object
- Company: Freshet   Type: review-to-own   Level: L1
- Real-world grounding: WarpStream agents batch data from many
  topic-partitions into one file, and acknowledge produce requests only
  after the file is in object storage and its metadata is committed;
  batch timeout default 250 ms trades PUT cost for latency —
  [write path](https://docs.warpstream.com/warpstream/overview/architecture/write-path),
  [tuning](https://docs.warpstream.com/warpstream/kafka/configure-kafka-client/tuning-for-performance).
- Ticket: "Kenji rewrote the batcher to cut PUTs by 3×. It's the hottest
  code we have. Review it; you're its owner after merge."
- Stack: Go.
- Skills: DIST, OS (timers, concurrency), PERF, READ, TEST
- Size: 5 h → read + run `bench/` (60), review + quiz (60), voice
  walk-through "life of a produce request" (30), fixes (90), ownership
  change (60).
- Done-condition: 100 random `kill -9`s of the agent during produce.
  Pass = every acknowledged record is readable at its offset,
  per-partition offsets contiguous and unique, default-config produce
  p99 < 600 ms *(calibrate)*, ≥ 4 of 5 bugs found.
- Planted bugs: ack sent after upload but before metadata commit; batch
  timer reset on every append (a steady trickle never flushes on time);
  size limit counts records, not bytes; offset ranges assigned outside
  the lock across concurrent flushes; object key reused on retry
  (overwrites a file already referenced).
- Ownership change request: per-tenant `batchMaxSizeBytes` override,
  with a cost-bench run showing the PUT delta.

#### F2 Compaction of small multi-partition files
- Company: Freshet   Type: add-your-part   Level: L2
- Real-world grounding: naive object-storage streaming means many small
  files and high API cost; batching plus compaction is the standard
  answer —
  [WarpStream reducing costs](https://docs.warpstream.com/warpstream/kafka/advanced-agent-deployment-options/reducing-infrastructure-costs),
  [AutoMQ on WarpStream's architecture](https://www.automq.com/blog/warpstream-architecture-explained-kafka-teams) (competitor, secondary).
- Ticket: "Catch-up consumers on low-throughput topics do ~40 GETs per
  MB. The read path and metadata exist (ADR 0009). Write the compactor:
  merge small files into per-partition-sorted larger files, swap metadata
  atomically, delete old objects only when no reader can need them."
- Stack: Go + Postgres + MinIO.
- Skills: DB (LSM-style compaction), DIST, PERF, TEST
- Size: 9 h → read ADR (45), planner (90), merge + upload (90), atomic
  metadata swap (90), grace-period deletion (60), chaos test (60).
- Done-condition: after a 1 h synthetic workload (1,000 low-throughput
  partitions), GETs per catch-up MB drop ≥ 5×; offset scan finds zero
  missing or duplicate records; no reader gets a 404 while compaction
  runs concurrently with 20 catch-up consumers.
- Pushback hooks: ADR 0009 deletes old files right after the metadata
  swap: he should find the in-flight-reader race.
- Ownership change request: a compaction-debt metric (bytes in files
  < 4 MB) and an alert.

#### F3 Hedged PUTs: produce p99 under a cost budget
- Company: Freshet   Type: perf-hunt   Level: L3   *(paper-inspired)*
- Real-world grounding: "The Tail at Scale" (Dean & Barroso, CACM 2013):
  send a backup request once the first has been outstanding past ~p95,
  limiting extra load to ~5% while cutting the tail
  ([CACM](https://cacm.acm.org/research/the-tail-at-scale/),
  [summary](https://blog.acolyer.org/2015/01/15/the-tail-at-scale/));
  for WarpStream, writing a 4 MiB file to S3 is ~400 ms p99, so storage
  tail = produce tail ([tuning docs](https://docs.warpstream.com/warpstream/kafka/configure-kafka-client/tuning-for-performance)).
- Idea-bank seed: 06/P03 (hedged requests) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "A fintech customer's SLO is produce p99 < 350 ms. Our p99 is
  dominated by slow PUTs. Cut it without blowing the PUT budget."
- Stack: Go; MinIO + toxiproxy injecting 1% 2 s stalls.
- Skills: PERF, NET, DIST, OBS
- Size: 8 h → measure + latency histogram by stage (90), hedging with
  delay = live p95 estimate (90), idempotent object naming so hedges
  can't double-commit (60), tune batch timeout (60), report (60).
- Done-condition: under injected stalls, produce p99 < 350 ms
  *(calibrate)*, extra PUTs ≤ 5% of baseline, zero duplicate files
  referenced in metadata.
- Pushback hooks: a peer suggests 3 parallel PUTs always: he should
  price it with `bench/` cost accounting.
- Ownership change request: hedge-rate metric + a circuit breaker that
  disables hedging when > 20% of PUTs are slow (it's an outage, not a
  tail).

#### F4 Incident: consumer-group rebalance storm
- Company: Freshet   Type: incident   Level: L3
- Real-world grounding: the classic rebalance protocol stops the group
  at a global synchronization barrier; KIP-848 (GA in Kafka 4.0) made
  rebalances incremental and broker-driven —
  [Kafka docs](https://kafka.apache.org/40/operations/consumer-rebalance-protocol/),
  [Confluent](https://www.confluent.io/blog/kip-848-consumer-rebalance-protocol/).
- Ticket (the page): "Usage-metering lag is 40M messages and climbing;
  billing runs tonight. The group rebalances every few minutes and
  nobody touched it."
- Setup: Apache Kafka 4.x container (Freshet is wire-compatible), a
  12-consumer Go metering service with eager assignment, downstream
  stalls that push processing past `max.poll.interval.ms`.
- Stack: Go (`franz-go`), Kafka, Prometheus.
- Skills: DIST, OBS, DEBUG, COMM
- Size: 6 h → triage (lag, rebalance logs) (60), root cause (60), fix:
  decouple processing from polling (pause/resume), static membership,
  cooperative or KIP-848 protocol (2×60), postmortem (60).
- Done-condition: harness replays 30 min of traffic + stalls. Pass =
  zero rebalances in steady state, lag < 10k at all times, end-to-end
  p99 < 30 s; postmortem names the poll-interval cause.
- Pushback hooks: the on-call wants `max.poll.interval.ms` = 1 h: he
  should explain what a truly dead consumer then costs.
- Ownership change request: a rebalance-rate alert and a runbook entry.

#### F5 Idempotent producers on stateless agents
- Company: Freshet   Type: build   Level: L4
- Real-world grounding: Kafka's idempotent producer (KIP-98) uses
  producer IDs, epochs and per-partition sequence numbers so retries
  can't duplicate —
  [KIP-98](https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging);
  WarpStream's low-latency Lightning Topics *reject* idempotent producers,
  which shows how hard this is without brokers
  ([WarpStream, Feb 2026](https://www.warpstream.com/blog/the-art-of-being-lazy-log-lower-latency-and-higher-availability-with-delayed-sequencing)).
- Idea-bank seed: 06/P09 (fencing tokens: producer epochs are the same idea) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Customers' Java clients default to `enable.idempotence=true`.
  Our agents are stateless, any agent can get any partition. Make
  sequence checks correct across agents. Design doc first."
- Stack: Go; Java + `franz-go` clients in the compatibility suite.
- Skills: DIST, API (wire protocol), DB, TEST, SD
- Size: 20 h → M1 doc (3 h); M2 InitProducerId + epoch fencing (4 h);
  M3 sequence validation at metadata commit (6 h); M4 compatibility
  matrix (3 h); M5 chaos (4 h).
- Done-condition: 1M records through toxiproxy that drops acks and
  duplicates requests; Java and `franz-go` idempotent producers. Pass =
  zero duplicates and zero reorders per partition; a planted sequence gap
  produces `OUT_OF_ORDER_SEQUENCE_NUMBER`; a zombie producer with an old
  epoch is fenced.
- Pushback hooks: the staff engineer wants sequence state cached in
  agents: he should find the agent-failover duplicate.
- Ownership change request: expire idle producer IDs after 7 days with a
  metadata-size test.

#### F6 Delayed sequencing (LazyLog) for low-latency topics
- Company: Freshet   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: LazyLog (SOSP 2024, reported best paper) separates durability from
  ordering: records are made durable first, and order is bound later but
  before any read. WarpStream applied it: ack after the object write,
  commit metadata asynchronously; median 33 ms / p99 50 ms on S3 Express,
  and agents kept accepting writes through a ~1 h control-plane cut —
  [WarpStream, Feb 2026](https://www.warpstream.com/blog/the-art-of-being-lazy-log-lower-latency-and-higher-availability-with-delayed-sequencing),
  [LazyLog paper (NSF PAR)](https://par.nsf.gov/biblio/10557948),
  [artifact](https://github.com/DistributedSystemResearch/24SOSP-LazyLog-Artifact).
- Ticket: "Product wants a 'fast topic' tier. Implement delayed
  sequencing for opt-in topics: ack after durable write, sequence
  asynchronously, consumers only see sequenced data, and writes survive a
  control-plane outage."
- Stack: Go.
- Skills: DIST, PERF, SD, TEST
- Size: 22 h → M1 read the paper + doc on what guarantees the tier
  drops (3 h); M2 async sequencer + pending-file index (6 h); M3 read
  barrier (consumers never see unsequenced data) (5 h); M4 outage mode +
  catch-up (5 h); M5 benchmark (3 h).
- Done-condition: produce p99 ≥ 40% lower than classic topics in the
  MinIO setup *(calibrate)*; control plane killed for 10 min → produce
  continues, and after recovery every acked record is sequenced exactly
  once; the consistency checker never sees an unsequenced or reordered
  read.
- Pushback hooks: the PM wants idempotent producers on fast topics too:
  he must explain the conflict (F5) and propose what to tell customers.
- Ownership change request: a "sequencing lag" metric and SLO.

#### F7 Virtual log for the metadata store (Delos)
- Company: Freshet   Type: build   Level: L5   *(paper-inspired)*
- Real-world grounding: Delos (OSDI 2020 best paper) virtualises the
  shared log: a VirtualLog chains pluggable "Loglets" that only need a
  fault-tolerant `seal`, so the consensus protocol can be swapped with no
  downtime (Meta did it in production for a 10× latency win) —
  [USENIX](https://www.usenix.org/conference/osdi20/presentation/balakrishnan),
  [Vanlightly intro, 2025](https://jack-vanlightly.com/blog/2025/2/5/an-introduction-to-virtual-consensus-in-delos).
  Context: LinkedIn's Northguard moved metadata to sharded Raft
  ([SiliconANGLE](https://siliconangle.com/2025/06/25/linkedin-introduces-northguard-xinfra-replace-kafka/)).
- Idea-bank seed: 06/P18 (protocol-aware recovery) as a stretch for the Raft loglet — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Postgres as our metadata log is our scaling ceiling. Before
  we pick its replacement, make the replacement swappable: put a
  VirtualLog in front, then migrate live from the Postgres loglet to a
  Raft loglet."
- Stack: Go (`etcd-io/raft` or `hashicorp/raft` for the new loglet).
- Skills: DIST, SD, DB, TEST
- Size: 32 h → M1 paper + doc (4 h); M2 VirtualLog + metastore of the
  chain (6 h); M3 Postgres loglet with seal (5 h); M4 Raft loglet (8 h);
  M5 live reconfiguration under load (5 h); M6 fault drill (4 h).
- Done-condition: live migration under 2,000 commits/s. Pass = zero lost
  or duplicated metadata entries (checker), write pause ≤ 500 ms,
  reverse migration works; the harness's fault scheduler (seal racing
  in-flight appends, leader crash mid-seal, 200 seeds) finds no
  violation.
- Pushback hooks: the staff engineer says "just dual-write during
  migration": he must give the interleaving that breaks it.
- Ownership change request: a `metalog inspect` CLI that prints the
  loglet chain and the sealed tails.

#### F8 Design review: per-topic diskless vs classic storage
- Company: Freshet   Type: design-review   Level: L4
- Real-world grounding: KIP-1150 (accepted March 2026) lets classic and
  diskless topics coexist, chosen per topic; open work includes offset
  assignment for batches in shared storage —
  [Aiven](https://aiven.io/blog/kip-1150-accepted-and-the-road-ahead),
  [KIP-1163](https://cwiki.apache.org/confluence/display/KAFKA/KIP-1163%3A+Diskless+Core);
  Kora paper on cloud-native Kafka
  ([VLDB 2023](https://www.vldb.org/pvldb/vol16/p3822-povzner.pdf));
  WarpStream TCO
  ([benchmark](https://www.warpstream.com/blog/warpstream-s3-express-one-zone-benchmark-and-total-cost-of-ownership)).
- Ticket: "A big prospect wants one cluster with both: sub-10 ms topics
  for trading signals and cheap diskless topics for logs. Whiteboard a
  mixed-mode design and the cost model sales will quote from."
- Stack: design doc + a cost/latency calculator (Python).
- Skills: SD, DIST, PERF, COMM
- Size: 10 h → reading (2 h), doc (3 h), whiteboard (60 min), calculator
  (3 h), revise (60 min).
- Done-condition: rubric (placement of the source of truth per mode,
  offset assignment, inter-AZ traffic, failure modes, migration between
  modes) + his calculator reproduces the harness's reference model
  within 5% on 6 workload profiles (throughput, partitions, retention,
  fan-out, AZs → compute, PUT/GET, inter-AZ transfer, storage $/month).
- Pushback hooks: sales wants "one price per GB": he must show the
  workload that makes that lose money.
- Ownership change request: add a tiered-storage (KIP-405) column to
  the calculator.

### 2.4 Siltstone Foundation — stewards of SiltDB, an embeddable time-series + key-value engine on object storage

- **Niche / domain:** databases & storage engines (LSM on object
  storage, time-series compression, caching).   **Stage:** open-source
  foundation (12 maintainers employed by 5 sponsor companies, ~150
  contributors).
- **Culture:** everything in public: RFCs in `rfcs/`, design debates in
  issues, reviews that can take a week and ask for a benchmark on every
  claim. No deadlines, but a release train every 6 weeks: miss it and
  your PR waits. "Boss" = lead maintainer who chairs the technical
  steering committee; the contributor ladder (contributor → reviewer →
  committer) is the promotion system. Kind but rigorous: unsafe code
  needs a `// SAFETY:` comment and a second reviewer.
- **Stack (and why):** Rust (SlateDB, Neon, InfluxDB 3, GreptimeDB are
  Rust; memory safety + no GC pauses for a storage engine); `object_store`
  crate over S3/GCS/MinIO; Arrow/Parquet for exports; `criterion`
  benchmarks; `proptest`; Python bindings via PyO3.
- **Team roster:** lead maintainer (TSC chair); storage-engine maintainer
  (LSM, compaction); query/time-series maintainer; release manager;
  2 sponsor-company engineers (one runs SiltDB in production and files
  the incidents); a first-time contributor he mentors later (the
  "junior").
- **Main codebase:** `siltdb/`: `silt-core` (memtable, WAL, SSTs,
  manifest, compaction), `silt-ts` (time-series columns, codecs),
  `silt-cache` (block + disk cache), `silt-cli` (`silt-wal`, `silt-sst`
  inspectors), `bench/` (YCSB-like + TSBS-like workloads), `rfcs/`,
  `compose.yml` (MinIO + toxiproxy).
- **In-house tools:** SST/WAL inspectors; crash-state explorer; I/O
  accounting layer (counts every GET/PUT and byte); trace-driven cache
  simulator; benchmark regression bot; fault-injecting object store.
- **Inspired by:** SlateDB, RocksDB (write stalls), Neon (WAL/pageserver
  split), Facebook Gorilla, Monkey (Harvard DASlab), WiscKey, ALICE
  (UW-Madison), S3-FIFO (CMU/Harvard), InfluxDB 3.

#### D1 Scan statistics: "why was this query slow?"
- Company: Siltstone   Type: add-your-part   Level: L1
- Real-world grounding: object-storage engines live or die by
  GETs-per-query; SlateDB's design leans on block caches, bloom filters
  and disk caches to cut reads
  ([dbdb.io on SlateDB](https://dbdb.io/db/slatedb/revisions/2));
  this card mirrors the shape of SlateDB's open "good first issue" and
  "help wanted" items (section 3).
- Ticket (a `good first issue`): "Add per-scan counters: SSTs
  considered, bloom negatives, blocks read, cache hits by tier, bytes
  fetched. Expose via `ScanStats` and `silt-cli scan --stats`. The I/O
  accounting layer already counts; you wire it through the iterator."
- Stack: Rust.
- Skills: READ, DB, OBS, TEST
- Size: 4 h → read the iterator stack (60), wire counters (90),
  tests + CLI (60), PR description in the project's template (30).
- Done-condition: counters match the harness's expected values on 5
  fixture databases; scan throughput regression < 2% in `criterion`;
  `cargo clippy -D warnings` clean.
- Pushback hooks: the reviewer asks whether counters should be atomics
  or per-iterator: he must justify (contention vs aggregation).
- Ownership change request: add a `--stats-json` output used by the
  benchmark bot.

#### D2 Review: per-SST bloom filters
- Company: Siltstone   Type: review-to-own   Level: L2
- Real-world grounding: bloom filters are the main defence against
  extra object-storage GETs on misses in LSMs on S3
  ([SlateDB README](https://docs.rs/crate/slatedb/0.15.0/source/README.md));
  RocksDB documents the same bits-per-key/FPR trade
  ([RocksDB bloom filter wiki](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter) `[unverified URL]`;
  RocksDB's Ribbon filter saves ~30% filter memory for 3–4× CPU:
  [RocksDB blog](https://rocksdb.org/blog/2021/12/29/ribbon-filter.html)).
- Idea-bank seed: 06/P13 (binary fuse / Ribbon filters) as the follow-up after the review — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "A sponsor engineer's PR adds bloom filters to SSTs. CI is
  green. Review it like a committer: you'll maintain this module."
- Stack: Rust.
- Skills: DB, READ, TEST, PERF
- Size: 5 h → read + run property tests (60), review + quiz (60), voice
  explanation of FPR vs bits/key (30), fixes (90), ownership change (60).
- Done-condition: harness property test: zero false negatives over 1M
  keys, measured FPR within 10% of target at 10 bits/key, ≤ 1 data-block
  read on 99% of misses; ≥ 4 of 5 bugs found.
- Planted bugs: filter built on the internal key (with sequence number)
  but probed with the user key → false negatives; FPR formula uses
  `log10` instead of `ln`; filter fetched from object storage on every
  `get` (no caching); hash depends on platform endianness (filters built
  on one machine fail on another); filter block not covered by the SST
  checksum.
- Ownership change request: a `silt-sst inspect --bloom` that prints the
  measured FPR of a file.

#### D3 Monkey: per-level bloom filter memory
- Company: Siltstone   Type: perf-hunt   Level: L3   *(paper-inspired)*
- Real-world grounding: Monkey (SIGMOD 2017) shows that uniform
  bits-per-key across LSM levels is suboptimal; allocating memory to
  minimise the *sum* of false-positive rates cut lookup latency 50–80% in
  its LevelDB implementation —
  [paper](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf),
  [TODS 2018 extension](https://cs-people.bu.edu/mathan/publications/tods18-dayan.pdf).
- Ticket (RFC 0031 accepted): "Implement Monkey-style allocation behind
  `filter_policy = "monkey"`. Same total memory as today. Show the
  zero-result-lookup improvement with the I/O accounting layer, not wall
  clock alone."
- Stack: Rust.
- Skills: PERF, DB, COMM (benchmark write-up)
- Size: 9 h → read the paper's allocation derivation (90), implement the
  allocator from level sizes (90), rebuild filters on compaction (90),
  benchmark + write-up (2×60).
- Done-condition: on the harness's 7-level dataset with an average of
  5 bits/key, zero-result lookups read ≥ 40% fewer blocks than uniform
  allocation *(calibrate)*, existing-key lookups no worse than +5%, total
  filter memory within 1% of the budget.
- Pushback hooks: a maintainer asks "what happens while levels are being
  resized during compaction?": he must handle the transition.
- Ownership change request: expose the per-level FPRs in `ScanStats`
  (D1).

#### D4 Gorilla codec for float columns
- Company: Siltstone   Type: add-your-part   Level: L3   *(paper-inspired)*
- Real-world grounding: Facebook's Gorilla (VLDB 2015) compresses
  timestamps with delta-of-delta and values by XOR with the previous
  value, reducing storage ~10× and enabling in-memory queries
  (73× lower latency than its HBase design) —
  [PVLDB 8, p1816](https://www.vldb.org/pvldb/vol8/p1816-teller.pdf).
- Ticket: "`silt-ts` has a codec trait and a plain + LZ4 codec (ADR in
  `rfcs/0019`). Add `gorilla` for timestamp and f64 columns, with a
  fast decoder; metrics users are 70% of our storage."
- Stack: Rust (bit-level I/O; SIMD optional).
- Skills: PERF, DB, OS (cache behaviour), TEST
- Size: 10 h → bit writer/reader (90), timestamps (90), XOR floats
  (2×90), fuzzing edge cases (60), decode speed work (60).
- Done-condition: ≥ 8× smaller than raw 16 B/point on the harness's 3
  metric datasets *(calibrate)*; bit-exact round trip including NaN
  payloads, ±0.0, ±∞; decode ≥ 150M points/s on one core
  *(calibrate)*; `cargo fuzz` 10 min, no crash.
- Pushback hooks: RFC 0019 allows codecs to allocate per block: he
  should notice the allocator showing up in the decode flamegraph.
- Ownership change request: choose codec per column automatically from
  a sample (pick the smaller of gorilla vs LZ4).

#### D5 Incident: ingestion stalls during a customer backfill
- Company: Siltstone   Type: incident   Level: L3
- Real-world grounding: LSM engines throttle or stop writes when L0
  files or pending compaction bytes pile up ("write stalls") —
  [RocksDB Write Stalls wiki](https://github.com/facebook/rocksdb/wiki/Write-Stalls).
- Ticket (sponsor's bug report): "Ingest p99 went from 5 ms to 9 s
  during a backfill, then writes stopped for 40 s at a time. Logs
  attached. We changed nothing (we did upgrade to 0.18)."
- Setup: harness ships the sponsor's config (compaction concurrency
  lowered to 1 by a new default in "0.18"), MinIO with 80 ms injected
  PUT latency, and the backfill traffic.
- Stack: Rust engine, Prometheus metrics, the sponsor's logs.
- Skills: DB, OBS, DEBUG, PERF, COMM
- Size: 6 h → read logs/metrics (60), reproduce (60), root cause: L0
  count + the changed default (60), fix: restore concurrency, add
  write-rate limiting that slows smoothly before the stop trigger (90),
  public postmortem in an issue (60).
- Done-condition: backfill replay: no write blocked > 100 ms, L0 count
  stays below the slowdown trigger, ingest throughput ≥ 80% of the
  no-backfill baseline; postmortem names the default change.
- Pushback hooks: a contributor proposes raising the stop trigger to
  1,000 files: he must explain the read-amplification cost.
- Ownership change request: a `write_stall_seconds_total` metric with
  a reason label.

#### D6 `silt-crashcheck`: crash-consistency explorer + WAL tools
- Company: Siltstone   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: ALICE (OSDI 2014) showed applications' update
  protocols (incl. LevelDB, SQLite) depend on file-system "persistence
  properties" POSIX doesn't promise, and built a tool that generates
  post-crash states to find vulnerabilities —
  [UW-Madison](https://research.cs.wisc.edu/adsl/Publications/alice-osdi14.html),
  [summary](https://blog.acolyer.org/2016/02/11/fs-not-equal/); LazyFS (PVLDB
  2024) reproduces lost un-fsynced writes and found 8 new bugs in
  PostgreSQL, etcd, Redis and others
  ([paper](https://www.vldb.org/pvldb/vol17/p3017-ramos.pdf),
  [GitHub](https://github.com/dsrhaslab/lazyfs)).
- Idea-bank seed: 06/P17 (LazyFS); LazyFS can replace or validate the VFS shim — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket (RFC 0027): "Build a crash explorer for SiltDB's local WAL +
  manifest path: record the syscall trace of an update, generate crash
  states (prefixes, reorderings allowed between fsyncs, torn last write),
  run recovery on each, check acknowledged writes survive. Ship
  `silt-wal verify|dump|replay --until <lsn>` alongside."
- Stack: Rust; `strace`-style recording via an in-process VFS shim
  (portable and deterministic).
- Skills: OS (fsync, rename, directory entries), DB, TEST, DEBUG
- Size: 24 h → M1 RFC reading + design note (3 h); M2 VFS shim +
  recorder (5 h); M3 crash-state generator (6 h); M4 recovery checker
  (4 h); M5 `silt-wal` tools (4 h); M6 CI integration (2 h).
- Done-condition: harness re-introduces 3 historical-style bugs
  (rename without fsync of the parent directory; manifest updated before
  the SST is fsynced; a torn final WAL record treated as corruption
  instead of truncated). The explorer flags all 3. On the fixed engine,
  500 generated crash states all recover every acknowledged write.
  `silt-wal verify` reports the exact byte offset of a planted
  corruption.
- Pushback hooks: the lead maintainer asks whether the shim's model
  matches ext4 or "POSIX minimum": he should pick, and say what's not
  covered.
- Ownership change request: run 50 crash states per PR in CI (< 3 min).

#### D7 Read path on S3: coalesced range GETs + S3-FIFO cache
- Company: Siltstone   Type: perf-hunt   Level: L4   *(paper-inspired)*
- Real-world grounding: S3-FIFO (SOSP 2023): three FIFO queues (small,
  main, ghost) beat state-of-the-art eviction on 6,594 traces with ~6×
  LRU's throughput at 16 threads —
  [paper](https://junchengyang.com/publication/sosp23-s3fifo.pdf),
  [slides](https://junchengyang.com/slides/sosp23-s3fifo.pdf); SIEVE
  (NSDI 2024) is a simpler alternative. SlateDB uses in-memory block
  caches plus local SST disk caches for the same problem.
- Idea-bank seed: 06/P01 (SIEVE / S3-FIFO); 06/P15 (mmap adopt memo) for the pushback — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Dashboards querying a day of data issue ~3,000 GETs and take
  4 s. Coalesce adjacent block reads into range GETs, add a local disk
  tier, and replace the LRU block cache with S3-FIFO. Use the I/O
  accounting layer to prove each step."
- Stack: Rust; MinIO + toxiproxy (30 ms GET latency).
- Skills: PERF, DB, OS (page cache, concurrency), NET
- Size: 16 h → baseline + I/O profile (2 h), range coalescing (4 h),
  disk tier (4 h), S3-FIFO + concurrency (4 h), report (2 h).
- Done-condition: 24 h-range query p50 ≥ 3× faster and GET count ≥ 5×
  lower *(calibrate)*; on the harness's cache trace, S3-FIFO's hit ratio
  ≥ LRU's + 3 points at the same size *(calibrate)*; no stale block ever
  served after compaction deletes an SST (checker).
- Pushback hooks: a maintainer wants `mmap` for the disk tier: he should
  cite "Are You Sure You Want to Use MMAP in Your DBMS?" (CIDR 2022)
  ([CMU page](https://db.cs.cmu.edu/mmap-cidr2022/)) and argue either way with numbers.
- Ownership change request: cache admission skip for full scans
  (scan-resistance flag).

#### D8 RFC review: key-value separation for large values (WiscKey)
- Company: Siltstone   Type: design-review   Level: L5   *(paper-inspired)*
- Real-world grounding: WiscKey (FAST 2016) stores keys in the LSM and
  values in a separate log to cut write amplification for large values,
  at the cost of range-scan locality and value-log GC
  ([USENIX FAST '16](https://www.usenix.org/conference/fast16/technical-sessions/presentation/lu)).
  Trace spans and blobs are a growing share of SiltDB writes.
- Ticket: "Write RFC 0034: key-value separation for values > 1 KB. It
  goes to public review by the TSC: expect hard questions on GC, crash
  safety, and scan regressions. Include a spike that measures the core
  claim on object storage."
- Stack: RFC (Markdown, project template) + Rust spike.
- Skills: SD, DB, PERF, COMM
- Size: 14 h → paper + prior art (2 h), RFC draft (4 h), spike (5 h),
  review round with the TSC (voice, 60 min), revision (2 h).
- Done-condition: (1) RFC rubric (motivation with data, design, GC
  algorithm and its crash safety, interaction with compaction and
  snapshots, scan mitigation, migration, alternatives incl. "do
  nothing"); (2) spike: for 4 KB values, write amplification (bytes
  PUT / user bytes) ≥ 3× lower *(calibrate)*; a delete-heavy run's GC
  reclaims ≥ 80% of dead value-log space; range scans within 2× of
  baseline with prefetch.
- Pushback hooks: the storage maintainer argues object storage already
  makes write amplification cheap: he must price it (PUT counts, bytes)
  rather than assert.
- Ownership change request: none: if accepted, the RFC becomes the next
  `build` ticket.

### 2.5 Glimmerline — usage-priced observability: logs, metrics and traces in one columnar store

- **Niche / domain:** observability platforms.   **Stage:** growth /
  late-stage (~600 people, ~180 eng, pre-IPO).
- **Culture:** cost is the product: every team owns a $/GB or $/query
  number on a wall dashboard. Quarterly OKRs set the deadlines. The
  manager is an ex-SRE who answers every proposal with "show me the
  graph." Heavy on-call, real blameless postmortems, and an uncomfortable
  truth everyone knows: Glimmerline monitors itself with itself.
- **Stack (and why):** Go (an OpenTelemetry Collector distribution as
  agent; ingest gateways), Kafka (Redpanda in dev), ClickHouse for logs
  and traces, a Go metrics store in the Mimir mould, Rust for the
  log-parsing hot path (ClickHouse replaced OTel parsing for CPU reasons:
  [ClickHouse, 2025](https://clickhouse.com/blog/scaling-observability-beyond-100pb-wide-events-replacing-otel)),
  Python notebooks for capacity planning.
- **Team roster:** EM (Ingest); staff engineer (storage & query);
  senior engineers (metrics pipeline, log pipeline); PM (pricing &
  usage); junior engineer; embedded SRE; billing engineer.
- **Main codebase:** `glimmerline/`: `agent/` (collector distro, custom
  processors), `ingest/` (auth, rate limits, routing to Kafka),
  `writers/` (Kafka → ClickHouse with dedup), `metrics/` (series store,
  sketches), `query/`, `billing/usage`, `deploy/compose.yml` (Redpanda,
  ClickHouse, MinIO, Grafana).
- **In-house tools:** synthetic telemetry generator with cardinality
  knobs; incident traffic replayer; cost-per-tenant dashboard; query
  cost estimator; meta-monitoring dead-man's switch; schema-drift
  checker.
- **Inspired by:** Datadog (Husky, DDSketch, 2023-03-08 incident),
  ClickHouse LogHouse, Uber CLP, Grafana Mimir, OpenTelemetry Collector,
  CockroachDB admission control.

#### G1 Review: tail-sampling processor
- Company: Glimmerline   Type: review-to-own   Level: L1
- Real-world grounding: tail sampling decides per trace after waiting
  for its spans; it needs all spans of a trace on one collector (trace-ID
  load balancing) and bounded memory —
  [collector-contrib tailsamplingprocessor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/tailsamplingprocessor) `[README not re-read this session]`.
- Ticket: "Customers pay per ingested span; they want 'keep all error
  traces, 10% of the rest'. Ola's PR adds our tail-sampling processor
  with per-tenant policies. Review it; you own sampling after this."
- Stack: Go (collector component API).
- Skills: OBS, DIST, OS (memory bounds), READ, TEST
- Size: 5 h → read + run (60), review + quiz (60), voice walk-through
  of one trace's journey (30), fixes (90), ownership change (60).
- Done-condition: 100k traces (2% errors, spans spread over 30 s, 5%
  arriving late) through 2 collectors behind a trace-ID load balancer.
  Pass = 100% of error traces kept *complete*, overall kept ratio
  within ±5% of 10%, collector RSS < 1 GB *(calibrate)*, ≥ 4 of 5 bugs
  found.
- Planted bugs: decision cache keyed by span ID; late spans after the
  decision are dropped instead of following the cached decision; the
  trace-count limit evicts undecided traces silently; probabilistic
  policy uses `rand` instead of a trace-ID hash, so two collectors
  disagree; per-tenant policy lookup on every span takes a global lock.
- Ownership change request: a "keep slowest 1%" latency policy using a
  streaming p99 estimate.

#### G2 DDSketch percentiles in the rollup service
- Company: Glimmerline   Type: add-your-part   Level: L2   *(paper-inspired)*
- Real-world grounding: DDSketch (Datadog, PVLDB 2019) is the first
  quantile sketch that is fully mergeable *and* has relative-error
  guarantees (any quantile within α of the true value); rank-error
  sketches give large relative errors on skewed latency data —
  [PVLDB](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf),
  [arXiv 1908.10693](https://arxiv.org/abs/1908.10693),
  [summary](https://blog.acolyer.org/2019/09/06/ddsketch/).
- Ticket: "Our p99s come from fixed histogram buckets and customers
  catch us being 30% off. The rollup service and its storage format exist
  (ADR 0022). Add a DDSketch metric type end to end: ingest, merge
  across shards and time, query."
- Stack: Go (interop test with Datadog's `sketches-go`).
- Skills: OBS, PERF, API, TEST
- Size: 8 h → read paper §2–3 (60), mapping + store (90), merge +
  serialisation (90), query path (60), accuracy tests (60).
- Done-condition: after merging 64 shard sketches, relative error ≤ 1%
  for p50/p90/p99/p99.9 on 4 distributions (Pareto, log-normal, bimodal,
  constant + outliers); merged sketch identical to one built over the
  union; ≤ 2 KB per sketch for 1M values at α = 1% *(calibrate)*;
  round-trips through `sketches-go`.
- Pushback hooks: ADR 0022 stores sketches as JSON: he should measure
  size and decode cost and push for protobuf.
- Ownership change request: support negative values (two stores) for
  clock-skew metrics.

#### G3 CLP-style log compression with search on compressed data
- Company: Glimmerline   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: CLP (OSDI 2021) splits each log line into a
  template + variables, compresses losslessly and searches without full
  decompression, matching or beating Elasticsearch/Splunk search speed;
  Uber reported 169× compression and cut a $1.8M/yr log-storage line to
  ~$10k/yr in phase 1 —
  [USENIX](https://www.usenix.org/conference/osdi21/presentation/rodrigues),
  [Uber](https://www.uber.com/blog/reducing-logging-cost-by-two-orders-of-magnitude-using-clp).
  Datasets: [Loghub](https://github.com/logpai/loghub) (19 real system
  log sets).
- Ticket: "Log storage is 61% of our COGS. Prototype a CLP-style
  encoding for our cold log tier and prove it on public logs before we
  touch customer data."
- Stack: Rust (parsing hot path, the team's choice for CPU-bound work).
- Skills: PERF, DB (encodings, dictionaries), DATA, TEST
- Size: 22 h → M1 paper + design note (3 h); M2 tokenizer + template
  extraction (5 h); M3 variable dictionaries + encoded columns (5 h);
  M4 search on encoded data (5 h); M5 benchmark vs zstd (4 h).
- Done-condition: on 4 Loghub datasets: byte-exact lossless round trip;
  compressed size ≤ 0.5× of `zstd -19` on raw *(calibrate)*; a search for
  a variable value (e.g. an HDFS block id) runs ≥ 5× faster than
  decompress + grep.
- Pushback hooks: the staff engineer wants to drop rare templates into a
  raw fallback: he should measure the cliff.
- Ownership change request: wildcard search (`*timeout*`) over
  templates.

#### G4 Incident: one customer's deploy adds `request_id` as a metric label
- Company: Glimmerline   Type: incident   Level: L3
- Real-world grounding: per-tenant series limits
  (`max_global_series_per_user`) exist in Mimir-family systems because
  one tenant's cardinality can take down shared ingesters —
  [Grafana limits docs](https://grafana.com/docs/enterprise-metrics/latest/manage/tenant-management/limits/).
- Ticket (the page): "Metrics ingesters OOM-looping in us-east. Series
  count 50× in 20 min. All tenants' dashboards are gaps."
- Setup: replay of the incident traffic (one tenant's new label with
  unbounded values) against the compose stack.
- Stack: Go metrics store, Prometheus self-metrics, Grafana.
- Skills: OBS, OS (memory), DIST, DEBUG, COMM
- Size: 6 h → triage (60), find the tenant and the label (60),
  per-tenant series limiter at ingest with a clear 429 (90), label-drop
  rule as emergency lever (30), postmortem (60).
- Done-condition: on replay, ingester RSS stays < 2 GB, other tenants'
  ingest p99 < 2× baseline, the offending tenant gets 429s naming the
  limit and label; postmortem has the structured fields filled.
- Pushback hooks: the PM fears 429s cause churn: he should propose a
  soft limit + customer notification before the hard limit.
- Ownership change request: a "top cardinality contributors per
  tenant" API for support.

#### G5 Perf-hunt: the "top endpoints by p99" dashboard takes 9 s
- Company: Glimmerline   Type: perf-hunt   Level: L3
- Real-world grounding: ClickHouse at petabyte log scale lives on
  sorting keys, wide events and pre-aggregation (LogHouse: from 19 PiB to
  100+ PB) —
  [ClickHouse](https://clickhouse.com/blog/scaling-observability-beyond-100pb-wide-events-replacing-otel),
  [LogHouse across 3 clouds](https://clickhouse.com/blog/a-quadrillion-rows-across-the-three-cloud-scaling-loghouse).
- Ticket: "The default APM dashboard's main panel is 9 s p95 on big
  tenants. Get it under half a second without changing what it shows."
- Stack: ClickHouse SQL (ORDER BY keys, skip indexes, projections,
  materialized views), Go query service.
- Skills: PERF, DB, OBS
- Size: 8 h → `EXPLAIN` + `system.query_log` analysis (90), sorting-key
  experiment (90), projection or materialized view (90), verify results
  + ingest cost (90).
- Done-condition: on the 500M-row harness dataset, panel query p95
  < 500 ms *(calibrate)*, results identical to the original query,
  ingest throughput down ≤ 10%, storage up ≤ 20%.
- Pushback hooks: a peer proposes caching the panel for 5 min: he should
  say why a perf fix beats a cache for an incident-time dashboard.
- Ownership change request: add the query to the perf regression suite
  with a budget.

#### G6 Exactly-once writers: Kafka → ClickHouse
- Company: Glimmerline   Type: build   Level: L4
- Real-world grounding: Datadog's Husky routes each event
  deterministically by (timestamp, id) to one shard, so dedup is
  shard-local; duplicates would skew alerting and usage billing —
  [Datadog](https://www.datadoghq.com/blog/engineering/husky-deep-dive/),
  [InfoQ](https://www.infoq.com/news/2023/06/datadog-husky-data-ingestion/).
- Ticket: "Billing found 0.3% double-counted spans after a writer
  crash-loop. Make writers exactly-once end to end: agents retry, Kafka
  redelivers, writers crash. Design doc first."
- Stack: Go writers, Redpanda, ClickHouse.
- Skills: DIST, DB, SD, TEST
- Size: 20 h → M1 doc (3 h); M2 deterministic routing + shard-local
  dedup state (5 h); M3 atomic "insert + offset" via insert tokens or a
  commit table (6 h); M4 chaos suite (4 h); M5 throughput (2 h).
- Done-condition: 50M events with chaos (writer crash between insert
  and offset commit, Kafka redelivery, agent duplicate sends). Pass =
  zero duplicates and zero losses by event ID; throughput ≥ 200k
  events/s *(calibrate)*.
- Pushback hooks: the staff engineer says "ReplacingMergeTree dedups
  for us": he must explain when merges happen and what queries see
  before them.
- Ownership change request: a daily dedup audit job with a metric.

#### G7 Design review: monitoring that survives our own outage
- Company: Glimmerline   Type: design-review   Level: L4
- Real-world grounding: Datadog's 2023-03-08 outage: an automatic
  systemd security update restarted `systemd-networkd`, which deleted
  Cilium's routes on tens of thousands of nodes in several regions at
  once (the unattended-upgrade window was the same everywhere) —
  [Datadog deep dive](https://www.datadoghq.com/blog/engineering/2023-03-08-deep-dive-into-platform-level-impact/);
  Cloudflare's independent status page failed during its 2025-11-18
  outage by coincidence ([Cloudflare](https://blog.cloudflare.com/18-november-2025-outage/)).
- Idea-bank seed: 06/P50 (spectral-residual anomalies) for "silent zero" detection; 06/P48 (sequential testing) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "If Glimmerline is down, Glimmerline can't tell us.
  Whiteboard a meta-monitoring path with no shared fate, then build the
  minimum version."
- Stack: design doc + a small Go or Python dead-man's switch.
- Skills: SD, OBS, NET, COMM
- Size: 10 h → reading (90), doc (3 h), whiteboard (60), minimal build
  (3 h), drill (60).
- Done-condition: rubric (shared-fate analysis incl. OS update
  channels, independent alert delivery, "silent zero" detection, test
  plan); chaos drill in compose: harness kills ingest + Kafka → his
  monitor pages a webhook within 60 s; traffic drops to zero while
  services stay "up" → page within 120 s; zero false pages in a 30 min
  normal run.
- Pushback hooks: the EM suggests running the meta-monitor on the same
  Kubernetes cluster "for ops simplicity": he must name the shared fate.
- Ownership change request: a monthly game-day script.

#### G8 Query admission control for shared ClickHouse clusters
- Company: Glimmerline   Type: build   Level: L5
- Real-world grounding: CockroachDB's admission control queues work by
  priority and tenant, using CPU slots and storage tokens (LSM health),
  so one tenant can't degrade another —
  [CockroachDB 2022](https://www.cockroachlabs.com/blog/admission-control-in-cockroachdb/),
  [2024](https://www.cockroachlabs.com/blog/admission-control-unexpected-overload/),
  [Vanlightly analysis](https://jack-vanlightly.com/analyses/2023/11/21/serverless-cockroachdb-asds-chapter-4-part-2).
- Idea-bank seed: 06/P43 (Dominant Resource Fairness) for CPU + memory query shares — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "One tenant's analysts ran 50 heavy queries a minute and
  every other tenant's dashboards timed out. Build admission control in
  the query service: estimate cost before running, queue fairly by
  tenant, shed with a useful error."
- Stack: Go query service; ClickHouse `EXPLAIN ESTIMATE` and
  `system.query_log` for cost signals.
- Skills: SD, PERF, DB, DIST, OBS
- Size: 30 h → M1 doc (4 h); M2 cost estimator trained on query-log
  history (6 h); M3 weighted-fair queue per tenant (6 h); M4 feedback
  from cluster CPU/memory (6 h); M5 noisy-neighbour replay + tuning
  (6 h); demo (2 h).
- Done-condition: noisy-neighbour replay: other tenants' p99 ≤ 1.5×
  their solo baseline; the heavy tenant gets 429s carrying its cost
  estimate and retry-after; cluster CPU ≥ 70% busy (not
  over-conservative); estimator within 2× of actual cost for 80% of
  queries.
- Pushback hooks: the PM wants paid tiers to bypass the queue: he
  should design priority classes without starvation.
- Ownership change request: a per-tenant "query budget remaining"
  header.

### 2.6 Alderwick Edge — the edge platform division of Alderwick (a fictional big-tech cloud)

- **Niche / domain:** edge proxy, CDN cache, WAF, L4 load balancing,
  rate limiting, DNS automation, global config.   **Stage:** big-tech
  division (~400 engineers in the division; he joins Edge Proxy, 12
  people).
- **Culture:** process-heavy and proud of it. Design docs have named
  approvers; production-readiness reviews before launch; every change
  rides the staged rollout (dogfood → canary PoP → 1% → 10% → global).
  Postmortems follow a fixed template and are read at a weekly review.
  Deadlines are quarter-scale, but a Sev-1 drops everything. Senior
  manager is political but protective; the principal tech lead reviews
  for "what does this do at 30M requests per second?"
- **Stack (and why):** Rust proxy on a Pingora-style framework
  (Cloudflare replaced NGINX with Pingora and FL1 with Rust FL2:
  [Pingora](https://blog.cloudflare.com/how-we-built-pingora-the-proxy-that-connects-cloudflare-to-the-internet/),
  [InfoQ on FL2](https://www.infoq.com/news/2025/10/cloudflare-rust-proxy));
  Rust + eBPF/XDP for the L4 balancer; Go control plane; legacy Lua WAF
  being ported; ClickHouse for request analytics.
- **Team roster:** senior manager; principal tech lead (proxy); senior
  engineers (cache, WAF); edge SRE; TPM (rollouts); PM (security
  products); new-grad engineer.
- **Main codebase:** `edge/` monorepo: `proxy/` (Rust), `waf/` (Lua
  legacy + Rust engine), `l4lb/` (Rust + eBPF loader), `ratelimit/`,
  `config/` (plan/enact control plane), `dnsauto/`,
  `tools/fleet-sim` (fleet + rollout simulator), compose with toxiproxy,
  `tc netem` and synthetic origins.
- **In-house tools:** fleet rollout simulator; config validator and
  fuzzer; regex cost profiler; synthetic origins (slow, flaky,
  erroring); sampled-traffic replayer; global kill-switch service.
- **Inspired by:** Cloudflare (Pingora, FL2, 2019 and 2025 outages,
  rate limiting, Quicksilver), AWS (2025-10 DynamoDB DNS race), Google
  Maglev, Netflix concurrency limits, Meta Configerator, Fly.io
  Corrosion.

#### E1 Review: the bot-feature file loader
- Company: Alderwick Edge   Type: review-to-own   Level: L1
- Real-world grounding: Cloudflare 2025-11-18: a ClickHouse permission
  change made a metadata query return duplicate rows; the bot-management
  feature file doubled, exceeded the proxy's preallocated limit of 200
  features (normal use ~60), and FL2 panicked with "called
  `Result::unwrap()` on an `Err` value"; the file regenerated every ~5 min
  so the network flapped. Remediation: treat internal config files like
  user input, add kill switches —
  [Cloudflare](https://blog.cloudflare.com/18-november-2025-outage/).
- Ticket: "Ren's PR moves the bot-feature file loader to the new proxy.
  After what happened to *a certain other company* in November, the
  principal wants you to review it and own it."
- Stack: Rust.
- Skills: READ, TEST, SEC (input hardening), OBS, DEBUG
- Size: 4 h → read + run (45), review + quiz (60), voice explanation
  of "what happens to a request when the file is bad" (30), fixes (75),
  ownership change (30).
- Done-condition: harness fuzzes 1,000 bad files (oversized, duplicate
  rows, truncated, wrong types) while the proxy serves traffic. Pass =
  no panic, no 5xx spike, last-known-good stays active,
  `config_rejected_total{reason}` increments correctly, ≥ 4 of 5 bugs
  found.
- Planted bugs: `.unwrap()` on the capacity check; size and row-count
  validated *after* the swap; duplicate rows not rejected; non-atomic
  swap (worker threads can see half-updated state); on restart, loads
  only the newest file from disk (no last-known-good).
- Ownership change request: a per-feature kill switch readable without
  a restart.

#### E2 Incident: WAF rule takes CPU to 100% everywhere
- Company: Alderwick Edge   Type: incident   Level: L2
- Real-world grounding: Cloudflare 2019-07-02: an XSS rule containing
  `.*(?:.*=.*)` backtracked catastrophically in PCRE; the CPU protection
  had been removed weeks earlier; WAF rules skipped the staged rollout
  by design; ~27 min outage. Fixes: re-add CPU protection, profile every
  rule in tests, move to RE2/Rust regex ("run-time guarantees") —
  [Cloudflare](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/).
- Ticket (the page): "Proxy CPU 100% in all PoPs, 502s everywhere,
  started 4 minutes after a WAF managed-rules push."
- Stack: Lua WAF (legacy) + Rust `regex` crate; flamegraphs.
- Skills: DEBUG, PERF, OBS, COMM
- Size: 6 h → triage + kill switch (45), find the rule with a CPU
  profile (60), port the rule set's hot rules to a linear-time engine
  (90), CI rule-cost check (90), postmortem (60).
- Done-condition: on replay, CPU < 40% and p99 < 20 ms; his CI check
  run on 200 rules (3 planted pathological) flags exactly the 3; the
  postmortem names both the regex and the rollout bypass.
- Pushback hooks: the PM insists security rules must stay instant
  global: he should propose a fast-but-guarded path (CPU budget +
  automatic rollback) instead of the staged path.
- Ownership change request: per-rule CPU-time metrics in production
  sampled at 1%.

#### E3 Maglev hashing for the L4 balancer
- Company: Alderwick Edge   Type: build   Level: L3   *(paper-inspired)*
- Real-world grounding: Google's Maglev (NSDI 2016) spreads packets with
  ECMP and maps each flow with consistent hashing + connection tracking
  to limit disruption on failures; one machine saturates 10 Gbps with
  small packets; the lookup-table construction is §3.4 —
  [Google Research](https://research.google/pubs/pub44824/),
  [summary](https://blog.acolyer.org/2016/03/21/maglev-a-fast-and-reliable-software-network-load-balancer/).
- Idea-bank seed: 06/P05 (bounded-load consistent hashing) for the ownership change — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Our L4 balancer uses `hash % N`, so every backend change
  reshuffles every connection. Implement Maglev table population and
  connection tracking in `l4lb`, and show the paper's balance/disruption
  numbers on our simulator."
- Stack: Rust (the userspace data path; eBPF loading stays as is).
- Skills: NET, DIST, PERF, TEST
- Size: 10 h → read §3 (60), permutation + table population (2×90),
  connection tracking with bounded memory (90), simulator runs (60),
  write-up (30).
- Done-condition: N = 100 backends, M = 65,537 table: max/min backend
  load ≤ 1.05 *(calibrate)*; removing one backend remaps ≤ 1.5× the ideal
  1/N of the table; existing tracked flows keep their backend during
  changes; table rebuild < 50 ms.
- Pushback hooks: the TL asks about weighted backends: the paper only
  hints; he should propose and measure a weighting.
- Ownership change request: bounded-load fallback when one backend is
  hot.

#### E4 Adaptive concurrency limits toward origins
- Company: Alderwick Edge   Type: perf-hunt   Level: L3
- Real-world grounding: Netflix replaced hand-set limits with adaptive
  concurrency limits (gradient: compare long-term RTT to sampled RTT,
  shrink the limit when queueing appears) and open-sourced the library —
  [Netflix](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581),
  [concurrency-limits README](https://github.com/Netflix/concurrency-limits),
  [Gradient2Limit source](https://java-browser.yawk.at/com.netflix.concurrency-limits/concurrency-limits-core/0.3.2/com/netflix/concurrency/limits/limit/Gradient2Limit.java).
- Idea-bank seed: 06/P40 (adaptive concurrency limits from TCP congestion control) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "When one customer's origin slows down, our connection pools
  to it fill, queues grow, and other customers on the same PoP see
  timeouts. Add adaptive per-origin limits and fast shedding."
- Stack: Rust (proxy); toxiproxy slowing one origin 10×.
- Skills: PERF, DIST, NET, OBS
- Size: 9 h → reproduce + measure queueing (90), gradient limiter (90),
  shedding with a 503 + `Retry-After` (60), tuning (90), report (30).
- Done-condition: one origin slowed 10×: other routes' p99 < 1.2× their
  baseline; goodput to the slow origin ≥ 90% of its capacity; in-flight
  queue length bounded; recovery to full rate within 30 s after it heals.
- Pushback hooks: a peer wants a fixed limit of 200 per origin: he must
  show the case where that's both too high and too low.
- Ownership change request: export the live limit per origin as a
  metric and an alert on "limit pinned at minimum".

#### E5 Rate limiting across PoPs
- Company: Alderwick Edge   Type: build   Level: L4
- Real-world grounding: Cloudflare's rate limiter counts per client in
  each PoP and uses a sliding-window approximation (previous window's
  count weighted by overlap: two integers instead of a log) —
  [Cloudflare](https://blog.cloudflare.com/counting-things-a-lot-of-different-things/).
- Ticket: "Enterprise customers want one limit across all PoPs ('1,000
  req/min per API key, globally'). Design and build it: accuracy, cost
  per request, and behaviour under partition are all in the design doc."
- Stack: Rust data path; Go control plane; 3 PoP containers with
  `tc netem` 50 ms between them.
- Skills: DIST, SD, NET, PERF
- Size: 20 h → M1 doc (3 h); M2 local sliding window (3 h); M3 cross-PoP
  sync: gossip deltas or regional aggregator (6 h); M4 partition
  behaviour (4 h); M5 load test (4 h).
- Done-condition: one client spread over 3 PoPs: enforced rate within
  ±10% of the limit; per-request overhead < 1 ms p99; under a PoP
  partition the configured fail-open/fail-closed policy holds and the
  error stays within the doc's stated bound.
- Pushback hooks: the TL proposes a central Redis: he should compute
  the added latency and blast radius.
- Ownership change request: a "dry-run" mode that logs would-be blocks.

#### E6 Incident: an endpoint's DNS record went empty during a game day
- Company: Alderwick Edge   Type: incident   Level: L4
- Real-world grounding: AWS us-east-1, 2025-10-19/20: DynamoDB's DNS
  automation has a Planner and Enactors in 3 AZs; one Enactor stalled, a
  newer plan was applied by another, the stale Enactor then applied its
  old plan and cleanup deleted it, leaving the regional endpoint with an
  empty record set that the automation couldn't repair —
  [AWS summary](https://aws.amazon.com/message/101925/),
  [analysis](https://urandom.io/blog/2026-02-17-the-race-that-ate-us-east-1) (secondary).
- Idea-bank seed: 06/P09 (fencing tokens) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Game day: `api.edge-internal` resolved to nothing for 11 min.
  Our `dnsauto` has the same planner/enactor shape. Find the race, prove
  the fix, and write the postmortem."
- Stack: Go (`dnsauto`); a provided interleaving explorer (Python) or
  `stateright` (Rust) if he prefers.
- Skills: DIST, DEBUG, TEST, COMM
- Size: 8 h → read code + logs (60), reproduce with forced interleaving
  (90), fix with plan-generation fencing + "never empty" invariant in
  cleanup (90), exhaustive interleaving check (90), postmortem (60).
- Done-condition: his regression test reproduces the empty record on the
  old code; the explorer checks all interleavings of 3 enactors × 2 plan
  generations × cleanup with no reachable state where the record set is
  empty or an older plan overwrites a newer one.
- Pushback hooks: the SRE suggests a lock in etcd: he should say what
  happens when the lock holder stalls (the AWS failure mode) and why
  fencing tokens are still needed.
- Ownership change request: an alert on "record set size below N".

#### E7 Design review: global config rollout with a real kill switch
- Company: Alderwick Edge   Type: design-review   Level: L5   *(paper-inspired)*
- Real-world grounding: Facebook's Configerator ("Holistic Configuration
  Management at Facebook", SOSP 2015 `[paper not re-checked this
  session]`) treats config as code with canaries; Cloudflare's 2019 WAF
  rules bypassed staged rollout and Quicksilver spread them in seconds;
  its 2025 remediation list adds global kill switches and treating
  internal files as untrusted —
  [Cloudflare 2019](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/),
  [Cloudflare 2025](https://blog.cloudflare.com/18-november-2025-outage/);
  Fly.io's Corrosion shows how a gossip system can amplify a bad schema
  change ([Fly.io](https://fly.io/blog/corrosion)).
- Idea-bank seed: 06/P48 (sequential testing for canary analysis) for halt signals — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Design the next config-distribution system for the edge:
  every config type staged by default, an emergency path that's fast but
  guarded, automatic halt on bad signals, and a kill switch that works
  when the control plane itself is broken."
- Stack: design doc + rollout policy implemented against
  `tools/fleet-sim` (Go).
- Skills: SD, DIST, OBS, COMM
- Size: 14 h → reading (2 h), doc (4 h), whiteboard with the principal
  (60 min), policy implementation (5 h), revise (2 h).
- Done-condition: rubric (config taxonomy, stages + bake times, halt
  signals, emergency path guard, kill-switch independence, data-plane
  validation); in `fleet-sim`, 3 injected bad configs (crash, CPU spike,
  silent error-rate rise) each halt at ≤ 1% of fleet within 2 min of
  simulated time; the emergency path reaches 100% in < 60 s and still
  auto-rolls-back a CPU-spiking rule.
- Pushback hooks: the PM wants "instant" for all security configs; the
  SRE wants 24 h bake for everything. He has to land a policy both sign.
- Ownership change request: none; the doc becomes next quarter's
  roadmap item.

#### E8 Cache: stale-while-revalidate + request collapsing
- Company: Alderwick Edge   Type: add-your-part   Level: L2
- Real-world grounding: RFC 5861 (`stale-while-revalidate`,
  `stale-if-error`); Cloudflare moved its cache onto a Pingora-based
  proxy in 2026 citing fewer misses and closer adherence to HTTP caching
  standards —
  [Cloudflare changelog, May 2026](https://developers.cloudflare.com/changelog/post/2026-05-04-pingora-powers-cache/index.md).
- Idea-bank seed: 06/P02 (coalescing + XFetch) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "The cache module (Ilse's, ADR 0031) handles freshness but
  every expired hot object stampedes the origin. Add a cache lock for
  request collapsing and RFC 5861 support."
- Stack: Rust.
- Skills: NET, PERF, DIST, TEST
- Size: 7 h → read ADR + module (60), cache lock with timeout (90),
  `stale-while-revalidate` background refresh (90), `stale-if-error`
  (45), tests (60).
- Done-condition: 10,000 concurrent requests for an expired hot key →
  exactly 1 origin fetch; RFC 5861 test vectors pass; no request waits
  longer than the 2 s lock timeout (falls through to origin).
- Pushback hooks: ADR 0031 keys the lock by URL only: he should spot
  `Vary` headers.
- Ownership change request: a `cache_lock_wait_seconds` histogram.

### 2.7 Saggarworks — remote build cache, CI and artifact registry for polyglot monorepos

- **Niche / domain:** developer platforms: build caching/execution,
  CI, merge queues, package and artifact registries.   **Stage:** growth
  (Series C, ~250 people, ~110 eng).
- **Culture:** "our CI builds our CI": they dogfood everything, so a
  slow build is a P1 for the people who own it. Metrics on the wall: CI
  p50, cache hit rate, main-branch green rate. Reviews are fast but
  strict on compatibility (customers' build files depend on every flag).
  Design docs for anything cross-team; "papercut Fridays" for DX fixes.
  The manager is a former build engineer at a big monorepo shop who
  asks "what does this do to cache hit rate?"
- **Stack (and why):** Go for the registry, CI orchestrator and the
  Bazel Remote Execution API (REAPI) server (`bazel-remote` and
  Buildbarn-style servers are Go); Rust for the chunking/dedup engine
  (throughput-bound, Hugging Face's Xet is Rust `[unverified]`); gRPC;
  Postgres metadata; object storage (MinIO in dev); Python + DuckDB for
  CI analytics (flaky tests, test selection).
- **Team roster:** EM (Build & Cache); staff engineer (REAPI/CAS);
  senior engineers (CI orchestrator, registry); PM (developer
  experience); data engineer (CI analytics); junior engineer; security
  engineer (supply chain).
- **Main codebase:** `saggarworks/`: `registry/` (npm-, PyPI- and
  cargo-compatible endpoints), `cas/` (Rust chunk store), `reapi/` (Go),
  `ci/` (orchestrator, merge queue), `analytics/` (Python, DuckDB CI
  warehouse), `deploy/compose.yml`.
- **In-house tools:** CI history warehouse; flaky-test detector;
  cache-hit auditor (re-execute and diff); merge-queue simulator that
  replays commit history; dependency-resolver benchmark; registry
  security scanner.
- **Inspired by:** Uber SubmitQueue, GitHub merge queue and Project
  Cyclops, Slack flaky tests, Bazel remote caching, Hugging Face Xet,
  crates.io sparse index, Meta predictive test selection, PyPI/PEP 706.

#### K1 Review: package upload endpoint
- Company: Saggarworks   Type: review-to-own   Level: L1
- Real-world grounding: Python's `tarfile` path traversal
  (CVE-2007-4559) was still exploitable across hundreds of thousands of
  repos in 2022 and led to extraction filters in PEP 706 —
  [PEP 706](https://peps.python.org/pep-0706/); registries treat
  published versions as immutable (yank, never overwrite) —
  [crates.io sparse index RFC 2789](https://rust-lang.github.io/rfcs/2789-sparse-index.html)
  (context on index consistency) `[URLs from memory, not re-checked]`.
- Ticket: "Wes's PR adds `PUT /api/v1/packages/{name}/{version}` for
  the PyPI-compatible registry: it unpacks the sdist to read metadata,
  stores the blob, updates the index. Security wants a second pair of
  eyes; you'll own the endpoint."
- Stack: Go.
- Skills: SEC, API, DB, READ, TEST
- Size: 5 h → read + run (60), review + quiz (60), voice walk-through
  of an upload (30), fixes (90), ownership change (60).
- Done-condition: harness security suite (traversal, symlink, zip-bomb,
  oversized chunked upload) and a concurrent-publish test (two versions
  at once, 500 trials, no lost index entry) pass; ≥ 4 of 5 bugs found.
- Planted bugs: tar members with `../` extracted while reading
  metadata; hash checked after the blob is written to its final,
  servable path; re-publishing an existing version overwrites it; size
  limit enforced only from `Content-Length` (chunked upload bypass);
  index update is read-modify-write without a lock or CAS.
- Ownership change request: `yank` with a reason, visible to resolvers
  but never deleting the blob.

#### K2 Sparse HTTP index for the cargo-compatible registry
- Company: Saggarworks   Type: add-your-part   Level: L2
- Real-world grounding: crates.io moved from cloning a git index to a
  sparse HTTP protocol (one file per crate, cached via HTTP semantics),
  RFC 2789 —
  [RFC](https://rust-lang.github.io/rfcs/2789-sparse-index.html)
  `[from memory, not re-checked]`.
- Ticket: "Customers' CI clones our git index on every job: 90 s and
  climbing. Storage and the publish path exist (ADR 0012). Add the
  sparse index: per-crate files, ETag/`If-None-Match`, CDN-friendly
  cache headers, and never serve an index line before its `.crate`
  exists."
- Stack: Go.
- Skills: API, NET, DIST, PERF
- Size: 7 h → read RFC + ADR (60), file generation on publish (90),
  conditional GETs (60), publish ordering (blob → index) (60), tests
  (60).
- Done-condition: the harness resolver resolves a 500-package graph
  with requests ≤ the number of packages in it; a second resolve gets
  all 304s; a publish is visible within 5 s; under 50 concurrent
  publishes no resolver ever sees an index line whose artifact 404s.
- Pushback hooks: ADR 0012 regenerates the whole index on every
  publish: he should measure it at 100k crates.
- Ownership change request: an `index-config` endpoint with auth
  requirements for private registries.

#### K3 Content-defined chunking for the artifact store
- Company: Saggarworks   Type: perf-hunt   Level: L3   *(paper-inspired)*
- Real-world grounding: Hugging Face's Xet splits files into ~64 KB
  content-defined chunks (8–128 KB) found by a rolling hash so an edit
  in the middle keeps neighbouring chunks, then dedups globally —
  [HF docs](https://huggingface.co/docs/hub/xet/deduplication),
  [explainer, 2026](https://00f.net/2026/01/19/xet-intro-1/);
  FastCDC (USENIX ATC 2016) is the fast gear-hash CDC most systems use
  ([USENIX](https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia)
  `[URL from memory]`).
- Ticket: "Artifact storage grew 4× this year; most uploads are a new
  version of something we already have. `cas/` uses fixed 4 MB blocks.
  Switch to FastCDC and show storage and upload savings on real release
  histories."
- Stack: Rust.
- Skills: PERF, DB (dedup indexes), OS (I/O, memory), TEST
- Size: 10 h → read FastCDC (60), gear-hash chunker with normalized
  chunking (2×90), dedup index (90), benchmark on the corpus (90),
  write-up (30).
- Done-condition: corpus = 20 consecutive versions of 3 open-source
  release tarballs + 10 versions of a binary blob set. Pass = stored
  bytes ≤ 0.5× the fixed-block store *(calibrate)*; inserting 1 byte at
  a random offset changes ≤ 3 chunks; chunker ≥ 1 GB/s per core
  *(calibrate)*; chunk sizes within 8–128 KB with mean 64 KB ± 10%.
- Pushback hooks: the staff engineer wants SHA-256 per chunk "for
  safety" on the hot path: he should measure it vs BLAKE3 and decide.
- Ownership change request: a `cas stats` command showing dedup ratio
  per repository.

#### K4 Incident: the binary built green, then crashed in production
- Company: Saggarworks   Type: incident   Level: L3
- Real-world grounding: Bazel's docs: missing remote cache hits come
  from "something non-hermetic in the build causing the actions to
  receive different action keys"; diagnose by comparing execution logs
  of two runs. The dangerous twin is a key that *doesn't* change when
  the output does (cache poisoning) —
  [Bazel](https://bazel.build/remote/cache-remote),
  [community book on cache diagnostics](https://bazel.virtuslab.com/book/5~5~3/) (secondary).
- Ticket (the page): "Customer's release binary segfaults on start.
  Rebuilt with `--noremote_accept_cached` it's fine. Our cache served
  them someone else's output."
- Setup: an action reads a host compiler path not declared as an input;
  a developer machine with a different compiler uploaded to the shared
  cache.
- Stack: Go REAPI server, Bazel client, Python for log diffing.
- Skills: DEBUG, TEST, SEC (trust boundaries), COMM
- Size: 7 h → reproduce (60), diff execution logs (90), fix the key and
  purge (60), build an auditor that re-executes 1% of cache hits and
  diffs outputs (2×60), postmortem (60).
- Done-condition: the poisoned action identified in the postmortem's
  structured field; purge removes exactly the poisoned entries; the
  harness plants a second, different poisoning and his auditor flags it
  within 200 sampled hits with zero false positives over 2,000 clean
  hits.
- Pushback hooks: the PM wants "only CI may write to the cache": he
  should agree and explain why it's necessary but not sufficient.
- Ownership change request: write-permission scoping per cache
  namespace.

#### K5 Speculative merge queue
- Company: Saggarworks   Type: build   Level: L4   *(paper-inspired)*
- Real-world grounding: Uber's SubmitQueue keeps main green by
  speculating on which pending changes will pass and cancelling builds
  predicted to lose; a 2025 follow-up reports ~53% less CI resource use
  and 37% lower P95 wait —
  [Uber blog](https://www.uber.com/us/en/blog/slashing-ci-costs-at-uber/),
  [arXiv 2501.03440](https://arxiv.org/abs/2501.03440);
  GitHub's merge queue tests base + queued PRs on a temporary branch
  ([GitHub, 2024](https://github.blog/engineering/engineering-principles/how-github-uses-merge-queue-to-ship-hundreds-of-changes-every-day)).
- Ticket: "Our customers' merge queue is FIFO batches: one bad PR
  resets everything. Build speculative execution with a success model
  learned from history. Graded on our replay simulator."
- Stack: Go (queue policy) + Python (success model) against the
  provided simulator.
- Skills: SD, DIST, PERF, ML (light), TEST
- Size: 26 h → M1 papers + doc (4 h); M2 speculation tree (6 h);
  M3 success model from history (5 h); M4 cancellation + budget (5 h);
  M5 tuning on replay (4 h); demo (2 h).
- Done-condition: replay of 2,000 changes (8% would break main, with
  planted conflict pairs): main is never red; median time-to-merge ≤ 0.4×
  serial *(calibrate)*; CI machine-hours ≤ 1.5× serial.
- Pushback hooks: the EM wants unlimited speculation depth: he must
  plot the cost curve.
- Ownership change request: priority lane for hotfixes that can't
  starve the queue.

#### K6 Flaky-test detection and auto-quarantine
- Company: Saggarworks   Type: experiment   Level: L3
- Real-world grounding: Slack's mobile main branch hovered around a 20%
  pass rate; automatic flaky detection + suppression took test-job
  failures from 57% to < 5% —
  [Slack](https://slack.engineering/handling-flaky-tests-at-scale-auto-detection-suppression).
- Ticket: "Customers keep asking for 'Slack-style' flaky handling. The
  CI warehouse has every test result for 30 days. Build detection +
  quarantine policy; show it on a held-out month."
- Stack: Python + DuckDB.
- Skills: DATA, TEST, OBS, ML (light)
- Size: 10 h → explore the warehouse (90), features (retry-pass,
  same-commit disagreement, timing variance) (90), policy +
  un-quarantine rule (90), evaluate on held-out (60), write-up (30).
- Done-condition: held-out month with 40 planted flaky tests (flake
  rates 1–30%) and 15 truly broken tests: flaky precision ≥ 0.9, recall
  ≥ 0.8; zero broken tests quarantined; replayed main pass rate ≥ 95%.
- Pushback hooks: a peer wants "quarantine anything that failed twice":
  he must show it hides the broken tests.
- Ownership change request: auto-file an issue to the test's owner
  with the evidence.

#### K7 Predictive test selection
- Company: Saggarworks   Type: experiment   Level: L4   *(paper-inspired)*
- Real-world grounding: Meta's "Predictive Test Selection"
  (Machalica et al., ICSE-SEIP 2019) learned which tests to run per
  change, reporting that it caught almost all faulty changes while
  running about a third of transitively affected tests
  ([arXiv 1810.05286](https://arxiv.org/abs/1810.05286)
  `[ID and numbers from memory, not re-checked]`); Uber's 2025 CI work
  shows the same cost pressure
  ([arXiv 2501.03440](https://arxiv.org/abs/2501.03440)).
- Ticket: "Pre-merge CI runs every affected test: 38 min p50. Build a
  selector that runs fewer tests and still catches failing changes.
  Offline evaluation first, on our history."
- Stack: Python (gradient-boosted model, DuckDB features).
- Skills: ML, DATA, PERF, TEST
- Size: 16 h → paper (90), features: file-test history, distance,
  churn (3 h), model + calibration (3 h), selection policy at a budget
  (3 h), held-out evaluation + report (3 h).
- Done-condition: on a held-out month, catch ≥ 95% of failing changes
  (≥ 1 failing test selected) while running ≤ 30% of tests
  *(calibrate)*; deterministic rerun of the evaluation.
- Pushback hooks: the security engineer asks what happens to tests that
  never fail (they never get selected): he needs an exploration rule.
- Ownership change request: shadow mode that logs what would have been
  skipped.

#### K8 Design review: multi-region artifact registry
- Company: Saggarworks   Type: design-review   Level: L5
- Real-world grounding: registries need immutable versions, an index
  that never points at missing blobs (RFC 2789's ordering), and fast
  reads worldwide; GitHub's Project Cyclops shows the monorepo Git side
  of the same scale pressure —
  [GitHub](https://github.blog/engineering/engineering-principles/improving-large-monorepo-performance-on-github/).
- Ticket: "Two customers need an EU region with failover. Whiteboard
  the registry across regions: where publishes are ordered, how the
  index and blobs replicate, read-after-publish guarantees, yanks, CDN
  purges, and region failure mid-publish."
- Stack: design doc + a policy implemented in the provided registry
  simulator (Go).
- Skills: SD, DIST, DB, SEC, COMM
- Size: 12 h → reading (90), doc (4 h), whiteboard (60), simulator
  policy (4 h), revise (60).
- Done-condition: rubric (single writer per package name or
  conflict rule, replication order, failover, yank propagation,
  signatures/provenance); simulator scenarios: region failover during
  publish never produces an index entry without its blob; a
  read-after-publish in the same region always succeeds; the stated
  cross-region visibility bound holds in 1,000 randomized runs.
- Pushback hooks: the PM wants active-active publishes for latency: he
  should produce the conflicting-version scenario.
- Ownership change request: none; it feeds next quarter's plan.

#### K9 Transparency log for published artifacts
- Company: Saggarworks   Type: add-your-part   Level: L3   *(blog-inspired)*
- Real-world grounding: Russ Cox's "Transparent Logs for Skeptical
  Clients" (the design behind Go's checksum database, RFC 6962 hashing):
  Merkle-tree logs give inclusion and consistency proofs of ~lg N hashes,
  and tiling makes proofs cacheable —
  [research.swtch.com/tlog](https://research.swtch.com/tlog).
- Idea-bank seed: 06/P20 (transparency log) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "A customer's security team asks how they'd know if we ever
  served different bytes for the same published version. The publish
  path exists (K1, K2). Add an append-only Merkle log of (name, version,
  digest), signed tree heads, inclusion and consistency proofs, and a
  verifier CLI customers can run in CI."
- Stack: Go (the registry's language; `golang.org/x/mod/sumdb/tlog` is
  allowed as reading, not as the implementation).
- Skills: SEC, API, DB, TEST
- Size: 9 h → Cox's post + RFC 6962 rules (90), tree + tile storage
  (90), proofs (90), signing + verifier CLI (90), tests (60).
- Done-condition: harness tampers with history (edit, delete, reorder,
  and a fork that shows two clients different trees): the verifier flags
  100%; proofs for 1M records ≤ 20 hashes; RFC 6962 leaf/node-prefix test
  vectors pass; publish p99 rises ≤ 10 ms *(calibrate)*.
- Pushback hooks: a peer wants to store the tree as Postgres rows and
  recompute hashes on read: he should measure proof latency at 1M
  entries.
- Ownership change request: a "monitor" mode where two verifiers
  exchange tree heads to detect a fork.

### 2.8 Pawl Labs — durable workflows as a library: your code, your Postgres, no orchestration server

- **Niche / domain:** workflow orchestration / durable execution, job
  queues, timers.   **Stage:** seed (6 people, $3.5M, open-source core).
- **Culture:** founder-led by two ex-database researchers. "Write down
  exactly what is exactly-once" is the house rule: every guarantee has a
  doc page and a test. Weekly releases; the community Discord drives
  priorities; docs and DX matter as much as the engine. The CTO (his
  boss) asks for the invariant before the code and will happily spend a
  whiteboard session on one edge case.
- **Stack (and why):** Python SDK (the customer surface: `@workflow`,
  `@step` decorators, like DBOS), Go daemon `pawld` for scheduling,
  timers and the admin API (Temporal and Inngest servers are Go),
  Postgres only (DBOS's whole pitch:
  [DBOS](https://dbos.dev/blog/postgres-is-all-you-need-for-durable-execution)).
- **Team roster:** CEO (DX + sales); CTO (tech lead); 2 engineers
  (server, Python SDK); developer advocate; junior engineer; contractor
  on the TypeScript SDK.
- **Main codebase:** `pawl/`: `pawld/` (Go: scheduler, timers, queues,
  admin API), `sdk-python/` (decorators, replay engine), `sdk-ts/`,
  `migrations/`, `bench/` (steps/s, latency), `chaos/` (kill workers,
  kill Postgres, pause network), `compose.yml`.
- **In-house tools:** history replayer; workflow-history diff viewer;
  queue-bloat monitor; chaos harness; fairness simulator; timer-drift
  checker.
- **Inspired by:** DBOS, Temporal, Restate, Inngest, River, Netflix
  Maestro, Brandur Leach's Postgres queue writing.

#### P1 Review: `SKIP LOCKED` task dequeue
- Company: Pawl Labs   Type: review-to-own   Level: L1
- Real-world grounding: Postgres-backed queues dequeue with
  `FOR UPDATE SKIP LOCKED`; River (Go) and DBOS build on it; the classic
  pitfalls are lost visibility timeouts and unindexed scans —
  [River](https://github.com/riverqueue/river),
  [Brandur on Postgres queues](https://brandur.org/postgres-queues).
- Ticket: "Ana's PR replaces our `LISTEN/NOTIFY` polling hack with a
  proper `SKIP LOCKED` dequeue, leases and heartbeats. Review it; you
  own the queue after."
- Stack: Go + Postgres.
- Skills: DB, OS (concurrency), DIST, READ, TEST
- Size: 5 h → read + run (60), review + quiz (60), voice walk-through
  of a task's lease life (30), fixes (90), ownership change (60).
- Done-condition: 10,000 tasks, 32 workers, 20 random worker kills.
  Pass = zero tasks executed twice concurrently (side-effect ledger),
  zero lost tasks, dequeue p99 < 10 ms *(calibrate)*, ≥ 4 of 5 bugs
  found.
- Planted bugs: no `ORDER BY` → old tasks starve; lease not extended by
  the heartbeat (long tasks run twice); completion `UPDATE` doesn't
  check the lease owner (a zombie worker overwrites); missing partial
  index on `(queue, run_at) WHERE state = 'ready'`; retry backoff
  computed with no cap.
- Ownership change request: per-queue max concurrency enforced in SQL.

#### P2 Incident: dequeue latency 100× during month-end reporting
- Company: Pawl Labs   Type: incident   Level: L2
- Real-world grounding: Brandur's "Postgres Job Queues & Failure By
  MVCC": a long-running transaction elsewhere keeps dead queue rows
  visible to vacuum's horizon, so every dequeue scans more dead tuples
  and the queue degrades —
  [Brandur](https://brandur.org/postgres-queues) `[URL from memory]`.
- Ticket (customer report): "Workflows stall for minutes every month
  end. Our analytics team runs reports on the same database. Pawl's
  fault?"
- Setup: compose with a 30-minute `REPEATABLE READ` reporting
  transaction and a steady 500 tasks/s.
- Stack: Postgres, `pg_stat_activity`, `pg_stat_user_tables`.
- Skills: DB, OBS, DEBUG, COMM
- Size: 5 h → reproduce + measure dead tuples (60), find the horizon
  holder (45), fix options: move reporting to a replica, statement
  timeouts, partitioned queue table with drop/truncate rotation (2×60),
  customer-facing postmortem (60).
- Done-condition: with the 30-min reporting transaction running,
  dequeue p99 < 10 ms and dead tuples in the active partition stay
  < 100k; the customer write-up explains MVCC in two paragraphs a
  non-DBA understands (rubric).
- Pushback hooks: the CEO wants "a doc page that says don't run long
  transactions": he should argue for an engine-side fix too.
- Ownership change request: a `pawl doctor` check that warns when
  `backend_xmin` age > 5 min.

#### P3 Non-determinism detector for the Python SDK
- Company: Pawl Labs   Type: add-your-part   Level: L3
- Real-world grounding: durable execution replays recorded history;
  if new code issues a different command than the history, replay fails
  ("non-determinism error"); Temporal teams replay captured production
  histories in CI to catch this —
  [Bitovi](https://bitovi.com/blog/replay-testing-to-avoid-non-determinism-in-temporal-workflows),
  [Keith Tenzer](https://keithtenzer.com/temporal/Altering_Space-Time_Continuum_Testing_for_Determinism/).
- Ticket: "Users deploy a code change and their in-flight workflows
  wedge. The replay engine exists (ADR 0005). Add `pawl replay-check`:
  run new code against stored histories and report incompatible
  changes, with the line that caused them."
- Stack: Python.
- Skills: DIST, TEST, API, READ
- Size: 9 h → read replay engine (90), command-stream comparison (90),
  source attribution (90), CLI + CI recipe (60), tests (60).
- Done-condition: harness gives 40 workflow version pairs (20
  compatible, e.g. added logging or a new step behind a version gate;
  20 breaking, e.g. reordered steps, `random()`/`time.time()` in workflow
  code, changed step names). Pass = ≥ 38/40 classified correctly, and
  for breaking pairs the reported line is right in ≥ 18/20.
- Pushback hooks: ADR 0005 treats changed step *arguments* as
  breaking: he should ask whether that's right for idempotent steps.
- Ownership change request: a `pawl.patched("name")` version-gate API.

#### P4 Durable timers on a hierarchical timing wheel
- Company: Pawl Labs   Type: build   Level: L3   *(paper-inspired)*
- Real-world grounding: Varghese & Lauck, "Hashed and Hierarchical
  Timing Wheels" (SOSP 1987): O(1) start/stop timers using wheels of
  increasing granularity; used in kernels and Kafka's purgatory
  `[classic; URLs not re-checked]`. Customers' workflows `sleep()` for
  days, so timers must be durable and cheap.
- Ticket: "`sleep(timedelta(days=30))` is a row polled every second by
  every `pawld`. At 10M sleeping workflows Postgres CPU is 60% idle-poll.
  Build a timer service: in-memory hierarchical wheel for the near
  future, Postgres for the far future, crash-safe hand-off."
- Stack: Go (`pawld`).
- Skills: OS (timers, memory), DB, PERF, DIST
- Size: 12 h → paper (60), wheel (2×90), far-future loading by time
  bucket (90), crash recovery (90), benchmark (60).
- Done-condition: 10M timers spread over 30 days (+ a burst of 1M due
  in the same second): fire lateness p99 < 100 ms; zero lost or
  duplicate fires across 20 `pawld` kills; Postgres polling queries
  ≤ 1 per second per node; RSS < 1 GB *(calibrate)*.
- Pushback hooks: the CTO asks what happens if two `pawld` nodes both
  load the same bucket: he needs ownership/fencing.
- Ownership change request: timer cancellation API with O(1) removal.

#### P5 Group commit for step checkpoints
- Company: Pawl Labs   Type: perf-hunt   Level: L3
- Real-world grounding: DBOS checkpoints every workflow step into
  Postgres; the commit (WAL flush) per step bounds throughput —
  [DBOS architecture](https://docs.dbos.dev/architecture),
  [DBOS blog](https://www.dbos.dev/blog/why-postgres-durable-execution);
  Postgres offers `commit_delay` / `synchronous_commit` trade-offs
  `[docs, not re-checked]`.
- Ticket: "Benchmarks show 1,900 steps/s on a box where Postgres can do
  far more. Every step is its own transaction + fsync. Raise throughput
  without weakening the guarantee that an acknowledged step survives a
  crash."
- Stack: Python SDK + Postgres (and the Go daemon if he moves batching
  there).
- Skills: PERF, DB, OS (fsync), DIST
- Size: 8 h → profile (90), batch checkpoints across concurrent
  workflows (2×90), measure with `kill -9` of Postgres (60), write-up
  (30).
- Done-condition: steps/s ≥ 3× baseline *(calibrate)*; 50 Postgres
  container kills during the benchmark lose zero acknowledged steps;
  p99 step latency ≤ 2× baseline.
- Pushback hooks: a contributor's PR sets `synchronous_commit = off`:
  he must explain why that's a different guarantee and say no politely.
- Ownership change request: expose the batch size as an adaptive
  setting with a metric.

#### P6 Fair multi-tenant scheduling
- Company: Pawl Labs   Type: build   Level: L4
- Real-world grounding: in a shared queue a high-volume tenant starves
  the rest; Inngest built per-function virtual queues and per-key
  concurrency limits for fairness —
  [Inngest, noisy neighbours](https://www.inngest.com/blog/fixing-multi-tenant-queueing-concurrency-problems),
  [Inngest, fair queue](https://inngest.com/blog/building-the-inngest-queue-pt-i-fairness-multi-tenancy).
- Idea-bank seed: 06/P43 (Dominant Resource Fairness), 06/P44 (Karma credits) as alternatives to weigh in the doc — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Pawl Cloud beta: one customer enqueued 1M tasks and 40 other
  tenants waited an hour. Build fair scheduling across tenants with
  per-key concurrency limits, in Postgres, without a global lock."
- Stack: Go (`pawld`) + Postgres.
- Skills: SD, DB, DIST, PERF
- Size: 22 h → M1 doc (3 h); M2 per-tenant virtual queues (6 h);
  M3 weighted round robin / deficit scheduling across tenants (5 h);
  M4 per-key concurrency limits (4 h); M5 fairness simulator + tuning
  (4 h).
- Done-condition: noisy tenant enqueues 1M; 40 small tenants keep
  normal load: their queue-wait p99 < 2 s; total throughput ≥ 90% of
  single-tenant max *(calibrate)*; per-key limits never exceeded (audit
  log).
- Pushback hooks: the CEO wants paying tenants to always go first: he
  should show starvation and propose weights.
- Ownership change request: a per-tenant "queue depth and wait" panel.

#### P7 Design review: move the journal off Postgres?
- Company: Pawl Labs   Type: design-review   Level: L5   *(paper-inspired)*
- Real-world grounding: Restate replaced "a database" with its own
  replicated log, Bifrost: one sequencer per partition, commit on quorum
  ack, virtual consensus based on Flexible Paxos —
  [Restate docs](https://docs.restate.dev/references/architecture),
  [Restate blog](https://restate.dev/blog/the-anatomy-of-a-durable-execution-stack-from-first-principles/),
  [Thoughtworks Radar](https://www.thoughtworks.com/en-gb/radar/platforms/restate);
  Flexible Paxos (Howard, Malkhi, Spiegelman 2016) shows only
  leader-election and replication quorums need to intersect
  ([arXiv 1608.06696](https://arxiv.org/abs/1608.06696) `[ID from memory]`);
  DBOS argues the opposite: Postgres is all you need.
- Idea-bank seed: 06/P18 (protocol-aware recovery) for the recovery section — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Pawl Cloud's largest tenant needs 50k steps/s. The CTO wants
  a real debate: keep Postgres (and how far it goes), or build a
  replicated log. Bring numbers, a design, and a failure analysis."
- Stack: design doc + a Python model of his quorum/recovery protocol
  run by the harness's fault explorer.
- Skills: SD, DIST, DB, COMM
- Size: 14 h → reading (3 h), Postgres ceiling estimate with `bench/`
  (2 h), doc (4 h), whiteboard with the CTO (60 min), model (3 h),
  revise (60 min).
- Done-condition: rubric (Postgres ceiling with data, log design,
  quorum choice, recovery, snapshotting, migration, ops cost, "what we
  give up"); his model passes 500 fault schedules (crashes, partitions,
  message loss) with no lost acknowledged entry; mutation check: with
  non-intersecting quorums the model must fail.
- Pushback hooks: the CTO plays DBOS's side hard ("one less system to
  run"); he should concede where it's right.
- Ownership change request: none; the decision record goes in `adr/`.

#### P8 Retries with backoff, jitter and a retry budget
- Company: Pawl Labs   Type: add-your-part   Level: L2
- Real-world grounding: AWS Builders' Library, "Timeouts, retries, and
  backoff with jitter" ([AWS](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
  `[URL from memory]`), Brooker's
  [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
  and [retry token buckets](https://brooker.co.za/blog/2022/02/28/retries.html);
  Metastable Failures in the Wild (OSDI 2022) names retries as a main
  amplifier ([USENIX](https://www.usenix.org/conference/osdi22/presentation/huang-lexiang));
  Slack's 2-22-22 outage shows retries keeping a system in overload ([Slack](https://slack.engineering/slacks-incident-on-2-22-22/)).
- Idea-bank seed: 06/P06 (retry budgets vs. metastable failure) — see [`06-paper-idea-bank.md`](06-paper-idea-bank.md).
- Ticket: "Steps retry immediately and forever by default; a customer's
  flaky API got hammered. The step runner exists; add a retry policy API
  (max attempts, exponential backoff, full jitter, non-retryable errors)
  and a per-workflow retry budget."
- Stack: Python SDK.
- Skills: API, DIST, TEST
- Size: 6 h → read the runner (45), policy API + defaults (90),
  budget (60), tests with a fake clock (60), docs page (45).
- Done-condition: harness's flaky dependency fails 30% of calls; with
  default policy, call amplification ≤ 1.5× and no more than 10% of
  retries land in the same 100 ms window (jitter works); non-retryable
  errors are never retried; all tests run on a fake clock in < 5 s.
- Pushback hooks: the SDK engineer wants retries on by default for all
  exceptions: he should ask about non-idempotent steps.
- Ownership change request: per-exception-type policies.

## 3. Real OSS repos with workable issues

For a later "real upstream issue" task type. Counts are open issues
carrying the label, from the GitHub search API on **2026-10-19**
(they change daily; re-query before assigning). Example issues are real
open issues seen that day. "Pairs with" = the catalog card that teaches
the background first.

| # | Repo (lang) | Niche | Label: open count | Why it suits him | Example open issues (2026-10-19) | Pairs with |
|---|---|---|---|---|---|---|
| 1 | [apache/datafusion](https://github.com/apache/datafusion) (Rust) | query engine | `good first issue`: 29, `help wanted`: 31 | Very active, mentors newcomers, small refactors and benchmark fixes land in days | #26297 gcd benchmarks pass `number_rows: 0`; #26307 dedupe bucket computation in `width_bucket` | D1, D4 |
| 2 | [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse) (C++) | columnar DB / observability | `easy task`: 68, `help wanted`: 49 | Huge label pool; C++ systems code with strong CI; real users | #115318 Parquet ALP encoding; #123272 enable `kill_throw_if_noop` by default | G5, D4 |
| 3 | [risingwavelabs/risingwave](https://github.com/risingwavelabs/risingwave) (Rust) | streaming DB | `good first issue`: 50, `D-easy`: 9 | Streaming state + CDC bugs; some "good first" issues are real correctness bugs | #27060 SQL UDF inflates streaming state ~33×; #25828 SQL Server CDC silent data loss | F4, G6 |
| 4 | [GreptimeTeam/greptimedb](https://github.com/GreptimeTeam/greptimedb) (Rust) | time-series DB on object storage | `good first issue`: 15, `help wanted`: 11 | Closest real analogue of SiltDB; ingestion/TTL bugs are scoped and testable | #8951 metric engine ignores TTL on a logical table; #9185 auto-created tables miss columns | D5, G4 |
| 5 | [grafana/mimir](https://github.com/grafana/mimir) (Go) | metrics backend | `good first issue`: 21, `help wanted`: 14 | Go, Kafka ingest path, per-tenant limits: exactly G4's world; also a `not-as-easy-as-it-looks` label (honest) | #14271 compression before sending to Kafka; #15917 `kafkatool` flag bug | G4, G2 |
| 6 | [open-telemetry/opentelemetry-collector-contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib) (Go) | telemetry pipeline | `good first issue`: 13, `help wanted`: 25 (+ `first-time contributor`) | Component-per-directory structure keeps changes local; codeowners respond | #51845 configurable decompressed batch limit in the Kafka receiver; #51889 document filter-processor metrics | G1 |
| 7 | [vectordotdev/vector](https://github.com/vectordotdev/vector) (Rust) | observability pipeline | `good first issue`: 23 | Rust data pipeline, clean contribution guide; issues range from lint cleanup to new transforms | #23659 eliminate `allow` statements; #22069 more EC2 metadata categories | G1, G3 |
| 8 | [tikv/tikv](https://github.com/tikv/tikv) (Rust) | distributed KV (Raft) | `difficulty/easy`: 51, `help wanted`: 95 | Raft + RocksDB engine; easy issues are old, so ask before starting | #13574 arch detection via `uname -m`; #9942 gRPC DNS timeout for all clients | D2, F7 |
| 9 | [cockroachdb/cockroach](https://github.com/cockroachdb/cockroach) (Go) | distributed SQL | `good first issue`: 6 | Meta-issue #49203 holds many small geospatial builtins; great for reading a huge codebase | #49203 geo builtins meta-issue; #65659 verbose drain logging | G8 (admission control reading) |
| 10 | [temporalio/temporal](https://github.com/temporalio/temporal) (Go) | durable execution | `good first issue`: 6 | The reference durable-execution server; issues touch history/reset logic | #1338 reset-point logic in the service; #607 tests for parent-close policy | P3, P1 |
| 11 | [restatedev/restate](https://github.com/restatedev/restate) (Rust) | durable execution, own log | `good first issue`: 4 | Small team, Rust, the Bifrost log behind P7 | #3615 snapshot config not updated on reload; #3872 universal `--output` in CLI | P7 |
| 12 | [neondatabase/neon](https://github.com/neondatabase/neon) (Rust + C) | Postgres storage/compute split | `m/good_first_issue`: 6 | Pageserver/safekeeper code is the best real WAL-replication codebase to read; **activity has slowed (last push 2026-08-31)**, check before investing | #9758 expose `commit_lsn` and per-safekeeper `flush_lsn`; #6452 JWT auth in python tests | D6, T4 |
| 13 | [slatedb/slatedb](https://github.com/slatedb/slatedb) (Rust) | LSM on object storage | `good first issue`: 1, `help wanted`: 2 | Small, readable LSM on S3; maintainers discuss design in issues | #163 more flexible bloom filter sizes (D2/D3 directly); #293 developer quick-start guide | D2, D3, D7 |
| 14 | [openfga/openfga](https://github.com/openfga/openfga) (Go) | Zanzibar-style authz | `good first issue`: 11, `help wanted`: 5 | Real Zanzibar implementation in Go; scoped cleanup + validation issues | #1528 remove panics in the codebase; #1874 missing server config validation | S7 |
| 15 | [cloudflare/pingora](https://github.com/cloudflare/pingora) (Rust) | proxy framework | `help wanted`: 10, `good first issue`: 1 | The framework behind E-cards; issues are feature-sized, need design discussion first | #841 SSE body not flushed on macOS; #780 early request-body access for upstream selection | E1, E4, E8 |
| 16 | [apache/arrow-rs](https://github.com/apache/arrow-rs) (Rust) | columnar formats | `good first issue`: 6, `help wanted`: 10 | Mechanical refactors + test work, high review quality, Parquet internals | #11033 split cast tests into a suite; #9921 improve Parquet `ArrayReaderBuilder` tests | D4, D7 |
| 17 | [etcd-io/etcd](https://github.com/etcd-io/etcd) (Go) | consensus / config store | `help wanted`: 18 (`good first issue`: 0 today) | Robustness-testing issues teach Jepsen-style thinking | #20623 more Kubernetes-traffic ops in robustness tests; #21032 classify etcdserver exit codes | T7, E6 |
| 18 | [valkey-io/valkey](https://github.com/valkey-io/valkey) (C) | in-memory cache/KV | `help wanted`: 11 | C systems code (OS skills: event loop, memory, replication); bigger items | #2621 improve active expiration job (hash-field expiry); #2767 full sync from replica | D7, S3 |
| 19 | [tigerbeetle/tigerbeetle](https://github.com/tigerbeetle/tigerbeetle) (Zig) | financial ledger DB | `good first issue`: 2 | Reading-only value is huge (VOPR, ledger design); the 2 open issues are REPL UX | #1185 REPL eager parser errors; #1183 REPL history | T5, T7 |
| 20 | [superfly/corrosion](https://github.com/superfly/corrosion) (Rust) | gossip + CRDT SQLite | `help wanted`: 3, `good first issue`: 2 | Small codebase, real distributed-systems bugs | #183 subscription channel runs out of capacity and drops events; #129 sync volume drops after restart | E7 |

Labelled-but-empty today (watch; good codebases, nothing labelled
open): `riverqueue/river`, `redpanda-data/redpanda`, `vitessio/vitess`,
`dbos-inc/dbos-transact-py`, `twmb/franz-go`, `nats-io/nats-server`,
`authzed/spicedb`, `loro-dev/loro`, `facebook/buck2`,
`buchgr/bazel-remote`. Apache Kafka tracks issues in Jira (`newbie`
label), not GitHub.

Suggested upstream-issue rules for the harness: pick issues updated in
the last 90 days, comment to claim before starting, budget ≤ 2 sessions
before the first maintainer contact, and grade on "PR opened with a
test + a reply to the first review", not on merge (merge timing isn't
his to control).

## 4. Notes for the harness builders

### 4.1 Coverage

- 66 cards: L1 8 · L2 11 · L3 21 · L4 18 · L5 8.
- Types: build 18 · add-your-part 11 · review-to-own 9 · incident 9 ·
  perf-hunt 9 · design-review 8 · experiment 2.
- Skill tags appearing on cards: DIST 41 · DB 39 · TEST 35 · PERF 33 ·
  COMM 22 · SD 21 · OBS 21 · OS 17 · READ 13 · DEBUG 13 · API 9 ·
  NET 9 · SEC 6 · DATA 4 · ML 3. SD is the *primary* tag on 11 cards,
  PERF on 11, DB on 9, matching the learner's stated focus.
- 24 cards are paper- or blog-inspired; every company has ≥ 2
  (Tallyhaven 4, Scribblewire 2, Freshet 3, Siltstone 5, Glimmerline 2,
  Alderwick 2, Saggarworks 4, Pawl 2). Most others are blog/postmortem
  grounded.
- 26 cards cite a seed from the paper idea bank (`06/P##`, file
  `06-paper-idea-bank.md`), so builders can reuse its reproduce targets.
  Backend seeds not used here: 06/P04 (Prequal), 06/P14 (PGM index),
  06/P16 (io_uring), 06/P19 (UUIDv7, a good extra L1 for Tallyhaven),
  06/P38 (Vivaldi), 06/P39 (Kalman autoscaling), 06/P47 (counting
  quotient filter), 06/P49 (drive survival).

### 4.2 Suggested spines through the catalog (cross-company)

- **Databases + OS spine:** T3 (locks, WAL) → T4 (MVCC horizon) → P2
  (MVCC bloat) → T9 (isolation anomalies with Elle) → D2 (bloom filters) → D6 (fsync/rename crash
  consistency) → S6 (journal + group commit) → D3/D7 (LSM + cache
  papers) → D8 (RFC).
- **Performance spine:** S3 (coalescing) → T5 (hot rows) → G5
  (ClickHouse) → E4 (concurrency limits) → F3 (hedging) → D7 (cache) →
  P5 (group commit) → K3 (CDC throughput).
- **System-design spine:** S8 → T8 → F8 → G7 → E7 → K8 → P7 (each
  ends in an executable model or simulator, so design work is graded,
  not just discussed).
- **Incident spine (on-call readiness):** E2 → P2 → T4 → S5 → G4 →
  F4 → D5 → K4 → E6.

### 4.3 Running it on his machine

- Images all cards need: `postgres:16/17`, `redpandadata/redpanda`,
  `apache/kafka:4.x`, `minio/minio`, `ghcr.io/shopify/toxiproxy`,
  `clickhouse/clickhouse-server`, `scylladb/scylla` (run with
  `--smp 2 --memory 4G`), `memcached`, `redis`, `quay.io/coreos/etcd`,
  Prometheus + Grafana. Peak cards (G5, G6, G8) need Docker Desktop
  memory ≥ 16 GB.
- Keep repos and Docker volumes on the WSL2 ext4 filesystem, never
  `/mnt/c`: fsync semantics and speed differ on the Windows mount, which
  would silently break D6, S6, P5 and T7 measurements.
- `tc netem` inside containers needs `cap_add: [NET_ADMIN]` (E5, S2,
  F-cards); toxiproxy covers latency/stalls where netem isn't needed.
- Benchmarks: pin with `taskset`, warm up, run 3×, grade the median;
  set every *(calibrate)* threshold from the reference solution on this
  machine (e.g. 80% of the reference's improvement).
- The XID fast-forward in T4 is the riskiest setup: prototype it first
  (`pg_resetwal -x` + zero-filled `pg_xact` segment, or PG17's
  `xid_wraparound` test module) `[unverified]`.

### 4.4 Reusable grader components (build once, use in many cards)

| Component | Used by |
|---|---|
| Duplicate/retry fuzzer with `kill -9` injection | T1, F1, F5, G6, P1, P8 |
| Invariant checkers (trial balance, offset contiguity, acked-write survival) | T2, T5, T7, F1, F2, F6, S6, P1 |
| Linearizability checker (Porcupine) | T7, S2, F7 |
| Elle (isolation anomalies from histories) + `docker pause`/partition nemesis | T9, T2 (optional) |
| Interleaving / fault-schedule explorer (seeded) | T7, T8, E6, F7, P7 |
| Crash-state generator (VFS shim) | D6, S6, P5 |
| Object-store fault proxy + PUT/GET cost accounting | F1–F3, F6, D7, D8 |
| `pg_locks` / `pg_stat_activity` sampler | T3, T4, T5, P2 |
| Replay load generators (WebSocket swarm, telemetry, CI history) | S1, S3, S5, G1, G4, K5–K7 |
| Structured postmortem schema (contributing factors as fields) | every incident card |
| Mutation check for models ("remove a step, model must fail") | T8, P7 |

### 4.5 Overlap checks

- **His existing projects:** S1/S2 are server fan-out and failover, not
  game netcode; D-cards never ask for a full KV store or LSM from
  scratch (they extend SiltDB); nothing touches HNSW/vector search; D6 is
  user-space crash consistency, not xv6's file system; P-cards are
  workflow engines, not his journal CLI.
- **Sibling catalog (02, AI/ML infra):** no model serving, GPU,
  training, RAG or vector-index cards here. K7 (predictive test
  selection) and K5's success model use light ML on CI data; G3 and K3
  touch storage formats near ML-artifact storage (Xet), but the
  deliverables are backend.

### 4.6 Unverified or secondary items (fix before building)

- Figma "Rust in production" URL (company 2.2 stack line).
- RocksDB bloom-filter wiki URL (D2).
- Configerator SOSP 2015 paper details (E7); timing-wheels paper (P4);
  (the mmap CIDR 2022, Tail at Scale and FoundationDB links were
  confirmed via the idea bank's checked links);
  Flexible Paxos arXiv ID (P7); Meta predictive-test-selection arXiv ID
  and its headline numbers (K7); FastCDC USENIX URL and speed claims
  (K3); PEP 706, RFC 2789 and AWS Builders' Library URLs (K1, K2, P8);
  Brandur's postgres-queues URL (P2).
- Secondary-only facts: LinkedIn Northguard figures (SiliconANGLE),
  Airbnb Orpheus (Airbnb's later post + mirrors), Discord's node/latency
  numbers, Square Books on Spanner (StackShare), Hugging Face Xet
  speed-up figures (only docs used in cards).
- Web search budget ran out midway through company 2.6; items marked
  "from memory" or "not re-checked this session" were written after
  that point.
