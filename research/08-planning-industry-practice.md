# 08 — How working engineers plan and check a plan, and what that means for Offer Letter's planning stage

Research agent: planning-industry-practice. 2026-10-21.
Citation status: **[checked]** = I opened the URL this session and confirmed the
claim named. **[not re-checked]** = cited from memory or from
`04-workplace-realism.md`; the URL is believed right but I did not open it.
Where a claim is my own inference it says **(inference)**.
Overlap rule: `04` already covers the design-doc/RFC *review ritual*, estimation
in blocks, templates 4.1/4.2 and persona lenses. This file does not repeat them.
It covers the *individual's planning moves before coding*, and how each can be
checked.

---

## 0. What this means for Offer Letter's planning stage (15 lines)

1. **Plan by example first, not by diagram.** Example Mapping / test list → he writes 3–6 concrete input→output examples (one edge case, one error) before any steps. Mechanic: examples are typed into a table; the app turns them into runnable asserts. Real because every TDD/BDD shop starts here.
2. **Make the plan something that runs.** Plan = signatures + docstrings + `raise NotImplementedError` + the example asserts. The app runs the type checker and the examples against it. Real: type-driven design, "write the comments/stubs first", walking skeleton.
3. **Capture reasons with a fixed "because / instead of / would change if" line per decision.** ADR (Nygard) and MADR "considered options" in 3 lines. App rejects "I chose a dict" with no because.
4. **Predict, then run.** He predicts which existing tests fail, which call sites exist, the baseline number, the repro output. App runs the real thing and shows prediction vs reality. This fixes "validation was opinions".
5. **Read-first for existing code.** Change tickets start with "find the seam": he names the file/function and lists call sites; app verifies with grep/AST. Real: every senior's first move on a legacy change.
6. **A pre-mortem of exactly 3 failures**, answered before coding. Kit holds a hidden `plan_traps` list (like `answer_key.issues`); persona reacts to which he hit.
7. **Appetite, not estimate.** "This is worth 2 blocks; what is the smallest change meeting the acceptance criteria?" plus a no-gos line (Shape Up). Over-scope is flagged by comparing plan against the ticket's `size_hours`.
8. **Worked example of planning shown before he plans** (his stated need): a teammate posts a 12-line plan for a *different, finished* ticket in the same repo, with the reasoning visible. Each ticket type has one.
9. **Plan is a text file in his repo clone** (`PLAN.md` on his branch), reviewed by a teammate in a short thread like a mini design doc. Real: design docs live next to code.
10. **A "plan check" persona with one job:** ask the two questions a senior asks of a junior's plan ("what does this do on empty input?", "how will you know it works?") and stop. Not a grader of prose.
11. **Plan adapts by ticket type** (table in §12): perf needs baseline+hypothesis; incident needs repro-first; experiment needs tolerance+ablation; design needs alternatives. Skips the rest.
12. **Plans can change; drift is data, not failure.** After the change stage, the app diffs plan vs actual (files touched, functions added, examples that moved) and a persona asks "what surprised you?" No scoring against him. Real: blameless retros (Etsy/Allspaw).
13. **Spike is allowed and bounded.** If a step says "I don't know if X works", he may open a 20-minute scratch spike; its output is one sentence added to the plan. Real: XP spike.
14. **Smallest default plan = 7 boxes, 10–20 minutes** (§13), scaling by adding boxes, never by making boxes longer.
15. **Grade the plan by what it predicts and how reality answered**, not by wording. Automatic checks (§12) carry most of the weight; the persona handles only the judgment calls.

---

## 1. Design docs and RFCs at small scale

**What it is.** A short written proposal circulated before building. At Google
the norm is a design doc covering context and scope, goals and non-goals, the
design, alternatives considered, cross-cutting concerns; for incremental work a
1–3 page "mini design doc"; and, importantly, *don't write one when the solution
is not ambiguous* (Malte Ubl, [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/)
**[not re-checked this session; cited and quoted in 04 §1.6]**). Rust RFCs add
"Drawbacks", "Rationale and alternatives", "Prior art", and **"Unresolved
questions"** ([rust-lang/rfcs template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)
**[not re-checked]**). Oxide's RFD 1 says docs should be "timely rather than
polished" ([RFD 1](https://rfd.shared.oxide.computer/rfd/0001) **[not
re-checked]**). Gergely Orosz: write one for non-trivial projects, draft and
circulate before starting; engineers who do so ship more maintainable
architecture; Uber's RFC process (to about 2019) asked for approvers, SLAs,
dependencies, load testing, security, rollout, metrics
([Pragmatic Engineer, RFCs and design docs](https://blog.pragmaticengineer.com/rfcs-and-design-docs/)
**[checked]**).

**What part of planning it covers.** Shared understanding and early objection.
It is the *communication* layer; it does not by itself show the design works.

**Smallest useful note for a 1–5 hour change** (inference, distilled from the
above): five headings, 10–25 lines total.
1. *Problem in one sentence* (context).
2. *Done when* (the acceptance example(s)).
3. *Approach* (3–6 lines, naming the seam: file + function).
4. *Not doing* (non-goals/no-gos).
5. *Open questions* (Rust's "unresolved questions" — what I do not know yet).
Alternatives only when there is a real fork (otherwise one line "no real
alternative, because …").

**Mechanic for Offer Letter.**
- The plan stage's output is `PLAN.md` in his branch with exactly these five
  headings (plus per-type extras, §12). A heading with only placeholder text
  blocks submission (automatic).
- "Open questions" is a feature: he is *rewarded* (persona answers, in-world)
  for listing a real unknown, and the persona says "good catch, here's what I
  know" or "that one you can find by reading `x.py`". Never penalise a stated
  unknown; penalise an unstated one that the kit knows is a trap.
- Teammate persona (tech lead), 2–3 lines max: "I read your plan. You said
  you'd change `load_config`. Who else calls it? That's my only question."
- Skip rule, taken from Ubl: for a tiny, unambiguous ticket the plan collapses
  to the "done when" example + seam line (3 lines). The app shows this
  *shortcut* for tickets with `size_hours < 1`.

---

## 2. Architecture Decision Records

**What it is.** Michael Nygard's 2011 format: Title, Context (forces, in
value-neutral language), Decision ("We will …", active voice), Status,
Consequences (positive, negative and neutral), each "one or two pages", written
as a conversation with a future developer
([Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
**[checked]**). MADR adds **Considered Options**, optional Decision Drivers,
**Decision Outcome** with justification, per-option Good/Neutral/Bad pros and
cons, and an optional **Confirmation** section: "how compliance with the
decision will be verified, such as through a review or an automated test"
([MADR](https://adr.github.io/madr/) **[checked]**).

**What part of planning it covers.** *Why* a choice was made, preserved for
someone (including future-him) who will wonder. This is exactly the gap Luigi
found: his prototype "captured choices not reasons".

**Lightweight version.** One decision = three lines:
`We will X. Because Y. Instead of Z (rejected because W). Revisit if V.`
That is MADR's decision outcome + one considered option + "revisit conditions"
(MADR's "More Information" lists revisit conditions **[checked]**). Only for
decisions that are hard to undo or that a reviewer would ask about: typically 1–3
per ticket.

**Mechanic for Offer Letter.**
- Decision slots are structured: `choice`, `because`, `instead_of`,
  `would_change_if`. The app refuses empty `because`/`instead_of`.
- Automatic check (cheap): `because` must mention something from the world, not
  a tautology. Heuristic: contains a reference to a plan example, a file, a
  constraint from the ticket, or a measured number. Hard rule: fail "it is
  cleaner" alone; a persona then asks "cleaner how? Show me the call site that
  gets simpler."
- MADR "Confirmation" becomes the link between decision and check: each
  decision must name *which example or test would break if the decision were
  wrong*. This ties reasons to something that runs (his third complaint).
- Persona line (senior): "You said dict over a dataclass because it's simpler.
  What happens when a key is misspelled? Which of your examples would catch that?"
- After the ticket, the decision log is part of the retro (§11): "was the
  `would_change_if` condition triggered?"

---

## 3. Example Mapping, Specification by Example, the test list, invariants

**What it is.**
- **Example Mapping** (Matt Wynne, Cucumber): a ~25-minute conversation using four
  colours of card: yellow story, blue **rules**, green **examples**, red
  **questions**; too many red cards means the story is not ready
  ([Example Mapping intro](https://cucumber.io/blog/bdd/example-mapping-introduction/)
  **[checked]**).
- **Specification by Example** (Gojko Adzic, 2011 book): concrete examples as the
  shared specification that later become executable acceptance tests **[not
  re-checked; book]**.
- **Test list** (Kent Beck, "Canon TDD"): step 1 is to list the behavioural
  variants the change should cover, leaving out internal design decisions; then
  turn one item at a time into a test; add newly discovered cases to the list
  ([Canon TDD](https://newsletter.kentbeck.com/p/canon-tdd) **[checked]**).
- **Property-based thinking / invariants:** instead of one example, state a rule
  that must hold for all inputs (e.g. "decoding an encoded value returns the
  original"; "output is sorted and has the same elements"). Hypothesis docs:
  [hypothesis.readthedocs.io](https://hypothesis.readthedocs.io/) **[not
  re-checked]**; John Hughes, "How to Specify It!" (2019) on finding properties
  **[not re-checked]**.

**What part of planning it covers.** *What does done mean, concretely?* This is
the strongest anti-"vibes" move there is: if you cannot write one example with
an exact expected output, you do not understand the task.

**Lightweight version (15 minutes).** Four columns on a page:
`rule | example (input → expected) | question | status`. Needs at least: one
happy path, one boundary (empty/zero/one/max), one error (bad input / dependency
fails). One *rule in a sentence* per group of examples. Stop when red questions
are written down, not when they are answered.

**How examples become tests.** In Python this is nearly mechanical: each green
card is a `pytest.mark.parametrize` row or a doctest; each red card is an
`xfail`/`skip` with the question as reason; a rule that is universal gets one
Hypothesis property (optional, advanced tickets only, because it needs concepts
Luigi is still building (inference)).

**Mechanic for Offer Letter.**
- Plan section "Examples" is a table he fills in: `input | expected | why this one`
  (the `why` column forces the edge-case label: happy, boundary, error).
- The app compiles the table to `plan_examples_test.py` in his clone and runs it
  against the **existing** code. Result is shown *before he writes any
  implementation*:
  - Example passes already → "you've found existing behaviour; is it right?"
    (for change tickets this is a *characterization test*, Michael Feathers,
    *Working Effectively with Legacy Code* **[not re-checked; book]**).
  - Example fails → that is his to-do, and the failure message is his first
    concrete feedback.
  - Example errors (can't even be called) → his seam/signature is wrong; he fixes
    the plan.
- Automatic checks: ≥ 3 examples; ≥ 1 labelled boundary; ≥ 1 labelled error;
  no two examples identical in shape (cheap duplicate detection).
- Hidden: the kit has `plan_key.examples` — cases the real acceptance tests
  exercise. After he submits the plan, the app tells him "your examples cover
  2 of the 4 behaviours the grader will check; the uncovered ones involve:
  empty input, duplicate keys". It says **what kind**, not the answer. (Hint ladder
  matches the review stage's `hint_md`.)
- Persona line (QA-minded peer): "Your three examples all have non-empty input.
  What does the caller get if there's nothing?"
- Rules in a sentence: persona asks him to restate the rule in one sentence per
  group; app checks only that each group has one.

---

## 4. Pseudocode Programming Process, comments first, stepwise refinement, wishful thinking

**What it is.**
- **PPP** (Steve McConnell, *Code Complete* 2nd ed., ch. 9 **[not re-checked;
  book]**): write the routine's purpose and header, then pseudocode in plain
  language at the intent level (not syntax), review the pseudocode, convert each
  pseudocode line into a comment, write code beneath each comment, then check.
  Rule of thumb in the book: pseudocode describes *what*, not *how* in language
  terms.
- **Stepwise refinement** (Niklaus Wirth, "Program Development by Stepwise
  Refinement", *CACM* 14(4), April 1971, pp. 221–227): programming as a sequence
  of design decisions that break tasks into subtasks and data into data
  structures, with the eight-queens problem as the worked example
  ([search result confirming bibliographic details](https://blog.acolyer.org/2016/10/14/program-development-by-stepwise-refinement/)
  **[checked: details via search; paper not opened]**).
- **Wishful thinking** (Abelson & Sussman, *SICP* §2.1.1, rational numbers): code
  the caller as if `make-rat`, `numer`, `denom` already existed, then implement
  them ([SICP text](https://mitpress.mit.edu/sites/default/files/sicp/full-text/book/book.html)
  **[not re-checked; I could not confirm the exact phrase on the section page I
  opened, so treat the term as the lecture/book community's name for it]**).
- "Write the comments/docstrings first" is the lay version of PPP.

**What part of planning it covers.** Turning "what" into "what steps, with what
inputs and outputs" — the middle of Luigi's prototype (nouns → data, verbs →
steps, step contracts).

**Lightweight version.** Write the top-level function as ~5–8 lines calling
functions that do not exist yet. Name each helper so a stranger could guess what
it does. Each helper gets a one-line docstring and a signature. That is the
whole plan. If a helper's docstring needs an "and", split it.

**Mechanic for Offer Letter.**
- The "steps" part of the plan **is Python**, not prose: a `plan_skeleton.py`
  with real signatures, type hints, docstrings, and `raise NotImplementedError`.
  The top-level function's body is the wishful-thinking call sequence.
- The app *runs* it three ways (all automatic, no LLM needed):
  1. `python -m py_compile` / import: does it parse and import?
  2. `mypy`/`pyright` on the skeleton: do the output types of step N match the
     input types of step N+1? This is the machine-checkable version of his
     "data-flow map".
  3. AST walk: every helper called in the top-level function is defined; every
     defined helper is called (dead steps flagged); no function body is anything
     other than `NotImplementedError`/docstring (so he hasn't started coding
     under the cover of "planning").
- Teammate (senior) line: "Rename `process()`. If I only read your top function,
  would I know the order things happen in?" Judgment-only; capped at one.
- Refinement is explicit: a step may be marked `refine` and expanded one level
  down, allowed to a max depth of 2 for a ≤ 5 h ticket (more is over-planning).
- Hybrid: when the repo's code already has helpers, the plan marks each step
  `existing` (with a path) or `new`. App verifies `existing` ones are real
  (import and signature compatible).

---

## 5. Walking skeleton, tracer bullets, spikes, "make it work, right, fast"

**What it is.**
- **Walking skeleton** (Alistair Cockburn): "a tiny implementation of the system
  that performs a small end-to-end function"; it need not use the final
  architecture but links the main components. *Growing Object-Oriented Software,
  Guided by Tests* adds: the thinnest slice you can build, deploy and test
  automatically end to end ([summary of sources via search](https://henricodolfing.com/2018/04/start-your-project-with-walking-skeleton.html)
  **[checked via search result; Cockburn's own page not retrieved, a 404 on the
  URL I guessed]**).
- **Tracer bullets** (Hunt & Thomas, *The Pragmatic Programmer*): Tip 20, "Use
  Tracer Bullets to Find the Target"; contrasted with prototypes, Tip 21,
  "Prototype to Learn" ([tips list](https://pragprog.com/tips/) **[checked,
  tip numbers from the 20th-anniversary edition list]**). Difference that
  matters: a tracer is kept and grown; a prototype is thrown away.
- **Spike** (Extreme Programming): a time-boxed experiment to answer one
  technical question, thrown away; the outcome is an answer, not code
  ([extremeprogramming.org/rules/spike.html](http://www.extremeprogramming.org/rules/spike.html)
  **[not re-checked]**).
- **Make it work, make it right, make it fast** (Kent Beck's phrasing, widely
  attributed; sometimes credited to Butler Lampson/Stephen C. Johnson variants)
  **[attribution not re-checked]**.

**What part of planning it covers.** Ordering the work to reduce risk: do the
most uncertain integration first, thinly, and keep the result green.

**Lightweight version.** Step 1 of the *implementation* is always "the thinnest
path that makes ONE example pass", even if hard-coded. Everything else is added
example by example. A spike is allowed when a plan step contains "I don't know
whether".

**Mechanic for Offer Letter.**
- Plan field `first_slice`: "the one example I will make pass first, and which
  steps it touches". App checks it is one of his listed examples and touches ≤ 3
  steps.
- Ordering check (automatic, cheap): the first slice should include whichever
  step he marked `risky` (see pre-mortem, §6). If the risky step is last, the
  persona nudges: "Why do the riskiest part last?"
- Spike box: `spike: question | time-box (minutes) | what answer unblocks`. Time-box
  cap 20 minutes for a 1–5 h ticket. Output field `learned:` one sentence. App
  stores it; the persona reads it. Spike files are marked scratch and excluded
  from the change grader (so he can't be penalised for messy exploration).
- "Make it work/right/fast" shows up as stage order inside the change stage: the
  app can run the examples at "work" time, and the hidden grader later at
  "right". The perf ticket type inserts "fast" explicitly with measurements
  (§12).
- Tracer vs prototype distinction is taught once in the worked example (§0 item
  8), not quizzed.

---

## 6. Validating a plan before coding

This is the core of Luigi's third complaint. Practices, then the specific
"runnable" checks.

**6a. Desk checking / dry-running.** Walk a concrete example through the plan by
hand, recording the value of each variable after each step (a trace table). It
is old (structured-walkthrough practice) and exactly what his prototype's "trace
an example" step wanted. **[general practice; no single source re-checked]**
McConnell's *Code Complete* covers it under reviews/inspections (ch. 21)
**[not re-checked]**.

**6b. Pre-mortem.** Gary Klein, "Performing a Project Premortem", *HBR*,
September 2007: team members assume the project "has just failed", then
brainstorm believable reasons why; this makes it safe for people with doubts to
speak in planning ([HBR](https://hbr.org/2007/09/performing-a-project-premortem)
**[checked, abstract-level; the rest of the procedure is paywalled]**).

**6c. "What would have to be true."** Roger Martin's strategy question; for code
it becomes "for this approach to work, which assumptions must hold?" — each
assumption is a thing to check (read the code, run a query). **[general
practice; attribution to Martin not re-checked]**

**6d. Failure-mode listing.** For each external interaction (file, network, DB,
parse) list what goes wrong, how it is detected, what the user sees. Public
checklists to borrow items from: Kubernetes KEP Production Readiness Review
(rollout/rollback, monitoring, troubleshooting)
([KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md)
**[not re-checked; cited in 04]**); Google's code review "what to look for"
list, which includes design, functionality (explicitly "think about concurrency
problems"), complexity (be vigilant against over-engineering: "solve the problem
they know needs to be solved now"), tests, naming, comments
([Google eng-practices](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
**[checked]**).

**6e. Rubber-duck review.** Explaining the plan aloud to someone (or something)
that asks naive questions surfaces gaps. *The Pragmatic Programmer* describes
rubber-ducking as a debugging technique **[book, not re-checked]**. Offer
Letter already has the explain-it-back stage; applying that to the *plan* is a
natural reuse.

**6f. Plan mode in AI coding agents.** Claude Code's plan mode: "Claude reads
files and proposes a plan but makes no edits until you approve"
([Common workflows, Plan before editing](https://code.claude.com/docs/en/common-workflows)
**[checked]**). The validation there is human approval of a *text* plan, with
the agent having first read the code. Nothing executes the plan; the safeguard
is separation of read-only exploration from write. **(inference)** Cursor and
other tools have comparable "plan" or "spec" steps; I did not check them. Lesson
for Offer Letter: the step that adds value is *read-only exploration before
proposing*; the weak part is that approval is by opinion — exactly Luigi's
critique. So: copy the read-first separation, replace approval-by-opinion with
the runnable checks below.

**What part of planning it covers.** Finding wrong assumptions while they are
cheap.

**Lightweight version (≤ 10 min).** Three things only: (1) trace one example
through the skeleton on paper; (2) write exactly three "it failed because …"
sentences; (3) mark each assumption `verified` (I ran/read it) or `unverified`.

**Mechanics for Offer Letter: "plan checks that run".** Ranked by how
mechanical they are:

| # | Check | Runs what | Verdict source |
|---|---|---|---|
| 1 | Skeleton imports and type-checks | py_compile + mypy/pyright | automatic |
| 2 | Data-flow closure: every step's inputs are given or produced earlier (his own `inputs/outputs` declarations vs AST names) | AST | automatic |
| 3 | Examples run against existing code; predictions compared | pytest on `plan_examples_test.py` | automatic |
| 4 | Call-site list matches reality (he lists callers; app greps/AST-finds callers; shows missing and bogus) | `ast`/ripgrep | automatic |
| 5 | Trace table: he fills expected variable values for one example at each step; app executes the *existing* code under a tracer on that example where the steps already exist and diffs | `sys.settrace` / `pdb`-style trace | automatic where code exists; otherwise persona |
| 6 | Assumption list: each `verified` assumption must cite a command or file:line; app re-runs the command / confirms the line exists | shell, file read | automatic (existence), persona (meaning) |
| 7 | Pre-mortem vs hidden `plan_traps` | compare tags | semi-automatic (LLM grader classifies his 3 sentences against trap tags; separate grader call, as the explain stage does) |
| 8 | Desk-check challenge: persona gives one *new* input he did not list and asks "what does your plan do?" | persona + reference behaviour | persona + app (the reference impl produces the true answer) |

Check 8 is the "rubber duck that has a reference solution", only possible
because the kit has a server-only `reference/` fix (ARCHITECTURE §5). The
persona can truthfully say "that would return `[]` in the real system" without
inventing.

Persona lines: skeptical senior on pre-mortem: "You listed 'bad input'. Which
function gets the bad input first, and what does it do with it?"

---

## 7. Type-driven and contract-driven design

**What it is.**
- **Design by Contract** (Bertrand Meyer, *Object-Oriented Software
  Construction*, 1988/1997; Eiffel): each routine has preconditions (caller's
  obligation), postconditions (routine's promise), and class invariants **[book;
  not re-checked]**. Pragmatic Programmer devotes a topic to it **[not
  re-checked]**.
- **Make illegal states unrepresentable** (Yaron Minsky, Jane Street, "Effective
  ML Revisited", 2011): instead of a record with many optional fields that allows
  impossible combinations, use a variant where each state carries only its own
  fields ([blog](https://blog.janestreet.com/effective-ml-revisited/)
  **[checked]**).
- **Parse, don't validate** (Alexis King, 2019): checks on input are most useful
  when they produce a more precise type that keeps what was learned, instead of
  returning a boolean and discarding it
  ([blog](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
  **[checked]**).
- **Signatures as plans:** in typed languages a function's signature is already
  a contract the compiler enforces; the plan's "step contracts" are signatures.

**What part of planning it covers.** The "data kinds" and "step contracts"
sections of his prototype: what shapes exist, what each step may assume, who
owns what.

**In Python (his language).**
- Type hints + `mypy --strict`/pyright on a skeleton: output of step N must be
  accepted by step N+1. Catches missing `Optional` handling (the "can it fail?"
  column) — pyright reports "possibly None".
- `@dataclass(frozen=True)` for a value that must not change; `enum.Enum` or
  `Literal["open","closed"]` for a closed set of states; a tagged union as
  `A | B | C` of dataclasses, and `match` with `assert_never` for exhaustiveness
  (mypy/pyright report a missed case). This is Minsky's idea in Python.
- `Protocol` for "anything with these methods" at a seam (lets a test pass a
  fake); `NewType` for ids that must not be mixed up.
- `async def` signatures show what awaits: the plan can state "this step does
  I/O, so it is `async`; its callers must be too" — a real planning consequence
  (inference).
- Runtime parse step at the boundary: build the precise type from raw input
  once (pydantic or a hand-written `parse_x(raw) -> X | ParseError`), and
  everything after takes `X` (King).
- Contracts as `assert` or small `require()` helpers; or `icontract`/`deal`
  libraries **[not re-checked]**.

**In Rust (if he moves there).** Ownership is in the signature: `&T` read only,
`&mut T` exclusive write, `T` consumed, `Result<T, E>` can fail, `Option<T>` may
be absent. A plan sketched as `fn` signatures + `todo!()` bodies compiles
(`cargo check`) and the borrow checker already tells him if a data-flow plan is
impossible. Enum variants carry per-state data (Minsky's pattern, natively).
Offer Letter currently ships Python repos (kit graders are pytest, §5), so Rust
is a later extension (inference).

**Lightweight version.** Skeleton with types + one `Literal`/`Enum` for each
"mode" and a rule "no `Optional` field whose presence depends on another field".

**Mechanic for Offer Letter.**
- "Can it fail? how?" in the step contract maps to the return type: `X |
  None`, raises `E`, or `Result`-like. App checks the declared answer agrees with
  the type (e.g. "can't fail" but returns `X | None` → flagged; "can fail" with
  return type `X` and no `raises:` docstring → flagged). Automatic.
- "Ownership" = who may mutate. App lists, via AST, which parameters a step
  mutates (assigns to attributes/items, calls `.append`, etc.) vs what he
  declared. Heuristic, so output is "I see `rows.append` in step 3; you
  declared rows read-only. Intentional?" Not a failure.
- Illegal-states prompt, persona (type-minded peer): "Your `Job` has `error` and
  `result` both optional. Can both be set? Can neither?" Only if the AST shows
  that pattern (a dataclass with ≥ 2 `Optional` fields). Automatic trigger,
  persona wording.
- Quiz tie-in: after the ticket, one question from King/Minsky applied to the
  code he just wrote (fits the existing quiz stage).

---

## 8. Estimation and scoping inside a plan

**What it is.**
- **Shape Up** (Basecamp, Ryan Singer): **appetite** is "the amount of time we
  want to spend", not an estimate ([ch.1](https://basecamp.com/shapeup/0.3-chapter-01)
  **[cited in 04]**); **rabbit holes** are parts "too unknown, complex, or
  open-ended to bet on" that can stretch work to several times its appetite;
  shapers *patch* a hole by dictating a simpler solution in advance; **no-gos**
  are use cases explicitly declared out of bounds
  ([ch.5 Risks and Rabbit Holes](https://basecamp.com/shapeup/1.4-chapter-05)
  **[checked]**).
- **Slicing to ≤ 1 day** (Ron Jeffries, "Story Points Revisited", cited in 04).
- **Smallest change that satisfies the acceptance criteria:** Google's reviewers
  are told to push developers toward solving "the problem they know needs to be
  solved now" and be vigilant about over-engineering
  ([Google eng-practices](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
  **[checked]**); YAGNI from XP **[not re-checked]**.

**What part of planning it covers.** Keeping the plan inside the time that is
available, and naming the traps.

**Lightweight version.** Three fields: `appetite` (blocks), `no-gos` (≥ 1),
`rabbit hole + patch` (≥ 1: "X is unknown; I'll patch it by doing the simpler Y").

**Mechanic for Offer Letter.**
- `appetite` is pre-filled from the ticket `size_hours` but he writes his own in
  30/60/90-minute blocks, per 04 §1.4. App compares: if the number of plan steps
  × a rough per-step cost (kit-defined, e.g. 20 min) exceeds appetite, banner
  "Your plan has 9 steps; at ~20 min each that's 3 h against a 90-minute
  appetite. Which step is the first to cut?" Automatic arithmetic, persona
  wording, he answers.
- "Smallest change" check: after the change stage, the app measures the diff
  size against the reference fix (files/lines). If > 3× the reference, the
  retro asks about it (not a failure). Before coding, the plan's `files_to_touch`
  list is compared with the reference's file set: extra files flagged ("you plan
  to touch `db.py`; the grader never calls it").
- Persona (PM-ish): "Is the CSV export in scope, or can I tell the customer it's
  next sprint?" He must say in or out, with a reason. Fits the no-gos field.
- Splitting rule for bigger tickets: a plan with > 4 blocks must be sliced into
  slices each with a "done when" example (04 already adopted Jeffries' rule; this
  is where it is applied).

---

## 9. Writing to think; what senior reviewers look for in a junior's plan

**What it is.**
- **Daybooks / engineering notebooks** (Hunt & Thomas): keep a log of what you
  tried and decided; the *Pragmatic Programmer* recommends engineering daybooks
  and writing things down (tip on "Build Documentation In" is #13 in the tips
  list I checked; the daybook passage itself **[not re-checked]**).
- **PR descriptions as visible reasoning:** Google's guide stresses that a CL
  description should say *what* and *why*, and reviewers read it first
  ([CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
  **[not re-checked]**). Teams put "why this approach, what I rejected, how I
  tested" in the description.
- **Staff-level writing habits:** Will Larson, *Staff Engineer* and
  [staffeng.com](https://staffeng.com/) (writing, "Technical quality", design
  review guides) **[not re-checked]**; Orosz's Pragmatic Engineer pieces on
  design docs **[checked: RFC article only]**.
- **What reviewers look for in a junior's plan** (synthesised; **inference**
  from the Google reviewer list above plus Ubl's and Shape Up's guidance, not a
  single source):
  1. Did they look at the existing code first (names the real seam)?
  2. Is the problem stated in their own words and the done-state testable?
  3. Edge/error cases listed before being asked?
  4. Is it the smallest change? Did they avoid building for imagined futures?
  5. Do they know what they do not know (open questions), and a plan to find out?
  6. Do the steps connect (no step uses data no earlier step produced)?
  7. How will they know it worked, and how will someone else?
  8. Rollback / blast radius (for production-like tickets).
  9. Is the plan short enough to be read?
  Also in the ask: *not* polish, not diagrams, not a specific framework.

**Lightweight version.** A running `NOTES.md` in the branch: timestamped one-line
entries "tried X → saw Y → so Z". Done while working, not after. The plan is its
first entry.

**Mechanic for Offer Letter.**
- The plan stage creates `PLAN.md`; the change stage keeps a `WORKLOG.md`. Both
  are committed on his branch; the PR description (auto-scaffolded with headings
  Why / What / How I tested / What I'm unsure about) is filled by him.
- A reviewer persona's checklist is the 9 items above, but in **one comment, not
  nine**. Rule: max 2 questions per plan review; the senior picks the two most
  important (the app supplies the list ranked by what failed the automatic
  checks).
- Visible reasoning scoring: "Why" lines present for each decision (§2) —
  automatic presence check; quality judged only by whether the later retro shows
  the reason survived contact with the code.
- Worklog prompt at the end of each work block (existing clock-out flow): "One
  line: what did you learn?" Stored. No grading.

---

## 10. Planning per ticket type

The plan stage is one frame with type-specific slots. Below, what a good plan
looks like per type, with sources where I have them.

### 10a. Change request to existing code (add-your-part, change-after-review, review-to-own)
**Good plan:** (1) restate in one sentence; (2) read the code path *before*
planning: entry point → the function that needs to change; (3) **find the
seam**: the smallest place where behaviour can change without touching
unrelated code (Feathers' term "seam", *Working Effectively with Legacy Code*
**[book; not re-checked]**); (4) list call sites of anything whose signature or
behaviour changes; (5) characterize current behaviour with an example or two
before changing; (6) examples of the new behaviour; (7) what can break (callers,
tests, config); (8) smallest edit that works.
**Source support:** Google design/functionality review criteria ([checked](https://google.github.io/eng-practices/review/reviewer/looking-for.html));
"Make the change easy, then make the easy change" (Kent Beck tweet, 2012)
**[not re-checked]**.
**Auto-checkable:** seam exists (file:function resolves); call-site list vs AST
(precision/recall shown); examples run on existing code; files-to-touch vs
reference.
**Persona:** "Who calls this? Check `grep -rn load_config .` and tell me if you
missed any."
**Needs running code:** characterization tests; callers' tests still green.

### 10b. Perf ticket
**Good plan:** a **hypothesis** ("the time is in the JSON parse inside the
loop"), a **baseline measurement** with the command and its noise (run 5 times,
report min/median), an **expected gain** with a reason ("parse is 60% of time →
caching it can save up to 60%"), a **measure-after** plan with the same command,
and the **profile first** step (cProfile / py-spy). Source thinking: Amdahl's
law for expected gain; Brendan Gregg's methodology pages
([brendangregg.com/methodology.html](https://www.brendangregg.com/methodology.html)
**[not re-checked]**) for "measure before tuning"; Knuth's "premature
optimization" quote from *Structured Programming with go to Statements* (1974)
**[not re-checked]**; "make it right before you make it fast" (§5).
**Auto-checkable:** he must paste a baseline number from a command; the app
re-runs the command in his clone and checks the number is the same order of
magnitude (±noise, e.g. 3×); the hypothesis must name a function that exists
and, if profile data is available, appears in the top N. Expected gain
arithmetic sanity (cannot exceed Amdahl bound derived from his own profile
numbers).
**Persona:** "You said parse is 60% of runtime. Where did that number come from?
Show me the profile line."
**Needs running code:** the measurement; the correctness examples must still pass
after the change.

### 10c. Incident fix
**Good plan:** **repro first** (a failing test or script before any fix),
**timeline** (what changed, when it started: from `git log`/deploy), **trigger
vs root cause** (the trigger is what set it off; the root cause is the latent
condition: e.g. trigger = traffic spike; cause = unbounded cache), a
**mitigation vs fix** distinction (stop the bleeding vs correct), **how we will
know it is fixed**, and **what would have caught it**. Sources: Google SRE book
postmortem chapter ([sre.google/sre-book/postmortem-culture](https://sre.google/sre-book/postmortem-culture/)
**[not re-checked; 04 cites SRE]**); Etsy's blameless post-mortem debriefing
guide ([Debriefing Facilitation Guide PDF](https://extfiles.etsy.com/DebriefingFacilitationGuide.pdf)
**[URL resolves to a PDF; I could not read its text, so the contents are not
verified]**).
**Auto-checkable:** repro test fails on the broken commit (app runs it); the
same test passes after (that's a completed check); timeline entries link to real
commits (`git rev-parse`).
**Persona (on-call lead):** "Did you reproduce it before you changed anything?
Show me the failing run."
**Needs running code:** the repro, and regression.

### 10d. Design ticket
**Good plan:** this *is* a design doc: problem, goals/non-goals, two real
alternatives with reasons, failure modes, rollout/rollback, open questions —
04's §4.1 template. The "plan" stage is thin because the ticket's output is the
doc; a *mini-plan* is "what questions must the doc answer, and who will I ask".
**Auto-checkable:** sections present; each alternative has a rejected-because;
numbers (limits, sizes) appear if the ticket gives load figures; the doc names at
least one existing component by file/module (grounding).
**Persona:** reviewers by lens (04 §1.6).
**Needs running code:** nothing, unless the ticket says "include a benchmark" or
a sketch interface that the app type-checks (§4).

### 10e. Paper-reproduction experiment
**Good plan:** the claim to reproduce (one sentence with the paper's number and
table), the **baseline** (what simple thing we compare against), the **metric and
tolerance** (e.g. "within 2 points of the paper's 71.3"), the **seeds/runs** to
average over, the **ablation** (remove one component and see the effect), the
**compute budget**, and the **stop rule** (if off by more than X after Y, write
up why rather than keep tuning). References on practice: Joelle Pineau's ML
Reproducibility Checklist (NeurIPS 2019) **[not re-checked]**; Andrej Karpathy,
"A Recipe for Training Neural Networks" (2019, start simple, overfit one batch,
verify the loss at init) **[not re-checked]**; the paper-idea bank in
`06-paper-idea-bank.md`.
**Auto-checkable:** tolerance is a number; baseline and metric commands exist;
the seed list is non-empty; after the run, observed vs tolerance is computed by
the app; compute budget vs the machine (ticket-provided).
**Persona (research lead):** "If the number comes out 3 points low, what do you
change first, and what would tell you it's a bug versus noise?"
**Needs running code:** all outcomes; the plan's value is the pre-registered
tolerance (**inference**: pre-registration analogy; keeps him honest).

### 10f. Build (greenfield small feature) and incident are covered; build in brief
**Good plan:** walking skeleton first slice (§5), examples table, step
skeleton, failure modes, test list. Same default plan (§13) without the
call-site/seam parts.

---

## 11. Plan-versus-actual retros ("plan drift")

**What it is.** After the work, compare what was planned to what happened and
learn from the gap without blaming. Relevant sources:
- Blameless post-mortems (Etsy, [Allspaw, "Blameless PostMortems and a Just
  Culture"](https://www.etsy.com/codeascraft/blameless-postmortems/) **[not
  re-checked]**; Google SRE postmortem chapter **[not re-checked; in 04]**).
- Agile **sprint retrospective** (Esther Derby & Diana Larsen, *Agile
  Retrospectives*) **[book; not re-checked]**; 04 §1.9 already covers the ritual.
- *Hindsight bias* caution: judging decisions by outcomes. The Etsy guide
  discusses avoiding counterfactual blame **[not verified, PDF unreadable
  here]**.
- Planning fallacy (Kahneman & Tversky) as the reason plans run short
  **[not re-checked]**.

**What part of planning it covers.** Calibration: the only way to get better at
planning is to see how past plans fared.

**Lightweight version.** Five minutes at the end of the ticket, three lines:
- *What matched the plan?*
- *What did I not expect?* (and where in the plan was the assumption?)
- *What would I put in the plan next time?*

**Mechanic for Offer Letter.**
- **Plan drift report**, produced automatically from the plan and the final
  branch (no judgment):
  - planned files vs touched files (added, missing);
  - planned helper functions vs those that exist in the diff;
  - plan examples: passed first run, passed finally, never passed, modified
    during work (examples edited after the plan are "learned something");
  - planned appetite vs actual blocks (from the clock);
  - decisions whose `would_change_if` condition appears to have triggered
    (user-confirmed);
  - pre-mortem items that occurred (user-confirmed) and traps he missed that
    bit (hidden `plan_traps` that correspond to a failing hidden test).
- Persona leads a 3-minute retro in blameless style: "Your plan said touch two
  files; you touched five. Walk me through the first extra one." Rule: persona
  asks about *the plan's assumption*, never about *him*. Use 04's after-action
  review principle (feedback on the work, not the person).
- Calibration line over time: "In 6 tickets, you finished within appetite 4
  times; you underestimate tickets that touch the DB layer." No scores, no
  streaks.
- Drift is *celebrated* when he changed the plan on purpose and wrote why (a
  worklog line). Silent drift (touched files not in plan, no worklog entry) is
  the only thing flagged.

---

## 12. Table: ticket type → plan moves → who checks what

Legend. **A** = automatic (script/AST/tests, no LLM). **P** = teammate persona
(judgment, one or two questions). **R** = only by running code (the real
system or hidden grader). "skip" = not required for that type.

| Plan move | Change request / review-to-own | Add-your-part / build | Perf | Incident | Design | Experiment (paper) |
|---|---|---|---|---|---|---|
| Restate task + done-when example | required: A (≥1 example runs) | required: A | required: done-when = metric target | required: failing repro = done-when | required: "questions the doc must answer" | required: claim+number |
| Read-first: seam + call sites | **required**: A (grep/AST) | needed for the existing-code part: A | profile first: A (profile output present) | timeline + suspect code: A (commits exist) | name 1+ existing components: A | skip (read paper, A: cites section) |
| Examples incl. boundary + error | required: A runs on existing code | required: A | correctness examples must still pass: R | the repro + 1 regression example: A, R | skip (use scenarios): P | skip (use tolerance/ablation) |
| Step skeleton (signatures) | required: A (type-check) | required: A | optional (only if restructure) | optional | optional sketch: A (type-check) | optional: experiment script outline |
| Step contracts (fail/ownership) | brief: A | required: A | skip | skip | interface only | skip |
| Decision lines (because/instead) | 1–3: A presence, P quality | 1–3: A, P | 1–2 (why this optimization): A, P | 1 (mitigation vs fix): A, P | **required**, most: A, P | 1–2 (why this baseline): A, P |
| Hypothesis + baseline measurement | skip | skip | **required**: A (re-run baseline) | root cause hypothesis: P; repro: A/R | skip | baseline: A, R |
| Expected gain / tolerance | skip | skip | **required**: A (Amdahl sanity) | skip | numbers if given: A | **required**: A (number), R (result) |
| Pre-mortem (3 failures) | required: P vs hidden traps | required: P vs traps | required: P (noise, cache warm-up) | 1 line "how could the fix mask it?": P | required: P | required: P (leakage, seed) |
| First slice / walking skeleton | required: A | required: A | skip (instrumentation first) | skip (repro first) | skip | required: tiny end-to-end run: R |
| Appetite + no-gos | required: A arithmetic | required: A | required (stop rule): A | required (time box to mitigate): A | required | required (stop rule): A |
| Spike allowed | yes, 20 min | yes | the profile *is* the spike | yes (to repro) | yes | yes (small-data run) |
| Teammate reads plan | tech lead, 2 questions | peer + lead | perf-minded senior | on-call lead | reviewers by lens | research lead |
| Plan-vs-actual retro | files, call sites, examples | files, helpers, examples | predicted vs measured gain: A | timeline vs actual cause: P | doc revision log (04) | tolerance vs observed: A |
| **Only running code can tell** | callers' tests; hidden grader | hidden grader | real speedup, no regression | repro fails→passes | nothing (human judgment) | whether number reproduces |

What a persona is *not* used for: checking that something exists, parses,
type-checks, or that a number matches a re-run. Those are scripts. Personas ask
the question a script cannot: "is this the right seam", "is this reason
believable", "what did you not think of".

---

## 13. Smallest default plan: 10–20 minutes for a 1–5 hour ticket

Seven boxes. Each is small; none may be a paragraph. Order matters: read first.

1. **Read (3–5 min, not typed):** open the files on the code path. Output: `seam:
   <file>::<function>` and `callers: [...]` (for change tickets) or `where I'll
   put it: <file>` (for build). *Check A.*
2. **Restate (1 min):** "Given ___, produce ___." One sentence. *Check A:
   present, ≤ 40 words. Persona sees it.*
3. **Examples (4–5 min):** table, 3–6 rows, each labelled happy / boundary /
   error, plus one line "rule" per group. *Check A:* ≥ 3, labels present;
   compiled and run against existing code; shows pass/fail/error now.
4. **Skeleton (4–5 min):** signatures with type hints and docstrings, top
   function written as the sequence of calls, bodies `raise NotImplementedError`.
   *Check A:* imports, type-checks, data-flow closure, no early implementation.
5. **Decisions (2 min):** 1–3 lines, each `choice / because / instead of /
   would change if`. *Check A presence; P quality.*
6. **Pre-mortem (2 min):** exactly three "it failed because …". *Check P versus
   hidden traps.* Plus mark one step `risky` and put it in the first slice.
7. **Scope (1 min):** `appetite` (blocks), `no-gos` (≥ 1), `first slice` (one
   example). *Check A arithmetic.*

Then the plan review: persona reads it, asks **at most two** questions, he may
answer or revise; the stage passes when automatic checks are green and he has
replied to the persona (not when the persona approves, to avoid sycophancy-style
"approval by opinion"; if he reasonably disagrees and says why, that counts,
per 04 §2.3 concession policy).

**Per-type additions** (each ≤ 2 extra minutes):
perf adds `hypothesis`, `baseline command + number`, `expected gain`;
incident adds `repro`, `timeline`, `trigger vs cause`; experiment adds `claim
number`, `tolerance`, `ablation`, `stop rule`; design swaps boxes 3–4 for
alternatives + failure modes.

**Scaling up.** Plans get *more boxes*, not longer ones:
- 5–15 h ticket (build, small project): add "failure modes" per external
  interaction (6d), alternatives for any decision that is expensive to undo
  (MADR with considered options), slice into ≤ 4-block slices each with its
  own done-when (8), and a short "rollout/rollback" line (04 §4.1).
- 15–40 h (design + build, milestone project): promote `PLAN.md` to the 04 §4.1
  mini design doc; asynchronous review by 2–3 persona lenses; the skeleton
  becomes a walking skeleton that actually runs end to end (5); a milestone plan
  with a plan-drift check at each milestone.
- < 1 h ticket: collapse to boxes 1–3 and 7 (about 5 minutes). Ubl's "don't
  write one when the solution is not ambiguous" is the justification.

---

## 14. Answers to Luigi's three prototype problems

1. **"No worked example of planning."** Ship a `plan_example.md` per ticket type
   in the company pack (parallel toy ticket in the same repo, already finished:
   the plan, then the diff, then the drift report). The tech lead posts it in the
   first message of each ticket type: "Here's how I planned the retry fix last
   month." The example is *shown*, not required reading; the pass criterion is
   that his plan uses the boxes (no copying check, since toy tickets differ).
   This matches his learn-by-example preference and mirrors how real teams share
   past design docs and PRs as templates (Oxide/Rust RFC repos are literally
   libraries of examples).
2. **"Captured choices not reasons."** Decision lines with `because / instead of
   / would change if` (§2) and the MADR "confirmation" link to an example that
   would break (§2, §3). Reasons are re-examined in the retro (§11).
3. **"Validation was opinions, not anything that ran."** The eight checks in
   §6: skeleton type-check, data-flow closure, examples run against existing
   code, call-site verification, trace-table diff, command-backed assumptions,
   hidden `plan_traps`, and reference-backed desk-check challenges.
   *Prediction-vs-reality* is the heart: whenever he predicts something (which
   examples fail now, the baseline, who calls this), the app runs it and shows
   the diff.

---

## 15. Kit and architecture implications (for the builder, not part of the plan UX)

(Inference; keep small. ARCHITECTURE §4–§5 only describe the review-to-own flow:
`review → quiz → explain → change → own → done`.)
- Add an optional `plan` stage before `change` (and for non-review types, as
  stage 1). `ticket.json.stages` already lists stages per ticket, so the stage
  list can carry it: `["plan", "change", ...]`. The unlock rule (previous
  stage_result passed) already exists.
- Suggested endpoints (names only): `GET/POST /tickets/{id}/plan`, `POST
  /tickets/{id}/plan/check` (returns the 8 check results as `[{id, ok, detail}]`
  in the same shape as `setup-check`), `GET /tickets/{id}/plan/drift`.
- Kit additions: `plan_key.json` = `{seam, callers[], examples_behaviours[],
  traps[], no_gos[], expected_files[]}`; `plan_example.md`. `verify_kit.py` can
  check that `seam` and `callers` resolve in the repo and that
  `expected_files` equals the reference fix's file set, so the plan key cannot
  rot.
- Checks 1–6 in §6 are plain Python (py_compile, mypy/pyright, ast, subprocess
  pytest) and need no model call; only #7 and persona turns do. That keeps the
  plan stage cheap on the 5-hour usage limit (see memory note on session
  limits) and testable offline.
- Pass bar suggestion: all automatic checks green, ≥ 3 examples, 1 reply to the
  persona. No numeric prose score.

---

## 16. Source index (status)

Checked this session: Example Mapping (Wynne, Cucumber); Canon TDD (Beck);
Nygard ADR; MADR; Parse, don't validate (King); Effective ML Revisited (Minsky);
Klein HBR premortem (abstract); Shape Up ch.5; Google eng-practices
"what to look for"; Claude Code common workflows (plan mode); Pragmatic
Engineer RFC article; Pragmatic Programmer tips list (tips 20, 21 numbers); the
Wirth 1971 bibliographic details and the walking-skeleton definition (via search
summaries).

Not re-checked (cited from memory or from `04`): Ubl design docs; Rust RFC
template; Oxide RFD 1; KEP template; Jeffries; McConnell *Code Complete* ch. 9
and ch. 21; Adzic; Feathers; Meyer; Hunt & Thomas daybooks and rubber duck
passages; SICP wishful-thinking phrase location; XP spike page; Gregg; Knuth;
Pineau checklist; Karpathy recipe; Etsy blameless post-mortems article and
Debriefing Guide contents; Derby & Larsen; Kahneman & Tversky; Roger Martin
attribution; "make it work, right, fast" attribution; Google CL descriptions page;
staffeng.com.
