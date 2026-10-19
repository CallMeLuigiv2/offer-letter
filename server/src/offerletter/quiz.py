"""Quiz: strip answers for the client, grade answers by question kind, pass at 80%."""

from __future__ import annotations

from typing import Any

PASS_BAR = 0.8
PUBLIC_KEYS = ("id", "kind", "prompt_md", "code", "options")


def public_questions(quiz: dict[str, Any]) -> list[dict[str, Any]]:
    """The questions without answer, explanation or verify command."""
    out = []
    for q in quiz.get("questions", []):
        item = {k: q[k] for k in PUBLIC_KEYS if k in q}
        if "options" in item:
            item["options"] = [option_text(o) for o in item["options"]]  # the web sends the option string back
        out.append(item)
    return out


def option_text(option: Any) -> str:
    return str(option.get("text", option.get("id", ""))) if isinstance(option, dict) else str(option)


def accepted_answers(question: dict[str, Any]) -> list[Any]:
    """The kit's answer plus, for choice questions, the text of the option it points at (by id or letter)."""
    answer = question["answer"]
    options = question.get("options") or []
    if not options or isinstance(answer, list):
        return [answer]
    accepted = [answer]
    for index, option in enumerate(options):
        ident = option.get("id") if isinstance(option, dict) else None
        letter = chr(ord("a") + index)
        if _norm(answer) in (_norm(ident) if ident is not None else None, letter):
            accepted.append(option_text(option))
    return accepted


def _norm(value: Any) -> Any:
    """Case/space-insensitive form. Lists compare as sets (which_test can take several names)."""
    if isinstance(value, list | tuple | set):
        return sorted(_norm(v) for v in value)
    if isinstance(value, bool):
        return str(value).lower()
    return " ".join(str(value).split()).casefold().strip("`'\"")


def is_correct(question: dict[str, Any], given: Any) -> bool:
    if given is None or given == "" or given == []:
        return False
    for answer in accepted_answers(question):
        if _norm(given) == _norm(answer):
            return True
        # a single answer may be written as a list of one, or a list answer sent as one string
        if _norm(given if isinstance(given, list) else [given]) == _norm(answer if isinstance(answer, list) else [answer]):
            return True
    return False


def grade(quiz: dict[str, Any], answers: dict[str, Any], bar: float = PASS_BAR) -> dict[str, Any]:
    """{score, results: [{id, correct, explanation_md}], passed}; unanswered questions count as wrong."""
    questions = quiz.get("questions", [])
    results = [
        {"id": q["id"], "correct": is_correct(q, answers.get(q["id"])), "explanation_md": q.get("explanation_md", "")}
        for q in questions
    ]
    score = sum(r["correct"] for r in results) / len(results) if results else 0.0
    return {"score": score, "results": results, "passed": bool(results) and score >= bar}
