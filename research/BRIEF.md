# Offer Letter — research brief (shared by every research agent)

## What Offer Letter is

A local web app that simulates a software job so one learner (Luigi, US
undergrad, strong in Python, aiming at AI/ML infrastructure and backend
roles) becomes job-ready by building. He picks a fictional company from a
catalog, is onboarded, joins a team of AI teammates (manager, tech lead,
peers, PM, a junior), and works tickets in his own editor with real git.
Task types:

- **review-to-own** — an AI teammate's pull request (with deliberately
  planted bugs) → he reviews it, is quizzed (answers verified by running
  code), explains it by voice, makes an unaided change → then he owns it.
- **add-your-part** — teammates have built parts of a codebase with
  written decision notes; he builds his part; they review and push back.
- **build** — a whole project: design doc → review → milestones → demo.
- **perf-hunt** — make something measurably faster/cheaper; graded by a
  benchmark the harness runs.
- **incident** — a service he runs locally breaks; logs/metrics →
  fix → postmortem.
- **design-review** — system design on a whiteboard with a senior teammate.
- **experiment** — ML/data work graded by a metric on a held-out set.

Companies are FICTIONAL but research-built: their niches, problems,
stacks, and in-house tools come from what real companies actually build,
hire for, and write about. Never use a real company's name or branding for
a fictional company. Real names appear only in the "inspired by" notes.

## Learner's machine (projects must run here, no paid cloud)

Ryzen 9 5900X (12 cores / 24 threads), 32 GB RAM, NVIDIA RTX 4070
(12 GB VRAM), Windows 11 + WSL2 Ubuntu, Docker Desktop, 173 GB free.
Python/uv, Go, Rust/cargo, Node, gcc/clang available. GPU work must fit
12 GB (e.g. ≤ 8B models at 4-bit, small CV/recsys training runs).

## Hard rules for project ideas

1. **Unique, grounded in a real need.** Each project cites at least one
   real source (engineering blog, postmortem, OSS issue/PR, paper, job
   posting) showing a real company needed this. No tutorial clones
   ("build Redis/Git/SQLite/an HTTP server from scratch", CodeCrafters
   lists, todo apps).
   **Research papers and blogs from ANY domain are valid sources too**
   (learner's request): a systems/DB/ML paper turned into "our team wants
   to try the technique from this paper in production", or a cross-domain
   idea (biology, finance, robotics, physics, logistics…) a company in
   this catalog would plausibly adopt. Aim for at least 2 paper-inspired
   or blog-inspired projects per company (arXiv, VLDB/SIGMOD/OSDI/SOSP/
   NSDI/MLSys/NeurIPS papers, personal engineering blogs), saying what the
   paper claims and what the ticket asks him to reproduce or apply.
2. **No repeats of the learner's existing projects.** He already has:
   a multiplayer game server with netcode, a Rust CPU LLM inference
   engine, CHIP-8 and 6502 emulators, a C++ Vulkan game engine, an HNSW
   vector index, xv6 OS labs, a RAG app over city guides, a 3-tool agent
   with MCP, a fine-tuned comment classifier, a journal CLI, a
   reverse-engineering lab app, an ML/GPU compiler. Adjacent work in the
   same area is fine only if the deliverable is different (e.g. "add
   filtered search + tombstone compaction to our ANN service" is fine;
   "build an HNSW index" is not).
3. **Objectively gradable.** Every project has a done-condition the
   harness can check by running something: tests pass, a benchmark
   reaches a threshold (p99 latency, throughput, memory), a metric on a
   held-out set, a fault-injection scenario survives, a planted bug found.
4. **Sized in work blocks.** He works in 30–90 min sessions (sometimes
   hours). Give total hours and how it splits into blocks / milestones.
5. **Any language the work demands.** Python is a given; otherwise pick
   what that kind of company really uses (Go, Rust, C++, CUDA, TypeScript,
   SQL, Java/Kotlin…) — say why.

## Provisional skill tags (use these; the hiring agent refines them)

SD system design · PERF performance & profiling · DB databases & storage
internals · OS operating systems, concurrency, memory · NET networking ·
DIST distributed systems & consistency · MLSYS ML systems (serving, GPU,
kernels, training infra) · ML modelling/training/eval · DATA data
pipelines & quality · OBS observability, reliability, SRE · SEC security ·
API API & interface design · TEST testing & quality · READ reading
unfamiliar code · DEBUG debugging · COMM design docs, review, discussion.

## Project card template

```
### <ID> <Title>
- Company: <fictional company>   Type: <task type>   Level: L1–L5
- Real-world grounding: <the real need, 1–2 lines> — <source URLs>
- Ticket (as the PM / tech lead would write it): <3–6 lines>
- Stack: <languages/libs> — why
- Skills: <tags, primary first>
- Size: <total hours> → <blocks/milestones>
- What teammates already built / what the AI writes vs. what HE writes
- Done-condition (harness-checkable): <exact check + threshold>
- Planted-bug ideas (review-to-own) or pushback hooks (decisions a
  teammate made that he should question)
- Ownership change request (small unaided follow-up)
```

## Fictional company card template

```
## <Name> — <one-line pitch>
- Niche / domain:          - Stage: seed | growth | big-tech division | OSS foundation
- Culture (sets how the boss, reviews, deadlines feel):
- Stack (and why, from real companies in this niche):
- Team roster (roles only):
- Main codebase sketch (the repo(s) the harness would generate):
- In-house tools this company would build (each a possible project):
- Inspired by (real companies + sources, for the builders only):
- Projects: 6–10 cards spread across task types and levels L1–L5
```

## Output rules

**Write early and progressively** (the session can hit a usage limit
mid-run): create your file with the full outline after your first ~10
tool calls, then rewrite/extend it after each section is done, so an
interruption loses at most one section. Mark unfinished sections
`<!-- TODO -->`.

Write your file in this folder (`C:\Users\Owner\projects\offer-letter\research\`),
in Markdown, sources as inline links. Prefer 2025–2026 sources. Mark
anything you could not verify. Your final chat reply should be ≤ 200
words: the file path + the 5 most important findings — the file holds the
detail.
