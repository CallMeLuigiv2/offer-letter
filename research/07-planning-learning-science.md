# 07 - Learning science for a planning stage ("think like a programmer before implementing")

Author: research agent, 2026-10-21. For: Offer Letter planning stage (successor to RustPlease).

## How to read this file

**Verification status.** I could only verify a few sources live this session. Tags used in every source line:
- `[verified]` = I confirmed title/authors/venue/key finding via a live search or fetch this session.
- `[not re-checked]` = cited from memory of the literature; the paper exists to the best of my knowledge, but the exact numbers or DOI should be checked before anyone quotes them. I give effect sizes only where I am fairly sure, and I say "about" or "I recall".
- Nothing here is invented on purpose. If a claim has no source I say "no direct evidence" or "my inference".

**Strength labels.**
- `META` = meta-analysis or large systematic review.
- `EXP` = controlled experiment or classroom RCT (one or a few studies).
- `OBS` = observational / think-aloud / qualitative / design-based.
- `THEORY` = established theory with experimental backing but not tested on this exact use.
- `OPINION` = practitioner or expert view.

**The learner.** Adult, intermediate Python, learning Rust/C++, wants an AI-infra job, prefers clicking to typing, learns from worked examples on a parallel toy, restarts rather than finishes. Most evidence below is from novices (CS1). Intermediates differ: see the expertise reversal effect (topic 3). Where a finding is novice-only I say so.

---

## A. What this means for the planning stage (15 lines)

Format: mechanic -> evidence -> strength.

1. **Show a planning worked example before he plans, on a parallel toy, in the same UI he will use.** Narrate stage names and the "why" of each move. -> Worked-example effect; subgoal-labelled examples beat unlabelled ones; cognitive apprenticeship "modeling". -> META (worked examples) + EXP (subgoals) + THEORY.
2. **Fix a short list of named stages (about 5-6) and show the current stage always.** E.g. Restate -> Examples -> Data -> Steps -> Run it -> Compare. -> Loksa et al. CHI 2016: explicit stage guidance raised productivity and self-awareness for novices. -> EXP (one study, n about 44).
3. **Every stage carries a one-line "what am I doing / why / how does it help" prompt**, answered by a click or short phrase, not an essay. -> Loksa 2016 prompts; self-explanation. -> EXP + META (self-explanation).
4. **Restate the brief and work one concrete example BEFORE designing.** -> Prather et al. SIGCSE 2019: scaffold to interpret the prompt and solve a test case first improved comprehension and task success. -> EXP.
5. **Write examples first and make them executable.** The examples become the plan's test cases. -> Design Recipe; Wrenn & Krishnamurthi "executable examples" (ICER 2019). -> EXP (small) + long classroom practice.
6. **Subgoal labels as the vocabulary of planning**: offer a label menu ("define the data", "validate input", "transform", "report failure") that he applies to his own steps. -> Margulieux, Catrambone, Guzdial. -> EXP (several, replicated, one CS1 deployment).
7. **Menu-based reasons, with an always-available one-sentence free-text and voice escape.** Click a reason chip ("these are the options of level") instead of typing. -> Aleven & Koedinger 2002 menu explanations; Johnson & Mayer 2010; Hausmann & Chi 2002 (speech elicits more self-explanation than typing). -> EXP (several); moderate.
8. **Record the reason next to every choice, and show the reason to the AI reviewer.** Reviewer must restate his intent and ask before critiquing. -> Self-explanation; "feedback that asks for intent" is mostly design inference, thin direct evidence. -> THEORY / OPINION.
9. **Run the plan on his own example with a tracer that moves values through steps** (a trace table generated from his step contracts), and fail loudly when a step's input does not exist yet. -> Tracing precedes writing skill; trace-first pedagogy (Xie et al. 2019; Nelson et al. 2017). -> EXP + OBS.
10. **Executable plan checks, not opinions**: type-check the data-flow (each step's "takes" must be produced earlier), run his 3 examples through a stub pipeline, flag unused data and orphan steps. -> No direct plan-validation study found; justified by feedback research (concrete, verifiable, task-level feedback) and by tracing. -> my inference, backed by Shute 2008 (review).
11. **Compare with expert designs AFTER he commits his own, and ask him to name differences.** -> Cognitive apprenticeship "reflection"; productive failure (generate first, then instruction). -> THEORY + META (productive failure, moderate).
12. **Fade the scaffold**: full form on first tickets, then pre-filled stages, then he picks which stages the ticket needs; the system proposes lighter planning for small tickets. -> Backward fading (Renkl & Atkinson); expertise reversal (Kalyuga). -> EXP (several) + THEORY.
13. **Hint ladder for the coach**: nudge question -> pointed question -> concrete observation -> (only on request) example from the parallel toy; the design itself never given. -> Hint-ladder ITS research; CodeAid / CodeHelp guardrails; "Generative AI can harm learning" (Bastani). -> EXP (several).
14. **Capture speech as an optional input**: push-to-talk "say your reasoning", transcribed into the reason field, then edited. Do NOT prompt him to explain continuously. -> Think-aloud is non-reactive; explanation prompts are reactive and help (Fox et al. 2011); speech yields more self-explanation (Hausmann & Chi). -> META (Fox) + EXP.
15. **Keep the stage short and finishable; make the plan the first commit's artifact** (plan file + reasons + examples checked in). Skipping must be possible but cost something visible. -> Students rarely do planning/testing early without incentives (Wrenn & Krishnamurthi 2020); mandatory long forms get gamed. -> OBS/EXP (small); my inference for the rest.

---

## 1. Explicit problem-solving stages and metacognition in programming

### Findings
- **Loksa, Ko, Jernigan, Oleson, Mendez, Dorn (CHI 2016), "Programming, Problem Solving, and Self-Awareness: Effects of Explicit Guidance."** Between-subjects study with novice programmers (n about 44, a multi-day programming camp-style setting; I do not recall exact details) comparing a control with a group given a tool that walked them through six problem-solving stages and prompted them about their process. The six stages, from Loksa's model: (1) reinterpret the problem prompt, (2) search for analogous problems, (3) search for solutions, (4) evaluate a potential solution, (5) implement a solution, (6) evaluate the implemented solution. Prompts took the form of the tool telling them what stage they were in, why it matters, and how it helps. Reported result: the guided group completed more work, was more productive, showed more awareness of their own process and more independence/less need for help; the pattern was robust across the measured outcomes. I do not remember effect sizes reliably; check the paper before quoting numbers. [not re-checked on content; DOI 10.1145/2858036.2858252; the ACM page returned HTTP 403 to my fetch].
- **Loksa & Ko (ICER 2016), "The Role of Self-Regulation in Programming Problem Solving Process and Success."** Observational analysis of think-aloud sessions: learners who engaged more in explicit self-regulation (stage awareness, evaluating their own approach) were more successful; most time lost came from skipping or mishandling early stages (misreading the prompt, committing to an approach too early, not checking the solution). DOI 10.1145/2960310.2960334 [not re-checked].
- **Prather, Pettit, McMurry, Peters, Homer, Simone, Becker (SIGCSE 2019, best paper), "First Things First: Providing Metacognitive Scaffolding for Interpreting Problem Prompts."** Controlled experiment with code submissions plus think-aloud. Students given a scaffold that made them interpret the prompt and solve a concrete test case (by hand) before coding understood the problem better and were more likely to complete the task. [verified via search: authors/venue/pages 531-537, DOI 10.1145/3287324.3287374; result summary from the abstract]. Link: https://dl.acm.org/doi/10.1145/3287324.3287374 (ACM pages block bots; UCD repository copy: https://researchrepository.ucd.ie/entities/publication/391f7626-5896-4d43-8835-d93ab5dbb1cb).
- **Prather et al. (ICER 2018), "Metacognitive difficulties faced by novice programmers in automated assessment tools."** Think-aloud study: novices often don't know what they are doing, misjudge their position in the process, and use feedback badly. DOI 10.1145/3230977.3230981 [not re-checked].
- **Prather et al. (ICER 2020), "What do we think we are doing? Metacognition and self-regulation in programming."** Reports that metacognitive skill varies and that struggling students are less accurate in self-assessment. DOI 10.1145/3372782.3406263 [not re-checked].

### Strength
EXP for the CHI 2016 and SIGCSE 2019 results (single studies, novices, short duration, researcher-built tools); OBS for the rest. Replication in intermediate learners or long-term settings: not found.

### Mechanic implied
- A visible **stage rail** (5-6 stages) showing where he is. Stages for Offer Letter, mapped to Loksa: Restate (1) / Examples + analogy (1, 2) / Data + steps (3) / Contracts + evaluate (4) / Implement (5, outside the planning stage) / Check against plan (6).
- A **three-part prompt per stage**: "What am I doing? Why now? How will it help?" Shown the first few times as a worked example; later shown on hover or as a single chip.
- **Interpret the prompt and solve one example by hand first** (Prather). In the harness: the ticket's example input is shown, he writes the expected output himself (click-built or short text) before any design.
- A "you are here" nudge when he skips or jumps ahead: "you're in Implement; the Examples stage is empty".

### Pitfalls
- Novice populations, short duration; the tool in the CHI study was custom and the guidance was constant. A heavy 6-stage rail on every ticket may be overkill for a 10-line fix (see fading).
- Metacognitive prompts can feel patronising to someone who already does the thing; scale them.
- Self-assessment is inaccurate, so any "did I understand the prompt?" self-check should be paired with an external check (the example test).

---

## 2. The Design Recipe (HtDP)

### What it is
Felleisen, Findler, Flatt, Krishnamurthi, *How to Design Programs* (2nd ed.), https://htdp.org/ [not re-checked live, stable]. The recipe, in order:
1. **Data definition**: what information is represented and how (itemization, structure, union, self-reference). The shape of the data determines the shape of the code.
2. **Signature, purpose statement, stub**: types in/out, one-line purpose.
3. **Examples**: concrete input/output (before the body).
4. **Template**: skeleton derived from the data definition (e.g., one case per variant of an enum; recursion for self-referential data).
5. **Body**: fill in the template.
6. **Test**: run the examples.

This maps almost one-to-one onto RustPlease: nouns -> data definitions, struct/enum bins -> data shapes, step contracts -> signature, 3 examples -> examples. The thing RustPlease lacked is the **template step** (derive code skeleton from data shape) and **tests that run**.

### Evidence
- **Fisler (ICER 2014), "The Recurring Rainfall Problem."** Re-examination of Soloway's Rainfall problem with a design-recipe-taught population; shows how the problem is a plan-composition test and how language/design-recipe changes the error profile. DOI 10.1145/2632320.2632346 [not re-checked]. OBS.
- **Fisler, Krishnamurthi, Siegmund (SIGCSE 2016), "Modernizing Plan-Composition Studies."** Methodological update, argues for studying composition of plans with modern languages and tasks. DOI 10.1145/2839509.2844556 [not re-checked].
- **Schanzer, Fisler, Krishnamurthi (SIGCSE 2018), "Assessing Bootstrap:Algebra Students on Scaffolded and Unscaffolded Word Problems."** Students taught with a design-recipe-style scaffold did better on scaffolded word problems and, I recall, retained a benefit on unscaffolded ones, though the transfer gain was smaller. DOI 10.1145/3159450.3159498 [not re-checked]. EXP-ish (classroom, middle school).
- **Wrenn & Krishnamurthi (ICER 2019), "Executable Examples for Programming Problem Comprehension."** Students write input/output examples as executable checks that are run against a reference implementation and against deliberately wrong implementations ("wheats and chaffs"); this exposes misunderstandings of the problem before coding. DOI 10.1145/3291279.3339416 [not re-checked]. EXP (small), directly relevant to "examples that actually run".
- **Wrenn & Krishnamurthi (Koli Calling 2020), "Will Students Write Tests Early Without Coercion?"** Found that students mostly do not write tests/examples early unless the course structure pushes them. DOI 10.1145/3428029.3428060 [not re-checked]. OBS.
- Overall: strong practitioner/curricular tradition, decades of use; controlled causal evidence on the recipe as a whole is thinner than its reputation. OPINION + modest EXP.

### Mechanic implied
- Keep the order: **data first, then signature/contract, then examples, then template, then body**. RustPlease did data -> steps -> contracts; add an explicit **"template" check**: for each enum he created, the plan must say what happens in each variant (match arm per variant). A missing arm is a concrete, checkable flag, and it is exactly the `level` enum bug (three separate enums instead of one enum with three variants would be visible as "no type has variants Info/Warn/Error").
- **Examples as executable cases**: his 3 examples (incl. edge) are stored as `(input -> expected)` and are re-used as hidden-test seeds / trace inputs.
- "Wheats and chaffs" idea: after he writes examples, the harness (not the AI) can show 2-3 wrong plan behaviours and ask "does your example set tell these apart?" (my adaptation).

### Pitfalls
- The recipe presumes data-directed design; fine for Rust enums/structs, less so for systems code driven by performance or I/O layout.
- Recipe can become ritual: students fill the form without thinking. Hence need for real checks (topic 6) and fading (topic 3).

---

## 3. Worked examples, completion problems, fading, expertise reversal

### Findings
- **Worked example effect** (Sweller & Cooper 1985; Sweller, van Merriënboer, Paas 1998, "Cognitive architecture and instructional design", Educ. Psych. Review). Novices learn more efficiently studying solved examples than solving equivalent problems, because problem-solving search eats working memory. THEORY with strong EXP backing; DOI 10.1023/A:1022193728205 [not re-checked].
- **Meta-analytic support**: Barbieri, Miller-Cotto, Clerjuste, Chawla (2023), "A Meta-analysis of the Worked Examples Effect on Mathematics Performance", Educational Psychology Review. I recall an overall benefit of about g = 0.48 for example-based over problem-solving instruction, larger for novices and for example-problem pairs than for examples alone. [not re-checked; check the number]. META (mathematics, not programming).
- **Completion problems / fading** (van Merriënboer; Renkl & Atkinson). Replace some steps of a worked example with blanks, then more, until the learner solves whole problems. **Backward fading** (blank the last step first, then last two...) beat forward fading and example-problem pairs in several experiments: Renkl, Atkinson, Maier, Staley (2002) "From example study to problem solving: Smooth transitions help learning", J. Experimental Education 70(4); Atkinson, Renkl, Merrill (2003) "Transitioning from studying examples to solving problems: Effects of self-explanation prompts and fading worked-out steps", J. Educational Psychology 95(4). [not re-checked]. EXP (several), math/physics-type domains.
- **Faded Parsons problems in programming**: Weinman, Fox, Hearst (CHI 2021), "Improving Instruction of Programming Patterns with Faded Parsons Problems": fading from fully given scrambled code to blanks, positive learner response and good performance. DOI 10.1145/3411764.3445228 [not re-checked]. EXP (small).
- **Expertise reversal effect**: Kalyuga, Ayres, Chandler, Sweller (2003), "The Expertise Reversal Effect", Educational Psychologist 38(1), 23-31. Guidance that helps novices becomes neutral or harmful for more knowledgeable learners, because processing redundant instruction costs working memory. DOI 10.1207/S15326985EP3801_4 [not re-checked]. THEORY with many EXP.
- **Adaptive fading by performance**: Kalyuga & Sweller (2004) "Measuring knowledge to optimize cognitive load factors during instruction" - dynamic assessment to choose how much guidance; Salden, Aleven, Schwonke, Renkl (2010) "The expertise reversal effect and worked examples in tutored problem solving", Instructional Science - adaptive fading helped in a Cognitive Tutor. [not re-checked].
- **Counter-view**: Kirschner, Sweller, Clark (2006) "Why minimal guidance during instruction does not work" argues for strong guidance for novices; Kapur's productive failure shows generate-then-instruct can beat direct instruction for conceptual understanding and transfer (Sinha & Kapur 2021, Review of Educational Research, meta-analysis of 53 studies; I recall moderate positive effect for conceptual knowledge and transfer when failure was followed by consolidation) [not re-checked]. META (productive failure).

### Mechanic implied (the central design problem for "every ticket")
- **Worked examples of planning**: a short, replayable, annotated plan of a parallel toy problem (e.g. "tiny log-level filter", "bank-account CLI") rendered in the same UI, showing both the final plan AND the narrated decisions: "I made `level` one enum with three variants because the options of one choice are variants, not separate types".
- **Example -> completion -> full** ladder across the first N tickets:
  1. Ticket 1-2: expert plan on a toy, he studies and answers 2-3 self-explanation chips.
  2. Ticket 3-5: toy plan with last stage blank (backward fading: he does the contracts or the trace).
  3. Ticket 6+: he plans; examples available on request.
  4. Later: planning scales with ticket size (see below).
- **Scale with ticket size and with measured skill** (expertise reversal): a "plan weight" setting derived from ticket complexity (number of new types, number of steps) and his recent plan-success record. Light mode = restate + 1 example + step list; heavy = full stages. He can raise but not silently disable.
- Keep **one fixed worked example always one click away** ("show me how a plan looks") so fading never leaves him without words.

### Pitfalls
- Most effects are in math/physics; programming-specific evidence on faded planning is thin (Parsons only).
- Expertise reversal means the scaffold that helps today can slow him in two months; require a mechanism that detects this (time per stage, skipped stages, plan pass rate) rather than a fixed schedule.
- Adult intermediates are not novices in Python but are in Rust ownership; expertise is domain-specific, so fade per concept/stage, not globally.
- Worked-example benefits require **self-explanation of the example** (Renkl 1997); passive reading of a plan gives smaller gains. Pair with chips.

---

## 4. Subgoal labelling

### Findings
- **Catrambone's subgoal learning model** (Catrambone 1998 "The subgoal learning model: Creating better examples so that students can solve novel problems", J. Exp. Psych: General): labelling the functional purpose of groups of steps helps learners abstract the structure and transfer to new problems. THEORY + EXP.
- **Margulieux, Catrambone, Guzdial (ICER 2012), "Subgoal-labeled instructional material improves performance and transfer in learning to develop mobile applications."** DOI 10.1145/2361276.2361291 [not re-checked]. Learners with subgoal-labelled worked examples (App Inventor) performed better on later problems, including transfer, than those with identical unlabelled examples. EXP.
- **Margulieux, Guzdial, Catrambone, "Subgoal-labeled instructional material..." / "Employing subgoals in computer programming education", Computer Science Education 26(1), 2016** (review/synthesis of their lab studies and subgoal use) [not re-checked].
- **Margulieux & Catrambone (2016), "Improving problem solving with subgoal labels in expository text and worked examples", Learning and Instruction.** Labels in both the text and the examples helped novel-problem solving; the text labels seemed to help learners state the procedure, the example labels to execute it. [verified via search summary].
- **Morrison, Margulieux, Guzdial (ICER 2015), "Subgoals, context, and worked examples in learning computing problem solving"** - labelled examples helped in a Java-like setting; effects depended on context/variation. [not re-checked].
- **Margulieux, Morrison, Decker (2020), "Reducing withdrawal and failure rates in introductory programming with subgoal labeled worked examples", Int. J. STEM Education.** CS1 deployment: improved performance, lower variance, higher persistence. [verified via search summary of results; check final numbers].
- **Learner-generated subgoals**: Margulieux & Catrambone (2019), "Finding the best types of guidance for constructing self-explanations of subgoals in programming", Journal of the Learning Sciences 28(1). I recall that asking learners to generate subgoal labels works better when scaffolded (e.g., given feedback or a structure) than unguided; unguided generation is hard. [not re-checked; I'm unsure of the exact comparison]. EXP.

### Strength
EXP, several labs plus one CS1 deployment; mostly one research group; replication across groups is limited. Moderate.

### Mechanic implied
- A **subgoal vocabulary** for planning: a short fixed label set, shown on the worked example and offered as chips when he names his own steps (e.g. `parse`, `validate`, `decide`, `transform`, `store`, `emit`, `handle failure`). Each step card gets a purpose label plus his free-text name.
- Labels double as the **words he lacked** ("articulation" gap): the stage prompts use the same words.
- Label generation by him, scaffolded: after seeing 1-2 labelled toy plans, he labels his own steps by picking/typing; the coach only compares labels to step contracts (e.g., a step labelled `validate` that can't fail is suspicious).
- For group labels at a higher level: "group these 6 steps into 3 phases and name each".

### Pitfalls
- Labels can become rote tags. Research-tested labels came with explanations of why the steps belong together; keep the "because" on the worked example.
- Domain-specific labels do not transfer unless the abstraction is the same; use a small vocabulary and let him add his own.
- Evidence of benefit mostly for procedures with clear structure; open design decisions (which data shape?) are less covered.

---

## 5. Self-explanation: menu-based vs open (does clicking work?)

### Findings
- **Chi, Bassok, Lewis, Reimann, Glaser (1989), "Self-explanations: How students study and use examples in learning to solve problems", Cognitive Science 13.** Good learners generate more explanations while studying examples. DOI 10.1207/s15516709cog1302_1 [not re-checked]. OBS/EXP.
- **Chi, de Leeuw, Chiu, LaVancher (1994)**, prompted self-explanation improved understanding of text. [not re-checked]. EXP.
- **Bisra, Liu, Nesbit, Salimi, Winne (2018), "Inducing Self-Explanation: a Meta-Analysis", Educational Psychology Review 30.** Overall effect about g = 0.55 for prompting self-explanation over control; moderators included who explains and the prompt type. DOI 10.1007/s10648-018-9434-x [not re-checked; effect size from memory]. META.
- **Rittle-Johnson, Loehr, Durkin (2017), "Promoting self-explanation to improve mathematics learning: A meta-analysis", ZDM.** Positive but smaller effect (around g = 0.2-0.3, I recall) with more benefit for conceptual and transfer outcomes than procedural. [not re-checked]. META.
- **Aleven & Koedinger (2002), "An effective metacognitive strategy: learning by doing and explaining with a computer-based Cognitive Tutor", Cognitive Science 26(2).** Geometry tutor in which students explained each step by **selecting a reason from a glossary/menu**; those who explained with menus had better understanding and transfer than those who didn't explain; the menu approach was helpful even though it's less "generative". DOI 10.1207/s15516709cog2602_1 [not re-checked]. EXP, classroom. This is the strongest evidence that **picking reasons from a menu works**.
- **Johnson & Mayer (2010), "Applying the self-explanation principle to multimedia learning in a computer-based game-like environment", Computers in Human Behavior 26(6).** Students who answered menu-style self-explanation prompts (choose the principle) in a game scored better on transfer than controls. [not re-checked; the web search could not retrieve this paper, treat as unconfirmed]. EXP.
- **Hausmann & Chi (2002), "Can a computer interface support self-explaining?", Cognitive Technology 7(1).** Typing explanations produced fewer self-explanations than speaking; spoken prompts led to more inference-bearing statements. [not re-checked]. EXP (small).
- **ICAP framework** (Chi & Wylie 2014, Educational Psychologist 49(4)): Interactive > Constructive > Active > Passive. Menu selection is "active" or weakly constructive; free generation is "constructive"; the framework predicts open explanation beats menu on deep learning but menu beats nothing. THEORY. DOI 10.1080/00461520.2014.965823 [not re-checked].
- Reviews: Dunlosky et al. (2013, Psychological Science in the Public Interest) rate self-explanation "moderate utility". [not re-checked].

### Strength
META for self-explanation in general; EXP for menu-based; direct comparison of menu vs open in programming planning: none found. Moderate. Practical conclusion is hedged: menus are about as good for **procedural/reason-selection** goals and cheaper; open text is probably better for **conceptual** understanding (ICAP).

### Mechanic implied
- **Default to a reason menu per decision**: when he sets `level` as an enum, a chip row asks "why?": `these are the alternatives of one choice` / `values with no behaviour` / `different shapes of data` / `other: ___`. Menus come from the domain (Rust rules) and are the equivalent of Aleven's glossary.
- **Always include "other" with a one-line free-text or voice entry.** The menu is the fast path; the escape is where the AI learns intents the UI didn't foresee (the `level` bug).
- **Selection plus a "relation" gesture**: the missing UI primitive in RustPlease was "these three are variants of that one" -> offer a "group as options of ___" gesture on cards. (UI inference from the failure, not a literature finding.)
- Add an **open, short explanation at moments where conceptual understanding matters** (contract of a risky step, the trace mismatch), and reduce to menu elsewhere. Rotate: if a menu choice repeats unchanged ten times, ask for words once.
- Consider **speech** for the open parts (Hausmann & Chi).

### Pitfalls
- Menus can be gamed by guessing the "correct-sounding" reason; include plausible wrong options and check reason-vs-choice consistency (mismatch -> coach question, not a grade).
- Menu design is work: options must reflect real distinctions, or he picks "other" every time.
- Prompts increase time (Fox 2011); cap prompts per ticket.

---

## 6. Tracing before writing; notional machines; "run the plan on an example"

### Findings
- **Lister et al. (ITiCSE WGR 2004), "A multi-national study of reading and tracing skills in novice programmers"** - many novices fail to trace short code correctly. [not re-checked]. OBS.
- **Lopez, Whalley, Robbins, Lister (ICER 2008), "Relationships between reading, tracing and writing skills in introductory programming"** - tracing and explaining ("explain in plain English") scores correlate with code writing; tracing skill appears to be a prerequisite hierarchy. DOI 10.1145/1404520.1404531 [not re-checked]. OBS (correlational, regression).
- **Venables, Tan, Lister (ICER 2009), "A closer look at tracing, explaining and code writing skills in the novice programmer"** - threshold effects: weak tracers rarely write well. [not re-checked].
- **Xie, Loksa, Nelson, Davidson, Dong, Kwik, Tan, Hwa, Li, Ko (2019), "A theory of instruction for introductory programming skills", Computer Science Education 29(2-3).** Proposes that instruction be organised around four skills: **reading code (tracing), writing code, and the two higher-order skills of planning/design and testing/debugging**, taught explicitly with tracing/reading first and strategies made explicit. DOI 10.1080/08993408.2019.1565235 [not re-checked]. THEORY with supporting experiments.
- **Nelson, Xie, Ko (ICER 2017), "Comprehension First: Evaluating a Novel Pedagogy and Tutoring System for Program Tracing in CS1"** - an explicit tracing strategy tutor improved tracing and later writing in a controlled comparison. DOI 10.1145/3105726.3106178 [not re-checked]. EXP.
- **Hertz & Jump (SIGCSE 2013), "Trace-based teaching in early programming courses"** - teaching with hand-traced memory diagrams showed gains. [not re-checked].
- **Cunningham, Blanchard, Ericson, Parker (ICER 2017), "Using tracing and sketching to solve programming problems: replicating and extending an analysis of what students draw"** - students who traced/sketched during problem solving succeeded more; many do not sketch. DOI 10.1145/3105726.3106190 [not re-checked]. OBS.
- **Notional machines**: du Boulay (1986) "Some difficulties of learning to program"; Sorva (2013) "Notional machines and introductory programming education", ACM TOCE 13(2), DOI 10.1145/2483710.2483713; Fincher et al. (2020) "Notional machines in computing education: the education of attention" (ITiCSE WGR). A notional machine is the simplified model of how the language executes that a learner uses to predict behaviour. Wrong or missing models cause misconceptions. [not re-checked]. THEORY/OBS.
- **Rainfall / plan errors** relate: running an example against a plan finds composition errors earlier than reading it (see topic 7).

### What this says about "run the plan on an example before coding"
- Reading/tracing skill is a *correlate and probable prerequisite* of writing skill (strongest for novices). It is not direct evidence that tracing a *plan* (not code) helps, but the mechanism is the same: executing a model on concrete values exposes gaps.
- The weakness in RustPlease (self-graded trace) is a known failure: students' self-assessment is unreliable (Prather 2020) and traces are most useful when a **checker compares** the learner's trace to the true one (Nelson 2017 tutor does this).
- For Rust ownership specifically, the notional machine is "who owns each value at each step": a trace table with columns (value, owner, borrowed by, moved to) is the natural sheet. Sorva-style visualisation is established; the plan-level version is my extension.

### Mechanic implied
- **Plan runner**: executes the plan as a dataflow simulation with *his* example values. For each step: inputs available? (produced earlier or given), moves/borrows consistent with the declared "takes" (e.g., a value moved in step 2 used by step 4 -> red), failure paths reachable? What is output vs expected output?
- **He predicts, then the runner shows.** He first writes the expected value after each step (click choices or short values), then the runner reveals the real sim values. Divergence is highlighted and explained by the system, not by AI opinion. This is a predict-then-observe loop (Nelson et al.), not a self-grade.
- Always run the edge-case example too, and run a **"surprise" example** he did not write (system-generated) to test the plan.
- Plan runner cannot know semantics of his steps beyond the declared contracts; bodies may be stubs with typed placeholders (default values) so the sim can run. State this limit honestly in the UI ("I checked flow and types, not logic").

### Pitfalls
- Correlational base; tracing may be a marker of general ability rather than a cause.
- Runner trust: a green plan runner can give false confidence; show *what was and wasn't checked*.
- Building a faithful runner for arbitrary designs is hard; scope it to contract-level checks first.

---

## 7. Programming plans, plan composition, goal/plan thinking

### Findings
- **Soloway & Ehrlich (1984), "Empirical studies of programming knowledge", IEEE TSE SE-10(5)** - experts have stored *programming plans* (stereotypical code fragments with goals) and *rules of programming discourse*; violating discourse rules slows experts. DOI 10.1109/TSE.1984.5010283 [not re-checked]. OBS/EXP.
- **Spohrer, Soloway, Pope (1985), "A goal/plan analysis of buggy Pascal programs", Human-Computer Interaction 1(2)** - most bugs arise from plan composition/goal interactions and unmet goals, not syntax: e.g., plans merged poorly, goals missing, "loop-plan" mistakes. [not re-checked]. OBS.
- **Soloway (1986), "Learning to program = learning to construct mechanisms and explanations", CACM 29(9)** - includes the **Rainfall problem** (average of non-negative numbers before a sentinel, with validation); novices commonly failed to compose guard, sentinel, sum, and count plans. DOI 10.1145/6592.6594 [not re-checked].
- **Bonar & Soloway (1985), "Preprogramming knowledge: a major source of misconceptions in novice programmers", HCI 1(2)** - novices import natural-language readings (e.g., "then" as a global jump) into code. [not re-checked].
- **Rist (1989), "Plans in programming: definition, demonstration, and development"; Rist (1995) "Program structure and design", Cognitive Science** - expert design proceeds by **focal expansion** (build around the key goal, expand outward); novices work forward in a linear sequence. [not re-checked]. THEORY/OBS.
- **Fisler (2014)** and **Fisler, Krishnamurthi, Siegmund (2016)** (topic 2): Rainfall with design-recipe-taught students, plan composition errors remain; language features influence them. [not re-checked].
- **Muller, Haberman, Ginat (2007), "Pattern-oriented instruction and its influence on problem decomposition and solution construction", ITiCSE** - explicit teaching of solution patterns improved solution quality and decomposition. [not re-checked]. EXP (classroom).
- **Izu, Weerasinghe, Pope (ICER 2016), "A study of code design skills in novice programmers using the SOLO taxonomy"** - most novices don't reach a design level where components are composed. [not re-checked]. OBS.
- **Robins, Rountree, Rountree (2003), "Learning and teaching programming: a review and discussion", Computer Science Education 13(2)** - review confirming the knowledge/strategies distinction. [not re-checked].

### Strength
Classic OBS; replicated qualitatively for decades; instruction studies (pattern-oriented) are EXP but few. Moderate.

### Mechanic implied
- **Name common composition errors in the coach** (the system knows them): *goal with no producing step*, *produced data never consumed*, *two steps both mutate the same thing*, *validation after use*, *failure path not handled (sentinel/early exit)*. These are executable structural checks and double as vocabulary ("this is the 'guard before use' pattern").
- **Plan library as worked examples**: 8-12 reusable plans for the ticket genre (parse-validate-transform-report; accumulator; lookup/index; state machine; producer/consumer). Each is shown on a toy; planning stage offers "does this ticket look like any of these?" (Loksa's "search for analogous problems").
- **Focal expansion prompt**: "Which one step is the heart of this ticket? Start there, then ask what it needs and what must happen before/after." That mirrors expert order and gives him a way to start when the page is blank.

### Pitfalls
- Plan inventories are language/paradigm-specific; Rust plans (ownership shapes, error propagation, builder, typestate) must be authored, not borrowed from Pascal studies.
- Pattern catalogs can create pattern-matching without understanding; always ask for the reason it fits.

---

## 8. Cognitive apprenticeship

### Findings
- **Collins, Brown, Newman (1989), "Cognitive apprenticeship: Teaching the crafts of reading, writing, and mathematics", in Resnick (ed.), *Knowing, Learning, and Instruction*.** Framework of six methods: **modeling** (expert externalises thinking), **coaching** (feedback while learner works), **scaffolding** (support with fading), **articulation** (learner verbalises knowledge, reasoning, problem-solving), **reflection** (learner compares own process with expert/peer), **exploration** (learner sets own problems). Plus sequencing: increasing complexity and diversity, global before local skills. [not re-checked; book chapter]. A shorter version: Collins, Brown, Holum (1991), "Cognitive Apprenticeship: Making Thinking Visible", American Educator 15(3). THEORY; evidence base is design-based studies (reciprocal teaching, Schoenfeld's problem-solving courses, Scardamalia & Bereiter's procedural facilitation for writing).
- **Schoenfeld (1985/1992)** on mathematical problem solving: students who got explicit teaching of heuristics, managerial control questions ("What am I doing? Why? How does it help?") improved; observed that novices often commit to an approach and pursue a "wild goose chase" without checking. This is the origin of the prompt wording used by Loksa. [not re-checked]. EXP/OBS.
- **Palincsar & Brown (1984), reciprocal teaching** - effective in reading comprehension (modeling, questioning, summarising, predicting) - one of the best-supported cognitive-apprenticeship-style interventions. [not re-checked]. EXP.
- In CS: Loksa's guidance and Xie's theory are explicit-strategy interventions in the same spirit; **de Raadt, Watson, Toleman (2009)** "Teaching and assessing programming strategies explicitly" (ACE) found explicit teaching of strategies helped. [not re-checked].

### Strength
THEORY; supported by a family of design-based and some controlled studies. No single meta-analysis of "cognitive apprenticeship" as a package that I could point to; treat the components, not the label, as the evidence.

### Mechanic implied
- **Modeling**: expert-plan replay with a spoken or written "thinking track" beside each action (the lacking worked example). Show false starts too (expert tries something, notices a problem, backs up), because novices believe experts don't fail.
- **Articulation**: the reason chips and one-sentence "why" fields are articulation lite. A short "explain your plan in 3 sentences" at the end to a Offer Letter teammate persona (the plan standup) is articulation to an audience; the evidence for teaching expectancy (Fiorella & Mayer 2013, "The relative benefits of learning by teaching and teaching expectancy", Contemporary Educational Psychology) suggests that expecting to explain improves learning even without the actual explanation. [not re-checked].
- **Reflection**: after he commits his plan, show the *expert's process* (order of moves, not just final design) and have him compare: "I started with the output; the expert started with the input. Which helped here?" Plus a post-ticket reflection: where did the plan break? (Compare the plan to the final code diff.)
- **Coaching**: the AI coach during planning; keep hint ladder (topic 10).
- **Scaffolding with fading**: topic 3.
- **Exploration**: later tickets let him choose his own decomposition or propose an alternative design.

### Pitfalls
- Modeling needs real experts' thinking, not a post-hoc tidy story. Capture it from an actual think-aloud (Luigi or the author planning a toy aloud, then edited) rather than AI-written monologue; or label AI-written ones as such.
- Reflection without a concrete comparison anchor turns into vague journalling.

---

## 9. Think-aloud and capturing reasoning

### Findings
- **Ericsson & Simon (1980/1993), "Verbal reports as data" / *Protocol Analysis*** - concurrent verbalisation of thoughts that are already in verbal form (think-aloud) doesn't alter the thought process, only slows it; explanations and introspection can alter it. THEORY.
- **Fox, Ericsson, Best (2011), "Do procedures for verbal reporting of thinking have to be reactive? A meta-analytic review and recommendations for best reporting methods", Psychological Bulletin 137(2), 316-344.** Meta-analysis of 94 studies (about 3,500 participants): pure think-aloud effect on accuracy about r = -.03 (non-reactive), while procedures that ask participants to **describe or explain** their thinking are reactive, with performance **higher** than silent controls; all verbal reporting slows tasks. DOI 10.1037/a0021663 [verified via search; supplement page https://supp.apa.org/psycarticles/supplemental/a0021663/a0021663_supp.html]. META.
- **Hausmann & Chi (2002)** (topic 5) - speaking vs typing for explanations. [not re-checked].
- **Journaling / decision records**: Architecture Decision Records (Nygard 2011, "Documenting Architecture Decisions", https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) are practitioner advice for capturing *why*. OPINION; no controlled evidence found for their learning effect.
- **Rubber-duck debugging** (Hunt & Thomas, *The Pragmatic Programmer*, 1999) - OPINION. Related evidence: self-explanation, teaching expectancy, "protege effect" (Fiorella & Mayer 2013; Chase et al. 2009 "Teachable agents and the protege effect", J. Science Education and Technology) [not re-checked]. Supports that explaining to an audience, even a non-responsive one, improves understanding; direct programming-specific controlled studies not found.
- **Prather et al. SIGCSE 2019 and Loksa 2016** both rely on think-aloud data - think-aloud is a valid research method but expensive to analyse; the app can't analyse speech meaningfully without LLM transcript processing (practical, not evidence).

### Strength
META for reactivity; OPINION for logs and ducks.

### Mechanic implied
- **Reasons are captured at decision time**: a "because" chip/voice note on each decision card; stored with the decision (not just the final plan). This directly fixes the "recorded choices, not reasons" finding.
- **Voice**: push-to-talk, 10-20 seconds, auto-transcribed (Whisper-class model locally or API), attached to the card; transcript editable; the raw audio discarded or kept per his setting. Think-aloud being non-reactive means ambient narration wouldn't hurt his planning, but **explicit explanation prompts will change (improve) his reasoning and slow it**, which is the point here: use explain prompts at the decision points, not continuous narration. Keep push-to-talk to avoid always-on recording (privacy and also the no-real-desktop rule in his notes).
- **Intent field the AI must read**: reviewers' input includes `{decision, options he considered, reason}`. The AI's first move is "Here's what I think you intended: ... right?" with a yes/no/correct chip.
- **Low-friction capture hierarchy**: (1) auto-captured actions (what he did, what he undid, what he hovered/hesitated on); (2) one-tap reason chip; (3) optional 10-second voice note; (4) free text. Never force 3 or 4.
- Undo/redo history and hesitation are free signals ("changed `level` from struct to enum twice") - the coach can ask about them. My inference.

### Pitfalls
- Forced explanation lengthens time on task (Fox); keep it light and bounded.
- Speech-to-text of Rust jargon is error-prone; keep it editable.
- Privacy/consent: always local or explicit.

---

## 10. Feedback design, hint ladders, Socratic questioning, AI tutors

### Findings (general feedback)
- **Shute (2008), "Focus on Formative Feedback", Review of Educational Research 78(1)** - review: elaborated, specific, goal-referenced, non-evaluative-of-person feedback works; timing: **immediate** helps for difficult/procedural tasks and low-ability learners, **delayed** can help transfer for simple tasks and higher-ability learners; avoid feedback that gives the answer too early. DOI 10.3102/0034654307313795 [not re-checked]. Review.
- **Hattie & Timperley (2007), "The Power of Feedback", RER 77(1)** - feedback levels (task, process, self-regulation, self); process and self-regulation feedback most useful. DOI 10.3102/003465430298487 [not re-checked].
- **Kluger & DeNisi (1996), meta-analysis, Psychological Bulletin 119** - about a third of feedback interventions *reduced* performance, particularly when attention was drawn to the self rather than the task. DOI 10.1037/0033-2909.119.2.254 [not re-checked]. META.
- **Corbett & Anderson (1995/2001)** - immediate feedback in programming ITS (LISP tutor) produced faster learning with similar outcomes vs delayed. [not re-checked].
- **VanLehn (2011), "The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems", Educational Psychologist 46(4)** - step-based tutors approached human tutors (effect sizes about d = 0.76 vs 0.79 over no tutoring in his synthesis); finer-grained interaction predicts better outcomes. DOI 10.1080/00461520.2011.611369 [not re-checked]. META.
- **Hint ladders / next-step hints in programming**: Price, Dong, Lipovac (SIGCSE 2017) "iSnap: Towards intelligent tutoring in novice programming environments"; Marwan, Williams, Price (ICER 2019) "An evaluation of the impact of automated programming hints on performance and learning" - hints helped students complete tasks but did not reliably improve later performance; Marwan et al. (ITiCSE 2019) "The impact of adding textual explanations to next-step hints in a novice programming environment" - explanations made hints more useful. [not re-checked]. EXP.
- **Help-seeking**: Aleven, McLaren, Roll, Koedinger (2016) "Help helps, but only so much: research on help seeking with intelligent tutoring systems", IJAIED 26 - learners misuse help (bottom-out hints quickly), so ladders need friction on the last rung. [not re-checked]. REVIEW.
- **Productive failure and generate-first** (Kapur; Sinha & Kapur 2021, RER meta-analysis) - see topic 3. Supports "your attempt first, then expert designs".

### AI tutors with guardrails
- **Liffiton, Sheese, Savelka, Denny (Koli Calling 2023), "CodeHelp: Using Large Language Models with Guardrails for Scalable Support in Programming Classes."** LLM assistant that refuses to output solution code and gives explanations/hints; deployed in a CS course; students found it helpful; instructors could review usage; evidence = deployment and survey, not an RCT. arXiv 2308.06921 [not re-checked live; I am fairly sure of the id]. OBS.
- **Kazemitabaar, Ye, Wang, Henley, Denny, Craig, Grossman (CHI 2024), "CodeAid: Evaluating a Classroom Deployment of an LLM-based Programming Assistant that Balances Student and Educator Needs."** Deployment in a systems programming course, about 700 students, 12 weeks, 8,000 usages analysed, 22 student interviews and 8 educator interviews; designed not to reveal code solutions (conceptual answers, pseudocode with line-by-line explanation, annotated fix suggestions). [verified via search; arXiv https://arxiv.org/abs/2401.11314]. Findings I recall but did not re-check: students liked quick conceptual help, but also wanted code; educators worried about over-reliance and wanted pedagogical guardrails; usage patterns differed by prior skill.
- **Kazemitabaar et al. (CHI 2023), "Studying the effect of AI code generators on supporting novice learners in introductory programming"** - novices using Codex completed more tasks and did not do worse on later manual tasks in a short study, but some over-relied. DOI 10.1145/3544548.3580919 [not re-checked]. EXP (short).
- **Liu, Zhao, Leong, Malan et al. (SIGCSE 2024), "Teaching CS50 with AI: Leveraging Generative AI in Computer Science Education"** - CS50's "duck" is an LLM instructed not to give full solutions; descriptive report of design and student reception. DOI 10.1145/3626252.3630938 [not re-checked]. OBS.
- **Bastani, Bastani, Sungu, Ge, Kabakcı, Mariman (2024/2025), "Generative AI Can Harm Learning" (PNAS 2025; SSRN 4895486)** - field experiment (about 1,000 high-school math students, Turkey): unrestricted GPT-4 access improved practice performance but **reduced** later unassisted exam performance (about -17% in the report I recall), while a tutor version with teacher-written hints and guardrails mostly eliminated the harm. [not re-checked; confirm numbers]. EXP (large field, different domain). This is the best evidence on guardrails mattering.
- **Prather et al. (ICER 2024), "The Widening Gap: The Benefits and Harms of Generative AI for Novice Programmers"** - observational study: students with strong metacognition used Copilot/ChatGPT productively; those with weak metacognition fell into illusions of competence and were hurt more. arXiv 2405.17739 [not re-checked live]. OBS. Directly relevant to Luigi: planning scaffolds are a metacognitive prosthesis, AI without it widens the gap.
- **Lehmann, Cornelius, Sting (2024), "AI Meets the Classroom: When Do Large Language Models Harm Learning?"** - LLM use harms when substituting for thinking, helps when used to supplement. arXiv 2409.09047 [not re-checked]. OBS/EXP.
- **LLM asks clarifying question before critiquing**: I found **no controlled study** of this exact tactic in programming education. Adjacent evidence: (1) tutoring research that human tutors often elicit student reasoning before correcting (VanLehn 2011; Chi et al. 2001 "Learning from human tutoring", Cognitive Science 25) [not re-checked]; (2) LLM agent research on clarifying questions for ambiguous user intents (e.g., Qian et al. 2024 "Tell Me More!", arXiv 2402.09205) [not re-checked]; (3) "Socratic" chatbot prototypes with small evaluations. Treat "ask intent first" as a justified design bet, not a proven effect; instrument it so you can test it (do plans survive review better when intent was asked?).

### Strength
Feedback: META/review for general principles; EXP for hints; AI-guardrail evidence: a handful of EXP/large OBS, young field. Clarifying-question-first: inference.

### Mechanic implied
- **Coach protocol**:
  1. *Intent restatement*: "I read your plan as X because Y. Right?" (chip: yes / no / partly + reason).
  2. *Only then* raise flags, limited to "won't work" (checked by a runner or a type/flow rule) and "works but costs" (with a cost he can verify: e.g., clone count, extra allocation).
  3. Hint ladder: L1 question that points at the area ("What owns `config` after step 3?"), L2 observation ("Step 4 uses `config` after step 3 moves it"), L3 parallel-toy example of the same problem, L4 (explicit request only, and logged) a concrete fix sketch. Delay between rungs or require a one-line attempt to move down.
  4. Never provide a full design before he commits his own; expert designs appear only after commit (reflection).
- **Immediate feedback for mechanical things** (flow/type errors in the plan: instant, from the runner), **delayed feedback for design judgement** (end of stage), matching Shute's timing conclusions.
- **Answerable feedback**: every coach question has a place to answer (chips + free text/voice) and the answer is stored and shown to later reviewers (the finding: feedback questions had nowhere to be answered).
- **Task-level, not person-level feedback** (Kluger & DeNisi): "step 4 has no input" not "you forgot".
- Track hint use and bottom-out use; if he always goes to L4, surface that gently.

### Pitfalls
- Over-reliance: the AI "teammates" in Offer Letter will be tempted to solve; the persona prompt must forbid giving the design in planning; plan-stage responses should be validated by a rule (no code blocks, no full struct definitions) and logged.
- Immediate feedback can reduce transfer (feedback dependence): reserve some stages for no-feedback self-checks followed by delayed review.
- Guardrails frustrate learners who want the answer (CodeAid/CodeHelp students); the escape hatch should be explicit and logged, not hidden.
- LLM critiques sometimes hallucinate Rust semantics; the executable checks should dominate, the AI should annotate them.

---

## 11. Does planning before coding improve outcomes?

### Findings
- **Pseudocode/plan-first in CS1**: evidence is mixed and mostly weak. Reviews (Robins et al. 2003; Luxton-Reilly et al. 2018 "Introductory programming: a systematic literature review", ITiCSE WGR) note that explicit teaching of problem-solving strategy and design shows benefits in several small studies but few large controlled trials. [not re-checked]. Review.
- **Explicit strategy teaching**: de Raadt (2008 thesis, Univ. Southern Queensland) and de Raadt, Watson, Toleman (2009) - explicit strategies taught in CS1 improved outcomes in the cohort. [not re-checked]. EXP-ish (quasi).
- **Loksa 2016, Prather 2019, Xie 2019** (topics 1, 6) - the strongest direct evidence that *explicit* process guidance, including interpreting the prompt and solving an example first, improves success for novices. EXP.
- **Muller, Haberman, Ginat (2007)** - pattern-oriented instruction improved decomposition (topic 7). EXP.
- **Parsons problems**: Parsons & Haden (2006) "Parson's programming puzzles: a fun and effective learning tool for first programming courses" (ACE); Ericson, Margulieux, Rick (2017) "Solving Parsons problems versus fixing and writing code" (Koli Calling); Ericson, Guzdial, Morrison (2015) ICER - Parsons problems were as effective as writing with less time; they train *structure/ordering* without syntax load. Weinman et al. 2021 (faded Parsons). [not re-checked]. EXP, moderate. Relevant: the "order the steps" mechanic is a Parsons problem for plans; and Parsons problems can be used as the fading rungs for plan-ordering practice.
- **Decomposition**: Rich, Binkowski, Strickland, Franklin (ICER 2018), "Decomposition: A K-8 Computational Thinking Learning Trajectory" - a proposed trajectory (OBS/synthesis); Charitsis, Piech, Mitchell (L@S 2022) used NLP to score decomposition quality. [not re-checked]. Little causal evidence for adults.
- **Kinnunen & Simon (2012), "My program is ok - am I? Computing freshmen's experiences of doing programming assignments", Computer Science Education 22(1)** - students judge correctness by "it runs on my example" and lack means to verify; supports external checks. [not re-checked]. OBS.
- **Test-first/TDD in education**: Edwards (2003, SIGCSE) "Using test-driven development in the classroom"; Buffardi & Edwards (2013) on adaptive feedback for testing; mixed results on learning but reliable gains in student-written-test quality when feedback is given. [not re-checked].
- **Implementation intentions** (not planning-the-solution but planning-the-behaviour): Gollwitzer & Sheeran (2006), meta-analysis of 94 studies, d about 0.65 for "if-then" plans on goal attainment, JESP / Advances in Experimental Social Psychology 38. DOI 10.1016/S0065-2601(06)38002-1 [not re-checked]. META. Relevant to Luigi's "restarts rather than finishes" and to making planning *the default*: "When I open a ticket, I do the restate step first". Mark as adjacent evidence.

### Strength
Direct causal evidence for "plan-then-code" in adults/intermediates: **thin**. For novices: EXP moderate. The stronger evidence is about *specific components* (interpret prompt + example first, explicit strategy, tracing, subgoals) rather than "planning" as a generic stage. Be honest in the product: planning is a bundle of sub-skills; test which of them pay off for Luigi.

### Mechanic implied
- Treat **order-the-steps** as a Parsons-style rung, fade to free ordering.
- Include **small, measurable outcomes** to evaluate planning on him: plan-to-code divergence (how many types/steps changed), tests passed on first run, time to first green, number of restarts. Use them to tune plan weight (topic 3).
- Use an **if-then commitment** at ticket open ("When I click Start, the first thing is Restate"), set by him, as the default-habit hook.

### Pitfalls
- Hawthorne: measurement of his own plan quality could become gamified.
- The control comparison (no plan vs plan) doesn't exist for Luigi unless some tickets are randomly assigned light/heavy planning; consider doing that deliberately (A/B on himself) for a few weeks.

---

## B. Anti-patterns to avoid

1. **Long mandatory forms on every ticket.** Prompts increase time (Fox 2011) and cause ritual compliance (design-recipe-as-form). Cap the planning stage (target < 10-15 min for a normal ticket; less for small) and make the plan weight scale with the ticket.
2. **Scaffolds that never fade** (expertise reversal). A fixed 6-stage rail forever will become friction; fade by stage and per concept.
3. **Self-graded checks** (traces, "does this look right?"). Self-assessment is unreliable (Prather 2020); use a runner or tests that compare against truth.
4. **Opinion-only validation** (5-item AI lists). Prefer executable checks first (flow, types, contracts, examples), AI second; and always state what was not checked.
5. **AI giving the design away** (Bastani 2024: unguarded access harmed later performance; Prather 2024: widens gap). Hint ladder, no code in planning, expert designs only after commit.
6. **Critiquing before asking intent** (the `level` bug). Restate intent, get a yes/no/correction, then critique.
7. **Menus with no escape.** If the UI can't express the thing (variants of one choice), he distorts the model; always give "other" + voice and a relation gesture.
8. **Recording choices without reasons.** A plan with no reasons can't be reviewed or learned from.
9. **Worked examples that show only the product.** Show the process, including false starts and the vocabulary.
10. **Passive worked examples.** Pair every study with a self-explanation or prediction task.
11. **Free-form journaling as the main capture.** High friction, low use. Prefer click + optional voice.
12. **Generic grade/scoring of the plan.** Focus feedback on task and process (Kluger & DeNisi); do not display a single score that invites gaming.
13. **Letting the plan and the code drift apart silently.** Show plan-vs-implementation diff at PR time; plans nobody revisits teach that planning is theatre.
14. **Treating one research group's results as settled.** Subgoal labelling and Loksa's guidance are promising but come from few groups, mostly novices.
15. **Making skipping impossible, or free.** Both fail: forced = gaming; free = never done (Wrenn & Krishnamurthi 2020). Allow "light plan" with a visible cost (e.g., review will ask for the missing pieces).

## C. Open questions

1. **Do these effects hold for intermediate adults learning a new language/paradigm?** Almost all evidence is novices. A/B on Luigi himself (heavy vs light plan on randomly assigned tickets) is the cheapest answer.
2. **Menu vs open vs voice explanation in plan design**: no direct comparison in a planning task. Instrument which input mode he uses and whether reason quality (as judged later by the runner failing or not) differs.
3. **Does a plan runner on contract-level stubs find real design errors**, or only trivial ones? Needs a bank of known-bad plans (like wheats/chaffs) to measure recall; start with the errors he actually made (`level` enum split, committed plan that didn't work).
4. **Does asking intent first improve later AI critique relevance?** No controlled evidence found. Log "critique later rejected as unintended" rate.
5. **How quickly should the scaffold fade, and what signal drives it?** Candidate signals: plan-pass rate on first run, time per stage, skip rate, divergence between plan and code. No validated rule exists.
6. **Is the Loksa six-stage model the right grain for systems/Rust tickets?** It was built from novice web-style tasks; design-heavy tickets may need a "constraints and performance" stage (my guess, no evidence).
7. **What is the minimum worked-example set** (how many toy plans) before he can plan unaided, and does it transfer across ticket genres (parser, cache, scheduler)?
8. **Will planning-as-default hold up under his tendency to restart?** Implementation-intention evidence (Gollwitzer & Sheeran) suggests if-then commitments help, but nothing studied his specific failure mode; consider coupling the plan to a "finish line" (done-definition from hidden tests) to reduce restarts.
9. **Over-reliance dynamics with a persistent AI team**: studies are on semester-long courses; Offer Letter's teammates are always on. Needs a policy for when teammates may reveal design (after PR? after N failed attempts?) and logging to review it.
10. **Speech capture**: benefits for explanation quantity (Hausmann & Chi) are from 2002 lab work; modern ASR on Rust terminology and his actual usage rate are unknown.

## D. Quick source index (all `[not re-checked]` unless marked)

- Loksa et al. CHI 2016 - https://doi.org/10.1145/2858036.2858252 (ACM page 403 on fetch)
- Loksa & Ko ICER 2016 - https://doi.org/10.1145/2960310.2960334
- Prather et al. SIGCSE 2019 - https://doi.org/10.1145/3287324.3287374 [verified via search]
- Prather et al. ICER 2018 - https://doi.org/10.1145/3230977.3230981; ICER 2020 - https://doi.org/10.1145/3372782.3406263
- HtDP - https://htdp.org/
- Fisler ICER 2014 - https://doi.org/10.1145/2632320.2632346; Wrenn & Krishnamurthi ICER 2019 - https://doi.org/10.1145/3291279.3339416
- Sweller et al. 1998 - https://doi.org/10.1023/A:1022193728205; Kalyuga et al. 2003 - https://doi.org/10.1207/S15326985EP3801_4
- Weinman et al. CHI 2021 - https://doi.org/10.1145/3411764.3445228
- Margulieux et al. ICER 2012 - https://doi.org/10.1145/2361276.2361291; Margulieux & Catrambone 2016 L&I [verified via search]; Margulieux, Morrison, Decker 2020 [verified via search summary]
- Bisra et al. 2018 - https://doi.org/10.1007/s10648-018-9434-x; Aleven & Koedinger 2002 - https://doi.org/10.1207/s15516709cog2602_1; Chi & Wylie 2014 - https://doi.org/10.1080/00461520.2014.965823
- Lopez et al. ICER 2008 - https://doi.org/10.1145/1404520.1404531; Xie et al. 2019 - https://doi.org/10.1080/08993408.2019.1565235; Nelson et al. ICER 2017 - https://doi.org/10.1145/3105726.3106178; Sorva 2013 - https://doi.org/10.1145/2483710.2483713
- Soloway & Ehrlich 1984 - https://doi.org/10.1109/TSE.1984.5010283; Soloway 1986 - https://doi.org/10.1145/6592.6594
- Collins, Brown, Holum 1991 - American Educator (search "Cognitive Apprenticeship: Making Thinking Visible")
- Fox, Ericsson, Best 2011 - https://doi.org/10.1037/a0021663 [verified via search]
- Shute 2008 - https://doi.org/10.3102/0034654307313795; Hattie & Timperley 2007 - https://doi.org/10.3102/003465430298487; Kluger & DeNisi 1996 - https://doi.org/10.1037/0033-2909.119.2.254; VanLehn 2011 - https://doi.org/10.1080/00461520.2011.611369
- CodeHelp - https://arxiv.org/abs/2308.06921; CodeAid - https://arxiv.org/abs/2401.11314 [verified]; Widening Gap - https://arxiv.org/abs/2405.17739; CS50 duck - https://doi.org/10.1145/3626252.3630938; Bastani et al. - https://doi.org/10.1073/pnas.2422633122 (I recall this DOI, check)
- Gollwitzer & Sheeran 2006 - https://doi.org/10.1016/S0065-2601(06)38002-1
