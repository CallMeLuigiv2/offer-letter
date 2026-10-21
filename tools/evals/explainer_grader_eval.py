"""Explainer grader eval: KLN-01's open pauses graded on the REAL runner (Claude plan, Haiku), then teammate lines.

Everything goes through the server's own code (`explainer_grading.grade`, `matched_branch`, `line_prompt`,
`teammate_line`, the quote check and both guards), as the app does. About 25 Haiku calls. The automatic checks
compare against the expected verdict and branch; the lead reads every transcript.

Run from server/ (Git Bash or PowerShell):
    uv run python ../tools/evals/explainer_grader_eval.py [G3 G10 ...]
Writes docs/evals/explainer-grader-<date>.md (with case names given, only those cases and their lines, to
explainer-grader-<date>-<names>.md).
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from offerletter import explainer_grading as g
from offerletter.plan_review import guard_violation
from offerletter.teammates.personas import load_persona
from offerletter.teammates.runner import ClaudeRunner, check_auth

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "content" / "companies" / "kilnworks"
EXPL = KIT / "tickets" / "KLN-01" / "explainers"
HOME = Path(r"C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner\d2b539f4-2c43-48b6-b22d-31a68fb8a936"
            r"\scratchpad\explainer-eval-home")
OUT = REPO / "docs" / "evals" / f"explainer-grader-{date.today().isoformat()}.md"
TICKET = {"id": "KLN-01", "title": "Fix the load generator before we trust its p99"}

# (name, question, his words, expected verdicts, expected branch or None). Typed the way he types.
CASES: list[tuple[str, str, str, set[str], str | None]] = [
    ("G1 good, story terms", "w1",
     "i would make the stop watch start when the order was suposed to go out, not when it actually got handed over",
     {"works"}, None),
    ("G2 good, code terms", "w1",
     "ttft should be first_token_at minus intended_at, and if intended_at is None use sent_at", {"works"}, None),
    ("G3 wrong: faster handover", "w1",
     "put more people at the door so the orders get handed to the kitchen quicker", {"off_track", "partly"}, "w1-faster"),
    ("G4 partly: keeps schedule only", "w2",
     "the dispatcher keeps taking orders on time even when the trays are all out", {"partly", "works"}, None),
    ("G5 good", "w2",
     "keep taking every order at its time. if theres no free tray that order waits in line for one by itself, the "
     "dispatcher doesnt stand at the door", {"works"}, None),
    ("G6 wrong: more trays", "w2", "just get more trays so they never run out", {"off_track", "partly"}, "w2-more-trays"),
    ("G7 wrong: skip", "w2", "skip the customers that show up while the oven is stalled", {"off_track", "partly"},
     "w2-skip"),
    ("G8 good", "w3", "round up instead of down so he grabs the 10th slip", {"works"}, None),
    ("G9 wrong: average", "w3", "average the last few slips together", {"off_track", "partly"}, "w3-average"),
    ("G10 good", "w4", "put it in the book anyway but mark it failed with timeout so it counts as an error",
     {"works"}, None),
    ("G11 wrong: retry", "w4", "retry it until it comes out right", {"off_track", "partly"}, "w4-retry"),
    ("G12 good, code word", "w5", "use perf_counter for the waits and write down time.time once at the start for the logs",
     {"works"}, None),
    ("G13 wrong: sync", "w5", "sync the wall clock more often so it doesnt drift", {"off_track", "partly"}, "w5-sync"),
    ("G14 vague", "w6", "test it more", {"cant_tell", "off_track"}, None),
    ("G15 good", "w6", "a trial day where the oven stalls on purpose at a steady rate, then check every order that was "
     "due is in the book and the stall shows in p99", {"works"}, None),
    ("G16 wrong: slow bakes", "w7", "count the orders that took more than 10 ms to bake", {"off_track", "partly"},
     "w7-slowbake"),
    ("G17 good", "w8", "keep taking orders, the one with no tray waits for one but its time already started when it "
     "was due, and put up one note the first time it happens", {"works"}, None),
    ("G18 too short", "w3", "idk", {"cant_tell", "off_track"}, None),
]

# Teammate lines after a miss: (case name, rung, a follow-up he sends before the line or None).
LINES: list[tuple[str, int, str | None]] = [
    ("G3 wrong: faster handover", 0, None),
    ("G4 partly: keeps schedule only", 1, None),
    ("G6 wrong: more trays", 2, "ok so more trays and also a bigger oven"),
    ("G16 wrong: slow bakes", 0, None),
]

# Story words that would hand him the fix (the model answers' key phrases).
GIVEAWAY = re.compile(r"\bwas due\b|\bdue time\b|\bround(?:s|ing)? (?:it )?up\b|\bwaits? in line\b|"
                      r"\bonly (?:moves|goes) forward\b|\bmark(?:ed)? (?:it )?(?:as )?failed\b|"
                      r"\bstall(?:s)? on purpose\b|\bmore than 10 ?ms after\b", re.I)


def load(name: str) -> Any:
    return json.loads(name.read_text(encoding="utf-8"))


async def main() -> None:
    auth = check_auth()
    if not auth.ok:
        raise SystemExit(auth.message)
    runner = ClaudeRunner(HOME / "teammates")
    only = sys.argv[1:]
    cases = [c for c in CASES if not only or c[0].split()[0] in only]
    out_path = OUT if not only else OUT.with_name(f"{OUT.stem}-{'-'.join(only)}.md")
    rubric = load(EXPL / "rubric.json")["questions"]
    wwr = load(EXPL / "what-went-wrong" / "script.json")
    story = load(EXPL / "how-it-works" / "script.json")["story"]
    chapters = {c["question"]["id"]: c for c in wwr["chapters"] if isinstance(c.get("question"), dict)}
    personas = {slug: load_persona("kilnworks", KIT / "personas" / f"{slug}.json") for slug in ("ines", "amara")}
    out = [f"# Explainer grader eval ({date.today().isoformat()})", "",
           "Real runs on the Claude plan (Haiku) through `offerletter.explainer_grading`: the grader with its quote "
           "check, branch selection, then teammate lines with both guards.", "",
           "| case | q | verdict | expected | branch | quote ok | auto |", "|---|---|---|---|---|---|---|"]
    detail: list[str] = []
    results: dict[str, dict[str, Any]] = {}
    passed = 0
    for name, qid, text, want, want_branch in cases:
        q, rq = chapters[qid]["question"], rubric[qid]
        res = await g.grade(runner, "kilnworks", q["prompt"], rq, [text])
        branch = g.matched_branch(rq, res)
        ok_verdict = res["verdict"] in want
        ok_branch = branch == want_branch if want_branch else branch is None or res["verdict"] in ("partly", "off_track")
        quote_ok = res["verdict"] == "cant_tell" and not res["quote"] or g.quote_ok(res["quote"], [text])
        ok = ok_verdict and ok_branch and quote_ok
        passed += ok
        results[name] = {"q": q, "rq": rq, "text": text, "res": res, "chapter": chapters[qid], "branch": branch}
        out.append(f"| {name} | {qid} | {res['verdict']} | {'/'.join(sorted(want))} | {branch or '-'}"
                   f"{'' if ok_branch else ' (want ' + str(want_branch) + ')'} | {'yes' if quote_ok else 'NO'} | "
                   f"{'OK' if ok else 'CHECK'} |")
        detail += [f"**{name}** ({qid}): \"{text}\"  ", f"verdict {res['verdict']}, matched "
                   f"`{res['matched_wrong_idea'] or '-'}`, quote \"{res['quote']}\"  ", f"note: {res['note']}", ""]
    out += ["", f"Grader: {passed}/{len(cases)} as expected.", "", "## Grader details", "", *detail,
            "## Teammate lines", ""]
    for name, rung, follow in LINES:
        if name not in results:
            continue
        r = results[name]
        q, rq, ch = r["q"], r["rq"], r["chapter"]
        persona = personas[q.get("who") or "ines"]
        history = [("player", r["text"])]
        verdict = r["res"]["verdict"]
        if follow:
            history += [("persona", "What happens in the story with that?"), ("player", follow)]
            verdict = (await g.grade(runner, "kilnworks", q["prompt"], rq, [r["text"], follow]))["verdict"]
        scene = g.scene_text(q, r["branch"]) if r["branch"] else ""
        make = lambda reminder, p=persona, h=history, rr=rung, v=verdict, c=ch, qq=q, rqq=rq, sc=scene: g.line_prompt(
            p, "Luigi", TICKET, story, c.get("title", ""), qq["prompt"], rqq, h, rr, v, reminder, sc)
        fallback = g.FALLBACK["cant_tell" if verdict == "cant_tell" else rung]
        line = await g.teammate_line(runner, persona, make, rq, q["prompt"], fallback)
        auto = {"no code": guard_violation(line) is None, "no 6-word leak": not g.leaks(line, rq, q["prompt"]),
                "no giveaway words": GIVEAWAY.search(line) is None, "not the fallback": line != fallback}
        out += [f"**{name}**, rung {rung}" + (f", after \"{follow}\" ({verdict})" if follow else "") + "  ",
                f"{persona.first_name}: {line}  ",
                "Automatic: " + ", ".join(f"{k} {'OK' if v else 'FAIL'}" for k, v in auto.items()), ""]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    asyncio.run(main())
