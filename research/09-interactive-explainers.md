# 09 - Interactive "Explain it to me" videos

Research for one feature: Luigi presses a button on a PR, a ticket, or a paper behind an
experiment ticket, and gets a short animated explainer with characters, backgrounds, and
pause points where he answers a question (typed, clicked or spoken) and an agent checks it.

Written 2026-10-21. Sources were checked with WebSearch/WebFetch on that date unless marked
"[not re-checked]" (that means: I know it from memory or from a secondary source and did not
open the original this session). Where a search gave only a press summary I say so.

Read first, not repeated here: `research/04-workplace-realism.md`,
`research/07-planning-learning-science.md`, `docs/ARCHITECTURE.md` sections 1, 4, 6, 8.

---

## Recommendation

1. **Build approach: (c), a browser-native "live explainer", not rendered video.** The server
   asks an agent for a JSON scene script, validates it against a schema, checks every claim
   against facts pulled from the real diff, checks it for answer leaks, caches Kokoro audio per
   line, and the web app plays it with React + Motion (SVG diagrams, portraits, office
   backgrounds). Pausing, branching, replaying a beat and "try your idea" are free because the
   player is a state machine, not a video file. Phaser is used only if a beat wants the pixel
   office as its backdrop.
2. **Keep Manim as an optional "polish" tier**, not the core. Pre-rendered Manim per ticket is
   fine for a handful of hand-made flagship explainers (the studio already exists), but it
   cannot branch, cannot be generated on demand, and LLM-written Manim fails often enough
   (see 6b) that it would turn "press a button" into "wait and hope".
3. **Scene script format, one paragraph.** A script is a list of *beats*. Each beat has one
   narration line (spoken by a named character, shown as a subtitle, voiced by cached Kokoro
   audio), a `stage` (background id + which characters stand where with which expression), and
   a short list of *visual ops* drawn only from a fixed widget library (`code` with line
   highlight, `queue`, `timeline`, `request_arrow`, `table`, `callout`, `analogy_card`,
   `compare`). A beat may carry a `cites` list of fact ids; every factual claim must cite a fact
   the server extracted. Beats are grouped into *segments* of 60-90 seconds. At the end of a
   segment there may be a `question`: prompt, rubric (key ideas + accepted alternatives +
   common wrong ideas), a `try_idea` branch (a simulated consequence), and a three-rung
   `hints` ladder. Everything is plain JSON validated by Pydantic on the server and zod on the
   client.
4. **Question loop.** Play segment, pause at the question, he answers by clicking an option, typing
   or holding a mic key. A *separate* grader call (Haiku, fresh context, rubric only, no
   persona) returns one of: `works`, `partly`, `different_but_valid`, `off_track`,
   `cant_tell`. `works` and `different_but_valid` continue the video; `partly` and
   `off_track` play the "try your idea" branch (what would happen if you did that) and then
   hint rung 1; after two misses a worked example on a parallel toy; after three, the video
   shows the intended idea and marks the question "seen, not solved" so the escape hatch never
   feels like a pass. He can always press "show me" or "skip".
5. **Answers are mostly clicks.** Luigi prefers clicking. Use a *predict-then-reveal* click
   ("what do you think happens when the queue is full? [drops / blocks / grows forever]")
   for most pause points, and reserve the open "how would you solve this?" box for 1 in 3. The
   LLM check only runs on open answers.
6. **Review-stage safety.** In `review` stage a script is generated in "describe only" mode:
   the generator gets the diff and facts but never the answer key; allowed beat types are
   `what_it_does` and `concept`; `question` kinds are limited to predict-the-output and
   concept checks; a server-side leak check compares the finished script to the answer key
   (token overlap plus an LLM judge on the key only) and rejects the script on any hit. After
   review the stage unlocks `what_went_wrong`, `why_it_matters`, and design-alternative
   questions.
7. **Papers.** Generate from the paper's text (PDF to text, section-tagged) using a
   Keshav-style structure: claim, why it matters, method intuition, the key number, assumptions
   and limits. Every number and claim cites a quoted span from the paper; the server
   verifies the quote exists in the extracted text.
8. **Cost.** One script is one Sonnet call (about 3-6k tokens in, 2-4k out) plus a cheap Haiku
   validate/repair pass if needed; each answer check is one small Haiku call. On a Claude plan
   this is roughly the cost of one code-review turn per video plus a few percent per
   answer. Cache by `(artifact_hash, stage, level, script_version)`. Details in section 8.
9. **Build first (smallest slice that proves it):** the player, schema, 5 widgets and 1 hand-written
   script for one real KLN ticket PR; Kokoro line cache; click questions only; then the
   grader + hint ladder; then the generator; then voice input; then papers. Do *not* start
   with the generator: a hand-written script will show within a day whether the player feels
   good, and it gives the generator a gold example to imitate.
10. **Time-box and ship-gate** (he restarts rather than finishes): the first slice is
    "one script plays end to end, one question gates it, one wrong answer shows a branch."
    Nothing else before that works.

---

## 1. Learning science of explainer video

### 1.1 Mayer's principles, and which ones bind here

Mayer's cognitive theory of multimedia learning (Mayer 2009/2021, *Multimedia Learning*;
Cambridge Handbook of Multimedia Learning) gives a set of design principles. Effect sizes in
Mayer's own summaries are mostly medium (median d around 0.4-0.9 on transfer tests, larger for
signalling-free baseline comparisons in tightly controlled lab studies; treat them as upper
bounds for a self-directed adult watching a screen) [not re-checked per principle].

| Principle | Plain meaning | What it forces in our player |
|---|---|---|
| Coherence | Cut interesting-but-irrelevant material | No decorative animation, no jokes that don't carry the point; backgrounds are quiet; characters do not wander |
| Signalling | Mark the important thing | The `code` widget highlights the line being narrated; arrows/pulses on the thing named; words like "first, second" |
| Redundancy | Narration + identical on-screen text hurts | Subtitles are optional (default off for the narrator, on for accessibility); do not print the full narrated sentence in a bubble *and* speak it; put only key terms on screen |
| Spatial / temporal contiguity | Put words near the picture; say it as it appears | Callouts attach to the object; a visual op fires on the word it refers to (`at: "word:queue"`) |
| Segmenting | Learner-paced chunks beat one continuous stream | Segments of 60-90 s, with a Next/Replay at every boundary |
| Pre-training | Know the key terms first | A 10-second "three words you'll hear" beat at the start of a segment when it has new vocabulary |
| Modality | Narration + picture beats text + picture | Kokoro audio is the default channel |
| Personalization / voice | Conversational style, human-like voice, beat formal style | Narration written as one teammate talking to Luigi ("you"), Kokoro voices chosen after the pending blind test |
| Embodiment / image | See below | See below |

Sources:
- Mayer's principle list and the Handbook chapters on social-cue principles:
  https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-based-on-social-cues-in-multimedia-learning/093C1CDE75CF486DACD4CABC325ABE47
- Brame, C. J. (2016), *Effective Educational Videos*, CBE-Life Sciences Education 15(4):es6,
  organizes the same ideas around cognitive load, engagement and active learning:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5132380/ (checked: framework and signalling
  advice confirmed; the search did not return her segmenting passage, so read it before
  quoting it).

**Do animated characters help or distract?** The honest answer from the literature:

- The *image principle* says that putting a talking face on screen does **not** reliably
  improve learning; it can split attention. The *embodiment principle* says that when an
  on-screen agent does behave like a person (gestures, gaze toward what matters, facial
  expression), learning is better than with a static agent. A Mayer & Fiorella chapter
  summarises agent studies as g = .45 on transfer and g = .23 on retention (secondary
  summary of the Handbook chapter, found via search; the chapter itself was not opened):
  https://core-cms.cambridgecore.org/core/books/cambridge-handbook-of-multimedia-learning/multimedia-learning-with-animated-pedagogical-agents/B629E8948494D949DB818B4AB31F3B4F
- Schroeder et al. (2013) meta-analysis (43 studies, 3,088 participants): agents give a small
  but significant benefit; agents that communicate by on-screen text did better than narrated
  ones (reported in the same search; original paper [not re-checked]).
- A 2025 meta-analysis of 24 studies found the teaching agent only slightly reduced
  cognitive load (search summary; https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1635465/pdf
  was the nearest link, not opened).
- Takeaway: characters are worth it only if they *do work*: point at the diagram, look at the
  line being discussed, change expression when the point is "this is a surprise". A character
  who just sits in a corner reciting is the image-principle failure case.

**Design consequences for Offer Letter.**
- The narrator portrait is small (corner, 18-22% width), the *diagram* is the hero.
- Use the existing 7 expressions as *signals* (puzzled when a wrong idea is introduced,
  thinking during a pause, pleased on a good answer). Lip-flap from audio amplitude is
  already built and gives the "human-like behavior" cheaply.
- A second character is allowed only when the explainer is a dialogue that *models* the
  question (Luigi's teammate asks the naive question, the other answers). Dialogue-style
  explanation has a good record as a way to surface misconceptions [not re-checked];
  keep to two speakers.
- Use the pixel office as the stage for analogies about *people at work* (the queue at the
  coffee machine). Use the clean panel for code. Mixing the two in one frame breaks
  coherence.

### 1.2 Length and engagement: Guo, Kim & Rubin 2014

Analysis of 6.9 million edX video sessions: **shorter videos engaged more** (the strongest
predictor), and informal talking/tablet-style videos beat polished lecture-hall footage cut
into pieces; faster, enthusiastic speakers were more engaging (the last point is from a
secondary summary). The "6 minutes" figure often quoted was **not** confirmed by my search;
the paper's own median-watch-time chart is the place to check. Paper:
https://www.cs.rochester.edu/hci/pubs/pdfs/edX-MOOC-video-production-and-engagement_LAS-2014.pdf

Mechanic for us: total video <= 5-6 minutes, segments 60-90 s, and the pause points reset
attention. Note: MOOC watch time is not learning; it is about whether he stays, which matters
for a person who restarts.

### 1.3 Questions inside the video

- **Szpunar, Khan & Schacter (2013, PNAS)** "Interpolated memory tests reduce mind wandering
  and improve learning of online lectures." Tests between lecture segments: about half the
  mind wandering (the no-test group reported wandering about 40% of the time), roughly three
  times as much note-taking, better final recall, and *lower* reported anxiety about a final
  test. Open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699/ . The 2016 Jing,
  Szpunar & Schacter follow-up extended it to a 40-minute video and found better
  integration across the lecture (search summary).
- **Kovacs (2016, Learning at Scale)** "Effects of in-video quizzes on MOOC lecture viewing":
  74% of viewers who start a video attempt its quiz; 76% are right first try; learners seek
  *backward* from a quiz to the earlier section (a natural "let me rewatch"); in-video dropout
  was lower in videos with quizzes; some learners skip from quiz to quiz.
  https://hci.stanford.edu/publications/paper.php?id=314 . Design consequence: the player
  must make "replay the last segment" one click away from the question, and must not let the
  quiz-to-quiz skipping strategy defeat the point (the grader checks an answer, it is not
  multiple choice you can brute force; for click questions rotate options).
- A Cambridge study of in-video questions in a *programming* course found engagement of
  71-86% at a rate of about 1 question per 8.7 minutes
  (https://www.repository.cam.ac.uk/handle/1810/248411, search summary only). Our rate will be
  higher (one per 60-90 s of video), so expect more friction; keep questions cheap.
- Vural (2013), van der Meij (in-video interactive questions in instructional video), and
  Haagsman et al. (2020) on embedded questions in video: I could not verify these in this
  session. Treat as "known literature, direction consistent with Szpunar, not re-checked".
  If cited in the design doc, fetch the originals first.

**Predict-observe-explain (POE).** Ask for a prediction before showing the result; the surprise
when wrong is the learning event (White & Gunstone 1992 [not re-checked]). In our player this
is the cheapest and most useful pattern: "the queue has 3 slots and 5 requests arrive; what
happens to request 4?" then run the `queue` widget. It also works for code: "what does this
function return for `[]`?" then step the `code` widget.

**Generative activities** (Fiorella & Mayer, *Learning as a Generative Activity*, 2015
[not re-checked]): having the learner explain, draw or summarise during the lesson helps more
than re-watching. For us: the open question ("how would you solve it?") is the generative
activity, and the *explain it back in one sentence* end-of-video question reuses the existing
`explain.py` flow.

**Learner-controlled pacing.** Always: pause, replay segment, speed 0.75x-1.5x, subtitles
toggle, jump to a segment from a segment strip. Mayer's segmenting effect is stronger when
the learner controls the advance.

### 1.4 What this means in one list

- 3-6 segments, 60-90 s each, one idea per segment.
- Question at the end of most segments, but a *click* by default, an open box on the key one.
- Signal everything: highlight, pulse, point.
- Do not read the screen aloud; do not show long text.
- Characters point, look, and react; they do not decorate.
- One-click replay of the preceding segment from every question.

---

## 2. Analogies and real-world examples

### 2.1 What the research says

- **Gentner's structure-mapping theory** (1983, *Cognitive Science*) [not re-checked]: a good
  analogy maps *relations* (A is blocked until B finishes) not surface features (both are
  round). Learners often grab surface similarity first; novices need the relations pointed out.
- **Glynn's Teaching-With-Analogies model** (Glynn 1991; Glynn & Takahashi 1998 [not
  re-checked]), six steps: (1) introduce the target concept, (2) cue recall of the analog, (3)
  identify similar features, (4) map the similarities, (5) **indicate where the analogy
  breaks down**, (6) draw conclusions.
- **Richland and colleagues** (Richland, Zur & Holyoak 2007, *Science*, "Cognitive supports
  for analogies in the mathematics classroom" [not re-checked]; Richland & Simms 2015 on
  analogy in STEM [not re-checked]): analogies work much better when the teacher
  *visibly aligns* the two cases side by side, gestures or highlights the corresponding parts,
  and keeps both on screen together rather than describing the source from memory.
- **Risk**: an analogy imports wrong inferences. Learners keep the analog's features that were
  never meant to map ("a pointer is a street address, so it can only point to a house").
  Remedy is Glynn's step 5, and ending with a question that probes the *edge* of the analogy.

### 2.2 Mechanic: the `analogy_card` beat

Three visual states, each a beat: (1) *the everyday scene* in the office background
("a coffee machine and six people"), (2) *the same shape* drawn as the technical diagram,
with matching parts joined by coloured links (this is the alignment), (3) *where it breaks*
("a real server can't ask people to come back tomorrow; it drops or blocks"). Schema field:
`analogy: {source, target, maps: [[src_part, tgt_part]...], breaks: [str]}`. The generator is
required to fill `breaks` (non-empty); the validator rejects an analogy without it.

### 2.3 Picking an analogy for a systems concept

Rules that follow from the above:
1. Pick an analogy where the **relations** match: ordering, capacity, waiting, who blocks whom.
   Lead with a *worked example on a parallel toy*, which is already Luigi's best mode.
2. Use things he has lived: a restaurant pass, a supermarket checkout, a printer queue, a
   group chat, a bus stop. Avoid analogies that need domain knowledge he lacks.
3. One analogy per concept per video; reuse the same analogy for related concepts so it
   becomes a schema he owns (the restaurant for the whole ticket).
4. Prefer analogies that *have a failure mode* to map (full queue, slow cook), because the
   interesting engineering is in the failure.

Starter table (generator may propose others; all need `breaks`):

| Concept | Analogy | Maps | Breaks where |
|---|---|---|---|
| Queue / bounded buffer | Checkout lane with a rope line | cashier = consumer, shoppers = items, rope length = capacity | shoppers choose to leave; a server must decide (drop, block, reject) |
| Backpressure | Kitchen that stops taking orders when tickets pile up | pass = buffer, "86'd" = reject/slow producer | the host can see the pile; software often cannot unless signaled |
| Latency percentiles (p50/p99) | Pizza delivery times over a month | median vs the one-in-a-hundred late order | averages hide the late order; customers remember the worst one |
| Async / event loop | One waiter taking many tables | waiter = single thread, kitchen = I/O | waiter can't cook; if they cook a long dish the whole room waits |
| Cache | Your desk vs the filing cabinet | desk = fast small memory | stale papers: the cabinet may have changed |
| Batching | Elevator going up with everyone who is waiting | trade latency for throughput | elevators have no deadline per rider; requests do |
| Rate limit | Bouncer with a clicker | token bucket as tickets handed out per minute | bouncer is visible; clients get a 429 |
| Idempotency | Pressing the lift-call button twice | second press changes nothing | payment buttons are not naturally idempotent, you must make them so |
| Retries with backoff | Redialling a busy phone line after waiting longer each time | jitter = not everyone redials at the same second | phones don't have a thundering herd of 10,000 |

### 2.4 Pitfalls
- A cute analogy with no `breaks` beat leaves a durable misconception.
- Two analogies in one segment compete (coherence).
- Analogy as decoration: if the beat could be deleted and the video still made sense, delete it.

---

## 3. Gating progress on open answers

### 3.1 Findings

- **Mastery learning** (Bloom 1984, "2 sigma" claim; later meta-analyses show smaller but
  positive effects, roughly d = 0.5 [not re-checked]) supports "don't move on until you've
  got it" for prerequisite chains. A video is a chain (segment 3 uses segment 2), so a gate at
  a *load-bearing* point is justified; a gate at every point is not.
- **Productive failure** (Kapur): attempting a problem before instruction, even failing,
  prepares learning from the instruction that follows. Sinha & Kapur (2021, *Review of
  Educational Research*) meta-analysis: 53 studies, 166 comparisons, secondary and
  undergraduate students in STEM; the authors describe the effect as large when design
  fidelity is high (press summaries; pooled g not in the sources I could reach):
  https://techlearning.com/news/study-productive-failure-a-success-in-education . Note it
  was run mostly with conceptual maths/physics problems; transfer to "how would you handle
  this queue" is plausible, not proven.
- **Hint-ladder tutoring**: intelligent tutoring systems use graded hints (nudge, specific
  pointer, bottom-out) and measure help abuse; "gaming the system" (clicking through hints
  to get the answer) is a known failure mode that correlates with worse learning (Baker et al.
  2004 [not re-checked]). Cap hint rate with delay and escalate by miss count, not by button
  mash.
- **Frustration**: open-answer gates with a hidden accept condition feel like guessing the
  teacher's word. Mitigation: show *what kind* of answer is wanted ("name the failure and
  one way to handle it"), and treat "different but valid" as a pass.

### 3.2 Mechanic: the gate

Each question has `gate: "hard" | "soft"`.
- **Hard** (the next segment depends on it): ladder of 3 attempts, then the "show me the
  idea" resolution, recorded as `seen`, and the video continues, but the app notes it for the
  debrief and a later spaced re-ask. No dead end: after the bottom-out hint, he continues.
- **Soft** (nice to think about): wrong answer plays a one-line response and continues.

Attempt ladder for a hard question:
1. **Attempt 1 wrong or partial** -> `try_idea` branch (see 3.3), then hint 1 (a nudge: restate
   the situation or point at the key object in the diagram), then re-ask.
2. **Attempt 2 wrong** -> hint 2 (narrow: "think about what happens to request 4 specifically")
   plus a **worked example on a parallel toy** (the 20-second version with different numbers),
   then re-ask.
3. **Attempt 3 wrong** -> hint 3 = the intended idea told plainly, the question marked `seen`,
   a one-click "ask the teammate" to open a DM about it, and the video continues.
At any time: **"Skip for now"** (continues, marked `skipped`), **"Replay last segment"**, **"I'm
stuck"** (jumps to hint 2 directly). Rate-limit the "I'm stuck" button to avoid hint abuse
(10 s delay before hint 3).

### 3.3 Showing the consequence of his idea ("let's try your idea")

This is the most important mechanic and the one that makes the loop feel like a teammate and
not a quiz. When an answer is `partly` or `off_track`, the grader also returns a short
`idea_summary` (one sentence, in neutral words: "block the producer when full"). The
`try_idea` branch is one of:
- **Pre-authored per wrong idea**: the script lists 2-4 `common_wrong_ideas`, each with a
  prewritten 10-20 s branch (beats + visual ops) showing what happens. The grader maps his
  answer to one of them (or `none`). This is deterministic, cheap and safe for review stage.
- **Generic fallback**: if `none`, the player shows the generic "let's trace it" beat, a
  stepper over the same widget with his idea described in one sentence as a label on a toggle
  ("your idea: drop the newest request"), and the diagram runs with that rule. Only possible
  for widgets with a small rule vocabulary (queue: block / drop-new / drop-old / grow).
  Never free-form simulation by LLM.
Then the character says "so with that, request 4... [lost]. What would you change?" That is
productive failure in 20 seconds.

### 3.4 Valid-but-different answers

Do not require his idea to match the script's. The rubric (section 4) lists `key_ideas`
(must be present) and `acceptable_alternatives` (other ways to meet the same need), and the
grader has a `different_but_valid` verdict whose response is explicit: "That also works. Mine
was X; yours trades Y for Z." Show the video's approach *after* acceptance as a comparison
card. If the grader is unsure it returns `cant_tell`, and the player says "I can't tell from
that; say a bit more about what happens to the 4th request" (one clarification turn, doesn't
count as an attempt).

### 3.5 Pitfalls
- Silent hard gate with no escape: leads to quit/restart. Always provide the escape hatch.
- Too many gates: more than one per ~90 s becomes annoying; the Kovacs data shows 74% attempt
  rates at ordinary densities, so we budget.
- Congratulating everything: praise only on `works`; for `different_but_valid` say what is
  different.

---

## 4. Checking his open answer with an LLM

### 4.1 Findings on reliability

Recent studies disagree, and the disagreement is the finding:
- A small study with the marking rubric in the prompt (GPT-4, 30 pharmacology answers)
  reported r of .93-.96 with examiners and ICC .94, with the authors flagging the small
  sample (as summarised by search; original not opened).
- A 2025 postgraduate medical preprint (ChatGPT-4o, 557 answers) found systematically lower
  marks than humans (bias about -1.3 of 10) and poor individual agreement (ICC about .09):
  https://arxiv.org/abs/2505.04645v1
- A *J. Computer Assisted Learning* study (232 answers; GPT-4o, Gemini 2.0 Flash, DeepSeek
  V3, Llama 3.3) found only moderate LLM-human agreement on total scores (QWK .585-.640) and
  worse agreement for higher cognitive complexity; LLMs "suitable for basic comprehension
  checks" (search summary).
- A Purdue-style analysis of rubric-conditioned grading finds brittleness to harmless
  rewordings: https://arxiv.org/html/2601.08843v1 (search summary).
- Not found in this session: a specific paper on code-reasoning short answers. Fine; the
  point is "test your own grader on your own data".

What generalises: (a) answers about *whether an idea would work* are closer to "comprehension"
than "evaluation", so they are the grader's easy case; (b) the grader fails at
**calibration** (too lenient or too harsh) more than at gross error; (c) rewordings flip
borderline cases.

### 4.2 Mechanics for our grader

1. **Rubric is generated with the script**, in the same call, as structured data:
   `key_ideas` (list of claims; an answer needs at least `need: k` of them),
   `acceptable_alternatives` (other mechanisms that satisfy the requirement, e.g. "bounded
   queue + reject with 429", "drop oldest", "shed load at the load balancer"),
   `common_wrong_ideas` (each with a short explanation of why it fails, and a `branch` id),
   `must_not` (statements that make an answer wrong even if a key idea appears).
2. **Separate grader from persona**, as `explain.py` already does. The grader prompt sees:
   the question, the rubric, his answer, and the *facts list* (so it can check a claim about
   the code). It does not see the persona, the chat, or the narration. Output is strict JSON:
   `{verdict, key_ideas_hit:[ids], wrong_idea_id|null, idea_summary, confidence, quote}`
   where `quote` is the exact span of his answer that justifies the verdict. The server
   rejects a verdict whose `quote` is not a substring of his answer (cheap sycophancy brake).
3. **Anti-sycophancy**:
   - The grader is told to default to `partly` if a key idea is not stated in his own words,
     and to ignore politeness, confidence and length.
   - Always require the `quote`. No quote, no pass.
   - Include 3-5 *adversarial test answers per question class* in the test suite (a confident
     wrong answer; a vague "add a queue"; an answer that copies the question; an answer that
     says "it depends"). Run them in CI against the grader prompt on each prompt change, as
     `tests/test_grader_regression.py`. Calibration checks: the rate of `works` on known-wrong
     answers must be 0 of N on the fixture set.
   - Two-vote variant for hard gates: if the first verdict is `works` with confidence < 0.8,
     run once more with a rewritten (paraphrased) rubric; require agreement. Costs one more
     Haiku call only on borderline cases.
4. **Click answers need no LLM**: option -> verdict is a table lookup in the script.
5. **Code-checkable answers**: when the question is "what does this return?", run it
   (section 7) rather than ask a model.
6. **Latency budget.** Target <= 3 s to verdict. Haiku with ~600 input tokens and a 100-token
   JSON output through `claude -p` typically costs process start-up (about 1-2 s in the
   existing runner [measure it]) plus generation. To keep the pause from dragging:
   (a) pre-warm: keep one idle Haiku grader process hot or spawn it when the question
   appears, not when he submits; (b) while it runs, the character plays a "hmm, let me
   think" idle animation (the 7 portrait expressions already cover it) with the text "checking
   your idea"; (c) stream the verdict's `idea_summary` first so the character can echo it
   ("so you'd drop the oldest request..."); (d) if no verdict by 6 s, offer "keep waiting / skip".
   Measure in a spike before promising: [not measured].
7. **Voice input** goes through the same grader after transcription (section 6e), with the
   transcript shown for correction before it is graded; ASR errors on jargon would
   otherwise look like wrong answers.

### 4.3 Pitfalls
- A grader that sees the persona's script wording will reward echoing it. Keep it blind to
  the narration; give it only the rubric.
- A rubric written *after* seeing a failing answer drifts. Freeze it at script validation.
- Over-trusting: log every verdict + his answer + rubric id to a table; show "disagree?" on
  the verdict screen; a click on it records the case and lets him pass. The disagreements
  become the next regression fixtures.

---

## 5. Explaining research papers

### 5.1 How experts read: Keshav's three passes

S. Keshav, "How to Read a Paper" (ACM SIGCOMM CCR 2007) [not re-checked, from memory]:
- **Pass 1 (5-10 min)**: title, abstract, intro, section headings, conclusions; answer the
  "five Cs": category, context, correctness (assumptions), contributions, clarity.
- **Pass 2 (up to an hour)**: figures, graphs, main method; ignore proofs; mark references.
- **Pass 3 (hours)**: re-implement mentally, challenge every assumption.
The explainer should deliver a *guided pass 1 and the entry to pass 2*, never pretend to be
pass 3.

### 5.2 What a good explainer covers

Five beats, always in this order, one segment each (the fifth optional):
1. **The claim** in one sentence, and what the baseline was ("X is N times faster than Y on Z").
2. **Why it matters** for someone who runs this in production, tied to *his ticket*
   (the experiment ticket says "try paged KV cache"; the paper's claim is the reason).
3. **Method intuition**: one analogy (section 2) plus a diagram of the mechanism on a toy
   with small numbers.
4. **The key number** with context: what was measured, on what hardware, against what, with
   what error bars; the figure or table from the paper rendered as a `table`/`chart` widget with
   the *quoted* values.
5. **Assumptions and limits**: what the paper doesn't show; what would make the number not
   transfer to the ticket (batch sizes, model sizes, hardware).
Question at the end of segments 1, 4 and 5: predict the direction of an effect
("with batch size 1, would the speed-up be bigger or smaller?"), then reveal.

### 5.3 Grounding so the explainer doesn't hallucinate

- Extract text with section tags (pymupdf / `pdftotext -layout` [not re-checked for the
  quality of our extraction]; tables are the weak spot, so numbers from tables are cited
  from the table text, or the beat is flagged "read the table yourself").
- Pass the paper text as *numbered passages*; the generator must output `cites: [p17]`; the
  server checks the quoted span (`quote` field, <= 25 words) appears in passage p17 after
  whitespace normalisation. A claim beat without a valid cite is dropped, or the whole script
  is regenerated once.
- Numbers on screen must come from `facts` (a list of `{id, text, source}`) the server built
  from the paper text with a regex/number extractor, not from the model's memory. The
  model may *choose* among them, not invent them.
- For long papers, summarise by section in parallel (Haiku), then write the script with
  Sonnet from the section summaries plus the original passages the script cites.
- Cache by the paper's content hash so two tickets citing the same paper share a script
  (re-voiced if personas differ).

### 5.4 Pitfalls
- LLM summaries of abstracts overstate; prefer experiments and limitations sections.
- A paper explainer that never says what the paper does **not** show.
- Do not let the explainer pre-solve the experiment ticket (it is his work); explain the
  idea, not the implementation plan (parallels the review-stage rule).

---

## 6. Ways to build it

### 6a. Pre-rendered Manim per ticket from the studio

What exists: `C:\Users\Owner\fundamentals-studio`: Manim + Kokoro + subtitles + widget library
(CodePanel with line highlight, MemoryRow, networking pieces, threads-as-receptionists),
Catppuccin theme. Render: 480p15 preview in "a few minutes", 1080p30 final longer (per its
README).

Pros: best visual quality; the widget library encodes hard-won style; works offline; zero
runtime cost once rendered.
Cons: hand-written scenes take hours per minute of video; render takes minutes per
scene, so "press a button, get a video" is not interactive; cannot branch (each "try your
idea" outcome is a separate render); changes to a script mean re-render; a pause point needs
the video split into files per segment, which can be done (the studio already has one scene
per chapter) but branching multiplies the files. Licence: Manim is MIT (ManimCommunity)
[not re-checked].
Verdict: use it for a *small number of hand-made, high-value explainers*, played in the
same player as a "video beat" with a pause question after it. Do not make it the pipeline.

### 6b. LLM-generated Manim on demand

Research systems:
- **TheoremExplainAgent** (Ku et al., ACL 2025): planner + coder agents produce Manim
  videos for 240 theorems (TheoremExplainBench). Best configuration (o3-mini) reached a 93.8%
  success rate, overall score 0.77; the authors' error analysis: Manim API hallucinations
  (nonexistent functions/properties/assets) most common, then LaTeX errors, then ordinary
  coding errors; even successful videos often had layout problems. They used RAG over Manim
  docs to cut errors. https://arxiv.org/pdf/2502.19400 , https://aclanthology.org/2025.acl-long.332
  (the "6.2% failure" is my arithmetic from their 93.8%, not a number they state).
- **Code2Video** (Chen, Lin, Shou, NUS Show Lab, arXiv 2510.01174, NeurIPS 2025 DL4Code
  workshop per the repo changelog): Planner + Coder (with scope-guided auto-fix) + Critic
  (a vision-language model looks at frames and refines layout); claims a 40% improvement
  over direct code generation; evaluated with TeachQuiz (can a VLM relearn the knowledge
  from the video). https://arxiv.org/pdf/2510.01174 , code https://github.com/showlab/Code2Video
  (an aggregator page labels it "ICML 2026"; unverified, ignore).
- Lessons for us: success rates are good for *theorem* videos with minutes of agent time
  and rendering; but both pipelines are tens of LLM calls per video plus render and critic
  loops (exact per-video figures not re-checked); layout defects survive; and no
  interactivity.
Pros: unlimited variety of visuals; reuses the studio's look.
Cons: minutes-to-tens-of-minutes per video, heavy usage on his plan (a coder + critic loop
is many calls, against "≤2 concurrent" and the 70%/90% governor); fragile (API
hallucinations, layout overlap) so a verification loop with frame inspection is needed;
no branching.
Verdict: reject as the on-demand path. Possibly useful as an *offline authoring aid* for a
new widget (let the agent draft a Manim scene which a human then curates).

### 6c. Browser-native interactive "live explainer" (recommended)

Design:
- **Script**: JSON (section 9). Generated by one agent call; validated by Pydantic; auto-repair
  on validation errors (one retry with the error messages, as TheoremExplainAgent's and
  Code2Video's fix loops do, but with a schema instead of a compiler, so failures are
  cheap and legible).
- **Player**: a state machine in the web app: `idle -> beat(n) -> segment_end ->
  question -> checking -> {branch | hint | continue} -> ...`. Each beat starts the audio
  (HTMLAudioElement, `ended` event advances), fires visual ops via Motion variants and
  SVG, and sets portrait expressions. Pausing is just not advancing; branching is jumping
  to another beat id.
- **Narration**: Kokoro on the server, per line, cached by `(voice, text_hash)` like the
  studio's `cache/voice`. Pre-synthesise all lines of a script right after validation
  (parallel on GPU or CPU). Per Kokoro benchmarks quoted by hosting vendors, GPU real-time
  factor is about 0.01-0.03 (i.e. a 10-second sentence in 0.1-0.3 s) but those are vendor
  marketing pages with no RTX 4070 figure (https://gigagpu.com/?p=1841 , https://tts.ai/voices/kokoro/);
  measure on the 4070 and on CPU [not measured]. A 5-minute video is roughly 700 words, i.e.
  well under 30 s of synthesis even at pessimistic CPU speeds; start playing beat 1 as
  soon as it is ready (stream the rest).
- **Widget library (fixed)**, each a React component with a small op vocabulary:
  `Stage` (background image + character slots), `Character` (existing portraits,
  expression, talk-frame lip flap), `CodePanel` (line highlight, token pulse, diff view),
  `Queue` (slots, items, ops: push/pop/drop/block), `Timeline` (lanes, bars, markers; for
  latency, p99), `RequestArrow` (A -> B with label, color for success/fail, delay),
  `Table`, `Chart` (bars only), `Callout`, `AnalogyCard` (side-by-side with links),
  `Compare`, `Counter`. Each op has a duration, so beats are deterministic.
- **Backgrounds**: the generated office (tileset) rendered as a static image per room
  (kitchen, desk, meeting room) plus abstract panel backgrounds (grid, dark) for code.
  Phaser is available but heavy; a pre-rendered PNG per room plus CSS parallax is enough.
- **Why this is the best fit**: runs on the existing stack (React 18, Motion, Phaser, FastAPI,
  Kokoro); generated in seconds; branchable and replayable at beat granularity; cacheable
  (script JSON is a few KB, audio a few hundred KB); safe by construction (the generator
  cannot emit arbitrary code, only schema ops); the leak check and fact check run on
  structured data, which is much easier than on video.
- **Cost**: the widget library is the real work. Build 5 widgets first (Code, Queue,
  Timeline, RequestArrow, Callout), add more as scripts demand.

Pros: fast, interactive, cheap, testable (Playwright can play a script and screenshot a
beat; the repo already runs headless UI tests), accessible (subtitles = the narration text).
Cons: less cinematic than Manim; the visual vocabulary is bounded by the widgets (that is
also its safety and its coherence); needs a good "director" prompt so scripts don't feel
slideshow-like.

### 6d. Code-based animation libraries for the browser

| Library | Licence | Fit | Notes |
|---|---|---|---|
| **Motion** (already used, MIT) | MIT | Core of the player | Variants + `animate()` sequences cover widgets; no extra dep |
| **Motion Canvas** | MIT (listed as MIT by AlternativeTo and Smithery; check its repo LICENSE before shipping) | Authoring tool for scenes with generator functions, closest to Manim in feel, TypeScript | Is an *editor + renderer to video*, awkward to embed in an interactive app; useful if we ever want TS-authored flagship scenes |
| **Revideo** | Repo README states MIT (checked via GitHub fetch; repo now appears under `redotvideo/revideo`, an older link `midrender/revideo` also appeared) | A Motion Canvas fork turned into a library, headless video rendering in Node | Good for *server-side rendering of a script to MP4* (e.g. if he wants to keep a video of a script); not needed for the live player |
| **Remotion** | Source-available custom licence; the free tier covers individuals, non-profits and for-profit organisations with up to 3 employees; paid tiers for 4+ (pricing page: Creators $25/mo per seat, Automators $100/mo minimum, as found via search); licence said to change slightly in 5.0 | React-based video; would fit our stack | Free for Luigi as an individual and not redistributable as a derivative product; check licence text before depending on it, and Offer Letter is not meant to be sold anyway. https://remotion.dev/license . Still not recommended: it is a *render-to-video* model, we need a live player |
| **Theatre.js** | `@theatre/core` Apache-2.0; `@theatre/studio` AGPL-3.0 (checked: GitHub README) | Timeline-based animation, keyframes | The AGPL studio is dev-only, but keep the repo's rule "MIT where we can": skip, Motion suffices |
| **Rive** | Runtime MIT, editor is proprietary/free tier [not re-checked] | Interactive character animation with state machines | Good if we want a *rigged* character later; our portraits + expression swaps are enough |
| **Lottie** (lottie-web / dotLottie) | MIT [not re-checked] | Pre-made vector clips (e.g. a "thinking" loop) | Needs After Effects or a Lottie editor to author; skip for v1 |
| **Ren'Py-style script ideas** | Ren'Py itself is MIT/LGPL [not re-checked]; we copy ideas only | See below | |

Ideas to borrow from visual-novel engines (Ren'Py, Ink, Yarn): a script is a flat list of
statements (`show`, `say`, `menu`, `jump`, `label`), choices are `menu` entries with jumps,
state is tiny variables, and "rollback" (go back one beat) is built in. Our JSON should
look like that rather than a nested animation timeline. Also borrow the "say" statement's
inline tags (`{w}` wait, `{p}` pause) to align visual ops with words.

### 6e. Speech-to-text for "say your answer", and TTS latency

- **Model**: faster-whisper (CTranslate2) on the RTX 4070. Secondary pages (not primary
  benchmarks; they conflict) report large-v3 at about 12x real time with int8 and ~2.5 GB
  VRAM on a 4070, and distil-large-v3 about 6x faster again than large-v3, with English
  WER about 2.6% vs 2.5% on clean read speech; large-v3-turbo (4 decoder layers) is the
  recommended low-latency choice for voice (sources: https://www.promptquorum.com/es/power-local-llm/local-whisper-stt-comparison ,
  https://jisaku.com/posts/ai-bench-faster-whisper-speed-2026 , search summaries). Even with the pessimistic
  number, a 10-second spoken answer transcribes in about 1 s on a 4070. **No source found
  for accuracy on programming jargon**: expect errors on "gRPC", "kubernetes", "p99",
  "idempotent", "Kafka". Mitigation: Whisper accepts an `initial_prompt` of domain words
  (supply the ticket's glossary), and always show the transcript editable before grading.
- **Capture in WebView2**: `navigator.mediaDevices.getUserMedia({audio:true})` works in
  WebView2; the first use shows a permission prompt, and Tauri 2 needs the WebView2
  permission handler to remember it [not re-checked on Tauri 2.x]. Record with
  `MediaRecorder` to webm/opus or an AudioWorklet to 16 kHz PCM; POST the blob to the
  server (`/api/stt`); server runs faster-whisper. A push-to-talk key (hold Space or a held
  button) avoids needing VAD in v1.
- **VRAM**: Kokoro (~1.5 GB per the tts.ai page) + faster-whisper large-v3-turbo int8
  (about 2 GB) on a 12 GB card, leaving room for the game and browser. Load STT on first
  use; unload after idle.
- **Latency target**: press release -> transcript on screen <= 1.5 s, then the grader
  <= 3 s: about 4-5 s total from "done talking" to verdict. Acceptable; show the
  transcript immediately.
- **Pitfall**: do not synthesize OS input or record the whole screen (repo rule 6). Mic
  capture is not that; it is the app asking the browser for audio. Mention in the settings
  panel that the mic is only live while the button is held.

### 6f. Comparison and decision

| | Pre-rendered Manim | LLM Manim on demand | Live explainer (c) |
|---|---|---|---|
| Time to first view | hours-days authoring | many minutes per video | seconds to a minute |
| Branching/pausing | files per branch | files per branch | native |
| Visual ceiling | highest | high but fragile | medium, consistent |
| Plan usage per video | 0 after authoring | high (many calls + critic) | low (1 Sonnet + few Haiku) |
| Testability | manual review | hard | schema + Playwright |
| Leak control | author-checked | hard | server-checkable text |
| Licence risk | Manim MIT | Manim MIT | Motion MIT |
Decision: (c) with Manim as an optional embedded `video` beat for hand-made flagship content.

---

## 7. Correctness of generated explanations

Risks: the explainer invents what the code does; mis-states a library API; invents a number;
leaks a review answer.

### 7.1 Fact list, not free text

Before generation the server builds `facts`:
- **From the diff**: changed files, hunks with line numbers, added/removed function names,
  signatures and call sites (Python `ast` for `.py`; `tree-sitter` or `ctags` for other
  languages [not re-checked]), imports, and configuration values. Each fact:
  `{id:"F12", kind:"function_added", file, lines:[a,b], text}`.
- **From running code**: for short, side-effect-free snippets the explainer wants to show
  output for, the server runs them in the same sandboxed way as the kit verifier
  (`verify_kit.py` already proves answers by running commands) and stores `{id:"F20",
  kind:"run_output", cmd, stdout}`. Any "this prints X" claim must cite such a fact.
- **From the ticket/paper**: quoted spans with ids (section 5.3).
- The generator must reference facts by id in `cites`; the validator drops any beat whose
  claim kind (`code_behaviour`, `number`, `quote`) has no cite. Beats of kind `concept` or
  `analogy` need no fact but are marked as "teaching, not code claims".

### 7.2 Checks, cheapest first

1. Schema validation (Pydantic): beat ids unique, jumps resolve, widget ops legal, durations
   bounded, no URLs, no HTML, text length limits.
2. **Cite check**: every cited id exists; quoted spans are substrings of the source.
3. **Line check**: `code` ops reference real lines of the cited file and hunk; highlights
   match.
4. **Run check**: claims of type `run_output` match what the server ran.
5. **LLM claim audit (optional, Haiku)**: given only `facts` and the narration, flag
   narration sentences that assert something not entailed by a fact or marked as concept. This
   is a second pair of eyes; it doesn't replace 1-4.
6. **Leak check** (section 7.3).
Failure of 1-4 triggers one regeneration with the error list; a second failure returns a
"can't explain this one right now" card and offers the plain-text "what does this code do"
(the current feature), so the button never gives nothing.

### 7.3 Stopping review answer leaks

The existing rule: in review stage the AI explains "what does this code do / teach the
construct", never "what's wrong". Enforcement for videos:
- **Structural**: the generator prompt in review stage receives the diff, the facts and the
  ticket text; it does **not** receive the answer key, hidden tests or `reference/` fix.
  Server-only data stays in `.data/kits/` (CLAUDE.md rule 4).
- **Allowed beat kinds** in review stage: `what_it_does`, `concept`, `analogy`, `trace`
  (walk an input through the code). Disallowed: `critique`, `risk`, `fix`. Schema enforces
  by stage, not by prompt alone.
- **Allowed question kinds** in review stage: `predict_output`, `concept_check`, `explain_back`.
  No "what could go wrong here?".
- **Automatic leak check, server side, after generation**: for each planted bug the key stores
  its `file`, `line range`, a short description and a set of keywords. The check flags a
  script if (a) any `code` op highlights lines inside a planted-bug range while the
  narration uses evaluative words (bug, wrong, off by one, missing, unsafe, should), (b)
  narration or question text has high token overlap with a key description, or (c) an
  LLM judge (Haiku, sees *only* the key and the narration, not the code) says the narration
  would help him find any listed bug. Trigger -> regenerate with "avoid lines X-Y" or
  fall back to the concept-only video. This is the same "separate grader" idea turned
  around.
- **A planted-bug line may still be explained** (a PR reader must understand all the lines)
  but only with neutral description ("this loop reads the file in chunks") and no
  highlighting that singles it out among peers: the highlight op in review mode steps
  through *all* changed hunks in order at equal emphasis (a "walk the diff" mode), so
  attention is not steered.
- **Log** every generated script with its stage and leak-check result.
- **Residual risk**: a concept video about, say, "integer overflow" may hint at an overflow bug.
  Mitigation: in review stage the concept list is restricted to concepts *present in the
  code's constructs* and not in the bug key's `concepts` list; if a needed concept overlaps,
  the server downgrades to a one-line glossary card.

### 7.4 After review
Unlock `critique` and `fix` kinds, plus "why this failed in production" stories. Still no
writing his change for him: the explainer may show a *parallel toy* fix, not his code.

---

## 8. Usage cost on his Claude plan, and caching

Rough budget (assumptions, to be measured with the governor's `rate_limit_event` readings):

| Call | Model | Tokens in / out (est.) | When |
|---|---|---|---|
| Fact extraction | none (Python) | 0 | every time, free |
| Script generation | Sonnet | 4-8k in (diff slices, facts, schema, 1 gold example) / 2-4k out | once per artifact+stage+level |
| Repair retry | Sonnet or Haiku | 3-5k in / 2-4k out | ~20-30% of runs [guess] |
| Claim audit | Haiku | 2-3k in / <300 out | optional |
| Leak judge | Haiku | 1-2k in / <200 out | review stage |
| Answer check | Haiku | 0.5-1k in / <150 out | per open answer, 1-3 per video |
| Paper section summaries | Haiku | 3-8k in each, 3-6 sections | once per paper |

So a video is about 1 Sonnet turn plus 5-10 Haiku calls. On a plan with a 5-hour window, that
is on the order of a normal code-review turn per video, not a heavy session. The numbers
above are my estimates, not measurements; the first spike should log real
`rate_limit_event` deltas.

Governor rules:
- At 70% (thrifty): serve cached scripts only; generation uses Haiku with fewer beats
  (a "short explainer": 2 segments, click questions only); grading unchanged (cheap).
- At 90% ("out to lunch"): button shows the plain-text fallback and "video available when
  [teammate] is back".
- Count against the 2-concurrency limit: script generation is one process; answer checks
  wait their turn; pre-warm graders only when under 70%.

Caching and reuse:
- Key `(artifact_kind, artifact_hash, stage, level, script_schema_version)` where
  `artifact_hash` = hash of PR diff / ticket text / paper text. A new push to the PR changes
  the hash and invalidates the cache.
- Store the validated script JSON in SQLite and the audio under `.data/explainers/<hash>/`.
- Reuse concept-only segments across tickets: a "bounded queue" segment is keyed by
  `concept_id` and `analogy_id`, and can be spliced into any video that needs it. A small
  library (grows by use) means the second PR touching queues costs almost nothing. Mark a
  reused segment's `source: library`.
- Pre-generation: after a PR is created (and the leak check passes), generate the
  review-stage video in the background when the governor is under 50%, so the button is
  instant. Cheap because the cache is keyed on the diff.
- Voice cache: `(voice, normalised text)` -> wav; the same line in two scripts costs nothing.

---

## 9. Proposed script JSON shape

One script. Comments are explanatory only (JSON does not allow them).

```json
{
  "schema": "explainer/1",
  "id": "exp_9f2c...",
  "artifact": {"kind": "pr", "ref": "kilnworks/api#14", "hash": "sha256:..."},
  "stage": "review",                       // review | plan | build | post_review | paper
  "level": "intermediate",
  "title": "What this PR changes, in a restaurant",
  "est_seconds": 270,
  "glossary_pretrain": [{"term": "bounded queue", "gloss": "a waiting line with a maximum length"}],
  "facts": [
    {"id": "F1", "kind": "function_added", "file": "api/jobs.py", "lines": [12, 31],
     "text": "enqueue() appends a job to a list and returns its position"},
    {"id": "F2", "kind": "run_output", "cmd": "python -c '...'", "stdout": "[1, 2, 3]"}
  ],
  "characters": {
    "mara": {"persona": "kilnworks.mara", "voice": "af_heart", "role": "narrator"},
    "theo": {"persona": "kilnworks.theo", "voice": "am_adam", "role": "asks_naive_question"}
  },
  "segments": [
    {
      "id": "s1",
      "title": "What enqueue does",
      "beats": [
        {
          "id": "s1b1",
          "say": {"who": "mara", "text": "Picture a checkout lane with a rope line.",
                  "expr": "neutral", "voice_speed": 1.0},
          "stage": {"background": "office/kitchen", "slots": {"left": "mara", "right": null}},
          "ops": [
            {"at": "start", "do": "show", "widget": "analogy_card", "id": "a1",
             "props": {"source": "checkout lane", "target": "job queue",
                       "maps": [["cashier", "worker"], ["shoppers", "jobs"]]}},
            {"at": "word:rope", "do": "pulse", "target": "a1.shoppers"}
          ],
          "kind": "analogy",
          "cites": []
        },
        {
          "id": "s1b2",
          "say": {"who": "mara", "text": "In the PR, enqueue adds one job to the end of the list."},
          "ops": [
            {"at": "start", "do": "show", "widget": "code",
             "props": {"file": "api/jobs.py", "lines": [12, 31], "mode": "walk"}},
            {"at": "word:adds", "do": "highlight", "target": "code", "lines": [15, 17]}
          ],
          "kind": "what_it_does",
          "cites": ["F1"]
        },
        {
          "id": "s1b3",
          "say": {"who": "mara", "text": "Here is where the analogy stops: a real worker can't ask jobs to come back tomorrow."},
          "kind": "analogy_breaks",
          "ops": [{"at": "start", "do": "show", "widget": "callout",
                   "props": {"text": "Jobs can't wait forever"}}]
        }
      ],
      "question": {
        "id": "q1",
        "kind": "predict_choice",            // predict_choice | predict_output | open | explain_back
        "gate": "hard",                      // hard | soft
        "allowed_in_stage": ["review", "post_review"],
        "prompt": "The lane holds 3 people and 5 arrive at once. What happens to person 4?",
        "ask_character": "theo",
        "options": [
          {"id": "o1", "text": "They get in line", "verdict": "wrong", "wrong_idea": "w_unbounded"},
          {"id": "o2", "text": "They are turned away or must wait outside", "verdict": "right"},
          {"id": "o3", "text": "It depends on the code", "verdict": "partly", "feedback": "True; so what choice has to be made?"}
        ],
        "reveal": {"beats": ["s1r1", "s1r2"]}
      }
    },
    {
      "id": "s2",
      "title": "How would you handle a full queue?",
      "beats": [ ],
      "question": {
        "id": "q2",
        "kind": "open",
        "gate": "hard",
        "prompt": "If this lane can't grow, what should the system do with person 4? Give one way and what it costs.",
        "input": ["type", "voice", "click_chips"],
        "chips": ["Reject with an error", "Make them wait", "Drop the oldest", "Add more cashiers"],
        "rubric": {
          "need": 1,
          "key_ideas": [
            {"id": "k1", "text": "Names a specific behaviour when the queue is full (reject, block, drop, or shed load)"},
            {"id": "k2", "text": "States a cost or trade-off of that choice"}
          ],
          "acceptable_alternatives": [
            "Bounded queue and return 429/503",
            "Block the producer until space frees (backpressure)",
            "Drop oldest or lowest priority",
            "Scale workers / add capacity, provided the answer admits the queue is still bounded"
          ],
          "common_wrong_ideas": [
            {"id": "w_unbounded", "text": "Just make the queue bigger / unbounded",
             "why_fails": "Memory grows until the process dies and latency grows without limit",
             "branch": "t_unbounded"},
            {"id": "w_ignore", "text": "Nothing special happens", "why_fails": "...", "branch": "t_silent_drop"}
          ],
          "must_not": ["claims the queue is infinite"],
          "answer_key_ref": null
        },
        "try_idea": {
          "branches": {
            "t_unbounded": {"beats": ["t1b1", "t1b2"], "widget_rule": {"queue": "grow"}},
            "t_silent_drop": {"beats": ["t2b1"]}
          },
          "generic": {"widget": "queue", "rules": ["block", "drop_new", "drop_old", "grow"]}
        },
        "hints": [
          {"rung": 1, "type": "nudge", "text": "Look at the rope. It has a length."},
          {"rung": 2, "type": "worked_toy",
           "beats": ["h2b1", "h2b2"], "note": "same question on a pizza oven with 2 trays"},
          {"rung": 3, "type": "tell", "text": "The usual answers are: reject, make the sender wait, or drop something. Each has a cost."}
        ],
        "on_pass": {"say": {"who": "theo", "text": "Right, and that cost is what the PR author had to choose."}},
        "on_valid_different": {"say": {"who": "mara", "text": "That works too. Mine trades X for Y."}},
        "on_skip": {"mark": "skipped", "resurface": "debrief"},
        "max_attempts": 3
      }
    }
  ],
  "closing": {"kind": "explain_back",
              "prompt": "In one sentence: what does this PR change?",
              "uses": "explain.py"},
  "meta": {"generator": "sonnet", "prompt_version": "v1", "leak_check": "pending"}
}
```

Notes on the shape:
- `ops[].at` is `start`, `end`, `word:<token>`, or `t:<ms>`; the player resolves `word:` by the
  Kokoro word timestamps if available [Kokoro's pipeline can return token timestamps in some
  versions; not re-checked], otherwise by proportional position in the sentence.
- `kind` tags drive the review-stage filter (7.3).
- `answer_key_ref` is always `null` in the script; the key never enters the generator or the
  script. The leak check reads the key by id on the server.
- The `facts` block is part of the script so the client can show a "where does this come
  from?" popover (citing file and lines) to build trust.
- Branches and hints reference beat ids; beats live in a flat `beats_by_id` map in a real
  implementation (shown inline above for readability).

### Runtime loop

```
load(script) -> preload audio for segment 1
for segment in segments:
    play each beat: audio + subtitles + ops
    controls: pause, back-one-beat, replay segment, 0.75-1.5x, subtitles toggle
    if segment.question:
        pause video; show question UI (chips/choices; open box with mic button)
        attempts = 0
        loop:
            answer = wait_for_user()                 # or Skip / I'm stuck / Replay
            if skip:     mark skipped; break
            verdict = table_lookup(answer) if click else grader(answer, rubric, facts)
            # grader returns within ~3 s; character plays "thinking" idle meanwhile
            if verdict in (works, different_but_valid): play on_pass / on_valid_different; break
            if verdict == cant_tell: ask one clarification (not counted); continue
            attempts += 1
            play try_idea branch (matching wrong idea, or generic widget run)
            if attempts >= max_attempts: play hint rung 3 (tell); mark seen; break
            play hint rung = attempts, then re-ask
    continue to next segment
closing: explain_back via explain.py grader; show summary card
record: per-question results {passed|different|seen|skipped, attempts} -> db -> debrief
```

Edge handling: if the grader errors or times out, treat as `cant_tell` once, then offer "skip
for now" (never fail closed forever); if audio fails, show subtitles and advance on a timer
based on word count; if a widget op fails validation at runtime, drop the op and log, never
crash the player.

---

## 10. Anti-patterns

1. **Rendering video for something that must pause and branch.** Files per branch, minutes
   per change.
2. **Letting the model free-write animation code at runtime.** Fragile (TheoremExplainAgent
   found hallucinated API calls the top error), unsafe, slow.
3. **Characters as decoration** (image principle). They must point, look, react.
4. **Reading the screen aloud**, or showing a whole paragraph while speaking it (redundancy).
5. **A hard gate with no exit.** He will quit and restart.
6. **Praise on every answer.** Praise only for `works`; for `different_but_valid` say what's
   different; for wrong, show what would happen.
7. **One grader prompt sharing context with the narrator persona** (echo bias).
8. **Trusting the first verdict on a borderline answer** without a quote check.
9. **Analogy with no "where it breaks"** beat.
10. **The explainer pointing at the planted bug** by highlighting it differently, by asking
    "what could go wrong here", or by choosing a concept that exists only in the bug key.
11. **A video longer than ~6 minutes** (Guo et al.: shorter is more engaging).
12. **More than one question per ~60-90 s**, or questions that are re-recall of the narrator's
    last sentence (low value, Kovacs's quiz-skipping behaviour).
13. **Numbers from the model's memory.** Numbers come from the facts list.
14. **Pre-solving his experiment/implementation.** Explain the idea; the work stays his.
15. **XP, streaks, badges for finishing videos.** Violates D1. Use debrief consequences.
16. **Generating at 90% usage.** Fall back to cached/plain text.
17. **Building the generator before the player.** Hand-write one script first.

---

## 11. Open questions for Luigi

1. **Where does the button live** (PR view header, ticket page, inside the paper link)? And
   should it ask "how deep?" (30-second gist vs 4-minute walk) or choose from the stage?
2. **Voice vs typing**: is "say your answer" worth building in v1, or is clicking chips plus
   an optional typed box enough? (Voice adds STT, mic permission in WebView2, and
   jargon-error handling.)
3. **Who narrates?** The teammate who owns the ticket, or a neutral "guide" character used
   only for explainers? Same voice as in chat (pending blind test)?
4. **Two characters (dialogue) or one narrator** per video? Dialogue models the naive
   question but costs more screen and attention.
5. **Hard gates**: OK that after 3 misses the video shows the idea and continues, marked
   "seen"? Or do you want to be stopped until you can say it?
6. **Review-stage rules**: should the review video ever offer "what could go wrong" on
   *other* code (a parallel toy PR) as a safe way to practice? That teaches the skill
   without touching the planted bugs.
7. **Replays**: should the app resurface "seen/skipped" questions in the debrief or as a
   spaced re-ask a few days later?
8. **Visual style**: Catppuccin clean panels (like the studio) for diagrams, pixel office
   for analogies; or all pixel? Is a Manim-quality hand-made flagship video for a few
   concepts worth the hours?
9. **Usage budget**: how many Sonnet generations per day are you willing to spend on
   explainers? (This decides pre-generation after PR creation.)
10. **Papers**: pasted PDF only, or may the app fetch arXiv by id? (Network access rule
    for the server.)
11. **Subtitles**: default on or off?

---

## 12. Sources (consolidated)

Verified this session (search or fetch):
- Szpunar, Khan, Schacter 2013 PNAS: https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699/
- Guo, Kim, Rubin 2014: https://www.cs.rochester.edu/hci/pubs/pdfs/edX-MOOC-video-production-and-engagement_LAS-2014.pdf
- Kovacs 2016: https://hci.stanford.edu/publications/paper.php?id=314
- In-video questions in a programming course (Cambridge): https://www.repository.cam.ac.uk/handle/1810/248411
- Brame 2016: https://pmc.ncbi.nlm.nih.gov/articles/PMC5132380/
- Mayer principles, social-cue chapter: https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-based-on-social-cues-in-multimedia-learning/093C1CDE75CF486DACD4CABC325ABE47
- Pedagogical agents chapter: https://core-cms.cambridgecore.org/core/books/cambridge-handbook-of-multimedia-learning/multimedia-learning-with-animated-pedagogical-agents/B629E8948494D949DB818B4AB31F3B4F
- Sinha & Kapur 2021 (press summary only): https://techlearning.com/news/study-productive-failure-a-success-in-education
- LLM short-answer grading: https://arxiv.org/abs/2505.04645v1 ; https://arxiv.org/html/2601.08843v1
- TheoremExplainAgent: https://arxiv.org/pdf/2502.19400 ; https://aclanthology.org/2025.acl-long.332
- Code2Video: https://arxiv.org/pdf/2510.01174 ; https://github.com/showlab/Code2Video
- Remotion licence: https://remotion.dev/license ; https://www.remotion.dev/docs/license/faq
- Revideo (MIT per README): https://github.com/redotvideo/revideo ; docs https://docs.re.video/
- Theatre.js (core Apache, studio AGPL): https://github.com/theatre-js/theatre
- faster-whisper speed claims (secondary): https://www.promptquorum.com/es/power-local-llm/local-whisper-stt-comparison ; https://jisaku.com/posts/ai-bench-faster-whisper-speed-2026
- Kokoro speed claims (vendor pages): https://gigagpu.com/?p=1841 ; https://tts.ai/voices/kokoro/

Cited from memory, [not re-checked]: Gentner 1983 structure-mapping; Glynn TWA model;
Richland, Zur & Holyoak 2007 (Science); Richland & Simms 2015; Bloom 1984; Baker et al. 2004
on gaming the system; White & Gunstone POE; Fiorella & Mayer 2015; Schroeder et al. 2013
(seen only via a search summary); Vural 2013; van der Meij; Haagsman et al. 2020; Keshav 2007;
Motion Canvas licence (MIT per two aggregator pages); Rive, Lottie, Ren'Py licences;
Tauri 2 mic permission behaviour in WebView2.

Measurements to take before committing (none done here): Kokoro seconds per sentence on the
4070 vs CPU; `claude -p` Haiku cold-start latency for a 150-token JSON answer; faster-whisper
latency and jargon error rate on 20 recorded answers; real `rate_limit_event` cost of one
script generation.
