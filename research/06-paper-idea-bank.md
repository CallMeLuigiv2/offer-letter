# 06 — Paper & blog idea bank (techniques a company would try in production)

Research date: 2026-10-19. Feeds the AI/ML-infra catalog (02) and the
backend & distributed-systems catalog (03). Seeds map to a **niche**, not to
a company; catalog writers pick the fictional company that fits.

Each seed becomes a ticket of the form *"our team wants to try the technique
from <paper/post> in our system."* Skill tags are the 20 from
[01 §1.2](01-hiring-and-skills.md) plus **LIT** (research literacy), which
the hiring agent added on 2026-10-19 (01 §1.3). Every seed is tagged LIT
plus its domain tags.

## Contents

0. How to read a seed card
1. Seed bank (50 seeds) — index table, then cards
   - 1A Systems / DB / networking / OS (21)
   - 1B ML systems / ML (15)
   - 1C Cross-domain (14)
2. The "paper task" format (reproduce / apply / adopt memo / critical read /
   blog transfer), aligned with 01's LIT checks
3. Do employers value this?
4. 10 best starter seeds for L1–L2
5. From memory / not re-checked

## 0. How to read a seed card

```
### P## Title
- Source — title, authors/site, year, link · domain of origin
- Claim — the headline result, in the source's own numbers
- Niche — who would adopt it, and why it matters there
- Ticket — the text the PM / tech lead posts
- Stack · Skills · Level · Size — language (why) · tags, primary first · L1–L5 · hours → blocks
- Split — what AI teammates pre-build / what HE writes
- Reproduce target — the scaled-down, harness-checkable result on his machine
- Risk — does the result plausibly hold at small scale? replication notes
```

Conventions:
- **Blocks** are 30–90 min sessions; "6 h → 5 blocks" means five sittings.
- **Reproduce targets are relative** (ratio vs. a baseline measured in the
  same run on the same box), never absolute numbers from the paper's
  hardware. The harness runs baseline and treatment back to back, 3+
  repetitions, and grades the median ratio. This makes WSL2/Docker overhead
  cancel out.
- **"Verified"** means I opened the paper/post page or a primary mirror on
  2026-10-19 and the claim is quoted from it. Claims seen only in secondary
  write-ups are marked *(secondary)*; anything I could not confirm is marked
  *(unverified)*.
- **Verification gaps.** The session's shared web-search budget ran out
  midway; the remaining sources were verified by opening their primary pages
  directly. Pages that block fetchers (Netflix tech blog, Medium, ACM DL,
  SAGE) are marked where a claim depends on them. All other links returned
  HTTP 200 on 2026-10-19 except the S3-FIFO author blog (timed out).
- **Not a repeat.** Every seed was checked against his existing projects
  (BRIEF rule 2). Where one is adjacent (vector index, LLM serving), the card
  says why the deliverable differs.
- Mix: 21 systems/DB/networking/OS (42%), 15 ML systems/ML (30%), 14
  cross-domain (28%).

## 1. Seed index (for catalog writers)

Variant: A = reproduce, B = apply, C = adopt memo (see §2). Variant D
(critical-reading quiz) applies to every seed; E (blog transfer) to the
blog-sourced ones listed in §2.7. Every row also carries LIT.

| ID | Seed | Origin | Niche | Lvl | h | Primary tags | Var |
|---|---|---|---|---|---|---|---|
| P01 | SIEVE / S3-FIFO eviction | systems | edge/CDN, KV cache | L2 | 6 | PERF OS DB LIT | A→B |
| P02 | Coalescing + XFetch | algorithms | read-heavy backends | L1–2 | 4 | PERF DB DIST LIT | B |
| P03 | Hedged requests | systems | fan-out search/storage | L2 | 5 | PERF DIST NET LIT | A→B |
| P04 | Prequal load balancing | systems | RPC mesh, ML routers | L3 | 8 | DIST PERF NET LIT | A |
| P05 | Bounded-load consistent hashing | algorithms | CDN, cache routing | L1–2 | 4 | DIST PERF LIT | A→B |
| P06 | Retry budgets vs. metastable failure | SRE | any microservices | L2–3 | 8 | OBS DIST DEBUG LIT | A→B |
| P07 | Elle isolation check | DB testing | DB vendors, ledgers | L3 | 8 | TEST DIST DB LIT | B |
| P08 | Deterministic simulation testing | testing | storage, queues, workflows | L3–4 | 10 | TEST DIST DEBUG LIT | B |
| P09 | Fencing tokens | dist. systems | schedulers, payouts | L2 | 5 | DIST DB TEST LIT | B |
| P10 | Idempotency keys | payments | fintech APIs | L2 | 6 | API DB DIST LIT | B |
| P11 | Hybrid logical clocks | dist. systems | multi-region DB, CDC | L2 | 4 | DIST TEST LIT | B |
| P12 | Eg-walker | collaboration | real-time collab | L3/L5 | 10 | PERF DIST LIT | C→A |
| P13 | Binary fuse / Ribbon filters | algorithms | LSM engines | L2–3 | 6 | DB PERF CODE LIT | A→B |
| P14 | PGM learned index | DB | analytics/time-series | L3 | 8 | DB PERF LIT | A |
| P15 | mmap adopt memo | DB/OS | storage startups | L2–3 | 5 | LIT OS DB | C+A |
| P16 | io_uring read path | OS/storage | SSD-resident indexes | L3 | 8 | OS PERF DB LIT | A→B |
| P17 | WAL crash consistency (LazyFS) | OS/storage | queues, ledgers, KV | L3 | 8 | OS DB TEST LIT | B |
| P18 | Protocol-aware recovery | dist. storage | consensus logs | L5 | 16 | DIST DB TEST LIT | B |
| P19 | UUIDv7 keys | DB | any SaaS backend | L1 | 3 | DB PERF LIT | A |
| P20 | Transparency log | security | audit, registries | L2–3 | 8 | SEC API TEST LIT | B |
| P21 | Warm-pool keep-alive policy | cloud | serverless GPU | L2 | 6 | MLSYS DATA PERF LIT | A |
| P22 | Prefix-cache-aware routing | ML systems | LLM platforms | L3 | 10 | MLSYS DIST PERF LIT | A→B |
| P23 | Speculative decoding memo | ML systems | inference APIs | L2 | 6 | MLSYS PERF LIT | C+A |
| P24 | Chunked-prefill budget | ML systems | LLM serving | L2 | 6 | MLSYS PERF OBS LIT | A |
| P25 | Disaggregation memo (Vidur) | ML systems | LLM platforms | L4 | 8 | LIT SD MLSYS | C |
| P26 | Virtual Token Counter fairness | ML systems | multi-tenant LLM APIs | L3 | 8 | MLSYS SD API LIT | B |
| P27 | Constrained JSON decoding | ML systems | extraction/agents | L1–2 | 4 | ML MLSYS API LIT | C+A |
| P28 | Cut Cross-Entropy | ML systems | fine-tuning platforms | L2 | 5 | MLSYS ML PERF LIT | A→B |
| P29 | Selective recompute | ML systems | training infra | L3 | 8 | MLSYS PERF LIT | A+C |
| P30 | Async checkpointing | ML systems | training infra | L2–3 | 6 | MLSYS OS TEST LIT | B |
| P31 | Data stalls | ML systems | CV/recsys training | L2 | 6 | MLSYS PERF OBS LIT | A→B |
| P32 | ACORN filtered vector search | ML systems/DB | vector DBs, RAG | L3 | 8 | MLSYS DB PERF LIT | A→B |
| P33 | MinHash near-dup + leak check | ML data | data platforms | L2 | 6 | DATA ML PERF LIT | B |
| P34 | Confident learning | ML data | any labelled test set | L1–2 | 4 | ML DATA LIT | A |
| P35 | LLM-judge position bias | ML evals | eval platforms | L2 | 5 | ML TEST LIT | A |
| P36 | Temperature scaling | ML | confidence routing | L1 | 3 | ML TEST LIT | A→B |
| P37 | SWIM + Lifeguard | epidemiology | cache clusters, discovery | L3 | 10 | DIST NET TEST LIT | B |
| P38 | Vivaldi coordinates | physics | edge/CDN, geo-DB | L2 | 6 | NET DIST PERF LIT | A→B |
| P39 | Kalman CPU allocation | control theory | autoscaling | L2–3 | 6 | INFRA OBS PERF LIT | A |
| P40 | Adaptive concurrency limits | control/TCP | gateways | L2 | 5 | PERF OBS DIST LIT | B |
| P41 | Learned SJF for LLM requests | queueing/OR | LLM APIs | L3 | 8 | MLSYS ML SD LIT | A |
| P42 | Themis GPU auctions | mechanism design | ML platforms | L4 | 12 | SD MLSYS COMM LIT | C+A |
| P43 | Dominant Resource Fairness | economics | job queues, CI | L2 | 5 | SD TEST CODE LIT | B |
| P44 | Karma credits | economics | multi-tenant caches | L3 | 8 | SD DIST TEST LIT | A |
| P45 | Spot under deadlines | OR | training platforms | L2–3 | 6 | MLSYS INFRA SD LIT | A |
| P46 | Honey-bee replica allocation | biology/ecology | model serving, hosting | L2–3 | 6 | SD PERF LIT | C+A |
| P47 | Counting quotient filter | bioinformatics | gateways, CDNs | L3 | 6 | DATA PERF DB LIT | A |
| P48 | Sequential canary testing | clinical statistics | CD platforms | L2 | 5 | OBS TEST INFRA LIT | A→B |
| P49 | Drive survival analysis | biostatistics | storage/bare metal | L2 | 8 | DATA ML OBS LIT | A |
| P50 | Spectral-residual anomalies | computer vision | observability | L2 | 5 | OBS ML DATA LIT | A |

Level spread: L1–L2 = 24 seeds, L2–3 = 8, L3 = 14, L3–4 to L5 = 4 (plus the L5 variant of P12).
Coverage of the 20 tags: every tag appears; EXEC is exercised by the
multi-block plans of every card rather than tagged per card.

## 1A. Systems / DB / networking / OS

### P01 FIFO-based eviction (SIEVE / S3-FIFO) for the object cache
- **Source:** [SIEVE is Simpler than LRU](https://www.usenix.org/conference/nsdi24/presentation/zhang-yazhuo), Zhang, Yang, Yue, Vigfusson, Rashmi, NSDI 2024; companion [FIFO queues are all you need for cache eviction (S3-FIFO)](https://junchengyang.com/publication/sosp23-s3fifo.pdf), Yang et al., SOSP 2023 ([author blog](https://blog.junchengyang.com/system/cache/2023/08/01/s3fifo), timed out on 2026-10-19 re-check) · systems (caching).
- **Claim:** SIEVE: up to 63.2% lower miss ratio than ARC; lower miss ratio than 9 algorithms on >45% of 1,559 traces; 2× the throughput of an optimized LRU at 16 threads; <20 lines changed to adopt in 5 libraries. S3-FIFO: lowest mean miss ratio on 10 of 14 datasets (6,594 traces), 6× LRU throughput at 16 threads. *Verified.*
- **Niche:** edge/CDN caches and in-memory KV caches. Miss ratio is egress money and origin load; the global LRU lock is a known throughput ceiling.
- **Ticket:** "Our edge object cache runs LRU behind one mutex. Try SIEVE behind a flag. Report miss ratio vs. LRU on our five replayed traces and throughput at 1/4/8/16 threads. If it wins, propose the rollout."
- **Stack · Skills · Level · Size:** Rust (edge proxies in this niche are Rust/Go) · PERF, OS, DB, TEST, REVIEW, LIT · **L2** · 6 h → 5 blocks (paper + trace harness; single-thread SIEVE; miss-ratio sweep; lock-free-ish concurrent version; write-up).
- **Split:** teammates ship the trace replayer, cache trait, LRU baseline and bench harness. He writes SIEVE (the "hand" and visited bit), property tests vs. a reference model, the concurrent variant and the report.
- **Reproduce target:** on 5 public traces from [libCacheSim](https://github.com/1a1a11a/libCacheSim)'s data sets at cache size = 10% of footprint, SIEVE miss ratio ≤ LRU on ≥ 4/5 traces; 16-thread throughput ≥ 1.5× the mutex-LRU (paper: 2×).
- **Risk:** low. Miss ratio is a property of the trace, not of cluster size. No independent replication found, but the algorithms ship in several OSS libraries (e.g. [golang-fifo](https://pkg.go.dev/github.com/scalalang2/golang-fifo)), so the planted-bug review variant is easy to grade.

### P02 Stampede protection: request coalescing + XFetch early refresh
- **Source:** [Optimal Probabilistic Cache Stampede Prevention](https://www.vldb.org/pvldb/vol8/p886-vattani.pdf), Vattani, Chierichetti, Lowenstein, PVLDB 8(8) 2015; [How Discord Stores Trillions of Messages](https://discord.com/blog/how-discord-stores-trillions-of-messages), Discord blog, 2023 · algorithms / backend.
- **Claim:** XFetch (each reader refreshes early with probability rising toward expiry) is proven optimal and "performs much better than heuristics used in real-world systems" *(verified via paper index + Wikipedia; no numbers in abstract)*. Discord's Rust data services coalesce concurrent reads of the same row into one DB query and route by channel id so coalescing hits *(verified; no coalescing-specific numbers given)*.
- **Niche:** read-heavy product backends (feeds, chat, catalog) with Redis in front of Postgres/Cassandra.
- **Ticket:** "Last month's incident: a hot key expired and 400 requests recomputed it at once; the DB fell over. Add per-instance coalescing (singleflight) and XFetch-style probabilistic early refresh across instances."
- **Stack · Skills · Level · Size:** Go + Redis + Postgres in Docker Compose · PERF, DB, DIST, OBS, LIT · **L1–L2** · 4 h → 3 blocks.
- **Split:** teammates ship the service, the load generator and a Grafana panel of DB queries/s. He writes coalescing, XFetch (with the β knob), and the test that proves both.
- **Reproduce target:** 50 concurrent clients hammering one key with TTL = 5 s: DB recomputations per expiry ≤ 1.2 on average (baseline ≈ client count); p99 latency in the expiry window ≥ 5× lower than baseline.
- **Risk:** low. The math is scale-free; the only trap is clock skew between instances (a good pushback hook).

### P03 Hedged requests for the fan-out aggregator
- **Source:** [The Tail at Scale](https://cacm.acm.org/research/the-tail-at-scale/), Dean & Barroso, CACM 2013 (classic; [MIT 6.1800 reading](https://web.mit.edu/6.1800/www/readings/03-tail.shtml)) · systems.
- **Claim:** in a BigTable benchmark reading 1,000 keys across 100 servers, hedging after 10 ms cut 99.9th-percentile latency from 1,800 ms to 74 ms for 2% more requests *(secondary: CACM page blocked; numbers quoted by several course notes)*.
- **Niche:** search/feature-store/fan-out services where one slow shard sets p99.
- **Ticket:** "Our query aggregator calls 20 shard replicas; one slow replica dominates p99. Add hedged requests: send a backup after the p95 delay, cancel the loser, cap extra load at 5%."
- **Stack · Skills · Level · Size:** Go + gRPC (context cancellation is first-class) · PERF, DIST, NET, OBS, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the shard servers, the aggregator and a latency injector. He writes the hedging policy, the load cap (token bucket), cancellation and the measurement.
- **Reproduce target:** 10 replica containers, 1% of requests get +200 ms injected independently: p99.9 of a 10-way fan-out drops ≥ 5× with ≤ 5% extra requests.
- **Risk:** low if tail latency is *injected* per replica. Natural Docker noise on one host is correlated (shared CPU), which defeats hedging — that is the lesson the memo should name.

### P04 Probe-based load balancing (Prequal) in the RPC sidecar
- **Source:** [Load is not what you should balance: Introducing Prequal](https://www.usenix.org/conference/nsdi24/presentation/wydrowski), Wydrowski, Kleinberg, Rumble, Archer (Google), NSDI 2024 · systems / networking.
- **Claim:** choosing replicas by probed requests-in-flight and latency, not CPU, "dramatically decreased tail latency, error rates, and resource use"; in YouTube for over a year. *Verified; the abstract has no numbers.*
- **Niche:** service mesh / internal RPC platform teams, ML-serving routers with heterogeneous replicas.
- **Ticket:** "Our balancer picks the least-CPU replica. Prototype Prequal's probe pool and hot-cold rule in the sidecar; compare against round-robin and power-of-two-choices (least requests) with two slow replicas."
- **Stack · Skills · Level · Size:** Go · DIST, PERF, NET, SD, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the sidecar skeleton, replicas with a `/probe` endpoint, the load generator. He writes probe pooling, aging, the selection rule and the experiment.
- **Reproduce target:** 6 replicas, 2 capped at `--cpus 0.5`, 80% aggregate load: Prequal p99 ≤ 0.5× round-robin and ≤ P2C-least-requests.
- **Risk:** medium. Paper gains come from multi-tenant antagonists at scale; one host gives fewer samples, so heterogeneity is emulated with CPU caps.

### P05 Consistent hashing with bounded loads for the cache router
- **Source:** [Consistent Hashing with Bounded Loads](https://arxiv.org/abs/1608.01350), Mirrokni, Thorup, Zadimoghaddam, SODA 2018; [Vimeo engineering blog](https://medium.com/vimeo-engineering-blog/improving-load-balancing-with-a-new-consistent-hashing-algorithm-9f1bd75709ed), Rodland, 2016; [Google Research blog](https://research.google/blog/consistent-hashing-with-bounded-loads/), 2017 · algorithms.
- **Claim:** cap every node at c × average load; Vimeo implemented it in HAProxy (`hash-balance-factor`) and cut cache bandwidth "by a factor of almost 8" *(secondary: figure from Google's post)*.
- **Niche:** CDN/video, cache clusters, sticky routing for LLM prefix caches.
- **Ticket:** "A viral asset pins one cache node at 100% while others idle. Add bounded loads (c = 1.25) to our ring and show what it costs in hit ratio."
- **Stack · Skills · Level · Size:** Go or Python · DIST, PERF, TEST, LIT · **L1–L2** · 4 h → 3 blocks.
- **Split:** teammates ship the ring, the simulator and Zipf workload. He writes the bounded-load lookup, rebalancing on node add/remove, property tests.
- **Reproduce target:** Zipf(1.1) over 10 nodes: max/avg load ≤ 1.25 (plain ring > 2); hit-ratio loss ≤ 3 points; keys moved on node add within 2× of plain consistent hashing.
- **Risk:** low; it's a combinatorial guarantee.

### P06 Retry budgets vs. a reproduced metastable failure
- **Source:** [Metastable Failures in the Wild](https://www.usenix.org/conference/osdi22/presentation/huang-lexiang), Huang et al., OSDI 2022; [Fixing retries with token buckets and circuit breakers](https://brooker.co.za/blog/2022/02/28/retries.html), Marc Brooker, 2022; [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/), Brooker, AWS, 2015; [Fail at Scale](https://queue.acm.org/detail.cfm?id=2839461), Maurer (Facebook), ACM Queue 2015 (ACM blocks fetchers; confirmed via index) (adaptive LIFO + CoDel; [summary](https://blog.acolyer.org/2015/11/19/fail-at-scale-controlling-queue-delay/)) · systems / SRE.
- **Claim:** 22 metastable failures from 11 organizations; ≥ 4 of 15 major AWS outages in a decade were metastable; retries are a main amplifier. Brooker: a token bucket that deposits 0.1 per success and spends 1 per retry behaves like N retries when healthy and ~no retries under failure. *Verified.*
- **Niche:** any microservice platform; SRE/reliability teams.
- **Ticket:** "Postmortem action item: a 30 s DB slowdown became a 40 min outage because clients retried 3× with no backoff. Reproduce it in compose, then add jittered backoff + a retry token bucket to our client library and prove the system recovers once the trigger is gone."
- **Stack · Skills · Level · Size:** Python or Go + [Toxiproxy](https://github.com/Shopify/toxiproxy) · OBS, DIST, DEBUG, PERF, LIT · **L2–L3** · 8 h → 6 blocks (reproduce first — that is half the learning).
- **Split:** teammates ship the 3-service app, the dashboard, the trigger script. He writes the reproduction scenario, the client retry policy, the recovery test and the postmortem addendum. Stretch: adaptive-LIFO + CoDel server queue.
- **Reproduce target:** naive client — goodput stays < 20% of baseline for 5 min after a 30 s trigger ends (metastable); with retry budget — goodput ≥ 90% within 30 s after the trigger ends.
- **Risk:** medium. Metastability needs a sustaining loop (queue + client timeout shorter than queueing delay); the paper's authors reproduced their cases in a controlled environment, so the loop is attainable on one box.

### P07 Elle-check our "serializable" claim
- **Source:** [Elle: Inferring Isolation Anomalies from Experimental Observations](https://arxiv.org/abs/2003.10554), Kingsbury & Alvaro, PVLDB 14(3) 2020; [Jepsen analyses](https://jepsen.io/analyses) · distributed systems / DB testing.
- **Claim:** infers an Adya dependency graph from client-observed histories and finds anomalies (G0…G2, lost update) in polynomial time, where general serializability checking is NP-complete. Jepsen uses it in its analyses. *Verified (paper); breadth of Jepsen use from memory.*
- **Niche:** database vendors and any team selling "transactions" on top of a KV store (also payments ledgers).
- **Ticket:** "Docs say our KV store is serializable. Before the launch post, run a list-append workload with partitions and pauses and check the history with Elle. Fix or downgrade the claim."
- **Stack · Skills · Level · Size:** Python client + [jepsen-io/elle](https://github.com/jepsen-io/elle) (Clojure, run as a JVM tool) · TEST, DIST, DB, DEBUG, READ, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the 3-node store (with an isolation bug planted behind a config flag), Docker network faults, history logger stub. He writes the workload, the nemesis schedule, the history encoder, interprets Elle's cycle output, and fixes the bug.
- **Reproduce target:** Elle reports the planted anomaly in ≥ 9/10 60-second runs; zero anomalies on the fixed build over 10 runs.
- **Risk:** low; Elle's soundness doesn't depend on scale. Only tooling risk is the JVM step.

### P08 Deterministic simulation testing for the lease service
- **Source:** [FoundationDB: A Distributed Unbundled Transactional Key Value Store](https://www.foundationdb.org/files/fdb-paper.pdf), Zhou et al., SIGMOD 2021; [What's the big deal about Deterministic Simulation Testing?](https://notes.eatonphil.com/2024-08-20-deterministic-simulation-testing.html), Phil Eaton, 2024 (FoundationDB, TigerBeetle, Antithesis, WarpStream, Polar Signals) · distributed systems / testing.
- **Claim:** run all nodes on one thread with a seeded scheduler, simulated clock and network, inject faults, check invariants; any failure replays from its seed. Limits: external integrations, workload quality, seeds rot as code changes. *Verified.*
- **Niche:** storage, queues, durable-workflow engines; anything with leader leases.
- **Ticket:** "The lease-renewal test flakes once a week in CI and nobody can reproduce it. Put the service under a DST harness, find a seed that fails, fix the race."
- **Stack · Skills · Level · Size:** Python asyncio (custom event loop) or Rust ([turmoil](https://github.com/tokio-rs/turmoil)) · TEST, DIST, DEBUG, OS, LIT · **L3–L4** · 10 h → 8 blocks.
- **Split:** teammates ship the service with Clock/Network interfaces already injected (and a planted lease-expiry race). He writes the simulator loop, fault injector, invariant checker, seed replay and the fix.
- **Reproduce target:** finds a failing seed within 10,000 seeds (< 5 min); that seed fails 10/10 replays; after the fix 100,000 seeds pass.
- **Risk:** low; DST is scale-free. Real risk is determinism leaks (dict order, `time.time()`), which the harness can test for by running a seed twice and diffing traces.

### P09 Fencing tokens for the distributed job lock
- **Source:** [How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html), Martin Kleppmann, 2016 · distributed systems.
- **Claim:** a lease-based lock (e.g. Redlock) cannot by itself prevent two holders after a GC pause or clock jump; the storage must reject stale writers via monotonically increasing fencing tokens. *Verified (well-known post).*
- **Niche:** schedulers, cron/batch platforms, payout workers.
- **Ticket:** "Two workers both believed they held `payout:42` and paid twice. Add fencing tokens issued by the lock and checked by the ledger write."
- **Stack · Skills · Level · Size:** Python + Redis + Postgres · DIST, DB, TEST, DEBUG, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the worker, lock client and a "pause the holder" fault (`docker pause`). He writes token issue/check, the fault test, and a short note on why TTL tuning alone can't fix it.
- **Reproduce target:** without fencing ≥ 1 double-write in 20 paused-holder trials; with fencing 0 in 100.
- **Risk:** none; deterministic fault scenario.

### P10 Idempotency keys with atomic phases for the payments API
- **Source:** [Designing robust and predictable APIs with idempotency](https://stripe.com/blog/idempotency), Stripe, 2017; [Implementing Stripe-like Idempotency Keys in Postgres](https://brandur.org/idempotency-keys), Brandur Leach, 2017 · backend / payments.
- **Claim:** store key + recovery point; each atomic phase commits locally before the next foreign call; a completer finishes stalled requests, a reaper deletes keys after ~72 h. *Verified.*
- **Niche:** payments/fintech APIs, any POST that moves money or sends messages.
- **Ticket:** "Mobile clients retry `POST /payouts` on timeout; finance found duplicates. Add idempotency keys with recovery points, a completer, and a reaper."
- **Stack · Skills · Level · Size:** Python (FastAPI) + Postgres · API, DB, DIST, TEST, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship the API, a fake payment provider and a crash-point injector. He writes the key table, phases, recovery logic, completer, and the crash tests.
- **Reproduce target:** crash the server at each phase boundary and replay the client's retry, 200 runs: exactly one provider charge in 100%; concurrent duplicate requests get the same response or 409.
- **Risk:** none.

### P11 Hybrid logical clocks for the audit/event log
- **Source:** [Logical Physical Clocks and Consistent Snapshots in Globally Distributed Databases](https://cse.buffalo.edu/~demirbas/publications/hlc.pdf), Kulkarni, Demirbas, Madappa, Avva, Leone, 2014 (Murat Demirbas, author of [Metadata](https://muratbuffalo.blogspot.com/) blog) · distributed systems.
- **Claim:** HLC captures causality like a logical clock while staying within the NTP error of physical time and fitting in 64 bits; enables consistent snapshots without TrueTime hardware. *Verified.*
- **Niche:** multi-region DBs, CDC/event pipelines, audit logs.
- **Ticket:** "Our audit view orders events by wall clock; a node with skew shows effects before causes. Replace timestamps with HLC and prove ordering."
- **Stack · Skills · Level · Size:** Go or Python · DIST, TEST, CODE, LIT · **L2** · 4 h → 3 blocks.
- **Split:** teammates ship 3 services with skew injection ([libfaketime](https://github.com/wolfcw/libfaketime)). He writes HLC send/receive rules, encoding, property tests.
- **Reproduce target:** with ±200 ms skew, wall-clock ordering shows ≥ 1 causal inversion per 1,000 chains; HLC shows 0, and |HLC − physical| ≤ max skew.
- **Risk:** none.

### P12 Eg-walker for server-side document storage
- **Source:** [Collaborative Text Editing with Eg-walker: Better, Faster, Smaller](https://arxiv.org/abs/2409.14252), Gentle & Kleppmann, EuroSys 2025 · distributed systems / collaboration.
- **Claim:** vs. CRDTs, about an order of magnitude less steady-state memory and orders-of-magnitude faster document load; vs. OT, orders-of-magnitude faster merging of long branches. *Verified (no numbers in abstract).*
- **Niche:** real-time collaboration backends (docs, whiteboards, code editors).
- **Ticket:** "Each open doc holds a full CRDT in server memory; RAM is our top cost. Evaluate Eg-walker (reference impl: [diamond-types](https://github.com/josephg/diamond-types)) against our current CRDT on recorded editing traces."
- **Stack · Skills · Level · Size:** Rust or TypeScript · PERF, DIST, LIT, COMM · **L3** (adopt + benchmark) / **L5** (implement the walker) · 10 h → 8 blocks (L3).
- **Split:** teammates ship the doc service and trace loader. He writes the integration, the benchmark and the adopt memo; at L5 he writes the event-graph replay.
- **Reproduce target:** on the paper's public editing traces, final text identical to the CRDT's in 100% of traces; steady-state memory ≤ 1/5 of the CRDT's; cold load faster.
- **Risk:** low for the benchmark (single process; paper's claims are per-document). Implementation risk is high at L5.

### P13 Binary fuse / Ribbon filters in the SSTable format
- **Source:** [Ribbon filter: practically smaller than Bloom and Xor](https://arxiv.org/abs/2103.02515), Dillinger & Walzer, 2021; [Binary Fuse Filters](https://arxiv.org/abs/2201.01174), Graf & Lemire, JEA 2022; [RocksDB blog: Ribbon filter](https://rocksdb.org/blog/2021/12/29/ribbon-filter.html), 2021 · algorithms / storage.
- **Claim:** Ribbon: < 10% space overhead over the information bound where practical filters have ≥ 20%; RocksDB reports ~30% filter-memory savings for 3–4× CPU. Binary fuse: within 13% of the lower bound (8% with slower queries), > 2× faster to build than xor filters. *Verified.*
- **Niche:** LSM storage engines, time-series DBs, any "does this segment have key k" path.
- **Ticket:** "Filters are 30% of RAM on our big nodes. Our SSTables are immutable, so try a binary fuse filter at the same FPR and report bits/key, FPR, and lookup ns."
- **Stack · Skills · Level · Size:** Rust · DB, PERF, CODE, TEST, LIT · **L2–L3** · 6 h → 5 blocks.
- **Split:** teammates ship the SST reader/writer and the Bloom baseline. He writes the 3-wise binary fuse construction (peeling), the query, the serialization, and the benchmark.
- **Reproduce target:** 10 M keys: measured FPR within ±10% of 2^-8 at ≤ 9.1 bits/key; ≥ 20% fewer bits/key than the Bloom baseline at equal FPR.
- **Risk:** low; space/FPR are math, not scale.

### P14 A learned (PGM) index for immutable segments
- **Source:** [The PGM-index](https://pgm.di.unipi.it/), Ferragina & Vinciguerra, PVLDB 13(8) 2020; sanity check: [Benchmarking Learned Indexes (SOSD)](https://arxiv.org/abs/2006.12804), Marcus et al., PVLDB 2020 · DB / algorithms.
- **Claim:** matches a cache-optimised static B+-tree on lookups with 83× less space; dynamic variant up to 71% faster at 1,140× less space. SOSD's independent benchmark: learned indexes win only for read-only, in-memory, dense arrays. *Verified.*
- **Niche:** analytics/time-series engines, search posting lists, segment-based stores.
- **Ticket:** "Our sparse index for immutable segments is 1.6 GB on the largest node. Try a PGM index for sealed segments; keep the B-tree for the mutable one."
- **Stack · Skills · Level · Size:** Rust (or C++ with the [PGM library](https://github.com/gvinciguerra/PGM-index) as reference) · DB, PERF, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the segment format and the baseline index. He writes the streaming optimal piecewise-linear fit with error ε, the last-mile search and the benchmark.
- **Reproduce target:** on two SOSD datasets downsampled to 50 M keys: lookup latency ≤ 1.2× the B-tree's, index size ≤ 1/20; on `osm` (SOSD's hard set) the memo reports the smaller gain honestly.
- **Risk:** low inside the paper's setting (read-only, in memory). The memo should name SOSD's limits.

### P15 Adopt memo: should the new segment store use mmap?
- **Source:** [Are You Sure You Want to Use MMAP in Your DBMS?](https://db.cs.cmu.edu/mmap-cidr2022/), Crotty, Leis, Pavlo, CIDR 2022 (benchmark code linked from the page) · DB / OS.
- **Claim:** mmap "is not a suitable replacement for a traditional buffer pool": correctness traps (transactional safety, I/O error handling) and performance limits (page-table contention, TLB shootdowns, single-threaded eviction) once data exceeds memory. *Verified (numbers are in the PDF figures).*
- **Niche:** storage-engine and vector-DB startups tempted by mmap for speed of development.
- **Ticket:** "A teammate proposes mmap for the new segment store to save two weeks. Write a one-page adopt/don't-adopt memo: which of the paper's assumptions hold for us, then run its random-read benchmark scaled down."
- **Stack · Skills · Level · Size:** C++ or Rust + fio · LIT, OS, DB, PERF, COMM · **L2–L3** · 5 h → 4 blocks.
- **Split:** teammates provide the proposal PR and workload description (read-mostly, dataset 3× RAM). He runs the benchmark, writes the memo, defends it in the review.
- **Reproduce target:** file 2× a Docker memory cap: mmap random-read throughput ≤ 0.5× pread/O_DIRECT once the file exceeds memory (the paper's trend), and the memo names ≥ 3 assumptions with a verdict each.
- **Risk:** medium. The paper used many SSDs and high thread counts; TLB-shootdown effects need many cores (he has 12). WSL2's virtual disk adds noise; the ratio target absorbs it.

### P16 io_uring read path for an SSD-resident index
- **Source:** [What Modern NVMe Storage Can Do, And How To Exploit It](https://www.vldb.org/pvldb/vol16/p2090-haas.pdf), Haas & Leis, PVLDB 16(9) 2023 · DB / OS.
- **Claim:** 8 NVMe SSDs give 12.5 M random-read IOPS, but RocksDB, WiredTiger, PostgreSQL and MySQL reach only a fraction (a 3.5× gap even for their own LeanStore); with an I/O-optimized design the engine runs > 1 M TPC-C tx/s with data 10× RAM. *Verified from the PDF.*
- **Niche:** storage engines, vector DBs serving from SSD, feature stores.
- **Ticket:** "Our read path is a pread thread pool. We get 150 k IOPS; fio says the drive does far more. Rework it to batched io_uring submission with deep per-thread queues."
- **Stack · Skills · Level · Size:** Rust ([io-uring](https://github.com/tokio-rs/io-uring) crate) or C++ (liburing) · OS, PERF, DB, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the index format, the pread baseline and a fio job file. He writes the submission/completion loop, buffer management and benchmark.
- **Reproduce target:** reach ≥ 70% of fio's measured random-4K-read IOPS ceiling on his own NVMe (same WSL2 setup), vs. the baseline's measured fraction; ≥ 2× the baseline.
- **Risk:** medium. WSL2's ext4.vhdx caps IOPS below bare metal; expressing the target as a fraction of fio's ceiling on the same setup keeps it fair.

### P17 Crash-consistency audit of the WAL under LazyFS
- **Source:** [All File Systems Are Not Created Equal (ALICE)](https://research.cs.wisc.edu/adsl/Publications/alice-osdi14.html), Pillai et al., OSDI 2014; [When Amnesia Strikes (LazyFS)](https://www.vldb.org/pvldb/vol17/p3017-ramos.pdf), Ramos, …, Kingsbury, …, Paulo, PVLDB 17(11) 2024; [LazyFS](https://github.com/dsrhaslab/lazyfs) · OS / storage.
- **Claim:** ALICE found 60 crash vulnerabilities in 11 widely used applications (about half exposed on ext3/ext4/btrfs). LazyFS reproduces lost/torn un-fsynced writes; it reproduced 5 known bugs and found 8 new ones across PostgreSQL, etcd, ZooKeeper, Redis, LevelDB, PebblesDB, Lightning. *Verified.*
- **Niche:** anything that acks a write: queues, ledgers, KV stores.
- **Ticket:** "Our ledger WAL promises durability on ack. Run it on LazyFS, drop un-fsynced data at random points, and fix whatever loses acked writes."
- **Stack · Skills · Level · Size:** Go or Rust + LazyFS (FUSE in WSL2) · OS, DB, TEST, DEBUG, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the WAL with planted bugs (no directory fsync after rename; length header written after payload; no checksum). He writes the crash harness, finds and fixes the bugs.
- **Reproduce target:** 200 random crash points: 0 acknowledged writes lost; 0 torn records accepted on recovery.
- **Risk:** low. FUSE in Docker needs `--device /dev/fuse --cap-add SYS_ADMIN`; run in WSL2 directly if that fails.

### P18 Protocol-aware recovery for the replicated log
- **Source:** [Protocol-Aware Recovery for Consensus-Based Storage](https://www.usenix.org/conference/fast18/presentation/alagappan), Alagappan et al., FAST 2018 (Best Paper); a similar recovery in production at [TigerBeetle](https://docs.tigerbeetle.com/concepts/safety/) (docs describe surviving WAL corruption unless every replica is hit; PAR lineage from a third-party summary, not re-checked) · distributed storage.
- **Claim:** unmodified LogCabin and ZooKeeper can lose data or become unavailable after a single storage fault; CTRL recovers safely with little overhead by telling "crashed mid-write" from "corrupted committed entry" and repairing from peers. *Verified.*
- **Niche:** consensus/replicated-log teams (DBs, queues, financial ledgers).
- **Ticket:** "Our Raft log treats a checksum failure as 'truncate from here', which can erase committed entries. Implement CTRL's recovery rules."
- **Stack · Skills · Level · Size:** Go · DIST, DB, TEST, READ, LIT · **L5** · 16 h → 12 blocks.
- **Split:** teammates ship the Raft implementation (he reads it — he does not build Raft) and a sector-corruption injector. He writes the storage-layer distinction, peer repair, and the randomized fault campaign.
- **Reproduce target:** 500 randomized single-node corruptions (incl. the leader): 0 committed-entry losses, cluster available whenever a majority has intact copies; baseline loses data in ≥ 1 trial.
- **Risk:** low for the result; high for effort and reading load.

### P19 UUIDv7 primary keys for new tables
- **Source:** [The problem with using a UUID primary key in MySQL](https://planetscale.com/blog/the-problem-with-using-a-uuid-primary-key-in-mysql), Brian Morrison II, PlanetScale, 2024; Postgres 18 added native `uuidv7()` ([summary](https://www.dbvis.com/thetable/uuidv7-in-postgresql-18-what-you-need-to-know/), *secondary*) · DB.
- **Claim:** random v4 keys force page splits all over the B+tree; InnoDB fills pages to ~94% for sequential keys vs. as low as ~50% for random ones; v7 is time-ordered. *Verified (no benchmark in the post).*
- **Niche:** every SaaS backend.
- **Ticket:** "Insert latency on `orders` degraded once the table outgrew RAM. Measure v4 vs. v7 keys and propose the migration for new tables."
- **Stack · Skills · Level · Size:** Postgres 18 + Python · DB, PERF, COMM, LIT · **L1** · 3 h → 3 blocks.
- **Split:** teammates ship the schema, the loader and `pgstattuple` queries. He writes the experiment, reads the index stats and writes the proposal.
- **Reproduce target:** 20 M inserts with `shared_buffers` = 256 MB: v4 PK index ≥ 1.3× the size of v7; last-million insert throughput for v4 ≤ 0.5× v7; leaf density reported for both.
- **Risk:** low. The effect appears only once the index exceeds the buffer cache, so the cap matters.

### P20 Tamper-evident audit log (transparency log)
- **Source:** [Transparent Logs for Skeptical Clients](https://research.swtch.com/tlog), Russ Cox, 2019 (Go checksum DB design; RFC 6962 Certificate Transparency) · security / cryptography.
- **Claim:** Merkle-tree logs give inclusion and consistency proofs of ~lg N hashes; tiling makes proofs cacheable — ~24 kB of tiles to prove an entry in a 100 M-record log. *Verified.*
- **Niche:** fintech/compliance audit trails, package registries, supply-chain security.
- **Ticket:** "Compliance needs a tamper-evident audit log. Add signed tree heads, inclusion and consistency proofs, and a verifier CLI auditors can run."
- **Stack · Skills · Level · Size:** Go · SEC, API, TEST, CODE, LIT · **L2–L3** · 8 h → 6 blocks.
- **Split:** teammates ship the log append API. He writes the tree hashing, proofs, signing and the verifier.
- **Reproduce target:** harness edits, deletes, reorders and forks history: verifier flags 100% of cases; proofs for 1 M records ≤ 20 hashes; interop with RFC 6962 hash rules (leaf/node prefixes).
- **Risk:** none.

### P21 Keep-alive policy for the model-endpoint warm pool
- **Source:** [Serverless in the Wild](https://www.usenix.org/conference/atc20/presentation/shahrad), Shahrad et al. (Microsoft), ATC 2020; trace: [Azure Public Dataset](https://github.com/Azure/AzurePublicDataset) (Azure Functions 2019) · systems / cloud.
- **Claim:** invocation frequency spans ~8 orders of magnitude; a hybrid histogram policy (idle-time histogram + fallback keep-alive + ARIMA for long idle times) "significantly reduces" cold starts while using fewer resources than fixed keep-alive; later deployed in Azure Functions. *Verified; exact percentages are in the paper body (not checked).*
- **Niche:** serverless GPU / model-serving platforms (cold start = loading weights).
- **Ticket:** "Our warm pool keeps each model endpoint alive 10 min after its last call. Replay the Azure Functions trace and evaluate the hybrid-histogram policy; show the cold-start vs. idle-memory trade-off."
- **Stack · Skills · Level · Size:** Python (pandas) · MLSYS, DATA, PERF, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship the trace loader and a fixed keep-alive simulator. He writes the policy, the Pareto sweep and the memo.
- **Reproduce target:** on one day of the trace, the hybrid policy's (cold-start %, wasted memory-minutes) curve dominates fixed keep-alive at ≥ 3 of 4 memory budgets.
- **Risk:** low; trace-driven simulation is exactly the paper's setting.

## 1B. ML systems / ML

GPU seeds assume one RTX 4070 (12 GB) under WSL2 + Docker, models ≤ 8B at
4-bit or ≤ 3B at fp16, and a **pinned** vLLM/SGLang version (their flags
change between releases). Seeds that touch LLM serving configure, measure or
route around a production engine; none asks him to build a batching server,
which stays a separate roadmap project of his.

### P22 Prefix-cache-aware routing across serving replicas
- **Source:** [SGLang v0.4 release post](https://www.lmsys.org/blog/2024-12-04-sglang-v0-4) (cache-aware load balancer), LMSYS, 2024-12-04; [Preble: Efficient Distributed Prompt Scheduling for LLM Serving](https://arxiv.org/abs/2407.00023), Srivatsa et al., 2024 (ICLR 2025 per authors — venue not confirmed on page); code: [sgl-project/sglang](https://github.com/sgl-project/sglang) (router docs URL moved; not re-located) · ML systems.
- **Claim:** routing by an approximate radix tree of each worker's cached prefixes gave up to 1.9× throughput and 3.8× higher cache hit rate (20% → 75%) on a shared-prefix workload. Preble: 1.5–14.5× lower average and 2–10× lower p99 latency than SOTA serving systems. *Verified (both self-reported).*
- **Niche:** LLM inference platforms where agents/RAG share long system prompts.
- **Ticket:** "Our three vLLM replicas sit behind round-robin; prefix-cache hit rate is ~20%. Add prefix-aware routing with a load-balance guard so a hot prefix doesn't melt one replica."
- **Stack · Skills · Level · Size:** Python or Rust gateway (SGLang's router is Rust) + vLLM with prefix caching · MLSYS, DIST, PERF, SD, LIT · **L3** · 10 h → 8 blocks.
- **Split:** teammates ship the gateway, 3 small-model replicas sharing the GPU (e.g. 0.5B at fp16, `gpu_memory_utilization` 0.25 each), the shared-prefix load generator, and metrics scraping. He writes the per-worker prefix tree, its approximate eviction, the balance rule, the experiment.
- **Reproduce target:** 8 long shared-prefix groups: cache hit rate ≥ 2.5× round-robin's; throughput ≥ 1.3×; with one hot group, p99 TTFT ≤ 1.2× round-robin's (the guard works).
- **Risk:** medium. Small models make prefill cheap, so throughput gains shrink; hit rate is the robust metric. Not a repeat: his own engine is single-node CPU; this is a router.

### P23 Should we turn on speculative decoding? (measure + memo)
- **Source:** [Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192), Leviathan, Kalman, Matias, ICML 2023 · ML systems.
- **Claim:** 2–3× faster on T5-XXL than T5X with identical output distribution. *Verified.*
- **Niche:** inference API providers and on-prem LLM teams.
- **Ticket:** "Product asks whether to enable speculative decoding on our 8B chat endpoint. Measure acceptance rate and speedup on three traffic slices (code edits, chat, JSON extraction) at batch 1, 4, 16. Recommend per slice."
- **Stack · Skills · Level · Size:** vLLM + Python; 7–8B AWQ target with a 0.5–1B draft or n-gram (prompt-lookup) drafting · MLSYS, PERF, LIT, COMM · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship the endpoint, the three prompt sets and the timing client. He designs the sweep, checks correctness, writes the memo.
- **Reproduce target:** greedy outputs identical with and without speculation on 200/200 prompts; ≥ 1.5× decode speedup at batch 1 on the code-edit slice; the memo shows the speedup shrinking with batch size and names why (the paper assumes spare compute per step).
- **Risk:** medium. Support for draft models vs. n-gram/EAGLE varies by vLLM version — pin it. Not a repeat: he measures a production engine's feature rather than building decoding.

### P24 Chunked-prefill token budget for a mixed workload
- **Source:** [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve](https://www.usenix.org/conference/osdi24/presentation/agrawal), Agrawal et al., OSDI 2024 · ML systems.
- **Claim:** chunked prefills + stall-free batching give 2.6× serving capacity on Mistral-7B/1×A100, up to 3.7× on Yi-34B/2×A100, up to 5.6× on Falcon-180B with pipeline parallelism, under tail-latency SLOs. *Verified.*
- **Niche:** LLM serving teams with long-document and chat traffic on one fleet.
- **Ticket:** "Long-document users cause decode stalls for chat users (TPOT spikes). Pick a token budget (`max_num_batched_tokens`) for our mix and show the TTFT/TPOT trade-off."
- **Stack · Skills · Level · Size:** vLLM + Python · MLSYS, PERF, OBS, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship the load generator and an SLO-capacity search stub. He builds the workload mix, the sweep, the capacity search, the plot and the recommendation.
- **Reproduce target:** 1.5B model, 10% 6k-token prompts / 90% chat: at the chosen budget, p99 TPOT ≤ 0.5× the "no chunking" setting; capacity at p99 TPOT ≤ 100 ms ≥ 1.3× (paper: 2.6× on A100).
- **Risk:** medium. Newer vLLM engines chunk by default, so "no chunking" must be emulated with a budget ≥ the longest prompt; a small model shrinks the gain.

### P25 Adopt memo: prefill/decode disaggregation for our fleet
- **Source:** [DistServe](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin), Zhong et al., OSDI 2024; [Vidur: A Large-Scale Simulation Framework for LLM Inference](https://arxiv.org/abs/2405.05465), Agrawal et al., 2024; lineage: NVIDIA Dynamo's disaggregated serving cites DistServe (see 01 §1.3) · ML systems.
- **Claim:** DistServe serves 7.4× more requests or meets a 12.6× tighter SLO with > 90% of requests in SLO. Vidur predicts latency with < 9% error and finds a LLaMA2-70B config in ~1 CPU-hour vs. ~42K GPU-hours of trial deployment. *Verified.*
- **Niche:** LLM platform teams with ≥ tens of GPUs.
- **Ticket:** "Leadership read about disaggregated serving. Should our 16-GPU PCIe fleet do it? Simulate our trace and write the one-page memo."
- **Stack · Skills · Level · Size:** Python (Vidur on CPU + a small event model he writes for KV transfer) · LIT, SD, MLSYS, COMM · **L4** · 8 h → 6 blocks.
- **Split:** teammates supply the fleet description (PCIe, 25 GbE), the request trace and Vidur set up. He runs the colocated baseline in Vidur, models the disaggregated option (KV bytes ÷ link bandwidth per request), writes the memo, defends it.
- **Reproduce target:** memo-graded (see §2): names ≥ 3 DistServe assumptions and checks each (e.g. fast interconnect for KV transfer, SLO mix, prefill-heavy traffic); the harness re-runs his simulation config and gets numbers within 5%.
- **Risk:** low for the memo; Vidur's fidelity claim is for its profiled GPUs, not his.

### P26 Per-tenant fair scheduling (Virtual Token Counter)
- **Source:** [Fairness in Serving Large Language Models](https://www.usenix.org/conference/osdi24/presentation/sheng), Sheng et al., OSDI 2024 · ML systems / scheduling.
- **Claim:** VTC is work-conserving with a proven tight 2× upper bound on the service difference between two backlogged clients, where service counts input and output tokens. *Verified.*
- **Niche:** multi-tenant LLM APIs (free tier vs. enterprise).
- **Ticket:** "One enterprise tenant floods the endpoint and free-tier latency explodes. Add VTC to the gateway's admission queue in front of vLLM."
- **Stack · Skills · Level · Size:** Python (asyncio gateway) · MLSYS, SD, API, PERF, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the gateway with FCFS and a concurrency window to vLLM, plus a two-tenant load generator. He writes the counters, the selection rule, the counter lift for newly active tenants, the fairness test.
- **Reproduce target:** two backlogged tenants at 4:1 offered load: under FCFS the light tenant gets ≤ 25% of tokens; under VTC token shares are within 10% of 50/50, and the gateway stays work-conserving (GPU busy ≥ 95% of the run).
- **Risk:** low-medium. Gateway-level scheduling can't see inside vLLM's batch — a good pushback hook ("why not patch the engine scheduler?").

### P27 Grammar-constrained JSON for the extraction service
- **Source:** [XGrammar](https://arxiv.org/abs/2411.15100), Dong et al., MLSys 2025; [Fast JSON Decoding with Compressed FSM](https://lmsys.org/blog/2024-02-05-compressed-fsm/), LMSYS, 2024; counterpoint: [Let Me Speak Freely?](https://arxiv.org/abs/2408.02442), Tam et al., 2024 · ML systems / LLM apps.
- **Claim:** XGrammar: up to 100× faster than existing structured-generation engines, near-zero end-to-end overhead. Compressed FSM jump-forward: up to 2× lower latency, 2.5× throughput for JSON. Counterpoint: format restrictions cause "a significant decline in LLMs reasoning abilities". *Verified.*
- **Niche:** document-extraction and agent-tooling backends.
- **Ticket:** "3% of extraction responses are invalid JSON and we re-ask the model. Turn on schema-constrained decoding, measure validity, accuracy and per-token overhead. Check whether the constraint hurts accuracy, as one paper claims."
- **Stack · Skills · Level · Size:** vLLM structured outputs + Python · ML, MLSYS, API, TEST, LIT · **L1–L2** · 4 h → 3 blocks.
- **Split:** teammates ship the service and 500 labelled documents. He writes the schema, the evaluation harness (validity, field accuracy, TPOT), and the fallback path.
- **Reproduce target:** invalid-JSON rate = 0% (vs. measured baseline); field accuracy within 1 point of free-form + parse-retry, or the memo shows the accuracy drop the counter-paper predicts; TPOT overhead ≤ 10%.
- **Risk:** low. The two papers disagreeing is the point of the LIT exercise.

### P28 Cut Cross-Entropy in the fine-tuning job
- **Source:** [Cut Your Losses in Large-Vocabulary Language Models](https://arxiv.org/abs/2411.09009), Wijmans et al. (Apple), ICLR 2025 oral; [Liger Kernel](https://arxiv.org/abs/2410.10989), Hsu et al. (LinkedIn), 2024 · ML systems.
- **Claim:** CCE: loss-computation memory for Gemma 2 2B from 24 GB to 1 MB; classifier-head training memory 28 GB → 1 GB, without hurting speed or convergence. Liger: ~20% higher throughput and ~60% less GPU memory on average vs. HuggingFace implementations. *Verified.*
- **Niche:** fine-tuning platforms and training-infra teams on memory-bound GPUs.
- **Ticket:** "Fine-tuning a 1.5B model with a 151k vocab OOMs at seq 4096 on our 12 GB dev GPUs. Swap the loss for CCE (or Liger's fused linear cross-entropy) and report memory, speed and loss parity."
- **Stack · Skills · Level · Size:** PyTorch + Triton kernels · MLSYS, ML, PERF, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the training script and data. He integrates the kernel, writes the memory/speed benchmark and the parity test.
- **Reproduce target:** at the largest batch where the baseline fits, peak memory ≥ 30% lower; tokens/s within ±10%; loss at step 200 within 1% of baseline (same seed).
- **Risk:** low. Logit memory = vocab × tokens × bytes, so the saving is arithmetic; check Triton works under WSL2 first.

### P29 Selective activation recomputation (and when FlashAttention makes it moot)
- **Source:** [Reducing Activation Recomputation in Large Transformer Models](https://arxiv.org/abs/2205.05198), Korthikanti et al. (NVIDIA), arXiv 2022 (MLSys 2023 per proceedings — venue not shown on the arXiv page) · ML systems.
- **Claim:** 5× less activation memory, > 90% less recomputation overhead; 530B GPT on 2,240 A100s reaches 54.2% MFU vs. 42.1% with full recompute. *Verified.*
- **Niche:** training-infra teams.
- **Ticket:** "Our trainer checkpoints every layer and loses ~30% step time to recompute. Apply selective recompute and find the memory/time Pareto front."
- **Stack · Skills · Level · Size:** PyTorch (`torch.utils.checkpoint` with a selective policy) · MLSYS, PERF, LIT, ML · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship a ~350M GPT trainer with three modes stubbed. He writes the selective policy, the memory/time measurement and the memo.
- **Reproduce target:** with eager (materialized) attention, selective recompute gets ≥ 70% of full checkpointing's memory saving at ≤ 1/3 of its time overhead; with SDPA/flash attention the memo shows the gain mostly vanishes and explains why.
- **Risk:** medium, and that's the lesson: the paper's biggest saving is the attention score matrix, which FlashAttention never materializes.

### P30 Asynchronous checkpointing for the trainer
- **Source:** [Reducing Model Checkpointing Times by Over 10x with PyTorch Distributed Asynchronous Checkpointing](https://pytorch.org/blog/reducing-checkpointing-times/), PyTorch blog (with IBM Research), 2024-11 · ML systems.
- **Claim:** 7B checkpoint downtime from 148.8 s to 6.3 s (23.6×); the GPU→CPU copy is the only blocking part, CPU→disk runs in background threads; use a separate process group to avoid collective hangs. *Verified.*
- **Niche:** training-infra and fine-tuning platforms.
- **Ticket:** "Checkpoints stall training for minutes. Move to async checkpointing and prove checkpoints are consistent, resumable and never half-written."
- **Stack · Skills · Level · Size:** PyTorch (DCP `async_save`, or his own pinned-memory staging) · MLSYS, OS, TEST, LIT · **L2–L3** · 6 h → 5 blocks.
- **Split:** teammates ship the trainer with sync checkpoints. He writes the staging, background persist, atomic commit (temp dir + rename + fsync), and a kill-during-write test.
- **Reproduce target:** on a 0.5–1B model, training stall per checkpoint ≤ 0.2× sync; resume gives a bit-identical next-step loss; `kill -9` during persist never leaves "latest" pointing at a partial checkpoint (20/20 trials).
- **Risk:** low; ratio depends on PCIe vs. disk speed but stays large.

### P31 Find and fix data stalls in the training input pipeline
- **Source:** [Analyzing and Mitigating Data Stalls in DNN Training](https://www.vldb.org/pvldb/vol14/p771-mohan.pdf), Mohan, Phanishayee, Raniwala, Chidambaram, PVLDB 14(5) 2021 · ML systems / data.
- **Claim:** across 9 models on a Microsoft production cluster, training time is often dominated by data stalls (fetch + preprocessing); CoorDL cuts training time up to 5× vs. DALI on one server. *Verified.*
- **Niche:** CV/recsys training teams, ML platform.
- **Ticket:** "GPU utilization on the image trainer is 45%. Measure fetch, prep and compute rates separately (DS-Analyzer style), predict the speedup of each fix, then apply the best one."
- **Stack · Skills · Level · Size:** PyTorch DataLoader (DALI optional) · MLSYS, PERF, OBS, DATA, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship a ResNet-18 trainer on an ImageNet subset with a heavy JPEG + augmentation pipeline. He writes the three-rate profiler, the what-if prediction and the fix.
- **Reproduce target:** GPU utilization ≥ 85% (or epoch time ≥ 1.8× faster); his predicted speedup within ±20% of the measured one.
- **Risk:** low; JPEG decode easily starves a 4070 on 12 cores.

### P32 Filtered vector search with ACORN in our ANN service
- **Source:** [ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data](https://arxiv.org/abs/2403.04871), Patel, Kraft, Guestrin, Zaharia, SIGMOD 2024; [reference implementation on FAISS](https://github.com/guestrin-lab/ACORN) · ML systems / DB.
- **Claim:** 2–1,000× higher throughput at fixed recall than prior filtered-search methods, including complex multi-modal predicates. *Verified.*
- **Niche:** vector DBs and RAG platforms with tenant/category/price filters.
- **Ticket:** "We post-filter top-k and recall collapses for selective filters. Compare post-filter, pre-filter brute force and ACORN; ship the winner behind a flag."
- **Stack · Skills · Level · Size:** C++/Python (FAISS-based ACORN) or Rust on top of his own index · MLSYS, DB, PERF, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the ANN service, 1 M vectors with attributes and ground truth. He writes the predicate path, the benchmark across selectivities and the recommendation.
- **Reproduce target:** at 1% selectivity, recall@10 ≥ 0.9 at ≥ 5× the QPS of pre-filter brute force, and recall ≥ 0.3 above post-filter at equal QPS.
- **Risk:** medium; gains depend on predicate–vector correlation. Allowed by BRIEF rule 2 ("add filtered search to our ANN service" is a different deliverable from building HNSW).

### P33 Near-duplicate removal and eval-leak check (MinHash-LSH)
- **Source:** [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499), Lee et al., ACL 2022 · ML / data.
- **Claim:** one 61-word sentence repeats > 60,000 times in C4; deduplicated models emit memorized text 10× less often; train–test overlap affects > 4% of standard validation sets. *Verified.*
- **Niche:** data-platform and fine-tuning teams.
- **Ticket:** "We suspect our eval set leaks into the fine-tuning corpus. Add MinHash-LSH near-dup detection to the pipeline; dedup train vs. eval and within train; report the overlap."
- **Stack · Skills · Level · Size:** Python (datasketch) or Rust for speed · DATA, ML, PERF, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship the corpus and 2,000 planted near-duplicate pairs. He writes shingling, MinHash, banding, the verification step and the report.
- **Reproduce target:** at Jaccard ≥ 0.8, precision ≥ 0.95 and recall ≥ 0.9 on planted pairs; ≥ 5k docs/s on 12 cores.
- **Risk:** low.

### P34 Find label errors in the test set (confident learning)
- **Source:** [Confident Learning](https://arxiv.org/abs/1911.00068), Northcutt, Jiang, Chuang, JAIR 2021; [Pervasive Label Errors in Test Sets](https://arxiv.org/abs/2103.14749), Northcutt, Athalye, Mueller, NeurIPS 2021 D&B · ML / data.
- **Claim:** ≥ 3.3% label errors on average across 10 popular test sets (≥ 6% of ImageNet val); 51% of flagged candidates confirmed by humans; on corrected labels, smaller models can outrank larger ones. *Verified.*
- **Niche:** any team whose model choice rests on a contractor-labelled test set.
- **Ticket:** "Our ticket classifier leaderboard flips week to week. Run confident learning over the test set, review the top 100 flags with a teammate, re-rank models on the cleaned set."
- **Stack · Skills · Level · Size:** Python + cleanlab + scikit-learn · ML, DATA, LIT · **L1–L2** · 4 h → 3 blocks.
- **Split:** teammates ship the dataset (with 5% planted noise), two candidate models and out-of-sample probabilities. He runs CL, reviews flags, re-ranks, writes the note.
- **Reproduce target:** precision of flagged set ≥ 0.6 at recall ≥ 0.5 on planted errors; ranking change reported with bootstrap CIs.
- **Risk:** low. Different deliverable from his fine-tuned classifier: data audit, not training.

### P35 Position-bias audit of our LLM-as-judge
- **Source:** [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685), Zheng et al., NeurIPS 2023 D&B · ML / evals.
- **Claim:** strong judges reach > 80% agreement with humans (human–human level), but show position, verbosity and self-enhancement biases; MT-bench questions and 3K expert votes are public. *Verified.*
- **Niche:** eval-platform and LLM-app teams running judges in CI.
- **Ticket:** "Our CI uses a local 8B model as a pairwise judge. Measure its position and verbosity bias, add swap-and-agree, and report agreement with the public expert votes."
- **Stack · Skills · Level · Size:** Python + vLLM/Ollama (8B at 4-bit) · ML, TEST, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the judge prompt and harness. He writes the bias measurements, the mitigation, the agreement analysis.
- **Reproduce target:** reports the swap-consistency rate; with swap-and-agree, position-flip rate drops ≥ 50% and agreement with non-tie expert votes doesn't fall.
- **Risk:** low-medium; an 8B judge agrees with humans less than GPT-4 did, but the bias pattern should reproduce.

### P36 Temperature scaling for confidence-based escalation
- **Source:** [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), Guo, Pleiss, Sun, Weinberger, ICML 2017 · ML.
- **Claim:** modern deep nets are poorly calibrated; temperature scaling, a one-parameter Platt variant, is "surprisingly effective" on most datasets. *Verified.*
- **Niche:** any product routing low-confidence predictions to humans (support, moderation, fraud).
- **Ticket:** "The intent router escalates when confidence < 0.7, but it's overconfident and misses errors. Calibrate on a held-out split and set the threshold by target precision."
- **Stack · Skills · Level · Size:** Python + PyTorch · ML, TEST, LIT · **L1** · 3 h → 2 blocks.
- **Split:** teammates ship the model and splits. He writes ECE, the temperature fit, reliability plots and the threshold choice.
- **Reproduce target:** ECE drops ≥ 50% on test; accuracy unchanged; chosen threshold hits target precision 0.95 ± 0.02 on test.
- **Risk:** low; fine-tuned transformers may be less miscalibrated than 2017 CNNs — say so if so.

## 1C. Cross-domain

Ideas born in another field (epidemiology, physics, control theory,
operations research, economics, biology, biostatistics, clinical-trial
statistics, computer vision) that a software company has applied or would
plausibly apply. The "domain of origin" line says where the idea came from.

### P37 Gossip membership with SWIM + Lifeguard for the cache cluster
- **Source:** [SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol](https://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf), Das, Gupta, Motivala, DSN 2002; [Lifeguard: Local Health Awareness for More Accurate Failure Detection](https://arxiv.org/abs/1707.00788), Dadgar, Phillips, Currey (HashiCorp), 2017; production: [Consul gossip docs](https://developer.hashicorp.com/consul/docs/architecture/gossip) cite both · **origin: epidemiology** (infection-style spread).
- **Claim:** SWIM's expected time to first detection and per-member message load don't grow with group size; membership changes spread epidemically by piggybacking; a suspicion phase cuts false positives. Lifeguard "drastically reduces" false positives caused by a slow local detector while also reducing detection time. *Verified.*
- **Niche:** cache clusters, service discovery, edge fleets.
- **Ticket:** "All-to-all heartbeats flood the network at 200 nodes, and a node in a long GC pause marks healthy peers dead (flapping). Implement SWIM with suspicion and Lifeguard's local-health multiplier."
- **Stack · Skills · Level · Size:** Go (the niche's membership libraries are Go) · DIST, NET, TEST, PERF, LIT · **L3** · 10 h → 8 blocks.
- **Split:** teammates ship an in-process network simulator (loss, delay, CPU starvation) and the node shell. He writes probe/ping-req/suspect/confirm, piggyback dissemination, the local-health score, and the experiments.
- **Reproduce target:** messages per member per period constant (± 15%) as N goes 25 → 200; detection time of a crashed node roughly flat in N; with one CPU-starved node, Lifeguard cuts false-positive declarations ≥ 5× vs. plain SWIM.
- **Risk:** medium-low. Protocol-level properties reproduce in simulation; real-network effects don't (say so).

### P38 Vivaldi network coordinates for nearest-replica routing
- **Source:** [Vivaldi: A Decentralized Network Coordinate System](https://pdos.csail.mit.edu/papers/vivaldi:sigcomm/paper.pdf), Dabek, Cox, Kaashoek, Morris, SIGCOMM 2004; production: Consul computes [network coordinates](https://developer.hashicorp.com/consul/docs/architecture/coordinates) via Serf gossip (*the docs say "network tomography"; that it is Vivaldi is unverified on that page*) · **origin: physics** (hosts relax as masses on springs).
- **Claim:** a 2-D Euclidean model with height vectors predicts RTT among 1,740 Internet hosts with 11% median relative error; nodes converge from a few peers' measurements, piggybacked on normal traffic. *Verified.*
- **Niche:** multi-region edge/CDN, geo-distributed DB replica selection.
- **Ticket:** "We pick the 'nearest' replica by region tag, and some cities get routed badly. Add Vivaldi coordinates on existing RPCs and route by predicted RTT."
- **Stack · Skills · Level · Size:** Go · NET, DIST, PERF, LIT · **L2** · 6 h → 5 blocks.
- **Split:** teammates ship an RTT-matrix simulator (geo-based matrix with noise and triangle-inequality violations; a public measured matrix if one is found). He writes the spring update with adaptive timestep, the height vector, the routing rule and the error analysis.
- **Reproduce target:** median relative error ≤ 15% after convergence (paper: 11%); predicted-nearest replica within 20% of the true nearest's RTT in ≥ 90% of queries.
- **Risk:** low on a synthetic matrix; real-Internet error depends on the data.

### P39 Kalman-filter CPU limits for the vertical autoscaler
- **Source:** "Self-Adaptive and Self-Configured CPU Resource Provisioning for Virtualized Servers Using Kalman Filters", Kalyvianaki, Charalambous, Hand, ICAC 2009 ([ACM](https://dl.acm.org/doi/10.1145/1555228.1555261)); extended in ACM TAAS 9(2) 2014 ([listing](https://www.cl.cam.ac.uk/~ek264/)) · **origin: control theory / state estimation.**
- **Claim:** a Kalman filter tracks each VM's true CPU need from noisy utilization samples and sets allocations with small, self-tuned headroom that adapts to workload changes. *Titles/venues verified on the author's page; numeric results not checked (ACM page blocked).*
- **Niche:** container platforms, Kubernetes vertical autoscaling, inference-pod right-sizing.
- **Ticket:** "Our VPA sets CPU limits at last-hour p95 + 30%: bursty services get throttled, steady ones waste cores. Prototype a Kalman-filter allocator and compare on replayed utilization traces."
- **Stack · Skills · Level · Size:** Python (numpy) on [Azure public VM traces](https://github.com/Azure/AzurePublicDataset) · INFRA, OBS, PERF, ML, LIT · **L2–L3** · 6 h → 5 blocks.
- **Split:** teammates ship the trace replayer and the p95+30% baseline with throttle/waste accounting. He writes the filter (process/measurement noise, adaptive variant), the allocation rule, the comparison.
- **Reproduce target:** on 50 replayed VM CPU traces, at equal or lower throttled-time fraction, allocated-but-unused CPU ≥ 20% lower than the baseline.
- **Risk:** low; trace-driven.

### P40 Adaptive concurrency limits borrowed from TCP congestion control
- **Source:** [Netflix/concurrency-limits](https://github.com/Netflix/concurrency-limits) (README: concurrency limit ≈ TCP congestion window; Little's law; Vegas and Gradient2 limiters); Netflix tech blog "Performance Under Load", 2018 (*page blocked to the fetcher; unverified*) · **origin: control theory via TCP congestion control.**
- **Claim:** limit concurrency, not RPS (Limit = RPS × latency); Vegas estimates queueing as L·(1 − minRTT/sampleRTT) and nudges the limit; Gradient2 compares long- and short-term latency averages to detect queueing. *Verified (README).*
- **Niche:** API gateways, service meshes, LLM gateways in front of GPUs.
- **Ticket:** "Our static max-concurrency of 200 is wrong after every deploy. Port a Gradient2/Vegas limiter to the Python gateway and show it finds the knee."
- **Stack · Skills · Level · Size:** Python (asyncio) · PERF, OBS, DIST, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship a backend with a tunable capacity knee and the load generator. He writes the limiter, load shedding, and the convergence/overload tests.
- **Reproduce target:** converges to within ± 20% of the knee in ≤ 60 s; at 2× overload, admitted-request p99 ≤ 2× unloaded p99 (static limit: ≥ 10×).
- **Risk:** low.

### P41 Shortest-job-first for LLM requests via a learned ranker
- **Source:** [Efficient LLM Scheduling by Learning to Rank](https://arxiv.org/abs/2408.15792), Fu, Zhu, Su, Qiao, Stoica, Zhang, 2024 (NeurIPS 2024 per authors — venue not on the arXiv page) · **origin: queueing theory / operations research** (SJF/SRPT minimize mean response time).
- **Claim:** exact output lengths can't be predicted but their ranking can; approximating SJF this way gives 2.8× lower latency for chatbot serving and 6.5× higher throughput for synthetic-data generation vs. FCFS. *Verified.*
- **Niche:** LLM APIs with mixed short/long generations.
- **Ticket:** "Under FCFS, short chat replies wait behind 2,000-token essays. Train a small ranker on prompts, schedule by predicted rank, and add starvation protection."
- **Stack · Skills · Level · Size:** Python (small encoder ranker + discrete-event simulator; optional run against vLLM) · MLSYS, ML, SD, PERF, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship a public chat-prompt set with response lengths, the simulator with FCFS, and a GPU-backed replay script. He trains the ranker, writes the scheduler and starvation guard, runs the evaluation.
- **Reproduce target:** ranker Kendall's τ ≥ 0.5 on held-out prompts; mean latency ≥ 1.5× lower than FCFS; no request waits more than 5× its FCFS wait.
- **Risk:** medium; gains scale with output-length variance, which the replayed set fixes.

### P42 Auction-based, finish-time-fair GPU scheduling (Themis)
- **Source:** [Themis: Fair and Efficient GPU Cluster Scheduling](https://www.usenix.org/conference/nsdi20/presentation/mahajan), Mahajan et al., NSDI 2020; trace: [Microsoft Philly traces](https://github.com/msr-fiddle/philly-traces) · **origin: mechanism design / auctions.**
- **Claim:** jobs bid for offered GPUs in a partial-allocation auction; "finish-time fairness" improves by > 2.25× and cluster efficiency by ~5–250% vs. state-of-the-art schedulers on a production trace. *Verified.*
- **Niche:** internal ML platforms sharing a GPU cluster across teams.
- **Ticket:** "Teams say the GPU queue is unfair: long jobs starve. Build a trace-driven simulator comparing FIFO, a DRF-style policy and a Themis-style auction; recommend one."
- **Stack · Skills · Level · Size:** Python simulator · SD, MLSYS, DIST, COMM, LIT · **L4** · 12 h → 9 blocks.
- **Split:** teammates ship the trace loader and a FIFO simulator with a simple placement-penalty model. He writes the auction, the fairness metric ρ, the other policies and the design doc.
- **Reproduce target:** on the trace scaled to 64 simulated GPUs, max finish-time-fairness ρ improves ≥ 1.5× vs. FIFO with ≤ 10% worse average JCT.
- **Risk:** medium; gains depend on how placement sensitivity is modelled — a design-review pushback hook.

### P43 Dominant Resource Fairness for the CPU/RAM/GPU job queue
- **Source:** [Dominant Resource Fairness: Fair Allocation of Multiple Resource Types](https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types), Ghodsi, Zaharia, Hindman, Konwinski, Shenker, Stoica, NSDI 2011 (classic) · **origin: economics / fair division.**
- **Claim:** equalizing each user's *dominant* share gives sharing incentive, strategy-proofness, envy-freeness and Pareto efficiency; worked example: 9 CPUs/18 GB, A's tasks ⟨1 CPU, 4 GB⟩, B's ⟨3 CPU, 1 GB⟩ → A runs 3 tasks, B runs 2. *Title/authors verified; properties and example from the paper body, not re-checked today.*
- **Niche:** CI runners, batch/training job queues.
- **Ticket:** "Slot-based sharing lets GPU-heavy teams hog GPUs while CPU-heavy teams wait. Replace slots with DRF across CPU, RAM and GPU."
- **Stack · Skills · Level · Size:** Python or Go · SD, TEST, CODE, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the queue and resource model. He writes progressive filling, property tests (strategy-proofness, envy-freeness) and the comparison.
- **Reproduce target:** reproduces the paper's worked example exactly; 1,000 randomized scenarios: no user gains by misreporting demand; no envy.
- **Risk:** none.

### P44 Karma credits for multi-tenant cache memory
- **Source:** [Karma: Resource Allocation for Dynamic Demands](https://www.usenix.org/conference/osdi23/presentation/vuppalapati), Vuppalapati, Fikioris, Agarwal, Cidon, Khandelwal, Tardos, OSDI 2023 · **origin: economics / mechanism design** (credits, strategy-proofness).
- **Claim:** max-min fairness loses its guarantees when demands change; Karma adds memory via credits (donate idle share, earn credits; spend to borrow) and is proven Pareto-efficient, online strategy-proof and optimally fair; production workloads show minimal disparity at Pareto-optimal performance. *Verified (no numbers in abstract).*
- **Niche:** multi-tenant caches, shared memory pools, shared KV-cache budgets in LLM serving.
- **Ticket:** "Static per-tenant cache quotas waste memory, and max-min sharing lets bursty tenants game it. Prototype Karma for our cache and compare with static and max-min on tenant demand traces."
- **Stack · Skills · Level · Size:** Python simulator, then Go integration · SD, DIST, TEST, LIT · **L3** · 8 h → 6 blocks.
- **Split:** teammates ship the demand traces and the static/max-min simulators. He writes the credit ledger, the allocation round, the strategy test.
- **Reproduce target:** utilization ≥ max-min's; disparity (max/min of per-tenant cumulative allocation ÷ fair share) ≥ 2× lower than max-min; a tenant that over-reports demand gains nothing over 1,000 random traces.
- **Risk:** low (simulation).

### P45 Spot instances under deadlines (Uniform Progress)
- **Source:** [Can't Be Late: Optimizing Spot Instance Savings under Deadlines](https://www.usenix.org/conference/nsdi24/presentation/wu-zhanghao), Wu et al., NSDI 2024 (Outstanding Paper) · **origin: operations research / online decision-making.**
- **Claim:** Uniform Progress (parameter-free) halves greedy's gap to the optimal policy in average and worst case; on SkyPilot, 27–84% cost savings; 3 months of AWS spot traces open-sourced. *Verified.*
- **Niche:** ML training/fine-tuning platforms, batch compute brokers.
- **Ticket:** "Nightly fine-tunes must finish by 8 am, so we pay on-demand. Implement Uniform Progress over spot with on-demand fallback and replay the paper's spot traces."
- **Stack · Skills · Level · Size:** Python simulator · MLSYS, INFRA, SD, LIT · **L2–L3** · 6 h → 5 blocks.
- **Split:** teammates ship the trace replayer and greedy/on-demand baselines (with restart overhead). He writes Uniform Progress, the deadline-safety check and the cost analysis.
- **Reproduce target:** 0 deadline misses; cost ≤ greedy's on ≥ 80% of (trace, deadline) pairs; mean cost ≥ 25% below on-demand-only.
- **Risk:** low; trace-driven, same setting as the paper.

### P46 Honey-bee allocation of GPU replicas across model endpoints
- **Source:** "On Honey Bees and Dynamic Server Allocation in Internet Hosting Centers", Nakrani & Tovey, *Adaptive Behavior* 12(3–4), 2004 ([DOI](https://doi.org/10.1177/105971230401200308); *publisher page blocked, title from DOI record*); [Golden Goose Award 2016](https://www.goldengooseaward.org/01awardees/honey-bee-algorithm) · **origin: biology / behavioural ecology** (forager allocation by waggle dance).
- **Claim:** servers act as foragers and client demand as flower patches; in tests it beat a state-of-the-art method and, under highly variable demand, an omniscient benchmark (which pays switching costs). *Verified via the award page.*
- **Niche:** model-serving platforms reassigning GPU replicas between endpoints; multi-tenant hosting.
- **Ticket:** "We reassign replicas hourly from a forecast; demand shifts faster. Prototype the honey-bee allocator and compare with hourly greedy and an omniscient oracle, switching costs included."
- **Stack · Skills · Level · Size:** Python simulator · SD, PERF, LIT · **L2–L3** · 6 h → 5 blocks.
- **Split:** teammates ship the simulator, demand traces (stable and bursty) and the baselines. He writes the dance-floor recruitment rule, its tuning and the memo on when it loses.
- **Reproduce target:** on bursty traces, revenue ≥ hourly greedy and ≥ 90% of the oracle; the memo shows where it loses on stable traces.
- **Risk:** medium; results depend on the switching-cost model — that's the discussion.

### P47 Counting quotient filter (from genomics) for hot-key counting
- **Source:** "A General-Purpose Counting Filter: Making Every Bit Count", Pandey, Bender, Johnson, Patro, SIGMOD 2017 ([code + citation](https://github.com/splatlab/cqf)) · **origin: bioinformatics** (built for k-mer counting in genome data; the k-mer link is from the authors' later work and *unverified here*).
- **Claim:** approximate membership plus counting that is small, fast, cache-local and scales from RAM to SSD, with deletes, resizing, merging and concurrent access. *Verified (README); the paper's numeric comparisons not checked.*
- **Niche:** API gateways and CDNs (hot keys, abuse), streaming analytics.
- **Ticket:** "Our hot-key detector uses a count-min sketch that overestimates rare keys and can't delete, so the sliding window is a hack. Evaluate a CQF on our key stream: error vs. memory, deletes for window expiry, throughput."
- **Stack · Skills · Level · Size:** C library via Python bindings, or Rust · DATA, PERF, DB, LIT · **L3** · 6 h → 5 blocks.
- **Split:** teammates ship the key stream and the CMS baseline. He integrates the CQF, writes the sliding-window expiry and the accuracy/throughput benchmark.
- **Reproduce target:** Zipf stream (100 M events, 10 M keys), equal memory: CQF count error for keys with true count ≥ 1,000 ≤ CMS's; exact deletes; insert throughput reported against CMS.
- **Risk:** low.

### P48 Sequential testing for canary analysis
- **Source:** [Rapid Regression Detection in Software Deployments through Sequential Testing](https://arxiv.org/abs/2205.14762), Lindon, Sanden, Shirikian (Netflix), KDD 2022; Netflix tech blog "Sequential A/B Testing Keeps the World Streaming Netflix", 2024 (*page blocked; unverified*) · **origin: clinical-trial statistics** (sequential analysis with interim looks).
- **Claim:** sequential tests of stochastic order and of equality in distribution let canaries be monitored continuously, catching regressions fast while "strictly controlling the false detection probability throughout"; two Netflix case studies. *Verified.*
- **Niche:** CD/deploy platforms, experimentation platforms.
- **Ticket:** "Our canary judge runs a t-test at 30 min, but engineers peek every 5 min and roll back on noise. Replace it with an anytime-valid sequential test so we can stop early safely."
- **Stack · Skills · Level · Size:** Python (scipy) · OBS, TEST, INFRA, ML, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship the canary metric simulator and current judge. He writes the sequential test, the A/A false-alarm study and the detection-time study.
- **Reproduce target:** A/A with continuous peeking: false-alarm rate ≤ 5% (fixed t-test with peeking: ≥ 20%); injected 5% latency regression: median detection time ≤ 0.5× the fixed-horizon test.
- **Risk:** low; statistics don't care about scale.

### P49 Survival analysis for drive replacement and spares
- **Source:** [Failure Trends in a Large Disk Drive Population](https://www.usenix.org/conference/fast-07/failure-trends-large-disk-drive-population), Pinheiro, Weber, Barroso (Google), FAST 2007; data: [Backblaze Hard Drive Data](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data) (daily SMART snapshots, 2013 → Q2 2026, open with attribution) · **origin: biostatistics** (Kaplan–Meier, Cox proportional hazards).
- **Claim:** several SMART parameters correlate strongly with failure, but "models based on SMART parameters alone are unlikely to be useful for predicting individual drive failures"; temperature and activity matter far less than believed. *Verified.*
- **Niche:** storage infra, bare-metal fleets (DB vendors, CDNs, GPU clouds).
- **Ticket:** "Ops replaces drives at five years. Fit survival models on the Backblaze data and propose risk-based replacement plus a spares forecast."
- **Stack · Skills · Level · Size:** Python (DuckDB + lifelines) · DATA, ML, OBS, LIT · **L2** · 8 h → 6 blocks.
- **Split:** teammates ship the DuckDB ingestion for two years of data. He builds the survival table (censoring!), fits KM and Cox, writes the forecast and memo.
- **Reproduce target:** time-based split (train ≤ 2024, test 2025): concordance ≥ 0.70 on held-out drives; spares forecast within ± 20% of actual failures in the test quarter; memo restates the paper's caveat about individual prediction.
- **Risk:** low-medium; data volume (multi-GB) — restrict to a few models.

### P50 Spectral-residual anomaly scoring for metrics alerts
- **Source:** [Time-Series Anomaly Detection Service at Microsoft](https://arxiv.org/abs/1906.03821), Ren et al., KDD 2019; benchmark: [Numenta Anomaly Benchmark](https://github.com/numenta/NAB) · **origin: computer vision** (spectral residual from visual saliency detection).
- **Claim:** borrowing spectral residual from visual saliency (plus a CNN) beats state-of-the-art baselines on public data and Microsoft production metrics; deployed as a monitoring service. *Verified (no F1 numbers in abstract).*
- **Niche:** observability platforms.
- **Ticket:** "Static thresholds drown on-call in pages. Prototype SR (the unsupervised part, no CNN) as an anomaly scorer and evaluate it on labelled public data against our rolling z-score."
- **Stack · Skills · Level · Size:** Python (numpy FFT) · OBS, ML, DATA, LIT · **L2** · 5 h → 4 blocks.
- **Split:** teammates ship NAB loading and the z-score baseline. He writes SR, thresholding, the evaluation with event-level scoring.
- **Reproduce target:** on two NAB categories, event-level F1 ≥ z-score's + 0.05; scoring ≤ 1 ms/point.
- **Risk:** medium; anomaly benchmarks are noisy and point-adjusted F1 inflates results — make him use event-level scoring and say why.

## 2. The "paper task" format

The formats below line up one-to-one with the six LIT harness checks in
[01 §1.3](01-hiring-and-skills.md) and its LIT-by-level ladder (01 §2).

| 01 LIT check | Variant here | Harness task type | First level (01) |
|---|---|---|---|
| Scaled-down reproduction within X%, deviations list, ablation | **A Reproduce** | experiment / perf-hunt | L1 toy (teammate-scoped), L2 on his own |
| "Should we adopt this?" memo with a planted assumption that fails on our data | **C Adopt memo** | design-review | L3 (L2 with a guide) |
| Prediction calibration | **cross-cutting** (A, B, C) | — | every level; L4 gate: within 2× |
| Paper → flagged PR → benchmark | **B Apply** | add-your-part / build / perf-hunt | L3–L4 |
| Critical-reading quiz, incl. a synthetic paper with a planted flaw | **D Critical read** | gate before A/B/C; also 01's placement test F | L1 |
| Blog/postmortem transfer | **E Transfer** | incident follow-up / design-review | L1–L2 |

The variants form a ladder on the same seed: **D → C → A → B**, with E
used for blog-sourced seeds. A memo's predicted gain becomes the
hypothesis of the next reproduce/apply ticket.

### 2.1 Common kit (every paper task)

- **Reading guide** from the tech lead: which sections matter, which to
  skip, the figures that carry the claim.
- **Worked example on a different paper**: a memo or reproduction report
  the team wrote earlier. He learns by example, so the model answer is
  always for a *parallel* paper, never the one he's on.
- **`system.md`**: our workload, hardware, SLOs and traffic mix, with **one
  planted fact that breaks one of the paper's key assumptions** (e.g. "we
  already use FlashAttention" for P29; "PCIe-only fleet on 25 GbE" for
  P25; "80% of prompts are under 200 tokens" for P24).
- **`PREDICTION.md`** (see 2.2).

### 2.2 Prediction calibration (cross-cutting)

Before building or running anything, he commits `PREDICTION.md`: a gain
*range* (low/high) for our workload, derived from `system.md` numbers, plus
the reasoning. The harness:
- checks the git timestamp is before the first results commit;
- logs (predicted range, measured) per task and scores
  |log(midpoint ÷ measured)|, tracked across tasks like EXEC's estimate
  error;
- counts a correct "no gain for us" prediction as a hit;
- uses 01's gate: at L4, the prediction must be within 2× of measured.

### 2.3 Variant A — Reproduce

"Before we spend a sprint on this, show the claimed effect exists on our
kind of workload."

Deliverables: `PREDICTION.md`, the experiment code, `REPRO.md` (claim →
setup → our result vs. theirs → deviations → ablation → verdict).

| Check | How the harness grades it |
|---|---|
| Effect within X% | `make repro` runs baseline and treatment back to back, 3 repetitions, median ratio. **Pass line = the card's reproduce target**, already scaled to his hardware (some cards deliberately ask for less, e.g. P24's 1.3× vs. the paper's 2.6× on an A100). The harness also reports the fraction of the paper's relative gain achieved; where a card states no ratio, the default X comes from the claim class (table 2.8): **S** (scale-free: miss ratio, FPR, fairness, ordering) ≥ 80% of the paper's relative gain; **H** (hardware/scale-bound: throughput, latency, GPU memory) ≥ 50%, e.g. a reported 2× must reach ≥ 1.5×. |
| Ablation | One extra run with the key component removed (table 2.8). Pass if the gain drops to ≤ 25% of the full gain, i.e. the gain comes from the mechanism and not from a side effect. |
| Deviations list | ≥ 3 deviations from the paper's setup (scale, data, hardware, hyperparameters, versions), matched against the builder's key. |
| Fair baseline | The harness runs its own copy of the baseline; his must be within 10% of it (catches strawman baselines). |
| Honest numbers | Every figure attributed to the paper string-matches the paper's text or tables; result files match the logged runs. |
| Calibration | 2.2. |

### 2.4 Variant B — Apply (paper → flagged PR → benchmark)

"Port the technique into our codebase behind a flag."

| Check | How the harness grades it |
|---|---|
| Flag off = old behaviour | Golden/regression suite passes byte-for-byte with the flag off. |
| Benchmark on the company workload | Pass rule from 01: the gain meets the memo's predicted lower bound, **or** the memo correctly predicted no gain. For correctness seeds (class C), the fault-injection suite on the card passes. |
| Edge cases | Hidden tests built from the paper's own corner cases (SIEVE's hand wrap-around, HLC's counter overflow, XFetch as β → 0, DRF with a zero-demand user). |
| Review | The AI tech lead posts 2–3 review comments, one deliberately wrong; he fixes the valid ones and pushes back on the wrong one with evidence. |
| Ownership change | A small unaided follow-up (e.g. "export a metric for the hedge rate") graded by tests. |

### 2.5 Variant C — Adopt memo + team discussion (the light variant)

1–3 blocks. "A teammate posted this paper in #infra. Should we adopt it?"

**Memo (one page, ≤ ~500 words), sections fixed to 01's rubric:**
1. Claim, mechanism, and **evidence quality** (self-reported? one workload?
   baseline strength? replicated?).
2. **Assumptions table**: assumption | holds / doesn't hold for us | our
   number from `system.md`.
3. **Predicted gain range** for us (feeds 2.2).
4. Risks and cost.
5. **Decision** (adopt / pilot behind a flag / reject) and **the cheapest
   experiment that would confirm it**.

**Team discussion.** Three AI teammates reply in a review thread (text or
voice): a skeptical tech lead, a peer who over-claims, a PM asking about
cost. Exactly one objection is valid by design.

| Check | How the harness grades it |
|---|---|
| Planted trap caught | Binary, required to pass: the memo marks the assumption `system.md` breaks as "doesn't hold". |
| Assumption recall | ≥ 3 of the builder's (typically 5) key assumptions, each backed by a verbatim quote from the paper (string-checked). |
| Evidence quality | Names ≥ 2 weaknesses from the builder's key (e.g. P22's numbers are self-reported on one workload). |
| Numbers are real | Any figure attributed to the paper string-matches the paper. |
| Predicted range | Overlaps the builder's range computed from the same `system.md`. |
| Cheapest experiment | ≤ 1 day of work and targets the riskiest assumption (rubric). |
| Discussion | Each objection answered with evidence; he concedes the valid one and holds on the others (grader rubric with the builder's key). |

Optional **paper talk** (COMM, L5 per 01): a 5-minute recorded summary,
scored on the same claim/mechanism/assumption rubric.

### 2.6 Variant D — Critical-reading quiz (with a synthetic flawed paper)

20–30 min, click questions only (no typing), auto-scored.

1. **Real paper (6 clicks, 01's placement-test format F):** the claim, the
   baseline, the metric, the figure that carries the claim, one assumption
   that fails for our workload, the expected gain direction for us.
2. **Synthetic paper:** the harness generates a 2-page "paper" from a
   seed's real paper with **one planted flaw** from the catalog below. He
   clicks the flawed passage, picks the flaw type, and picks the fix from 4
   options.

| Planted flaw | Seed-linked example the generator can use |
|---|---|
| Leaky split | Temperature fitted on the test set (P36); dedup run within train but not train-vs-eval (P33) |
| Weak / unequal baseline | Lock-free SIEVE vs. an LRU behind one global mutex, sold as "the algorithm is faster" (P01); FCFS baseline run at a different batch size than the ranker (P41) |
| Cherry-picked metric | Point-adjusted F1 for anomaly detection (P50); mean latency reported, p99 omitted (P03) |
| Favourable regime only | Learned index tested only on dense read-only arrays (P14, cf. SOSD); mmap benchmark with the file smaller than RAM (P15) |
| No variance / single seed | One run, 3% speedup, no error bars (P31) |
| Unequal resource budget | Filters compared at different bits/key (P13); judge "bias-free" because only one answer order was ever tested (P35) |
| Censoring ignored | Still-running drives counted as "survived forever" (P49) |
| Peeking | Fixed-horizon test checked every 5 minutes (P48) |

Score: flaw located and typed correctly; fix chosen correctly. Gate: L1
must pass D on a seed before starting its A or C task.

### 2.7 Variant E — Blog / postmortem transfer

30–60 min, L1–L2. Given a real post and `system.md`, he lists the post's
lessons and marks each **applies / doesn't apply / needs measurement**,
citing the `system.md` fact that decides it. Scored against the builder's
answer key (5–8 lessons): precision and recall of "applies", and every
"doesn't apply" must cite its deciding fact. The top applicable lesson
becomes his next B ticket.

Blog-sourced seeds that fit E: P02 (Discord), P05 (Vimeo / Google
Research), P06 (Brooker, AWS; plus the incident reports catalogued by
Metastable Failures in the Wild), P09 (Kleppmann), P10 (Stripe /
brandur), P13 (RocksDB blog), P19 (PlanetScale), P20 (Russ Cox), P22 and
P27 (LMSYS), P30 (PyTorch/IBM), P40 (Netflix concurrency-limits).

### 2.8 Per-seed claim class and ablation

Class: **S** = scale-free (pass at ≥ 80% of the paper's relative gain),
**H** = hardware/scale-bound (≥ 50%), **C** = correctness (binary
fault-injection pass; the "ablation" is removing the fix), **M** = memo
only.

| ID | Class | Ablation (key component removed → gain should vanish) |
|---|---|---|
| P01 | S / H | Visited bit off (SIEVE → FIFO) for miss ratio; SIEVE behind a global lock for throughput |
| P02 | C | Coalescing and early refresh off → recomputations ≈ client count |
| P03 | H | Hedge lands on the same throttled host (correlated slowness) |
| P04 | H | Probing off (stale requests-in-flight only) → ≈ P2C |
| P05 | S | c = ∞ (plain ring) |
| P06 | H | Keep backoff + jitter, drop the token bucket (shows which part breaks the loop) |
| P07 | C | Bug flag off → Elle reports nothing (checker doesn't cry wolf) |
| P08 | C | Fault injector off → bug not found in 10k seeds |
| P09 | C | Token check removed from the ledger write |
| P10 | C | Recovery point written outside the phase's transaction |
| P11 | C | Receive rule ignores the remote timestamp |
| P12 | S | Load the full CRDT state instead of the event graph |
| P13 | S | Bloom filter at the same bits/key |
| P14 | S | One coarse model (ε very large); `osm` dataset |
| P15 | H | File smaller than the memory cap |
| P16 | H | Queue depth 1 per thread |
| P17 | C | LazyFS pass-through mode (no lost writes) → no failures |
| P18 | C | CTRL rules off |
| P19 | H | Index fits in `shared_buffers` |
| P20 | C | Verifier skips the consistency proof → fork undetected |
| P21 | S | Histogram off (fixed keep-alive only) |
| P22 | H | Prefix tree off (→ round-robin); balance guard off → hot-group p99 explodes |
| P23 | H | Batch 16; random draft model (acceptance ≈ 0) |
| P24 | H | Token budget ≥ longest prompt |
| P25 | M | — |
| P26 | S | Counters off (→ FCFS) |
| P27 | S | Constraint off |
| P28 | H | Small-vocabulary model (saving should shrink with vocab) |
| P29 | H | FlashAttention/SDPA on |
| P30 | H | Synchronous save |
| P31 | H | Decoded-data cache / extra workers off |
| P32 | H | Neighbour expansion off (plain graph + post-filter) at 1% selectivity |
| P33 | S | Exact-hash dedup instead of MinHash |
| P34 | S | No planted noise (precision should fall to the base rate) |
| P35 | S | Swap-and-agree off |
| P36 | S | Temperature fitted on the training split |
| P37 | S | Lifeguard off; suspicion off |
| P38 | S | Height vector off |
| P39 | S | Fixed-gain EWMA instead of the Kalman filter |
| P40 | S | Static limit |
| P41 | S | Random ranker (floor); oracle lengths (ceiling) |
| P42 | S | Bids ignored (FIFO) |
| P43 | C | Allocate by CPU share only |
| P44 | S | Credits off (→ max-min) |
| P45 | S | Greedy policy |
| P46 | S | Recruitment off (static allocation) |
| P47 | S | Count-min sketch at equal memory |
| P48 | S | Fixed horizon with peeking |
| P49 | S | Age-only Kaplan–Meier (no SMART covariates) |
| P50 | S | z-score on the raw series (no saliency step) |

## 3. Do employers value this?

The hiring agent covered this (01 §1.2 LIT row, §1.3 LIT); in brief:

- **Weight:** LIT is **M for AI infra (H in research-engineer, inference
  and training roles)** and **L→M for backend (H in query/storage-engine
  teams)**.
- **Explicit asks** ("read papers", "research to production", "reproduce
  published results"): 5% of AI-company and 2% of backend postings; 25% of
  research-engineer titles, 10% of ML-engineer titles, 6% of early-career
  postings. Examples: Fireworks Evals, "insist on rigorously reproducing
  published results internally"
  ([posting](https://jobs.ashbyhq.com/fireworks/cca38fd5-9cbd-4cee-8fdb-d6e6d230b036));
  Starburst, "you read papers and you ship code"
  ([posting](https://job-boards.greenhouse.io/starburst/jobs/5416956008));
  Coinbase ML intern, "a research-to-production project"
  ([posting](https://www.coinbase.com/careers/positions/8175441?gh_jid=8175441)).
- **Implicit demand is larger:** 38% of inference-serving and 33% of
  training postings name paper-born techniques (speculative decoding,
  chunked prefill, disaggregation, FSDP…), which is why P22–P30 exist.
- **No standard "implement the paper" interview round** for SWE; the payoff
  is portfolio evidence (a reproduction report or memo with real numbers).

**Implication for the catalogs:** AI-infra companies (02) get ≥ 2 paper
tasks each, at least one A or B on a P22–P32 seed; backend companies (03)
get ≥ 2 each, mostly B on correctness seeds (P07–P11, P17, P18) plus one C.
Use 01's cadence: one paper or blog a month at L1–L2 (D, E, toy A), the
full memo → flagged PR → benchmark loop from L2 → L3.

## 4. 10 best starter seeds (L1–L2)

Ordered so each one adds one new habit on top of the last.

| # | Seed | Level · size | Why this one, now |
|---|---|---|---|
| 1 | **P19** UUIDv7 keys | L1 · 3 h | Smallest possible "blog claim → our measurement": one Postgres box, one number, teaches baseline-vs-treatment discipline. |
| 2 | **P36** Temperature scaling | L1 · 3 h | Pure Python, his strongest language; first "paper claim → our metric on a held-out set". |
| 3 | **P05** Bounded-load hashing | L1–L2 · 4 h | First time reading a *guarantee* and checking it by simulation; no infra to fight. |
| 4 | **P02** Coalescing + XFetch | L1–L2 · 4 h | Real incident shape (stampede), a probability argument, and Redis/Postgres in compose. |
| 5 | **P27** Constrained JSON vs. "Let Me Speak Freely" | L1–L2 · 4 h | First adopt memo; two papers disagree, so he has to weigh evidence, not just cite it. First GPU task, low setup. |
| 6 | **P34** Confident learning | L1–L2 · 4 h | Data-quality audit with an existing library; shows how a paper changes a model-selection decision. |
| 7 | **P09** Fencing tokens | L2 · 5 h | First fault injection; deterministic pass/fail; a blog post, not a paper, as the source. |
| 8 | **P23** Speculative decoding memo | L2 · 6 h | AI-infra measurement where the paper's assumption (spare compute) visibly breaks as batch size grows. |
| 9 | **P48** Sequential canary testing | L2 · 5 h | First cross-domain idea (clinical-trial statistics); the "peeking" lesson transfers to every dashboard he'll read. |
| 10 | **P01** SIEVE / S3-FIFO | L2 · 6 h | First full reproduction on public traces, with a concurrency stretch goal that opens the L3 seeds. |

Natural next steps once these pass: P10 (idempotency), P24 (chunked
prefill), P11 (HLC), P30 (async checkpointing), then the L3 band (P06, P07,
P13, P17, P22).

## 5. From memory / not re-checked

The shared web-search budget ran out mid-run; everything below was either
taken from memory or could not be opened (fetcher blocked). Builders should
re-check these before a card quotes them to the learner.

**Claims seen only second-hand**
- P03: the Tail at Scale numbers (1,800 → 74 ms, +2% requests): CACM page
  blocked; quoted from course notes and summaries.
- P05: Vimeo's "almost 8×" cache-bandwidth cut: from Google Research's
  post; Vimeo's own Medium post blocked.
- P06: Fail at Scale's adaptive-LIFO + CoDel design: ACM Queue blocked;
  taken from The Morning Paper summary and HBase's
  `AdaptiveLifoCoDelCallQueue`.
- P19: Postgres 18's native `uuidv7()`: secondary write-ups only, not the
  official release notes.

**Pages blocked to the fetcher**
- P40: Netflix tech blog "Performance Under Load" (2018); the card relies on
  the Netflix/concurrency-limits README instead.
- P48: Netflix tech blog "Sequential A/B Testing Keeps the World Streaming
  Netflix" (2024); the card relies on the KDD 2022 paper instead.
- P39: the ICAC 2009 Kalman paper's numeric results (ACM DL blocked); its
  title and venue are confirmed on the first author's page.
- P46: the Nakrani & Tovey 2004 paper text (SAGE blocked); its title and
  venue come from memory plus the DOI, and its results from the Golden
  Goose Award page.

**Details from memory**
- Venues missing from the arXiv pages: Preble at ICLR 2025 (P22), Learning
  to Rank at NeurIPS 2024 (P41), selective recompute at MLSys 2023 (P29).
  Vidur (P25) is cited as arXiv only.
- P07: how widely Jepsen uses Elle across its analyses.
- P11: that HLC fits in a 64-bit timestamp.
- P12: that the paper's editing traces are public.
- P15 and P21: the numbers in the paper bodies (mmap figures; exact
  cold-start and memory percentages). Only the abstracts were read.
- P17: Docker flags for FUSE (`--device /dev/fuse --cap-add SYS_ADMIN`).
- P18: TigerBeetle's lineage from PAR.
- P23, P24 and P27: vLLM behaviour (draft-model vs. n-gram support,
  chunked prefill on by default in newer engines, the xgrammar structured-
  output backend). All depend on the pinned version.
- P28: that the CCE/Liger Triton kernels run under WSL2.
- P38: Consul's coordinates being Vivaldi (its docs say only "network
  tomography" via Serf). Also whether public measured RTT matrices (King,
  PlanetLab) are still downloadable.
- P39: that the Azure Public Dataset's VM traces contain per-VM CPU
  readings (the repo exists; its contents weren't opened).
- P43: DRF's four properties and its worked example (9 CPU / 18 GB) come
  from the paper body, which wasn't re-opened.
- P47: the CQF's origin in k-mer counting (Squeakr). The README doesn't
  mention it.

**Link status:** every other link returned HTTP 200 on 2026-10-19, except
the S3-FIFO author blog (timed out). The SGLang router docs moved (404), so
the card links the repo instead.
