"""Theo's 'after' run: what p99 TTFT is reported, and what should it be?"""

from _common import answer, pause_repro

run = pause_repro()
reported = run["summary"]["ttft_ms"]["p99"]

# Truth: a 1 s pause every 20 s means 5% of arrivals land in a pause and wait for it to end,
# uniformly between 0 and 1 s. p99 sits 80% of the way up that band, plus the 20 ms prefill.
paused_share = 1 / 20
truth = 20 + (1 - (1 - 0.99) / paused_share) * 1000

if reported < 100 and 700 <= truth <= 900:
    answer("About 30 ms reported; it should be about 800 ms")
if reported > 600:
    answer("About 1,000 ms reported, which is right")
answer(f"unexpected: reported p99 {reported:.0f} ms, truth {truth:.0f} ms")
