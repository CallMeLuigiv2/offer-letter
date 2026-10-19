# 04 — Workplace realism: how real engineering orgs work, and how Offer Letter simulates it

Research agent: workplace-realism. 2026-10-19. Sources inline.
Unverified items are marked **unverified** / **secondary**. All six
sections complete.

## Key findings (read this first)

1. **Every ritual should leave a written artifact, and grading reads the
   artifact.** Real orgs already work this way (GitLab: write down the
   conclusions of offline talks; Apache: "off-list discourse and
   transactions must be brought on-list"; Google SRE: "An unreviewed postmortem might as well never have
   existed"). That makes communication gradable from observable
   behaviours, not vibes (§1, §5).
2. **Teammates must not be sycophants.** RLHF assistants tend to agree
   with the user (Sharma et al.); Rehearsal (CHI 2024) only let simulated
   counterparts agree after real interest-based moves, and trainees cut
   escalating tactics by 67%. Encode a **concession policy** (concede to
   evidence/constraints/better alternatives, never to repetition) and
   plant ~1 in 4 *wrong* pushbacks he should catch (§2.3).
3. **Onboarding strategy is a culture dial with research behind it.**
   Microsoft's study found three manager strategies: Simple-Complex
   (best for juniors), Priority-First (teams under pressure; scary
   early), Exploration-Based (seniors/new teams; juniors stalled). Map
   them to growth/big-tech, seed and OSS respectively, and start him in
   growth culture (§1.1, §3).
4. **"Firm but fair" has a clean real-world form:** deadlines in the
   culture's own mechanism (founder date / sprint / release train /
   release freeze), a miss surfaced **once** in standup and **once** in
   the review artifact, PTO declared in advance, informational not
   controlling wording (autonomy-supportive language raised autonomous
   motivation, d = 0.63), nothing on weekends (§1.0, §3.5, §6 #8).
5. **Avoid gamification and add debriefs.** Badges/leaderboards lowered
   motivation and exam scores (Hanus & Fox); expected rewards undermine
   intrinsic motivation (Deci et al.); feedback is "the single most
   important feature" of simulation learning (BEME), but feedback aimed
   at the self hurts performance in ~⅓ of cases (Kluger & DeNisi). So:
   no XP, in-world rewards only, an after-action review per artifact
   about the work, not the person (§6).

Contents
1. Org rituals → harness mechanics
2. Team roster and persona archetypes
3. Culture profiles (seed / growth / big-tech division / OSS foundation)
4. Templates the harness can ship
5. Communication skills a senior shows (gradable behaviours)
6. Pitfalls of workplace simulations and serious games

---

## 1. Org rituals → harness mechanics

### 1.0 Ground rules that apply to every ritual

- **The sim calendar is his real calendar.** Main days Mon/Wed/Fri, short days
  Tue/Thu, weekends never exist in the sim (no ritual, deadline, page or
  message lands on Sat/Sun; due dates skip them). One sprint = 2 real weeks =
  6 main + 4 short days. Real companies handle absence with PTO, so give him
  PTO: he can mark a day off **in advance** (like a real job) and deadlines
  shift; an *undeclared* missed day is what counts as a miss. This keeps
  "firm but fair" honest: the rule is the same one a real manager applies.
- **Every ritual produces an artifact** (a written update, a PR, a doc, a
  postmortem, a 1:1 note). Grading reads the artifact, not a vibe. Real orgs
  work this way too: GitLab asks that "conclusions of offline conversations
  are written down" ([GitLab communication handbook](https://handbook.gitlab.com/handbook/communication/));
  Apache requires "off-list discourse and transactions must be brought
  on-list" ([The Apache Way](https://www.apache.org/theapacheway/)).
- **Grade observable behaviours, not personality.** Each rubric line below is
  something a grader (harness check, or LLM judge with a fixed rubric and
  quoted evidence) can point at in the artifact.
- **Ritual time budget.** Rituals must not eat the build time. Target: ≤ 10%
  of a main day, ≤ 5 min on a short day. Real teams cap rituals hard
  (Scrum: Daily Scrum is 15 min; planning ≤ 8 h per *month* of sprint,
  retro ≤ 3 h per month — [Scrum Guide 2020](https://scrumguides.org/scrum-guide.html));
  scale those down proportionally to his ~1–3 h days.

### 1.1 Onboarding week

**How real companies run it.**
- GitLab: "We don't expect you to hit the ground running from day one"; two
  full weeks of onboarding before team-specific work; everything tracked in
  an onboarding *issue* with a 30-day due date; an onboarding buddy; a
  pre-start AMA call; default Slack channels to say hi and ask questions
  ([GitLab general onboarding](https://handbook.gitlab.com/handbook/people-group/general-onboarding/)).
- Meta's bootcamp (historical, ~6 weeks; now reportedly ~2–4 weeks with
  team matching before offer — **partly unverified**, community sources):
  ship a trivial change on **day one** to learn the IDE → review → CI →
  deploy path; a shared backlog of starter tasks graded L1–L5, written by
  real teams; 1 mentor per 2–3 campers
  ([dev.to account](https://dev.to/automationhacks/engineering-practices-meta-3-conduct-an-engineering-bootcamp-for-new-joiners-591e)).
- Research (Microsoft, 32 devs + 15 managers interviewed, surveys N=189/37):
  managers onboard with one of three strategies — **Simple-Complex**
  (gradually harder tasks; "a good strategy for onboarding junior
  developers"), **Priority-First** (take the top of the backlog; teams under
  pressure; early hard tasks "could spur fears and low confidence"), and
  **Exploration-Based** (loosely defined spikes; better for experienced
  hires; two juniors given spikes had *not delivered* and felt pressure).
  Mentors/"onboarding buddies" were the first contact; 14 of 18 with one
  found them helpful; an important mentor job is "to reduce barriers for
  help-seeking" ([Ju et al., ICSE 2021](https://arxiv.org/abs/2103.05055)).
- Remote onboarding (267 Microsoft hires, 2020): the biggest problem was
  forming a social bond with the team; recommendations include multiple
  onboarding speeds, docs that describe how things *actually* work, and a
  follow-up check-in months later ([Rodeghero et al., ICSE SEIP 2021](https://arxiv.org/abs/2011.08130);
  [summary](https://neverworkintheory.org/2022/03/28/remote-onboarding.html)).

**By culture.** Seed: Priority-First, a README and a Loom video, "ask in
#eng". Growth: a checklist + buddy, first PR in week 1, on-call shadow in
month 2. Big-tech division: Simple-Complex, formal multi-week program,
lots of internal tooling to learn, readability/ownership gates. OSS:
self-serve CONTRIBUTING.md, "good first issue" labels, no one assigned to
you; you earn attention by showing up.

**Offer Letter mechanic: "Week 0" (one sprint-week, 3 main + 2 short days).**
- Day 1 (main): offer-letter scene → manager welcome call (visual-novel) →
  onboarding *issue* on the task board (checklist in §4.8) → environment
  setup script he runs → **day-one PR**: a trivial, real change (fix a typo
  in a runbook, add a test case) that walks the full path: branch → PR
  description → review by the buddy → CI → merge. (Meta's day-one change.)
- Day 2 (short): read 2 teammate decision notes; post one question in
  #team that follows the "good question" pattern (§5.1).
- Day 3 (main): first real starter ticket (L1, Simple-Complex), paired
  voice session with the buddy.
- Day 4 (short): coffee-chat scene with one non-manager teammate (social
  bond is the #1 remote-onboarding gap per Rodeghero).
- Day 5 (main): finish starter ticket; first async standup; 30/60/90
  conversation with manager.
- **Culture changes the strategy:** seed = Priority-First (a real bug on
  day 2, warned it's "trial by fire"); growth/big-tech = Simple-Complex;
  OSS = Exploration-Based with a mentor label.
- **Graded:** day-one PR merged with a description that passes the PR rubric
  (§4.4); onboarding checklist complete by its due date; ≥ 1 well-formed
  question asked (not graded on *whether* he knew, graded on the form);
  setup problems reported with exact error + what he tried.

### 1.2 Daily standup

**How real teams run it.** Purpose: "Share understanding of goals",
"Coordinate efforts", "Share problems", "Identify as a team"; the three
questions *or* **walk the board** (work items, from nearest-done to
newest, instead of people); "Fifteen Minutes or Less"; "Take It Offline"
for problem-solving; anti-pattern "Reporting to the Leader" — talking to
the manager instead of the team ([Yip, "It's Not Just Standing Up", martinfowler.com](https://martinfowler.com/articles/itsNotJustStandingUp.html)).
Scrum: the Daily Scrum belongs to the developers, who pick the format;
output is a plan for the next day ([Scrum Guide 2020](https://scrumguides.org/scrum-guide.html)).
Remote companies often run it async in a channel (GitLab: async "as a
starting point" — [handbook](https://handbook.gitlab.com/handbook/communication/)).

**By culture.** Seed: no standup or a 5-min huddle; founder asks "what
shipped?". Growth: async bot thread daily + one sync per week. Big-tech:
sync 15 min, walk the board, often a TPM/EM running it. OSS: no standup;
weekly WG/SIG meeting with public notes (Kubernetes SIGs must keep
meeting notes and recordings public — [SIG governance](https://git.k8s.io/community/committee-steering/governance/sig-governance.md)).

**Offer Letter mechanic.**
- Short days: async written standup in #standup (3 fields: done / next /
  blocked-with-ask). Main days: a 2-minute voice standup scene where the
  tech lead **walks the board** and teammates give one-line headlines;
  he gives his.
- **Deadline enforcement lives here** (the brief's "misses show up in
  standup"): the board shows his ticket as late; the tech lead says it
  once, plainly, in front of the team ("PAY-112 was due Monday — what's the
  new date and what changed?"). No follow-up nagging; the next mention is
  in the perf review.
- Teammates' headlines carry information he needs (a dependency slipping,
  an API changed) — standup is a source of plot, not filler.
- **Graded (per update, cheap rubric):** says *outcome* not activity
  ("PR #41 merged; p99 now 38 ms" vs "worked on perf"); a blocker names who
  can unblock and what is needed; a slipping item gives a new date + the
  reason *before* it is late (counts as "early warning", heavily
  weighted); ≤ 60 words; does not problem-solve in standup.

### 1.3 Sprint planning

**How real teams run it.** Scrum Sprint Planning answers *why* (the Sprint
Goal), *what* (items selected with the Product Owner) and *how* (developers
decide); scope can be renegotiated mid-sprint without changing the goal
([Scrum Guide 2020](https://scrumguides.org/scrum-guide.html)). Basecamp's
Shape Up rejects backlogs and sprints: six-week cycles, shaped work, a
**betting table**, a two-week cool-down, and a **circuit breaker** — "If a
project runs over, by default it doesn't get an extension"
([Shape Up](https://basecamp.com/shapeup/0.3-chapter-01)). Big orgs layer
quarterly planning on top to line up cross-team dependencies
([Pragmatic Engineer, startup vs Big Tech](https://blog.pragmaticengineer.com/working-at-a-startup-vs-in-big-tech/)).

**By culture.** Seed: weekly "what are we shipping" + founder priorities
that change. Growth: 2-week sprints, a PM-owned board, OKRs per quarter.
Big-tech: quarterly OKR/roadmap planning, sprint planning inside it,
dependency negotiation with other teams. OSS: release milestones and
whoever volunteers; nothing is "assigned".

**Offer Letter mechanic.** First main day of each sprint, ≤ 15 min.
The PM proposes a sprint goal + candidate tickets; the tech lead flags
risk; **he commits** to a set of his own tickets with dates. The harness
knows his calendar capacity (≈ 6 main × ~1.5 h + 4 short × ~0.5 h ≈ 11 h /
sprint, tune per learner) and the AI PM will *over-ask* on purpose
~1 in 3 sprints to test "saying no" (§5.5).
- **Graded:** total committed estimate ≤ his capacity (harness math);
  each commitment has an acceptance check he can name; if he declines or
  defers a ticket he gives a reason and an alternative; at sprint end,
  **commitment reliability** = done-on-time ÷ committed (tracked, feeds
  perf review; target ≥ 80% — a realistic bar, not 100%).

### 1.4 Estimation

**How real teams do it.** Planning poker / story points are common, and
also widely criticised: Ron Jeffries, who may have coined story points,
writes "I may have invented story points, and if I did, I'm sorry now",
because they get used to predict dates, compare teams and apply pressure;
he recommends slicing work to ≤ 1 day ("until they just need a single
acceptance test") and delivering thin slices
([Jeffries, "Story Points Revisited"](https://ronjeffries.com/articles/019-01ff/story-points/Index.html)).
Shape Up replaces estimates with **appetite** — "the amount of time we want
to spend on a project, as opposed to an estimate"
([Shape Up](https://basecamp.com/shapeup/0.3-chapter-01)).

**Offer Letter mechanic.** Estimate in **his own work blocks** (30/60/90-min
blocks — the unit the brief already uses), never in points. Every ticket
he takes gets a block estimate *before* work starts; the harness logs
actual blocks (session timer).
- **Graded:** calibration over time, not single accuracy: the harness
  shows a running ratio actual/estimate and the perf review comments on
  the *trend*. Also graded: splitting — a ticket estimated > 4 blocks must
  be split into slices each with its own check (Jeffries' rule).
- Culture variant: Shape-Up-style growth company uses appetite ("this is
  worth 6 blocks, not more — what's the smallest version?") with a circuit
  breaker; big-tech uses T-shirt sizes in quarterly planning.

### 1.5 Code review (his PRs and teammates' PRs)

**How real orgs run it.**
- Google's standard: approve once a change "definitely improves the overall
  code health"; "there is no such thing as 'perfect' code"; label
  non-blocking comments "Nit:", "Optional:", "FYI"; comment on the code
  not the person; explain why; disagreements go author ↔ reviewer → call
  → TL/EM, and "Don't let a CL sit around"
  ([standard](https://google.github.io/eng-practices/review/reviewer/standard.html),
  [comments](https://google.github.io/eng-practices/review/reviewer/comments.html)).
  Speed: "One business day is the maximum time it should take to respond";
  LGTM-with-comments across time zones
  ([speed](https://google.github.io/eng-practices/review/reviewer/speed.html)).
- At Google every change needs a peer LGTM, an OWNERS approval and a
  readability approval (one person can cover several); keep changes to
  ~200 lines; "the most important LGTM is the first one"
  ([Software Engineering at Google, ch. 9](https://abseil.io/resources/swe-book/html/ch09.html)).
  Google's log study (9M changes) reports median < 4 h to approval
  ([Sadowski et al. 2018](https://research.google/pubs/modern-code-review-a-case-study-at-google/);
  the < 4 h figure is via a [citing paper](https://arxiv.org/pdf/2507.09637) — **verify in original**).
- Microsoft's study: review finds fewer defects than people expect; its
  main outcomes are **knowledge transfer, team awareness, alternative
  solutions**, and *understanding the change* is the central difficulty
  ([Bacchelli & Bird, ICSE 2013](https://2013.icse-conferences.org/content/expectations-outcomes-and-challenges-modern-code-review.html)).
- "Pushback" (negative interpersonal review experiences) is rare but
  costly ([Egelman et al., ICSE 2020](https://research.google/pubs/predicting-developers-negative-feelings-about-code-review/));
  the amount received varies with author gender, race/ethnicity and age
  ([Murphy-Hill et al., CACM 2022](https://research.google/pubs/the-pushback-effects-of-race-ethnicity-gender-and-age-in-code-review/)).
- OSS (LLVM): anyone may review; every patch needs one expert; authors
  "must acknowledge" every comment; courtesy ping after **one week**;
  post-commit review is real and can mean a revert
  ([LLVM code review policy](https://llvm.org/docs/CodeReview.html)).
  Apache: a −1 on code is a veto that needs a technical justification
  ([ASF voting](https://www.apache.org/foundation/voting.html)).

**By culture.** Seed: one quick approval, "ship it", review = sanity check,
nits skipped. Growth: CODEOWNERS, CI gates, one approval, some nits,
review SLA in a team agreement. Big-tech: multiple approvals
(owner/readability-like), strict style, small CLs, lots of nits labelled
as nits. OSS: slow, async, maintainers are volunteers, you ping politely,
reviews can be blunt and public.

**Offer Letter mechanic.**
- *His PRs:* reviewed by 1–2 AI teammates within **one sim business day**
  (Google's SLA; on a short day he may get the review next main day).
  Comments use Conventional Comments labels (§4.5) so blocking vs nit is
  explicit. At least one comment per PR is a **real** question about a
  decision (not a nit), so he must defend or change it.
- *Teammates' PRs (review-to-own):* he gets review requests with the same
  one-business-day SLA. Planted bugs are found by the harness check; the
  *review comments themselves* are graded too.
- **Graded (author side):** PR description rubric (§4.4); every comment
  acknowledged (LLVM rule) — resolved, answered, or explicitly deferred
  with a follow-up ticket; PR size (flag > ~400 changed lines without a
  reason); response time ≤ 1 sim business day.
- **Graded (reviewer side):** planted bug found (harness); comment labels
  correct (a correctness bug marked blocking, a style point marked nit);
  each blocking comment states *why* and a suggested direction; no comment
  about the person; approves when code health improves rather than
  holding out for perfect (Google's standard) — the harness plants some
  PRs that are *fine* and grades whether he approves them without
  inventing problems.

### 1.6 Design doc / RFC review

**How real orgs run it.**
- Google design docs: context & scope, goals & **non-goals**, the design
  (trade-offs, system-context diagram, APIs, storage), **alternatives
  considered** ("one of the most important" sections), cross-cutting
  concerns; 10–20 pages for big projects, 1–3 page "mini design docs" for
  incremental work; review ranges from comment threads to a formal meeting;
  don't write one when the solution isn't ambiguous
  ([Ubl, Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/)).
  Google later automated parts of design review and cut median
  time-to-approval 25% over 141k docs
  ([ASE 2023 industry paper](https://www.se.cs.uni-saarland.de/conferences/ASE/ase2023/details/ase-2023/ase-2023-industry-showcase-papers/1/Dramatically-Improving-Design-Reviews-at-Google.html)).
- Rust RFCs: pre-RFC discussion first; PR to the RFC repo; revisions as
  new commits with a comment explaining changes; **Final Comment Period**
  of 10 calendar days with a disposition (merge/close/postpone) that all
  sub-team members sign off; acceptance ≠ commitment to implement
  ([rust-lang/rfcs README](https://github.com/rust-lang/rfcs/blob/master/README.md),
  [template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)).
- Oxide RFDs: states prediscussion → ideation → discussion (a PR) →
  published → committed / abandoned; "timely rather than polished"; a
  3–5 business-day comment window; don't merge if no one has read it
  ([RFD 1](https://rfd.shared.oxide.computer/rfd/0001)).
- HashiCorp RFC: Overview, Background (a newcomer must get full context
  from it), Proposal, **Abandoned Ideas** (kept, not deleted); status
  WIP/In-Review/Approved/Obsolete; owner, contributors, approvers; an RFC
  is for solutions, a PRD for problems
  ([HashiCorp RFC template](https://www.hashicorp.com/en/how-hashicorp-works/articles/rfc-template)).
- Uber's RFC template (to ~2019) for services: approvers, SLAs,
  dependencies, load testing, multi-DC, security, rollout, monitoring;
  Amazon uses PR/FAQ for products and narrative memos read silently in
  the meeting ([Pragmatic Engineer RFC roundup](https://blog.pragmaticengineer.com/rfcs-and-design-docs/);
  [CNBC on the 6-pager](https://www.cnbc.com/2018/04/23/what-jeff-bezos-learned-from-requiring-6-page-memos-at-amazon.html)).
- Kubernetes KEPs add a release sign-off checklist and a **Production
  Readiness Review** questionnaire (rollout/rollback, monitoring,
  scalability, troubleshooting)
  ([KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md)).

**Offer Letter mechanic (build + design-review tasks).**
- He writes a mini design doc (template §4.1) **before** milestone 1 code
  is accepted (the harness refuses to start milestone review until the doc
  is "Approved"). Lifecycle mirrors Oxide/HashiCorp: Draft → In Review →
  Approved → (later) Implemented/Obsolete.
- Review is **async comment threads** by 2–3 teammates over 2 sim days
  (≈ Oxide's window, scaled), then a 10-min synchronous design-review
  scene with the senior/TL for unresolved threads (the whiteboard for the
  design-review task type).
- Each reviewer persona has a *lens* (TL: failure modes/rollout; senior:
  alternatives/simplicity; PM: does it meet the user need/non-goals;
  peer: API ergonomics) — mirrors cross-cutting review in real orgs.
- OSS culture variant: RFC as a PR with an FCP banner ("FCP: merge, ends
  in 3 days") — silence = consent (Apache lazy consensus,
  [72 h](https://community.apache.org/committers/lazyConsensus.html)).
- **Graded:** has non-goals; ≥ 2 real alternatives with a reason each was
  rejected; states how success is measured (ties to the harness
  done-condition); has a rollout/rollback line; every thread closed with
  a decision ("changed X" / "kept, because…"); **revision note** listing
  what changed after review (Rust rule); doc length within appetite
  (a 1–3 page mini doc for a ≤ 20 h project).

### 1.7 Incident + postmortem

**How real orgs run it.**
- Roles: Incident Commander ("the Incident Commander is NOT a resolver"),
  Deputy, Scribe, SMEs, Customer and Internal Liaisons; internal status
  roughly every 30 min; "If in doubt, post it out"
  ([PagerDuty roles](https://response.pagerduty.com/before/different_roles/),
  [during an incident](https://response.pagerduty.com/during/during_an_incident/)).
- Severity SEV-1…SEV-5; "if unsure, treat it as the higher one"; tie
  severities to metrics like % of users affected
  ([PagerDuty severity levels](https://response.pagerduty.com/before/severity_levels/)).
- Google SRE postmortems: triggers defined in advance (user-visible
  downtime, data loss, on-call intervention, long resolution, monitoring
  failure); blameless — "You can't 'fix' people, but you can fix systems
  and processes"; "An unreviewed postmortem might as well never have
  existed"; Wheel of Misfortune role-play for training
  ([postmortem culture](https://sre.google/sre-book/postmortem-culture/));
  template: Summary, Impact, Root Causes, Trigger, Resolution, Detection,
  Action Items (Owner, Bug), Lessons Learned (went well / went wrong /
  **where we got lucky**), Timeline
  ([example postmortem](https://sre.google/sre-book/example-postmortem/)).
- A strong recent public example: Cloudflare, 18 Nov 2025 — a database
  permissions change made a query emit duplicate rows into a Bot
  Management feature file, which doubled past a hard size limit in the
  proxy; they first suspected a DDoS
  ([Cloudflare postmortem](https://blog.cloudflare.com/18-november-2025-outage/)).
  Good teaching shape: config/data change, not code; misleading first
  hypothesis; a limit nobody remembered.

**By culture.** Seed: whoever is awake fixes it; no IC; a Slack-thread
postmortem if any. Growth: PagerDuty-style roles, SEV levels, a template,
action items tracked. Big-tech: formal IC training, postmortem review
meetings, action items with owners and due dates, error budgets. OSS: a
security advisory or a GitHub issue; postmortem is a public blog post.

**Offer Letter mechanic (incident task type).**
- Incidents fire only on **main days**, never in the first 15 min of a
  session (let him start), and are announced by a page in the app.
- He is first **SME** (the fixer) with an AI IC for his first incidents,
  then later becomes **IC** while an AI SME fixes (trains the
  communication half: delegating, status updates, deciding under
  uncertainty).
- During: he must post a status update in #incident at a cadence
  (sim-time: every ~10 real minutes while it's open — scaled from 30
  min), declare a severity, and say what he's trying next.
- After: postmortem (template §4.3) due in 2 sim workdays; reviewed by
  the TL in a short scene (Google: unreviewed postmortem = didn't happen).
- **Graded:** service restored (harness check) and time-to-mitigate;
  severity chosen matches the SEV table; status updates on cadence, each
  with impact + next step + next-update time; postmortem is **blameless**
  (no "X should have"; names systems and conditions); root cause is
  deeper than the trigger (asks "why did the safeguard not catch it?");
  ≥ 1 action item that prevents the *class* of failure, each with an
  owner and a ticket; "where we got lucky" filled honestly.

### 1.8 On-call handoff

**How real orgs run it.** Google SRE workbook: "At the start of each
shift, the on-call engineer reads the handoff from the previous shift";
at the end they send one; teammates follow up when handoffs miss the
standard; target ≤ 2 incidents per 12-h shift; playbooks for each alert;
new on-callers shadow, run Wheel of Misfortune drills, and use a
checklist (roll back a push, drain traffic); out-of-hours on-call is
compensated ([SRE workbook, On-Call](https://sre.google/workbook/on-call/)).

**Offer Letter mechanic.** From his second company sprint onward, he
holds a 1-sprint "on-call" for a service he owns. Monday (main) he
**reads** the AI's handoff note (which contains one detail that matters
later — an alert that's flapping, a risky deploy). At sprint end he
**writes** the handoff (template inside §4.3's appendix: open incidents,
alerts that fired and whether actionable, deploys/changes in flight,
things to watch, playbook gaps found). The harness pages him at most
once per main day, never on weekends (mirrors the SRE load budget).
- **Graded:** handoff names every alert that fired with
  actionable/noise verdict; open risks carried forward; ≥ 1 playbook fix
  or ticket when a page had no playbook; the next AI on-call can act on
  it (the harness later asks the AI on-call a question only the handoff
  can answer — if the handoff omitted it, that shows up in the next
  standup).

### 1.9 Retrospective

**How real teams run it.** Derby & Larsen's five phases: set the stage,
gather data, generate insights, decide what to do (one or two actions),
close ([summary](https://agile.appliedframeworks.com/applied-frameworks-agile-blog/agile-retrospective-framework-in-five-steps));
Norm Kerth's Prime Directive opens many retros: "Regardless of what we
discover, we understand and truly believe that everyone did the best job
they could…" ([Retrospective Wiki](https://retrospectivewiki.org/index.php?title=The_Prime_Directive));
Scrum's retro inspects "individuals, interactions, processes, tools" and
the Definition of Done ([Scrum Guide 2020](https://scrumguides.org/scrum-guide.html)).

**Offer Letter mechanic.** Last main day of the sprint, ≤ 10 min, after
demo. Board with 3 columns (went well / didn't / try next). Teammates
post their own cards first — including **one card that is about him**,
fairly worded ("review turnaround on #52 was 3 days, blocked Mei"),
and one card where a teammate owns their own mistake (models the
behaviour). He adds ≥ 2 cards and proposes 1 action. Last sprint's
action is checked at the start ("did we do it?").
- **Graded:** his cards are specific (an event + effect, not "comms
  could be better"); he responds to the card about him without
  defensiveness (acknowledges, gives context once, proposes a change);
  his action is small, owned, and checkable next sprint; follow-through
  on last sprint's action (harness checks the artifact exists).

### 1.10 One-on-one (manager ↔ him; and him ↔ his junior)

**How real managers run it.** GitLab: a consistent shared agenda doc;
"Both parties add items… Preferably, the majority added by the team
member. If the manager puts more than half of the items on the agenda
this is an indication that something is wrong"; at least two sync 1:1s a
month; quoting *High Output Management*: the 1:1 is "the report's
meeting, with its agenda and tone set by them"; manager talks ~20%;
give feedback right away, don't save it for the 1:1; ask open questions;
monthly career-development conversation covering competencies, skill gaps
and career objectives ("What would you like to learn next?"); make clear
the report "can push back" on manager asks
([GitLab 1-1 handbook](https://handbook.gitlab.com/handbook/leadership/1-1/)).

**Offer Letter mechanic.** Every second Wednesday (main day), 10 min,
visual-novel scene. Shared agenda doc in the app that he can add to all
sprint. The manager seeds ≤ 1/3 of items (GitLab's warning sign is > ½).
Manager feedback cadence: specific feedback is given **the day it
happens** in DM (not saved up), and the 1:1 only references it. Once a
month the 1:1 is a career conversation using the GitLab question set.
When he mentors the junior, roles flip: *he* runs the junior's 1:1.
- **Graded (light — the 1:1 is his space):** he brought ≥ 1 agenda item;
  he asked for feedback on something specific at least once per month;
  career items are concrete ("I want to lead an incident as IC this
  cycle" vs "grow"). *As a mentor:* he lets the junior talk (talk-ratio
  from transcript), asks open questions, ends with one agreed action.
  Never grade emotions or disclosure.

### 1.11 Performance review / promotion packet

**How real companies run it.** Typical big-tech flow: self-review → peer
reviews → manager review → **calibration** across managers; promotion
packets cover a longer window and argue the candidate already shows
next-level behaviours ([Pragmatic Engineer on calibrations](https://newsletter.pragmaticengineer.com/p/performance-calibrations);
[developing.dev summary](https://www.developing.dev/p/how-promotions-and-ratings-work) — secondary).
Google's GRAD (2022) rates on a 5-tier impact scale from "Not Enough
Impact" to "Transformative Impact", yearly ([TechRepublic](https://www.techrepublic.com/article/news-google-cut-bonuses-underperforming-staff/);
press reports — **details unverified against Google**). Dropbox publishes
its ladder: IC levels × areas **Results, Direction, Talent, Culture,
Craft**, with first-person behaviours ("I avoid blame, clarify problems…
and 'disagree and commit' when necessary"; "I write and speak with
clarity and focus") ([Dropbox IC2](https://dropbox.github.io/dbx-career-framework/ic2_software_engineer.html));
their 2023 update fixed reviews "too heavily biased towards big, complex,
or high-profile achievements" by valuing ownership and keep-the-lights-on
work ([Dropbox tech blog](https://dropbox.tech/culture/our-updated-engineering-career-framework)).
Julia Evans' **brag document** — a running list of work and its
*results*, shared with your manager so they can advocate for you
([jvns.ca](https://jvns.ca/blog/brag-documents/)). Tanya Reilly's
"Being Glue": unglamorous coordination work is real technical leadership
but often unrewarded — "If you only do glue, you will only get better
at glue" ([noidea.dog/glue](https://noidea.dog/glue)).

**Offer Letter mechanic.**
- **Cycle = one company stint** (e.g., 6 sprints ≈ 12 weeks), with a
  mid-cycle check-in at sprint 3. The harness keeps an **evidence ledger**
  automatically (every graded artifact above, with links) — the sim's
  equivalent of the review system's data.
- He writes a **self-review / brag doc** (from the ledger; he must add
  *results*, not tasks — Evans' rule). Two AI peers write short peer
  reviews that cite specific artifacts (including one honest criticism
  each). Manager writes the review against the rubric (§4.7) and gives a
  rating on a 5-tier impact-style scale.
- **Calibration scene** (optional, flavour): he sees an anonymised
  "calibration note" explaining what moved his rating — teaches that
  impact must be *legible* to people who didn't watch the work.
- **Promotion packet** (L-up): available when the ledger shows
  next-level behaviours across ≥ 2 projects; he writes the packet; a
  "committee" persona that never worked with him reads it cold.
- **Graded:** the review itself *is* the grade summary; for the packet:
  each claim links an artifact; impact stated with numbers the harness
  measured; covers ≥ 3 rubric areas, not just Craft; includes glue work
  he did *and* its effect.

### 1.12 All-hands

**How real companies run it.** Company-wide meeting for strategy, launches,
org changes and Q&A/AMA; remote companies broadcast decisions to every
channel *the same day* and link a single source of truth ("The email or
Slack message should not be the source of truth")
([GitLab communication](https://handbook.gitlab.com/handbook/communication/)).
GitLab runs AMA calls even before day one ([onboarding](https://handbook.gitlab.com/handbook/people-group/general-onboarding/)).
**[unverified as a cited norm]**: cadence of monthly all-hands is common
practice but I found no authoritative source for a standard.

**Offer Letter mechanic.** Once per stint (or monthly), a 3–5 min
scene in the pixel office's big room: CEO/VP narrative — a launch, a
customer loss, a reorg, a priority shift — **that later changes his
work** (e.g., the PM moves a ticket in the next planning because of it).
He may post one question in the AMA thread.
- **Graded:** not graded directly. Indirectly: when the priority shift
  hits his ticket, does he connect it to the stated reason and re-plan,
  or argue from "but we agreed"? (scored inside sprint planning).

### 1.13 Demo day / sprint review

**How real teams run it.** Scrum: "The Sprint Review is a working session
and the Scrum Team should avoid limiting it to a presentation"
([Scrum Guide 2020](https://scrumguides.org/scrum-guide.html)). UK
government teams run regular **show and tells** for stakeholders —
recent work, plans, questions, team morale
([London.gov.uk](https://www.london.gov.uk/city-hall-blog/show-and-tells-new-londongovuk-website);
[GDS on service demos](https://services.blog.gov.uk/2020/10/12/service-demos-how-to-tell-the-story-of-your-service)).

**Offer Letter mechanic.** Last main day of a sprint (before retro), and
the final milestone of every **build** project. He demos for ≤ 5 min to
the PM + TL (+ "a customer" persona in growth culture): what it does,
the measured result (harness benchmark/metric shown live), what is not
done, what's next. Audience asks 2 questions, one of them awkward
("what happens when the queue is full?").
- **Graded:** the demo starts from the *user problem*, not the code;
  shows the measured result from the harness; states what is missing
  honestly; answers the awkward question or says "I don't know, I'll
  find out by <date>" and then does (follow-through checked).


## 2. Team roster and persona archetypes

### 2.1 Team shape

Use Team Topologies' vocabulary so the org feels coherent: his team is a
**stream-aligned** team (owns a slice of the product end to end); it
depends on a **platform** team (internal product, consumed
"X-as-a-Service" — you file a ticket and wait), sometimes works with an
**enabling** team (temporary help: e.g., an ML-infra or security
specialist) in **collaboration** mode for a defined period
([Team Topologies key concepts](https://teamtopologies.com/key-concepts)).
That gives realistic friction for free: cross-team waits, API contracts,
"that's not our service".

Core team (6 AI + him), plus a few recurring outsiders:

| Role | Owns | How they deal with a junior (him) | Realistic friction they create |
|---|---|---|---|
| **Engineering Manager** | people, delivery dates, 1:1s, perf review, hiring, shielding the team | sets expectations in week 0; one check-in per slipped deadline (no nagging); same-day feedback in DM; runs the biweekly 1:1 (his agenda); writes his review | pushes for a date when he's unsure; says no to his pet refactor "this quarter"; occasionally relays an unpopular decision from above ("disagree and commit") |
| **Tech Lead** (Larson's "Tech Lead" archetype: "guides the approach and execution of a particular team" — [staffeng.com](https://staffeng.com/guides/staff-archetypes/)) | technical direction, design approval, walks the board at standup, final call in design disputes | assigns his tickets on a Simple-Complex ladder; reviews his design docs; is his escalation point for review deadlocks (Google's path: author ↔ reviewer → TL) | strong prior opinions ("we tried queues in 2024, it was a mess"); asks for rollout/rollback plans he forgot; sometimes over-engineers |
| **Senior engineer** (Architect/Solver flavour) | a deep domain (storage, GPU serving, netcode…) and its decision notes | high-bar reviewer; design-review partner on the whiteboard; teaches through questions | nitpicks; holds out for "perfect" (violates Google's code-health standard — he should notice and push back); can be *wrong* about the domain he doesn't own |
| **Peer engineer** (same level or one above) | an adjacent component with an interface to his | pair partner, reviews his PRs fast and informally, swaps context | API contract disagreements; slow review when overloaded; merge conflicts; occasionally breaks his tests |
| **Product Manager** | the *why/what*, priorities, scope, stakeholder promises | writes tickets/PRDs; accepts demos; asks "when?" | mid-sprint scope change ("can it also export CSV?"); vague acceptance criteria; deprioritises tech debt until shown data; promises a customer a date before asking eng |
| **Junior / intern he mentors** (from ~his 3rd sprint) | starter tickets | asks him questions; sends him PRs to review; he runs their 1:1 | planted mistakes in PRs; hesitates to ask (Ju et al.: new devs "might feel hesitant to ask questions because they feel unsafe"); over-scoped first PR |
| *Outsiders (recurring, light)*: platform/SRE engineer, a designer or data scientist, support liaison (incidents), VP/CEO (all-hands), promo-committee member (reads packet cold), OSS maintainer from another org (OSS culture) | | | |

### 2.2 Making AI teammates distinct real people (not caricatures)

Evidence and design rules:

1. **Character sheet, not a quirk.** Each persona = role · this quarter's
   goal · what they're worried about · domain expertise and *blind spot* ·
   communication style (terse/verbose, async/sync, emoji or not) ·
   availability (timezone, OOO days) · review habits (what they always
   check) · history with the codebase (the decision notes they wrote) ·
   relationships with other personas · one thing they genuinely admire in
   others' work. Traits are **tendencies**, expressed in maybe 1 message in
   4, never every line — Radical Candor calls its own quadrants "a compass,
   not a label" ([radicalcandor.com](https://www.radicalcandor.com/our-approach/)).
2. **Memory, reflection and plans make NPCs believable.** In the
   Generative Agents study, removing memory, reflection and planning
   produced the least believable agents; each component "contribute[s]
   critically to the believability" ([Park et al., UIST 2023](https://arxiv.org/abs/2304.03442)).
   So each teammate keeps: an episodic log (what he did, what they said,
   promises made), periodic reflections ("he's improved at splitting
   PRs"), and a plan for the sprint (their own tickets). They should
   reference past events specifically ("like the retry bug in #31").
3. **Fight persona drift.** Instructed chatbots drift from their system
   prompts within ~8 rounds of dialogue ([Li et al., COLM 2024](https://arxiv.org/abs/2402.10962)).
   Re-inject the character sheet + recent memory on every turn, keep
   conversations short (rituals are short anyway), and run a cheap
   consistency check (a small model scores "does this sound like <name>?"
   against 5 canonical lines per persona) before sending.
4. **Everyone is competent; friction comes from interests, not
   villainy.** The PM changes scope because a customer is churning, the
   senior nitpicks because a past outage came from sloppy naming. The
   Rehearsal system (Stanford, CHI 2024) conditioned LLM counterparts on
   Interest-Rights-Power conflict theory: simulated counterparts reached
   agreement only after the learner used several interest-based
   strategies, and trainees cut escalating strategies by 67% and doubled
   cooperative ones vs a lecture control (N=40)
   ([Shaikh et al.](https://arxiv.org/abs/2309.12309)). Give every
   friction-creating persona an explicit *interest* the learner can
   discover by asking.
5. **Model psychological safety.** Google's Project Aristotle found
   psychological safety, dependability, structure & clarity, meaning and
   impact matter most for team effectiveness
   ([re:Work guide](https://rework.withgoogle.com/intl/en/guides/understand-team-effectiveness));
   DORA finds generative (high-trust, information-flowing) culture
   predicts delivery performance and well-being
   ([DORA capability](https://dora.dev/capabilities/generative-organizational-culture/)).
   So teammates **admit their own mistakes** in retro, say "I don't know,
   let me check", thank him for catches, and never mock a question.
6. **Realistic availability.** Teammates are busy: replies take minutes to
   hours (within the review SLA), someone is OOO, the senior is
   heads-down until 2 pm. This forces async writing quality (§5.3) and
   makes "who do I ask?" a real decision.
7. **No caricature tells.** Ban: catchphrases, constant jokes, every
   message mentioning their hobby, anime-trope personalities leaking into
   technical judgement. The visual-novel art can be stylised; the
   *dialogue* should read like a real Slack. Test: shown a message with
   the name removed, would an engineer believe a colleague wrote it?

### 2.3 Pushback: teammates question him, and accept good pushback

The failure mode to design against is **sycophancy**: RLHF-trained
assistants tend to agree with the user, and humans and preference models
sometimes prefer a convincing sycophantic answer over a correct one
([Sharma et al., ICLR 2024](https://arxiv.org/abs/2310.13548)). A
teammate who folds whenever he objects teaches nothing.

**Rules for teammates questioning him**
- Every non-trivial PR and design doc gets ≥ 1 *decision question*
  ("why a lock here instead of a channel?"), drawn from the project's
  pushback hooks. Asked as a question first (Google: "ask questions
  before assuming an approach is wrong" — [SWE at Google ch. 9](https://abseil.io/resources/swe-book/html/ch09.html)).
- Follow-up probing like a senior would: "what happens under 10× load?",
  "how would you roll this back?", "what did you measure?"
- **Roughly 1 in 4 pushbacks is planted-wrong** (a stale assumption, a
  benchmark misread, a preference stated as a rule). He should catch it.
  If he accepts a wrong suggestion, the consequence shows up later (test
  or benchmark regresses) and the teammate owns it in retro — no
  punishment for him beyond the lesson, but the perf ledger notes
  whether he *checked*.

**Concession policy (when a teammate changes their mind)** — encode it,
don't leave it to the model's mood:
- Concede when he brings **evidence** (a benchmark, a failing test, a
  profile, a doc/source quote), a **constraint** they missed, or a
  **better alternative with its trade-off stated**.
- Do **not** concede to repetition, confidence, seniority claims, or
  "I just prefer it". Reply instead with what *would* convince them
  ("show me p99 under the burst test and I'm in").
- Partial concessions are realistic: "OK for this PR, file a ticket for
  the general case."
- When the disagreement deadlocks after 2 exchanges, the persona proposes
  the real escalation path: a call, then the TL (Google's path —
  [standard](https://google.github.io/eng-practices/review/reviewer/standard.html)),
  and records the outcome in the thread.
- When he's right, they say so plainly and publicly ("good catch — Mei,
  this changes your PR too"). Credit is a reward the sim can give
  without points.

**Friction catalogue (scenario hooks the harness can schedule)**

| Scenario | Who | What a good response looks like |
|---|---|---|
| Design disagreement | TL vs him (e.g., queue vs direct call) | names the trade-off, offers data or a spike, agrees on a decision rule ("if p99 < 50 ms with direct calls we keep them") |
| Review nitpicks | Senior | accepts nits quickly, argues only blocking items, asks to move style rules to a linter |
| Holding out for perfect | Senior | points to the "improves code health" bar, proposes a follow-up ticket |
| Scope change mid-sprint | PM | restates the sprint goal, offers trade: "add CSV, drop X, or move date to Fri" (Scrum: scope renegotiated with the PO, goal unchanged) |
| Conflicting asks | PM vs TL | doesn't silently pick a side; writes both asks + cost to the two of them / EM (escalation, §5.6) |
| Cross-team dependency late | Platform engineer | early warning in standup, a workaround or a re-plan, a ticket with a clear ask |
| Junior's buggy PR | Junior | finds it, explains why with a question first, doesn't rewrite it for them |
| Manager asks for a date he can't give | EM | gives a range + what would narrow it + when he'll know |


## 3. Culture profiles

Each profile is a set of **dials** the harness reads (review strictness,
doc requirement, meeting load, deadline style, feedback style,
onboarding strategy, incident process, perf process). "Firm but fair" is
constant across all four; what changes is *what* is firm.

### 3.1 Seed startup (≈ 4–15 people)

Real accounts: startups are "very flat organizations, meaning you are
often involved in strategic decisions"; "startups are often races
against the clock"; in a monolith "the same changes take hours, not
days" ([Pragmatic Engineer, startup vs Big Tech](https://blog.pragmaticengineer.com/working-at-a-startup-vs-in-big-tech/)).
"Don't introduce any tools or processes unless they are solving a
present problem"; "Own the whole thing — if something is broken, don't
wait for someone else to fix it"; get to know the customers
([Dan Webb, How to be a startup engineer](https://danwebb.net/posts/how-to-be-a-startup-engineer/)).
Big-tech hires who try to import heavy process "completely failed";
"planning years in advance at a startup is usually a waste of time"
([Pragmatic Engineer, Hiring from Big Tech](https://newsletter.pragmaticengineer.com/p/hiring-from-big-tech)).
Carta data puts the median seed team at ~4 employees (via a
[recruiting blog](https://www.recruitingfromscratch.com/blog/how-to-hire-your-first-5-engineers-at-a-startup-2026) — **secondary**).
Onboarding is Priority-First / Exploration-Based ([Ju et al.](https://arxiv.org/abs/2103.05055)).

| Dial | Feels like |
|---|---|
| Deadlines | Tight, external (a demo for an investor, a pilot customer). Dates move when the founder learns something; he must re-plan fast. |
| Reviews | One approval, quick, correctness and "will this page us at 3 am?"; nits mostly skipped. |
| Documentation | README, a short decision note in the PR, a Loom. A design doc only for risky or irreversible things — writing a 10-page doc here is *penalised* (wrong-sized). |
| Meetings | Almost none: a Monday "what are we shipping" and ad-hoc calls. |
| Autonomy | Very high and ambiguous: "figure out what the customer needs". |
| Feedback | Direct, immediate, informal, from the founder/CTO; no formal review cycle — a "how's it going" chat at 3 months. |
| Incidents | Whoever is around fixes it; postmortem is a Slack thread; he learns to add the safeguard himself. |
| The boss | Founder-CTO who codes; checks in once, expects him to unblock himself. |
| Trains | ownership, scoping down, speed with judgement, talking to users |
| Failure mode to depict honestly | hero culture, no tests, burnout risk — the sim shows the cost (a 2 am-style incident on a main day) without glamorising it |

### 3.2 Growth company (≈ 100–1,500 people, Series C+ or newly public)

Real accounts: small product teams of 2–6 that own an area, have a
customer, set quarterly goals, run their own weekly sprint and retro
"transparently", and decide what ships "no need for external QA";
managers coach and "should not assign tasks"
([PostHog small teams](https://posthog.com/handbook/company/small-teams)).
GitLab-style async-first: "use asynchronous communication as a starting
point", "Use low-context communications by being explicit", a
**DRI** who must "acknowledge the comments… and say why, not just what"
([GitLab communication](https://handbook.gitlab.com/handbook/communication/)).
Process arrives as the org grows: Uber went from a few engineers to
2,000+ and leaned on RFCs read across teams to keep the bar consistent
([Pragmatic Engineer RFC piece](https://blog.pragmaticengineer.com/scaling-engineering-teams-via-writing-things-down-rfcs/)).
Shape-Up-style appetite and circuit breakers are a common growth-stage
choice ([Shape Up](https://basecamp.com/shapeup/0.3-chapter-01)).

| Dial | Feels like |
|---|---|
| Deadlines | Sprint commitments + quarterly OKRs; the PM negotiates scope; missing is visible on the board and discussed in planning. |
| Reviews | CODEOWNERS, CI gates, one approval, review SLA in a team agreement, labelled nits. |
| Documentation | 1–3 page RFC for anything cross-team; ADRs in the repo; runbooks for on-call. |
| Meetings | Daily async standup + weekly sync, biweekly planning/demo/retro, biweekly 1:1. |
| Autonomy | High inside the team's area; cross-team changes need an RFC. |
| Feedback | Biannual review cycle with a public ladder; peer feedback; same-day DM feedback from the EM. |
| Incidents | PagerDuty-style roles, SEV levels, templated postmortems, action items tracked. |
| The boss | EM with 6–8 reports, protective, data-driven, short 1:1s. |
| Trains | the full ritual set; this is the **default culture** for most stints |
| Failure mode | process creeping in faster than it helps; meetings multiply |

### 3.3 Big-tech division (a team inside a 50k+ company)

Real accounts: every change needs peer LGTM + OWNERS + readability
approval; small changes (~200 lines); a 24-working-hour review
expectation ([SWE at Google ch. 9](https://abseil.io/resources/swe-book/html/ch09.html));
design docs with formal review for big work and dedicated privacy/security
reviews ([Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/));
changes across many services need each owning team's approval across
time zones and quarterly planning to line up dependencies
([Pragmatic Engineer](https://blog.pragmaticengineer.com/working-at-a-startup-vs-in-big-tech/));
formal perf cycles with calibration and impact ratings
([GRAD press coverage](https://www.techrepublic.com/article/news-google-cut-bonuses-underperforming-staff/));
Simple-Complex onboarding with a months-long ladder ("3 to 9 months:
become an expert in one domain") ([Ju et al.](https://arxiv.org/abs/2103.05055));
specialisation on "very small product surface areas" and internal tools
([Hiring from Big Tech](https://newsletter.pragmaticengineer.com/p/hiring-from-big-tech));
Dropbox's own diagnosis that reviews over-rewarded "big, complex, or
high-profile achievements" ([Dropbox](https://dropbox.tech/culture/our-updated-engineering-career-framework))
— a real big-tech incentive the sim can show.

| Dial | Feels like |
|---|---|
| Deadlines | Release trains and quarterly roadmaps; deadlines are *planned* far ahead and slips need a written heads-up to dependent teams. |
| Reviews | Strict and multi-stage; style enforced (a "readability" gate); many nits but labelled; slower but predictable. |
| Documentation | Design doc required above a size threshold; production-readiness checklist (KEP-style PRR) before launch. |
| Meetings | More: standup, planning, design review meetings, cross-team syncs; staff engineers present in reviews. |
| Autonomy | Narrow scope, deep: he owns one component very well; changing a neighbour's service means asking them. |
| Feedback | Formal: peer reviews, manager review, calibration, rating scale, promo packets read by a committee. |
| Incidents | Trained ICs, SEV process, postmortem review meetings, error budgets; very blameless. |
| The boss | EM managing 8–12; skip-level exists; the TL/staff engineer is the technical authority. |
| Trains | writing for readers who weren't there, legible impact, working across teams, patience with process |
| Failure mode | optics over impact ("Doing work that results in a great performance review is not always the same work that best helps the company" — Spruijt in [Pragmatic Engineer](https://blog.pragmaticengineer.com/working-at-a-startup-vs-in-big-tech/)) |

### 3.4 Open-source foundation project (Apache / CNCF / Rust-style)

Real accounts: "Community over code"; earned, non-expiring merit;
decisions on public archived lists — "off-list discourse… must be
brought on-list"; consensus first, votes for releases and committers
([Apache Way](https://www.apache.org/theapacheway/)); **lazy consensus**:
state intent, wait ~72 h, "Silence indicates consent"
([ASF lazy consensus](https://community.apache.org/committers/lazyConsensus.html));
+1/0/−1 votes, a code −1 is a veto that needs a technical justification,
releases need 3 binding +1s and can't be vetoed
([ASF voting](https://www.apache.org/foundation/voting.html)); Rust RFCs
with a 10-day FCP ([rust-lang/rfcs](https://github.com/rust-lang/rfcs/blob/master/README.md));
Kubernetes SIGs with public notes and recordings
([SIG governance](https://git.k8s.io/community/committee-steering/governance/sig-governance.md));
reviews in "a few weeks (typically 2-3)", wait ≥ 1 week before pinging,
"ignoring reviewers is a good way to get ignored in return"
([Linux kernel, submitting patches](https://www.kernel.org/doc/html/latest/process/submitting-patches.html));
LLVM's one-week courtesy ping and "All comments by reviewers should be
acknowledged" ([LLVM](https://llvm.org/docs/CodeReview.html)).

| Dial | Feels like |
|---|---|
| Deadlines | No boss deadlines; **release freezes** are the deadline (miss the freeze, wait for the next release). Self-set milestones in his proposal. |
| Reviews | Volunteer maintainers, slow, async, public, sometimes blunt; he must ping politely and make PRs easy to review. Compressed for the sim: "a week" = 2 sim workdays. |
| Documentation | RFC/KEP/proposal as a PR; design discussion in issues; everything public and archived. |
| Meetings | One optional public community call per sprint; decisions never made there without being written to the list/issue. |
| Autonomy | Total in what he proposes; zero authority until merit is earned (committer status is a late-game reward). |
| Feedback | No manager review. Feedback = review comments, votes, and eventually a "we'd like to nominate you as committer" thread. The sim's perf review becomes a **"committer nomination"** written by a maintainer persona. |
| Incidents | Security advisories, regression reports from users, a public postmortem/issue. |
| The boss | No boss. A maintainer/PMC chair persona + a mentor (Rust/GSoC-style). |
| Trains | async writing, persuasion without authority, patience, consensus-building |
| Failure mode | maintainer burnout and silence; depict ignored PRs and teach the polite ping + making the PR easier to review |

### 3.5 Cross-culture constants

- Deadlines are always real *within the culture's mechanism* (founder
  date / sprint commitment / release train / release freeze).
- Misses are always surfaced once in the culture's public channel
  (standup, planning, release thread) and once in the review artefact
  (perf review / committer nomination). Never more.
- Teammates are always competent and in good faith; the culture changes
  *pace and formality*, not decency.


## 4. Templates the harness can ship

Compact versions built from the real ones. Each template has a
"graded on" line so the rubric and the template are the same thing.
Culture dial: seed uses the short form (marked *(seed: skip)*), big-tech
adds the marked extras.

### 4.1 Design doc (mini, 1–3 pages)

Sources: [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/),
[HashiCorp RFC template](https://www.hashicorp.com/en/how-hashicorp-works/articles/rfc-template),
[Uber RFC fields via Pragmatic Engineer](https://blog.pragmaticengineer.com/rfcs-and-design-docs/),
[KEP PRR](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md).

```markdown
# <Title>
Status: Draft | In Review | Approved | Implemented | Obsolete
Author: <him>   Reviewers: <TL>, <senior>, <PM>   Last updated: <date>
Ticket/epic: <link>

## Context and scope        (a newcomer gets full context from this; no requirements dump)
## Goals                    (each one measurable → ties to the harness done-condition)
## Non-goals                (things that could reasonably be goals but aren't)
## Design
### Overview                (one diagram: system context)
### API / data / storage    (high level; code only if it is the point)
### Failure modes           (what breaks, how we detect it)
## Alternatives considered  (≥2, each with why rejected)
## Rollout and rollback     (flag? migration? how to undo)
## Observability            (metrics/logs/alerts that prove it works)
## Cross-cutting            (security, privacy, cost) (seed: skip)
## Production readiness     (big-tech only: KEP-style PRR questions)
## Open questions
## Revision log             (what changed after review, and why)
```
**Graded on:** non-goals present; ≥ 2 real alternatives; success measured;
rollback stated; every review thread resolved with a decision; revision
log updated; length matches appetite.

### 4.2 RFC (for cross-team changes and OSS culture)

Sources: [Rust RFC template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)
and [process](https://github.com/rust-lang/rfcs/blob/master/README.md),
[Oxide RFD 1](https://rfd.shared.oxide.computer/rfd/0001),
[HashiCorp](https://www.hashicorp.com/en/how-hashicorp-works/articles/rfc-template),
[ASF lazy consensus](https://community.apache.org/committers/lazyConsensus.html).

```markdown
# RFC-<n>: <Title>
State: prediscussion | discussion | FCP(merge|close|postpone, ends <date>) | accepted | abandoned
Author · Sub-team/approvers · Discussion: <PR link>

## Summary                  (one paragraph)
## Motivation               (the problem, concrete use cases)
## Guide-level explanation  (teach it as if it already existed; examples)
## Reference-level design   (exact behaviour, edge cases, interactions)
## Drawbacks                (why we should NOT do this)
## Rationale and alternatives (incl. cost of doing nothing)
## Prior art                (how others solved it — cite)
## Abandoned ideas          (kept, labelled, with why)
## Unresolved questions
## Future possibilities
```
Process the sim runs: pre-RFC thread → PR → comments (author answers
each, revisions as new commits with a summary comment) → FCP banner
(sim: 3 workdays; real Rust: 10 days) → accept/close/postpone.
**Graded on:** drawbacks section is honest (not empty); prior art cites
something real; author responded to every thread; summary comment after
each revision.

### 4.3 Postmortem (+ on-call handoff appendix)

Sources: [Google SRE example postmortem](https://sre.google/sre-book/example-postmortem/),
[SRE postmortem culture](https://sre.google/sre-book/postmortem-culture/),
[PagerDuty template](https://response.pagerduty.com/after/post_mortem_template/),
[PagerDuty blameless guide](https://postmortems.pagerduty.com/culture/blameless/),
[SRE workbook on-call](https://sre.google/workbook/on-call/).

```markdown
# Postmortem: <short name>   (blameless)
Date · Authors · Status: Draft | In Review | Final · Severity: SEV-<n> · Duration

## Summary            (2–3 sentences: what, impact, cause, fix)
## Impact             (users/requests affected, error rate, SLO burn, duration — numbers)
## Timeline (UTC)     (start BEFORE the trigger; forward in time; detection, page, mitigation, resolution; link graphs/logs)
## Root cause(s) and contributing factors   (conditions, not people; why safeguards didn't catch it)
## Trigger            (the specific change/event)
## Detection          (how we found out; how long it took; would an alert have caught it?)
## Resolution         (mitigation first, then the real fix)
## What went well / What went wrong / Where we got lucky
## Action items
| Action | Type (prevent/mitigate/detect/process) | Owner | Ticket | Due |
## Messaging          (internal note; external status text if user-visible)
```
Blameless language rules (from PagerDuty): describe *how* a mistake was
made, not *who*; prefer "what/how" questions to "why did you"; frame
human actions so "anyone could have made the same mistake"; build the
timeline forward to avoid hindsight bias.

**Graded on:** blameless (no "X should have…"); root cause goes past the
trigger; ≥ 1 action item addresses the *class* of failure; every action
has owner + ticket; "where we got lucky" non-empty; timeline starts
before the trigger.

**On-call handoff note (end of shift):**
```markdown
## Handoff <service> <dates>  from <him> → <next>
- Open incidents / ongoing mitigations:
- Alerts that fired: <alert> × <n> — actionable? (yes/noise → ticket)
- Changes in flight: deploys, flags, migrations, risky PRs merging this week
- Watch list: things trending wrong (disk, latency, error budget)
- Playbook gaps found (+ ticket):
- Anything you'll need from me (I'm reachable until <time>):
```

### 4.4 PR description

Sources: [Google CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html),
[SWE at Google ch. 9](https://abseil.io/resources/swe-book/html/ch09.html),
[Linux kernel submitting patches](https://www.kernel.org/doc/html/latest/process/submitting-patches.html).

```markdown
<Imperative one-line summary of what this does>   e.g. "Batch embedding requests into 32-item calls"

Why: <the problem; link ticket/design doc; enough context that the link can die>
What: <the approach in 2–5 lines; what you chose NOT to do and why>
How tested: <tests added/changed; benchmark before → after; manual steps>
Risk / rollout: <flag? migration? how to roll back>
Reviewer notes: <where to start reading; what you're unsure about>
Follow-ups: <tickets for things deliberately left out>
```
**Graded on:** first line is imperative and specific (not "Fix bug",
"Phase 1"); *why* is present and self-contained; test evidence present;
≤ ~400 changed lines or a reason; description updated if the PR changed
during review (Google asks for a re-read before submit).

### 4.5 Review comment style guide (for teammates *and* for him)

Sources: [Google: comments](https://google.github.io/eng-practices/review/reviewer/comments.html),
[Google: standard](https://google.github.io/eng-practices/review/reviewer/standard.html),
[Conventional Comments](https://conventionalcomments.org/),
[LLVM](https://llvm.org/docs/CodeReview.html).

Format: `<label> [(blocking|non-blocking|if-minor)]: <subject>` + optional
reasoning.

| Label | Use for | Blocking by default? |
|---|---|---|
| `issue:` | a real problem (bug, race, wrong result, missing test for a risky path) | yes |
| `question:` | you suspect a problem or don't understand — ask before asserting | no (becomes `issue` if the answer confirms it) |
| `suggestion:` | a better way; say what and why | no unless marked |
| `nitpick:` / `Nit:` | trivial, preference | never |
| `todo:` / `chore:` | small required change (rename, changelog) | yes |
| `thought:` / `FYI:` | idea for later — "I don't expect you to do this in this CL" | never |
| `praise:` | something done well — at least one per review | — |

Rules: comment on the code, not the person; give the *why*; point out
the problem and let the author choose the fix unless direct guidance is
faster; approve when the change improves code health, not when it's
perfect; author acknowledges **every** comment (fixed / answered /
ticketed); disagreements: two rounds in-thread → call → TL; record the
outcome in the thread.
**Graded on (his reviews):** labels match severity; each blocking comment
has a why; one praise; no personal remarks; approves good-enough code.

### 4.6 One-on-one agenda (shared doc, his meeting)

Source: [GitLab 1-1 handbook](https://handbook.gitlab.com/handbook/leadership/1-1/).

```markdown
# 1:1 <him> / <manager> — <date>
## His items (add during the sprint; aim for most of the agenda)
-
## Manager's items (≤ 1/3)
-
## Feedback — both directions
- One thing to keep doing / one thing to change (manager → him)
- One thing the manager could do better (him → manager)
## Career (monthly)
- Competency I'm proud of · skill gap I'm working on · what I want to learn next
## Actions
- [ ] <owner> <action> <by when>
```
Prompt bank for when his list is empty (from GitLab): "What are you most
proud of since last time?", "What's unclear?", "What potential trouble do
you see for the team?", "What can I improve on?", "When X happened, what
would you do differently?"

### 4.7 Performance review rubric (outline)

Sources: [Dropbox Engineering Career Framework](https://dropbox.github.io/dbx-career-framework/ic2_software_engineer.html)
(areas Results / Direction / Talent / Culture / Craft) and its
[2023 update](https://dropbox.tech/culture/our-updated-engineering-career-framework);
[brag documents](https://jvns.ca/blog/brag-documents/);
[Being Glue](https://noidea.dog/glue). Five-tier outcome scale modelled
on impact ratings like GRAD's (names changed).

| Area | Observable evidence the harness already has | L2 "meets" looks like |
|---|---|---|
| **Results** | commitment reliability; done-conditions met; incident time-to-mitigate | ≥ 80% of commitments on time; early warning on slips; owns his mistakes |
| **Craft** | tests, benchmark results, review findings, PR size | correct mainline code; bugs only in edge cases; code "written to be read" |
| **Communication & collaboration** (Dropbox "Culture") | PR/doc/postmortem rubric scores; review comment quality; standup updates | clear writing; disagrees with evidence then commits; blameless |
| **Direction** | design alternatives, pushback accepted/rejected with reasons, proposals | asks good questions; proposes ideas; learns from experiments |
| **Talent** (from mentoring phase) | junior's progress; his 1:1s with the junior; feedback he sought | asks for feedback and acts on it; helps the junior without doing their work |
| **Glue** (shown, not a separate rating) | handoffs, runbook fixes, onboarding docs he improved | credited explicitly so it isn't invisible |

Outcome scale: *Not yet meeting · Partially meeting · Meeting · Exceeding
· Exceptional*. Each rating sentence must cite ≥ 1 artifact link.
Self-review = brag doc (results, not tasks). Peer reviews = two
teammates, each one strength + one growth area with an example.

### 4.8 Onboarding checklist (Week 0 issue)

Sources: [GitLab onboarding](https://handbook.gitlab.com/handbook/people-group/general-onboarding/),
[Meta bootcamp account](https://dev.to/automationhacks/engineering-practices-meta-3-conduct-an-engineering-bootcamp-for-new-joiners-591e),
[Ju et al.](https://arxiv.org/abs/2103.05055),
[Rodeghero et al.](https://arxiv.org/abs/2011.08130).

```markdown
# Onboarding: <him> @ <company>   due: end of week 0 (main) / week 2 (all)
Buddy: <peer>   Manager: <EM>   First ticket: <link>

## Day 1
- [ ] Welcome call with manager: expectations, how the team works, how to ask for help
- [ ] Dev environment: clone, run setup, tests green (paste output if not)
- [ ] Day-one PR: <tiny real change> → review by buddy → CI → merged
- [ ] Say hi in #team; read the team README / working agreement
## Days 2–3
- [ ] Read decision notes: <2–3 links>; write 1 question per note
- [ ] Architecture tour (voice) with the TL
- [ ] Starter ticket (L1) picked up; estimate in blocks posted
## Days 4–5
- [ ] Coffee chat with a non-manager teammate
- [ ] First async standup posted
- [ ] Starter ticket merged
- [ ] 30/60/90 conversation with manager (what "good" looks like at each point)
## By week 2
- [ ] Shadow one incident drill (Wheel of Misfortune-style) or read 2 past postmortems
- [ ] Review one teammate PR (labels per style guide)
- [ ] Fix one thing in the onboarding docs that was wrong (docs reflect reality)
```


## 5. Communication skills a senior shows

A useful single lens for all six: Westrum's definition of good
information, which DORA uses to define generative culture — it "provides
answers to the questions that the receiver needs answered", "It is
timely", and "It is presented in such a way that the receiver can use it
effectively" ([DORA](https://dora.dev/capabilities/generative-organizational-culture/)).
Every rubric below is that sentence made concrete. Dropbox's ladder puts
these in the job description even at IC2: "I write and speak with
clarity and focus"; "I proactively ask for feedback"; "'disagree and
commit' when necessary" ([Dropbox IC2](https://dropbox.github.io/dbx-career-framework/ic2_software_engineer.html)).

Each skill: what to observe → where the sim exercises it → a worked
before/after the harness can show as an example card.

### 5.1 Asking good questions

Sources: Julia Evans — "State what you understand about the subject so
far", be specific, ask questions with factual answers, ask questions that
surface hidden assumptions, research a little first, pick who to ask
(someone "a little less knowledgeable" is often better)
([jvns.ca/blog/good-questions](https://jvns.ca/blog/good-questions/));
new hires under-ask because they "feel unsafe, or they do not want to
bother others" ([Ju et al.](https://arxiv.org/abs/2103.05055)).

**Observable (graded):** states goal + current understanding + what he
tried (with exact error/output) before the ask; one specific question,
answerable; addressed to the right person/channel (owner of the code,
public channel over DM for shareable answers); asks *early* — the
harness tracks time-stuck and rewards asking before a block is wasted,
while still showing he tried; closes the loop ("that worked, added it
to the README").
**Exercised in:** onboarding, every ticket, review-to-own quizzes.
**Example:** ✗ "the build is broken, help?" → ✓ "Trying to run
`make bench` on main (a3f9e1). It fails at link: `undefined reference
to cblas_sgemm`. I installed libopenblas-dev; same error. Is the bench
expected to use MKL? @Priya you wrote the Makefile — is there a flag?"

### 5.2 Disagreeing well (and committing)

Sources: Amazon: "Leaders are obligated to respectfully challenge
decisions when they disagree" and then commit fully
([Leadership Principles](https://www.amazon.jobs/content/en/our-workplace/leadership-principles));
Google review conflicts: try to agree via the guide → talk live → TL/EM,
record the outcome
([eng-practices](https://google.github.io/eng-practices/review/reviewer/standard.html));
SBI(I): Situation, Behaviour, Impact, then ask about Intent —
"the only way to know what someone intended is to ask them"
([CCL](https://www.ccl.org/articles/leading-effectively-articles/closing-the-gap-between-intent-vs-impact-sbii/));
interest-based (not positional) negotiation trains better outcomes
([Rehearsal, CHI 2024](https://arxiv.org/abs/2309.12309)); Radical Candor
— challenge directly *and* care personally
([radicalcandor.com](https://www.radicalcandor.com/our-approach/)).

**Observable (graded):** restates the other position fairly first;
argues from evidence (benchmark, test, doc, constraint) not seniority or
taste; separates blocking from preference; proposes a decision rule or
experiment; asks about the other person's interest/constraint; knows
when to stop (2 rounds) and escalate; after the decision, **commits**
— no re-litigating in the next PR, executes the chosen option well.
Also graded in reverse: he **accepts** a teammate's good pushback
promptly, without defensiveness.
**Exercised in:** design review, PR threads, planted-wrong pushback
(§2.3), planning.
**Example:** ✗ "I don't think a queue is needed." → ✓ "I think we
can skip the queue for v1: at our 200 rps peak, direct calls measured
p99 31 ms (bench in PR). Your concern is burst traffic from the batch
job, right? Proposal: ship direct calls behind a flag, add the burst test
from INC-12; if p99 > 50 ms there, I'll add the queue in the next sprint."

### 5.3 Writing for readers

Sources: "Good documentation provides the necessary knowledge and skills
for the audience to perform a task"; beware the **curse of knowledge**
([Google Technical Writing: Audience](https://developers.google.com/tech-writing/one/audience));
GitLab's "low-context communications by being explicit" and "say why,
not just what" ([GitLab](https://handbook.gitlab.com/handbook/communication/));
HashiCorp's newcomer test for the Background section
([HashiCorp](https://www.hashicorp.com/en/how-hashicorp-works/articles/rfc-template));
Amazon's narrative memos read silently before discussion
([CNBC](https://www.cnbc.com/2018/04/23/what-jeff-bezos-learned-from-requiring-6-page-memos-at-amazon.html));
BLUF — the purpose and the ask in the first line
([Sehgal, HBR 2016 repost](https://kabir.cc/how-to-write-email-with-military-precision/)).

**Observable (graded):** first line carries the point/ask (BLUF);
names the audience implicitly by what's defined vs assumed; defines
acronyms/internal names on first use; links instead of pastes but
includes enough to stand alone if links die (Google CL rule); concrete
numbers over adjectives; one idea per paragraph; length fits the
artifact (standup ≤ 60 words; PR ≤ 1 screen; mini doc ≤ 3 pages).
A cheap automatic check: a "cold reader" AI (the promo-committee
persona, no context) must answer 3 questions about the doc from the doc
alone.
**Exercised in:** every artifact.
**Example:** ✗ "So I looked into the latency thing and there were a
few issues with the pool and also GC, I fixed some of it…" → ✓
"p99 is down from 120 ms to 45 ms (target 50). Two causes: connection
pool too small (8 → 32) and a per-request JSON re-parse. GC was *not* a
factor (flame graph linked). Remaining: cold-start spike, ticket
SRV-88."

### 5.4 Status updates

Sources: Westrum's "timely" + "usable" (above); PagerDuty incident
updates on a cadence, "If in doubt, post it out"
([PagerDuty](https://response.pagerduty.com/during/during_an_incident/));
PostHog cross-team owners post a status update every two weeks
([PostHog](https://posthog.com/handbook/company/small-teams));
standup "Tell the headline, not the whole story"
([martinfowler.com](https://martinfowler.com/articles/itsNotJustStandingUp.html)).

**Observable (graded):** status first (on track / at risk / off track),
then evidence, then the ask; outcomes not activity; dates as dates;
**bad news early** — the harness rewards a "at risk" flag raised while
there is still slack far more than a perfect on-time finish; next
update time stated (incidents); no surprises at the deadline.
**Exercised in:** standups, incident channel, milestone updates in
*build* projects, the weekly note to the PM on multi-week work.
**Example:** ✓ "**At risk** — ingest v2 (due Fri). Parser done + tested;
dedup is 2× slower than budget (bench: 9 s vs 4.5 s). Options: (a) ship
Fri without dedup behind a flag, (b) ship Mon with dedup. I recommend (a).
Need: PM call on (a)/(b) by Wed EOD."

### 5.5 Saying no (and "not now", "not like that")

Sources: GitLab tells managers to make clear reports "can push back (not
a good idea, not worth the time), and redirect (please handle it directly
with this person…)" ([GitLab 1-1](https://handbook.gitlab.com/handbook/leadership/1-1/));
Scrum: scope is renegotiated with the Product Owner while the Sprint Goal
holds ([Scrum Guide](https://scrumguides.org/scrum-guide.html)); Shape
Up's appetite and circuit breaker ([Shape Up](https://basecamp.com/shapeup/0.3-chapter-01));
startup engineers succeed by "making tradeoffs and saying no"
([Twill](https://twillrecruiting.beehiiv.com/p/what-makes-a-great-founding-engineer) —
secondary).

**Observable (graded):** never a bare "no": gives the trade-off ("yes,
if we drop X / move the date to Y"), or a smaller version, or the right
owner; ties the no to the shared goal (sprint goal, SLO, appetite);
says it *at planning or on receipt*, not by silently missing the date;
says no to his own scope creep too (a gold-plating PR gets flagged).
**Exercised in:** planning over-asks (~1 in 3 sprints), PM mid-sprint
scope changes, junior asking him to "just fix it", manager's
"can you also take on-call this week?".
**Example:** ✓ "I can't add CSV export this sprint without missing the
search goal. Two options: CSV next sprint (~3 blocks), or a 1-block
version now that dumps the current view only. Which matters more for
the customer call?"

### 5.6 Escalating

Sources: Google review deadlocks escalate to TL/EM and "Don't let a CL
sit around" ([eng-practices](https://google.github.io/eng-practices/review/reviewer/standard.html));
PagerDuty: "Never hesitate to page the IC"; severity: "if unsure, treat
it as the higher one" ([PagerDuty](https://response.pagerduty.com/before/severity_levels/));
Westrum generative culture: "Messengers trained", "Failure leads to
inquiry" ([DORA](https://dora.dev/capabilities/generative-organizational-culture/));
glue work and when to surface it to your manager
([Being Glue](https://noidea.dog/glue)).
**[unverified]** I did not find a single canonical industry source for an
"escalation template"; the form below is synthesised from the sources
above.

**Observable (graded):** escalates when a trigger is met — blocked >
1 workday on another person/team, conflicting asks from two people, a
risk to a commitment or to users — not before trying the direct route
and not after the deadline; writes it **neutrally** (both sides stated
fairly, no blame), with what he's tried, the decision needed, the
options and his recommendation, and the deadline for the decision;
copies the people involved (no going around them); records the outcome.
**Exercised in:** PM-vs-TL conflicts, a late platform-team dependency,
an incident he can't diagnose alone, a review deadlock.
**Example:** ✓ "@Dana (EM) need a priority call by Thu: Sam asked for the
cache rewrite this sprint, Lee asked for the export API; I can do one.
Cache: cuts p99 30%, no user asked. Export: blocks the Acme pilot on the
15th. I'd do export first. Sam and Lee are cc'd — both OK with you
deciding."

### 5.7 How these feed the perf review

Every rubric item above lands in the evidence ledger with a link to the
artifact. The review never says "communication: good"; it says "raised
'at risk' on INGEST-4 three days early with options (link)". This is the
legibility that big-tech calibration rewards and that a brag doc is for
([jvns.ca](https://jvns.ca/blog/brag-documents/)).


## 6. Pitfalls (and how Offer Letter avoids them)

What the research says, briefly: simulations work, and work well.
Chernikova et al.'s meta-analysis of 145 studies finds a large effect on
complex skills in higher education (g = 0.85), with scaffolding helping,
**examples** helping learners with low prior knowledge most, and
**reflection** phases helping those with high prior knowledge most
([Chernikova et al. 2020, RER](https://epub.ub.uni-muenchen.de/84298/)).
Serious games beat conventional instruction for learning (d = 0.29) and
retention (d = 0.36) but were **not more motivating**, and worked better
when supplemented with other instruction, used over multiple sessions,
and played in groups ([Wouters et al. 2013](https://research-portal.uu.nl/en/publications/a-meta-analysis-of-the-cognitive-and-motivational-effects-of-seri/)).
Simulation games raised self-efficacy (~20%), declarative (~11%) and
procedural knowledge (~14%) and retention (~9%), with strong signs of
publication bias (Sitzmann 2011, figures via
[Kapp's summary](https://karlkapp.com/?p=4333) — **secondary**). The
pitfalls below are where they fail.

| # | Pitfall | Evidence | Offer Letter rule |
|---|---|---|---|
| 1 | **Points, badges, leaderboards, XP** | Expected tangible rewards undermined free-choice intrinsic motivation (d = −0.28 to −0.40 by reward type) across 128 studies ([Deci, Koestner & Ryan 1999](https://depts.washington.edu/techdocs/papers/deciExtrinsicRewardsAndIntrinsicMotivation99.pdf)); a semester-long gamified course (badges + leaderboard) had *lower* motivation, satisfaction and exam scores than control ([Hanus & Fox 2015](https://doi.org/10.1016/j.compedu.2014.08.019)); gamification's average effects are small and unstable ([Sailer & Homner 2020](https://link.springer.com/article/10.1007/s10648-019-09498-w)) | **No XP, no leaderboard, no badges.** Rewards are in-world and informational: PR merged, a teammate's public credit, a harder project offered, a promotion with a written reason. Real jobs already have the right feedback loop; the sim just shortens it. |
| 2 | **"Chocolate-covered broccoli"** — a game wrapper around unrelated drills | The edutainment critique (term commonly traced to [Bruckman, "Can Educational Be Fun?", GDC 1999](https://faculty.cc.gatech.edu/~asb/papers/conference/bruckman-gdc99.pdf) — **attribution unverified**, PDF not machine-readable) | Every mechanic must be a real work practice (§1). The pixel office and visual-novel calls are *presentation*: always skippable, never gate work (no walking to a desk to start coding; one click to any room). |
| 3 | **Grind / repetition** | SimSE (software-process sim game): students found it "repetitive when played for extended periods", and it lacked an explanatory tool ([Navarro & van der Hoek, CSEET 2007](https://www.ics.uci.edu/~emilyo/papers/CSEET2007.pdf)) | Ritual time budget (§1.0); rituals with no new information are auto-skipped ("no standup today — nothing changed"); every recurring ritual must carry a plot beat or a decision; project shapes don't repeat within a stint. |
| 4 | **Sink-or-swim realism** for a learner | Minimal guidance is "likely to be ineffective" for novices ([Kirschner, Sweller & Clark 2006](https://www.davidlewisphd.com/courses/EDD8121/readings/2006-Kirschner_et_al.pdf)); SimSE players with no background improved least and none of them finished the assignment; Priority-First onboarding with early hard tasks "could spur fears and low confidence" ([Ju et al.](https://arxiv.org/abs/2103.05055)) | **Fading scaffolds:** worked example cards first (a parallel toy example, not his ticket), then hints on request, then reflection prompts only. First stint is growth culture with Simple-Complex onboarding; seed-startup "trial by fire" unlocks after one stint. |
| 5 | **No debrief** | In medical simulation, feedback "is the single most important feature… towards the goal of effective learning" and "the source of the feedback is less important than its presence" ([Issenberg & Scalese, BEME summary](https://laerdal.com/cdn-4adf0d/globalassets/documents/Issenberg_Scalese_Clinical_Teacher_BEME_Review.pdf)); SimSE needed its explanatory tool | **After-action review** after each ritual artifact and each project: what happened (timeline), rubric lines with quoted evidence, one thing to try next time. In-world (TL/EM comment) *and* out-of-world (a coach panel he can open). |
| 6 | **Feedback aimed at the person** | Feedback interventions improved performance on average (d = 0.41) but **lowered it in about a third of cases**; effectiveness drops as feedback draws attention toward the self and away from the task ([Kluger & DeNisi 1996](https://scholars.huji.ac.il/node/1802)) | Grade and comment on artifacts and behaviours ("the PR has no test evidence"), never traits ("you're careless"). Teammate feedback uses SBI (situation-behaviour-impact) form. |
| 7 | **Fake-feeling NPCs** — sycophantic, amnesiac, drifting, omniscient, always available | Sycophancy is a general behaviour of RLHF assistants ([Sharma et al.](https://arxiv.org/abs/2310.13548)); instruction drift within ~8 rounds ([Li et al.](https://arxiv.org/abs/2402.10962)); memory + reflection + planning drive believability ([Park et al.](https://arxiv.org/abs/2304.03442)) | §2.2–2.3: character sheets re-injected per turn, episodic memory, concession policy, planted-wrong pushback, **information boundaries** (the PM doesn't know the code; the junior wasn't in the incident), realistic reply latency and OOO. |
| 8 | **Nagging / controlling enforcement** | Controlling wording lowered perceived autonomy and was linked to stress in Reeve & Tseng's experiments (2011; known from secondary summaries — **original not read**); the same syllabus written in autonomy-supportive language raised autonomous motivation (d = 0.63) and lowered amotivation ([Herrera et al. 2025](https://www.frontiersin.org/articles/10.3389/fpsyg.2025.1536821/full)) | **Firm** = consequences are real and recorded (standup mention, perf-review line). **Fair** = rules published in week 0, PTO honoured, capacity-aware plans, no weekend anything. **No nagging** = one check-in per miss, informational wording ("PAY-112 was due Mon — what's the new date?"), never "you must"; no push notifications outside his scheduled hours; no streak-loss guilt screens. |
| 9 | **Unfair or opaque grading** (LLM judges) | LLM-as-judge shows position, verbosity and self-enhancement biases ([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)) | Harness checks first (tests, benchmarks, planted bugs); LLM judge only with a fixed rubric and quoted evidence per line; penalise padding (length limits per artifact); **he can appeal** a grade in writing and a fresh judge re-scores — the appeal is itself a "disagreeing well" exercise. |
| 10 | **Gaming the rubric** | (design risk, no specific study found — **unverified**) | Rubrics are public like a real ladder, but outcome checks (does the cold reader understand the doc? did the action item prevent the replayed incident?) dominate keyword-style checks. |
| 11 | **Simulating toxicity as "realism"** | Pushback in review is rare but costly and falls unevenly by demographics ([Egelman et al.](https://research.google/pubs/predicting-developers-negative-feelings-about-code-review/); [Murphy-Hill et al.](https://research.google/pubs/the-pushback-effects-of-race-ethnicity-gender-and-age-in-code-review/)); psychological safety predicts team effectiveness ([re:Work](https://rework.withgoogle.com/intl/en/guides/understand-team-effectiveness)) | Friction yes, disrespect never. Teammates can be blunt (OSS) or busy (big tech) but are always in good faith; no harassment or humiliation scenarios; persona traits never tied to demographics. |
| 12 | **Skills that don't transfer** | Games work better supplemented with other instruction ([Wouters et al.](https://research-portal.uu.nl/en/publications/a-meta-analysis-of-the-cognitive-and-motivational-effects-of-seri/)); SimSE "should not be used as a standalone tool" | All artifacts are real formats (git, Markdown docs, real PR descriptions, real benchmarks) he can show an interviewer; link each ritual card to the real source (Google eng-practices, SRE book) so he reads the original. |


---

## Appendix: verification notes

Read in the original (fetched page or PDF text): Google eng-practices
(standard, comments, speed, CL descriptions); SWE at Google ch. 9; Design
Docs at Google; Rust RFC README + template; Oxide RFD 1; HashiCorp RFC
template; KEP template; Google SRE postmortem culture + example
postmortem + workbook on-call; PagerDuty roles, during-incident,
severity levels, postmortem template, blameless guide; GitLab 1-1,
onboarding and communication handbook pages; Apache Way, lazy
consensus, voting; Kubernetes SIG governance (via search summary);
LLVM code review; Linux kernel submitting-patches; Scrum Guide 2020;
Yip standup patterns; Shape Up ch. 1; Ron Jeffries on story points;
Team Topologies key concepts; Dropbox IC2 + 2023 update; Julia Evans
(brag docs, good questions); Tanya Reilly "Being Glue"; Larson staff
archetypes; Radical Candor; CCL SBII; Amazon Leadership Principles;
Google tech-writing "Audience"; DORA generative culture; Ju et al.
2021 (PDF text); SimSE CSEET 2007 (PDF text); Issenberg & Scalese
BEME summary (PDF text); Herrera et al. 2025; Cloudflare 18 Nov 2025
postmortem (via search summary of the official post); Pragmatic
Engineer free posts (startup vs Big Tech, RFC roundup, Hiring from Big
Tech free part); PostHog small teams; Dan Webb.

Known from abstracts / search summaries only (numbers worth re-checking
before quoting in product copy): Sadowski et al. 2018 median < 4 h
(via a citing paper); Bacchelli & Bird 2013; Egelman et al. 2020;
Murphy-Hill et al. 2022; Rodeghero et al. 2021; Chernikova et al. 2020;
Wouters et al. 2013; Sitzmann 2011 (via Kapp); Hanus & Fox 2015; Sailer
& Homner 2020; Deci, Koestner & Ryan 1999 (effect sizes from abstract);
Kluger & DeNisi 1996; Kirschner, Sweller & Clark 2006; Sharma et al.;
Li et al.; Park et al.; Shaikh et al. (Rehearsal); Zheng et al. 2023
(from prior knowledge, not fetched this session); Google GRAD (press
reports); Meta bootcamp (one practitioner post + Blind threads);
Amazon 6-pager (CNBC + secondary); Reeve & Tseng 2011 (secondary);
"chocolate-covered broccoli" attribution to Bruckman (PDF not
machine-readable); Carta seed-team median (recruiting blog).

Not found / synthesised: a canonical escalation template (§5.6 is
synthesised); an authoritative norm for all-hands cadence (§1.12);
evidence on rubric-gaming in learning sims (§6 #10).
