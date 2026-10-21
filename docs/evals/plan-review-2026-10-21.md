# Plan review eval (2026-10-21)

Real runs: Sonnet for each review, Haiku for replies, through `offerletter.plan_review`.

## S1 gappy plan

**Intent:** I read your plan as: start from Theo's branch, apply the fixes from your review, then add Amara's three asks (p99.9, a late-sends line in the report, and a max-in-flight flag with a warning). The report step is the one you've detailed. Is that right?

**Q1** ({'type': 'step', 'id': 's1'}): Step 1 prints late sends in the report, but no earlier step produces that number. Step 3 takes nothing and gives nothing. Where does the count get made, and what does it hand to the report?  
_why:_ If nothing produces the count before the report prints, the late sends line can't show a real number.

**Q2** ({'type': 'example', 'id': 'e1'}): Example e1 expects 'late sends: 3' on a --rate 40 run. What would make a run produce exactly 3, and what should the line say when nothing is late?  
_why:_ Without a known cause for the 3, or a zero case, nobody else can tell whether the count is right.

Automatic: intent first OK, <= 2 questions OK, no code (guard) OK, no fallback OK, no leak words OK

## S2 solid plan

**Intent:** I read your plan as: each request record keeps its scheduled and sent time, summarize counts the sends that left more than 10 ms late, and the text and JSON reports show that count. The cap warning should print once. Is that right?

**Q1** ({'type': 'example', 'id': 'e3'}): Example e3 needs a `--max-in-flight` option and a warning, but s1 to s3 only record, count and render. Which step adds the cap and the warning? Same question for p99.9, which no step mentions.  
_why:_ e3 can't pass if no step produces the flag and the warning, so the steps don't yet connect to the acceptance list.

**Q2** ({'type': 'example', 'id': 'e1'}): Your pre-mortem p3 says your tests might also pass on Theo's branch. Which example fails today, and which of them would still fail on his branch if the closed-loop or timing bugs from your review are still there?  
_why:_ Without an example that fails before the fix and passes after, nobody can tell the review fixes landed.

Automatic: intent first OK, <= 2 questions OK, no code (guard) OK, no fallback OK, no leak words OK

## Replies to S1's first question

> Step 1 prints late sends in the report, but no earlier step produces that number. Step 3 takes nothing and gives nothing. Where does the count get made, and what does it hand to the report?

**R1 disagree with evidence** — he says (disagree): "I checked: on Theo's branch `kiln-bench run --rate 40 --format json` has no late field at all, and render_text only formats what summarize gives it. So I'm moving 'count late sends' first and making it give 'late sends' to the report step. That's the change, the order was the problem."  
Kenji: Yes, that's the gap I was pointing at: nothing makes the count today, so the report has nothing real to print. Counting late sends first, and handing it to the report, fixes that order. Good catch, Luigi.  
Automatic: no code (guard) OK, no leak words OK, conceded OK

**R2 disagree by insisting** — he says (disagree): "No, I think it's fine the way it is. I'm pretty sure it works."  
Kenji: not convinced yet. "pretty sure" isn't something I can take to Halyard. a run where a send goes late and the report prints the count would convince me. which flags did you use, and what did it print?  
Automatic: no code (guard) OK, no leak words OK, held (not conceded) OK

**R3 lost (rung 2)** — he says (lost): "I don't get what's wrong with it."  
Kenji: Luigi, you're sending late sends to the report, but the card that makes the count is "s3: count late sends", and it takes nothing and gives nothing. So "gives 'late sends' to the report step" has no producer behind it yet.  
Automatic: no code (guard) OK, no leak words OK

**R4 lost again (rung 3)** — he says (lost): "Still lost, sorry."  
Kenji: no worries, try it on a library returns desk. the sign says "overdue fines," but nobody has a step that counts which books came back late, so the sign can only ever show zero or a made-up number. someone checking the desk notices by tracing the sign back to whoever is supposed to do the counting, and finds no one. in your plan, look for the step that makes the late count and check whether anything hands that count to the report.  
Automatic: no code (guard) OK, no leak words OK, toy, not kiln-bench OK

**R5 show me the fix (rung 4)** — he says (show_fix): "Just show me what to change."  
Kenji: In the plan, s3 is the card that makes the count, so it has to take something and give something. Change it to take each request's scheduled send time and actual send time, and give one late count to d1. Make d1 a value rather than one_of, since it's a number, and move s3 above s1 so the count exists before the report reads it.  
Automatic: no code (guard) OK, no leak words OK

