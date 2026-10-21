"""Plan review eval: Kenji reads two KLN-01 plans on the REAL runner (Claude plan), then answers replies.

Everything goes through the server's own prompt code (`plan_review.review_prompt` / `reply_prompt`,
`run_review` / `run_reply`, the code guard), with Sonnet for the review and Haiku for replies, as the app
does. Seven calls in all. Automatic checks are a first pass; the lead reads every transcript.

Run from server/ (Git Bash or PowerShell):
    uv run python ../tools/evals/plan_review_eval.py
Writes docs/evals/plan-review-<date>.md.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from offerletter import plan_review as pr
from offerletter.teammates.personas import load_persona
from offerletter.teammates.runner import ClaudeRunner, check_auth

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "content" / "companies" / "kilnworks"
HOME = Path(r"C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner\d2b539f4-2c43-48b6-b22d-31a68fb8a936"
            r"\scratchpad\plan-eval-home")
OUT = REPO / "docs" / "evals" / f"plan-review-{date.today().isoformat()}.md"
TICKET = {"id": "KLN-01", "title": "Fix the load generator before we trust its p99"}

# Words that would point at a fix nobody in his plan or the request mentioned (the planted issues' fixes).
LEAK = re.compile(r"intended_at|re-?anchor|monotonic|time\.time|perf_counter|\bceil|\bfloor\b|next_at|"
                  r"wall.?clock|drop(?:s|ped|ping)? (?:the )?fail", re.I)


def _req() -> str:
    change = json.loads((KIT / "tickets" / "KLN-01" / "change.json").read_text(encoding="utf-8"))
    return ("This plan also covers the fixes from your review of Theo's PR.\n\n" + change["request_md"])


def _check(key: str, sev: str, msg: str, ask: str, ref: dict | None = None) -> dict:
    return {"key": key, "id": key.split(":")[0], "severity": sev, "msg": msg, "ask": ask, "observe": "", "ref": ref}


# A plan with the same kinds of gaps he made in the prototype, in KLN-01 terms.
GAPPY: dict[str, Any] = {
    "v": 1, "ticket_id": "KLN-01", "lang": "python", "weight": "standard",
    "read": {"seam": [{"path": "src/kiln_bench/report.py", "symbol": "render_text"}], "callers": [], "note": ""},
    "restate": {"given": "theo's branch", "produce": "the fixes and amara's stuff", "done_when": ""},
    "bridge": {"source": None, "story_md": "A bakery that sends batches on a schedule.",
               "solution_md": "count the late ones and stop sending when there are too many",
               "mapping": [{"id": "m1", "real": "late batches", "kind": "thing", "to": None}]},
    "examples": [
        {"id": "e1", "label": "happy", "rule": "late sends show up", "form": "text",
         "text": {"given": "a run with --rate 40", "expect": "late sends: 3"}, "predict": "fail"},
        {"id": "e2", "label": "happy", "rule": "p99.9 is there", "form": "text",
         "text": {"given": "a run with --format json", "expect": "p99.9 in the json"}, "predict": "pass"},
    ],
    "data": [
        {"id": "d1", "name": "late sends", "kind": "one_of", "options": [], "fields": [], "vtype": "text"},
        {"id": "d2", "name": "max in flight", "kind": "one_of", "options": [], "fields": [], "vtype": "text"},
        {"id": "d3", "name": "report", "kind": "value", "options": [], "fields": [], "vtype": "text"},
    ],
    "steps": [
        {"id": "s1", "label": "print the report", "subgoal": "report",
         "existing": {"path": "src/kiln_bench/report.py", "symbol": "render_text"},
         "takes": [{"data_id": "d1", "mode": "read"}], "gives": "d3", "fails": "no", "awaits": False, "risky": False},
        {"id": "s2", "label": "add max in flight flag and warning", "subgoal": "wire-up",
         "existing": {"path": "src/kiln_bench/cli.py", "symbol": "build_parser"},
         "takes": [], "gives": "d2", "fails": "no", "awaits": False, "risky": False},
        {"id": "s3", "label": "count late sends", "subgoal": "count", "existing": None, "new_fn": None, "where": None,
         "takes": [], "gives": None, "fails": "no", "awaits": False, "risky": False},
    ],
    "decisions": [{"id": "k1", "choice": "put everything in render_text", "because": "it's simpler",
                   "instead_of": "", "would_change_if": ""}],
    "premortem": [{"id": "p1", "text": "tests fail"}], "scope": {"appetite_blocks": 2, "no_gos": [], "first_slice": None},
    "thinking": [{"id": "t1", "at": "", "move": "contracts", "kind": "unsure", "text": "not sure where late sends get counted", "via": "text"}],
    "history": [{"at": "", "move": "pieces", "action": "kind: late sends value -> one_of"},
                {"at": "", "move": "pieces", "action": "kind: late sends one_of -> value"},
                {"at": "", "move": "pieces", "action": "kind: late sends value -> one_of"}],
    "kept": {},
    "derived": {"checks": [
        _check("flow.later_source:s1:d1", "wont_work", "Step 1 'print the report' takes 'late sends', but nothing gives it before step 1",
               "Which step gives 'late sends', and does it run before the report is printed?", {"type": "step", "id": "s1"}),
        _check("flow.no_contract:s3", "costly", "Step 3 'count late sends' takes nothing and gives nothing",
               "What does counting late sends need to look at, and what does it hand on?", {"type": "step", "id": "s3"}),
        _check("data.one_of_no_options:d1", "note", "'late sends' is 'one of' but has no options", "What are the options?", {"type": "data", "id": "d1"}),
        _check("examples.no_boundary", "costly", "No boundary example", "What happens when nothing is late?"),
        _check("steps.two_jobs:s2", "costly", "Step 2 does two jobs", "Which half could stand on its own?", {"type": "step", "id": "s2"}),
        _check("reasons.tautology:k1", "note", "'it's simpler' doesn't say simpler how", "Simpler for whom?", {"type": "decision", "id": "k1"}),
    ], "moves": {}, "computed_at": ""},
}

# A plan a reviewer should have little to ask about (plan-level only, no code).
SOLID: dict[str, Any] = {
    **{k: v for k, v in GAPPY.items() if k in ("v", "ticket_id", "lang", "weight", "kept")},
    "read": {"seam": [{"path": "src/kiln_bench/openloop.py", "symbol": "OpenLoopRunner._fire"},
                      {"path": "src/kiln_bench/metrics.py", "symbol": "summarize"},
                      {"path": "src/kiln_bench/report.py", "symbol": "render_text"},
                      {"path": "src/kiln_bench/cli.py", "symbol": "build_parser"}],
             "callers": [{"path": "src/kiln_bench/cli.py", "symbol": "_print_summary"},
                         {"path": "src/kiln_bench/cli.py", "symbol": "_run"}],
             "note": "each record knows when it was scheduled and when it left; summarize sees all records"},
    "restate": {"given": "the records of a --rate run, each with its scheduled and actual send time",
                "produce": "a report and JSON summary with p50/p90/p99/p99.9, a late-sends count, and one warning when the in-flight cap is hit",
                "done_when": "a run through a 1 s pause shows late sends > 0 in JSON and text, and the warning prints once"},
    "bridge": {"source": None, "story_md": "A bakery promises a batch every second; the oven sometimes stalls.",
               "solution_md": "The baker keeps the order book: each batch has the time it was promised and the time it left. At closing, count the batches that left more than a moment after their promised time. If every tray is in use, the next batch waits and the baker notes it once on the board.",
               "mapping": [{"id": "m1", "real": "promised time and left time per batch", "kind": "thing", "to": {"type": "data", "id": "d1"}},
                           {"id": "m2", "real": "count batches that left late", "kind": "action", "to": {"type": "step", "id": "s2"}},
                           {"id": "m3", "real": "note it once on the board when all trays are busy", "kind": "rule", "to": {"type": "example", "id": "e3"}}],
               "breaks": None},
    "examples": [
        {"id": "e1", "label": "happy", "rule": "late sends counted", "form": "cli",
         "cli": {"args": "run --rate 40 --duration 5 --arrival constant --format json", "fixture": "fake_server",
                 "fixture_args": "--pause-every 5 --pause-for 1", "checks": [{"kind": "json_gt", "path": "late_sends", "value": "0"}]},
         "predict": "error"},
        {"id": "e2", "label": "boundary", "rule": "no pause, nothing late", "form": "cli",
         "cli": {"args": "run --rate 5 --duration 2 --arrival constant --format json", "fixture": "fake_server",
                 "fixture_args": "", "checks": [{"kind": "json_eq", "path": "late_sends", "value": "0"}]},
         "predict": "error"},
        {"id": "e3", "label": "error", "rule": "cap reached warns once", "form": "cli",
         "cli": {"args": "run --rate 40 --duration 3 --max-in-flight 2", "fixture": "fake_server",
                 "fixture_args": "--pause-every 1 --pause-for 1", "checks": [{"kind": "stderr_contains", "value": "max-in-flight"}]},
         "predict": "error"},
    ],
    "data": [
        {"id": "d1", "name": "request record", "kind": "parts", "options": [], "vtype": "text",
         "fields": [{"name": "scheduled at", "type": "float"}, {"name": "sent at", "type": "float"}]},
        {"id": "d2", "name": "summary", "kind": "parts", "options": [], "vtype": "text",
         "fields": [{"name": "late sends", "type": "int"}, {"name": "percentiles", "type": "dict"}]},
        {"id": "d3", "name": "report text", "kind": "value", "options": [], "fields": [], "vtype": "text"},
    ],
    "steps": [
        {"id": "s1", "label": "record when each request was scheduled and sent", "subgoal": "measure",
         "existing": {"path": "src/kiln_bench/openloop.py", "symbol": "OpenLoopRunner._fire"},
         "takes": [], "gives": "d1", "fails": "no", "awaits": True, "risky": True},
        {"id": "s2", "label": "count late sends in the summary", "subgoal": "count",
         "existing": {"path": "src/kiln_bench/metrics.py", "symbol": "summarize"},
         "takes": [{"data_id": "d1", "mode": "read"}], "gives": "d2", "fails": "no", "awaits": False, "risky": False},
        {"id": "s3", "label": "show late sends in the text report", "subgoal": "report",
         "existing": {"path": "src/kiln_bench/report.py", "symbol": "render_text"},
         "takes": [{"data_id": "d2", "mode": "read"}], "gives": "d3", "fails": "no", "awaits": False, "risky": False},
    ],
    "decisions": [{"id": "k1", "choice": "count late sends from the records in summarize",
                   "because": "summarize already sees every record, so the JSON and the text report get the same number",
                   "instead_of": "counting inside the runner (rejected: the report command reads saved files and would miss it)",
                   "would_change_if": "records stop carrying the scheduled time", "confirmed_by": "e1"}],
    "premortem": [{"id": "p1", "text": "late is measured against the wrong time"},
                  {"id": "p2", "text": "the warning prints on every send"},
                  {"id": "p3", "text": "my tests also pass on Theo's branch"}],
    "scope": {"appetite_blocks": 4, "no_gos": ["no new report format"], "first_slice": "e1"},
    "thinking": [], "history": [],
    "derived": {"checks": [], "moves": {}, "computed_at": ""},
}

REPLIES = [
    ("R1 disagree with evidence", "disagree",
     "I checked: on Theo's branch `kiln-bench run --rate 40 --format json` has no late field at all, and render_text "
     "only formats what summarize gives it. So I'm moving 'count late sends' first and making it give 'late sends' to "
     "the report step. That's the change, the order was the problem."),
    ("R2 disagree by insisting", "disagree", "No, I think it's fine the way it is. I'm pretty sure it works."),
    ("R3 lost (rung 2)", "lost", "I don't get what's wrong with it."),
    ("R4 lost again (rung 3)", "lost", "Still lost, sorry."),
    ("R5 show me the fix (rung 4)", "show_fix", "Just show me what to change."),
]


async def main() -> None:
    auth = check_auth()
    if not auth.ok:
        raise SystemExit(auth.message)
    runner = ClaudeRunner(HOME / "teammates")
    kenji = load_persona("kilnworks", KIT / "personas" / "kenji.json")
    request = _req()
    out = [f"# Plan review eval ({date.today().isoformat()})", "",
           "Real runs: Sonnet for each review, Haiku for replies, through `offerletter.plan_review`.", ""]
    first_q = None
    for name, doc in (("S1 gappy plan", GAPPY), ("S2 solid plan", SOLID)):
        make = lambda reminder, d=doc: pr.review_prompt(kenji, "Luigi", TICKET, request, d, [], "normal", 1, [], reminder)
        review, fallback = await pr.run_review(runner, kenji, make, "sonnet")
        text = " ".join([review["intent_md"], *(q["ask_md"] + " " + q["why_md"] for q in review["questions"])])
        auto = {
            "intent first": review["intent_md"].lower().startswith("i read your plan as"),
            "<= 2 questions": len(review["questions"]) <= 2,
            "no code (guard)": pr.guard_violation(text) is None,
            "no fallback": not fallback,
            "no leak words": LEAK.search(text) is None,
        }
        out += [f"## {name}", "", f"**Intent:** {review['intent_md']}", ""]
        for i, q in enumerate(review["questions"], 1):
            out += [f"**Q{i}** ({q.get('ref')}): {q['ask_md']}  ", f"_why:_ {q['why_md']}", ""]
        out += ["Automatic: " + ", ".join(f"{k} {'OK' if v else 'FAIL'}" for k, v in auto.items()), ""]
        if name.startswith("S1") and review["questions"]:
            first_q = review["questions"][0]
    if first_q is None:
        OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
        raise SystemExit("S1 asked no question; replies skipped")
    out += ["## Replies to S1's first question", "", f"> {first_q['ask_md']}", ""]
    history: list[dict[str, Any]] = []
    rung = 1
    for name, choice, body in REPLIES:
        if choice == "lost":
            rung = min(rung + 1, 3)
        use_rung = 4 if choice == "show_fix" else rung
        structured = choice == "disagree"
        make = lambda reminder, c=choice, b=body, r=use_rung, h=list(history): pr.reply_prompt(
            kenji, "Luigi", first_q, c, b, r, GAPPY, h, request, reminder)
        text, conceded = await pr.run_reply(runner, kenji, make, "haiku", structured)
        auto = {"no code (guard)": pr.guard_violation(text) is None, "no leak words": LEAK.search(text) is None}
        if name.startswith("R1"):
            auto["conceded"] = conceded is True
        if name.startswith("R2"):
            auto["held (not conceded)"] = conceded is False
        if name.startswith("R4"):
            auto["toy, not kiln-bench"] = re.search(r"kiln|render_text|summarize|openloop|late send", text, re.I) is None
        out += [f"**{name}** — he says ({choice}): \"{body}\"  ", f"Kenji: {text}  ",
                "Automatic: " + ", ".join(f"{k} {'OK' if v else 'FAIL'}" for k, v in auto.items()), ""]
        history.append({"choice": choice, "body_md": body, "persona_md": text})
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    asyncio.run(main())
