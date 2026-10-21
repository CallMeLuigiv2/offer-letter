# Plan review eval (2026-10-21)

Real runs: Sonnet for each review, Haiku for replies, through `offerletter.plan_review`.

## S1 gappy plan

**Intent:** I read your plan as: take Theo's branch, apply the review fixes plus Amara's asks (late-send count in the report, p99.9, a max-in-flight flag with a warning), and show late sends in the text report via render_text. Right? The done-state and the counting part are still blank.

**Q1** ({'type': 'step', 'id': 's3'}): Step 1 prints late sends, but step 3 is what counts them, and it takes and gives nothing. What does step 3 look at, and does it run before the report is printed?  
_why:_ If nothing produces the late-send count before render_text runs, the report line has nothing to show.

**Q2** ({'type': 'example', 'id': 'e1'}): Example e1 expects "late sends: 3". What in the run schedule makes exactly three sends late, and what does the report say when none are late?  
_why:_ Without a known input that gives a known count, and a zero case, nobody else can tell whether the count is right.

Automatic: intent first OK, <= 2 questions OK, no code (guard) OK, no fallback OK, no leak words OK

## S2 solid plan

**Intent:** I read your plan as: keep the scheduled and sent time on every request record, count the sends that left late in summarize so JSON and text show the same number, and print one warning when the in-flight cap is hit. Is that right?

**Q1** ({'type': 'example', 'id': 'e3'}): Example e3 checks for a max-in-flight warning, but no step adds the flag or prints the warning. Which step produces it, and where does it get the count of requests in flight?  
_why:_ Without a step that makes the cap and warning, e3 can't pass, and the cap is half of what Halyard needs.

**Q2** ({'type': 'example', 'id': 'e1'}): Example e1 runs at rate 40 against fake_server. Which part of that run makes sends go late today, so it fails now and passes after? Without a pause, I'd expect late sends of 0.  
_why:_ Your done-state is a run through a 1 s pause, so the example needs to cause one or it can't tell us the count works.

Automatic: intent first OK, <= 2 questions OK, no code (guard) OK, no fallback OK, no leak words OK

## Replies to S1's first question

> Step 1 prints late sends, but step 3 is what counts them, and it takes and gives nothing. What does step 3 look at, and does it run before the report is printed?

**R1 disagree with evidence** — he says (disagree): "I checked: on Theo's branch `kiln-bench run --rate 40 --format json` has no late field at all, and render_text only formats what summarize gives it. So I'm moving 'count late sends' first and making it give 'late sends' to the report step. That's the change, the order was the problem."  
Kenji: Good catch, Luigi. If nothing computes the late count before the report runs, the report has nothing to print, so moving the count first and handing it to the report step fixes the order. Count it where the send happens, against the scheduled time, not from the JSON after the fact. When it's in, show me the late count from a `--rate 40` run.  
Automatic: no code (guard) OK, no leak words OK, conceded OK

**R2 disagree by insisting** — he says (disagree): "No, I think it's fine the way it is. I'm pretty sure it works."  
Kenji: not moving on "pretty sure." the evidence on the table is that the json has no late field and render_text only prints what summarize hands it, so the report has nothing to show until something counts late sends. show me one run with --rate 40 where a late count appears in the report text, or tell me what summarize returns today. what did you run?  
Automatic: no code (guard) OK, no leak words OK, held (not conceded) OK

**R3 lost (rung 2)** — he says (lost): "I don't get what's wrong with it."  
Kenji: Look at your step card for "count late sends": it takes nothing and gives nothing. Your print step takes "late sends" from the data card, but that card has no options listed, so no step fills it before render_text runs.  
Automatic: no code (guard) OK, no leak words OK

**R4 lost again (rung 3)** — he says (lost): "Still lost, sorry."  
Kenji: Luigi, picture a library book return desk where a clerk stamps each book with its due date, then sorts the stack into overdue and on-time, and the overdue count gets printed on the slip. If the clerk prints the slip before anyone has counted the overdue books, the slip says nothing useful, even though every individual step looks fine on its own. Someone checking that desk would ask "where does the overdue count come from, and is it ready before the slip prints?" and find the count is never made. Look at your own plan the same way: for the "late sends" line in the report, which step produces that number, and is it finished before the print step reads it?  
Automatic: no code (guard) OK, no leak words OK, toy, not kiln-bench FAIL

**R5 show me the fix (rung 4)** — he says (show_fix): "Just show me what to change."  
Kenji: Change s3 so it takes the scheduled send time and the actual send time for each request, and gives a late-sends count: the number of sends more than 10 ms after schedule. Make d1 a plain value instead of a one_of, since the recent edits flip-flopped between the two. Then move s3 ahead of s1, so the count exists before render_text reads it.  
Automatic: no code (guard) OK, no leak words OK

