# 01 — Hiring demand, skill map and leveling ladder

Domains covered: (1) AI/ML infrastructure and (2) backend and distributed systems.
Research date: 2026-10-19. This file builds on the hiring section of
`C:\Users\Owner\reports\RL frontier companies and projects.md` (lines 130–195:
undergrad doors, "reviewable, measured, owned work"). It does not repeat that
material; it cites it as **[RL report]**.

---

## 0. Evidence base and method

**Primary dataset: 3,056 live engineering postings.** On 2026-10-19 I pulled
the public job-board APIs (Greenhouse, Ashby, Lever) of 85 companies and kept
software-engineering titles. Sales, solutions, FDE, managers, hardware,
facilities and scientist roles were dropped, and postings were de-duplicated
by (company, title).

- **AI/ML infra companies (1,175 postings):** OpenAI, Anthropic, xAI, Together, Fireworks,
  Baseten, Modal, Anyscale, CoreWeave, Crusoe, Lambda, Nebius, RunPod, Cerebras,
  Etched, Cohere, Perplexity, Cursor, Scale, LangChain, LlamaIndex, Ollama,
  Pinecone, Weaviate, turbopuffer, LanceDB.
- **Backend / distributed-systems companies (1,881 postings):** Stripe, Coinbase,
  Robinhood, Affirm, Ramp, Plaid, Brex, Chime, Mercury, Modern Treasury,
  Databricks, MongoDB, ClickHouse, CockroachDB, SingleStore, Supabase, Neon,
  PlanetScale, Materialize, Yugabyte, TigerData, MotherDuck, Datadog, Grafana,
  Honeycomb, Sentry, Cribl, Elastic, Cloudflare, Vercel, GitLab, Temporal,
  Render, Railway, Tailscale, Fivetran, Airbyte, Astronomer, Prefect, Hex,
  Starburst, Imply, Airbnb, Discord, Figma, Pinterest, Reddit, Dropbox, Lyft,
  Instacart, Roblox, Samsara, Twilio, Notion, Linear, PostHog, Palantir,
  Spotify, Zoox.
- **Level** comes from the title: intern/new grad/early career/"Engineer I"/L3 →
  *early*; Senior → *senior*; Staff/Principal/Lead → *staff+*; everything else
  → *mid/unspecified*.
- **Percentages** are the share of postings whose text matches a keyword
  regex. Treat them as a proxy with some noise: phrases like "at scale" or
  "optimize" are generic, and a few non-software titles slipped through.
- The row-level data (company, level, niche, title, date, URL) is in
  [`01-postings-2026-10-19.csv`](01-postings-2026-10-19.csv) so other agents
  can reuse real titles.
- **Caveats.** Big companies often post university roles on separate campus
  portals, so early-career counts here are a floor. October is the main 2027
  intern season. A posting count measures demand, not hires.

**Secondary sources:**
- **Public career ladders:** Dropbox, CircleCI, GitLab, plus Google/Meta level
  mappings.
- **Interview-format evidence:** company blogs, candidate reports and prep
  sites; the weaker of these are marked.
- **2025–2026 market and AI-era reports:** Indeed Hiring Lab, Stanford Digital
  Economy Lab, SignalFire, NACE, Karat, LeadDev, Stack Overflow, DORA, and
  Anthropic's coding-skills trial.

---

## Top findings (detail below)

1. **Postings for juniors are rare and seniors get most of the demand.** Only
   **120 of 3,056 postings (3.9%)** are early-career. That is 2.0% at AI-infra
   companies and 5.2% at backend companies. At AI companies, postings with no
   level in the title are effectively senior: those that state a number ask for
   a median minimum of **5 years** (n=264). The macro data agrees.
   - Employment of 22–25-year-olds in AI-exposed jobs is **19% below** trend,
     and the drop comes through *fewer hires*
     ([Stanford DEL, rev. 2026-08-12](https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/)).
   - New grads are **7% of Big Tech hires**, down more than 50% from 2019
     ([SignalFire 2025](https://www.signalfire.com/blog/signalfire-state-of-talent-report-2025)).
   - NACE still projects **+5.6%** new-grad hiring for the class of 2026
     ([NACE spring 2026](https://naceweb.org/about-us/press/2026/outlook-brightens-for-college-class-of-2026-entry-level-hiring)).
2. **New-grad and senior postings ask for different things.**
   - **Early postings** ask for CS fundamentals (48% vs 9–10% at mid/senior),
     testing (45%), code review (28%) and AI-tool fluency (27%).
   - **Senior postings** add system design (21% early → 62% senior → 69%
     staff+), on-call/incidents (2% → 37%), observability (23% → 63%),
     distributed systems (16% → 40%) and mentoring others (1% → 18%).
   - **Staff+ postings** add technical leadership (1% → 16% → **40%**).
3. **"Use AI, and prove you understand the output" is now written into
   new-grad postings and interview loops.**
   - Vercel's intern posting: *"Use AI coding tools in your daily workflow,
     and can explain and debug every line you ship"*
     ([posting](https://job-boards.greenhouse.io/vercel/jobs/6181759004)).
   - Stripe early career: *"…applying rigorous critical thinking and
     professional judgement to review, refine, and validate all outputs"*
     ([posting](https://stripe.com/jobs/search?gh_jid=8212517)).
   - Meta's AI-enabled round has candidates fix a bug in, then extend, a
     multi-file codebase they did not write. Its internal bar, per prep-site
     sources: *"Should use AI, but need to show you understand the code"*
     ([Hello Interview](https://hellointerview.com/blog/meta-ai-enabled-coding)).
4. **Reading, debugging and reviewing code you didn't write are now tested
   directly.**
   - Stripe's "bug squash" and integration rounds (candidate reports).
   - Meta's phase-1 bug fix.
   - Anthropic's progressive CodeSignal build plus concurrency follow-ups, and a
     reported onsite where the candidate reviews four PRs with Claude Code
     (single report).
   - Dropbox's IC1 ladder already requires it: *"I'm capable of reading and
     navigating … a large codebase that I didn't write"*
     ([Dropbox IC1](https://dropbox.github.io/dbx-career-framework/ic1_software_engineer.html)).
5. **Python plus Go is the core language pair; the niche decides the third.**
   Python appears in 55% of AI-infra and 42% of backend postings, Go in 30% of
   each.
   - Inference serving adds **C++ 45% / Rust 32% / CUDA 30% / Triton 24%**.
   - Payments adds Java, Kotlin and Ruby.
   - Databases add Go, C++ and Rust.
   - Kubernetes (27–33%) is the most-requested infrastructure tool in both
     domains.
6. **Interview topics now include AI infrastructure.** Classic distributed
   design (caching, sharding, queues, contention, rate limiting, payments,
   metrics) is still the core. Prep catalogs now list LLM serving (time to first
   token (TTFT), batching, KV cache), batch inference and GPU scheduling, weight
   distribution and agent systems as their own category
   ([aced.io/Exponent 2026](https://www.aced.io/blog/how-to-nail-the-system-design-interview)).
7. **Over-delegating to AI measurably hurts debugging.** In Anthropic's
   randomized trial (n=52), the AI-assisted group scored **50% vs 67%** on a
   comprehension quiz, and the biggest gap was on debugging. Learners who
   asked *conceptual* questions kept their learning
   ([Anthropic, 2026-01-29](https://www.anthropic.com/research/AI-assistance-coding-skills)).
   The harness's AI teammates should coach, not hand over code, during
   learning tasks.
8. **Turning papers into production work is valued, but mostly implicitly.**
   - Explicit asks ("read papers", "research to production", "reproduce
     published results") appear in only **5% of AI-company** and **2% of
     backend** SWE postings. The share rises to **25% of research-engineer**
     and **10% of ML-engineer** titles.
   - But **38% of inference-serving** and **33% of training-infra** postings
     name techniques that came straight out of papers (speculative decoding,
     KV-cache paging, prefill/decode disaggregation, FSDP, GRPO/DPO).
   - This earns its own tag, **LIT** (§1.3), weighted M for AI infra and
     L→M for backend.

---

## 1. Skill taxonomy for the harness (21 skills)

### 1.1 Changes from the provisional tags

| Change | Why (evidence) |
|---|---|
| **All 16 provisional tags are kept**, so other agents' cards stay valid. | — |
| **+REVIEW** (split out of COMM): code review and verification of AI-written code. | Reviewing PRs is now an interview round (Anthropic report, JPMorgan merge request ([Hello Interview](https://www.hellointerview.com/community/questions/merge-request-review/cmh72k850011s08advgj5nxcs))). Code review appears in 28% of early and 21% of senior postings. "Validate all outputs" is a requirement in new-grad postings. Dropbox has review expectations at every level, from "raise questions" at IC1 to "surface hidden assumptions" at IC4. |
| **+CODE**: implementation craft and language fluency, including an AI-assisted workflow. | Every loop keeps at least one no-AI coding screen: Meta keeps one classic round; Cursor's screens allow only autocomplete **[RL report]**. Dropbox's "Code fluency" craft row runs IC1→IC7. |
| **+INFRA**: containers, Kubernetes, IaC, CI/CD, release safety. | Not in the provisional list, yet Kubernetes is in 33%/27% of postings (AI/backend), Docker/containers 21%/15%, Terraform 11%/12%, and a named cloud in 20–30%. |
| **+EXEC**: execution and ownership (scoping, estimates, incremental delivery, prioritization). | "Ownership" appears in 45–46% of postings, "end-to-end" in 34–38%, "ambiguity" in 23–27%. Dropbox's Results pillar is mostly about this. |
| **MLSYS** keeps GPU kernels as a sub-tag (`MLSYS.gpu`) instead of a new tag. | Kernel/compiler roles are a distinct niche (n=90, C++ 49%, CUDA 24%), but the provisional MLSYS already says "kernels". Sub-tags keep the count at 20. |
| **ML** absorbs LLM-application work (`ML.llmapp`: RAG, agents, evals). | "Agents" appears in 38% of AI and 35% of backend postings, and evals in 13%/5%. These are mostly product-side, so they fit with ML/eval work, not MLSYS. |
| **+LIT**: research literacy, i.e. reading papers and engineering blogs and turning them into production decisions. Added 2026-10-19 at the learner's request; this takes the count to 21. | Explicit asks are concentrated in research-engineer, ML-engineer and AI-infra roles; implicit demand runs through inference and training postings (top finding 8, §1.3). Project ideas in Offer Letter will also come from papers and blogs, so cards need a tag for this. |

### 1.2 Summary table

Weight key: **H** = in ≥30% of that domain's postings *or* a standard interview
round; **M** = 10–30% or critical in a sub-niche; **L** = <10% and rarely
interviewed. The posting columns give AI-company % / backend-company %.

| Tag | Skill | AI-infra | Backend | Posting signal (AI / BE) | Best harness task types |
|---|---|---|---|---|---|
| READ | Reading unfamiliar code | H | H | interview format (Meta, Stripe, Anthropic) | review-to-own, incident |
| DEBUG | Debugging and root cause | H | H | debug/troubleshoot/root cause 34% / 30% | incident, review-to-own |
| REVIEW | Code review and AI-output verification | M→H | H | code review 9% / 22%; AI-validation clauses in early postings | review-to-own, add-your-part |
| TEST | Testing and verification | M | H | test(s/ing) 36% / 42% | all; graded by mutation score |
| CODE | Implementation craft and languages | H | H | required in every posting | add-your-part, ownership change |
| API | API and interface design | M | H | APIs 35% / 34%; API/protocol design 10% / 19% | add-your-part, build |
| DB | Databases and storage internals | M | H | storage 25% / 13%; 301 DB-niche postings | perf-hunt, build |
| DIST | Distributed systems and consistency | H | H | distributed systems 31% / 36% | build, incident (fault injection) |
| OS | OS, concurrency, memory | M→H | M | concurrency 14% / 11%; Linux 17% / 8% | perf-hunt, review-to-own |
| NET | Networking | M | L→M | networking 32% / 18%; RDMA/InfiniBand 9% / 0% | incident, perf-hunt |
| PERF | Performance, profiling, cost | H | H | latency 27% / 15%; benchmark/measure 38% / 35% | perf-hunt |
| OBS | Observability, reliability, incident response | H | H | observability 55% / 56%; on-call/incident 25% / 31% | incident |
| INFRA | Cloud infra, containers, delivery | H | M→H | Kubernetes 33% / 27%; Terraform 11% / 12% | build, incident |
| SD | System design and architecture | H | H | design/architecture 58% / 56% (21% early → 69% staff+) | design-review, build |
| MLSYS | ML systems: serving, training infra, GPU | H | L | GPU 36% / 3%; kernels 14% / 3% | perf-hunt, build |
| ML | Modelling, evals, LLM apps | M | M | LLMs 30% / 19%; agents 38% / 35%; evals 13% / 5% | experiment |
| DATA | Data pipelines, streaming, quality | M | M | 176 data-platform postings; Kafka/Flink text in 220 | build, incident |
| SEC | Security | M | M | authn/authz/encryption/vulnerability 25% / 29%; 314 security postings | review-to-own |
| COMM | Design docs, writing, discussion | M | H | written communication 6% / 14%; design docs/RFCs 7% / 15%; cross-functional 21% / 29% | design-review, build |
| EXEC | Execution and ownership | H | H | ownership 45% / 46%; end-to-end 38% / 34% | build (milestones) |
| LIT | Research literacy: papers and blogs → production | M (H in research-engineer, inference and training roles) | L→M (H in query/storage-engine teams) | explicit 5% / 2%; implicit paper-born techniques in 33–38% of inference and training postings | experiment, perf-hunt, design-review |

### 1.3 Per-skill detail

The "observable evidence" lines are written as checks the harness can run or
score objectively. Thresholds are starting suggestions to calibrate later.

**READ — Reading unfamiliar code**
- *Sub-skills:*
  - tracing a request or data path across modules
  - finding where a decision is made
  - predicting behaviour from code
  - reading tests as specs
  - reading git history and blame to learn why
  - building a mental model of an AI-written codebase
- *Demand:* tested directly in Meta's AI-enabled round (phase 1: "explain the
  code and its complexity", then fix a bug)
  ([Hello Interview](https://hellointerview.com/blog/meta-ai-enabled-coding))
  and in Stripe's bug squash, judged on "whether you can read code you didn't
  write" ([Interview Query](https://www.interviewquery.com/guides/stripe-software-engineer)
  — candidate-report based). Affirm's early-career posting asks for being
  "comfortable navigating a large code base, debugging others' code"
  ([posting](https://job-boards.greenhouse.io/affirm/jobs/8010617003)).
  Osmani's "comprehension debt" essay explains why employers now value this
  ([addyosmani.com, 2026-03-14](https://addyosmani.com/blog/comprehension-debt/)).
- *Observable evidence:*
  - Answers "where/what-happens-when" questions with `file:line` pointers,
    checked against a call graph the harness computes.
  - Predicts a function's output on a given input before running it; the
    harness runs it and compares.
  - Draws the request path for a ticket, scored against the true module
    sequence (e.g. ≥ 80% of hops correct).
  - Answers "why does this code exist" from `git log`/`blame`, matched to the
    planted commit message.

**DEBUG — Debugging and root-cause analysis**
- *Sub-skills:*
  - reproducing the bug first, then writing a failing test
  - bisecting
  - localizing a fault using logs, metrics and traces
  - using debuggers, `strace`, `py-spy`, `pprof`
  - telling a symptom apart from its cause
  - debugging AI-generated code
- *Demand:* 34% / 30% of postings. Stack Overflow 2025: 66% of developers
  cite AI answers that are "almost right, but not quite", and 45% say
  debugging AI code takes longer
  ([SO survey](https://survey.stackoverflow.co/2025/ai)). In the Anthropic
  trial, debugging is the skill hurt most by AI delegation
  ([Anthropic](https://www.anthropic.com/research/AI-assistance-coding-skills)).
- *Observable evidence:*
  - Submits a reproducer test that fails on the buggy commit and passes on the
    fix.
  - The root-cause statement names the planted line or condition.
  - The fix diff is minimal (≤ N lines) and causes no suite regressions.
  - `git bisect` lands on the planted commit.
  - In an incident, names the faulted component (known to the harness) within
    the time budget, with no AI help in the first phase.

**REVIEW — Code review and AI-output verification**
- *Sub-skills:*
  - finding correctness, concurrency, security and performance defects
  - separating severity (blocker vs nit)
  - asking for the test that would have caught the bug
  - reviewing for maintainability and design
  - spotting AI failure modes: invented APIs, swallowed errors, missed edge
    cases, over-engineering
  - receiving review well: addressing comments, pushing back with evidence
- *Demand:*
  - Dropbox ladder: IC1 "participate in code reviews and raise questions" →
    IC2 "reconcile different opinions in code reviews" → IC4 "probing,
    constructive feedback … surfaces hidden assumptions"
    ([IC2](https://dropbox.github.io/dbx-career-framework/ic2_software_engineer.html),
    [IC4](https://dropbox.github.io/dbx-career-framework/ic4_software_engineer.html)).
  - GitLab Senior: "maintain and advocate for these standards through code
    review" ([GitLab](https://handbook.gitlab.com/job-families/engineering/backend-engineer/)).
  - The vLLM maintainer's point that plausible PRs are now cheap but review
    still costs the same **[RL report]**.
  - Willison: "Your job is to deliver code you have proven to work"
    ([blog, 2025-12-18](https://simonwillison.net/2025/Dec/18/code-proven-to-work/)).
- *Observable evidence:*
  - Recall of planted defects in a PR (L1 ≥ 50%, L3 ≥ 75%, L5 ≥ 90%).
  - False-alarm rate ≤ 1 per 100 changed lines.
  - Severity labels match ground truth.
  - Each blocking comment proposes a fix or a test; the harness runs the
    proposed test against the buggy branch, and it must fail there.
  - On his own PR: all comments resolved in ≤ 2 rounds, and a pushback is
    accepted when it is backed by a benchmark or test.

**TEST — Testing and verification**
- *Sub-skills:*
  - unit, integration and contract tests
  - regression test per bug
  - property-based testing and fuzzing
  - deterministic tests for concurrent code
  - diagnosing flaky tests
  - test design for AI-written code ("tests that fail if the implementation
    is reverted", per Willison)
- *Demand:* 36% / 42%. "Write … well tested and extensible code" is the
  first line of Affirm's early-career requirements
  ([posting](https://job-boards.greenhouse.io/affirm/jobs/8010617003)).
- *Observable evidence:*
  - Mutation score on his module ≥ threshold (e.g. 70%, via mutmut or
    cargo-mutants).
  - Every fixed bug has a test that fails on the old commit.
  - A property or fuzz test finds a planted edge-case bug.
  - Fixes a flaky test so it passes ≥ 200 of 200 runs under `--count`/stress.

**CODE — Implementation craft and language fluency**
- *Sub-skills:*
  - correct, readable code in Python and one systems language
  - idioms, error handling, typing
  - refactoring without changing behaviour
  - DSA for screens
  - AI-assisted workflow: writing a spec and acceptance tests before
    prompting, decomposing tasks for an agent, and owning every line
- *Demand:*
  - Every posting requires it.
  - The DSA/fundamentals line is in **48% of early postings** vs 9–10% at
    mid/senior.
  - "Fluency with AI coding harnesses" is a *minimum* requirement at Fireworks
    **[RL report]**.
  - Canva requires AI in interviews and expects engineers "to take full
    ownership of any code they produce, whether they wrote it themselves or with
    AI assistance"
    ([canva.dev](https://canva.dev/blog/engineering/yes-you-can-use-ai-in-our-interviews)).
- *Observable evidence:*
  - The unaided ownership-change request (AI teammates off) passes hidden
    tests within its time box.
  - Lint and type checks are clean (ruff/mypy, clippy, go vet).
  - Cyclomatic-complexity budget is met.
  - For AI-assisted work: he files a spec and test plan before generating code.
  - In the voice quiz he explains any line the harness picks from the
    accepted diff, and gets ≥ 90% of questions right.

**API — API and interface design**
- *Sub-skills:*
  - REST/gRPC resource modelling
  - error model, pagination, idempotency keys
  - versioning and backward compatibility
  - rate-limit and quota semantics
  - streaming APIs (SSE/gRPC streams for token streaming)
  - library and module interfaces that are "hard to misuse" (Dropbox IC3)
- *Demand:* 35% / 34%. Stripe's integration round is "pure API work …
  heavy emphasis on error handling" (candidate report,
  [PracHub](https://prachub.com/interview-experiences/stripe-software-engineer-interview-with-coding-bug-squash-api-integration-and-bq-rounds-cf992a00e3)).
  API Design is a Hello Interview core concept
  ([HI](https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview)).
- *Observable evidence:*
  - Contract tests pass.
  - Old-client test suite passes against the new server (backward-compat
    gate); `buf breaking` / OpenAPI diff is clean.
  - Duplicate POSTs with the same idempotency key produce exactly one side
    effect under a replay test.
  - Error responses follow the documented schema in 100% of fuzzed cases.

**DB — Databases and storage internals**
- *Sub-skills:*
  - data modelling
  - indexes and query plans
  - transactions and isolation levels (lost update, write skew)
  - zero-downtime migrations (expand/contract)
  - connection pooling
  - storage-engine basics: B-tree vs LSM, WAL, compaction
  - caching layers
  - OLAP vs OLTP
- *Demand:* 301 database/storage-niche postings (MongoDB 60, ClickHouse 55,
  Supabase 24, SingleStore 19). SingleStore's new-grad engine role works on
  "the query optimizer … SIMD and LLVM codegen"
  ([posting](https://job-boards.greenhouse.io/singlestore/jobs/8205427)). Data
  Modeling, Database Indexing, Sharding and Caching are Hello Interview core
  concepts.
- *Observable evidence:*
  - Reads an EXPLAIN plan and names the missing index; query p95 then drops
    below threshold in the benchmark.
  - Picks the isolation level or locking that makes a planted concurrency
    anomaly test pass 1,000 of 1,000 runs.
  - Runs a migration under synthetic traffic with 0 failed requests.
  - Estimates table and index size within 2× of the measured size.

**DIST — Distributed systems and consistency**
- *Sub-skills:*
  - timeouts, retries with backoff and jitter
  - idempotency, exactly-once effects
  - replication, quorums, leader election (conceptual), partitioning and
    consistent hashing
  - queues and backpressure
  - CAP and consistency models
  - clock skew and ordering
  - failure detection
- *Demand:* 31% / 36%. "Solid understanding of distributed systems" is the
  core requirement in inference-infra postings
  ([Anyscale](https://jobs.ashbyhq.com/anyscale/1cf38233-8aa0-47f8-9d85-65ce27bc3047),
  [Anthropic Senior SWE Inference](https://job-boards.greenhouse.io/anthropic/jobs/4641822008)).
  Contention, Scaling Writes and Multi-step Processes are HI patterns.
- *Observable evidence:*
  - Survives a fault-injection script (kill node, partition, latency,
    duplicate or reordered messages via toxiproxy) with invariants intact,
    checked by a linearizability-lite or ledger-balance checker.
  - The retry storm stays under X× baseline load.
  - The design doc states the consistency guarantee, and the test suite
    proves it.

**OS — Operating systems, concurrency, memory**
- *Sub-skills:*
  - threads, async and event loops
  - locks, atomics, lock ordering
  - data races and deadlocks
  - memory layout, allocation, leaks
  - processes and syscalls, file I/O and page cache
  - containers' cgroups and namespaces (bridges to INFRA)
- *Demand:* concurrency 14% / 11%; Linux 17% / 8%. Anthropic's onsite coding
  reportedly pushes into "thread safety and race conditions" (concurrent
  crawler, multiprocessing pipeline — candidate reports via
  [Hello Interview guide](https://www.hellointerview.com/guides/anthropic/swe);
  unverified). SingleStore's new-grad posting prefers "operating systems,
  distributed systems, concurrency, multithreading".
- *Observable evidence:*
  - Race detector clean: ThreadSanitizer, `go test -race`, loom.
  - A planted deadlock is removed and the stress test passes.
  - RSS drops below the target with no leak over a 30-minute soak (heap
    profile).
  - p99 improves after removing lock contention, shown in a before/after
    profile.

**NET — Networking**
- *Sub-skills:*
  - TCP behaviour (handshakes, Nagle, keepalive)
  - HTTP/1.1 vs HTTP/2 vs gRPC
  - TLS basics
  - DNS
  - load balancing and health checks
  - connection pooling
  - slow clients and backpressure
  - packet capture
  - RDMA/InfiniBand concepts for GPU clusters
- *Demand:* 32% / 18% (Cloudflare, Tailscale, GPU clouds). RDMA/InfiniBand
  appears in 20% of inference-serving postings.
- *Observable evidence:*
  - Fixes a planted timeout or pool-exhaustion bug; the error rate under the
    load test drops to ~0.
  - Answers packet-capture questions from a `pcap`.
  - Configures health checks so a failing replica is drained within N seconds
    in the harness test.

**PERF — Performance, profiling and cost**
- *Sub-skills:*
  - benchmarking methodology: warmup, variance, percentiles, steady state
  - CPU and memory profiling (flame graphs)
  - tail latency
  - throughput vs latency trade-offs
  - back-of-envelope estimation
  - cost per request or token
  - capacity planning
- *Demand:*
  - Latency is in 27% / 15% of postings, benchmark/measure 38% / 35%.
  - Baseten: "reason from first principles about where time and memory go …
    tracing a tail-latency regression"
    ([posting](https://jobs.ashbyhq.com/baseten/7cb19a05-8e5b-44cf-b3e7-19949e2eff04)).
  - "Numbers to Know" is an HI core concept.
- *Observable evidence:*
  - The harness benchmark meets the target (e.g. p99 ≤ X ms at Y RPS).
  - The run includes ≥ 5 trials and a reported spread.
  - He names the top hotspot *before* optimizing and matches the profiler's
    top frame.
  - The back-of-envelope estimate is within 2× of measured.
  - Cost-per-1M-requests (or tokens) is reduced by ≥ Z% with no
    quality/regression failures.

**OBS — Observability, reliability and incident response**
- *Sub-skills:*
  - metrics, logs and traces (OpenTelemetry)
  - SLOs and error budgets, burn-rate alerts
  - dashboards a teammate can use
  - on-call: mitigate first (rollback, flag off), then root-cause
  - runbooks
  - blameless postmortems
- *Demand:*
  - Observability is in 55% / 56% of postings (23% early → 63% senior).
    On-call/incident is in 25% / 31% (2% early → 37% senior).
  - Honeycomb's *Engineer I* posting: "Experience being on call. You'd join our
    rotation after about 90 days"
    ([posting](https://job-boards.greenhouse.io/honeycomb/jobs/5452586008)).
  - Dropbox IC1 already asks engineers to "contribute with urgency to
    operational issues (e.g., SEVs)" and to raise suspected regressions.
- *Observable evidence:*
  - Time-to-mitigate within budget.
  - Mitigation happened before root-cause work, where that was correct.
  - The injected fault can be found from his dashboards alone (a teammate quiz
    on them).
  - The SLO alert fires on the injected degradation and *not* on a noise
    replay.
  - The postmortem passes a rubric: timeline, impact, contributing factors,
    detection gap, owned action items.

**INFRA — Cloud infrastructure, containers and delivery**
- *Sub-skills:*
  - Dockerfiles (small, non-root, reproducible)
  - Kubernetes basics: probes, resources, rollouts, controllers/CRDs for
    advanced work
  - infrastructure as code
  - CI pipelines and caching
  - canary/blue-green releases with automatic rollback
  - feature flags
  - GPU scheduling and bin-packing (AI)
- *Demand:*
  - Kubernetes appears in 33% / 27% of postings, and in 59% of SRE and 45% of
    database-company postings.
  - Together's inference-infra role wants "hands-on experience with Kubernetes
    controller/CRD patterns … GPU scheduling and capacity efficiency
    (fragmentation, bin-packing)" and "You build it, you own it"
    ([posting](https://job-boards.greenhouse.io/togetherai/jobs/5186628007)).
- *Observable evidence:*
  - The service runs under local k8s (kind/k3d) with probes passing.
  - Image size is ≤ target.
  - When the harness injects a bad version, his canary script rolls back
    automatically within N minutes.
  - CI runs tests and lint and is ≤ X min with a warm cache.

**SD — System design and architecture**
- *Sub-skills:*
  - requirements and non-functional targets
  - capacity estimates
  - API and data model
  - component breakdown
  - trade-offs with alternatives
  - failure modes and mitigations
  - rollout and migration plan
  - evolving a design under new constraints (10× traffic, region loss)
- *Demand:* design/architecture appears in 58% / 56% of postings, with the
  steepest level gradient of any skill (21% → 48% → 62% → 69%). Hello
  Interview: for seniors "system design interviews are the norm and carry a
  disproportionate weight"; a mid-level candidate "might cover the basics well
  but not into great depth"
  ([HI](https://www.hellointerview.com/learn/system-design/in-a-hurry/introduction)).
- *Observable evidence:*
  - The design doc passes a rubric with required sections.
  - It names ≥ 2 alternatives with a stated reason for rejecting each.
  - It names each failure mode with a mitigation.
  - It includes numeric estimates, which are later checked against the build:
    the measured throughput/latency/memory falls within a factor of the
    estimate.
  - In design-review, he answers the senior teammate's level-calibrated
    curveballs with a concrete change, not a restatement.

**MLSYS — ML systems: serving, training infra, GPU**
- *Sub-tags:*
  - `MLSYS.serve`: continuous batching, KV-cache paging and reuse, prefill/decode
    disaggregation, speculative decoding, quantization, routing and
    autoscaling, structured output
  - `MLSYS.train`: data/tensor/pipeline parallelism, collectives, checkpointing,
    input pipelines, RL rollout infrastructure
  - `MLSYS.gpu`: CUDA/Triton kernels, memory hierarchy, roofline, profiling with
    Nsight
  - `MLSYS.platform`: feature stores, model registries, eval infrastructure
- *Demand:* GPU appears in 36% of AI postings (54% of AI senior), kernels in
  14%, and vLLM/SGLang/TensorRT in 30% / 20% / 19% of *inference-serving*
  postings. Baseten lists "quantization, speculative decoding, KV-cache reuse,
  chunked prefill, LoRA, guided generation … custom scheduling and routing"
  ([posting](https://jobs.ashbyhq.com/baseten/7cb19a05-8e5b-44cf-b3e7-19949e2eff04)).
  Anthropic inference projects include "intelligent routing algorithms …
  autoscaling our compute fleet … prompt caching"
  ([posting](https://job-boards.greenhouse.io/anthropic/jobs/4641822008)).
  Together's GPU intern role needs "CUDA and/or Triton … performance
  profiling" ([posting](https://job-boards.greenhouse.io/togetherai/jobs/5238460007)).
- *Observable evidence (all fit an RTX 4070 12 GB):*
  - Tokens/s ≥ X at p99 TTFT ≤ Y on a fixed request trace.
  - KV-cache memory estimate within 10% of measured.
  - The 4-bit model stays within Δ of baseline on a held-out eval, with a
    speedup ≥ S.
  - The kernel matches the reference within tolerance and reaches ≥ P% of the
    roofline or beats the PyTorch baseline.
  - Training resumes from a checkpoint after a `kill -9` with identical loss
    curves.
  - GPU utilization ≥ U% after the data-loader stall is fixed.

**ML — Modelling, evaluation and LLM applications**
- *Sub-skills:*
  - train/validation/test hygiene, baselines, ablations, error analysis
  - offline vs online metrics
  - building eval sets and harnesses
  - `ML.llmapp`: retrieval (RAG) quality, agent/tool loops, guardrails,
    cost/latency budgets, sandboxed execution
- *Demand:* LLMs 30% / 19%, agents 38% / 35%, evals 13% / 5%. ML-platform roles
  sit mostly at backend/consumer companies (Pinterest 20, Reddit 16, Airbnb 12).
  Notion's early-career AI role: "build or extend an evaluation set, run
  experiments, analyze results"
  ([posting](https://jobs.ashbyhq.com/notion/85947779-6b87-466a-98bc-30a640448c28)).
- *Observable evidence:*
  - Held-out metric ≥ threshold.
  - Leakage check passes (the harness hides a leak bait).
  - His eval set catches a planted model regression.
  - RAG recall@k ≥ X and agent task success ≥ Y within a cost cap.
  - The experiment write-up includes a baseline and ≥ 1 ablation.

**DATA — Data pipelines, streaming and data quality**
- *Sub-skills:*
  - batch pipelines that are idempotent and can be backfilled
  - orchestration (Airflow/Dagster/dbt)
  - streaming (Kafka, Flink): consumer lag, exactly-once sinks, late data
  - schema evolution
  - data-quality checks
  - columnar formats and lakehouse tables (Parquet/Iceberg)
- *Demand:*
  - Data-platform postings: Python 63%, SQL 49%, Java 34%; tools dbt 35%,
    Spark 30%, Snowflake 28%, Airflow 27%, Kafka 24%, Iceberg/Delta 20%.
  - Postings mentioning Kafka/Flink/stream processing (n=220): Kafka 87%,
    Spark 42%, Flink 29%.
- *Observable evidence:*
  - Rerunning the pipeline gives a byte-identical output hash.
  - Backfill of N days finishes with no duplicates.
  - Quality checks catch a planted bad batch (schema drift, null spike,
    duplicates) before it reaches the sink.
  - Consumer lag stays < X s under the harness load generator.

**SEC — Security**
- *Sub-skills:*
  - authentication and authorization (incl. multi-tenant isolation)
  - input validation: SQL injection, SSRF, path traversal
  - secrets handling
  - dependency and supply-chain hygiene
  - sandboxing untrusted code (agents, RL environments)
  - threat modelling a design
- *Demand:* 25% / 29% of postings; 314 security-niche postings. Multi-tenancy,
  isolation and sandboxing appear in 17% of AI postings (agent sandboxes;
  see [RL report] on xAI/Prime sandbox roles).
- *Observable evidence:*
  - Finds the planted vulnerability in review.
  - Fix plus exploit test: the exploit succeeds before the fix and fails
    after.
  - Tenant-isolation test suite passes.
  - Sandbox-escape probes from the harness are all blocked.
  - The design doc includes a threat-model section.

**COMM — Design docs, writing and discussion**
- *Sub-skills:*
  - PR descriptions (what, why, how tested, risk)
  - design docs
  - status updates that flag risk early
  - explaining by voice to seniors and to the junior teammate
  - productive disagreement and disagree-and-commit
- *Demand:* written communication 6% / 14%, design docs/RFCs 7% / 15%,
  cross-functional 21% / 29%. Dropbox IC1: "I write and speak with clarity and
  focus … proactively share … trade-offs."
- *Observable evidence:*
  - PR description rubric (4 required parts).
  - Design-doc rubric.
  - Voice explanation: ≥ 90% of the follow-up verification questions answered
    correctly.
  - Status-update accuracy: stated "on track" vs actual milestone date.
  - The junior teammate's quiz score after his explanation.

**EXEC — Execution and ownership**
- *Sub-skills:*
  - breaking work into milestones
  - estimating and re-estimating
  - incremental PRs that always leave the system working
  - proposing scope cuts when slipping
  - follow-through on action items
  - prioritizing by value
  - escalating at the right time
- *Demand:* ownership 45% / 46%, end-to-end 38% / 34%, ambiguity 27% / 23%.
  Dropbox's Results pillar: "follow through on my commitments" (IC1) →
  "propose scope changes" (IC2) → "recognize when work isn't making a
  difference and redirect" (IC3).
- *Observable evidence:*
  - Estimate/actual ratio tracked per ticket (L1 within 2×, L3 within 1.5×,
    L5 within 1.25×).
  - Median PR size ≤ N lines, with green CI on every PR.
  - Postmortem action items he owns are closed by their due date.
  - When a milestone slips, he proposes a cut *before* the deadline.

**LIT — Research literacy (papers and engineering blogs → production work)**
- *Sub-skills:*
  - extracting a paper's core claim, mechanism, baseline and evaluation setup
  - spotting weak evidence: unfair baselines, cherry-picked metrics,
    test-set leakage, scale-dependent gains
  - listing the paper's assumptions (workload, hardware, data, scale) and
    checking each against our system
  - estimating the expected gain from *our* numbers before building
  - scaled-down reproduction
  - porting a technique into an existing codebase behind a flag
  - reading engineering blogs and postmortems for transferable lessons
  - writing up the result: an adopt/don't-adopt memo, a reproduction report
    or a team paper talk
- *Demand: explicit asks.* A keyword pass over the 3,056 postings looked for
  reading/tracking papers, research-to-production and reproducing results.
  - *Shares:* 5% of AI-company postings (62), 2% of backend (32),
    **25% of research-engineer titles** (14 of 57), 10% of ML/AI-engineer
    titles (29 of 295), 6% of early-career (7 of 120). Phrases sitting in
    company boilerplate were stripped.
  - *Representative wording:*
    - Fireworks Evals Platform: "read the latest research papers … insist on
      rigorously reproducing published results internally"
      ([posting](https://jobs.ashbyhq.com/fireworks/cca38fd5-9cbd-4cee-8fdb-d6e6d230b036)).
    - Fireworks Systems Infrastructure, PhD new grad: "Turn research ideas
      into production systems that hold up under real workloads, real
      failures, and real customers"
      ([posting](https://jobs.ashbyhq.com/fireworks/ad58a098-ef75-4a4b-8475-55c2653213ef)).
    - Perplexity inference: "You can read a research paper on Monday, write a
      kernel on Wednesday, and debug a production incident on Friday"
      ([posting](https://jobs.ashbyhq.com/perplexity/8a976851-9bef-4b07-8d36-567fa9540aef)).
    - Together, large-scale training: "implement state-of-the-art techniques
      from both the research literature and our own scientists in production
      environments"
      ([posting](https://job-boards.greenhouse.io/togetherai/jobs/5199554007)).
    - Starburst: "you read papers and you ship code"
      ([posting](https://job-boards.greenhouse.io/starburst/jobs/5416956008)).
    - LlamaIndex: "not a pure research role where ideas stay in papers"
      ([posting](https://jobs.ashbyhq.com/llamaindex/5ef32675-090d-4eb2-bca0-ddb6fbde0215)).
    - CoreWeave: "You probably shared the ScaleRL paper in your group chats,
      and kicked off a few ablations after you read it"
      ([posting](https://coreweave.com/careers/job?4666901006&board=coreweave&gh_jid=4666901006)).
- *Demand: backend and data side.* Smaller, but present in engine and
  query teams:
  - Databricks Senior Staff: "bringing ideas from the academic literature or
    internal R&D into systems that solve real customer problems"
    ([posting](https://databricks.com/company/careers/open-positions/job?gh_jid=8493002002)).
  - MongoDB's senior query-optimization 12-month outcomes include "presenting
    a favorite paper or system architecture related to query systems"
    ([posting](https://www.mongodb.com/careers/job/?gh_jid=7870876)).
  - GitLab static analysis: "read, evaluate, and apply the research
    literature"
    ([posting](https://job-boards.greenhouse.io/gitlab/jobs/8693563002)).
  - Instacart ML: "paper sharing" as team culture
    ([posting](https://instacart.careers/job/?gh_jid=7963840)).
  - Even an *intern* role: Coinbase's ML intern "will take ownership of a
    research-to-production project"
    ([posting](https://www.coinbase.com/careers/positions/8175441?gh_jid=8175441)).
- *Demand: implicit, and larger.* Many postings name paper-born techniques
  without saying "paper":
  - **Inference-serving** titles at AI companies, **38%** (26 of 69):
    quantization, speculative decoding, KV-cache management, prefill/decode
    disaggregation, FP8, continuous batching, chunked prefill.
  - **Training/RL** titles, **33%** (26 of 78): RLHF, FSDP, LoRA,
    PPO/GRPO/DPO.
  - **GPU/kernel** titles, 23%.
  - **Database/query** titles, 15%: query optimization, vectorized execution,
    Raft/Paxos.
  - Production lineage is direct. NVIDIA Dynamo's disaggregated serving "is
    inspired by the DistServe (2024) paper"
    ([Dynamo docs](https://docs.dynamo.nvidia.com/dynamo/v-0-9-0/design-docs/disaggregated-serving)),
    and vLLM was the PagedAttention paper's own system
    ([Kwon et al., SOSP 2023](https://arxiv.org/abs/2309.06180)).
- *Demand: interviews.* No standard "implement the paper" round was found
  for SWE or research-engineer loops. A prep guide describes a 60-minute
  paper-discussion round for DeepMind's *Research Scientist* track only,
  probing "methodology, motivation, weaknesses, and how the candidate would
  extend the work"
  ([techinterview.org, 2026](https://www.techinterview.org/post/3233474918/deepmind-interview-process-2026/);
  unverified, no sources cited). For hiring, the value is mainly portfolio
  evidence: the [RL report]'s "measurable, reproducible worklog" pattern,
  plus Prime Intellect listing "writing engineering blogs" as a plus.
- *Observable evidence (harness checks):*
  - **Scaled-down reproduction.** Reproduces the paper's headline *relative*
    result within X% (e.g. a reported 2× throughput gain gives ≥ 1.6× on the
    harness trace, fitting 12 GB).
    - The reproduction report lists every deviation: scale, data, hardware,
      hyperparameters.
    - An ablation shows the gain disappears when the key component is
      removed.
  - **"Should we adopt this?" memo** (one page), graded on a rubric:
    - claim, mechanism, evidence quality
    - the paper's assumptions, each marked *holds / doesn't hold for us* with
      our numbers
    - a predicted gain range
    - risks, a decision and the cheapest experiment to confirm it
  - **Planted trap in the memo task.** The harness hides one assumption that
    breaks on the company's data. Example: the paper assumes long prompts,
    the company trace is mostly short. The memo must name it.
  - **Prediction calibration.** He predicts the gain before building; the
    harness compares it with the measured gain (tracked across tasks, like
    estimate error in EXEC).
  - **Paper → PR.** The technique lands behind a feature flag in the
    teammate codebase, with tests and a benchmark on the company workload.
    Passing means the gain meets the memo's lower bound, *or* the memo
    correctly predicted no gain.
  - **Critical-reading quiz.** Click-questions on a real paper: key insight,
    baseline, metric, the one figure that carries the claim. Plus a
    synthetic "paper" with a planted flaw (leaky split, weak baseline) that
    he must flag.
  - **Blog/postmortem transfer.** Given a real engineering blog post or
    postmortem, he names which of its lessons apply to the company's system
    and which don't, scored against an answer key.

---

## 2. Leveling ladder L1 → L5

### 2.1 Crosswalk to real ladders

| Harness | Real-world equivalent | Scope phrase (real ladder) | Years in postings (median of stated minimum) |
|---|---|---|---|
| **L1** Intern / new grad | Dropbox IC1; Google L3 entry; Meta E3; CircleCI E1 | "execute on defined tasks" (Dropbox IC1); E1 = "within a task" (CircleCI) | 0 (early postings; "less than two years" at [Notion](https://jobs.ashbyhq.com/notion/85947779-6b87-466a-98bc-30a640448c28)) |
| **L2** New grad after ~1 year | Upper Dropbox IC1 → IC2; GitLab Intermediate | "confidently ship small features … with minimal guidance" (GitLab baseline) | ~1–2 (backend early median 2, n=14 — small sample) |
| **L3** Mid-level | Dropbox IC2; Google L4; Meta E4; CircleCI E2 | "execute on defined projects to achieve team-level goals" (IC2); E2 = "within a project" | ~3 (backend mid median 3, n=410) |
| **L4** Senior-ready | Dropbox IC2 → IC3; Google L4 → L5 | "independently works out solutions to ambiguous problems" (IC3) | ~4–5 |
| **L5** Senior | Dropbox IC3 (with IC4 craft items); Google L5; Meta E5; CircleCI E3; GitLab Senior | "owns projects that support quarterly team goals … mentors new hires" (IC3); E3 = "within a team" | 5 (senior median 5 in both domains, n=157 AI / 484 BE) |

Sources:
- Dropbox Career Framework, IC1–IC7 with Results/Direction/Talent/Culture
  pillars plus a Craft section:
  [overview](https://dropbox.github.io/dbx-career-framework/overview.html),
  [IC1](https://dropbox.github.io/dbx-career-framework/ic1_software_engineer.html),
  [IC2](https://dropbox.github.io/dbx-career-framework/ic2_software_engineer.html),
  [IC3](https://dropbox.github.io/dbx-career-framework/ic3_software_engineer.html),
  [IC4](https://dropbox.github.io/dbx-career-framework/ic4_software_engineer.html).
  Dropbox average total compensation IC1 $179K / IC3 $379K, per
  [levels.fyi](https://www.levels.fyi/companies/dropbox/salaries/software-engineer),
  supports IC3 ≈ senior.
- CircleCI scope by level, E1 task → E2 project → E3 team → E4–E6 multiplying
  impact
  ([CircleCI blog](https://circleci.com/blog/7-steps-to-building-an-engineering-competency-matrix/)).
- GitLab backend job family
  ([handbook](https://handbook.gitlab.com/job-families/engineering/backend-engineer/)).
- Google L3/Meta E3 = entry and L5/E5 = senior. This mapping is secondary and
  inferred by those sites
  ([DesignGurus](https://www.designgurus.io/blog/understanding-faang-software-engineer-job-levels),
  [levels.fyi thread](https://www.levels.fyi/community/thread/i4i1uv/level-mapping)).
- progression.fyi indexes ~75 public frameworks, but its site could not be
  reached directly (mirror only), so it is not used as a source here.

### 2.2 How the postings change by level (all 85 companies, n = 119 / 1,107 / 853 / 947)

| Phrase family | Early | Mid | Senior | Staff+ | What it tells the harness |
|---|---|---|---|---|---|
| System design / architecture | 21% | 48% | 62% | 69% | SD is the main senior differentiator |
| Technical leadership | 1% | 9% | 16% | 40% | L5 → staff gate; L1–L3 barely |
| Mentors others | 1% | 6% | 18% | 18% | appears at L4–L5 |
| Receives mentorship | 19% | 1% | 0% | 0% | L1 is expected to be taught |
| On-call / incident | 2% | 27% | 37% | 27% | ops ownership starts at L2–L3 |
| Observability | 23% | 55% | 63% | 53% | — |
| Distributed systems | 16% | 28% | 40% | 39% | — |
| Security | 7% | 26% | 37% | 23% | — |
| Networking | 4% | 25% | 27% | 21% | — |
| Design docs / RFCs | 6% | 10% | 15% | 13% | — |
| Ambiguity | 16% | 23% | 22% | 29% | — |
| CS fundamentals / DSA | 48% | 9% | 9% | 10% | screens for L1 |
| Testing | 45% | 41% | 43% | 35% | flat: expected at every level |
| Code review | 28% | 14% | 21% | 15% | flat-ish: every level |
| AI coding tools | 27% | 23% | 22% | 18% | most explicit for L1 |

### 2.3 Rubric by dimension, as observable harness behaviours

**Scope**
- **L1:** one well-specified ticket (≤ 1 day, 1–3 files); TL wrote the
  acceptance criteria.
- **L2:** a feature inside an existing design (2–5 days, multi-file); he
  writes the acceptance criteria.
- **L3:** a defined project of weeks, split into milestones toward a team goal;
  he chooses the solution.
- **L4:** turns an *ambiguous* problem (e.g. "p99 regressed after the
  migration") into a scoped project with components spanning modules.
- **L5:** owns a quarter-sized team goal; coordinates work with other AI teams
  in the fictional company.

**Technical depth**
- **L1:** correct code in one language; reads modules he didn't write; knows
  the basics of SQL, HTTP, Big-O and threads.
- **L2:** navigates the whole service; uses a profiler and a debugger
  unprompted; knows the service's data model and main failure modes.
- **L3:** designs a component with clean separation; applies DB/DIST/PERF
  basics; predicts failure modes before testing.
- **L4:** has one deep area (e.g. `MLSYS.serve` or DB) plus breadth;
  quantitative estimates; chooses consistency models.
- **L5:** designs multi-component systems that are "simple, testable,
  debuggable, and hard to misuse" (Dropbox IC3); knows when *not* to
  refactor; sets standards others follow.

**Execution / quality**
- **L1:** small PRs with tests and green CI; "free of glaring errors" (IC1);
  asks for help after a set stuck-time.
- **L2:** splits a feature into ≥ 3 working PRs; estimate within 1.5×; review
  feedback addressed in ≤ 2 rounds.
- **L3:** delivers a project on its milestone plan; few mainline bugs after
  merge; reduces toil.
- **L4:** safe rollouts with monitoring and success metrics; proactive scope
  cuts; risk register in the design doc.
- **L5:** team goals on time; measures impact and redirects when a metric
  isn't moving; pays down tech debt in owned code.

**Communication**
- **L1:** clear PR descriptions; asks clarifying questions; explains his own
  change by voice.
- **L2:** short design note for his feature; specific, actionable review
  comments on peers' PRs.
- **L3:** design doc with alternatives; "reconcile different opinions in
  code reviews" (IC2); clear status updates with risks.
- **L4:** leads a design review with the senior AI; probing review comments
  that surface hidden assumptions (IC4).
- **L5:** tailors messages to the audience (PM vs TL vs junior); written
  rationale others build on; disagree-and-commit.

**Ownership / influence**
- **L1:** follows through; owns mistakes; joins incidents as a helper; flags
  suspected regressions (IC1).
- **L2:** secondary on-call; writes a runbook entry; fixes adjacent bugs he
  finds.
- **L3:** primary on-call for the service he owns; runs a SEV to
  mitigation; mentors the AI junior on a task.
- **L4:** drives an incident through the postmortem; mentors the junior every
  week; improves a team process.
- **L5:** mentors new hires and interns (IC3); maintains playbooks; declares
  SEVs; shapes the team roadmap.

**Research literacy (LIT) across levels.** The evidence is thinner than for
the five dimensions above; it is drawn from postings, not ladders.
- **L1:** with a reading guide, answers the critical-reading quiz on an
  assigned paper; reproduces a toy result a teammate has scoped.
- **L2:** reproduces a scoped result on his own and writes up the
  deviations.
- **L3:** writes the adopt/don't-adopt memo for his own component,
  including the assumption check and a predicted gain.
- **L4:** chooses which paper or blog technique to try for an ambiguous
  problem; lands it behind a flag; prediction within 2× of measured.
- **L5:** decides adoption for the team and teaches it. MongoDB's senior
  outcome is "presenting a favorite paper … to expand the team's horizons".

**Promotion signals the harness can compute (suggested gates).** Each level
requires at least 3 consecutive passing tasks at that level, plus:

| Signal | L1 → L2 | L2 → L3 | L3 → L4 | L4 → L5 |
|---|---|---|---|---|
| Planted-bug recall in review | 50% | 65% | 80% | 90% |
| Estimate error | ≤ 2× | ≤ 1.5× | ≤ 1.5× | ≤ 1.25× |
| Design-doc rubric | — | ≥ 60% | ≥ 75% | ≥ 85%, and alternatives judged sound by the senior AI |
| Incident | helper | mitigates a P2 | runs a P1 and writes the postmortem | prevents a recurrence through a systemic fix |
| Mentoring | — | — | the junior AI's quiz improves | 2+ juniors improve, and a review standard is adopted |
| Unaided change | passes | passes | passes | passes |

---

## 3. Language and tool demand by niche

Values are the share of postings in that niche (classified from the title,
or from the company for single-niche companies) that name the item. **n** =
postings. Source: [`01-postings-2026-10-19.csv`](01-postings-2026-10-19.csv).

| Niche (n) | Languages | Frameworks / infra tools | Example companies (posting counts) and notes |
|---|---|---|---|
| **Inference serving** (80) | Python 60%, **C++ 45%**, Rust 32%, CUDA 30%, Go 26%, Triton 24% | Kubernetes 39%, **vLLM 30%**, PyTorch 26%, containers 25%, SGLang 20%, RDMA/InfiniBand 20%, TensorRT 19%, NCCL/MPI 12% | Cerebras 12, Anthropic 12, OpenAI 10, Baseten 7, Together 5. Topics: batching, KV cache, routing, autoscaling. OpenAI's Model Inference role asks "at least 5 years" ([posting](https://jobs.ashbyhq.com/openai/83b6755d-7785-4186-9050-5ef3ad127941)) |
| **Training / RL infra** (102) | Python 54%, Rust 16%, C++ 16%, Go 15%, CUDA 14% | PyTorch 33%, Kubernetes 27%, **JAX 19%**, NCCL/MPI 13%, RDMA/InfiniBand 13%, Ray 11%, Slurm 8% | Anthropic 26, Cohere 11, OpenAI 11. Mostly senior; see [RL report] for undergrad doors |
| **GPU kernels / compilers / perf** (90) | **C++ 49%**, Python 46%, CUDA 24%, Rust 21%, Triton 13% | Linux 26%, PyTorch 23%, RDMA 13%, NCCL 12%, JAX 10%, TensorRT 8% | OpenAI 12, Cerebras 11, Anthropic 9, Etched 8. Intern door: Together GPU Programming intern ($58–70/h) |
| **ML platform / ML infra** (184) | **Python 64%**, Go 15%, C++ 14%, SQL 14%, Java 10% | PyTorch 38%, RAG/retrieval 34%, embeddings 22%, Spark 20%, Ray 15%, TensorFlow 15%, Airflow 9%, Kafka 8% | Pinterest 20, Reddit 16, Airbnb 12, Coinbase 11. ML infra at *consumer* companies is a big, under-noticed niche |
| **Vector / search / retrieval** (165) | Python 35%, **Java 27%**, Rust 19%, C++ 18%, Go 18% | Elasticsearch/OpenSearch 25%, embeddings 20%, RAG 35%, PyTorch 16% | Elastic 37 (Java), Anthropic 28, Perplexity 16. Vector-DB startups have tiny boards (Pinecone 2, LanceDB 4, turbopuffer 1), but their postings name Rust/Go/C++ |
| **Data platforms / pipelines** (176) | Python 63%, **SQL 49%**, Java 34%, Go 22%, Scala 14% | AWS 44%, Kubernetes 38%, dbt 35%, Spark 30%, Snowflake 28%, Airflow 27%, Kafka 24%, Iceberg/Delta 20% | Fivetran 32, Hex 13, Starburst 10 |
| **Streaming / events** (220 postings mentioning Kafka/Flink/stream processing) | Python 57%, Go 57%, Java 34%, SQL 25%, Rust 23%, C++ 21% | Kafka 87%, Kubernetes 57%, Spark 42%, AWS 36%, Flink 29%, ClickHouse 17% | Cloudflare, ClickHouse, Coinbase, CoreWeave, OpenAI. Confluent's board was empty on the pull date |
| **Databases / storage engines** (301) | **Go 41%**, C++ 35%, Python 34%, Rust 28%, Java 26%, SQL 19% | AWS 49%, Kubernetes 45%, GCP 43%, Azure 41%, ClickHouse 21%, Terraform 18%, Postgres 15% | MongoDB 60, ClickHouse 55, Supabase 24, SingleStore 19 (C++ engine new-grad roles) |
| **Observability** (159) | **Go 48%**, Python 46%, Rust 19%, Java 19%, TypeScript 19% | Kubernetes 43%, Grafana 31%, Prometheus 28%, OpenTelemetry 19%, Kafka 17%, ClickHouse 11% | Datadog 40, Grafana 35, Sentry 19 |
| **Dev platforms / cloud infra** (964) | Python 43%, **Go 40%**, Rust 20%, C++ 17%, Java 16%, TypeScript 14% | Kubernetes 41%, AWS 31%, containers 23%, GCP 22%, Terraform 20%, Linux 18% | Cloudflare 103 (Go and Rust heavy), GitLab 67 (Ruby/Go), OpenAI 48, Anthropic 44 |
| **SRE / reliability** (97) | Python 58%, Go 49%, Java 16%, Ruby 13% | **Kubernetes 59%**, AWS 47%, Terraform 44%, Linux 41%, Prometheus 30%, Grafana 31% | Crusoe 12, MongoDB 10, Nebius 10 |
| **Payments / fintech backends** (455) | Python 41%, Go 24%, Java 21%, **Kotlin 17%**, SQL 15%, **Ruby 12%** | AWS 32%, Kubernetes 20%, React 17%, Spark 10%, MySQL 9%, Kafka 7%, gRPC 5% | Stripe 108 (Java, Ruby, Go, Scala), Coinbase 80 (Go), Affirm 67, Robinhood 48 |
| **Security** (314) | Python 61%, Go 39%, Rust 15%, Java 11% | AWS 46%, Kubernetes 35%, GCP 32%, containers 27% | Anthropic 22, OpenAI 15, Cloudflare 15, CoreWeave 15 |
| **Product backend / full-stack** (1,251) | Python 42%, Go 33%, C++ 25%, Java 20%, TypeScript 20%, Rust 18% | Kubernetes 31%, AWS 23%, React 21% | OpenAI 106, Roblox 81, Databricks 74 |

**By domain (all levels).** Each cell is AI-infra % / backend %.

| | AI / BE |
|---|---|
| **Languages** | |
| Python | 55% / 42% |
| Go | 30% / 30% |
| Rust | 20% / 12% |
| C++ | 18% / 19% |
| Java | 6% / 23% |
| TypeScript | 11% / 15% |
| SQL | 6% / 15% |
| CUDA | 6% / 1% |
| Kotlin | 1% / 6% |
| Ruby | 0% / 7% |
| **Tools** | |
| Kubernetes | 33% / 27% |
| AWS | 20% / 30% |
| GCP | 16% / 20% |
| Docker/containers | 21% / 15% |
| Linux | 17% / 8% |
| Terraform | 11% / 12% |
| PyTorch | 9% / 4% |
| RDMA/InfiniBand | 9% / 0% |
| Kafka | 4% / 8% |
| Spark | 6% / 9% |
| Prometheus | 7% / 5% |
| Postgres | 3% / 6% |
| gRPC | 2% / 4% |
| vLLM | 4% / 0% |
| Ray | 4% / 2% |
| **AI-product terms** | |
| "agents" | 38% / 35% |
| LLMs | 30% / 19% |
| RAG | 10% / 8% |
| MCP | 4% / 5% |

**Early vs senior+ postings (n = 120 / 1,800):**
- Python 60% / 46%, C++ 39% / 19%, Java 39% / 19%, JavaScript 37% / 5%,
  Go 31% / 33%, Rust 9% / 16%.
- Intern postings list languages generically ("one or more of Python, Java,
  JavaScript/TypeScript, Go, or C++"), as at
  [Pinterest](https://www.pinterestcareers.com/jobs/?gh_jid=7838591).
  Senior postings name the team's actual stack.
- **Implication:** at L1 one strong language plus fundamentals is enough to
  pass screens. The niche language (Go, C++/CUDA, Rust) matters more when he
  joins a team.

**Language recommendation for the harness's company stacks.**
- **Backend and infra companies:** Python plus **Go**.
- **Inference and GPU companies:** **C++ with CUDA/Triton**, and Rust for
  routers and runtimes.
- **Payments companies:** Java/Kotlin or Ruby is realistic, but lower value
  for this learner's goals.
- **Data companies:** SQL is non-negotiable.

---

## 4. Interview topics, ranked

### 4.1 The 2026 loop for these roles

| Round | Who runs it (evidence) | Harness analogue |
|---|---|---|
| No-AI DSA/coding screen | Meta keeps one classic round ([HI](https://hellointerview.com/blog/meta-ai-enabled-coding)); Cursor's screens allow no AI beyond autocomplete **[RL report]**; Anthropic forbids AI in live interviews unless told ([Anthropic guidance](https://www.anthropic.com/candidate-ai-guidance)) | Unaided ownership-change request; fundamentals click-quiz |
| AI-enabled coding in a multi-file codebase (fix bug → implement → optimize under larger inputs) | Meta, since Oct 2025; Canva requires AI ([canva.dev](https://canva.dev/blog/engineering/yes-you-can-use-ai-in-our-interviews)); Mechanize AI take-home, then defend the code **[RL report]** | review-to-own → add-your-part |
| Progressive practical build (each level extends your code; e.g. in-memory DB with TTL) | Anthropic CodeSignal (candidate reports, [1point3acres](https://www.1point3acres.com/interview/thread/1049492)) | add-your-part with staged hidden tests |
| Debugging an unfamiliar repo ("bug squash") | Stripe (candidate reports, [Interview Query](https://www.interviewquery.com/guides/stripe-software-engineer)) | incident / review-to-own |
| Integration (read API docs, wire it up, handle errors) | Stripe (candidate reports) | add-your-part against a mock vendor API |
| Code review of PRs | Anthropic onsite: 4 PRs with Claude Code, explain and improve one (one candidate, Aug 2026 — **unverified**, [PracHub](https://prachub.com/interview-experiences/anthropic-software-engineer-interview-experience-reviewing-and-improving-pull-requests-with-claude-code)); JPMorgan ~70-line MR review ([HI](https://www.hellointerview.com/community/questions/merge-request-review/cmh72k850011s08advgj5nxcs)); a vendor calls it a growing format ([levelop](https://levelop.dev/blog/why-companies-are-moving-from-solve-this-problem-to-explain-this-code), opinion) | review-to-own |
| System design (classic and ML/LLM) | Universal from mid-level; weighted heaviest at senior ([HI](https://www.hellointerview.com/learn/system-design/in-a-hurry/introduction)) | design-review |
| Project deep dive / work trial | Cursor: "share an exceptional technical project", 2–3 short technicals, then an onsite small project ([posting](https://jobs.ashbyhq.com/cursor/d0e5b41d-84ab-4887-bd3a-55589b11dd7b)); paid work trials at small startups ([Casco](https://casco.com/blog/how-we-hire)) | build + demo |
| Values / culture | Anthropic's culture round reportedly eliminates the most candidates (prep-site claim) | manager 1:1s (out of scope here) |
| Paper discussion: defend or critique a paper's method and extensions | Research Scientist tracks, e.g. DeepMind (prep guide, **unverified**); not found in SWE loops | LIT memo, plus a design-review on the paper |

Karat's survey of 400 engineering leaders backs this shift.
- **71%** say AI makes technical skills harder to assess.
- **62%** still ban AI in interviews.
- Take-homes and automated tests lose signal fastest, so live interviews
  become more valuable
  ([Karat 2026](https://karat.com/engineering-interview-trends-2026); vendor
  survey).

### 4.2 Top 25 topics

Ranked by frequency in the sources combined with importance for an L1 → L3
path into these roles. "Level" is where the topic starts being asked.

**Sources behind the ranking:**
- Hello Interview's 32-problem catalog and core concepts
  ([HI](https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview)).
- aced.io/Exponent's 2026 categories (candidate-reported, attributions
  unverified)
  ([aced.io](https://www.aced.io/blog/how-to-nail-the-system-design-interview)).
- Company round formats (4.1).
- Concept counts in the 3,056 postings, AI % / BE %: observability 49 / 48;
  scheduling/orchestration 35 / 24; incident/root cause 25 / 23;
  authn/authz/encryption 24 / 26; profiling/benchmarks 22 / 12; API/protocol
  19% BE; GPU kernels/memory 17% AI; multi-tenancy/isolation/sandbox 17% AI;
  queues/messaging 13% BE; evals 13% AI; load balancing/routing 11 / 8;
  caching 8 / 7; SLO/tail latency 9 / 6; distributed training 5 / 0.4.

| # | Topic | Round | Level | Evidence | Harness tags |
|---|---|---|---|---|---|
| 1 | Extending or fixing a multi-file codebase you didn't write | practical / AI-enabled | L1 | Meta, Anthropic, Stripe, Canva | READ, CODE, DEBUG |
| 2 | Root-causing a bug from failing tests or logs | debugging | L1 | Stripe bug squash, Meta phase 1 | DEBUG, READ |
| 3 | DSA problem without AI (hashing, graphs, heaps, intervals) | screen | L1 | Meta classic round; 48% of early postings | CODE |
| 4 | Concurrency follow-ups: make it concurrent, find the race, thread-safe cache | practical | L1–L3 | Anthropic reports; SingleStore, Databricks postings | OS, CODE |
| 5 | Reviewing a PR (incl. AI-written): find bugs, judge design, approve or not | code review | L1–L5 | Anthropic (report), JPMorgan, Dropbox ladder | REVIEW, SEC |
| 6 | API design and integration: errors, pagination, idempotency, versioning | integration / SD | L1–L3 | Stripe integration; HI core concept | API |
| 7 | Data modelling, indexing, transactions | SD | L2–L3 | HI core concepts; payment, Ticketmaster problems | DB |
| 8 | Caching: cache-aside, invalidation, hot keys, distributed cache | SD | L2–L3 | HI core concept + Distributed Cache problem | DB, PERF |
| 9 | Scaling reads/writes: sharding, partitioning, consistent hashing, replication | SD | L3 | HI core concepts and patterns | DIST, DB |
| 10 | Contention: reservations, flash sale, auction (locks, optimistic concurrency, queues) | SD | L3 | HI Ticketmaster, Flash Sale, eBay; "Dealing with Contention" | DIST, DB |
| 11 | Rate limiter and quotas (incl. LLM API rate limits and fallback) | SD / practical | L2–L3 | HI, aced (Robinhood-style chatbot prompt) | DIST, API |
| 12 | Queues, job scheduler, long-running tasks: retries, idempotency, at-least-once | SD | L3 | HI Job Scheduler, Long Running Tasks; Kafka/Temporal deep dives | DIST, DATA |
| 13 | Payment system / ledger: double-entry, idempotency keys, reconciliation | SD | L3 | HI Payment System (Stripe); 455 fintech postings | DIST, DB, API |
| 14 | Metrics/logging/monitoring pipeline: time series, aggregation, top-K | SD | L3 | HI Metrics Monitoring (Datadog), Ad Click Aggregator, YouTube Top K | DATA, OBS |
| 15 | LLM serving system with latency SLOs: TTFT/TPOT, continuous batching, KV cache, routing, autoscaling | ML SD | L3+ (AI) | aced AI category #1; Perplexity-style prompt ([Codemia](https://codemia.io/practice/design-an-llm-serving-system-at-low-latency), unverified); Baseten/Anthropic postings | MLSYS.serve, PERF |
| 16 | Reliability: timeouts, retries, backoff, failure modes, safe rollout, degradation | SD follow-ups | L2+ | on-call in 27–37% of mid/senior postings; Dropbox SEV expectations | OBS, DIST, INFRA |
| 17 | Real-time fan-out: chat, live comments, notifications (websockets/SSE) | SD | L3 | HI WhatsApp, FB Live Comments, Notification System | NET, DIST |
| 18 | Search and retrieval: inverted index, ranking, vector search, filtered ANN | SD | L3 | HI Post Search + Vector DB deep dive; 165 search-niche postings | DB, ML.llmapp |
| 19 | Batch inference / GPU-cluster scheduling and compute allocation (bin-packing, preemption, fairness) | ML SD | L3+ (AI) | aced (Anthropic batch inference API; allocating compute); Together posting | MLSYS, INFRA |
| 20 | Inference-engine internals walkthrough: admission → prefill → decode, paged KV, out-of-memory behaviour | ML deep dive | L2+ (AI) | AMD onsite (Sept 2026, **unverified**, [PracHub](https://prachub.com/interview-questions/trace-an-llm-request-through-a-paged-kv-inference-engine)); Baseten | MLSYS.serve |
| 21 | GPU memory and throughput math: KV-cache size, parameter memory, roofline | ML deep dive / estimation | L2+ (AI) | prep guides ([techinterview](https://www.techinterview.org/post/3233476388/designing-an-llm-serving-system/)); Baseten "where time and memory go" | MLSYS, PERF |
| 22 | Distributed training: data/tensor/pipeline parallelism, all-reduce, checkpointing, stragglers | ML SD | L3+ (AI) | aced (distributed training system); prep guides ([techinterview](https://www.techinterview.org/post/3233477286/distributed-training-interview-questions/)) | MLSYS.train, DIST |
| 23 | Model-weight / artifact distribution to thousands of machines | ML SD | L3+ (AI) | aced (constrained link); Anthropic posting ("deployment pipelines for releasing new models") | DIST, NET, INFRA |
| 24 | Agentic system design: tools, sandboxing, safeguards, evals | ML SD | L3+ | aced (Anthropic agentic system; safeguards); agents in 35–38% of postings; sandbox roles in [RL report] | ML.llmapp, SEC |
| 25 | Project deep dive: defend design choices, numbers, and what you'd change | deep dive | L1+ | Cursor, Mechanize, Canva ("explain … what you'd improve") | COMM, EXEC |

**Cross-cutting for every SD topic:** back-of-envelope estimation ("Numbers to
Know"), stating trade-offs, and handling a follow-up that raises scale 10×.
The harness's design-review teammate should ask for all three every time.

---

## 5. What separates candidates in 2026

1. **They verify AI output and can explain every line.** This is now written
   into L1 postings:
   - Vercel: "explain and debug every line you ship".
   - Stripe: "review, refine, and validate all outputs".
   - Pinterest: AI "as an iterative coding partner … while exercising strong
     judgment around accuracy, security, and when to ask for help".
   - Cursor: "AI tools as leverage without giving up correctness".
   - Datadog interns: "experience using AI coding tools or a strong interest"
     ([posting](https://careers.datadoghq.com/detail/8052118/?gh_jid=8052118)).

   Meta's AI-enabled round marks candidates down for using AI "as a crutch".
   The bar: "You should be controlling AI … always need to be in control"
   ([HI](https://hellointerview.com/blog/meta-ai-enabled-coding), prep-site
   quotes of internal guidance).
2. **They can read and debug code they didn't write.** This was always part of
   the job. It is now *tested* (bug squash, Meta phase 1) because AI makes
   codebases grow faster than people understand them ("comprehension debt",
   [Osmani](https://addyosmani.com/blog/comprehension-debt/)). Charity Majors:
   writing code is not the hard part, operating and understanding it is
   ([via Willison](https://simonwillison.net/2024/Jun/12/generative-ai-is-not-going-to-build-your-engineering-team/)).
3. **They measure.** Infra postings describe the job as first-principles
   measurement: "where time and memory go" (Baseten), "explain performance
   problems quantitatively" (prep guides). The [RL report] found the common
   hiring pattern is "a well-documented, measurable, reproducible worklog".
4. **They own production, early.** Honeycomb puts an *Engineer I* on call
   after ~90 days. Together: "You build it, you own it". Dropbox IC1 already
   expects SEV participation. On-call language is in 37% of senior postings.
5. **They show work that can be reviewed, not claims.** Cursor *requires* "an
   app, OSS, or shipped product we can open and review". Vercel's intern bonus is "a
   merged pull request to an open-source project". Scale's new-grad posting
   lists "open source contributions or a portfolio of shipped side projects"
   as a nice-to-have
   ([posting](https://job-boards.greenhouse.io/scaleai/jobs/4730836005)). See
   the [RL report] for the maintainer/hiring-manager quotes.
6. **They still pass fundamentals without AI.** Postings and loops are
   bimodal: AI-allowed practical rounds *plus* a no-AI round.
   - DSA/fundamentals appear in 48% of early postings.
   - Anthropic's candidate policy: "no AI assistance unless we indicate
     otherwise" in live interviews.
   - AWS's Garman argues juniors are valuable for learning "how to think for
     ourselves … critical thinking"
     ([The Register](https://www.theregister.com/2025/08/21/aws_ceo_entry_level_jobs_opinion/)).
7. **System design depth is what makes someone senior.** It is the largest
   gradient in postings (21% → 69%). HI: the senior "works through the basics
   leaving time … to show off the depth".
8. **They write clearly.** Communication terms in ~10–17% of postings at every
   level. Dropbox expects "evidence-based" interview feedback and trade-off
   sharing from IC1.
9. **In AI infra, they turn new research into running systems, and they
   check it first.** Fireworks wants people who "insist on rigorously
   reproducing published results". Perplexity wants someone who reads "a
   research paper on Monday" and ships a kernel by Wednesday. For an L1 this
   is a portfolio advantage more than a screening requirement: only 6% of
   early postings ask for it. A reproduction with a deviations list and an
   ablation is the "measured, reproducible" evidence the [RL report] found
   hiring managers reward.

**Market context for planning (2026):**
- Indeed: US software postings rose ~15% after Feb 2025 while all postings
  fell ~7% (secondary coverage of a July 2026 Hiring Lab analysis,
  [OfficeChai](https://officechai.com/ai/us-software-job-postings-are-up-15-since-launch-of-claude-code-while-overall-job-postings-are-down-7-indeed-data/)).
  The claim that **71% of the increase was senior** roles is **unverified
  against Indeed's own page**. Indeed's own Jan 2026 update says jobs
  mentioning AI are growing while overall hiring is weak
  ([Hiring Lab](https://www.hiringlab.org/2026/01/22/january-labor-market-update-jobs-mentioning-ai-are-growing-amid-broader-hiring-weakness)).
- LeadDev 2025: 18% of 880+ leaders expect fewer junior hires within 12 months
  and 54% expect a long-term reduction (via LeadDev coverage;
  [report](https://leaddev.com/the-ai-impact-report-2025)).
- DORA 2025: AI "amplifies what's already there", so strong practices matter
  more
  ([Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report)).
- Shopify made "reflexive AI usage" a baseline expectation and added AI-usage
  questions to performance reviews
  ([BetaKit](https://betakit.com/shopify-ceo-tobi-lutke-tells-employees-to-prove-ai-cant-do-the-job-before-asking-for-resources/)).

**Harness takeaway:** the harness should grade two skills separately.
(a) **Unaided** craft: no-AI phases, voice defence of the diff.
(b) **AI-directed** delivery: spec-first, verified output, review of AI PRs.
The Anthropic trial suggests AI teammates should default to *conceptual
coaching* during learning tasks. The patterns that kept learning were
conceptual inquiry and generate-then-ask-why; the ones that lost it were full
delegation and AI-driven debugging.

---

## 6. Curriculum implications

### 6.1 Front-load (months 1–3, L1 → L2)

Ordered by evidence of what L1 screens and first-90-day jobs demand.

1. **READ + DEBUG** (every week)
   - *Why:* bug-squash and AI-enabled rounds; Dropbox IC1; Affirm's
     early-career requirements.
   - *Tasks:* review-to-own and small incidents. The first phase of each runs
     with AI teammates in coach-only mode.
2. **TEST + REVIEW** (on every task)
   - *Why:* "validate all outputs" clauses; Willison; review rounds. Every PR
     he opens needs a test that fails without the change, and every PR he
     reviews is scored on recall and precision.
3. **CODE, unaided, in Python + Go**
   - *Why:* Go is the #2 language in both domains (30%), and the harness
     companies' backend and infra stacks should use it.
   - A weekly no-AI ownership change plus a small DSA drill keeps no-AI
     screens passable (48% of early postings name fundamentals).
4. **DB + API basics**
   - *Why:* most-cited SD core concepts; Stripe-style integration rounds.
   - *Tasks:* EXPLAIN-plan perf-hunt, idempotent endpoint, safe migration.
5. **OBS + first incidents**
   - *Why:* on-call from day ~90 (Honeycomb Engineer I); observability in 55%
     of mid postings.
   - *Tasks:* instrument a service, write an SLO alert, run a P2 to
     mitigation, write a postmortem.
6. **PERF methodology**
   - Benchmarks with variance, a profile before optimizing, and estimates
     checked against measurement. This is the habit behind "measured,
     reproducible worklog" ([RL report]).
7. **OS concurrency**
   - Race and deadlock tasks with a race detector. Anthropic-style
     "make it concurrent" follow-ups.
8. **LIT, light touch: one paper or blog per month**
   - *Why:* paper-born techniques dominate inference and training postings
     (33–38%), but L1 postings rarely ask for them (6%).
   - *Tasks:* critical-reading quiz, then a scoped toy reproduction.
     Prefer papers behind techniques the company codebase already uses, so
     the reading feeds READ.

### 6.2 Next (months 4–6, L2 → L3)

- **DIST** with fault injection.
- **SD** through design-review on HI-core topics (#6–#14 above).
- **INFRA**: Docker, local Kubernetes, canary and rollback.
- **`MLSYS.serve`** (his strongest niche fit). This must be a *different
  deliverable* from his Rust engine, e.g. a scheduler, router or KV-cache
  policy inside a teammate-built server, graded on a request trace.
- **DATA** basics: idempotent pipeline, Kafka consumer lag.
- **LIT, full loop:** memo → flagged PR → benchmark, with a calibration
  score. Pair this with `MLSYS.serve` (e.g. a disaggregation or
  speculative-decoding paper) and DB (e.g. a query-optimization paper), so
  each paper ends in an objectively graded perf-hunt or experiment.

### 6.3 Later (months 7–12, L3 → L4)

- **`MLSYS.gpu`** in C++/CUDA/Triton (Together's GPU intern track),
  **`MLSYS.train`** (checkpoint, parallelism, data loader), and deeper SEC
  (sandboxing, tenant isolation).
- Leadership behaviours: mentoring the junior AI, leading design reviews,
  owning a quarter-sized goal with estimates. These count for little in L1
  postings (mentoring others 1%) but are required by L4–L5.

### 6.4 What the placement interview should test

Five core blocks (A–E) plus an optional paper block (F), 3–3.5 h in
total. Each block fits one session, so it can run
over 3–5 sessions. Every block yields a per-skill starting level (L0–L3; the
harness should not place anyone above L3 at intake).

| Block | Time | Content | Scoring |
|---|---|---|---|
| A. Codebase dive (READ, DEBUG, CODE) | 60 min | Seeded ~5k-LOC Python service, three phases like Meta's: (1) click-to-answer comprehension questions, then reproduce and fix a planted bug, **no AI**; (2) implement a small feature, **AI allowed**; (3) a larger hidden input exposes a performance flaw to fix | answers checked by running; fail→pass reproducer; hidden tests; voice "explain this line" on 3 random lines of the phase-2 diff |
| B. PR review (REVIEW, SEC, TEST) | 40 min | An AI-teammate PR with 6 planted issues: 2 correctness, 1 concurrency, 1 security, 1 performance, 1 missing test or design smell, including one AI-typical made-up API call | recall, precision, severity match; proposed tests are run |
| C. Measure-and-fix (PERF, DB, OS) | 45 min | Slow endpoint + harness benchmark: profile, name the hotspot *before* fixing, fix to threshold; EXPLAIN-plan question; a race-detector finding to explain | hotspot prediction vs profiler; p95 target; quiz |
| D. Design-lite (SD, API, DIST, COMM) | 45 min | Senior teammate asks, e.g., "rate-limited gateway in front of an LLM API", with level-calibrated follow-ups (10× load, provider outage) | rubric: requirements, estimate, API, data model, failure modes, trade-offs |
| E. Fundamentals quick-fire | 15–20 min | Click quizzes: Big-O, isolation anomalies, TCP/HTTP, threads vs async, KV-cache memory arithmetic, what a p99 means | auto-scored; tags weak areas for the drill system |
| F. Paper read (LIT), optional | 20 min | A 2-page excerpt of a real systems or ML paper (abstract, method figure, results table) plus a one-paragraph description of "our" workload. Six click questions: claim, baseline, metric, the figure that carries the claim, one assumption that fails for our workload, expected gain direction | auto-scored; sets the starting LIT level only, never the overall level |

**Placement rules:**
- Place at the *lowest* level that passes A and B. These two match L1 screens
  and are the hardest skills to fake with AI.
- Block D sets the starting difficulty of design-review tasks only.
- Re-run blocks A and B every ~6 weeks as a progress check (fresh repo, fresh
  planted bugs), so "level" stays based on evidence.

---

### Unverified or weak claims used above
- Meta AI-round internals: prep-site and press reports, no official Meta doc.
- Stripe round content: candidate reports.
- Anthropic onsite PR-review round: a single candidate report.
- AMD paged-KV interview question: a candidate report.
- aced.io/Exponent company attributions: self-reported.
- Indeed "71% senior" figure: secondary coverage only.
- LeadDev percentages: from LeadDev's coverage of its own report.
- Google/Meta level equivalences: secondary.
- Keyword-regex shares: proxies with some noise; small samples flagged where
  n < 30.
- DeepMind paper-discussion round: a prep guide that cites no sources.
- LIT keyword shares: research-engineer titles n=57 and early-career n=120
  are small samples. The "paper-born technique" counts treat a named
  technique as evidence of paper-reading demand, which is an inference.
