"""Where did the missing requests in Theo's 'after' run go? Decide from evidence."""

import random

from _common import answer, pause_repro

NEVER_SENT = "They were never sent: while the loop waited for a free slot, the schedule restarted from \"now\""
DROPPED = "They were sent but timed out, and timeouts are dropped from the results"
POISSON = "Poisson arrivals send fewer than rate × duration requests on average"
REJECTED = "The fake server answered them with HTTP 503"

run = pause_repro()
# What the schedule asked for: the same seeded Poisson process the CLI uses.
rng, t, scheduled = random.Random(0), 0.0, 0
while t < 20:
    scheduled += 1
    t += rng.expovariate(40)

if run["server_seen"] > run["records"]:
    answer(DROPPED)
if run["summary"]["errors"]:
    answer(REJECTED)
if scheduled < 0.9 * 800:
    answer(POISSON)
if run["records"] < 0.9 * scheduled:
    answer(NEVER_SENT)
answer(f"unexpected: scheduled={scheduled} records={run['records']} server_seen={run['server_seen']}")
