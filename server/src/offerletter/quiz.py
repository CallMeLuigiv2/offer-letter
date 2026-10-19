"""Quiz: strip answers for the client, grade answers by question kind, pass at 80%."""

from __future__ import annotations

from typing import Any

PASS_BAR = 0.8
PUBLIC_KEYS = ("id", "kind", "prompt_md", "code", "options")


def public_questions(quiz: dict[str, Any]) -> list[dict[str, Any]]:
    """The questions without answer, explanation or verify command."""
    return [{k: q[k] for k in PUBLIC_KEYS if k in q} for q in quiz.get("questions", [])]


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
    answer = question["answer"]
    if _norm(given) == _norm(answer):
        return True
    # a single answer may be written as a list of one, or a list answer sent as one string
    return _norm([given] if not isinstance(given, list) else given) == _norm([answer] if not isinstance(answer, list) else answer)


def grade(quiz: dict[str, Any], answers: dict[str, Any], bar: float = PASS_BAR) -> dict[str, Any]:
    """{score, results: [{id, correct, explanation_md}], passed}; unanswered questions count as wrong."""
    questions = quiz.get("questions", [])
    results = [
        {"id": q["id"], "correct": is_correct(q, answers.get(q["id"])), "explanation_md": q.get("explanation_md", "")}
        for q in questions
    ]
    score = sum(r["correct"] for r in results) / len(results) if results else 0.0
    return {"score": score, "results": results, "passed": bool(results) and score >= bar}
