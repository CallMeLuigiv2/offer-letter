"""Scoring a PR review against the kit's planted issues.

A comment matches an issue when the path is the same and the line is within
[line_start - 2, line_end + 2]. Each issue counts at most once toward recall. Comments on decoys
(code that looks wrong but is fine) are false flags. precision = matching / all comments, leaving out praise and nit ones (never false flags).
"""

from __future__ import annotations

from typing import Any

SLACK = 2
RECALL_BAR = 0.6
PRECISION_BAR = 0.5
UNJUDGED = ("praise", "nit")


def _near(comment: dict[str, Any], path: str, low: int, high: int) -> bool:
    return comment["path"] == path and low - SLACK <= comment["line"] <= high + SLACK


def score_review(issues: list[dict], decoys: list[dict], comments: list[dict],
                 also_valid: list[dict] | None = None) -> dict[str, Any]:
    """`comments` are the learner's new-side comments (id, path, line). Returns the section 4 score object."""
    found, matching_ids = [], set()
    # praise and nit comments may match an issue but never cost precision or count as false flags
    # also_valid: fair findings outside the key; they are left out of precision too (never a false flag)
    fair = also_valid or []
    judged = [c for c in comments if c.get("severity") not in UNJUDGED
              and not any(_near(c, a["path"], a["line_start"], a.get("line_end", a["line_start"])) for a in fair)]
    for issue in issues:
        hits = [c for c in comments if _near(c, issue["path"], issue["line_start"], issue["line_end"])]
        matching_ids.update(c["id"] for c in hits)
        if hits:
            # after submission he sees what each catch was and why it mattered, not just an id
            found.append({"issue_id": issue["id"], "comment_id": hits[0]["id"], "title": issue["title"],
                          "explanation": issue.get("explanation_md", "")})
    found_ids = {f["issue_id"] for f in found}
    missed = [
        {"issue_id": i["id"], "title": i["title"], "path": i["path"], "line": i["line_start"],
         "explanation": i.get("explanation_md", "")}
        for i in issues if i["id"] not in found_ids
    ]
    false_flags = [
        c["id"] for c in judged
        if c["id"] not in matching_ids and any(_near(c, d["path"], d["line"], d["line"]) for d in decoys)
    ]
    return {
        "found": found,
        "missed": missed,
        "false_flags": false_flags,
        "recall": len(found) / len(issues) if issues else 1.0,
        "precision": sum(c["id"] in matching_ids for c in judged) / len(judged) if judged else 0.0,
    }


def review_passed(score: dict[str, Any], recall_bar: float = RECALL_BAR, precision_bar: float = PRECISION_BAR) -> bool:
    return score["recall"] >= recall_bar and score["precision"] >= precision_bar


def build_debrief(score: dict[str, Any], issues: list[dict], decoys: list[dict], comments: list[dict],
                  verdict: str, passed: bool) -> str:
    """Markdown debrief: what he caught, what he missed (with the explanation), and his false flags."""
    by_issue = {i["id"]: i for i in issues}
    lines = ["# Review debrief", "",
             f"You found **{len(score['found'])} of {len(issues)}** planted issues "
             f"(recall {score['recall']:.0%}, precision {score['precision']:.0%}). "
             + ("That clears the bar." if passed else "That's below the bar, so the quiz stays locked. "
                "Read the misses below, then re-review the PR and submit again.")]
    if score["missed"] and verdict == "approve":
        lines += ["", "You approved this PR with real bugs in it. In a real team that is how they reach production."]
    lines += ["", "## What you caught"]
    lines += [f"- **{by_issue[f['issue_id']]['title']}** (`{by_issue[f['issue_id']]['path']}`)"
              for f in score["found"]] or ["- Nothing yet."]
    lines += ["", "## What you missed"]
    for m in score["missed"]:
        lines += [f"- **{m['title']}** (`{m['path']}` near line {m['line']})", f"  {m['explanation']}".rstrip()]
    if not score["missed"]:
        lines.append("- Nothing. Clean sweep.")
    by_comment = {c["id"]: c for c in comments}
    if score["false_flags"]:
        lines += ["", "## Flags that weren't bugs"]
        for cid in score["false_flags"]:
            c = by_comment[cid]
            decoy = next(d for d in decoys if _near(c, d["path"], d["line"], d["line"]))
            lines.append(f"- `{c['path']}:{c['line']}`: {decoy.get('why_not_a_bug', 'This code is fine.')}")
    return "\n".join(lines) + "\n"
