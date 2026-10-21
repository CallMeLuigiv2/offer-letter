# Explainer grader eval (2026-10-21)

Real runs on the Claude plan (Haiku) through `offerletter.explainer_grading`: the grader with its quote check, branch selection, then teammate lines with both guards.

**Run 1 (same day, replaced by this run)** found two things, both fixed before this run:
- G10 ("put it in the book anyway but mark it failed with timeout so it counts as an error") came back `partly`:
  w4's must idea said "(with what went wrong and when it ended)", and the grader treated that as required. That
  detail is now a nice idea of its own.
- Rung-0 lines hinted at the fix. Ines after G3: "In the scene, the order was due at nine, but the stopwatch didn't
  start until the door-person handed it over. Where should the stopwatch start…?" The teammate saw the must ideas
  and turned "what went wrong there?" into a hint. At rung 0 the teammate now sees the scene's narration instead
  of the key ideas (`explainer_grading.line_prompt`, test
  `test_right_after_a_scene_the_teammate_sees_the_scene_not_the_key_ideas`).

Reading of this run: all 18 verdicts as expected, every quote real. The lines read as teammates. G6's rung-2
observation points toward the due-time clock (w1/w8's idea) rather than w2's; rung 2 is allowed to be concrete,
and "Show me" opens after it.

| case | q | verdict | expected | branch | quote ok | auto |
|---|---|---|---|---|---|---|
| G1 good, story terms | w1 | works | works | - | yes | OK |
| G2 good, code terms | w1 | works | works | - | yes | OK |
| G3 wrong: faster handover | w1 | off_track | off_track/partly | w1-faster | yes | OK |
| G4 partly: keeps schedule only | w2 | partly | partly/works | - | yes | OK |
| G5 good | w2 | works | works | - | yes | OK |
| G6 wrong: more trays | w2 | off_track | off_track/partly | w2-more-trays | yes | OK |
| G7 wrong: skip | w2 | off_track | off_track/partly | w2-skip | yes | OK |
| G8 good | w3 | works | works | - | yes | OK |
| G9 wrong: average | w3 | off_track | off_track/partly | w3-average | yes | OK |
| G10 good | w4 | works | works | - | yes | OK |
| G11 wrong: retry | w4 | off_track | off_track/partly | w4-retry | yes | OK |
| G12 good, code word | w5 | works | works | - | yes | OK |
| G13 wrong: sync | w5 | off_track | off_track/partly | w5-sync | yes | OK |
| G14 vague | w6 | cant_tell | cant_tell/off_track | - | yes | OK |
| G15 good | w6 | works | works | - | yes | OK |
| G16 wrong: slow bakes | w7 | off_track | off_track/partly | w7-slowbake | yes | OK |
| G17 good | w8 | works | works | - | yes | OK |
| G18 too short | w3 | cant_tell | cant_tell/off_track | - | yes | OK |

Grader: 18/18 as expected.

## Grader details

**G1 good, story terms** (w1): "i would make the stop watch start when the order was suposed to go out, not when it actually got handed over"  
verdict works, matched `-`, quote "not when it actually got handed over"  
note: He starts the stopwatch at the scheduled time the order was due to go out instead of the handover time, which is the required idea, and he does not address the no-schedule fallback (which is only nice-to-have).

**G2 good, code terms** (w1): "ttft should be first_token_at minus intended_at, and if intended_at is None use sent_at"  
verdict works, matched `-`, quote "ttft should be first_token_at minus intended_at"  
note: He starts each order's clock at intended_at, the scheduled due time, rather than handover, and falls back to sent_at when there is no schedule, which covers both the must idea and the nice fallback.

**G3 wrong: faster handover** (w1): "put more people at the door so the orders get handed to the kitchen quicker"  
verdict off_track, matched `faster`, quote "put more people at the door so the orders get handed to the kitchen quicker"  
note: The answer tries to shorten the time before handover by adding door staff, but it still measures from handover and never starts the stopwatch at each order's due time, so it misses the must idea.

**G4 partly: keeps schedule only** (w2): "the dispatcher keeps taking orders on time even when the trays are all out"  
verdict partly, matched `-`, quote "the dispatcher keeps taking orders on time even when the trays are all out"  
note: He captures the first must idea (the dispatcher never stops taking orders at due time), but never says that an order with no free tray waits in line for one itself, so the second must idea is missing.

**G5 good** (w2): "keep taking every order at its time. if theres no free tray that order waits in line for one by itself, the dispatcher doesnt stand at the door"  
verdict works, matched `-`, quote "if theres no free tray that order waits in line for one by itself"  
note: He keeps taking every order at its due time and has each order wait for a free tray itself rather than the dispatcher waiting at the door, covering both must ideas; he omits the nice-to-have ideas, which is fine.

**G6 wrong: more trays** (w2): "just get more trays so they never run out"  
verdict off_track, matched `more-trays`, quote "just get more trays so they never run out"  
note: The learner proposes adding trays so they never run out, which is the more-trays wrong idea, since a long enough stall still exhausts any cap, and it omits the must ideas of the dispatcher never stopping at due time and orders waiting for a free tray.

**G7 wrong: skip** (w2): "skip the customers that show up while the oven is stalled"  
verdict off_track, matched `skip`, quote "skip the customers that show up while the oven is stalled"  
note: The learner's answer turns away customers who arrive during the stall, which is the wrong idea of skipping orders, and it never keeps the dispatcher taking orders on schedule or has orders wait for a free tray.

**G8 good** (w3): "round up instead of down so he grabs the 10th slip"  
verdict works, matched `-`, quote "round up instead of down so he grabs the 10th slip"  
note: The learner gives the must idea: round the position up instead of down so the clerk takes the tenth, slowest slip; the optional point about floating-point noise is not mentioned, but it is not required.

**G9 wrong: average** (w3): "average the last few slips together"  
verdict off_track, matched `average`, quote "average the last few slips together"  
note: The learner proposes averaging the slowest slips, which is the averaging wrong idea, and never says to round the position up to the tenth slip.

**G10 good** (w4): "put it in the book anyway but mark it failed with timeout so it counts as an error"  
verdict works, matched `-`, quote "put it in the book anyway but mark it failed with timeout"  
note: He keeps the failed or timed-out order in the book, marked as failed, and says it counts as an error, which covers the must idea and the error-counting nice idea, though he does not explicitly say when it ended.

**G11 wrong: retry** (w4): "retry it until it comes out right"  
verdict off_track, matched `retry`, quote "retry it until it comes out right"  
note: He proposes retrying the burned or timed-out order until it succeeds, which is the wrong idea, and never says the failed order should be recorded in the book as failed.

**G12 good, code word** (w5): "use perf_counter for the waits and write down time.time once at the start for the logs"  
verdict works, matched `-`, quote "use perf_counter for the waits and write down time.time once at the start for the logs"  
note: He times the waits with perf_counter, a monotonic clock that only moves forward, and records time.time once at the start so the run can be matched to the gateway logs, covering both must and nice ideas.

**G13 wrong: sync** (w5): "sync the wall clock more often so it doesnt drift"  
verdict off_track, matched `sync`, quote "sync the wall clock more often so it doesnt drift"  
note: The learner proposes syncing the wall clock more often, which is still a wall clock that can be stepped backward, so it misses the must idea of timing waits with a monotonic clock and never mentions noting the wall-clock time once for log alignment.

**G14 vague** (w6): "test it more"  
verdict cant_tell, matched `-`, quote ""  
note: The answer "test it more" is too vague to judge: it does not say what trial to run, whether the oven stalls, or what would be checked.

**G15 good** (w6): "a trial day where the oven stalls on purpose at a steady rate, then check every order that was due is in the book and the stall shows in p99"  
verdict works, matched `-`, quote "a trial day where the oven stalls on purpose at a steady rate"  
note: He names the must idea of a trial day with a deliberate oven stall, and adds the steady rate, the every-due-order check against the book, and the p99 check, which covers the nice-to-have ideas.

**G16 wrong: slow bakes** (w7): "count the orders that took more than 10 ms to bake"  
verdict off_track, matched `slowbake`, quote "count the orders that took more than 10 ms to bake"  
note: He counts orders by how long they took to bake rather than comparing when each order left the dispatcher with its due time, so none of the must ideas are present.

**G17 good** (w8): "keep taking orders, the one with no tray waits for one but its time already started when it was due, and put up one note the first time it happens"  
verdict works, matched `-`, quote "the one with no tray waits for one"  
note: He covers both must ideas: the order with no free tray waits for one, and one note is posted the first time trays run out, and he also includes the nice idea that the wait counts from the due time, though he does not mention a separate tray-limit setting.

**G18 too short** (w3): "idk"  
verdict cant_tell, matched `-`, quote ""  
note: The learner answered only "idk", which gives no idea about rounding the position or picking the tenth slip, so it cannot be judged.

## Teammate lines

**G3 wrong: faster handover**, rung 0  
Ines: In that scene, what went wrong, and how would you change your idea so the book still holds up?  
Automatic: no code OK, no 6-word leak OK, no giveaway words OK, not the fallback OK

**G4 partly: keeps schedule only**, rung 1  
Ines: Picture the oven full and a customer walking in at 9:00 sharp. Where are they standing until a tray frees up, and what time does the inspector's stopwatch show when they finally get one?  
Automatic: no code OK, no 6-word leak OK, no giveaway words OK, not the fallback OK

**G6 wrong: more trays**, rung 2, after "ok so more trays and also a bigger oven" (off_track)  
Ines: Say the oven stalls for two seconds while orders keep arriving on schedule. With the bigger oven, the trays still fill up, so what happens to the customer due at 9:00:02, and when does the inspector start the stopwatch for them? What would you change so that customer is on the clock from the moment they were due?  
Automatic: no code OK, no 6-word leak OK, no giveaway words OK, not the fallback OK

**G16 wrong: slow bakes**, rung 0  
Amara: Luigi, in the bakery scene, what happened to the orders that left on time but sat in the oven during a stall? Where would they have shown up in your count?  
Automatic: no code OK, no 6-word leak OK, no giveaway words OK, not the fallback OK

