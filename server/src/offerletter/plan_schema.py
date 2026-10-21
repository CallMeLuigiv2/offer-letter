"""A small Python mirror of the PlanDoc field names and enums (ARCHITECTURE 8.2).

Not the engine: the checks live in web/src/plan/engine and the server never re-implements them. This only knows
what fields exist and which values are allowed, so `verify_kit.py` can reject a broken worked plan and the server
can read a doc safely. Unknown fields are always allowed (the contract is forward compatible).
"""

from __future__ import annotations

from typing import Any

MOVES = ("watch", "read", "restate", "bridge", "examples", "pieces", "contracts", "run", "decide", "review")
WEIGHTS = ("lite", "standard", "full")
LANGS = ("python", "rust")
KINDS = ("change", "build", "perf", "incident", "design", "experiment")
EXAMPLE_LABELS = ("happy", "boundary", "error")
EXAMPLE_FORMS = ("call", "cli", "text")
COMPARES = ("eq", "approx", "raises", "truthy")
CLI_CHECKS = ("exit", "stdout_contains", "stderr_contains", "json_has", "json_eq", "json_gt", "json_lt")
PREDICTIONS = ("pass", "fail", "error")
DATA_KINDS = ("parts", "one_of", "many_of", "value", "outside")
VTYPES = ("text", "number", "bool", "path", "time", "bytes", "duration")
SUBGOALS = ("read", "parse", "validate", "decide", "transform", "count", "store", "report", "handle-failure",
            "wire-up", "measure")
STEP_MODES = ("read", "change", "consume")
FAILS = ("no", "none", "raises")
THINK_KINDS = ("think", "assume", "unsure", "because", "stuck", "next")
MAP_KINDS = ("thing", "action", "rule", "limit")
CHECK_SEVERITIES = ("wont_work", "costly", "note")

# Moves each weight must finish (moves.ts). `watch` and `read` have extra rules, see plan.required_moves.
REQUIRED_MOVES = {
    "lite": ("restate", "examples", "contracts", "decide"),
    "standard": ("watch", "read", "restate", "bridge", "examples", "pieces", "contracts", "run", "decide"),
    "full": ("watch", "read", "restate", "bridge", "examples", "pieces", "contracts", "run", "decide"),
}


def _opt_enum(errors: list[str], where: str, obj: dict[str, Any], key: str, allowed: tuple[str, ...]) -> None:
    value = obj.get(key)
    if value is not None and value not in allowed:
        errors.append(f"{where}.{key}: {value!r} is not one of {', '.join(allowed)}")


def _list(errors: list[str], where: str, obj: dict[str, Any], key: str) -> list[Any]:
    value = obj.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{where}.{key} must be a list")
        return []
    return value


def _items(errors: list[str], where: str, obj: dict[str, Any], key: str) -> list[dict[str, Any]]:
    out = []
    for i, item in enumerate(_list(errors, where, obj, key)):
        if isinstance(item, dict):
            out.append(item)
        else:
            errors.append(f"{where}.{key}[{i}] must be an object")
    return out


def validate_doc(doc: Any, partial: bool = True) -> list[str]:
    """Problems found in a PlanDoc (or, with partial=True, a PlanDoc-partial as a worked plan beat carries it)."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["the plan must be an object"]
    if not partial and doc.get("v") != 1:
        errors.append("v must be 1")
    _opt_enum(errors, "doc", doc, "lang", LANGS)
    _opt_enum(errors, "doc", doc, "weight", WEIGHTS)
    _opt_enum(errors, "doc", doc, "move", MOVES)
    for key in ("read", "restate", "bridge", "scope", "kept", "derived"):
        if doc.get(key) is not None and not isinstance(doc[key], dict):
            errors.append(f"doc.{key} must be an object")
    bridge = doc.get("bridge") if isinstance(doc.get("bridge"), dict) else {}
    for i, row in enumerate(_items(errors, "bridge", bridge, "mapping")):
        _opt_enum(errors, f"bridge.mapping[{i}]", row, "kind", MAP_KINDS)
    for i, ex in enumerate(_items(errors, "doc", doc, "examples")):
        w = f"examples[{i}]"
        _opt_enum(errors, w, ex, "label", EXAMPLE_LABELS)
        _opt_enum(errors, w, ex, "form", EXAMPLE_FORMS)
        _opt_enum(errors, w, ex, "predict", PREDICTIONS)
        if ex.get("form") == "call" and not isinstance(ex.get("call"), dict):
            errors.append(f"{w}: a call example needs a call object")
        if ex.get("form") == "cli" and not isinstance(ex.get("cli"), dict):
            errors.append(f"{w}: a cli example needs a cli object")
        if isinstance(ex.get("call"), dict):
            _opt_enum(errors, f"{w}.call", ex["call"], "compare", COMPARES)
        if isinstance(ex.get("cli"), dict):
            for j, chk in enumerate(_items(errors, f"{w}.cli", ex["cli"], "checks")):
                _opt_enum(errors, f"{w}.cli.checks[{j}]", chk, "kind", CLI_CHECKS)
    for i, card in enumerate(_items(errors, "doc", doc, "data")):
        _opt_enum(errors, f"data[{i}]", card, "kind", DATA_KINDS)
        _opt_enum(errors, f"data[{i}]", card, "vtype", VTYPES)
    for i, step in enumerate(_items(errors, "doc", doc, "steps")):
        w = f"steps[{i}]"
        _opt_enum(errors, w, step, "subgoal", SUBGOALS)
        _opt_enum(errors, w, step, "fails", FAILS)
        for j, take in enumerate(_items(errors, w, step, "takes")):
            _opt_enum(errors, f"{w}.takes[{j}]", take, "mode", STEP_MODES)
    for i, note in enumerate(_items(errors, "doc", doc, "thinking")):
        _opt_enum(errors, f"thinking[{i}]", note, "kind", THINK_KINDS)
    _items(errors, "doc", doc, "decisions")
    _items(errors, "doc", doc, "premortem")
    _items(errors, "doc", doc, "history")
    return errors


def validate_worked(plan: Any) -> list[str]:
    """Problems found in a WorkedPlan (content/plans/worked/<id>.json)."""
    if not isinstance(plan, dict):
        return ["a worked plan must be an object"]
    errors = []
    for key in ("id", "title", "lang", "kind", "narrator", "toy_request_md"):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            errors.append(f"{key} is missing")
    if plan.get("lang") not in LANGS:
        errors.append(f"lang must be one of {', '.join(LANGS)}")
    if plan.get("kind") not in KINDS:
        errors.append(f"kind must be one of {', '.join(KINDS)}")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return [*errors, "steps must be a non-empty list"]
    for i, step in enumerate(steps):
        w = f"steps[{i}]"
        if not isinstance(step, dict):
            errors.append(f"{w} must be an object")
            continue
        if step.get("move") not in MOVES:
            errors.append(f"{w}.move must be one of {', '.join(MOVES)}")
        if not isinstance(step.get("think_md"), str):
            errors.append(f"{w}.think_md is missing")
        errors += [f"{w}.doc: {e}" for e in validate_doc(step.get("doc", {}))]
        fs = step.get("false_start")
        if fs is not None:
            if not isinstance(fs, dict) or not isinstance(fs.get("think_md"), str):
                errors.append(f"{w}.false_start needs think_md")
            else:
                errors += [f"{w}.false_start.doc: {e}" for e in validate_doc(fs.get("doc", {}))]
        pr = step.get("predict")
        if pr is not None:
            opts = pr.get("options") if isinstance(pr, dict) else None
            if not isinstance(opts, list) or not opts or not all(isinstance(o, dict) and "id" in o and "text" in o for o in opts):
                errors.append(f"{w}.predict needs options with id and text")
            elif sum(bool(o.get("correct")) for o in opts) != 1:
                errors.append(f"{w}.predict needs exactly one correct option")
    return errors
