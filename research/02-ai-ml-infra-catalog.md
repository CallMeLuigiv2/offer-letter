# 02 — AI/ML Infrastructure: niche map, companies, and project catalog

Prepared 2026-10-19 for Offer Letter (research brief: `BRIEF.md`). Scope: the AI/ML
infrastructure domain, split into niches, turned into 7 fictional companies and 73 project
cards (14 explicitly paper/blog-inspired "try <paper> in production" cards, 2 per company,
some cross-domain), plus 20+ real OSS repos with workable issues.

**Conventions**
- Sources are inline links. **(unverified)** = I could not confirm from a primary source;
  **(secondary)** = taken from a third-party summary of a primary source; **(memory)** = a
  stable URL I cited from prior knowledge without re-fetching it this session.
- Issue numbers and label counts were pulled with the GitHub API on **2026-10-19**; they go
  stale fast.
- **Thresholds in done-conditions are provisional.** The harness should calibrate each one by
  running the reference solution and the baseline on Luigi's machine (RTX 4070 12 GB, 5900X,
  32 GB) and setting the bar relative to those (e.g. "≤ 0.25× baseline p99"). Absolute numbers
  are given so the builders know the intended scale.
- **Paper/blog-inspired cards** (marked ★ in the index; IDs -09…-12) add two fields:
  **Paper / blog** and **What it claims**. Their done-condition is split into
  **Reproduce** (the paper's headline effect on a small local setup, within a stated
  tolerance) and **Apply** (the technique working in the company's codebase). Cross-domain
  sources: airline revenue management (CPL-10), industrial quality control (SLG-09),
  psychometrics (BLJ-09), ecology statistics (MTH-10).
- **Idea-bank cross-reference:** cards that match a seed in `06-paper-idea-bank.md` carry
  an "Idea-bank seed: P##" line. Bank seeds that fit these companies but have no card
  here yet, as future extensions:
  - Kilnworks: P01 (SIEVE/S3-FIFO for KV-cache eviction), P27 (constrained JSON),
    P39 (Kalman autoscaling), P41 (learned SJF), P46 (honey-bee replica allocation)
  - Loopline: P29 (selective recompute)
  - Coldplate/Loopline: P45 (spot under deadlines)
  - Plumbline: P13 (binary fuse filters), P16 (io_uring read path)
- Fictional names (Kilnworks, Coldplate, Loopline, Plumbline, Sluicegate, Belljar, Mothlight)
  were web-searched; none matched a company in this space. (Rejected because they were taken:
  Nightjar, a real conservation edge-AI camera company; Shoal, an existing object-storage
  vector DB; Hermitcrab, an OSS agent runtime.)

---

## 0. Top findings (for the builders)

1. **The real work sits around the engines, not inside them.** Job posts describe operating
   and tuning engines and building tools around them. Baseten's model-performance role
   productionizes "quantization, speculative decoding, kv cache reuse, chunked prefill and
   LoRA" inside vLLM, SGLang and TensorRT
   ([posting](https://inferencejobs.com/companies/baseten/jobs/software-engineer-model-performance)).
   Together's forward-deployed engineers tune KV-cache settings to hit customer targets
   ([posting](https://jobs.generalcatalyst.com/companies/together-ai-2/jobs/77877285-forward-deployed-engineer-inference-post-training)).
   CoreWeave hires Go engineers for fleet lifecycle, health and remediation
   ([MetalDev](https://www.builtinla.com/job/staff-software-engineer-metaldev/10753620)), and
   E2B wants an orchestrator whose sandboxes start in ≤ 200 ms
   ([posting](https://jobera.com/job/e2b-platform-engineer-384e63f2/), job board). So most cards
   target **in-house tooling**: load generators, routers, admission control, health agents,
   eval gates, compaction, skew detectors, warm pools. This also keeps them clear of Luigi's
   existing engine, HNSW and compiler projects.
2. **Measuring correctly is a ticket class in itself, and the best planted-bug material.**
   Closed-loop load generators hide stalls (coordinated omission,
   [wrk2](https://github.com/giltene/wrk2)). "GPU utilization" can read 100% while doing zero
   math ([Trainy](https://trainy.ai/blog/gpu-utilization-misleading)). Evals need SEMs,
   clustered SEs and paired tests
   ([Anthropic](https://www.anthropic.com/research/statistical-approach-to-model-evals)).
   34 SWE-bench Lite problems have flaky tests ([Large Language Monkeys](https://arxiv.org/abs/2407.21787)).
   In synchronous training every rank shows the same step time, so naive straggler detectors
   can't work. turbopuffer measures recall on 1% of live traffic
   ([architecture](https://turbopuffer.com/docs/architecture)).
3. **Reliability numbers to anchor every incident card.** Llama 3 pre-training saw 466
   interruptions in 54 days; 419 were unexpected and ~78% of those were hardware
   ([paper](https://arxiv.org/abs/2407.21783)). Imbue saw ~10% of hosts fail to boot and ~3% of
   machines break each week, and open-sourced its health checks
   ([write-up](https://imbue.com/research/70b-infrastructure/),
   [cluster-health](https://github.com/imbue-ai/cluster-health)). NCCL watchdog timeouts give
   generic errors with no stack, which is why PyTorch built Flight Recorder
   ([blog](https://pytorch.org/blog/flight-recorder-a-new-lens-for-understanding-nccl-watchdog-timeouts/)).
4. **A single 12 GB GPU forces trace replay, simulators and fault injection.** Real teams do
   the same: DistServe-style capacity simulation, Alibaba's fragmentation work replayed in a
   scheduler simulator ([clusterdata](https://github.com/alibaba/clusterdata)), and public
   cluster traces from [Philly](https://github.com/msr-fiddle/philly-traces) and
   [Alibaba PAI](https://www.usenix.org/conference/nsdi22/presentation/weng). The harness
   should ship these traces plus a docker-compose kit (vLLM, Prometheus, Grafana, ClickHouse,
   MinIO, toxiproxy, Redpanda, Redis, Label Studio).
5. **Hot 2025–26 themes worth tickets:**
   - KV-cache-aware routing and prefill/decode disaggregation
     ([llm-d](https://llm-d.ai/blog/kvcache-wins-you-can-see), [Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models))
   - cold starts ([Modal GPU snapshots](https://modal.com/blog/gpu-mem-snapshots))
   - object-storage-native search (turbopuffer)
   - filtered ANN ([pgvector 0.8 iterative scans](https://www.postgresql.org/about/news/pgvector-080-released-2952/),
     [Weaviate ACORN](https://docs.weaviate.io/weaviate/concepts/filtering))
   - embedding-model migrations ([Drift-Adapter](https://arxiv.org/abs/2509.23471))
   - quantization accuracy gating (a [500k-evaluation study](https://arxiv.org/abs/2411.02355))
   - agent sandboxes and snapshots ([E2B](https://docs.e2b.dev/sandbox/snapshots))
   - OTel GenAI agent conventions, still "Development"
     ([spec](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans))
6. **Papers make strong "try this in prod" tickets when a small setup reproduces the
   headline.** Examples that fit 12 GB or one CPU box:
   - KIVI's 2-bit KV cache
   - PowerSGD on gloo ranks with `tc`-capped bandwidth
   - HSTU on MovieLens-1M (paper Table 4: HR@10 .3043 vs SASRec .2828)
   - learned indexes on SOSD
   - tinyBenchmarks IRT on public leaderboard item data
   - Gavel in a simulator
   - the Tail-at-Scale hedging trade-off (~5% extra load)
   Cross-domain methods map cleanly onto infra problems: airline protection levels → GPU
   block inventory; CUSUM process control → feature drift; IRT → cheap evals; occupancy
   models → detector-aware ecology reports.

---

## 1. Niche map

Eleven candidate niches were examined. Seven companies cover them: some niches are merged
where real companies merge them (recsys with training infra, edge with CV, eval/observability
with agent infra, quantization tooling with inference).

| Niche | Richness for projects | Company here |
|---|---|---|
| LLM inference serving & optimization | very high | **Kilnworks** |
| Model compression / quantization tooling | high | Kilnworks (+ Mothlight) |
| GPU cloud / cluster scheduling | very high | **Coldplate** |
| Training infra & distributed training | very high | **Loopline RTP** |
| Recommendation & ranking systems | high | Loopline RTP |
| Vector search / retrieval infra | high | **Plumbline** |
| ML data platforms (features, quality, labels, curation) | high | **Sluicegate** |
| ML evaluation & observability | high | **Belljar** (+ Kilnworks gate) |
| Agent-platform infra (sandboxes, tools, tracing) | high | Belljar |
| Computer-vision products | medium-high | **Mothlight** |
| On-device / edge inference | medium-high | Mothlight |

### 1.1 LLM inference serving & optimization → Kilnworks
- **Who / what:** API providers and platforms (Together, Fireworks, Baseten, Modal, Anyscale),
  self-hosted stacks (vLLM, SGLang, TensorRT-LLM, NVIDIA Dynamo, llm-d), and app companies
  with heavy inference (Character.AI).
- **Hardest real problems**
  1. *KV-cache locality across replicas.* Round-robin scatters shared prefixes. llm-d moved
     from approximate to precise prefix-cache scheduling using vLLM KV events
     ([blog](https://llm-d.ai/blog/kvcache-wins-you-can-see),
     [scorers](https://llm-d.ai/blog/intelligent-inference-scheduling-with-llm-d)). An SGLang
     page reports ~3× output throughput and 2× faster TTFT vs round-robin on Llama 3.1 70B
     ([page](https://docs.sglang.io/docs/advanced_features/llm-d), single source).
     Character.AI routes each dialogue to the same server and keeps a tree-structured
     inter-turn KV cache, reported at a 95% hit rate
     ([summary](https://buttondown.com/ainews/archive/ainews-shazeer-et-al-2024), secondary;
     the original `research.character.ai/optimizing-inference/` now redirects).
  2. *Prefill/decode interference vs. SLOs.* DistServe serves 7.4× more requests within SLO by
     splitting the phases ([paper](https://arxiv.org/abs/2401.09670)); Dynamo productizes this
     with a KV-aware router and NIXL transfers
     ([NVIDIA](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models)).
  3. *Admission, fairness and autoscaling.* GPU utilization stays near 100% during decode
     whatever the load, so scaling on it fails; use queue depth and KV pressure
     ([llm-d autoscaling](https://llm-d.ai/docs/guides/workload-autoscaling)). The VTC paper
     proposes token-level fair scheduling because rate limits waste capacity
     ([OSDI'24](https://arxiv.org/abs/2401.00588)). vLLM has an open "help wanted" issue for
     priority preemption of running requests
     ([#40004](https://github.com/vllm-project/vllm/issues/40004)).
  4. *Quantization without silent quality loss.* Across 500k+ evaluations: FP8 is ~lossless,
     well-tuned INT8 loses 1–3%, and W4A16 is competitive
     ([paper](https://arxiv.org/abs/2411.02355)).
  5. *Cold starts and spiky traffic.* Modal added CPU, then GPU, memory snapshots; its docs
     claim 3–10× faster starts for init-heavy functions
     ([blog](https://modal.com/blog/gpu-mem-snapshots),
     [docs](https://modal.com/docs/guide/memory-snapshots)).
  - Also: CPU-side grammar overhead in structured output grows with batch size
    ([XGrammar](https://arxiv.org/abs/2411.15100),
    [vLLM blog](https://vllm.ai/blog/2025-01-14-struct-decode-intro)). Static speculators
    decay as workloads drift ([Together ATLAS](https://www.together.ai/blog/adaptive-learning-speculator-system-atlas)).
- **Typical stack:**
  - Python (vLLM/SGLang)
  - CUDA/Triton kernels
  - Go for gateways and routers (llm-d router,
    [Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/))
  - Rust in hot paths (Dynamo, HF TEI)
  - Kubernetes and Prometheus
- **Team shapes:**
  - model-performance engineers
  - inference platform: routing, autoscaling, multi-tenancy
  - forward-deployed engineers who tune customer deployments
  - benchmarking/eval owners (GuideLLM came from this role at Neural Magic/Red Hat:
    [article](https://developers.redhat.com/articles/2025/06/20/guidellm-evaluate-llm-deployments-real-world-inference))

### 1.2 Model compression / quantization tooling → Kilnworks, Mothlight
- **Who:** llm-compressor (vLLM project), torchao, bitsandbytes, GPTQ/AWQ toolchains, NVIDIA
  Model Optimizer/TensorRT, ExecuTorch quantizers.
- **Problems:**
  - accuracy gating with statistics (above)
  - calibration-set choice
  - kernel availability per GPU architecture
  - robustness: INT8 YOLOv8 TensorRT engines run 1.5–3.3× faster than FP32 but lose 3–7
    mAP50-95, and the nano model loses > 60% (relative) under medium Gaussian noise
    ([arXiv 2508.19600](https://arxiv.org/abs/2508.19600))
- **Teams:** usually inside an inference or edge org rather than standalone. There are open
  issues to start on, e.g. [llm-compressor #3300](https://github.com/vllm-project/llm-compressor/issues/3300).

### 1.3 GPU cloud / cluster scheduling → Coldplate
- **Who:**
  - neoclouds: CoreWeave, Lambda, Crusoe, Nebius, Together GPU clusters
  - marketplaces: SF Compute
  - schedulers: Kueue, NVIDIA KAI (the open-sourced Run:ai scheduler), Slurm, SkyPilot, HAMi
  - internal platform teams
- **Hardest real problems**
  1. *Fleet health and acceptance.* At Imbue, ~10% of 511 hosts failed to boot at first, about
     a quarter needed PCIe reseating, and ~1,800 alerts came from flapping IB ports; their
     advice is 10–20% spare capacity ([Imbue](https://imbue.com/research/70b-infrastructure/)).
     Together's acceptance suite runs DCGM diag, gpu-burn, single- and multi-node NCCL,
     nvbandwidth and IB bandwidth, and keeps failing nodes out
     ([docs](https://docs.together.ai/docs/health-checks)). NVIDIA's XID catalog drives
     triage: XID 13 is usually an app bug, 48 an uncorrectable ECC error needing reset, 79
     means the GPU "fell off the bus"
     ([NVIDIA](https://docs.nvidia.com/deploy/xid-errors/contents.html),
     [Crusoe](https://support.crusoecloud.com/hc/en-us/articles/28336238021915-XID-Errors-Observed-in-Dmesg)).
  2. *Gang and topology scheduling, and fragmentation.* Gang scheduling and locality
     constraints hurt utilization ([Philly ATC'19](https://arxiv.org/abs/1901.05758)). Alibaba
     studied GPU fragmentation in "Beware of Fragmentation" (ATC'23), referenced from
     [clusterdata](https://github.com/alibaba/clusterdata). Gang scheduling is a headline KAI
     feature ([New Stack](https://thenewstack.io/nvidia-open-sources-kai-scheduler-to-help-ai-teams-optimize-gpu-utilization/)).
  3. *Multi-tenant quotas.* Kueue cohorts borrow unused quota; fair sharing preempts toward
     weighted shares ([preemption](https://kueue.sigs.k8s.io/docs/concepts/preemption/),
     [ClusterQueue](https://kueue.sigs.k8s.io/docs/concepts/cluster_queue)).
  4. *Sharing a GPU without isolation.* KAI reserves a memory slice but gives no memory
     isolation (New Stack, above). HAMi-core enforces caps by intercepting CUDA calls through
     `LD_PRELOAD` ([HAMi-core](https://github.com/Project-HAMi/HAMi-core),
     [Kubex](https://kubex.ai/blog/making-shared-gpus-even-safer-with-kubex-and-hami-core)).
  5. *Honest utilization accounting.* "GPU util" is the fraction of time any kernel runs, so a
     single-SM kernel reads 100% ([Trainy](https://trainy.ai/blog/gpu-utilization-misleading)).
  6. *Allocating scarce blocks.* SF Compute runs an order book of GPU×time blocks: orders are
     not reservations, buys default to immediate-or-cancel, and customers can resell
     ([market](https://sfcompute.com/docs/market), [orders](https://docs.sfcompute.com/current/orders)).
- **Stack:**
  - Go: controllers and fleet services (Kueue and KAI are Go)
  - Python: health checks
  - C for interception shims
  - DCGM exporter, Prometheus, Slurm, Ansible
- **Team shapes**, from CoreWeave postings: fleet provisioning automation, fleet monitoring &
  analysis ([posting](https://www.efinancialcareers.com/jobs-Poland-Warsaw-Senior_Software_Engineer_Fleet_Monitoring_Analysis.id24513471)),
  bare metal ("MetalDev"), server fleet infra with Kubernetes operators
  ([posting](https://builtin.com/job/software-engineer-infrastructure/4703413)), scheduler,
  SRE.

### 1.4 Training infrastructure & distributed training → Loopline RTP
- **Who:** frontier labs; big-tech training platforms (Meta, Google); ByteDance (MegaScale);
  recsys trainers (Pinterest, Netflix); Databricks/Mosaic.
- **Hardest real problems**
  1. *Interruptions and recovery* (Llama 3 numbers above; > 90% effective training time).
     Async checkpointing cut IBM's 7B checkpoint downtime from 148.8 s to 6.3 s
     ([PyTorch blog](https://pytorch.org/blog/reducing-checkpointing-times/)). TorchTitan
     reports 5–15× lower checkpoint overhead ([paper](https://arxiv.org/abs/2410.06511)).
     torchft adds per-step fault tolerance via a Lighthouse quorum
     ([repo](https://github.com/meta-pytorch/torchft)).
  2. *Hangs.* Watchdog errors are generic and causes span CPU-side divergence, GPU hangs and
     misconfigured collectives (Flight Recorder blog;
     [tutorial](https://docs.pytorch.org/tutorials/intermediate/debug_hangs_with_flight_recorder.html)).
  3. *Fail-slow stragglers.* GUARD (MLSys 2026) reports up to 1.7× higher mean FLOPs
     utilization and cut step variance from 20% to 1%
     ([poster](https://mlsys.org/virtual/2026/poster/3608)). See also Google Cloud
     ([blog](https://cloud.google.com/blog/products/compute/stragglers-in-ai-a-guide-to-automated-straggler-detection)),
     ByteDance's what-if study (stragglers are not always hardware,
     [arXiv 2505.05713](https://www.emergentmind.com/papers/2505.05713)), and Imbue (Python
     GC on single workers slowed the whole run).
  4. *Input-bound training.* Pinterest's ranker ran at 880k examples/s against 5M when
     compute-bound, and was fixed with Ray-based loading
     ([summary](https://www.zenml.io/mlops-database/pinterest-ml-platform-evolution-with-ray-talks-deep-dives-ray-based-distributed-data-loading-for-recommender-model-train),
     secondary; its throughput figures are internally inconsistent).
  5. *Memory.* OOM triage with memory snapshots
     ([PyTorch](https://pytorch.org/blog/understanding-gpu-memory-1/)). Cross-entropy logits
     can dominate memory: 24 GB → 1 MB for Gemma 2 2B with Cut Cross-Entropy
     ([arXiv](https://arxiv.org/abs/2411.09009)).
  6. *Efficiency accounting.* MegaScale reached 55.2% MFU on 12,288 GPUs
     ([paper](https://arxiv.org/abs/2402.15627)). Google ships a goodput/badput library
     ([docs](https://docs.cloud.google.com/tpu/docs/goodput)).
- **Stack:**
  - Python/PyTorch: FSDP2, DCP, torchtitan-style trainers, TorchRec
  - C++/CUDA, NCCL
  - Slurm or Kubernetes, object storage, Ray Data
- **Team shapes:** training platform, reliability and fault tolerance, data loading,
  performance (MFU), recsys/embedding infra, plus the model teams as internal customers.

### 1.5 Recommendation & ranking systems → Loopline RTP
- **Who:** Pinterest, Netflix, Meta, ByteDance, Spotify.
- **Problems:**
  - data-loading-bound training (above)
  - embedding-table sharding against HBM/DDR limits ([TorchRec planner](https://pytorch.org/torchrec/concepts.html))
  - consolidating many models into one foundation model: Netflix's autoregressive transformer
    is consumed through an Embedding Store, as a subgraph, or by fine-tuning
    ([summary](https://www.zenml.io/llmops-database/foundation-model-for-personalized-recommendation-at-scale),
    secondary)
  - GPU serving (Pinterest +16% Home feed engagement:
    [NVIDIA](https://blogs.nvidia.com/blog/pinterest-gpu-acceleration-recommenders/))
  - in-batch-negative sampling bias in two-tower retrieval (Yi et al., RecSys 2019:
    [Google Research](https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/), memory)
- **Stack:** PyTorch + TorchRec/FBGEMM, C++ serving with TorchScript and CUDA Graphs (per a
  [Pinterest posting](https://www.builtinseattle.com/job/sr-staff-software-engineer-product-ml-infrastructure/11448988)),
  Spark, Ray.

### 1.6 Vector search / retrieval infra → Plumbline
- **Who:** turbopuffer, Pinecone, Weaviate, Qdrant, Milvus/Zilliz, LanceDB/Lance, pgvector,
  Elastic/OpenSearch.
- **Hardest real problems**
  1. *Filtered search.* Post-filtering "overfilters" (pgvector, fixed by 0.8.0 iterative
     scans and better planner costing). Weaviate made ACORN its default from v1.34 for
     low-correlation filters
     ([docs](https://docs.weaviate.io/weaviate/concepts/filtering),
     [blog](https://weaviate.io/blog/speed-up-filtered-vector-search)). VDBBench tests filter
     selectivity from 50% to 99.9%
     ([VDBBench 1.0](https://zilliz.com/blog/vdbbench-1-0-benchmarking-with-your-real-world-production-workloads)).
  2. *Freshness and deletes.* Tombstones degrade recall and bloat indexes; FreshDiskANN queues
     deletes and merges in the background ([arXiv](https://arxiv.org/abs/2105.09613)). A
     course note cites HNSW 5-recall@5 falling from ~98% to ~88% over 20 update batches
     ([notes](https://khoury.northeastern.edu/home/pandey/courses/cs7800/spring26/notes/IVF-HNSW.pdf), secondary).
  3. *Memory cost.* RaBitQ gives bit codes with error bounds
     ([SIGMOD'24](https://arxiv.org/abs/2405.12497)). Elastic's BBQ derives from it and claims
     ~95% memory reduction; naive binary codes need 10–100× oversampling
     ([Elastic](https://www.elastic.co/search-labs/blog/better-binary-quantization-lucene-elasticsearch), vendor claims).
  4. *Object-storage-native architecture and cold starts.* turbopuffer pages give cold p50 of
     ~400–870 ms vs ~15 ms warm (the two pages disagree), with stateless compute, a WAL per
     namespace and an SPFresh-style centroid index
     ([architecture](https://turbopuffer.com/docs/architecture)). VDBBench's 2026 update adds
     cold-start and insert-readiness tests
     ([news](https://zilliz.com/news/vdbbench-cost-aware-vector-database-benchmarking)).
  5. *Multi-tenancy.* Weaviate tenants can be Active, Inactive or Offloaded (to S3)
     ([offloading](https://docs.weaviate.io/deploy/configuration/tenant-offloading),
     [states](https://docs.weaviate.io/weaviate/manage-collections/tenant-states)).
  6. *Embedding-model upgrades.* Mixing model versions makes similarity meaningless
     ([Zilliz FAQ](https://zilliz.com/ai-faq/change-embedding-model-without-reindexing)).
     Drift-Adapter (EMNLP'25) maps new queries into the old embedding space so a re-index can
     be deferred ([arXiv](https://arxiv.org/abs/2509.23471)).
- **Stack:** Rust (Qdrant, Lance, LanceDB, TEI; turbopuffer reportedly Rust, unverified), Go
  (Milvus, Weaviate), C (pgvector), Java (Lucene); Arrow/Parquet; S3.
- **Team shapes:** core index, storage/compaction, query planner, cloud control plane,
  SDK/devex, benchmarks.

### 1.7 ML data platforms → Sluicegate
- **Who:**
  - feature platforms: Tecton, Chalk, Feast, Airbnb Chronon, Uber Michelangelo
  - data quality: Great Expectations, Soda, Uber D3/Hue
  - labels: Label Studio, cleanlab, Argilla
  - LLM data curation: HF datatrove, NeMo Curator
  - versioning: lakeFS, DVC
- **Hardest real problems**
  1. *Point-in-time correctness.* Chronon promises "temporally accurate backfills"
     ([Airbnb](https://airbnb.tech/opensource/chronon/)). Feast's TTL is measured relative to
     each entity row's timestamp
     ([docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)).
  2. *Online/offline skew.* Uber Hue checks online-offline parity and can block promotions
     ([Uber](https://www.uber.com/en-IN/blog/raising-the-bar-on-ml-model-deployment-safety/)).
     Google's Rule #29: "save the set of features used at serving time"
     ([Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)).
  3. *Silent data regressions.* "The most impactful ones are generally silent"
     ([Uber D3](https://www.uber.com/blog/d3-an-automated-system-to-detect-data-drifts)).
  4. *Real-time freshness and latency.* Tecton serves "100K+ QPS with millisecond latency"
     ([posting](https://builtin.com/job/staff-software-engineer-realtime-data/7080774)); Chalk
     targets an online path under 5 ms ([docs](https://docs.chalk.ai/docs/architecture)).
  5. *Label noise.* Test sets average 3.3% label errors, ImageNet val ~6%
     ([Northcutt et al.](https://arxiv.org/abs/2103.14749)).
  6. *Dedup at scale.* FineWeb found per-dump MinHash beat global dedup
     ([arXiv 2406.17557](https://arxiv.org/abs/2406.17557)). One user reports datatrove's
     MinHash stage ran over 3 h 50 min on sample-10BT without finishing
     ([forum](https://discuss.huggingface.co/t/fastdedup-rust-based-dataset-deduplication-benchmarks-on-fineweb-sample-10bt/173672),
     single report).
- **Stack:**
  - Python SDKs
  - SQL engines (Spark, DuckDB)
  - Scala/Java (Chronon on Spark/Flink), Go (Feast feature server)
  - Kafka, Redis, DynamoDB
  - Parquet/Iceberg
- **Team shapes:**
  - realtime execution and realtime data
    ([Tecton](https://jobs.lever.co/tecton/928ddfbd-0977-409f-a70e-708f746ea055))
  - batch/backfill, online store, SDK
  - forward-deployed engineers
  - feature-store teams inside big companies
    ([Datadog](https://careers.datadoghq.com/detail/7050412))

### 1.8 ML evaluation & observability → Belljar (and Kilnworks' quant gate)
- **Who:** Langfuse, Arize Phoenix, Braintrust, W&B Weave, promptfoo, UK AISI inspect_ai,
  EleutherAI lm-evaluation-harness, MLflow GenAI. Job postings suggest Langfuse now belongs to
  ClickHouse ([posting](https://jobs.thrivecap.com/companies/clickhouse/jobs/94824335-technical-customer-support-engineer-ai-infrastructure-observability-emea), unverified).
- **Hardest real problems:**
  1. *Statistical validity:* SEM, clustered SEs, pairing, power
     ([arXiv 2411.00640](https://arxiv.org/abs/2411.00640)).
  2. *Judge reliability:* the strongest MT-Bench judge gave the same verdict under answer
     swapping only ~65% of the time ([arXiv 2306.05685](https://arxiv.org/abs/2306.05685)).
     Position bias is systematic and varies by judge and task
     ([arXiv 2406.07791](https://arxiv.org/abs/2406.07791)).
  3. *Infra-noisy evals:* flaky tests; a serial SWE-bench Lite run took days, 32 machines cut
     it to hours ([Epoch](https://epoch.ai/latest/swebench-docker); layered images in the
     [harness](https://swebench.com/SWE-bench/reference/harness)).
  4. *Trace storage at agent scale:* Langfuse moved from Postgres to ClickHouse in v3
     (Dec 2024), turned updates into inserts on ReplacingMergeTree, and moved to an
     observation-centric model in 2026
     ([eng post](https://langfuse.com/resources/engineering/clickhouse-at-agent-scale),
     [2026](https://langfuse.com/blog/2026-03-10-simplify-langfuse-for-scale)).
  5. *Standards churn:* OTel GenAI agent spans are still "Development".
  6. *Brittle answer extraction:* e.g. [lm-eval #2552](https://github.com/EleutherAI/lm-evaluation-harness/issues/2552).
- **Stack:** Python and TS SDKs, ClickHouse, OTel, Postgres.
- **Team shapes:** ingestion/storage, SDK and instrumentation, eval product, solutions.

### 1.9 Agent-platform infrastructure → Belljar
- **Who:** E2B, Modal Sandboxes, Daytona, Fly Machines, Northflank, durable-execution vendors.
- **Hardest real problems:**
  1. *Isolation vs. density.* Firecracker gives each VM its own kernel; gVisor is a userspace
     kernel ([Fly.io](https://fly.io/learn/firecracker-vs-gvisor/),
     [Northflank](https://northflank.com/blog/firecracker-vs-gvisor)).
  2. *Start latency.* E2B snapshots capture memory plus filesystem
     ([docs](https://docs.e2b.dev/sandbox/snapshots)), against a 200 ms start target (posting
     above). A competitor claims pausing costs ~4 s per GB of RAM
     ([Fly vs E2B](https://fly.io/learn/fly-vs-e2b/), vendor claim).
  3. *Cloning safety.* Every clone resumes with the same kernel RNG state; reseed after
     restore ([Firecracker](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/random-for-clones.md)).
  4. *Side effects on retries.* A tool times out after its write succeeded, the agent retries,
     and the action happens twice
     ([urandom.io](https://urandom.io/blog/2026-03-03-agentic-ai-idempotency-retries-and-compensation)).
     The standard fix is idempotency keys
     ([Stripe](https://docs.stripe.com/api/idempotent_requests)).
  5. *Eval infra at scale* (SWE-bench, above).
- **Stack:** Rust (Firecracker); Go (orchestrator and in-VM daemon; E2B's
  [runtime](https://github.com/e2b-dev/runtime) repo is Go); TS/Python SDKs; Nomad/Terraform
  ([E2B SRE posting](https://startup.jobs/sre-infrastructure-engineer-e2b-8145070), job board).
- **Team shapes**, from E2B postings:
  - core virtualization in Rust
    ([Systems Engineer](https://jobs.insightpartners.com/companies/e2b/jobs/56631629-systems-engineer))
  - platform/orchestrator
  - product backend, ~80% Go
    ([posting](https://www.builtinsf.com/job/product-engineer-backend-developer/10243084))
  - SRE/BYOC

### 1.10 Computer-vision products and 1.11 on-device / edge inference → Mothlight
- **Who:**
  - edge runtimes: ExecuTorch 1.0 (Oct 2025; runs in Meta's apps for billions of users:
    [PyTorch](https://pytorch.org/blog/introducing-executorch-1-0/)), ONNX Runtime,
    TensorRT/Jetson, llama.cpp
  - CV products: Frigate NVR (OSS); Ultralytics/Roboflow
  - conservation tech: Nightjar's TrailGuard AI edge cameras
    ([RESOLVE](https://resolve.ngo/projects/trailguard-ai-and-nightjar)); Google SpeciesNet,
    trained on 65M+ images with 2,000+ labels
    ([TechCrunch](https://techcrunch.com/2025/03/03/google-releases-speciesnet-an-ai-model-designed-to-identify-wildlife/),
    [repo](https://github.com/google/cameratrapai)); MegaDetector
    ([docs](https://megadetector.readthedocs.io/en/latest/getting-started.html))
- **Hardest real problems:**
  1. *Quantization loss and robustness* (arXiv 2508.19600, above).
  2. *Generalizing to new sites:* models are excellent where trained and poor at new camera
     locations ([Beery et al., ECCV'18](https://arxiv.org/abs/1807.04975)).
  3. *Labeling cost:* active learning matched state of the art with ~14.1k labels on 3.2M
     images (> 99.5% less labeling, [Norouzzadeh et al.](https://arxiv.org/abs/1910.09716)).
  4. *Blank filtering:* treating "no detection" as empty cut performance by up to 18.5%
     ([arXiv 2410.12769](https://arxiv.org/abs/2410.12769)); MegaDetector sorts blanks at
     ~95% recall ([ODU poster](https://digitalcommons.odu.edu/knowledge_expo/2026expo/postersession2/40)).
  5. *Backend churn:* Frigate dropped its TensorRT detector from the amd64 build in July 2025
     in favor of ONNX ([discussion](https://github.com/blakeblackshear/frigate/discussions/18605)).
- **Stack:** PyTorch, ONNX, TensorRT, ONNX Runtime/ExecuTorch, C++ device code, Label Studio.
- **Team shapes:** ML training/eval, embedded/firmware, data ops/labeling, MLOps/fleet.

---
## 2. Fictional companies and project cards

Shared rules for every card below:
- **AI teammates write scaffolding, fixtures, simulators, other services and planted-bug
  PRs. Luigi writes the core of his ticket.**
- **Hardware fit.** Every GPU step fits 12 GB: ≤ 8B models at 4-bit for serving, ≤ 3B BF16
  as a quality reference, small CV and recsys models for training.
- **Postmortems** are graded by a template checker. Required sections: timeline, impact, root
  cause, why detection failed, actions with owners.

---

## Kilnworks — "open models, served hot": a serverless + dedicated LLM inference API

- **Niche / domain:** LLM inference serving and optimization, plus quantization tooling.
- **Stage:** growth. Series B, ~120 people, ~40 engineers. Serves ~30 open models on a shared
  serverless tier and runs dedicated deployments for enterprises.
- **Culture:** benchmark-driven ("no perf claim without a trace and a p99"). Every PR that
  touches the hot path needs a before/after replay. Weekly incident review, blameless but
  blunt. Deadlines come from customer launches, through the FDE.
- **Stack, and why:**
  - Python for engine integration: vLLM and SGLang are Python-first.
  - Go for gateway and router: llm-d's router and the Gateway API Inference Extension are
    Go; Envoy ext-proc ecosystem.
  - Rust only in token-heavy hot paths, as Dynamo and HF TEI do.
  - Prometheus/Grafana; ClickHouse for request logs and billing; Kubernetes in prod,
    docker-compose locally.
- **Team roster:** EM (Inference Platform), tech lead (routing/scheduling), staff
  model-performance engineer, 2 peers (gateway; autoscaling), PM (dedicated deployments),
  forward-deployed engineer, junior engineer (benchmarks), on-call SRE.
- **Main codebase sketch:**
  - `kiln-gateway/` (Go): OpenAI-compatible API, auth, rate limits, usage metering to
    ClickHouse.
  - `kiln-router/` (Go): endpoint-picker scorers (load, prefix, LoRA).
  - `kiln-engine/` (Python): vLLM launch profiles, config registry, health probes.
  - `kiln-bench/` (Python): trace-replay load generator, SLO reports, regression bot.
  - `kiln-evals/` (Python): quality gates for new checkpoints and quantizations.
  - `deploy/`: docker-compose with 1–2 vLLM servers (Qwen2.5-1.5B or an 8B INT4 model, e.g.
    Qwen3-8B-AWQ), gateway, Prometheus, Grafana, ClickHouse.
- **In-house tools this company would build:** trace-replay load generator, SLO regression
  bot, prefix-aware router, tenant-fair admission controller, usage metering reconciler,
  quantization acceptance gate, P/D capacity planner, speculative-decoding policy
  controller, known-good launch-profile registry, KV-cache dashboard.
- **Inspired by:**
  - Together AI ([ATLAS](https://www.together.ai/blog/adaptive-learning-speculator-system-atlas),
    [FDE posting](https://jobs.generalcatalyst.com/companies/together-ai-2/jobs/77877285-forward-deployed-engineer-inference-post-training))
  - Baseten ([posting](https://inferencejobs.com/companies/baseten/jobs/software-engineer-model-performance))
  - Modal ([snapshots](https://modal.com/blog/gpu-mem-snapshots))
  - Character.AI ([summary](https://buttondown.com/ainews/archive/ainews-shazeer-et-al-2024))
  - Red Hat / llm-d ([blog](https://llm-d.ai/blog/kvcache-wins-you-can-see))
  - NVIDIA Dynamo
  - Neural Magic: GuideLLM and the [quantization study](https://arxiv.org/abs/2411.02355)
- **Projects:** KLN-01 … KLN-11. Paper/blog-inspired: ★KLN-10 (Tail at Scale) and ★KLN-11 (KIVI). KLN-06 (VTC) and KLN-09 (DistServe) are also built on papers.

### KLN-01 Fix the load generator before we trust its p99
- Company: Kilnworks   Type: review-to-own   Level: L1
- **Real-world grounding:** release gates rely on trace-replay generators
  ([GuideLLM](https://developers.redhat.com/articles/2025/06/20/guidellm-evaluate-llm-deployments-real-world-inference),
  [inference-perf](https://github.com/kubernetes-sigs/inference-perf)). Closed-loop
  generators hide stalls (coordinated omission: [wrk2](https://github.com/giltene/wrk2),
  [ScyllaDB](https://resources.scylladb.com/blog/on-coordinated-omission)). Benchmark
  trustworthiness is a live upstream problem:
  [LMCache #5402](https://github.com/LMCache/LMCache/issues/5402) "make flaky vllm_bench
  throughput comparisons reproducible".
- **Ticket:** "Priya's PR adds `kiln-bench replay`: open-loop Poisson arrivals from a recorded
  trace, streaming TTFT/ITL/E2E, p50/p90/p99, JSON output for the regression bot. We're about
  to gate releases on it. Review it hard; once it merges, you own it."
- **Stack:** Python asyncio + httpx. It's the team's tooling language, and GuideLLM and
  inference-perf are Python.
- **Skills:** TEST, PERF, READ, MLSYS
- **Size:** 5 h in 4 blocks:
  1. read and run against the mock server (60 min)
  2. review comments + quiz (60)
  3. fixes and tests (90)
  4. voice explanation + ownership change (60)
- **Built by AI vs. by him:** AI writes the PR (~600 lines) and a mock OpenAI-compatible
  server with a programmable latency distribution, which is the harness ground truth. He
  writes the review comments, the fixes and the regression tests.
- **Done-condition:**
  - He flags ≥ 4 of 5 planted bugs (the harness matches comment locations and explanations).
  - After his fixes, run against the mock with known injected latency (including a 2 s stall
    every 30 s): reported p99 TTFT and p99 ITL are within ±5% of ground truth at 3 load
    levels.
  - His new tests fail on the original PR (mutation check).
- **Planted bugs:**
  1. When `--rate` is set it still issues the next request only after the previous one
     completes (coordinated omission).
  2. The TTFT clock starts at send time instead of scheduled time, and stops on the first
     SSE chunk even when that is the empty role delta.
  3. Output tokens are counted with `len(text.split())` instead of the server's `usage` or a
     tokenizer.
  4. The overall p99 is the mean of per-request p99s.
  5. Timed-out requests are dropped from the stats instead of counted as failures.
- **Ownership change request:** add `--slo ttft_p99=800ms,itl_p99=60ms`, which exits non-zero
  and names the SLO that failed.

### KLN-02 Prefix-cache-aware routing for multi-turn chat
- Company: Kilnworks   Type: add-your-part   Level: L2
- **Idea-bank seed** (`06-paper-idea-bank.md`): P22 (related: P05 bounded-load hashing, P04 Prequal)
- **Real-world grounding:** round-robin scatters shared prefixes. llm-d's precise prefix
  scorer consumes vLLM KV events ([blog](https://llm-d.ai/blog/kvcache-wins-you-can-see)).
  SGLang reports ~3× throughput vs round-robin
  ([page](https://docs.sglang.io/docs/advanced_features/llm-d), single source). Character.AI
  uses sticky sessions (secondary). The Gateway API endpoint picker scores KV utilization,
  queue length, prefix indexes and loaded LoRAs
  ([CNCF](https://www.cncf.io/blog/2025/04/21/deep-dive-into-the-gateway-api-inference-extension/)).
- **Ticket:** "The router has `least-queue` and `round-robin` scorers plus a `/metrics`
  scraper. Add a `prefix` scorer:
  - block-hash the first N tokens, aligned to the engine's block size
  - track which replica holds which blocks: approximate from routing history first, precise
    from KV events as a stretch
  - blend with load so one hot prefix can't melt a replica."
- **Stack:** Go. The router is Go, like llm-d's router and the EPP.
- **Skills:** MLSYS, DIST, PERF, SD
- **Size:** 10 h:
  1. approximate prefix index + consistent hashing with bounded loads (3 h)
  2. scorer weighting + simulator runs (3 h)
  3. real run on 2× vLLM Qwen2.5-1.5B on the 4070 at `gpu_memory_utilization=0.4` each (2 h)
  4. review pushback + write-up (2 h)
- **Built by AI vs. by him:**
  - AI builds the router skeleton, scorer interface and metrics scraper.
  - AI builds a replay simulator where prefill cost ∝ uncached tokens, with LRU KV eviction.
  - AI builds a multi-turn trace from a public chat dataset (check its license).
  - He writes the prefix index, scorer, load bound and tests.
- **Done-condition:**
  - Simulator trace at 80% capacity:
    - p99 TTFT ≤ 0.6× round-robin
    - prefix-cache hit rate ≥ 2× round-robin
    - max replica load ≤ 1.25× mean
  - Real 2-replica run: mean TTFT ≥ 25% better than round-robin (calibrated).
  - Unit tests cover hash collisions and replica removal.
- **Pushback hooks:**
  - The tech lead hashes raw text instead of token IDs ("the tokenizer is slow"), so the
    hashes don't line up with KV block boundaries.
  - A peer wants pure session-ID stickiness, which fails when sessions share a system prompt
    and when a replica dies.
- **Ownership change request:** when a replica drains, hand its affinity entries to the
  replicas that inherit its traffic instead of cold-starting everywhere.

### KLN-03 Short prompts stuck behind 30k-token documents
- Company: Kilnworks   Type: perf-hunt   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P24 (related: P41 learned SJF)
- **Real-world grounding:** chunked prefill and batching budgets are core tuning knobs (Baseten
  posting), and FDEs tune KV-cache settings to hit customer targets (Together posting). vLLM
  has an open "help wanted" issue,
  [#40004](https://github.com/vllm-project/vllm/issues/40004) "Priority scheduling supports
  preemption of requests in the running queue". DistServe describes the prefill–decode
  interference behind this ([arXiv](https://arxiv.org/abs/2401.09670)).
- **Ticket:** "A customer's chat traffic (short prompts) shares an 8B endpoint with a batch
  summarization job (20–30k-token prompts). Chat p99 TTFT went from 0.4 s to 4 s. Get it under
  800 ms without losing more than 10% of total token throughput. Config, priority classes or
  a scheduler patch are all fine, but justify it with traces."
- **Stack:** Python (vLLM config, optional scheduler patch) + kiln-bench/GuideLLM.
- **Skills:** PERF, MLSYS, DEBUG, COMM
- **Size:** 14 h:
  1. reproduce + baseline with an 8B INT4 model on the 4070 (2 h)
  2. read vLLM's scheduler: chunked prefill, `max_num_batched_tokens`, priority (3 h)
  3. experiment matrix (4 h)
  4. optional: a priority-aware chunk budget patch (3 h)
  5. report (2 h)
- **Built by AI vs. by him:** AI provides the mixed trace, launch scripts and dashboards. He
  writes the experiment plan, configs or patch, and the report.
- **Done-condition:**
  - The harness replays the mixed trace at fixed QPS, 3 runs; every run must pass.
  - Chat-class p99 TTFT ≤ 800 ms (calibrated: ≤ 0.25× baseline).
  - Total output tok/s ≥ 90% of baseline.
  - The report includes at least one timeline/trace figure.
- **Pushback hooks:**
  - A peer suggests `max_model_len=8k`, which breaks the batch customer's contract.
  - The manager asks for a second GPU, which isn't in the budget.
- **Ownership change request:** add the "mixed-tenancy" scenario to kiln-bench CI.

### KLN-04 Quantization acceptance gate
- Company: Kilnworks   Type: experiment   Level: L3
- **Real-world grounding:** FP8 ~lossless, INT8 1–3% loss, W4A16 competitive
  ([arXiv 2411.02355](https://arxiv.org/abs/2411.02355)). Error bars need SEMs, clustered SEs
  and paired differences ([Anthropic](https://www.anthropic.com/research/statistical-approach-to-model-evals)).
  llm-compressor is the vLLM project's quantization tool, with open starter issues
  ([#3300](https://github.com/vllm-project/llm-compressor/issues/3300)).
- **Ticket:** "We ship ~4 quantized checkpoints a week. Last month an AWQ build with a bad
  calibration set shipped and code quality cratered for two days. Build `kiln-evals gate`.
  Given a BF16 reference and a candidate, it returns PASS/FAIL with error bars over a small
  task suite, plus a distribution check (token-level KL and top-1 agreement on fixed
  prompts)."
- **Stack:** Python, vLLM, numpy/scipy; lm-evaluation-harness tasks or our own.
- **Skills:** ML, TEST, MLSYS, DATA
- **Size:** 16 h:
  1. KL/top-1 agreement (4 h)
  2. task suite with paired bootstrap / clustered SE (5 h)
  3. decision rule + calibration on known candidates (4 h)
  4. CLI + report (3 h)
- **Built by AI vs. by him:**
  - AI makes 6 candidates of Qwen2.5-3B (the BF16 reference fits in 12 GB):
    1. FP8-dynamic
    2. W8A8-INT8
    3. good W4A16-GPTQ
    4. W4A16 calibrated on one repeated sentence
    5. AWQ with a group-size mismatch
    6. a lossless model whose chat template differs from the reference
  - He writes the gate, the statistics and the thresholds.
- **Done-condition:**
  - On the 6 known candidates plus 4 hidden ones, the verdicts match ground truth 10/10.
  - His 95% CIs on the paired difference cover the harness's large-sample "true" delta for
    ≥ 9/10 candidates.
  - ≤ 45 min per candidate on the 4070.
- **Pushback hooks:**
  - The lead proposes "fail if any benchmark drops > 1 point", which ignores noise: the SEM
    on a 500-item binary task is ~2 points.
  - The PM wants MMLU only.
- **Ownership change request:** add a chat-template/tokenizer drift check.
- *Overlap note:* adjacent to Luigi's planned quant runtime, but the deliverable here is an
  evaluation gate, not a runtime.

### KLN-05 Incident: preemption storm after "just raising max_model_len"
- Company: Kilnworks   Type: incident   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P40 adaptive concurrency limits
- **Real-world grounding:**
  - vLLM preempts and recomputes requests when the KV cache runs short. This hurts E2E
    latency, can be watched in Prometheus, and is tuned with `gpu_memory_utilization`,
    `max_num_seqs` and `max_num_batched_tokens`
    ([vLLM docs](https://docs.vllm.ai/en/v0.10.1/configuration/optimization.html)).
  - GPU utilization hides saturation ([llm-d](https://llm-d.ai/docs/guides/workload-autoscaling)).
- **Ticket (page):** "02:10. p99 E2E on `chat-8b` is up 9×, and 3% of requests return gateway
  5xx (timeouts). Change log: at 23:40 a config PR raised `max_model_len` from 8k to 32k for a
  new customer. The autoscaler says 'GPU util 99%, healthy'. You're on call."
- **Stack:** Python/vLLM, Prometheus, Grafana, Go gateway.
- **Skills:** OBS, DEBUG, MLSYS, COMM
- **Size:** 8 h:
  1. triage (90 min)
  2. root cause + mitigation (90)
  3. durable fix: a per-tenant max-input-tokens admission check in the gateway, and alerts on
     preemptions and KV usage (3 h)
  4. postmortem (2 h)
- **Built by AI vs. by him:** AI builds the local stack with the bad config, the incident
  traffic replay, and dashboards that at first show only GPU util. He writes the mitigation,
  the Go admission check, the alert rules and the postmortem.
- **Done-condition:**
  - Incident replay:
    - gateway 5xx < 0.1%
    - chat p99 E2E ≤ 1.5× pre-incident
    - the long-context customer's 32k requests still succeed within their SLO
  - His alert fires within 2 min on the bad config and stays silent on the fixed one.
  - The postmortem passes the checker.
- **Pushback hooks:**
  - The manager wants to roll back the customer's context length; the business says no.
  - A peer wants to autoscale on GPU util.
- **Ownership change request:** a pre-deploy "KV budget" check. It computes max concurrent
  sequences at a given `max_model_len` from the model config and refuses configs below a
  floor.

### KLN-06 Noisy-neighbor fairness for the shared serverless tier
- Company: Kilnworks   Type: build   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): P26 (related: P41, P43 DRF)
- **Real-world grounding:**
  - VTC (OSDI'24) shows rate limits under-use capacity and gives token-level fair scheduling
    with a 2× service-gap bound ([arXiv](https://arxiv.org/abs/2401.00588)).
  - vLLM [#40004](https://github.com/vllm-project/vllm/issues/40004) (priority preemption).
  - The Gateway API Inference Extension models request criticality; its API names changed
    between versions ([site](https://gateway-api-inference-extension.sigs.k8s.io/)).
- **Ticket:** "One tenant's batch job ate the shared tier on Tuesday. Build tenant-fair
  admission in the gateway:
  - per-tenant TPM/RPM limits with correct `429` + `Retry-After`
  - a work-conserving, plan-weighted fair queue in front of the engines, so idle capacity
    is still used."
  It starts with a design doc and review.
- **Stack:** Go (gateway). Single node first; Redis counters later.
- **Skills:** SD, DIST, API, PERF, TEST
- **Size:** 28 h. Design doc (4 h) → review, then:
  1. token-bucket limits + headers (6 h)
  2. VTC-style fair queue with streaming output-token accounting (8 h)
  3. estimating unknown output length, with correction (4 h)
  4. scenario tests + demo (6 h)
- **Built by AI vs. by him:** AI provides the gateway, a mock engine with a realistic
  throughput curve, and the scenario runner. He writes the design doc, limiter, fair queue,
  accounting and tests.
- **Done-condition** (real vLLM 1.5B or the calibrated mock):
  1. A floods at 10× its share: tenant B's p99 TTFT stays ≤ 1.3× its solo baseline.
  2. With A alone, A gets ≥ 90% of max throughput.
  3. Token-weighted Jain fairness ≥ 0.95 across 4 equal-weight backlogged tenants.
  4. A client that honors `Retry-After` never gets two consecutive 429s.
  5. Added gateway p99 ≤ 2 ms.
- **Pushback hooks:**
  - The lead's design charges prompt tokens only, so decode-heavy tenants starve others.
  - The PM wants hard per-tenant GPU partitions, which waste capacity.
- **Ownership change request:** burst credits (2× for 60 s after 10 idle minutes) without
  breaking scenario 1.

### KLN-07 Usage metering that finance can trust
- Company: Kilnworks   Type: review-to-own   Level: L2
- **Real-world grounding:** providers report cached prompt tokens separately and bill them at
  a discount ([OpenAI prompt caching](https://platform.openai.com/docs/guides/prompt-caching),
  memory). Usage-accounting bugs are common upstream:
  [inspect_ai #5815](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5815) "agent bridge
  drops reasoning_tokens from usage". Langfuse dedups at read time over ReplacingMergeTree
  ([post](https://langfuse.com/resources/engineering/clickhouse-at-agent-scale)).
- **Ticket:** "Deshawn's PR moves metering from engine logs into the gateway. It counts
  prompt, cached, completion and reasoning tokens per request, writes to ClickHouse, and
  rolls up nightly invoices. Review and own."
- **Stack:** Go + SQL (ClickHouse). Billing sits where the requests are.
- **Skills:** DB, TEST, API, READ
- **Size:** 6 h in 4 blocks (read + run, review + quiz, fixes, ownership change).
- **Built by AI vs. by him:** AI writes the PR, a replay set of 2,000 requests, and a
  ClickHouse fixture. He writes the review, fixes and tests.
- **Done-condition:**
  - Per-tenant invoices equal ground truth to the cent on the replay. The replay includes
    streams cut by client disconnects, retries and cached prefixes.
  - ≥ 4 of 5 planted bugs found.
- **Planted bugs:**
  1. A stream the client abandons is never billed, because usage arrives only in the final
     chunk.
  2. The cached-token discount is applied to all prompt tokens whenever any are cached.
  3. float64 dollars are rounded per line item, so cents drift.
  4. Gateway retries to another replica double-count prompt tokens.
  5. The rollup reads a ReplacingMergeTree without dedup, so at-least-once inserts double
     bill.
- **Ownership change request:** a per-tenant usage-anomaly query (z-score on tokens/hour).

### KLN-08 Speculative decoding: on, off, or per route?
- Company: Kilnworks   Type: experiment   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): P23
- **Real-world grounding:** static speculators "don't work well when their workload domain
  starts to shift". ATLAS adapts online; acceptance rose from 10% to 80% in an RL setting
  ([Together](https://www.together.ai/blog/adaptive-learning-speculator-system-atlas),
  [NeurIPS'25 talk](https://neurips.cc/virtual/2025/talk/127754)). Speculative decoding is a
  listed skill in the Baseten and Together postings.
- **Ticket:** "Spec decoding speeds up our code-edit traffic but slows chat at high batch.
  Measure acceptance and speedup by workload class × load level, for n-gram (prompt lookup)
  and for a small draft model. Then ship a routing policy that never loses to spec-off."
- **Stack:** Python (vLLM, kiln-bench) + a small Go change in the router.
- **Skills:** ML, PERF, MLSYS, DATA
- **Size:** 20 h:
  1. measurement matrix: 3 classes × 3 loads × 3 configs (6 h)
  2. break-even analysis (4 h)
  3. policy + router change (6 h)
  4. held-out evaluation + write-up (4 h)
- **Built by AI vs. by him:**
  - AI provides the traces and launch profiles: Qwen2.5-7B-AWQ as target, Qwen2.5-0.5B as
    draft, which together fit 12 GB.
  - Two 7B engines don't fit, so if vLLM can't toggle speculation per request (verify), the
    policy routes between two 1.5B instances.
  - He writes the measurement plan, analysis and policy.
- **Done-condition:**
  - Held-out mixed trace with a mid-run workload shift.
  - In every phase, tok/s ≥ max(spec-on, spec-off) − 5%.
  - No class's p99 ITL regresses more than 5% vs spec-off.
- **Pushback hooks:** the lead wants draft-model speculation on everywhere because a vendor
  blog says "up to 4×".
- **Ownership change request:** export per-class acceptance rate as a metric and alert when it
  drops below the measured break-even.

### KLN-09 Design review: disaggregated prefill/decode for the 70B tier
- Company: Kilnworks   Type: design-review   Level: L5
- **Idea-bank seed** (`06-paper-idea-bank.md`): P25
- **Real-world grounding:**
  - DistServe ([arXiv](https://arxiv.org/abs/2401.09670)) and NVIDIA Dynamo (NIXL, KV-aware
    router).
  - vLLM [#41230](https://github.com/vllm-project/vllm/issues/41230): document NIXL KV
    connector metrics.
  - Kueue [#11952](https://github.com/kubernetes-sigs/kueue/issues/11952): "Support
    DisaggregatedSet integration for disaggregated LLM inference".
- **Ticket:** "Sales sold a 70B tier with strict TTFT and ITL SLOs. A staff engineer proposes
  P/D disaggregation; ops says 'more moving parts'. Bring a capacity model and a
  recommendation: when P/D wins, what P:D ratio, what KV-transfer bandwidth we need, and
  what fails."
- **Stack:** Python (analytic model + small discrete-event simulator) + whiteboard.
- **Skills:** SD, MLSYS, PERF, COMM
- **Size:** 12 h:
  1. reading (3 h)
  2. roofline-style per-phase model (3 h)
  3. DES comparing colocated vs disaggregated (4 h)
  4. whiteboard session (2 h)
- **Built by AI vs. by him:** AI provides the reference simulator (hidden) and hardware specs.
  He writes the model and the recommendation.
- **Done-condition:**
  - For 4 scenarios (length mixes × SLOs), his predicted goodput is within 15% of the
    reference simulator.
  - His P:D ratio is within one step of the simulator's optimum in ≥ 3 of 4.
  - Whiteboard rubric covers KV-transfer stall, decode-pool OOM and router hot-spots.
- **Pushback hooks:** the staff engineer says P/D always wins. He must find the regime where it
  doesn't (short prompts, loose TTFT).
- **Ownership change request:** add prefix-cache hit rate to the model.


### KLN-10 Paper → prod: hedged and tied requests from "The Tail at Scale"
- Company: Kilnworks   Type: experiment (paper-inspired)   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P03
- **Paper / blog:** Dean & Barroso, "The Tail at Scale", CACM 2013
  ([Google Research](https://research.google/pubs/pub40801/), memory;
  [summary](https://blog.acolyer.org/2015/01/15/the-tail-at-scale/)).
- **What it claims:** sending a backup ("hedged") request only after the first has been
  outstanding longer than the 95th-percentile latency "limits the additional load to
  approximately 5% while substantially shortening the tail". "Tied" requests, which cancel the
  loser on the other server, cut median latency by 16% and the 99.9th percentile by 40% in a
  Google system. The paper also gives a BigTable example: a 10 ms hedge took p99.9 from
  ~1,800 ms to ~74 ms with ~2% more requests (memory, unverified).
- **Real-world grounding:** Kilnworks' dedicated deployments run several replicas, and
  customers have TTFT SLOs. A slow replica (GC pause, a long prefill ahead in its queue, a
  thermally throttled GPU) blows up p99 TTFT.
- **Ticket:** "Our team wants to try hedged + tied requests from *The Tail at Scale* in the
  gateway, for TTFT only. If the first token hasn't arrived by the p95 TTFT, send a hedge to a
  second replica. Use whichever streams first, cancel the other, and bill once. Reproduce the
  paper's trade-off on our stack, then decide if it ships."
- **Stack:** Go (gateway). Cancellation must also abort the engine-side request, or the GPU
  work is wasted.
- **Skills:** PERF, DIST, MLSYS, API
- **Size:** 14 h:
  1. read + simulator reproduction of the paper's curves (4 h)
  2. gateway hedge + cancel (5 h)
  3. 2-replica real run (2× Qwen2.5-1.5B on the 4070) with injected per-replica stalls (3 h)
  4. write-up (2 h)
- **Built by AI vs. by him:** AI provides the gateway, a stall injector (random 0.5–2 s pauses
  on one replica) and the billing hooks. He writes the hedge policy, cancellation, the
  simulator reproduction and the analysis.
- **Done-condition:**
  - **Reproduce:** in his simulator (two-server model with a heavy-tailed service time),
    hedging at p95 adds 3–7% extra work and cuts p99.9 by ≥ 50% vs. no hedging. This matches
    the paper's "~5% load" shape.
  - **Apply:** on the real run, p99 TTFT ≤ 0.6× the unhedged baseline, with extra GPU
    prefill-tokens ≤ 8%.
  - Cancelled hedges abort engine-side within 200 ms (checked in vLLM metrics).
  - Usage metering bills exactly one completion per request.
- **Pushback hooks:**
  - A peer wants to hedge every request immediately (2× load).
  - The PM asks whether hedging breaks prefix-cache affinity from KLN-02; he must measure the
    interaction.
- **Ownership change request:** adaptive hedge delay that tracks the live p95 per model.

### KLN-11 Paper → prod: 2-bit KV cache (KIVI) to fit more concurrent chats
- Company: Kilnworks   Type: experiment (paper-inspired)   Level: L4
- **Paper:** Liu et al., "KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache",
  ICML 2024 ([arXiv 2402.02750](https://arxiv.org/abs/2402.02750),
  [code](https://github.com/jy-yuan/KIVI)).
- **What it claims:** quantize keys per-channel and values per-token to 2 bits, keeping a
  small full-precision residual window. Llama, Falcon and Mistral keep "almost the same
  quality" with 2.6× less peak memory (weights included), up to 4× larger batches, and
  2.35–3.47× throughput.
- **Real-world grounding:** on a 12–24 GB card, KV cache capacity limits concurrency (see
  the KLN-05 preemption storm). vLLM ships an FP8 KV cache, and llm-d has an open "help
  wanted" to validate KV-cache-quantized serving
  ([llm-d-router #1365](https://github.com/llm-d/llm-d-router/issues/1365)).
- **Ticket:** "Our team wants to know if KIVI-style 2-bit KV is worth integrating beyond
  FP8. Reproduce KIVI's quality and memory claims on a small model:
  - FP16 vs. FP8 vs. KIVI-2 vs. naive per-token INT2 (the ablation that shows why the
    asymmetry matters)
  - a capacity model: max concurrent 4k-token chats on our 8B endpoint at each KV format."
- **Stack:** Python/PyTorch + the KIVI reference code (HF Transformers path) on Qwen2.5-1.5B
  or Llama-3.2-1B; vLLM for the FP8 baseline.
- **Skills:** ML, MLSYS, PERF, DATA
- **Size:** 20 h:
  1. run KIVI's reference and reproduce one of its long-context tables at small scale (6 h)
  2. naive INT2 ablation (3 h)
  3. memory/batch measurement on the 4070 (5 h)
  4. capacity model + recommendation (4 h)
  5. review (2 h)
- **Built by AI vs. by him:** AI provides the eval scaffolding (a LongBench subset, a GSM8K
  subset) and memory probes. He writes the ablation, measurements, capacity model and
  recommendation.
- **Done-condition:**
  - **Reproduce:** KIVI-2 stays within 1.5 points of FP16 on the chosen subsets.
  - **Ablation:** naive per-token INT2 for keys loses ≥ 5 points. This is the paper's key
    insight; if it doesn't show up he must explain why.
  - Measured KV memory per token at 2 bits is ≤ 0.2× FP16, within 10% of his formula.
  - His capacity model predicts max concurrency at each format within 10% of a harness run.
  - The write-up states a clear ship/no-ship given the vLLM integration cost.
- **Pushback hooks:**
  - The lead says "FP8 KV is free in vLLM, why bother".
  - A peer quotes the paper's 3.47× as if it transfers to our hardware.
- **Ownership change request:** add a "residual length" sweep (full-precision recent tokens)
  and show the quality/memory knee.

---

## Coldplate — "GPU clusters that tell you the truth": block-rented H100/H200 clusters + a managed scheduler

- **Niche / domain:** GPU cloud ("neocloud") and cluster scheduling.
- **Stage:** seed → Series A. ~35 people, 2 data-center cages, ~4,000 GPUs. Customers are ML
  labs and enterprises renting 64–512-GPU blocks for weeks.
- **Culture:** hardware-scarred pragmatism ("the fleet is always partly broken"). Runbooks for
  everything. Strict Go reviews on error handling. A Friday "burn-in board" review. Customers
  are ML researchers who notice every lost GPU-hour.
- **Stack, and why:**
  - Go: controllers, schedulers, fleet services. CoreWeave's MetalDev builds Go services for
    GPU data-center lifecycle; Kueue and KAI are Go.
  - Python: health checks, matching Imbue's cluster-health.
  - C for low-level shims, as HAMi-core is.
  - DCGM exporter + Prometheus; Kubernetes, plus Slurm for customers who want it.
  - Postgres for inventory, DuckDB for analytics.
- **Team roster:** founder-CTO, EM (fleet), scheduler tech lead, 2 SREs, hardware-ops lead,
  PM (marketplace), solutions engineer, junior engineer (dashboards).
- **Main codebase sketch:**
  - `fleetd/` (node agent: health checks, taints)
  - `cpl-sched/` (Go: queues, gang, topology)
  - `cpl-sim/` (Go discrete-event simulator replaying Philly/Alibaba traces)
  - `burnin/` (Python + CUDA stress kernels)
  - `ledger/` (usage/chargeback)
  - `market/` (block-time order book)
  - `cpl-vgpu/` (memory-cap shim)
  - `deploy/kind/` (kind cluster with a fake GPU device plugin)
- **In-house tools this company would build:** node health agent, burn-in/acceptance pipeline,
  scheduler simulator, fragmentation dashboard, idle-GPU reaper, chargeback ledger, GPU
  memory-cap shim, quota policy linter, market matching engine, XID triage bot.
- **Inspired by:**
  - CoreWeave postings ([MetalDev](https://www.builtinla.com/job/staff-software-engineer-metaldev/10753620),
    [fleet infra](https://builtin.com/job/software-engineer-infrastructure/4703413))
  - Together GPU clusters ([health checks](https://docs.together.ai/docs/health-checks))
  - Imbue ([write-up](https://imbue.com/research/70b-infrastructure/))
  - SF Compute ([market](https://sfcompute.com/docs/market))
  - NVIDIA KAI ([announcement](https://developer.nvidia.com/blog/nvidia-open-sources-runai-scheduler-to-foster-community-collaboration/))
  - Kueue, HAMi, Trainy
- **Projects:** CPL-01 … CPL-10. Paper-inspired: ★CPL-09 (Gavel) and ★CPL-10 (airline EMSR-b, cross-domain). CPL-07 also builds on Tsafrir et al.

### CPL-01 Review: the health agent that drained half the fleet
- Company: Coldplate   Type: review-to-own   Level: L1
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P49 survival analysis for bare-metal fleets
- **Real-world grounding:** Imbue's `health_checks`, `gpu_stress_test` and `host_validation`
  ([cluster-health](https://github.com/imbue-ai/cluster-health)); about a quarter of their
  hosts needed PCIe reseating. Together's acceptance suite. NVIDIA's XID semantics: 13 is
  usually an application bug, 48 uncorrectable ECC needs a reset, 79 is off the bus
  ([NVIDIA](https://docs.nvidia.com/deploy/xid-errors/contents.html),
  [Netdata on XID 13](https://www.netdata.cloud/guides/nvidia-gpu/nvidia-gpu-xid-13-graphics-engine-exception/)).
- **Ticket:** "Marta's PR adds `fleetd check`. It covers XID scan, ECC counters, PCIe link
  width/speed, thermals and throttle reasons, and outputs a JSON verdict plus a taint. Review
  and own."
- **Stack:** Python + pynvml/nvidia-smi, the same tooling style as Imbue's.
- **Skills:** DEBUG, OBS, READ, TEST
- **Size:** 5 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR and 40 labeled node snapshots (dmesg,
  `nvidia-smi -q`, sysfs). He writes the review, fixes and tests.
- **Done-condition:**
  - 40/40 fixture verdicts correct.
  - A live run on his 4070 produces a schema-valid report in < 10 s.
  - ≥ 4 of 5 planted bugs found.
- **Planted bugs:**
  1. Application XIDs (13/31/43) are classed as hardware, so healthy nodes get drained.
  2. Idle link *speed* is compared to max, but GPUs drop PCIe generation at idle; the check
     should look at width, or speed under load.
  3. The XID regex reads previous boots' logs (no boot-ID filter), so stale errors count
     forever.
  4. Aggregate (lifetime) ECC counters are used instead of volatile ones, so a node never
     recovers.
  5. Temperature thresholds in °C are compared with millidegree sysfs values.
- **Ownership change request:** add a flapping rule: fail → pass → fail within 24 h sends the
  node to `quarantine`, not `ready`.

### CPL-02 Gang scheduling with backfill in the cluster simulator
- Company: Coldplate   Type: add-your-part   Level: L2
- **Real-world grounding:** gang scheduling and locality constraints shaped utilization in
  Philly ([ATC'19](https://arxiv.org/abs/1901.05758),
  [traces](https://github.com/msr-fiddle/philly-traces)). KAI's headline features are gang
  scheduling and hierarchical queues. Kueue defines topology-aware scheduling to place pods for
  network throughput ([concepts](https://kueue.sigs.k8s.io/docs/concepts)).
- **Ticket:** "cpl-sim replays the Philly trace under FIFO. Add a gang scheduler with EASY
  backfilling and a topology preference (same node, then same leaf switch)."
- **Stack:** Go. The simulator shares policy code with cpl-sched.
- **Skills:** SD, DIST, OS, PERF
- **Size:** 10 h:
  1. gang placement (3 h)
  2. EASY backfill with head-of-queue reservation (4 h)
  3. topology scoring + pushback round (3 h)
- **Built by AI vs. by him:** AI builds the simulator core (event loop, node→leaf→spine
  model; cross-leaf jobs run at 0.8× speed), the trace loader, FIFO policy and metrics. He
  writes gang + backfill + topology + tests.
- **Done-condition** (2-week Philly slice):
  - mean JCT ≤ 0.75× FIFO
  - p95 queue wait ≤ 0.8× FIFO
  - zero partial gang allocations (invariant checker)
  - backfill never delays the head job's reservation (property test)
  - full run ≤ 60 s
- **Pushback hooks:**
  - The tech lead prefers conservative backfill.
  - A peer packs by GPU count and ignores topology.
- **Ownership change request:** emit `fragmentation_index`: free GPUs that can't fit the head
  job.

### CPL-03 Incident: allocation fell from 92% to 63% after the scheduler upgrade
- Company: Coldplate   Type: incident   Level: L3
- **Real-world grounding:** GPU fragmentation in production clusters (Alibaba "Beware of
  Fragmentation", ATC'23, via [clusterdata](https://github.com/alibaba/clusterdata)).
  Kubernetes packing vs spreading strategies
  ([bin packing](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/), memory).
  Missing scheduler observability upstream:
  [KAI #2352](https://github.com/kai-scheduler/KAI-Scheduler/issues/2352) "add aggregate
  evicted-pod counters by scheduler action".
- **Ticket (page):** "Since Tuesday's cpl-sched 0.9 rollout, 8-GPU jobs wait 6 h (was 20 min)
  and allocation dropped from 92% to 63%. Nothing is 'down'."
- **Stack:** Go, Prometheus, cpl-sim.
- **Skills:** DEBUG, OBS, SD, COMM
- **Size:** 8 h:
  1. triage on metrics (2 h)
  2. find both causes in the diff and logs (2 h)
  3. fix + fragmentation alert (2 h)
  4. postmortem (2 h)
- **Built by AI vs. by him:**
  - AI builds a simulator replay of 0.9 with two causes:
    - a config refactor flipped scoring from pack to spread
    - a new notebook anti-affinity rule scatters 1-GPU notebooks across nodes
  - He writes the diagnosis, fix, alert and postmortem.
- **Done-condition:**
  - Replay with his fix: 8-GPU p95 wait ≤ 30 min and allocation ≥ 88%.
  - The alert fires within 15 simulated minutes on the bad config and never across 7 clean
    days.
  - He names both causes.
  - The postmortem passes the checker.
- **Pushback hooks:** the manager wants to roll back 0.9 entirely, but it also contains a
  security fix.
- **Ownership change request:** any scoring-config change runs a 24 h simulator replay in CI
  and posts the delta.

### CPL-04 GPU memory caps for shared notebooks (CUDA interception shim)
- Company: Coldplate   Type: build   Level: L4
- **Real-world grounding:** KAI's GPU sharing gives no memory isolation
  ([New Stack](https://thenewstack.io/nvidia-open-sources-kai-scheduler-to-help-ai-teams-optimize-gpu-utilization/)).
  HAMi-core (CNCF Sandbox HAMi) enforces `CUDA_DEVICE_MEMORY_LIMIT` by preloading a library
  that hooks the CUDA driver and NVML ([repo](https://github.com/Project-HAMi/HAMi-core),
  [Kubex](https://kubex.ai/blog/making-shared-gpus-even-safer-with-kubex-and-hami-core)).
- **Ticket:** "Customers want 4 notebooks per GPU. With time-slicing, one notebook OOMs
  everyone. Build `cpl-vgpu`: an `LD_PRELOAD` shim that enforces a per-process GPU memory cap
  and reports usage."
- **Stack:** C. It interposes the CUDA driver API (`cuMemAlloc*`, `cuMemFree*`,
  `cuMemGetInfo`) and NVML, as HAMi-core does. Python/PyTorch test harness.
- **Skills:** OS, MLSYS, DEBUG, TEST, SEC
- **Size:** 30 h:
  1. driver API + `dlsym` interposition study (5 h)
  2. alloc/free accounting (8 h)
  3. a capped `cuMemGetInfo`, so PyTorch's caching allocator sees the cap (5 h)
  4. multi-process shared accounting (6 h)
  5. tests + overhead benchmark (6 h)
- **Built by AI vs. by him:** AI builds the test harness and workloads. He writes the shim.
- **Done-condition** (Linux/WSL2 on the 4070):
  - Two processes are capped at 5 GiB each. The one exceeding its cap gets a clean
    `torch.cuda.OutOfMemoryError` while the other keeps training.
  - `torch.cuda.mem_get_info()` reports the cap.
  - Overhead ≤ 5% on an allocation microbenchmark and ≤ 1% on a training loop.
  - Also works with `PYTORCH_CUDA_ALLOC_CONF=backend:cudaMallocAsync`.
  - WSL2 loads libcuda from `/usr/lib/wsl/lib`; that interposition works there is
    unverified. Fall back to a native Linux boot or Docker if not.
- **Pushback hooks:**
  - A peer says "just set `per_process_memory_fraction`", which doesn't cover non-PyTorch or
    adversarial code.
  - The lead wants to do it in the driver, which is closed source and out of scope.
- **Ownership change request:** a `soft` mode that logs over-cap allocations instead of
  failing them.

### CPL-05 Who's burning GPUs doing nothing? Chargeback + idle reaper
- Company: Coldplate   Type: build   Level: L3
- **Real-world grounding:** "GPU util" measures whether any kernel ran; memory traffic alone
  can read 100% ([Trainy](https://trainy.ai/blog/gpu-utilization-misleading)). CoreWeave's
  Fleet Monitoring & Analysis team builds this kind of tooling
  ([posting](https://www.efinancialcareers.com/jobs-Poland-Warsaw-Senior_Software_Engineer_Fleet_Monitoring_Analysis.id24513471)).
- **Ticket:** "Finance wants per-team GPU-hour cost. Customers want forgotten notebooks
  reaped. From DCGM metrics + scheduler allocation events:
  - produce a daily chargeback table
  - flag reservations idle > 30 min, using SM activity, not 'util'."
- **Stack:** Python + SQL (DuckDB over Parquet) + a small Grafana board. It's analytics, so
  SQL is the right tool.
- **Skills:** DATA, OBS, DB
- **Size:** 14 h in 6 blocks:
  1. data model
  2. chargeback SQL
  3. idle detection
  4. "busy-but-idle" heuristics
  5. dashboard
  6. tests
- **Built by AI vs. by him:** AI provides a synthetic week of DCGM metrics for 512 GPUs with
  planted idle and memcpy-only "100% util" reservations, plus allocation events. He writes
  the pipeline and detection logic.
- **Done-condition:**
  - chargeback within 0.5% of ground truth per team
  - all 15 planted idle reservations found (including the 3 "100% util, idle SMs"), ≤ 1 false
    positive
  - the week processes in ≤ 2 min
- **Pushback hooks:** the PM wants "util < 5%" as the idle definition.
- **Ownership change request:** a partial-idle report (< 25% SM activity for 6 h).

### CPL-06 Design review: quotas and borrowing for 6 customer teams
- Company: Coldplate   Type: design-review   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P43 DRF, P42 Themis
- **Real-world grounding:** Kueue cohorts, borrowing, weighted fair sharing and preemption
  ([preemption](https://kueue.sigs.k8s.io/docs/concepts/preemption/)); KAI hierarchical
  queues; [Kueue #9402](https://github.com/kubernetes-sigs/kueue/issues/9402) (configuring
  priority sorting within a cohort).
- **Ticket:** "An enterprise has 6 teams on a 512-GPU reservation.
  - Research gets 40% guaranteed under contention.
  - Prod inference can preempt anything.
  - Idle quota must be borrowable within 2 min.
  - No 3-day run is preempted without a checkpoint warning.
  Bring a design and a policy file the simulator can execute."
- **Stack:** Kueue-like YAML policy + Python simulator (provided) + whiteboard.
- **Skills:** SD, DIST, COMM
- **Size:** 10 h:
  1. reading (2 h)
  2. policy draft (3 h)
  3. simulator iterations (3 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the simulator and contention scenarios. He writes
  the policy and the defense.
- **Done-condition** (3 scenarios):
  - research ≥ 40% within 10 min of contention
  - borrow latency ≤ 2 min
  - jobs > 24 h old are preempted only after a 15-min notice
  - utilization ≥ 85%
  - rubric: starvation, priority inversion, cascading preemption
- **Pushback hooks:** a senior engineer wants static partitions ("simpler").
- **Ownership change request:** a lending limit so prod can't lend more than 50%.

### CPL-07 Experiment: predict job runtimes to make backfill bolder
- Company: Coldplate   Type: experiment   Level: L3
- **Real-world grounding:**
  - Tsafrir, Etsion & Feitelson, "Backfilling using system-generated predictions rather than
    user runtime estimates" (IEEE TPDS 2007, memory).
  - Public traces with user/queue/GPU-count features (Philly; Alibaba PAI,
    [NSDI'22](https://www.usenix.org/conference/nsdi22/presentation/weng)).
- **Ticket:** "Requested walltimes are ~5× too long, so backfill is timid. Train a runtime
  predictor and plug it into the simulator's backfill."
- **Stack:** Python (pandas, LightGBM/sklearn) + a Go simulator hook.
- **Skills:** ML, DATA, SD
- **Size:** 12 h:
  1. features + time split (3 h)
  2. model (3 h)
  3. simulator integration with an under-prediction policy (4 h)
  4. write-up (2 h)
- **Built by AI vs. by him:** AI provides trace prep and the simulator hook interface. He
  writes features, model, policy and evaluation.
- **Done-condition:**
  - On time-split held-out jobs (last 2 weeks), MAE on log-runtime ≥ 30% lower than user
    estimates.
  - In the simulator, mean wait ≥ 10% lower than backfill with user estimates, with zero
    head-of-queue reservation violations. He must handle under-prediction, e.g. with an
    extend-or-requeue rule.
- **Pushback hooks:**
  - A teammate's feature `job_end_status` is known only after the job ends (leakage).
  - A random split leaks per-user patterns across time.
- **Ownership change request:** per-user calibration (users with history vs. cold start).

### CPL-08 The block-time GPU market's matching engine
- Company: Coldplate   Type: build   Level: L5
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P42 Themis GPU auctions
- **Real-world grounding:** SF Compute trades blocks of GPUs × time:
  - orders are not reservations
  - a buy fills only against a sell at ≤ its price
  - immediate-or-cancel by default, standing orders optional
  - unused capacity can be resold
  ([market](https://sfcompute.com/docs/market), [orders](https://docs.sfcompute.com/current/orders)).
- **Ticket:** "We're launching a block market:
  - buy orders: N GPUs, start window, duration, max $/GPU-h, contiguous nodes in one
    cluster
  - sell orders: us, and customers reselling
  Build the matching engine: price-time priority, no partial fills for gang orders, no
  double allocation, auditable." It starts with a design doc and review.
- **Stack:** Rust. A deterministic single-threaded core with an event log: no GC pauses,
  invariants in types, `proptest` for properties. Matching engines are typically
  C++/Rust/Java.
- **Skills:** SD, DIST, TEST, DB, PERF
- **Size:** 40 h. Design doc (5 h) → review, then:
  1. single-cluster book (10 h)
  2. interval allocation with contiguity (8 h)
  3. event log, deterministic replay, recovery (8 h)
  4. property tests + fuzzing (5 h)
  5. perf + demo (4 h)
- **Built by AI vs. by him:** AI provides the API shell, order generator and audit checker. He
  writes the engine.
- **Done-condition:**
  - Properties hold over 1M random ops: no GPU-hour sold twice, never above the buyer's
    limit, price-time priority respected.
  - Replaying the event log reproduces the book-state hash.
  - 100 random crashes plus recovery lose no acknowledged order.
  - ≥ 50k orders/s on one core with p99 match ≤ 1 ms (5900X).
- **Pushback hooks:**
  - The PM wants partial fills for gang orders "to fill more".
  - The lead wants every order written to Postgres in the hot path.
- **Ownership change request:** an atomic cancel-replace.


### CPL-09 Paper → prod: heterogeneity-aware scheduling (Gavel)
- Company: Coldplate   Type: experiment (paper-inspired)   Level: L4
- **Paper:** Narayanan et al., "Heterogeneity-Aware Cluster Scheduling Policies for Deep
  Learning Workloads" (Gavel), OSDI 2020
  ([arXiv 2008.09213](https://arxiv.org/abs/2008.09213),
  [USENIX](https://www.usenix.org/conference/osdi20/presentation/narayanan-deepak)).
- **What it claims:** express each policy as an optimization over *effective throughput*:
  each job's throughput on each GPU type, times the fraction of time it holds that type.
  Heterogeneity-aware versions improve average JCT and makespan "by up to 3.5×" vs.
  heterogeneity-agnostic ones. The physical-cluster gains are smaller (~1.4×), and the
  simulator agrees with the physical cluster within 5%.
- **Real-world grounding:** Coldplate's fleet mixes H100, H200 and older A100 nodes. Some
  jobs speed up 3× on H100 and others barely notice, yet cpl-sched treats a GPU as a GPU.
  Alibaba's PAI trace comes from a heterogeneous cluster
  ([NSDI'22](https://www.usenix.org/conference/nsdi22/presentation/weng)).
- **Ticket:** "Our team wants to try Gavel's effective-throughput formulation in cpl-sim
  before touching prod. Implement heterogeneity-aware max-min fairness and min-avg-JCT
  policies as LPs over a job×GPU-type throughput matrix, plus Gavel's round-based allocation
  mechanism. Reproduce the paper's direction of improvement on our trace."
- **Stack:** Python (cvxpy/scipy LP, like Gavel's own implementation) for the policy, called
  from the Go simulator over a small gRPC/JSON boundary. LPs belong in Python.
- **Skills:** SD, ML (optimization), DIST, PERF
- **Size:** 22 h:
  1. read the paper + Gavel's repo (4 h)
  2. throughput-matrix estimation from the trace (3 h)
  3. two LP policies (6 h)
  4. round-based mechanism in the simulator (5 h)
  5. evaluation + write-up (4 h)
- **Built by AI vs. by him:** AI provides the simulator with 3 GPU types, a job-type
  throughput table and a heterogeneity-agnostic LAS baseline. He writes the LPs, the
  mechanism and the evaluation.
- **Done-condition:**
  - **Reproduce:** at the paper's load range, heterogeneity-aware max-min fairness cuts
    average JCT ≥ 1.3× vs. the agnostic baseline (paper: 1.4× physical, up to 3.5×
    simulated).
  - His policy LP solves for 2,048 GPUs × 500 jobs in ≤ 2 s.
  - No job gets less than its fair share under the max-min policy (property check).
- **Pushback hooks:**
  - The tech lead says "just route big jobs to H100s". He must show the cases where that
    loses.
  - Ops asks how throughput estimates are obtained for new jobs; it needs a profiling
    fallback.
- **Ownership change request:** add a cost-aware objective ($ per job completed at
  per-GPU-type prices).

### CPL-10 Cross-domain → prod: airline revenue management for GPU blocks (EMSR-b)
- Company: Coldplate   Type: experiment (paper-inspired, cross-domain: airlines/OR)   Level: L3
- **Paper:**
  - Belobaba, "Application of a Probabilistic Decision Model to Airline Seat Inventory
    Control", *Operations Research* 37(2), 1989
    ([IDEAS](https://ideas.repec.org/a/inm/oropre/v37y1989i2p183-197.html)).
  - The EMSR-a/EMSR-b heuristics ([overview](https://en.wikipedia.org/wiki/Expected_marginal_seat_revenue)).
- **What it claims:** with uncertain demand across fare classes that arrive low-fare first,
  set *protection levels*: seats held back for higher fares, using expected marginal seat
  revenue. Western Airlines' 1987 deployment beat judgmental booking limits on a live revenue
  test. EMSR-b aggregates higher-class demand and is the variant used in practice.
- **Real-world grounding:** GPU blocks are perishable inventory like seats: an unsold
  H100-hour is gone. SF Compute's market sells blocks at different prices, with long-term
  contracts vs. short spot-like blocks and resale
  ([market](https://sfcompute.com/docs/market)). Coldplate sells cheap long reservations early
  and gets high-paying urgent requests late.
- **Ticket:** "Finance thinks we sell out too early to cheap 3-month reservations. Our team
  wants to try airline revenue management. Implement EMSR-b protection levels for 4 'fare
  classes' (3-month reserved, 1-month, 1-week, on-demand burst) per cluster per week. Evaluate
  in the market simulator against first-come-first-served and the offline optimum."
- **Stack:** Python (numpy/scipy). The harness simulator is Python.
- **Skills:** ML (stats/forecasting), DATA, SD
- **Size:** 12 h:
  1. read Belobaba + EMSR-b derivation (3 h)
  2. demand-model fit per class from synthetic booking history (3 h)
  3. EMSR-b + nested booking limits (3 h)
  4. evaluation vs. FCFS and the DP optimum (3 h)
- **Built by AI vs. by him:** AI provides a booking simulator with stochastic class demand
  (low-before-high arrivals, plus a variant that violates that assumption) and a dynamic-
  programming oracle. He writes the demand fit, EMSR-b and the evaluation.
- **Done-condition** (held-out simulated weeks):
  - **Reproduce:** EMSR-b revenue is ≥ 8% above FCFS and within 3% of the DP optimum when
    the paper's assumptions hold.
  - **Robustness:** under the assumption-violating variant (interleaved arrivals) he must
    report the gap. A re-solve-daily version must recover ≥ half of it.
  - His protection levels match a reference EMSR-b implementation within 1 block on 10 test
    instances.
- **Pushback hooks:**
  - Sales: "holding back capacity looks like we're sold out to customers".
  - A peer wants a deep-RL pricing agent first.
- **Ownership change request:** add overbooking for the reserved class using the observed
  no-show/early-release rate.

---
## Loopline — Ranking & Training Platform (RTP), a division of a big short-video app

- **Niche / domain:** training infrastructure and distributed training, plus recommendation
  and ranking.
- **Stage:** big-tech division. Loopline is a fictional consumer app with ~600M MAU. RTP has
  ~140 engineers in 9 teams; the learner joins *Training Reliability*.
- **Culture:**
  - Design-doc-first: one-pager → review → launch review. Owning teams are mandatory
    reviewers, and launch checklists apply.
  - OKRs; on-call with SLAs to the model teams; "every GPU-hour is tracked".
  - Slower and more rigorous than a startup, with lots of internal tools.
- **Stack, and why:**
  - Python/PyTorch: FSDP2, DCP, a torchtitan-style trainer, TorchRec for embeddings (the
    Meta-style stack).
  - C++ for data decoders and serving.
  - Thrift/gRPC; an S3-compatible blob store; Kubernetes with a gang scheduler.
  - Spark for features, Ray Data for preprocessing (Pinterest-style).
- **Team roster:** EM (Training Reliability), tech lead, staff performance engineer, 2 peers
  (checkpointing; data loading), PM (platform), an embedded ML engineer from Home Feed (the
  customer), a new-grad junior.
- **Main codebase sketch:**
  - `rtp-trainer/`: loop, FSDP wrapper, metrics
  - `rtp-ckpt/`: async checkpointing
  - `rtp-data/`: sharded format + loader
  - `rtp-health/`: hang and straggler tools
  - `rtp-goodput/`
  - `models/`: a DLRM-style ranker, a two-tower retriever, small LMs
  - `traces/`: recorded per-rank timings and failure logs
- **In-house tools this company would build:** async checkpointer, resumable loader,
  Flight-Recorder hang analyzer, straggler detector, goodput/MFU service, OOM triage bot,
  sharding-plan memory estimator, checkpoint-cadence failure simulator, input-pipeline
  profiler.
- **Inspired by:**
  - Meta: [Llama 3](https://arxiv.org/abs/2407.21783), DCP,
    [Flight Recorder](https://pytorch.org/blog/flight-recorder-a-new-lens-for-understanding-nccl-watchdog-timeouts/),
    [TorchRec](https://pytorch.org/torchrec/concepts.html), [torchft](https://github.com/meta-pytorch/torchft)
  - Pinterest ([data loading](https://www.zenml.io/mlops-database/pinterest-ml-platform-evolution-with-ray-talks-deep-dives-ray-based-distributed-data-loading-for-recommender-model-train))
  - Netflix (foundation model)
  - ByteDance ([MegaScale](https://arxiv.org/abs/2402.15627))
  - Google ([goodput](https://docs.cloud.google.com/tpu/docs/goodput))
  - IBM ([async checkpointing](https://pytorch.org/blog/reducing-checkpointing-times/))
- **Projects:** LPL-01 … LPL-12. Paper-inspired: ★LPL-11 (PowerSGD) and ★LPL-12 (HSTU). Also paper-grounded: LPL-06 (GUARD), LPL-09 (Yi et al.), LPL-10 (Daly).

### LPL-01 Review: async checkpointing that sometimes saves garbage
- Company: Loopline RTP   Type: review-to-own   Level: L2
- **Idea-bank seed** (`06-paper-idea-bank.md`): P30
- **Real-world grounding:**
  - Async checkpointing (IBM 7B: 148.8 s → 6.3 s of downtime;
    [PyTorch blog](https://pytorch.org/blog/reducing-checkpointing-times/)).
  - TorchTitan: 5–15× lower overhead ([arXiv](https://arxiv.org/abs/2410.06511)).
  - torchft starter issue [#36](https://github.com/meta-pytorch/torchft/issues/36)
    "[CheckpointServer] use streaming transfers".
- **Ticket:** "Ken's PR makes rtp-ckpt async. It snapshots model, optimizer and dataloader
  state into pinned CPU memory, writes in a background thread, and publishes atomically.
  Three model teams are waiting for it. Review and own."
- **Stack:** Python/PyTorch.
- **Skills:** OS, MLSYS, TEST, READ
- **Size:** 6 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR, a small GPT training job that fits the 4070,
  and a chaos runner. He writes the review, fixes and tests.
- **Done-condition:**
  - ≥ 4 of 5 bugs found.
  - After fixes, SIGKILL at 50 random points (some mid-write): every resume loads the newest
    *complete* checkpoint and continues bitwise-identically (params + loss hash) to an
    uninterrupted reference.
  - Checkpoint stall ≤ 10% of the synchronous baseline.
- **Planted bugs:**
  1. The device-to-host copy runs on a side stream with no sync before the writer thread
     reads (torn tensors).
  2. A second save starts before the first finishes, into the same temp dir.
  3. The metadata file is published before the data files are fsync'd.
  4. Dataloader state is captured after the next batch was prefetched, so resume skips a
     batch.
  5. The CUDA RNG state isn't saved, so dropout diverges after resume.
- **Ownership change request:** `keep_last_n` retention that never deletes the only valid
  checkpoint.

### LPL-02 Exact mid-epoch resume for the sharded loader
- Company: Loopline RTP   Type: add-your-part   Level: L2
- **Real-world grounding:** torchdata's StatefulDataLoader saves and restores loader state
  but "does not handle state across distributed ranks"
  ([docs](https://pytorch.org/data/beta/torchdata.stateful_dataloader.html)). See also Mosaic
  Streaming's fast resumption
  ([docs](https://streaming.docs.mosaicml.com/en/latest/distributed_training/fast_resumption.html)).
  With 466 interruptions in 54 days (Llama 3), resumes are routine.
- **Ticket:** "rtp-data has the shard writer and a loader with deterministic per-epoch
  shuffling. A restart today replays the epoch from the start: hours wasted, samples counted
  twice. Implement exact resume across N ranks × M workers. Stretch: resume with a different
  N."
- **Stack:** Python.
- **Skills:** DIST, TEST, OS, DATA
- **Size:** 10 h:
  1. per-rank/per-worker state design (2 h)
  2. implementation (4 h)
  3. kill tests (2 h)
  4. elastic stretch (2 h)
- **Built by AI vs. by him:** AI provides the writer, loader, shuffling and test runner. He
  writes the resume state and logic.
- **Done-condition:**
  - 4 CPU ranks (gloo) × 3 workers, killed at 20 random steps.
  - Every sample index is seen exactly once per epoch globally, in the same order as an
    uninterrupted run.
  - Stretch: resuming 4 → 2 ranks still yields exactly-once.
  - Throughput regression ≤ 5%.
- **Pushback hooks:**
  - A teammate stores one global "samples consumed" int, which breaks with per-worker
    prefetch.
  - The lead says "just checkpoint the RNG".
- **Ownership change request:** a `--verify-epoch` mode that logs a Bloom filter of seen IDs
  and reports duplicates.

### LPL-03 Incident: the 3 a.m. NCCL watchdog timeout
- Company: Loopline RTP   Type: incident   Level: L3
- **Real-world grounding:**
  - Flight Recorder exists because watchdog errors are generic and causes include CPU-side
    divergence ([blog](https://pytorch.org/blog/flight-recorder-a-new-lens-for-understanding-nccl-watchdog-timeouts/),
    [tutorial](https://docs.pytorch.org/tutorials/intermediate/debug_hangs_with_flight_recorder.html)).
  - Imbue saw NCCL timeouts with no stack traces.
  - NVIDIA's resiliency-ext has an FR analysis skill that finds the divergent process group
    ([nvidia-resiliency-ext](https://github.com/NVIDIA/nvidia-resiliency-ext)).
- **Ticket (page):** "Home Feed's nightly retrain (64 ranks) died after 5 h with `Watchdog
  caught collective operation timeout`, for the second time this week. Flight Recorder dumps
  and logs are attached. Find the cause, fix it, and make the next one self-diagnosing."
- **Stack:** Python/PyTorch distributed.
- **Skills:** DEBUG, DIST, OBS, READ
- **Size:** 9 h:
  1. read the dumps (2 h)
  2. live repro (2 h)
  3. fix (1 h)
  4. `rtp-health hangcheck` tool (3 h)
  5. postmortem (1 h)
- **Built by AI vs. by him:**
  - AI provides pre-recorded FR-style dumps for 64 ranks.
  - The live repro runs on 4 CPU ranks over gloo, because NCCL can't run several ranks on one
    GPU. Whether Flight Recorder supports gloo is unverified, so the repro also carries
    harness-side collective tracing.
  - The cause: ranks whose batch has zero positive labels skip the auxiliary loss's
    `all_reduce`, so collective sequences diverge.
  - Red herring: an XID 13 on one node that morning.
  - He writes the analysis, the fix, and the `hangcheck` tool, which ingests dumps and
    reports the first divergent collective plus the missing ranks.
- **Done-condition:**
  - The repro runs 1,000 steps without hanging.
  - On 5 hidden dump sets, `hangcheck` names the right cause class and ranks 5/5: divergence,
    a rank stuck in data loading, mismatched collective sizes, a hung-GPU-like rank, no fault.
  - The postmortem passes the checker.
- **Pushback hooks:** the on-call peer wants to raise the NCCL timeout to 2 h.
- **Ownership change request:** a cheap assertion mode that all-gathers a per-step collective
  counter every 100 steps.

### LPL-04 Perf-hunt: the ranker trains at 15% of compute-bound speed
- Company: Loopline RTP   Type: perf-hunt   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P31
- **Real-world grounding:** Pinterest's Home Feed ranker was data-loading-bound (880k vs. 5M
  examples/s). Fixes included sparse tensor formats, compression, custom serialization, and
  moving expensive ops off GPU nodes
  ([summary](https://www.zenml.io/mlops-database/pinterest-ml-platform-evolution-with-ray-talks-deep-dives-ray-based-distributed-data-loading-for-recommender-model-train), secondary).
  MFU is the yardstick ([MegaScale](https://arxiv.org/abs/2402.15627)).
- **Ticket:** "The DLRM-style ranker (Criteo-like data, ~26 sparse + 13 dense features) trains
  at 60k ex/s on one GPU. With synthetic in-GPU data it does 400k. Find where the time goes
  and fix it without changing model quality."
- **Stack:** Python/PyTorch, `torch.profiler`. Optional C++/numba parsing.
- **Skills:** PERF, MLSYS, OS, DATA
- **Size:** 16 h:
  1. profile + hypothesis list (3 h)
  2. loader fixes (5 h)
  3. H2D and sync fixes (4 h)
  4. AUC check + write-up (4 h)
- **Built by AI vs. by him:**
  - AI writes a training script with realistic sins:
    - per-row Python TSV parsing and hashing in `__getitem__`
    - `num_workers=0`, no `pin_memory`
    - 40 tiny per-feature `.to(device)` copies
    - a `.item()` sync every step
  - Data: a subset of the Criteo display-ads dataset (check its license terms).
  - He writes the profiling evidence and the fixes.
- **Done-condition:**
  - ≥ 4× ex/s vs baseline (calibrated: ≥ 70% of the synthetic upper bound).
  - Profiler shows GPU active ≥ 70%.
  - Held-out AUC within ±0.001 of baseline after 1 epoch on the fixed subset.
  - The write-up includes before/after traces.
- **Pushback hooks:**
  - The staff engineer says "just add CPU nodes".
  - A peer pushes fp16 embeddings, which changes quality and must be proven.
- **Ownership change request:** a loader-only CI benchmark that fails if the input pipeline
  is < 1.5× model throughput.

### LPL-05 Goodput and MFU, measured honestly
- Company: Loopline RTP   Type: build   Level: L3
- **Real-world grounding:**
  - Google's ML Goodput library splits time into goodput and badput (startup, I/O stalls,
    disruption recovery) ([docs](https://docs.cloud.google.com/tpu/docs/goodput),
    [repo](https://github.com/google/cloud_tpu_goodput)).
  - Llama 3 reports > 90% effective training time; MegaScale 55.2% MFU.
  - "Util" is the wrong metric ([Trainy](https://trainy.ai/blog/gpu-utilization-misleading)).
- **Ticket:** "Leadership asks 'what fraction of our GPU-hours trained models?' Build
  `rtp-goodput`. It ingests trainer events (start, step begin/end, checkpoint save/load,
  restart, eval, stall) and reports per-job goodput, a badput breakdown, and MFU from model
  FLOPs."
- **Stack:** Python event schema + calculator, DuckDB, small dashboard.
- **Skills:** OBS, DATA, MLSYS, API
- **Size:** 14 h:
  1. event schema + SDK (3 h)
  2. calculator (5 h)
  3. MFU (2 h)
  4. property tests + dashboard (4 h)
- **Built by AI vs. by him:** AI provides 6 recorded runs with known ground truth. He writes
  the schema, calculator and MFU math.
- **Done-condition:**
  - Goodput within 0.5 pp of truth; each badput category within 1 pp.
  - MFU within 2% of the harness formula for the reference transformer.
  - Out-of-order and duplicated events handled (property tests).
- **Pushback hooks:**
  - A teammate counts steps re-done after a restart as goodput.
  - The PM wants one number per org.
- **Ownership change request:** alert on goodput < 85% over a rolling 6 h.

### LPL-06 Experiment: catch the straggler before it costs a day
- Company: Loopline RTP   Type: experiment   Level: L4
- **Real-world grounding:**
  - GUARD (MLSys 2026): online monitoring plus offline node qualification; up to 1.7× mean
    FLOPs utilization; step variance from 20% to 1%
    ([poster](https://mlsys.org/virtual/2026/poster/3608)).
  - Google Cloud on fail-slow stragglers
    ([blog](https://cloud.google.com/blog/products/compute/stragglers-in-ai-a-guide-to-automated-straggler-detection)).
  - ByteDance: stragglers are not always hardware ([arXiv 2505.05713](https://www.emergentmind.com/papers/2505.05713)).
  - Imbue: GC pauses on single workers.
  - NVIDIA NVRx straggler detection
    ([NeMo docs](https://docs.nvidia.com/nemo-framework/user-guide/latest/resiliency.html)).
- **Ticket:** "Build a detector over per-rank step, compute and communication timings. It
  should flag fail-slow ranks fast without paging us for noise. Labeled history from 300 past
  runs is in `traces/`."
- **Stack:** Python (pandas/numpy, optional sklearn), plus optional live hooks in the
  trainer.
- **Skills:** ML, OBS, DATA, DIST
- **Size:** 18 h:
  1. EDA + features (5 h)
  2. detector (6 h)
  3. attribution logic (4 h)
  4. evaluation + write-up (3 h)
- **Built by AI vs. by him:**
  - AI provides a trace generator from real-world patterns: thermal throttle ramps, a
    flapping NIC, periodic GC pauses, a data-starved rank, healthy jitter. Labels come with
    it; the held-out set stays hidden.
  - He writes the features, detector and evaluation.
- **Done-condition** (hidden set):
  - rank-level precision ≥ 0.9, recall ≥ 0.85
  - median detection delay ≤ 50 steps
  - ≤ 1 false alert per 10k healthy rank-hours
  - correctly separates the slow rank from "victim" ranks waiting in all-reduce
    (attribution check)
- **Pushback hooks:** the lead's baseline flags step time > mean + 3σ. In synchronous
  training every rank's step time is the same (they all wait), so it can never fire. He has
  to split compute from communication.
- **Ownership change request:** a node-qualification mode: fixed microbenchmark vs. fleet
  percentile.

### LPL-07 Incident: OOM after bumping context to 8k
- Company: Loopline RTP   Type: incident   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P28 (related: P29 selective recompute)
- **Real-world grounding:**
  - Memory snapshots (`_record_memory_history`, `_dump_snapshot`, pytorch.org/memory_viz) for
    OOM triage ([PyTorch](https://pytorch.org/blog/understanding-gpu-memory-1/)).
  - The cross-entropy logit matrix dominates memory for large vocabularies (Cut Cross-Entropy:
    24 GB → 1 MB for the loss on Gemma 2 2B; [arXiv](https://arxiv.org/abs/2411.09009)).
- **Ticket:** "Search Relevance's full fine-tune of a 0.5B LM was fine at 2k context and OOMs
  at 8k on the team's 12 GB dev GPUs. They need it today. Find what's using memory, fix it,
  and keep the loss curve."
- **Stack:** Python/PyTorch (Qwen2.5-0.5B on the 4070).
- **Skills:** DEBUG, MLSYS, PERF
- **Size:** 7 h:
  1. snapshot + attribution (3 h)
  2. fixes (2 h)
  3. verification + write-up (2 h)
- **Built by AI vs. by him:**
  - AI writes the script with three consumers:
    1. fp32-upcast logits over a ~152k vocabulary: 8,192 × 151,936 × 4 B ≈ 5 GB per copy,
       before gradients
    2. no activation checkpointing
    3. a `self.last_logits = outputs.logits` debug reference that keeps the previous step's
       logits alive
  - He writes the analysis and the fixes: chunked or fused CE, checkpointing, dropping the
    reference.
- **Done-condition:**
  - `max_memory_allocated` ≤ 10.5 GB at 8k, batch 1.
  - 200-step loss within 1% of a reference recorded on a larger GPU.
  - Step time ≤ 1.3× that reference.
  - The write-up names all three consumers with sizes.
- **Pushback hooks:**
  - "Just use LoRA" changes the experiment.
  - "Lower the batch": it's already 1.
- **Ownership change request:** `estimate_memory()` that predicts peak within 15% for 3
  context lengths.

### LPL-08 Review: the embedding sharding memory estimator
- Company: Loopline RTP   Type: review-to-own   Level: L1
- **Real-world grounding:** TorchRec's planner weighs memory, compute and bandwidth across
  table-wise, row-wise, column-wise and data-parallel sharding. Topology carries HBM and DDR
  sizes, and UVM caching handles tables larger than HBM
  ([concepts](https://pytorch.org/torchrec/concepts.html),
  [tutorial](https://pytorch.org/tutorials/advanced/sharding.html)).
- **Ticket:** "Ana's PR adds `estimate_plan_memory(plan, topology)` so model teams stop
  finding OOMs on the cluster. Review and own."
- **Stack:** Python.
- **Skills:** MLSYS, READ, TEST
- **Size:** 4 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR and 12 ground-truth configs. He writes the
  review, fixes and tests.
- **Done-condition:** within 5% of ground truth on all 12 configs; ≥ 4 of 5 bugs found.
- **Planted bugs:**
  1. Optimizer state is omitted: row-wise Adagrad keeps 1 float per row, Adam 2× params.
  2. fp16 tables are counted at 4 bytes per value.
  3. The row-wise remainder rows on the last rank are dropped.
  4. UVM-cached tables are counted fully in HBM instead of by `cache_load_factor`.
  5. The column-wise all-to-all output buffer is forgotten.
- **Ownership change request:** a warning when a plan comes within 10% of HBM.

### LPL-09 Experiment: two-tower retrieval with sampling-bias correction
- Company: Loopline RTP   Type: experiment   Level: L3
- **Real-world grounding:**
  - YouTube's logQ correction for in-batch negatives, with streaming frequency estimation
    (Yi et al., RecSys 2019:
    [Google Research](https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/), memory).
  - Netflix serves foundation-model embeddings through an Embedding Store (secondary summary
    above).
- **Ticket:** "Discover's candidate generator uses in-batch negatives and over-recommends
  popular items. Add logQ correction with a streaming item-frequency estimator and show the
  gain on held-out users."
- **Stack:** Python/PyTorch on MovieLens-25M
  ([GroupLens](https://grouplens.org/datasets/movielens/25m/), memory) or an Amazon
  Reviews'23 subset.
- **Skills:** ML, DATA, MLSYS
- **Size:** 12 h:
  1. time split + baseline (3 h)
  2. frequency estimator + correction (4 h)
  3. eval + ablations (3 h)
  4. write-up (2 h)
- **Built by AI vs. by him:** AI provides the data prep and baseline two-tower model. He
  writes the estimator, the corrected loss and the evaluation.
- **Done-condition:**
  - time-based held-out split
  - Recall@100 ≥ +8% relative over baseline, and catalog coverage@100 ≥ +15%
  - fits in 12 GB, ≤ 30 min/epoch
  - ablation table
- **Pushback hooks:**
  - The teammate's split is random by interaction, so the future leaks into training.
  - There's no popularity baseline.
- **Ownership change request:** mixed negative sampling behind a flag.

### LPL-10 Design review: checkpoint cadence, hot spares, per-step FT for a 4,096-GPU run
- Company: Loopline RTP   Type: design-review   Level: L5
- **Real-world grounding:**
  - Llama 3: 419 unexpected interruptions in 54 days on 16k GPUs, ~78% hardware.
  - Imbue: ~3% of machines per week; keep 10–20% spares.
  - Async checkpoint numbers: 70B on 1,856 GPUs, 436 s → 67 s of background time
    ([forum](https://discuss.pytorch.org/t/distributed-w-torchtitan-optimizing-checkpointing-efficiency-with-pytorch-dcp/211250)
    and the PyTorch blog).
  - torchft replica groups and Lighthouse ([repo](https://github.com/meta-pytorch/torchft)).
  - Young/Daly optimal checkpoint interval (Daly 2006, FGCS, memory).
- **Ticket:** "Next quarter's foundation ranker: 4,096 GPUs for 30 days. Propose the checkpoint
  interval, sync vs. async, the spare pool, and whether to adopt torchft-style per-step fault
  tolerance. Defend it with numbers."
- **Stack:** Python failure simulator (provided) + his analytic model + whiteboard.
- **Skills:** SD, DIST, MLSYS, COMM
- **Size:** 10 h:
  1. reading (2 h)
  2. analytic model (3 h)
  3. simulator validation (3 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the simulator (failure rates, correlated failures,
  storage bandwidth). He writes the model and the policy.
- **Done-condition:**
  - His predicted goodput is within 2 pp of the simulator on 3 failure-rate scenarios.
  - His policy reaches ≥ 92% goodput in the simulator at ≤ 8% spare capacity.
  - Rubric: correlated failures (a switch takes out 32 nodes), storage bandwidth, silent data
    corruption.
- **Pushback hooks:**
  - "Checkpoint every 10 minutes": storage bandwidth turns that into a stall.
  - "Per-step FT is free": not with replica-group overheads.
- **Ownership change request:** add a checkpoint-to-peer-memory tier.


### LPL-11 Paper → prod: PowerSGD gradient compression for the cross-datacenter run
- Company: Loopline RTP   Type: experiment (paper-inspired)   Level: L3
- **Paper:** Vogels, Karimireddy & Jaggi, "PowerSGD: Practical Low-Rank Gradient Compression
  for Distributed Optimization", NeurIPS 2019 ([arXiv 1905.13727](https://arxiv.org/abs/1905.13727)).
  PyTorch ships it as a DDP communication hook
  (`torch.distributed.algorithms.ddp_comm_hooks.powerSGD_hook`, memory).
- **What it claims:** a low-rank (power-iteration) compressor with error feedback that is
  all-reduce friendly. It gives "consistent wall-clock speedups over regular SGD" and test
  performance comparable to SGD on convnets and LSTMs.
- **Real-world grounding:** RTP wants to train a ranker across two regions over a thin link.
  Gradient all-reduce dominates when bandwidth is low. MegaScale and Llama 3 both treat
  communication as the scaling bottleneck ([MegaScale](https://arxiv.org/abs/2402.15627)).
- **Ticket:** "Our team wants to try PowerSGD for the cross-region job. Reproduce the paper's
  core claim at small scale: same accuracy, far fewer bytes, a real speedup when the link is
  slow. Then tell us which rank and warm-start settings to use, and where it breaks."
- **Stack:** Python/PyTorch DDP with 4 CPU ranks over gloo. NCCL can't run multiple ranks on
  one GPU, so a single-GPU variant measures compute overhead. Linux `tc netem` caps bandwidth
  on the loopback/veth.
- **Skills:** DIST, MLSYS, PERF, ML
- **Size:** 14 h:
  1. baseline DDP ResNet-18/CIFAR-10 on 4 gloo ranks with a 1 Gbit cap (4 h)
  2. PowerSGD hook: ranks 1/2/4, warm start on/off, error feedback on/off (4 h)
  3. bytes-on-wire + wall-clock measurements (3 h)
  4. write-up (3 h)
- **Built by AI vs. by him:** AI provides the training script, the `tc` bandwidth shaper and
  a byte counter on the process group. He writes the experiment matrix, the analysis and the
  recommendation. Stretch: implement the compressor himself instead of using the built-in
  hook.
- **Done-condition:**
  - **Reproduce:** at rank 2, test accuracy within 0.5 pt of uncompressed DDP after the same
    epochs.
  - Bytes all-reduced per step ≤ 1/50 of baseline.
  - Wall-clock to target accuracy ≤ 0.7× baseline at the 1 Gbit cap.
  - **Ablation:** turning error feedback off loses ≥ 1 pt or fails to converge. If not, he
    explains why.
- **Pushback hooks:**
  - The staff engineer: "compression always hurts accuracy, just buy bandwidth".
  - A peer applies it to embedding tables too. Sparse/embedding gradients need different
    handling, and he must explain why.
- **Ownership change request:** auto-select the rank from a measured bandwidth probe at job
  start.

### LPL-12 Paper → prod: reproduce HSTU (generative recommenders) before we bet the roadmap on it
- Company: Loopline RTP   Type: experiment (paper-inspired)   Level: L4
- **Paper:** Zhai et al. (Meta), "Actions Speak Louder than Words: Trillion-Parameter
  Sequential Transducers for Generative Recommendations", ICML 2024
  ([arXiv 2402.17152](https://arxiv.org/abs/2402.17152); open-source
  `generative-recommenders`, memory).
- **What it claims:**
  - recommendation reframed as sequential transduction
  - HSTU beats baselines "by up to 65.8% in NDCG"
  - its attention kernel is 5.3–15.2× faster than FlashAttention2-based Transformers at
    8192-length sequences
  - On MovieLens-1M (Table 4): SASRec HR@10 .2828 / NDCG@10 .1545 vs. HSTU .3043 / .1700
    and HSTU-large .3306 / .1858.
- **Real-world grounding:** Netflix moved many recommenders onto one foundation model
  ([summary](https://www.zenml.io/llmops-database/foundation-model-for-personalized-recommendation-at-scale),
  secondary). Leadership wants a generative-recommender roadmap. RecTools warns that the
  paper's public-dataset metrics depend on the evaluation setup
  ([RecTools tutorial](https://rectools.readthedocs.io/en/stable/examples/tutorials/transformers_HSTU_tutorial.html)).
- **Ticket:** "Before we fund a generative-recommender team, reproduce HSTU on ML-1M with your
  own implementation of the HSTU block: pointwise aggregated attention, relative
  attention bias, gating. Match the paper's evaluation protocol exactly, compare against
  SASRec, and tell us what the gain depends on."
- **Stack:** Python/PyTorch on the 4070. ML-1M is small; a run takes minutes to an hour.
- **Skills:** ML, READ, MLSYS, TEST
- **Size:** 20 h:
  1. read the paper + its eval protocol (4 h)
  2. SASRec baseline that reproduces the paper's SASRec number (4 h)
  3. HSTU block (6 h)
  4. training + eval sweeps (4 h)
  5. write-up (2 h)
- **Built by AI vs. by him:** AI provides the data download and a leave-one-out evaluation
  harness, validated against the paper's SASRec number. He writes SASRec, HSTU and the
  experiments.
- **Done-condition** (ML-1M, paper protocol, 3 seeds):
  - **Reproduce:** his SASRec HR@10 within ±5% relative of .2828
  - his HSTU HR@10 within ±5% relative of .3043, beating his SASRec in all 3 seeds
  - an ablation table: remove the gating, swap pointwise attention for softmax, remove the
    relative bias
  - **Apply:** unit tests that his attention output matches a naive reference
    implementation to 1e-5
- **Pushback hooks:**
  - The PM quotes "65.8%" for the business case. He must show which dataset and setup that
    comes from.
  - A peer evaluates with sampled negatives instead of full ranking, which inflates metrics.
- **Ownership change request:** add ML-20M (if it fits the time budget) and report whether
  the gap grows with data.

---

## Plumbline — open-source, object-storage-native vector + full-text search engine (Plumbline Foundation)

- **Niche / domain:** vector search and retrieval infrastructure.
- **Stage:** OSS foundation. A foundation-funded core team of 9 maintainers plus ~80 regular
  contributors. Member companies run it in production; one sells a managed cloud.
- **Culture:**
  - RFCs in `rfcs/`; two maintainer approvals per PR.
  - On-disk format compatibility is sacred.
  - Benchmarks run in CI ("no perf claim without the bench job").
  - Async across time zones; newcomer-friendly but pedantic about tests.
- **Stack, and why:**
  - Rust core: SIMD, memory control, no GC, the language of Qdrant, Lance/LanceDB and TEI.
  - Arrow-style columnar segments; S3-compatible object storage (MinIO locally).
  - Python client and bench tools; Go for the member company's cloud control plane.
- **Team roster (the learner's working group):** storage maintainer (lead), query
  maintainer, community manager/PM, two contributor peers from member companies, a junior
  contributor, the bench-bot owner.
- **Main codebase sketch:**
  - `plumbline-core/` (Rust): segments, WAL, an SPFresh-style centroid/IVF index (already
    built by teammates; Luigi never builds a graph index here)
  - `plumbline-query/`: planner, filters, hybrid fusion
  - `plumbline-store/`: object-store tier, caches
  - `plumbline-py/`
  - `bench/`: recall/latency harness, dataset loaders
  - `rfcs/`
- **In-house tools this project would build:** recall-regression CI, filter-selectivity
  bench, churn/compaction test, quantization tuner, cold-start bench with toxiproxy,
  namespace cost model, embedding-version guard, hybrid-fusion eval kit.
- **Inspired by:**
  - turbopuffer ([architecture](https://turbopuffer.com/docs/architecture))
  - LanceDB/Lance, Qdrant
  - Weaviate ([ACORN](https://weaviate.io/blog/speed-up-filtered-vector-search),
    [tenant offloading](https://docs.weaviate.io/deploy/configuration/tenant-offloading))
  - pgvector ([0.8.0](https://www.postgresql.org/about/news/pgvector-080-released-2952/))
  - Elastic ([BBQ](https://www.elastic.co/search-labs/blog/better-binary-quantization-lucene-elasticsearch))
  - Zilliz ([VDBBench](https://zilliz.com/blog/vdbbench-1-0-benchmarking-with-your-real-world-production-workloads))
- **Projects:** PLB-01 … PLB-10. Paper/blog-inspired: ★PLB-09 (learned index) and ★PLB-10 (Russ Cox trigram regex). Also paper-grounded: PLB-03 (FreshDiskANN), PLB-04 (RaBitQ), PLB-07 (Bruch et al.).

### PLB-01 Review: the recall CI job that lies
- Company: Plumbline   Type: review-to-own   Level: L1
- **Real-world grounding:** turbopuffer continuously measures recall on 1% of live traffic.
  VDBBench standardizes recall and latency. Flaky benches are a known upstream pain
  ([LMCache #5402](https://github.com/LMCache/LMCache/issues/5402)). Noise needs error bars
  ([Anthropic](https://www.anthropic.com/research/statistical-approach-to-model-evals)).
- **Ticket:** "A new contributor's PR adds a CI job that computes recall@10 against
  brute-force ground truth on 3 datasets and fails PRs that regress more than 1 pp. Review it
  before we turn it on for everyone."
- **Stack:** Python bench + the Rust index under test.
- **Skills:** TEST, READ, ML
- **Size:** 4 h in 3 blocks.
- **Built by AI vs. by him:** AI writes the PR and fixtures. He writes the review, fixes and
  noise handling.
- **Done-condition:**
  - ≥ 4 of 5 bugs found.
  - After fixes, CI flags a planted 2 pp regression 10/10 times and flags 0 of 10 noise-only
    reruns.
- **Planted bugs:**
  1. Ground truth uses L2 while the index uses cosine on unnormalized vectors.
  2. The recall denominator is k even when the filter matches fewer than k.
  3. ID mapping is off by one after a delete in the fixture.
  4. Query sampling has no fixed seed.
  5. The gate compares means with no confidence interval.
- **Ownership change request:** report recall per selectivity bucket.

### PLB-02 Filtered search that always returns k
- Company: Plumbline   Type: add-your-part   Level: L2
- **Idea-bank seed** (`06-paper-idea-bank.md`): P32
- **Real-world grounding:**
  - pgvector 0.8.0 added iterative index scans against overfiltering, plus planner costing
    that prefers B-trees for selective filters (100% recall).
  - Weaviate made ACORN its default from v1.34 because of low-correlation filters
    ([docs](https://docs.weaviate.io/weaviate/concepts/filtering)).
  - VDBBench: selectivity from 50% to 99.9% hurts both speed and recall.
- **Ticket:** "Filters are applied after the centroid probe. With selective or
  anti-correlated filters, users get 3 results for k=10. The inverted attribute index exists.
  Implement a selectivity-aware plan:
  - exact scan over the filter bitmap for tiny match sets
  - filtered probing with adaptive `nprobe` expansion in the middle
  - post-filtering for loose filters."
- **Stack:** Rust.
- **Skills:** DB, PERF, SD, TEST
- **Size:** 12 h:
  1. selectivity estimation (3 h)
  2. three plans (5 h)
  3. bench + property tests (2 h)
  4. review round (2 h)
- **Built by AI vs. by him:** AI provides the index, inverted index, bench and datasets
  (1M × 768-d fits in RAM). He writes the planner and plans.
- **Done-condition:**
  - Grid: selectivity {50, 90, 99, 99.9%} × {correlated, anti-correlated}.
  - recall@10 ≥ 0.95 in every cell.
  - Exactly k results whenever ≥ k matches exist (property test).
  - p99 ≤ 2× unfiltered p99 at 99% selectivity (calibrated).
- **Pushback hooks:**
  - A maintainer wants a fixed "oversample 10×", which fails at 99.9%.
  - A peer wants to always exact-scan, which is slow at 50%.
- **Ownership change request:** an `EXPLAIN` output showing the chosen plan and the estimated
  selectivity.

### PLB-03 Deletes, tombstones and compaction without losing recall
- Company: Plumbline   Type: build   Level: L4
- **Real-world grounding:**
  - FreshDiskANN: a DeleteList filtered at query time, plus background StreamingMerge
    ([arXiv](https://arxiv.org/abs/2105.09613)).
  - Tombstones degrade recall over update batches (notes cited in §1.6).
  - pgvector indexes don't shrink after deletes. This is the brief's own example of an
    acceptable adjacent ticket.
- **Ticket:** "Deletes are tombstones forever. Add background compaction:
  - merge segments
  - drop deleted vectors
  - reassign them to centroids and split oversized clusters
  - publish a new manifest atomically, while readers keep their snapshot."
  It starts with an RFC.
- **Stack:** Rust.
- **Skills:** DB, OS, DIST, TEST
- **Size:** 24 h. RFC (3 h) → review, then:
  1. manifest versioning + snapshot reads (6 h)
  2. merge/drop/reassign (8 h)
  3. concurrency + crash safety (4 h)
  4. churn bench (3 h)
- **Built by AI vs. by him:** AI provides the segment format, the centroid index and the churn
  generator. He writes compaction and manifests.
- **Done-condition:**
  - Churn test, 20 cycles of 10% deletes + 10% inserts: recall@10 ≥ 0.93 every cycle. The
    harness first verifies that recall falls ≤ 0.85 without compaction.
  - No deleted ID is ever returned over 1M queries (property test).
  - Space amplification ≤ 1.3×.
  - During compaction: 0 query errors, p99 ≤ 1.5× idle.
  - kill -9 mid-compaction → restart serves the last published manifest, no data loss.
- **Pushback hooks:**
  - An RFC reviewer asks "why not rebuild nightly?" (cost, freshness).
  - A peer wants in-place deletes, which break snapshot readers.
- **Ownership change request:** a `compaction_debt` metric and auto-trigger policy.

### PLB-04 Perf-hunt: 1-bit codes + rescoring, 10× more vectors per node
- Company: Plumbline   Type: perf-hunt   Level: L3
- **Real-world grounding:**
  - RaBitQ: D-bit codes, bitwise distance estimation, error bound
    ([arXiv](https://arxiv.org/abs/2405.12497)).
  - Elastic's BBQ derives from it: a single centroid, no random rotation, rescoring after
    estimation. Naive binary codes need 10–100× oversampling
    ([Elastic](https://www.elastic.co/search-labs/blog/better-binary-quantization-lucene-elasticsearch)).
- **Ticket:** "Memory is our top cost. Add a 1-bit code path for candidate scoring:
  center, optional random rotation, sign bits + correction factors. Then rescore at full
  precision from NVMe."
- **Stack:** Rust, with SIMD popcount via `std::arch` or a portable fallback.
- **Skills:** PERF, DB, ML
- **Size:** 18 h:
  1. encoding (5 h)
  2. SIMD scorer (5 h)
  3. rescoring + tuning curves (5 h)
  4. write-up (3 h)
- **Built by AI vs. by him:**
  - AI provides the datasets: a public 1M OpenAI-embedding DBpedia set on Hugging Face
    (`KShivendu/dbpedia-entities-openai-1M`, memory) or a 768-d wiki-embedding subset; check
    licenses.
  - AI also provides the float baseline and the bench.
  - He writes the codes, scorer and rescoring.
- **Done-condition:**
  - In-memory footprint ≤ 1/12 of float32.
  - recall@10 ≥ 0.95 with rescoring.
  - ≥ 2× float-baseline QPS at equal recall (12 threads, 5900X).
  - A recall-vs-oversample curve is reported.
- **Pushback hooks:** a maintainer says "skip the rotation, BBQ did". He must measure what it
  does on *this* dataset.
- **Ownership change request:** per-namespace auto-tuning of oversampling to a target recall.

### PLB-05 Cold namespaces on object storage
- Company: Plumbline   Type: build   Level: L4
- **Real-world grounding:**
  - turbopuffer: object storage is the source of truth, behind NVMe and memory caches,
    stateless compute and a WAL per namespace. Cold p50 runs ~400–870 ms vs ~15 ms warm (the
    pages disagree; [architecture](https://turbopuffer.com/docs/architecture)).
  - Weaviate offloads tenants to S3.
  - VDBBench 2026 adds cold-start and insert-readiness tests
    ([news](https://zilliz.com/news/vdbbench-cost-aware-vector-database-benchmarking)).
- **Ticket:** "Most namespaces are touched once a week. Build the cold tier:
  - a namespace is a WAL plus immutable segments on S3
  - a cold query fetches the centroid index, then batch-fetches the needed clusters in one
    round trip
  - an NVMe LRU cache
  - writes are acked only after the WAL object PUT succeeds."
- **Stack:** Rust (tokio, `object_store`) + MinIO + toxiproxy in Docker.
- **Skills:** DB, DIST, NET, PERF, SD
- **Size:** 32 h. Design note (3 h), then:
  1. layout + WAL (8 h)
  2. cold read path (8 h)
  3. cache (5 h)
  4. fault injection (5 h)
  5. bench + cost report (3 h)
- **Built by AI vs. by him:** AI provides the docker kit, the fault injector and the
  datasets. He writes the tier.
- **Done-condition:**
  - MinIO behind toxiproxy at +20 ms RTT, 1 Gbit, 1M-vector namespace.
  - cold p50 ≤ 500 ms, p99 ≤ 1.2 s; warm p50 ≤ 20 ms.
  - ≤ 4 GETs per cold query.
  - 200 fault runs (kill between PUT and ack, PUT timeouts, partial reads): 0 lost
    acknowledged writes, 0 corrupt reads.
- **Pushback hooks:**
  - The lead wants one object per cluster, which explodes GET counts.
  - A peer wants local disk as the source of truth (durability).
- **Ownership change request:** prefetch-on-first-write for bursty namespaces.

### PLB-06 Incident: recall cratered after the embedding-model upgrade
- Company: Plumbline   Type: incident   Level: L3
- **Real-world grounding:**
  - Vectors from different model versions live in different spaces, so cosine between them is
    meaningless. The fix is dual-index migration
    ([Zilliz FAQ](https://zilliz.com/ai-faq/change-embedding-model-without-reindexing)).
  - Drift-Adapter maps new queries into the legacy space during a migration
    ([arXiv 2509.23471](https://arxiv.org/abs/2509.23471)).
- **Ticket (user report):** "Since Monday, a big user's semantic search quality has dropped
  hard on new documents. Our recall monitor is green."
- **Stack:** Rust (write-path guard) + Python (analysis).
- **Skills:** DEBUG, DATA, OBS, COMM
- **Size:** 8 h:
  1. diagnosis (2 h)
  2. mitigation (2 h)
  3. guard + canary (2 h)
  4. postmortem (2 h)
- **Built by AI vs. by him:**
  - AI provides the replay. The user's pipeline switched queries and new docs to the new
    model; old docs stayed on the old one.
  - The trap: the recall monitor compares ANN results with brute force over the *same*
    vectors, so it measures index recall, not retrieval quality.
  - He writes the diagnosis, the `embedding_model_id` + dimension + norm-stats guard, a
    golden-query canary and the postmortem.
- **Done-condition:**
  - Writes from a mismatched model are rejected with a clear error.
  - The canary detects the incident within 1 replay-hour and stays quiet over 7 clean days.
  - After mitigation, nDCG@10 on the golden set is within 1 pt of pre-incident.
  - The postmortem names "the monitor measured the wrong thing".
- **Pushback hooks:** a maintainer says "embedding models are the user's problem".
- **Ownership change request:** an optional Procrustes adapter (Drift-Adapter-style) for
  serving during backfill, with measured recall.

### PLB-07 Experiment: hybrid fusion that beats RRF on held-out queries
- Company: Plumbline   Type: experiment   Level: L3
- **Real-world grounding:**
  - Bruch et al. (ACM TOIS): a tuned convex combination beats RRF, RRF is sensitive to its
    parameters, and CC needs few labels ([arXiv 2210.11934](https://arxiv.org/abs/2210.11934)).
  - BEIR ([arXiv 2104.08663](https://arxiv.org/abs/2104.08663), memory).
- **Ticket:** "We ship RRF(k=60) as the hybrid default. On BEIR SciFact, FiQA and NFCorpus,
  using our BM25 and dense paths, compare:
  - RRF
  - a tuned convex combination
  - a tiny learned fusion
  Ship the best default plus a per-namespace tuner that needs ≤ 50 labeled queries."
- **Stack:** Python eval + a Rust fusion operator.
- **Skills:** ML, DATA, TEST
- **Size:** 12 h:
  1. eval kit (3 h)
  2. fusion variants (4 h)
  3. Rust operator (3 h)
  4. write-up (2 h)
- **Built by AI vs. by him:** AI provides the indexes and retrieval runs. He writes the
  fusion, the tuner and the eval statistics.
- **Done-condition:**
  - Tuned CC (50 labels) ≥ RRF + 1.5 nDCG@10 on average across the 3 held-out sets, and
    never worse than RRF − 0.5 on any one.
  - Paired bootstrap CIs are reported.
  - The Rust operator matches the Python reference to 1e-6.
- **Pushback hooks:** a maintainer says "RRF is parameter-free and users love it".
- **Ownership change request:** add a min-max vs. z-score normalization choice.
- *Overlap note:* Luigi has a RAG app; this deliverable is an engine operator plus an eval
  kit, not an app.

### PLB-08 Design review: one million tenants
- Company: Plumbline   Type: design-review   Level: L5
- **Real-world grounding:** turbopuffer namespaces (a prefix + WAL per namespace). Weaviate
  multi-tenancy: tenants in Active, Inactive or Offloaded states, eventually consistent
  across nodes ([states](https://docs.weaviate.io/weaviate/manage-collections/tenant-states)).
  Qdrant payload-based tenancy (unverified; not re-checked).
- **Ticket:** "A member company wants 1M end-user tenants with Zipf-distributed sizes (median
  2k vectors, largest 50M). Index-per-tenant, a shared index with a tenant filter, or a hybrid
  with promotion? Bring a cost/latency model and an RFC draft."
- **Stack:** Python model + RFC.
- **Skills:** SD, DB, COMM
- **Size:** 10 h:
  1. reading (2 h)
  2. model (4 h)
  3. RFC (2 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the simulator (hidden) and price sheet. He writes
  the model and the RFC.
- **Done-condition:**
  - Monthly cost and p99 predictions within 20% of the simulator for 3 tenant distributions.
  - The RFC passes the rubric: noisy neighbors, metadata fan-out, tenant deletion/GDPR,
    promotion thresholds, compaction scheduling.
- **Pushback hooks:** a maintainer wants one design for every tenant size.
- **Ownership change request:** promotion/demotion hysteresis.


### PLB-09 Paper → prod: learned index for the doc-ID → row lookup
- Company: Plumbline   Type: perf-hunt (paper-inspired)   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P14
- **Paper:**
  - Kraska et al., "The Case for Learned Index Structures", SIGMOD 2018
    ([arXiv 1712.01208](https://arxiv.org/abs/1712.01208)).
  - Kipf, Marcus et al., "SOSD: A Benchmark for Learned Indexes"
    ([arXiv 1911.13014](https://arxiv.org/abs/1911.13014)).
- **What it claims:**
  - Kraska et al. treat an index as a model of the key CDF; a recursive model index (RMI)
    was "up to 70% faster than cache-optimized B-Trees" with an order of magnitude less
    memory, on real datasets.
  - SOSD's follow-up found learned models often beat tuned traditional structures, with
    caveats.
- **Real-world grounding:** every Plumbline segment maps sorted 64-bit doc IDs to row offsets.
  This lookup sits in the rescoring and filter paths (PLB-02/04) and is currently binary
  search plus a B-tree-ish page index.
- **Ticket:** "Our team wants to try a learned index (a two-level RMI, or a PGM-style
  piecewise-linear model) for the doc-ID lookup. It must have bounded error and fall back to
  local search. Reproduce the paper's speed/memory trade-off on SOSD datasets and on our own
  segment keys, then decide if it goes in the format RFC."
- **Stack:** Rust: cache-conscious code, `criterion` benchmarks.
- **Skills:** PERF, DB, ML
- **Size:** 16 h:
  1. read the papers + SOSD (3 h)
  2. baselines: binary search, Eytzinger layout, a B-tree (3 h)
  3. RMI with error bounds + last-mile search (6 h)
  4. benchmarks + RFC note (4 h)
- **Built by AI vs. by him:** AI provides SOSD dataset downloads (e.g. `books`, `fb`, `osm`
  200M-key sets; subsample to fit RAM) and real segment-key dumps. He writes the index and the
  benchmarks.
- **Done-condition:**
  - **Reproduce:** on ≥ 2 SOSD datasets, his RMI is ≥ 1.3× faster (mean lookup) than his
    B-tree baseline, using ≤ 1/10 of its memory.
  - On `osm` (known to be hard), he reports honestly whether it wins.
  - Lookups are correct for 100% of 10M random probes, including absent keys (property
    test).
  - Build time ≤ 2 s per 100M keys.
- **Pushback hooks:** a maintainer: "segments are immutable, so a perfect hash is simpler".
  He must compare, because range scans need order.
- **Ownership change request:** persist the model in the segment footer with a format version
  and a fallback flag.

### PLB-10 Blog → prod: regex search over the text column with a trigram index
- Company: Plumbline   Type: build (blog-inspired)   Level: L4
- **Blog:**
  - Russ Cox, "Regular Expression Matching with a Trigram Index, or How Google Code Search
    Worked" (2012, [swtch.com](https://swtch.com/~rsc/regexp/regexp4.html), memory).
  - Reused by Etsy's Hound and others ([background](https://en.wikipedia.org/wiki/Trigram_search)).
  - Recent take: Cursor's "Fast regex search" ([blog](https://cursor.com/en-US/blog/fast-regex-search)).
- **What it claims:** turn a regex into a boolean query over trigrams (AND/OR of required
  trigrams). Use a posting-list index to find candidate documents, then run the real regex
  only on candidates. That makes regex search over large code corpora interactive.
- **Real-world grounding:** member companies store code chunks for coding agents in Plumbline
  and want `grep`-like exact and regex queries next to vector search. Agents call regex
  search constantly.
- **Ticket:** "Our team wants to add regex search over text columns using the trigram-index
  technique from Russ Cox's post:
  - trigram extraction at ingest
  - posting lists in segments
  - regex → trigram-query compilation, following the post's analysis rules: emptyable,
    exact, prefix/suffix sets
  - verification with Rust's `regex` crate."
- **Stack:** Rust (`regex-syntax` for the parse tree).
- **Skills:** DB, PERF, READ, TEST
- **Size:** 26 h:
  1. read the post + build a toy (4 h)
  2. ingest + posting lists (6 h)
  3. regex → query compiler (8 h)
  4. integration + benchmarks (5 h)
  5. fuzz tests (3 h)
- **Built by AI vs. by him:** AI provides the corpus loader (a Linux kernel source snapshot,
  ~1.2 GB of text) and a query set. He writes the index, the compiler and the verification.
- **Done-condition:**
  - **Reproduce:** the post's candidate-then-verify scheme gives results identical to
    brute-force `regex` scanning on 200 queries plus 10k fuzzed
    regexes: zero false negatives, the property that matters.
  - **Apply:** on 20 selective queries, median latency ≥ 50× faster than brute force.
  - Index size ≤ 35% of corpus size.
  - Queries that compile to "match all" (e.g. `.*`) are detected and fall back to a scan.
- **Pushback hooks:** a contributor wants to skip the compiler and require users to pass
  literals. He must show agent queries are full regexes.
- **Ownership change request:** case-insensitive mode without tripling index size.

---
## Sluicegate — "features you can trust": managed feature platform + data-quality layer

- **Niche / domain:** ML data platforms: feature store, data quality, training-data
  curation.
- **Stage:** growth. Series C, ~220 people. Customers are fintech fraud/risk teams,
  marketplaces, and companies fine-tuning LLMs on their own data.
- **Culture:** correctness-obsessed ("silent data bugs are sev-1"). Customer SLAs on
  freshness and serving latency. Forward-deployed engineers in customer Slacks. Data
  contracts everywhere. "Show me the backfill" is the review question.
- **Stack, and why:**
  - Python SDK + transformations; SQL (DuckDB locally, Spark in prod) for batch.
  - Go for online serving and streaming: latency and modest GC, like Feast's Go server.
  - Redpanda/Kafka, Redis online store, Parquet/Iceberg offline.
  - Rust for CPU-bound curation tools.
  - Real peers: Chronon is Scala on Spark/Flink; Tecton; Chalk.
- **Team roster:** EM (Data Correctness), tech lead, staff data engineer, 2 peers (streaming;
  online store), PM, forward-deployed engineer, junior (SDK tests/docs).
- **Main codebase sketch:**
  - `sg-sdk/`: Python feature definitions
  - `sg-offline/`: point-in-time training-set builder
  - `sg-stream/`: Go windowed aggregations
  - `sg-online/`: Go serving + Redis
  - `sg-quality/`: profiles, drift, contracts
  - `sg-curate/`: dedup, PII, label audit
  - `fixtures/`: synthetic fraud and marketplace data with planted issues
- **In-house tools this company would build:** PIT join engine, skew detector, drift monitor,
  data-contract checker, near-dup remover, PII scrubber with measured recall, label-error
  finder, backfill verifier, freshness SLO monitor.
- **Inspired by:**
  - Airbnb ([Chronon](https://airbnb.tech/opensource/chronon/))
  - Tecton ([postings](https://jobs.lever.co/tecton/928ddfbd-0977-409f-a70e-708f746ea055)), Chalk ([architecture](https://docs.chalk.ai/docs/architecture))
  - Feast
  - Uber ([D3](https://www.uber.com/blog/d3-an-automated-system-to-detect-data-drifts),
    [Hue / deployment safety](https://www.uber.com/en-IN/blog/raising-the-bar-on-ml-model-deployment-safety/))
  - Datadog feature stores ([posting](https://careers.datadoghq.com/detail/7050412))
  - Hugging Face (datatrove/FineWeb), cleanlab, Presidio
- **Projects:** SLG-01 … SLG-10. Paper-inspired: ★SLG-09 (CUSUM, cross-domain) and ★SLG-10 (Snorkel). SLG-06 (Northcutt et al.) is also paper-grounded.

### SLG-01 Review: the point-in-time join that leaks the future
- Company: Sluicegate   Type: review-to-own   Level: L1
- **Real-world grounding:** Chronon's temporally accurate backfills; Feast's PIT semantics,
  where TTL is relative to each entity row's timestamp
  ([docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)).
- **Ticket:** "Lin's PR rewrites `get_training_set()` as an as-of join in DuckDB; the pandas
  version was too slow. Review and own."
- **Stack:** Python + SQL (DuckDB).
- **Skills:** DATA, DB, TEST, READ
- **Size:** 4 h in 3 blocks.
- **Built by AI vs. by him:** AI writes the PR, the fixtures and a hidden leakage suite. He
  writes the review, fixes and tests.
- **Done-condition:** the hidden leakage suite passes 100%; ≥ 4 of 5 bugs found; still ≥ 10×
  faster than pandas on 50M rows.
- **Planted bugs:**
  1. `<=` instead of `<` between feature time and label time, so same-second events leak.
  2. Feature TTL is ignored.
  3. The join uses `ingested_at` (processing time) instead of `event_time`.
  4. Naive timestamps are assumed UTC, but one source is America/Sao_Paulo.
  5. Ties at equal timestamps are resolved non-deterministically.
- **Ownership change request:** an `--audit` flag that prints which feature row was chosen
  for 100 sampled labels.

### SLG-02 Online/offline skew detector
- Company: Sluicegate   Type: add-your-part   Level: L2
- **Real-world grounding:** Uber Hue verifies online-offline feature parity and can block
  promotions. Chronon measures training-serving skew. Rules of ML #29 (log serving features)
  and #32 (reuse code between training and serving)
  ([Google](https://developers.google.com/machine-learning/guides/rules-of-ml)).
- **Ticket:** "sg-online logs 1% of served feature vectors. Build the comparator:
  - recompute the same features offline for each logged (entity, timestamp)
  - compare with type-aware tolerances
  - attribute a likely cause: staleness, default-value mismatch, precision, missing join
    key."
- **Stack:** Python + SQL (DuckDB).
- **Skills:** DATA, OBS, DB
- **Size:** 10 h:
  1. recompute join (3 h)
  2. comparators (3 h)
  3. cause attribution (2 h)
  4. report + review (2 h)
- **Built by AI vs. by him:** AI provides the serving logs and offline store. He writes the
  comparator and the attribution.
- **Done-condition:**
  - The replay has 6 planted differences:
    1. stream lag
    2. -1 vs. null defaults
    3. float32 vs. float64
    4. timezone bucket shift
    5. missing-key fallback
    6. an *intended*, documented difference
  - He detects all 5 real ones with the correct feature and cause class.
  - 0 alerts on the intended one; false-positive rate < 1% over 200 clean features.
- **Pushback hooks:** a peer uses one global 1e-6 tolerance for floats and counts alike.
- **Ownership change request:** a daily top-5 skew report in markdown.

### SLG-03 Streaming windowed aggregations that match the backfill
- Company: Sluicegate   Type: build   Level: L4
- **Real-world grounding:**
  - Chronon defines features once for batch and streaming.
  - Tecton realtime teams serve "100K+ QPS with millisecond latency", and their roles cover
    "online ingestion and serving" ([posting](https://builtin.com/job/staff-software-engineer-realtime-data/7080774)).
  - Chalk's online path runs under 5 ms.
- **Ticket:** "Implement sliding-window aggregations per `card_id` from Redpanda:
  count/sum/approx-distinct over 10 m, 1 h and 24 h. Use event-time semantics and watermarks,
  allow events up to 5 min late, and produce exactly the batch backfill's values at window
  boundaries." It starts with a design doc.
- **Stack:** Go. sg-stream is Go, with franz-go and allocation-aware code to keep GC
  pauses down.
- **Skills:** DIST, DATA, PERF, TEST
- **Size:** 30 h. Design doc (4 h), then:
  1. event-time windows + watermarks (8 h)
  2. state + checkpointing to offsets (8 h)
  3. Redis sink (4 h)
  4. batch-equivalence and fault tests (6 h)
- **Built by AI vs. by him:** AI provides the event generator, batch reference and docker
  kit. He writes the streaming job.
- **Done-condition** (20k events/s, 2% out of order by ≤ 5 min):
  - Streaming equals batch for ≥ 99.99% of (key, window-end) pairs: exact for count/sum,
    HLL distinct within 2%.
  - p99 event-to-online freshness ≤ 2 s.
  - 20 kill/restart cycles cause no double counting.
- **Pushback hooks:**
  - The lead wants processing-time windows.
  - A peer writes Redis once per event (write amplification).
- **Ownership change request:** Chronon-like tiled pre-aggregation that cuts Redis writes by
  ≥ 5×.

### SLG-04 Incident: the fraud model's AUC dropped 4 points overnight
- Company: Sluicegate   Type: incident   Level: L3
- **Real-world grounding:** Uber D3: the most impactful data regressions are silent, so
  detection shouldn't depend on hand-set thresholds. Uber Hue runs drift checks.
- **Ticket:** "Customer FinCo: daily-eval AUC fell from 0.91 to 0.87. No pipeline failed. No
  alert fired."
- **Stack:** Python + SQL.
- **Skills:** DEBUG, DATA, OBS, COMM
- **Size:** 8 h:
  1. triage (2 h)
  2. root causes (2 h)
  3. monitor + contract test (2 h)
  4. backfill + postmortem (2 h)
- **Built by AI vs. by him:**
  - AI provides 37 days of data: 30 clean, 7 broken.
  - Two causes:
    1. The upstream payments team switched `amount` from dollars to cents in one region.
    2. A merchant-category enum was renamed (`GROCERY` → `grocery_store`), so it falls into
       the unknown bucket.
  - He writes the diagnosis, monitor, contract test, backfill and postmortem.
- **Done-condition:**
  - His monitor alerts within 1 h of the break on both causes, with zero alerts on the 30
    clean days (which include holiday seasonality).
  - The fixed backfill restores AUC ≥ 0.905.
  - The contract test fails on the upstream change.
  - The postmortem passes the checker.
- **Pushback hooks:** the manager wants PSI > 0.2 on every feature, which storms on seasonal
  days.
- **Ownership change request:** seasonality-aware baselines (same weekday, last 4 weeks).

### SLG-05 Perf-hunt: near-duplicate removal on 5M documents, one box
- Company: Sluicegate   Type: perf-hunt   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P33
- **Real-world grounding:**
  - FineWeb's datatrove pipeline: per-dump MinHash beat global dedup
    ([arXiv 2406.17557](https://arxiv.org/abs/2406.17557)).
  - One user reports datatrove's MinHash stage ran > 3 h 50 min on sample-10BT without
    finishing ([forum](https://discuss.huggingface.co/t/fastdedup-rust-based-dataset-deduplication-benchmarks-on-fineweb-sample-10bt/173672), single report).
- **Ticket:** "A customer wants their 5M-doc fine-tuning corpus near-deduped nightly. Our
  Python MinHash-LSH takes 6 h. Make it < 20 min on one 12-core box at equal quality."
- **Stack:** Rust (rayon, explicit memory layout) behind a Python CLI. Shingling and hashing
  are CPU-bound.
- **Skills:** PERF, DATA, OS
- **Size:** 18 h:
  1. profile the Python baseline (2 h)
  2. Rust shingling + MinHash (6 h)
  3. LSH banding + union-find (5 h)
  4. quality eval (3 h)
  5. write-up (2 h)
- **Built by AI vs. by him:** AI provides the Python baseline, a FineWeb subset and a labeled
  pair sample. He writes the Rust tool.
- **Done-condition:**
  - ≤ 20 min wall-clock and ≤ 16 GB peak RAM on the 5900X (calibrated ≤ 0.06× baseline).
  - On 20k labeled pairs (truth: exact 5-gram Jaccard ≥ 0.8): precision ≥ 0.95, recall ≥ 0.90.
  - Deterministic cluster IDs across runs.
- **Pushback hooks:**
  - A peer wants exact all-pairs Jaccard on the GPU, which is O(n²).
  - The lead wants fewer LSH bands, which costs recall.
- **Ownership change request:** per-source vs. global modes, with a report of the removal
  ratio.

### SLG-06 Experiment: find the label errors before the customer trains on them
- Company: Sluicegate   Type: experiment   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P34
- **Real-world grounding:**
  - Test sets average 3.3% label errors, ImageNet val ~6%, and fixing them can change model
    rankings ([Northcutt et al.](https://arxiv.org/abs/2103.14749)).
  - CIFAR-10N ships real human noisy labels alongside clean ones (Wei et al., ICLR'22,
    [arXiv 2110.12088](https://arxiv.org/abs/2110.12088), memory).
- **Ticket:** "Customers upload labeled datasets for managed training. Build
  `sg-curate label-audit`:
  - out-of-sample probabilities via K-fold
  - confident-learning ranking of likely errors
  - a report
  Validate on CIFAR-10N."
- **Stack:** Python/PyTorch, a small ResNet on the 4070. cleanlab only as a baseline; he
  implements the core.
- **Skills:** ML, DATA, TEST
- **Size:** 14 h:
  1. K-fold training (4 h)
  2. confident-learning core (4 h)
  3. validation (3 h)
  4. report (3 h)
- **Built by AI vs. by him:** AI provides data loaders and the training recipe. He writes the
  audit.
- **Done-condition** (CIFAR-10N "worst" labels):
  - precision@1000 of flagged errors ≥ 0.8
  - retraining without the flagged examples improves clean-test accuracy ≥ 2 pts
  - flagged set overlaps cleanlab's ≥ 85%
- **Pushback hooks:** a teammate scores with in-sample predictions, so memorized noise hides
  the errors.
- **Ownership change request:** add the per-class noise matrix to the report.
- *Overlap note:* Luigi fine-tuned a classifier before; this deliverable is a data-quality
  tool.

### SLG-07 PII scrubbing with measured recall
- Company: Sluicegate   Type: build   Level: L3
- **Real-world grounding:**
  - datatrove includes PII formatters.
  - Presidio (now [data-privacy-stack/presidio](https://github.com/data-privacy-stack/presidio)).
  - ai4privacy's labeled set: 406,896 entries, 17 public classes, 6 languages
    ([HF](https://huggingface.co/datasets/ai4privacy/pii-masking-400k); license "other",
    check before bundling).
- **Ticket:** "Enterprise customers require PII removal before data reaches training. Ship
  `sg-curate pii`:
  - structured detectors with regex + checksums: email, phone, cards with Luhn, IBAN
  - NER for names and addresses
  - configurable masking
  - a per-class recall/precision report."
- **Stack:** Python (small NER model on the GPU allowed); optional Rust regex fast path.
- **Skills:** DATA, ML, SEC, PERF
- **Size:** 16 h:
  1. structured detectors (4 h)
  2. NER (4 h)
  3. eval harness (3 h)
  4. throughput (3 h)
  5. report (2 h)
- **Built by AI vs. by him:** AI provides the eval split, an adversarial set and the CLI shell.
  He writes the detectors and the eval.
- **Done-condition** (held-out English split):
  - recall ≥ 0.97 on structured classes, ≥ 0.85 on names; overall precision ≥ 0.9
  - structured-only mode ≥ 5 MB/s per core
  - 0 misses on a 200-item adversarial set: cards with spaces or dashes, plus-tagged emails,
    and similar
- **Pushback hooks:**
  - The lead wants regex only ("NER is too slow"); measure it.
  - The PM wants "100% recall" in the marketing copy.
- **Ownership change request:** a reversible pseudonymization mode (keyed HMAC) so joins still
  work.

### SLG-08 Design review: real-time features for card authorization at p99 ≤ 10 ms
- Company: Sluicegate   Type: design-review   Level: L5
- **Real-world grounding:**
  - Tecton realtime postings: 100K+ QPS; DynamoDB, Redis and BigTable experience.
  - Chalk: < 5 ms online path; Redis or DynamoDB online stores.
  - Chronon's shared batch/stream definitions.
- **Ticket:** "A card-network customer needs features at authorization time:
  - p99 ≤ 10 ms end to end at 50k QPS
  - ≤ 1 s freshness on velocity features
  - 99.99% availability
  - 2-year backfills
  Lambda or kappa? Which online store? On-demand or precomputed? Bring the design and a
  capacity model."
- **Stack:** Python capacity model + whiteboard.
- **Skills:** SD, DB, DIST, COMM
- **Size:** 10 h:
  1. reading (2 h)
  2. model (4 h)
  3. design doc (2 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the reference simulator (hidden). He writes the
  model and the design.
- **Done-condition:**
  - p99 and cost predictions for 3 options within 20% of the simulator.
  - Rubric: hot keys (merchant aggregates), cross-region failover, backfill/stream
    consistency, new-card cold start.
- **Pushback hooks:** the staff engineer says "compute everything on demand from Postgres".
- **Ownership change request:** model a 1% hot-key skew.


### SLG-09 Cross-domain → prod: CUSUM control charts from manufacturing for feature drift
- Company: Sluicegate   Type: experiment (paper-inspired, cross-domain: industrial quality control)   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P50 spectral-residual anomalies
- **Paper:** E. S. Page, "Continuous Inspection Schemes", *Biometrika* 41 (1954), 100–115
  (memory). This is CUSUM, the basis of statistical process control. The standard trade-off
  metric is average run length (ARL): time to detect vs. time between false alarms.
- **What it claims:** accumulating small deviations from a target detects persistent
  shifts much faster than threshold-per-sample (Shewhart) charts, at the same false-alarm
  rate. Its design is tuned directly in ARL terms.
- **Real-world grounding:** silent data regressions are the most impactful (Uber
  [D3](https://www.uber.com/blog/d3-an-automated-system-to-detect-data-drifts)). SLG-04's
  "PSI > 0.2 on everything" baseline alert-storms on seasonal days. Feature monitoring is
  production QC on a stream.
- **Ticket:** "Our team wants to try manufacturing-style SPC for feature monitoring:
  - per-feature CUSUM (and EWMA) on robust summary statistics: null rate, mean/quantiles,
    category shares
  - parameters picked to hit a target in-control ARL
  - compare against our PSI thresholds."
- **Stack:** Python (numpy/pandas) + DuckDB.
- **Skills:** DATA, OBS, ML (stats)
- **Size:** 12 h:
  1. read Page + an SPC primer, derive ARL for the chosen k and h (3 h)
  2. implement CUSUM/EWMA on feature summaries (4 h)
  3. benchmark against PSI (3 h)
  4. write-up (2 h)
- **Built by AI vs. by him:** AI provides a benchmark generator: 200 features × 120 days with
  seasonality, 30 planted shifts (step, slow drift, variance change) of known size and onset,
  plus SLG-04's real incident. He writes the detectors, ARL calibration and evaluation.
- **Done-condition:**
  - **Reproduce:** on simulated in-control data, his empirical ARL₀ is within 15% of the
    theoretical/target value.
  - **Apply:** at matched false-alarm rate (≤ 1 per 30 feature-days), CUSUM's median
    detection delay is ≤ 0.5× PSI's on small (≤ 1σ) persistent shifts.
  - It catches both SLG-04 causes within 1 h.
  - Fewer alerts than PSI on seasonal clean days.
- **Pushback hooks:**
  - The lead: "nobody knows what CUSUM is, PSI is industry standard".
  - A peer forgets to reset after an acknowledged alert, so alarms repeat.
- **Ownership change request:** a self-starting CUSUM for brand-new features with no baseline.

### SLG-10 Paper → prod: weak supervision (Snorkel) for customers with no labels
- Company: Sluicegate   Type: build (paper-inspired)   Level: L3
- **Paper:** Ratner et al., "Snorkel: Rapid Training Data Creation with Weak Supervision",
  VLDB 2018 ([arXiv 1711.10160](https://arxiv.org/abs/1711.10160);
  [PMC copy](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7075849/)).
- **What it claims:** users write *labeling functions*; a generative label model learns their
  accuracies and correlations without ground truth and outputs probabilistic labels. In a
  user study experts built models "2.8× faster" with "45.5%" better predictive performance
  than seven hours of hand labeling. Across datasets, results came "within an average 3.60%"
  of large hand-labeled training sets.
- **Real-world grounding:** Sluicegate customers want classifiers (e.g. "is this merchant
  description a gambling business?") but have no labels. SLG-06 audits labels; this ticket
  creates them.
- **Ticket:** "Our team wants to offer weak supervision in sg-curate:
  - a labeling-function SDK
  - a label model that estimates LF accuracies without ground truth, as Snorkel's
    generative model does
  - coverage/conflict analysis
  - probabilistic labels for training.
  Reproduce Snorkel's headline on a public dataset."
- **Stack:** Python (numpy/PyTorch for the label model; scikit-learn end model). He
  implements the label model (EM or the matrix-completion approach); Snorkel only as a
  reference.
- **Skills:** ML, DATA, API
- **Size:** 16 h:
  1. read the paper (3 h)
  2. LF SDK + LF matrix + analysis (4 h)
  3. label model (5 h)
  4. end-to-end eval on the YouTube spam comments dataset (UCI) or a similar public text set
     (3 h)
  5. report (1 h)
- **Built by AI vs. by him:** AI provides the dataset, a held-out labeled test split and 10
  starter LFs of varying quality. He writes the SDK, label model and evaluation. He also
  writes ≥ 5 of his own LFs.
- **Done-condition:**
  - **Reproduce:** his label model's accuracy on the train split beats majority vote over the
    same LFs by ≥ 2 pts.
  - His estimated LF accuracies are within 0.05 of the true ones (computed with hidden labels)
    for ≥ 8/10 LFs.
  - **Apply:** an end model trained on probabilistic labels scores within 5 pts (F1) of the
    same model trained on the full gold labels, on the held-out test set.
  - LF coverage/overlap/conflict report matches the reference.
- **Pushback hooks:**
  - The PM: "just use an LLM to label everything". He must compare cost and accuracy with an
    LLM-as-LF approach.
  - A peer treats LF outputs as independent votes when two LFs are near-duplicates.
- **Ownership change request:** add an LLM-prompt labeling function type with caching.

---

## Belljar — sandboxes, traces and evals for AI agents

- **Niche / domain:** agent-platform infrastructure, plus LLM evaluation and observability.
- **Stage:** seed. 14 people, a $9M seed, ~300 customers building coding and data agents.
- **Culture:** founders write code. Ship daily behind flags. "Assume the agent is hostile."
  A tiny on-call rotation, customers in shared Slack, Friday demos, and "every flaky thing
  gets a ticket".
- **Stack, and why:**
  - Go control plane and in-sandbox daemon: E2B's orchestrator/runtime is Go
    ([e2b-dev/runtime](https://github.com/e2b-dev/runtime)).
  - Rust at the VMM layer (Firecracker is Rust).
  - TypeScript and Python SDKs.
  - ClickHouse for traces (Langfuse's path); OpenTelemetry GenAI conventions.
  - Nomad/Terraform, as E2B's SRE posting describes.
- **Team roster:** CEO (engineer), CTO, staff systems engineer (virtualization), 2 platform
  engineers (orchestrator; traces), product engineer (SDKs), devrel/PM, junior (evals).
- **Main codebase sketch:**
  - `bj-orchestrator/` (Go): placement, warm pools, lifecycle
  - `bj-envd/` (Go): exec, files, PTY
  - `bj-runtime/`: cgroups/seccomp; Firecracker behind an interface
  - `bj-traces/`: OTLP → ClickHouse
  - `bj-evals/`: runner, judges, stats
  - `sdk-py/`, `sdk-ts/`
- **In-house tools this company would build:** exec supervisor, isolation policy + escape
  bench, warm-pool/snapshot manager, trace ingester, eval runner with error bars, judge
  calibration kit, tool-call idempotency layer, usage metering.
- **Inspired by:**
  - E2B ([snapshots](https://docs.e2b.dev/sandbox/snapshots); 200 ms posting)
  - Modal ([memory snapshots](https://modal.com/blog/mem-snapshots))
  - Fly.io ([Firecracker vs gVisor](https://fly.io/learn/firecracker-vs-gvisor/)), Daytona
  - Langfuse/ClickHouse, Braintrust, inspect_ai
  - SWE-bench ([harness](https://swebench.com/SWE-bench/reference/harness))
  - Stripe ([idempotency](https://docs.stripe.com/api/idempotent_requests))
- **Projects:** BLJ-01 … BLJ-10. Paper/blog-inspired: ★BLJ-09 (tinyBenchmarks/IRT, cross-domain) and ★BLJ-10 (Brooker's backoff & jitter). Also paper-grounded: BLJ-05 (MT-Bench), BLJ-06 (error bars).

### BLJ-01 Review: `exec` with timeouts that don't time out
- Company: Belljar   Type: review-to-own   Level: L1
- **Real-world grounding:** agent sandboxes and eval harnesses run untrusted commands under
  timeouts. The SWE-bench harness runs per-instance containers. Session and timeout handling
  are a recurring E2B operations topic
  ([Blaxel](https://blaxel.ai/blog/e2b-session-limit.html), third-party). The planted bugs
  are classic POSIX process-group pitfalls.
- **Ticket:** "Ravi's PR adds envd `exec`: stream stdout/stderr over gRPC, enforce a timeout,
  return the exit code. Review and own."
- **Stack:** Go.
- **Skills:** OS, READ, TEST, SEC
- **Size:** 5 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR and an adversarial command suite. He writes the
  review, fixes and tests.
- **Done-condition:**
  - ≥ 4 of 5 bugs found.
  - `sh -c 'sleep 1000 & sleep 1000'` is fully killed at timeout: 0 leftover PIDs after 100
    runs.
  - `yes` output is capped at 10 MiB without envd running out of memory.
  - Signal deaths report 128+N.
  - Per-stream ordering is preserved.
- **Planted bugs:**
  1. No `Setpgid`, and only the child is killed (orphans).
  2. An unbounded `bytes.Buffer`.
  3. `Wait()` is called before the pipes drain, which deadlocks above 64 KiB of output.
  4. `ExitError` signal status is ignored, so a killed process reports 0.
  5. `exec.Command` is used instead of `exec.CommandContext`.
- **Ownership change request:** `--kill-grace 2s` (SIGTERM, then SIGKILL), with tests.

### BLJ-02 Resource isolation: cgroups v2, seccomp, egress policy
- Company: Belljar   Type: add-your-part   Level: L2
- **Real-world grounding:** isolation trade-offs for agent code
  ([Fly.io](https://fly.io/learn/firecracker-vs-gvisor/),
  [Northflank](https://northflank.com/blog/firecracker-vs-gvisor)). E2B hires for
  Firecracker, Cloud Hypervisor and gVisor experience
  ([posting](https://jobs.insightpartners.com/companies/e2b/jobs/56631629-systems-engineer)).
- **Ticket:** "Container mode, for self-hosted customers without KVM, has no limits. Add:
  - cgroup v2 limits: `memory.max`, `pids.max`, `cpu.max`
  - a seccomp profile denying ptrace, mount, bpf, kexec and similar
  - a read-only rootfs with tmpfs
  - an egress allowlist."
- **Stack:** Go (runtime layer, cgroupfs directly or libcontainer).
- **Skills:** OS, SEC, NET, TEST
- **Size:** 12 h:
  1. cgroups (3 h)
  2. seccomp (3 h)
  3. filesystem (2 h)
  4. egress (2 h)
  5. escape bench + overhead (2 h)
- **Built by AI vs. by him:** AI provides the runtime glue and the escape-bench suite. He
  writes the limits and policies.
- **Done-condition** (WSL2 or Docker Desktop VM with cgroup v2; verify `cgroup2fs`):
  - a memory hog is OOM-killed inside its own cgroup only
  - a fork bomb is capped
  - a CPU spinner is held to 1 CPU, and the neighbor sandbox's p99 exec latency stays ≤ 1.2×
    idle
  - ptrace/mount/bpf return EPERM
  - blocked egress fails and allowlisted egress works
  - overhead ≤ 5% on a Python test suite
- **Pushback hooks:** a teammate's seccomp profile adds `ptrace` back "for debuggers".
- **Ownership change request:** a per-sandbox disk quota on the writable layer.

### BLJ-03 Warm pools + snapshot restore: sandboxes in under 200 ms
- Company: Belljar   Type: build   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): P21
- **Real-world grounding:**
  - E2B's Platform Engineer posting: sandboxes must not take > 200 ms to start (job board).
  - E2B snapshots capture memory and filesystem.
  - Modal snapshots more than halve cold starts.
  - Cloned VMs share RNG state and must reseed
    ([Firecracker](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/random-for-clones.md)).
- **Ticket:** "p50 sandbox start is 1.4 s. Get p50 ≤ 150 ms and p99 ≤ 400 ms:
  - a warm pool with predictive refill
  - snapshot/restore of a pre-initialized Python environment."
- **Stack:** Go orchestrator, with one of:
  - the Firecracker API, if `/dev/kvm` exists in his WSL2 (nested virtualization,
    unverified on his machine)
  - else CRIU (unverified in WSL2)
  - else paused containers for the pool, with snapshot as a stretch
- **Skills:** OS, PERF, SD, DIST
- **Size:** 30 h:
  1. measure + design (4 h)
  2. warm pool + refill (8 h)
  3. snapshot/restore (10 h)
  4. isolation + entropy tests (4 h)
  5. bench (4 h)
- **Built by AI vs. by him:** AI provides the orchestrator skeleton, the load generator and the
  tests. He writes the pool, restore and reseeding.
- **Done-condition:**
  - 500 starts at 5/s plus bursts of 50/s: start-to-first-exec p50 ≤ 150 ms, p99 ≤ 400 ms.
  - A restored sandbox imports pandas in ≤ 50 ms.
  - No writable state is shared between sandboxes.
  - `os.urandom` differs across restores from one snapshot (fails if identical).
- **Pushback hooks:**
  - The CTO wants a fixed pool of 100.
  - A peer skips RNG reseeding.
- **Ownership change request:** per-template pool sizing from the last hour's demand.

### BLJ-04 Trace ingestion: OTel GenAI spans → ClickHouse
- Company: Belljar   Type: build   Level: L3
- **Real-world grounding:**
  - Langfuse v3 moved traces to ClickHouse: Redis queues, S3, async workers, and
    ReplacingMergeTree with updates turned into inserts and dedup at read
    ([post](https://langfuse.com/resources/engineering/clickhouse-at-agent-scale),
    [ClickHouse](https://clickhouse.com/blog/langfuse-llm-analytics)).
  - OTel GenAI agent spans (`create_agent`, `invoke_agent`, `execute_tool`) are still
    Development ([spec](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans)).
- **Ticket:** "Customers send OTLP from several agent frameworks. Build the ingest path:
  - OTLP/HTTP receiver
  - normalize attributes to GenAI semconv (3 framework dialects)
  - batch insert into ClickHouse
  - a query API for trace trees plus token/cost rollups."
- **Stack:** Go + ClickHouse (Docker) + SQL.
- **Skills:** DB, OBS, API, PERF
- **Size:** 22 h:
  1. schema (3 h)
  2. receiver + batching (6 h)
  3. normalization (4 h)
  4. tree/rollup queries (5 h)
  5. load + property tests (4 h)
- **Built by AI vs. by him:** AI provides span generators per framework, golden files and the
  load generator. He writes the ingest service and the queries.
- **Done-condition:**
  - 20k spans/s sustained for 10 min, with p99 ingest-to-queryable ≤ 5 s.
  - Out-of-order, duplicated and late child spans still produce correct trees, 100% under a
    property-based generator.
  - Rollups equal ground truth.
  - All 3 dialects match the golden files.
- **Pushback hooks:**
  - A peer wants `UPDATE`s for span-end events.
  - The lead says "Postgres JSONB for now".
- **Ownership change request:** tail sampling: keep 100% of error traces and 10% of OK ones,
  consistent by trace ID.

### BLJ-05 Experiment: calibrate the LLM judge
- Company: Belljar   Type: experiment   Level: L3
- **Idea-bank seed** (`06-paper-idea-bank.md`): P35
- **Real-world grounding:**
  - MT-Bench: judge–human agreement approaches human–human agreement, but verdicts are
    position-biased ([arXiv 2306.05685](https://arxiv.org/abs/2306.05685)).
  - Position bias varies by judge, task and quality gap ([arXiv 2406.07791](https://arxiv.org/abs/2406.07791)).
  - Human labels: `lmsys/mt_bench_human_judgments` on Hugging Face (memory).
- **Ticket:** "Customers use our `judge()` with a local open model. Calibrate it on
  human-labeled pairwise comparisons: maximize agreement on held-out data and remove
  position bias."
- **Stack:** Python + vLLM with a 7–8B INT4 instruct model on the 4070.
- **Skills:** ML, TEST, DATA
- **Size:** 14 h:
  1. splits + baseline (3 h)
  2. prompt/rubric iterations on dev (5 h)
  3. swap-and-aggregate (2 h)
  4. held-out eval + write-up (4 h)
- **Built by AI vs. by him:** AI provides the serving kit and dataset loader. He writes the
  judge, the calibration and the stats.
- **Done-condition** (held-out, non-tie pairs):
  - agreement with the human majority ≥ 0.70 (calibrated vs. baseline)
  - swap consistency ≥ 0.90
  - Cohen's κ with a bootstrap CI
  - prompts versioned
  - ≤ 60 min judging run
- **Pushback hooks:**
  - A teammate tuned prompts on the test split.
  - The PM wants 1–10 scores instead of pairwise.
- **Ownership change request:** an abstain option when swapped verdicts disagree, with a
  coverage-vs-accuracy report.

### BLJ-06 Eval runner with error bars and infra-aware retries
- Company: Belljar   Type: build   Level: L4
- **Real-world grounding:**
  - Error bars: SEM, clustered SEs, paired differences, power
    ([Anthropic](https://www.anthropic.com/research/statistical-approach-to-model-evals)).
  - 34 SWE-bench Lite problems have flaky tests, 30 of them flaky even with correct solutions
    ([arXiv 2407.21787](https://arxiv.org/abs/2407.21787)).
  - A serial run takes days; 32 machines cut it to hours ([Epoch](https://epoch.ai/latest/swebench-docker)).
  - [lm-eval #1883](https://github.com/EleutherAI/lm-evaluation-harness/issues/1883)
    "Add Regression Testing".
- **Ticket:** "`bj-evals run` compares agent versions. Make it trustworthy:
  - parallel sandboxes
  - retry infra failures but never task failures
  - detect flaky tasks with pass-flip reruns
  - paired comparisons with clustered SEs
  - a gate that blocks real regressions and passes noise."
- **Stack:** Python (runner, stats) + the Go orchestrator API.
- **Skills:** TEST, ML, DIST, OBS
- **Size:** 26 h. Design (3 h), then:
  1. runner + failure taxonomy (8 h)
  2. flaky detection (4 h)
  3. stats + gate (7 h)
  4. calibration runs (4 h)
- **Built by AI vs. by him:** AI provides a synthetic agent suite: 500 tasks in 50 clusters
  with known pass probabilities, 10% injected infra failures and 5% flaky tasks. He writes the
  runner logic and statistics.
- **Done-condition:**
  - The 95% CI covers the true pass rate in ≥ 93/100 seeded runs.
  - The gate blocks a true 5 pp regression ≥ 90% of the time and false-blocks ≤ 5%.
  - Flaky-task precision ≥ 0.8.
  - The audit log shows no retries of genuine task failures.
  - 8-way parallel on his box.
- **Pushback hooks:**
  - The lead wants "rerun until pass", which inflates scores.
  - A peer computes SEs as if tasks were independent.
- **Ownership change request:** a power-analysis command ("how many tasks/epochs to detect
  3 pp").

### BLJ-07 Incident: the agent refunded a customer twice
- Company: Belljar   Type: incident   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): P10
- **Real-world grounding:**
  - A tool times out after its write succeeded, the agent retries, and the action happens
    twice. Fixes: idempotency, bounded retries, compensation
    ([urandom.io](https://urandom.io/blog/2026-03-03-agentic-ai-idempotency-retries-and-compensation)).
  - Stripe saves the first result per idempotency key, prunes keys after ≥ 24 h, and errors
    on parameter mismatch ([docs](https://docs.stripe.com/api/idempotent_requests)).
- **Ticket (page):** "A customer's billing agent issued two refunds for one ticket. The trace
  shows one `refund()` tool call, but the payments mock received two POSTs. Fix it
  platform-wide."
- **Stack:** Go tool-execution proxy + SQLite/Redis dedup store.
- **Skills:** DIST, DEBUG, OBS, API, COMM
- **Size:** 10 h:
  1. trace forensics (2 h)
  2. both causes (2 h)
  3. idempotency layer (4 h)
  4. postmortem (2 h)
- **Built by AI vs. by him:**
  - AI provides the incident replay with two causes:
    1. The gateway retried on a 504 after the tool had already succeeded.
    2. The LLM re-issued the call after seeing the timeout.
  - AI also provides the chaos injector.
  - He writes the fix and the postmortem.
- **Done-condition:**
  - Chaos replay: 10k tool calls with 20% timeouts, drops and duplicate deliveries.
  - 0 duplicate side effects; every logical call completes or fails definitively.
  - Keys stay stable across LLM re-issues: derived from the trace + step's semantic ID, not
    request bytes.
  - p99 overhead ≤ 5 ms.
  - The postmortem passes the checker.
- **Pushback hooks:** the manager wants all retries disabled. The replay measures the
  availability cost.
- **Ownership change request:** TTL/GC for the dedup store, with a test that keys outlive the
  max retry horizon.

### BLJ-08 Design review: a multi-tenant sandbox fleet (Firecracker vs. gVisor vs. containers)
- Company: Belljar   Type: design-review   Level: L5
- **Real-world grounding:**
  - Dedicated guest kernel (KVM) vs. userspace kernel, density vs. assurance (Fly.io,
    Northflank).
  - E2B's team includes original Firecracker authors
    ([posting](https://www.builtinsf.com/job/product-engineer-backend-developer/10243084), job board).
  - Snapshot-clone entropy (Firecracker doc).
- **Ticket:** "An enterprise will run untrusted agent code for 50k end users. Choose isolation
  per tier, density targets, snapshot strategy and network isolation. Bring a threat model and
  a cost/density model."
- **Stack:** whiteboard + Python cost model.
- **Skills:** SD, SEC, OS, COMM
- **Size:** 10 h:
  1. reading (3 h)
  2. threat model (2 h)
  3. cost/density model (3 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the reference simulator (hidden). He writes the
  model and the threat model.
- **Done-condition:**
  - Density/cost within 20% of the simulator for 3 workload mixes.
  - The threat model covers the rubric:
    - kernel exploit and side channels
    - metadata-service SSRF
    - noisy neighbor
    - clone secrets/entropy
    - egress abuse (crypto-mining)
- **Pushback hooks:** the CEO wants containers everywhere for density.
- **Ownership change request:** add a GPU-sandbox tier to the model.


### BLJ-09 Cross-domain → prod: psychometrics (IRT) to run evals on 1% of the items
- Company: Belljar   Type: experiment (paper-inspired, cross-domain: educational testing)   Level: L4
- **Paper:** Maia Polo et al., "tinyBenchmarks: evaluating LLMs with fewer examples",
  ICML 2024 ([arXiv 2402.14992](https://arxiv.org/abs/2402.14992),
  [PMLR](https://proceedings.mlr.press/v235/maia-polo24a.html)). It borrows Item Response
  Theory (IRT) from educational testing: models are test-takers, items have difficulty and
  discrimination.
- **What it claims:** to estimate an LLM's MMLU score (14K items), "it is sufficient to
  evaluate this LLM on 100 curated examples". IRT-based selection and estimation beat
  stratified random sampling. They released tiny versions of Open LLM Leaderboard, MMLU, HELM
  and AlpacaEval 2.0.
- **Real-world grounding:** customers run `bj-evals` on every agent commit, and full suites in
  sandboxes are slow and expensive. Serial SWE-bench runs take days
  ([Epoch](https://epoch.ai/latest/swebench-docker)).
- **Ticket:** "Our team wants to try tinyBenchmarks' IRT approach for cheap per-commit evals:
  - fit a 2-parameter IRT model on historical per-item results from many models
  - pick ~100 anchor items
  - estimate full-suite accuracy for a new model from the anchors alone
  - report an uncertainty interval.
  Reproduce the paper's MMLU result first, then apply it to our own suite."
- **Stack:** Python (PyTorch or pyro for IRT fitting, numpy).
- **Skills:** ML (stats), TEST, DATA
- **Size:** 18 h:
  1. read paper + IRT basics (3 h)
  2. data: per-item correctness for ~400 models from public Open LLM Leaderboard detail
     datasets (3 h)
  3. 2PL IRT fit + anchor selection (5 h)
  4. estimator + intervals (4 h)
  5. apply to Belljar's synthetic agent suite from BLJ-06 (3 h)
- **Built by AI vs. by him:** AI provides data loaders and a model-wise train/test split
  (held-out models, not held-out items). He writes the IRT fit, selection, estimator and
  evaluation.
- **Done-condition:**
  - **Reproduce:** with ≤ 100 MMLU items, mean absolute error of estimated vs. true full-MMLU
    accuracy on held-out models is ≤ 2.5 pts, and ≤ 0.6× the MAE of 100 random items.
  - Interval coverage ≥ 85% at nominal 90%.
  - **Apply:** on the BLJ-06 suite, his estimator ranks 10 agent versions with Kendall τ ≥ 0.8
    vs. full runs.
- **Pushback hooks:**
  - The lead: "selected items will go stale as models improve". He must design anchor
    refresh.
  - A peer validates on the same models the IRT was fit on (leakage).
- **Ownership change request:** flag when a new model's response pattern is out of
  distribution for the IRT fit (person-fit statistic), so the estimate isn't trusted.

### BLJ-10 Blog → prod: backoff with jitter + retry budgets for the tool proxy
- Company: Belljar   Type: perf-hunt (blog-inspired)   Level: L2
- **Idea-bank seed** (`06-paper-idea-bank.md`): P06
- **Blog:**
  - Marc Brooker, "Exponential Backoff And Jitter", AWS Architecture Blog
    ([post](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)).
  - Follow-up on his own blog ([2022](https://brooker.co.za/blog/2022/08/11/backoff.html)).
  - The AWS Well-Architected guidance that cites it
    ([REL05-BP03](https://docs.aws.amazon.com/en_us/wellarchitected/2022-03-31/framework/rel_mitigate_interaction_failure_limit_retries.html)).
- **What it claims:** in a contention simulation, plain exponential backoff without jitter
  is "the clear loser" and still produces clusters of calls. "Full Jitter" and "Equal
  Jitter" do about the same number of calls; "Decorrelated Jitter" does more; all three cut
  total work substantially. The 2022 follow-up says backoff only helps long-term if it
  reduces total work, hence retry budgets.
- **Real-world grounding:** after BLJ-07, every agent sandbox retries rate-limited tools
  (GitHub API, a customer's CRM). When a shared upstream rate-limits, 500 sandboxes retry in
  lockstep (a thundering herd) and the upstream bans the customer's key.
- **Ticket:** "Our team wants to apply Brooker's jitter strategies plus a per-tenant retry
  budget in the tool proxy. First reproduce the blog's simulation, then ship the policy and
  show it on our herd scenario."
- **Stack:** Python for the simulation, matching the blog's setup; Go for the proxy change.
- **Skills:** DIST, PERF, API, TEST
- **Size:** 8 h:
  1. reproduce the blog's simulation (3 h)
  2. Go policy: full jitter + cap + retry budget as a token bucket of retries (3 h)
  3. herd scenario + write-up (2 h)
- **Built by AI vs. by him:** AI provides the tool proxy, a rate-limited mock upstream (429
  with Retry-After) and the herd generator. He writes the simulation, policy and tests.
- **Done-condition:**
  - **Reproduce:** his simulation shows the blog's ordering. No-jitter does the most total
    calls and has the longest completion time; full and equal jitter are within 10% of each
    other in calls; decorrelated does more calls than full jitter. Plots included.
  - **Apply:** in the 500-sandbox herd scenario, total upstream calls ≤ 0.4× the current
    no-jitter policy.
  - The upstream never sees > 2× its rate limit in any 1 s window.
  - When the retry budget is exhausted, callers get a definite error instead of retrying
    forever.
  - Retry-After is honored when present.
- **Pushback hooks:** a peer wants "retry 10 times with 1 s sleep".
- **Ownership change request:** expose retry-budget consumption as a per-tenant metric with an
  alert.

---

## Mothlight — field cameras that only wake you for animals

- **Niche / domain:** computer-vision product with on-device/edge inference and model
  compression.
- **Stage:** seed. 11 people. Ships solar camera traps with an on-device detector and a cloud
  dashboard to conservation NGOs, ranches and research stations.
- **Culture:** hardware and ML in one room ("battery is the budget"). Rangers send WhatsApp
  photos of failures. Mission-driven. Models are evaluated by site, never by random split.
  Modest pace, high ownership.
- **Stack, and why:**
  - Python/PyTorch training on an Ultralytics-style detector, with ONNX as the interchange
    format.
  - TensorRT for the NVIDIA-edge SKU (the 4070 stands in for a Jetson).
  - ONNX Runtime / ExecuTorch for the ARM SKU.
  - C++ device pipeline; Label Studio; DuckDB telemetry; a Go or Python OTA service.
  - Frigate made the same ONNX-first shift.
- **Team roster:** founder-CEO (ecologist), CTO (embedded), ML lead, ML engineer peer,
  firmware engineer, field-ops PM, labeling coordinator, junior ML engineer.
- **Main codebase sketch:**
  - `mt-train/`: datasets, location-split tool, training, eval
  - `mt-device/` (C++): capture → preprocess → infer → postprocess → decide
  - `mt-export/`: ONNX/TensorRT/INT8 calibration
  - `mt-label/`: active learning + Label Studio
  - `mt-fleet/`: OTA, telemetry, canary
  - `datasets/`: LILA BC subsets ([LILA](https://lila.science), memory;
    [mirror](https://source.coop/agentmorris/lila-wildlife))
- **In-house tools this company would build:** location-aware eval, train/device parity
  tester, INT8 calibration tuner, blank filter, active-learning selector, telemetry drift
  dashboard, OTA canary/rollback, energy/latency profiler.
- **Inspired by:**
  - Nightjar / TrailGuard AI ([RESOLVE](https://resolve.ngo/projects/trailguard-ai-and-nightjar))
  - Google SpeciesNet / Wildlife Insights ([repo](https://github.com/google/cameratrapai))
  - MegaDetector ([agentmorris/MegaDetector](https://github.com/agentmorris/MegaDetector))
  - Frigate, Ultralytics
  - ExecuTorch ([1.0](https://pytorch.org/blog/introducing-executorch-1-0/))
- **Projects:** MTH-01 … MTH-10. Paper-inspired: ★MTH-09 (BioCLIP distillation) and ★MTH-10 (occupancy model, cross-domain). Also paper-grounded: MTH-02 (Beery et al.), MTH-04 (Norouzzadeh et al.).

### MTH-01 Review: training/device preprocessing parity
- Company: Mothlight   Type: review-to-own   Level: L1
- **Real-world grounding:** edge deployments must reproduce training-time preprocessing
  exactly. Frigate's model config exposes input pixel format and tensor layout for this
  reason (from memory, unverified field names). Detector backends churn
  ([Frigate #18605](https://github.com/blakeblackshear/frigate/discussions/18605)). Mostly
  practitioner knowledge rather than a single citation.
- **Ticket:** "Jules's PR ports preprocessing (letterbox, normalize, NCHW) and postprocessing
  (decode, NMS, un-letterbox) to C++ in mt-device. Review and own."
- **Stack:** C++17 device code + a Python reference.
- **Skills:** READ, DEBUG, TEST, ML
- **Size:** 5 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR, a reference pipeline and 500 images. He writes
  the review, fixes and a per-stage parity test.
- **Done-condition:**
  - Device mAP50 within 0.5 pt of the Python reference.
  - His parity test catches each planted bug on its own (mutation check).
  - ≥ 4 of 5 found in review.
- **Planted bugs:**
  1. BGR vs. RGB.
  2. Pad value 0 instead of 114.
  3. Nearest instead of bilinear resize.
  4. Un-letterboxing ignores the pad offset on one axis.
  5. NMS is class-agnostic on the device but per-class in the reference.
- **Ownership change request:** a `--dump-stage` flag that writes intermediate tensors as
  `.npy`.

### MTH-02 Experiment: the blank-frame filter
- Company: Mothlight   Type: experiment   Level: L2
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P36 temperature scaling
- **Real-world grounding:**
  - Camera traps produce volumes that take days to weeks to sift ([SpeciesNet](https://techcrunch.com/2025/03/03/google-releases-speciesnet-an-ai-model-designed-to-identify-wildlife/)).
  - MegaDetector sorts blanks at ~95% recall (ODU poster).
  - "No detection = empty" cuts performance by up to 18.5% ([arXiv 2410.12769](https://arxiv.org/abs/2410.12769)).
  - Models generalize poorly to new locations ([Beery et al.](https://arxiv.org/abs/1807.04975)).
- **Ticket:** "Uploads cost battery and satellite bandwidth. Train an on-device blank filter.
  Missing an animal is 20× worse than uploading a blank. Evaluate on held-out *locations*."
- **Stack:** Python/PyTorch, MobileNetV3/EfficientNet-B0 class, on a LILA BC subset (e.g.
  Caltech Camera Traps; per-dataset licenses).
- **Skills:** ML, DATA, TEST
- **Size:** 12 h:
  1. location/sequence split (2 h)
  2. baseline (3 h)
  3. cost-weighted training + threshold choice (4 h)
  4. latency + write-up (3 h)
- **Built by AI vs. by him:** AI provides the data download and metadata. He writes the split,
  model, threshold and evaluation.
- **Done-condition** (held-out locations):
  - animal-frame recall ≥ 0.97 and blank rejection ≥ 0.60
  - model ≤ 10 MB, ≤ 15 ms/frame at batch 1 FP16 on the 4070
  - threshold chosen on validation locations only (audited)
- **Pushback hooks:** a teammate splits randomly by image, so bursts from one trigger land on
  both sides. That gives 99% "recall" that collapses on new sites.
- **Ownership change request:** per-site threshold calibration from a site's first week.

### MTH-03 Perf-hunt: INT8 at 30+ FPS with ≤ 1 mAP loss
- Company: Mothlight   Type: perf-hunt   Level: L3
- **Real-world grounding:**
  - Static INT8 TensorRT YOLOv8 engines run 1.5–3.3× faster but lose 3–7 mAP50-95.
    Calibrating on degraded images didn't consistently help
    ([arXiv 2508.19600](https://arxiv.org/abs/2508.19600)).
  - Frigate moved its detectors to ONNX.
- **Ticket:** "The Jetson SKU needs the detector at INT8. Our first INT8 engine lost 5 mAP.
  Cut latency while keeping the loss ≤ 1.0 mAP50-95 vs. FP16. Options: calibration-set
  choice, per-layer precision fallback, QAT only if needed."
- **Stack:** Python, ONNX, TensorRT on the 4070 as the edge stand-in.
- **Skills:** PERF, MLSYS, ML
- **Size:** 16 h:
  1. baselines (3 h)
  2. calibration studies (4 h)
  3. per-layer sensitivity + mixed precision (5 h)
  4. write-up (4 h)
- **Built by AI vs. by him:** AI provides the exported model, the eval set and the latency
  harness. He writes the calibration/precision strategy and the analysis.
- **Done-condition** (held-out-location set):
  - mAP50-95 drop ≤ 1.0 vs. the FP16 engine
  - batch-1 p99 ≤ 0.6× the FP16 engine (calibrated)
  - a per-layer sensitivity table
- **Pushback hooks:**
  - A peer calibrates on 50 random images.
  - The lead jumps straight to QAT.
- **Ownership change request:** add a Gaussian-noise robustness check to the INT8 gate.

### MTH-04 Active learning: 2,000 labels that count like 4,000
- Company: Mothlight   Type: build   Level: L3
- **Real-world grounding:** active learning matched state-of-the-art accuracy with ~14.1k
  labels on 3.2M images, > 99.5% less labeling ([Norouzzadeh et al.](https://arxiv.org/abs/1910.09716)).
- **Ticket:** "The new region's labeling budget is 2,000 boxes a month. Build
  `mt-label select`: batch-mode selection by uncertainty + diversity (k-center over
  embeddings), push tasks to Label Studio, ingest the labels, retrain."
- **Stack:** Python (PyTorch, faiss/sklearn) + Label Studio in Docker.
- **Skills:** ML, DATA, SD
- **Size:** 18 h:
  1. embeddings + uncertainty (4 h)
  2. k-center (3 h)
  3. Label Studio integration (4 h)
  4. simulated rounds (5 h)
  5. write-up (2 h)
- **Built by AI vs. by him:** AI provides the oracle-label simulator and the training script.
  He writes the selector and the loop.
- **Done-condition:**
  - 4 rounds × 500 labels reach mAP50 ≥ random selection at 4,000 labels (mean of 3 seeds).
  - The Label Studio round-trip integration test passes.
  - Selecting 500 from 200k takes ≤ 5 min.
- **Pushback hooks:** the ML lead wants pure uncertainty sampling, which picks near-duplicate
  burst frames.
- **Ownership change request:** reserve part of the budget for rare species.

### MTH-05 Incident: night false positives spiked after firmware 2.3
- Company: Mothlight   Type: incident   Level: L3
- **Real-world grounding:** INT8 detectors are very sensitive to noise (> 60% relative mAP loss
  for YOLOv8n INT8 under medium noise, arXiv 2508.19600). Domain shift by site and condition
  (Beery et al.). Telemetry drift checks (Uber Hue).
- **Ticket:** "Since FW 2.3 reached 40% of devices, ranchers get 10× more night alerts, mostly
  empty IR-noise frames. Daytime is fine. Fix it, and make sure we'd catch the next one."
- **Stack:** Python, DuckDB telemetry, model export tools.
- **Skills:** DEBUG, ML, OBS, DATA
- **Size:** 9 h:
  1. cohort analysis (2 h)
  2. root cause (2 h)
  3. fix: noise-aware augmentation + recalibration, or a per-cohort threshold (3 h)
  4. monitor + postmortem (2 h)
- **Built by AI vs. by him:** AI provides the replayed telemetry; the cause is that FW 2.3
  raised IR gain. He writes the analysis, fix, monitor and postmortem.
- **Done-condition:**
  - Post-FW night data: false-positive alerts/night ≤ 1.2× pre-FW, with animal recall within
    1 pt.
  - The drift monitor flags the FW 2.3 cohort within 6 h of rollout in replay and stays quiet
    on FW 2.2.
  - The postmortem passes the checker.
- **Pushback hooks:** the firmware lead wants a higher night threshold, which kills recall on
  nocturnal species (measured).
- **Ownership change request:** an OTA gate that requires telemetry-stat parity before a
  rollout passes 10%.

### MTH-06 OTA model rollout with shadow mode and auto-rollback
- Company: Mothlight   Type: build   Level: L4
- **Idea-bank seed** (`06-paper-idea-bank.md`): related: P48 sequential canary testing
- **Real-world grounding:**
  - Uber (Oct 2025): shadow testing in > 75% of critical online use cases; controlled rollout
    from a small slice; auto-rollback on thresholds
    ([Uber](https://www.uber.com/en-IN/blog/raising-the-bar-on-ml-model-deployment-safety/)).
  - On-device deployment via ExecuTorch.
- **Ticket:** "Ship models to 2,000 devices safely:
  - signed manifests
  - shadow mode (the new model runs and logs agreement but never alerts)
  - canary 5% → 25% → 100% behind metric gates
  - auto-rollback
  - correct behavior for devices that are offline for days."
  It starts with a design doc.
- **Stack:** Go (OTA service) + a Python device simulator (200 processes).
- **Skills:** SD, DIST, SEC, OBS, TEST
- **Size:** 30 h. Design doc (4 h), then:
  1. manifests + signing (5 h)
  2. shadow mode (6 h)
  3. canary controller (8 h)
  4. offline convergence (4 h)
  5. demo (3 h)
- **Built by AI vs. by him:** AI provides the device simulator and a planted bad model (recall
  drop on one species). He writes the service and controller.
- **Done-condition:**
  - A good model reaches 100% within ≤ 3 canary windows.
  - The bad model rolls back within 2 windows and never exceeds 25%.
  - Every device rejects a tampered manifest or hash.
  - Devices offline during a rollback converge to the right version.
- **Pushback hooks:** the CTO wants to skip shadow mode to save battery. He must quantify the
  shadow sampling cost against the risk.
- **Ownership change request:** per-region rollout waves.

### MTH-07 Design review: on-device vs. cloud species ID under 2 Wh/day
- Company: Mothlight   Type: design-review   Level: L5
- **Real-world grounding:**
  - SpeciesNet: 2,000+ labels, cloud-scale.
  - TrailGuard AI sends edge alerts within seconds; battery claims of 6–12 months
    (secondary).
  - ExecuTorch backends: Arm KleidiAI, Qualcomm Hexagon
    ([Arm](https://newsroom.arm.com/blog/executorch-1-0),
    [Qualcomm](https://www.qualcomm.com/developer/blog/2025/10/bringing-edge-ai-performance-to-pytorch-developers-with-executorch-1-0)).
- **Ticket:** "Customers want species-level alerts in < 60 s from solar cameras on LTE-M or
  satellite. The full species model doesn't fit on the device. Design the cascade:
  - on-device detector → crop selection → uplink → cloud classifier
  - per-stage thresholds
  - an energy and bandwidth budget."
- **Stack:** Python energy/bandwidth model + whiteboard.
- **Skills:** SD, ML, MLSYS, COMM
- **Size:** 10 h:
  1. reading (2 h)
  2. model (4 h)
  3. threshold study (2 h)
  4. whiteboard (2 h)
- **Built by AI vs. by him:** AI provides the reference simulator and the site profiles. He
  writes the model and the design.
- **Done-condition:**
  - Predicted daily energy, uplink bytes and species-alert recall within 15% of the simulator
    for 3 site profiles.
  - His thresholds give recall ≥ 0.9 at ≤ 2 Wh/day in ≥ 2 of 3 profiles.
  - Rubric: night bursts, offline buffering, rare species, cost of model updates.
- **Pushback hooks:** the ML lead wants full-resolution uploads "for retraining".
- **Ownership change request:** model a retraining-sample upload budget.

### MTH-08 Review: the mAP evaluation script
- Company: Mothlight   Type: review-to-own   Level: L2
- **Real-world grounding:** evaluation must split by location, because generalization to new
  sites is poor ([Beery et al.](https://arxiv.org/abs/1807.04975)). Benchmark errors change
  conclusions ([Northcutt et al.](https://arxiv.org/abs/2103.14749)).
- **Ticket:** "Sam's PR replaces the eval notebook with `mt-train eval`. Every model decision
  will hinge on it. Review and own."
- **Stack:** Python (numpy; pycocotools as the reference).
- **Skills:** ML, TEST, READ
- **Size:** 5 h in 4 blocks.
- **Built by AI vs. by him:** AI writes the PR and 3 fixture sets. He writes the review, fixes
  and property tests.
- **Done-condition:** ≥ 4 of 5 bugs found; matches pycocotools mAP50-95 within 0.001 on all 3
  fixtures; the split tool guarantees no location or sequence overlap (property test).
- **Planted bugs:**
  1. A random image-level split (burst leakage).
  2. IoU 0.5 only, labeled as "mAP50-95".
  3. Class-agnostic NMS before evaluation merges co-occurring species.
  4. "Ignore" boxes are dropped, so correct detections get penalized.
  5. The confidence threshold is applied before computing the PR curve.
- **Ownership change request:** a per-location mAP breakdown plus a worst-5-sites report.


### MTH-09 Paper → prod: distill BioCLIP into the on-device species classifier
- Company: Mothlight   Type: experiment (paper-inspired)   Level: L4
- **Paper:** Stevens et al., "BioCLIP: A Vision Foundation Model for the Tree of Life",
  CVPR 2024 ([arXiv 2311.18803](https://arxiv.org/abs/2311.18803),
  [CVF](https://openaccess.thecvf.com/content/CVPR2024/papers/Stevens_BioCLIP_A_Vision_Foundation_Model_for_the_Tree_of_Life_CVPR_2024_paper.pdf)).
  It is a CLIP ViT-B/16 trained on TreeOfLife-10M.
- **What it claims:** it beats existing baselines on fine-grained biology classification "by
  16% to 17% absolute" in zero- and few-shot settings, and does especially well on species
  held out of training. The Microsoft Research page says 17–20%, so the numbers vary by
  source.
- **Real-world grounding:** Mothlight wants species-level labels on the device. Customers
  give few labels per new region (MTH-04), and the full classifier doesn't fit on the device
  (MTH-07). SpeciesNet shows the cloud-model route
  ([repo](https://github.com/google/cameratrapai)).
- **Ticket:** "Our team wants to use BioCLIP as a teacher:
  - reproduce its zero-shot advantage over OpenAI CLIP on our camera-trap crops
  - distill it into a ≤ 10 MB student, using 1k labeled + 50k unlabeled crops
  - beat a student trained on the 1k labels alone."
- **Stack:** Python/PyTorch, open_clip for BioCLIP. A ViT-B/16 teacher fits easily on the
  4070; the student is MobileNetV3/EfficientNet-B0.
- **Skills:** ML, MLSYS, DATA
- **Size:** 18 h:
  1. read + zero-shot eval of CLIP vs. BioCLIP on held-out-location crops (4 h)
  2. teacher logit caching (2 h)
  3. distillation (KD loss with temperature, plus feature distillation optional) (6 h)
  4. INT8 export check (3 h)
  5. write-up (3 h)
- **Built by AI vs. by him:** AI provides MegaDetector-style crops from a LILA dataset with a
  location split, label maps to species names for prompts, and the export path. He writes the
  zero-shot eval, distillation and analysis.
- **Done-condition:**
  - **Reproduce:** BioCLIP zero-shot top-1 beats OpenAI CLIP ViT-B/16 by ≥ 10 pts absolute on
    the held-out-location crops. This is the paper's direction; the domain differs, so
    16–17% isn't required.
  - **Apply:** the distilled student (≤ 10 MB) beats the labels-only student by ≥ 5 pts top-1
    and reaches ≥ 85% of the teacher's top-1.
  - After INT8 export (MTH-03 path) it loses ≤ 1 pt.
  - ≤ 10 ms/crop on the 4070 at batch 1.
- **Pushback hooks:**
  - The ML lead says "just fine-tune BioCLIP and run it in the cloud". He must cost it out
    against MTH-07's bandwidth budget.
  - A peer tunes prompts on the test locations.
- **Ownership change request:** add a "not in our species list" abstain option using the
  teacher's open-vocabulary scores.

### MTH-10 Cross-domain → prod: occupancy modeling from ecology for imperfect detection
- Company: Mothlight   Type: build (paper-inspired, cross-domain: ecology/statistics)   Level: L3
- **Paper:** MacKenzie et al., "Estimating site occupancy rates when detection probabilities
  are less than one", *Ecology* 83(8):2248–2255, 2002
  ([USGS](https://www.usgs.gov/publications/estimating-site-occupancy-rates-when-detection-probabilities-are-less-one)).
- **What it claims:** "Nondetection of a species at a site does not imply that the species is
  absent unless the probability of detection is 1." Use repeated surveys to estimate
  occupancy ψ and detection probability p jointly by likelihood. The estimator is
  approximately unbiased for p > 0.3. In their example, naive occupancy undercounted American
  toads by 44%.
- **Real-world grounding:** Mothlight's conservation customers report "species X present at
  N% of sites" straight from the dashboard. That number is biased low, because the camera and
  detector miss animals. Camera-trap occupancy studies already use this framework. Turning
  detector output into an occupancy report is a product feature.
- **Ticket:** "Ecologists want occupancy estimates with intervals per species per region. Build
  `mt-report occupancy`:
  - group detections into survey occasions (camera-days/weeks)
  - fit the single-season occupancy model by maximum likelihood, with site covariates
    optional
  - fold in the detector's own false-negative rate from validation
  - report ψ̂ ± CI next to the naive estimate."
- **Stack:** Python (numpy/scipy optimize; validate against the R `unmarked` package if
  available, else against a harness reference implementation).
- **Skills:** ML (stats), DATA, API
- **Size:** 12 h:
  1. read the paper, derive the likelihood (3 h)
  2. MLE + profile/bootstrapped CIs (4 h)
  3. detections → occasion matrices from real telemetry (2 h)
  4. simulation study + report (3 h)
- **Built by AI vs. by him:** AI provides a simulator of sites with known ψ and p plus the
  detector's measured miss rate, and real detection logs from a LILA dataset. He writes the
  model, estimator and report.
- **Done-condition:**
  - **Reproduce:** on 200 simulated landscapes (60 sites × 8 occasions, ψ ∈ [0.2, 0.8],
    p ∈ [0.3, 0.7]), mean |ψ̂ − ψ| ≤ 0.05.
  - 95% CI coverage between 0.90 and 0.98.
  - Bias grows for p < 0.3, as the paper warns, and he reports where.
  - **Apply:** on the real logs, the report shows naive vs. corrected occupancy per species.
  - His MLE matches the reference implementation within 1e-3 on 5 fixed datasets.
- **Pushback hooks:**
  - The PM wants one "presence %" number with no interval.
  - A peer treats burst frames within one trigger as separate occasions, which inflates p.
- **Ownership change request:** add a site-level covariate (e.g. habitat type) to ψ, with a
  likelihood-ratio test.

---
## 3. Card index (for the hiring agent and the harness)

73 cards, about 1,050 hours in total. ★ = an explicitly paper/blog-inspired card.
- **By type:** review-to-own 10 · add-your-part 6 · build 17 · perf-hunt 7 · incident 8 ·
  design-review 7 · experiment 18.
- **By level:** L1 7 · L2 11 · L3 30 · L4 18 · L5 7.

| ID | Title | Type | L | h | Lang | Primary skills |
|---|---|---|---|---|---|---|
| KLN-01 | Fix the load generator | review | 1 | 5 | Py | TEST PERF READ |
| KLN-02 | Prefix-cache-aware routing | add-part | 2 | 10 | Go | MLSYS DIST PERF |
| KLN-03 | Short prompts behind long docs | perf | 3 | 14 | Py | PERF MLSYS DEBUG |
| KLN-04 | Quantization acceptance gate | experiment | 3 | 16 | Py | ML TEST MLSYS |
| KLN-05 | Preemption storm incident | incident | 3 | 8 | Py/Go | OBS DEBUG MLSYS |
| KLN-06 | Noisy-neighbor fairness | build | 4 | 28 | Go | SD DIST API |
| KLN-07 | Usage metering | review | 2 | 6 | Go/SQL | DB TEST API |
| KLN-08 | Spec decoding policy | experiment | 4 | 20 | Py/Go | ML PERF MLSYS |
| KLN-09 | P/D disaggregation review | design | 5 | 12 | Py | SD MLSYS PERF |
| KLN-10 | ★ Hedged/tied requests (Tail at Scale) | experiment | 3 | 14 | Go/Py | PERF DIST MLSYS |
| KLN-11 | ★ 2-bit KV cache (KIVI) | experiment | 4 | 20 | Py | ML MLSYS PERF |
| CPL-01 | Health agent review | review | 1 | 5 | Py | DEBUG OBS READ |
| CPL-02 | Gang + backfill in sim | add-part | 2 | 10 | Go | SD DIST OS |
| CPL-03 | Fragmentation incident | incident | 3 | 8 | Go | DEBUG OBS SD |
| CPL-04 | CUDA memory-cap shim | build | 4 | 30 | C | OS MLSYS DEBUG |
| CPL-05 | Chargeback + idle reaper | build | 3 | 14 | Py/SQL | DATA OBS DB |
| CPL-06 | Quotas & borrowing | design | 4 | 10 | YAML/Py | SD DIST COMM |
| CPL-07 | Runtime prediction for backfill | experiment | 3 | 12 | Py/Go | ML DATA SD |
| CPL-08 | GPU block market engine | build | 5 | 40 | Rust | SD DIST TEST |
| CPL-09 | ★ Heterogeneity-aware scheduling (Gavel) | experiment | 4 | 22 | Py/Go | SD ML DIST |
| CPL-10 | ★ Airline EMSR-b for GPU blocks (cross-domain) | experiment | 3 | 12 | Py | ML DATA SD |
| LPL-01 | Async checkpoint review | review | 2 | 6 | Py | OS MLSYS TEST |
| LPL-02 | Exact mid-epoch resume | add-part | 2 | 10 | Py | DIST TEST OS |
| LPL-03 | NCCL watchdog incident | incident | 3 | 9 | Py | DEBUG DIST OBS |
| LPL-04 | Input-bound ranker | perf | 3 | 16 | Py | PERF MLSYS OS |
| LPL-05 | Goodput & MFU | build | 3 | 14 | Py/SQL | OBS DATA MLSYS |
| LPL-06 | Straggler detection | experiment | 4 | 18 | Py | ML OBS DIST |
| LPL-07 | 8k-context OOM | incident | 3 | 7 | Py | DEBUG MLSYS PERF |
| LPL-08 | Sharding estimator review | review | 1 | 4 | Py | MLSYS READ TEST |
| LPL-09 | Two-tower logQ correction | experiment | 3 | 12 | Py | ML DATA |
| LPL-10 | Checkpoint cadence review | design | 5 | 10 | Py | SD DIST MLSYS |
| LPL-11 | ★ PowerSGD gradient compression | experiment | 3 | 14 | Py | DIST MLSYS PERF |
| LPL-12 | ★ Reproduce HSTU on ML-1M | experiment | 4 | 20 | Py | ML READ MLSYS |
| PLB-01 | Recall CI review | review | 1 | 4 | Py | TEST READ ML |
| PLB-02 | Filtered search plans | add-part | 2 | 12 | Rust | DB PERF SD |
| PLB-03 | Tombstones & compaction | build | 4 | 24 | Rust | DB OS DIST |
| PLB-04 | 1-bit codes + rescoring | perf | 3 | 18 | Rust | PERF DB ML |
| PLB-05 | Cold tier on object storage | build | 4 | 32 | Rust | DB DIST NET |
| PLB-06 | Embedding-upgrade incident | incident | 3 | 8 | Rust/Py | DEBUG DATA OBS |
| PLB-07 | Hybrid fusion vs RRF | experiment | 3 | 12 | Py/Rust | ML DATA TEST |
| PLB-08 | 1M tenants review | design | 5 | 10 | Py | SD DB COMM |
| PLB-09 | ★ Learned index for doc-ID lookup | perf | 3 | 16 | Rust | PERF DB ML |
| PLB-10 | ★ Trigram-index regex search (Russ Cox) | build | 4 | 26 | Rust | DB PERF READ |
| SLG-01 | PIT join review | review | 1 | 4 | Py/SQL | DATA DB TEST |
| SLG-02 | Skew detector | add-part | 2 | 10 | Py/SQL | DATA OBS DB |
| SLG-03 | Streaming windows = backfill | build | 4 | 30 | Go | DIST DATA PERF |
| SLG-04 | Silent AUC drop incident | incident | 3 | 8 | Py/SQL | DEBUG DATA OBS |
| SLG-05 | 5M-doc dedup | perf | 3 | 18 | Rust | PERF DATA OS |
| SLG-06 | Label-error audit | experiment | 3 | 14 | Py | ML DATA TEST |
| SLG-07 | PII scrubber | build | 3 | 16 | Py | DATA ML SEC |
| SLG-08 | Card-auth features review | design | 5 | 10 | Py | SD DB DIST |
| SLG-09 | ★ CUSUM drift detection (cross-domain) | experiment | 3 | 12 | Py | DATA OBS ML |
| SLG-10 | ★ Weak supervision (Snorkel) | build | 3 | 16 | Py | ML DATA API |
| BLJ-01 | exec timeout review | review | 1 | 5 | Go | OS READ TEST |
| BLJ-02 | cgroups/seccomp/egress | add-part | 2 | 12 | Go | OS SEC NET |
| BLJ-03 | Warm pools + snapshots | build | 4 | 30 | Go | OS PERF SD |
| BLJ-04 | OTel → ClickHouse ingest | build | 3 | 22 | Go/SQL | DB OBS API |
| BLJ-05 | Judge calibration | experiment | 3 | 14 | Py | ML TEST DATA |
| BLJ-06 | Eval runner with error bars | build | 4 | 26 | Py | TEST ML DIST |
| BLJ-07 | Double-refund incident | incident | 4 | 10 | Go | DIST DEBUG API |
| BLJ-08 | Sandbox fleet review | design | 5 | 10 | Py | SD SEC OS |
| BLJ-09 | ★ IRT tiny evals (cross-domain) | experiment | 4 | 18 | Py | ML TEST DATA |
| BLJ-10 | ★ Backoff + jitter + retry budgets (Brooker) | perf | 2 | 8 | Py/Go | DIST PERF API |
| MTH-01 | Preprocessing parity review | review | 1 | 5 | C++ | READ DEBUG TEST |
| MTH-02 | Blank-frame filter | experiment | 2 | 12 | Py | ML DATA TEST |
| MTH-03 | INT8 ≤ 1 mAP | perf | 3 | 16 | Py | PERF MLSYS ML |
| MTH-04 | Active learning loop | build | 3 | 18 | Py | ML DATA SD |
| MTH-05 | Night FP incident | incident | 3 | 9 | Py | DEBUG ML OBS |
| MTH-06 | OTA shadow/canary | build | 4 | 30 | Go/Py | SD DIST SEC |
| MTH-07 | On-device vs cloud review | design | 5 | 10 | Py | SD ML MLSYS |
| MTH-08 | mAP eval review | review | 2 | 5 | Py | ML TEST READ |
| MTH-09 | ★ Distill BioCLIP to device | experiment | 4 | 18 | Py | ML MLSYS DATA |
| MTH-10 | ★ Occupancy modeling (cross-domain) | build | 3 | 12 | Py | ML DATA API |

**Suggested "AI-infra internship" path** (one company per step, rising level):
KLN-01 → LPL-08 → KLN-02 → LPL-07 → KLN-05 → LPL-04 → CPL-04 → KLN-06 → LPL-06 → KLN-09.
This path follows what inference and training-infra postings ask for: vLLM/SGLang tuning,
KV cache, OOM debugging, profiling, Go gateways, fairness and SLOs.

**Overlap check against Luigi's existing and planned projects**
- No card builds an inference engine, a continuous-batching engine, an ANN graph index, an
  emulator, a game server, a RAG app or a compiler.
- Adjacent cards, each with a different deliverable:
  - KLN-04 is an eval gate, not a quant runtime.
  - KLN-06 is gateway admission, not a batching server.
  - PLB-02/03/04 extend an IVF-style index that teammates built.
  - PLB-07 is a fusion operator plus an eval kit.
  - SLG-06 is a data-quality tool.
  - BLJ-05 is judge calibration, not an agent.
  - KLN-11 is a KV-quantization reproduction plus a capacity model, not engine work.
  - LPL-12 reimplements one model block for a reproduction study.

---

## 4. Real OSS repos with workable issues

These feed the later "real upstream issue" task type. Counts and issue numbers come from the
GitHub API on **2026-10-19**. "GFI" = open issues labeled `good first issue` (excluding PRs);
"HW" = `help wanted`.

| Repo (lang) | Niche | Why it suits Luigi | Example open issues | Labels |
|---|---|---|---|---|
| [vllm-project/vllm](https://github.com/vllm-project/vllm) (Python/CUDA) | inference | Runs on his 4070; the most-hired-for codebase in inference job posts. Measurement issues fit his skills. | [#50128](https://github.com/vllm-project/vllm/issues/50128) measure Transformers-backend startup vs native (HW); [#41230](https://github.com/vllm-project/vllm/issues/41230) document NIXL KV-connector metrics (GFI); [#40004](https://github.com/vllm-project/vllm/issues/40004) priority preemption (HW, hard) | GFI 18, HW 28 |
| [sgl-project/sglang](https://github.com/sgl-project/sglang) (Python) | inference | Many starter issues, many about profiling and launch-time breakdowns | [#9674](https://github.com/sgl-project/sglang/issues/9674) benchmark/dataset scripts for embedding models; [#19087](https://github.com/sgl-project/sglang/issues/19087) launch-time breakdown; [#19612](https://github.com/sgl-project/sglang/issues/19612) unified JIT cache dir | GFI 46, HW 14 |
| [LMCache/LMCache](https://github.com/LMCache/LMCache) (Python) | KV-cache layer | Explicit onboarding: [#3372](https://github.com/LMCache/LMCache/issues/3372) first issues, [#5751](https://github.com/LMCache/LMCache/issues/5751) "good second issues" | [#5402](https://github.com/LMCache/LMCache/issues/5402) make flaky vllm_bench throughput comparisons reproducible (mirrors KLN-01) | GFI 9, HW 11 |
| [kubernetes-sigs/inference-perf](https://github.com/kubernetes-sigs/inference-perf) (Python) | LLM benchmarking | Small and young; load-generator work like KLN-01 | [#465](https://github.com/kubernetes-sigs/inference-perf/issues/465) random interval for session rate; [#838](https://github.com/kubernetes-sigs/inference-perf/issues/838) template endpoint; [#482](https://github.com/kubernetes-sigs/inference-perf/issues/482) custom datasets | GFI 2, HW 2 |
| [vllm-project/llm-compressor](https://github.com/vllm-project/llm-compressor) (Python) | quantization | Small refactors in a hot area | [#3300](https://github.com/vllm-project/llm-compressor/issues/3300) route basic calibration through the sequential pipeline; [#3161](https://github.com/vllm-project/llm-compressor/issues/3161) nested tensors → pytree | GFI 4 |
| [ai-dynamo/dynamo](https://github.com/ai-dynamo/dynamo) (Rust/Python) | distributed inference | API-correctness bugs, a good way into a Rust+Python serving stack | [#13342](https://github.com/ai-dynamo/dynamo/issues/13342) typed overload error instead of a 503 envelope; [#14069](https://github.com/ai-dynamo/dynamo/issues/14069) `/v1/responses` drops raw reasoning | GFI 7, HW 2 |
| [llm-d/llm-d-router](https://github.com/llm-d/llm-d-router) (Go) | routing | The real version of KLN-02 | [#1472](https://github.com/llm-d/llm-d-router/issues/1472) explicit backend selector field; [#1365](https://github.com/llm-d/llm-d-router/issues/1365) validate/document KV-cache-quantized serving | HW 5 |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) (C/C++) | edge inference | Huge user base; CPU/GPU on his box | [#17611](https://github.com/ggml-org/llama.cpp/issues/17611) wrong default threads in llama-bench; [#20632](https://github.com/ggml-org/llama.cpp/issues/20632) graceful reasoning-budget termination | GFI 17, HW 27 |
| [kubernetes-sigs/kueue](https://github.com/kubernetes-sigs/kueue) (Go) | GPU scheduling | Testable locally with kind; the real version of CPL-06 | [#3880](https://github.com/kubernetes-sigs/kueue/issues/3880) kueue-viz backend config params; [#5172](https://github.com/kubernetes-sigs/kueue/issues/5172) document two-step admission | GFI 3, HW 6 |
| [kai-scheduler/KAI-Scheduler](https://github.com/kai-scheduler/KAI-Scheduler) (Go) | GPU scheduling | Metrics issues are self-contained | [#2352](https://github.com/kai-scheduler/KAI-Scheduler/issues/2352) evicted-pod counters by action; [#901](https://github.com/kai-scheduler/KAI-Scheduler/issues/901) HPA for the admission service | GFI 3, HW 2 |
| [skypilot-org/skypilot](https://github.com/skypilot-org/skypilot) (Python) | GPU cloud orchestration | Python; real cloud/k8s bugs | [#9035](https://github.com/skypilot-org/skypilot/issues/9035) GPU prefix matching allows non-existent variants; [#8812](https://github.com/skypilot-org/skypilot/issues/8812) `.skyignore` negation | GFI 8 |
| [Project-HAMi/HAMi-core](https://github.com/Project-HAMi/HAMi-core) (C) | GPU sharing | The real version of CPL-04 | uses `good first issue` / `help wanted` labels (none sampled) | labels exist |
| [meta-pytorch/torchft](https://github.com/meta-pytorch/torchft) (Python/Rust) | fault-tolerant training | Small; ties to LPL-01/10 | [#36](https://github.com/meta-pytorch/torchft/issues/36) streaming checkpoint transfers; [#66](https://github.com/meta-pytorch/torchft/issues/66) bucketized averaging for LocalSGD | GFI 2 |
| [pytorch/ao](https://github.com/pytorch/ao) (Python) | quantization/training | Docs/CI starters, then kernels | [#3863](https://github.com/pytorch/ao/issues/3863) doc build warnings; [#2367](https://github.com/pytorch/ao/issues/2367) slow ROCm tests | GFI 5 |
| [lance-format/lance](https://github.com/lance-format/lance) (Rust) | columnar/vector storage | Lots of scoped Rust issues; good Rust practice | [#9113](https://github.com/lance-format/lance/issues/9113) preserve Retry-After on ThrottlingError; [#8244](https://github.com/lance-format/lance/issues/8244) LazyLock for Field/Schema; [#5069](https://github.com/lance-format/lance/issues/5069) inefficient `project_batch` | GFI 28, HW 13 |
| [lancedb/lancedb](https://github.com/lancedb/lancedb) (Rust/Py/TS) | vector DB | Its contributing guide points newcomers to GFI | [#3211](https://github.com/lancedb/lancedb/issues/3211) `col()` camelCase; [#2949](https://github.com/lancedb/lancedb/issues/2949) split `table.rs` | GFI 16, HW 7 |
| [milvus-io/milvus](https://github.com/milvus-io/milvus) (Go/C++) | vector DB | Many small correctness/UX issues | [#52049](https://github.com/milvus-io/milvus/issues/52049) REST returns wrong values for ints > 2^53; [#50965](https://github.com/milvus-io/milvus/issues/50965) field name/type in mismatch errors | GFI 28, HW 13 |
| [feast-dev/feast](https://github.com/feast-dev/feast) (Python/Go) | feature store | Mirrors Sluicegate; includes flaky tests | [#6417](https://github.com/feast-dev/feast/issues/6417) flaky CLI test; [#6429](https://github.com/feast-dev/feast/issues/6429) state APIs for all feature-view types | GFI 13 |
| [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) (Python) | evals | The canonical eval harness | [#2552](https://github.com/EleutherAI/lm-evaluation-harness/issues/2552) Hendrycks Math extraction too strict; [#1883](https://github.com/EleutherAI/lm-evaluation-harness/issues/1883) add regression testing | GFI 15, HW 14 |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) (Python) | evals/agents | Fresh, precise bug reports (Oct 2026) | [#5815](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5815) usage drops reasoning_tokens; [#5711](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5711) loaders silently change answer labels; [#5712](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5712) timezone shift on import | GFI 7 |
| [pytorch/executorch](https://github.com/pytorch/executorch) (C++/Python) | on-device | Edge runtime; some issues need specific hardware, so filter | [#21943](https://github.com/pytorch/executorch/issues/21943) ops not lowered to Cortex-M kernels; [#12812](https://github.com/pytorch/executorch/issues/12812) run the size-test binary in CI | GFI 27 |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) (Python/TS) | LLM observability | Has a "good student issue" label | [#9294](https://github.com/Arize-ai/phoenix/issues/9294) export experiments | HW 2 |

Also checked, with beginner labels but no open issues sampled today: vllm-project/guidellm,
kubernetes-sigs/gateway-api-inference-extension, pytorch/torchtitan,
NVIDIA/nvidia-resiliency-ext, huggingface/datatrove, ultralytics/ultralytics,
data-privacy-stack/presidio, meta-pytorch/torchrec. mlflow/mlflow has 72 `help wanted`
issues, mostly feature requests.

**How the harness should use these**
1. Pick an issue that is unassigned and has no linked PR; re-check on the day.
2. Reproduce locally and write the failing test first.
3. An AI teammate reviews the PR as a maintainer would.
4. **Luigi submits it himself.** Nothing is posted upstream automatically.
5. Check contribution rules first (memory, verify per repo): vLLM requires DCO sign-off;
   Kubernetes SIGs need the CNCF CLA; PyTorch-org repos need the Meta CLA.
6. Grade on: the repro test fails before the fix and passes after, plus a maintainer-style
   review rubric. Merging is a bonus, not the done-condition.

---

## 5. Builder notes for the harness

- **Calibration rule:** run the baseline and the reference solution 3× on Luigi's machine,
  then set each threshold relative to those results. Re-calibrate after driver or library
  upgrades.
- **Shared assets to pre-fetch** (check licenses):
  - traces: Philly, Alibaba PAI v2020/v2023
  - datasets:
    - LILA BC subsets
    - CIFAR-10N
    - ai4privacy 400k
    - BEIR SciFact/FiQA/NFCorpus
    - a 1M-vector OpenAI-embedding DBpedia set
    - MT-Bench human judgments
    - Criteo display-ads subset
    - MovieLens-25M
    - a FineWeb sample
  - models: Qwen2.5 0.5B/1.5B/3B (BF16), a 7–8B AWQ/GPTQ instruct model, a small YOLO-class
    detector
- **docker-compose kit:** vLLM, Prometheus, Grafana, ClickHouse, MinIO, toxiproxy, Redpanda,
  Redis, Label Studio, a kind cluster with a fake GPU device plugin.
- **Environment risks on his machine** (all unverified, check before assigning):
  - `/dev/kvm` in WSL2 for Firecracker (BLJ-03); CRIU in WSL2.
  - cgroup v2 in WSL2 (`stat -fc %T /sys/fs/cgroup` should print `cgroup2fs`; BLJ-02).
  - `LD_PRELOAD` interposition with WSL's `/usr/lib/wsl/lib/libcuda.so` (CPL-04).
  - TensorRT under WSL2 (MTH-03).
  - NCCL can't put two ranks on one GPU, so distributed cards use gloo CPU ranks and
    pre-recorded NCCL/Flight Recorder dumps (LPL-02/03). Flight Recorder's gloo support is
    unverified.
  - FP8 W8A8 on Ada (sm_89): expected to work in vLLM (KLN-04), but verify.
- **Generic planted-bug patterns** that recur across this domain and make good review-to-own
  material:
  - closed-loop timing; percentiles of percentiles; dropped failures in stats
  - stale or aggregate counters in health checks
  - event time vs. processing time
  - `<=` vs. `<` leakage
  - random splits that leak sequences, users or locations
  - missing stream synchronization before reading GPU tensors
  - non-atomic publish (metadata before fsync)
  - process-group kills
  - per-line-item rounding
  - at-least-once inserts without dedup
  - tolerance/units mismatches (°C vs. m°C, $ vs. ¢)

## 6. Things I could not verify (keep marked in the product)
- Character.AI's numbers (95% cache hit rate, 33× cost reduction): secondary summaries only;
  the original post's URL now redirects.
- SGLang's "3× throughput vs. round-robin" for llm-d prefix routing: one page.
- E2B's job details (200 ms start target, Firecracker authors on staff, Nomad/Terraform):
  job-board mirrors, not E2B's careers page.
- Langfuse being part of ClickHouse: inferred from ClickHouse job postings.
- GuideLLM v0.8.0's release date and features: a community post.
- The Pinterest throughput figures: a secondary summary with inconsistent numbers.
- turbopuffer's implementation language, and Qdrant's multitenancy specifics: not
  re-checked.
- The FineWeb dedup threshold (~75%) and the datatrove "3 h 50 min" report: secondary or a
  single user.
- Paper-card details from memory:
  - the Tail-at-Scale BigTable example (1,800 → 74 ms with ~2% more requests); the ~5%
    load and 16%/40% tied-request figures are verified via a summary
  - the PowerSGD DDP-hook module path
  - the generative-recommenders repo name
  - Page (1954) bibliographic details
  - the swtch.com URL for Russ Cox's post
  - The tinyBenchmarks "≤ 2.5 pt MAE" bar is my threshold, not a quoted paper number; the
    abstract only says 100 curated items suffice.
- URLs marked (memory): cited from prior knowledge without re-fetching. They are stable
  canonical pages (Rules of ML, Feast, Stripe and Firecracker were re-fetched and confirmed).
