"""Reading Python source with `ast` for the Plan stage: the outline, call sites, symbol and module lookup.

Pure functions over a directory (a temp checkout of a ref). Nothing here runs the code. `verify_kit.py`
imports this module too, so the kit check and the server agree on what "resolves" means.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".tox", ".mypy_cache",
             ".pytest_cache", ".ruff_cache"}
MAX_FILE_BYTES = 400_000


def is_test_path(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    return "tests" in parts[:-1] or "test" in parts[:-1] or name.startswith("test_") or name == "conftest.py"


def python_files(root: Path) -> Iterator[tuple[str, Path]]:
    """(posix path relative to root, file) for each .py file, skipping virtualenvs and caches. Sorted."""
    found = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(p in SKIP_DIRS or p.endswith(".egg-info") for p in rel.parts[:-1]):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        found.append((rel.as_posix(), path))
    yield from sorted(found)


def parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return None


# -- signatures and doc lines ---------------------------------------------------------------------


def _arg(a: ast.arg, default: ast.expr | None) -> str:
    text = a.arg
    if a.annotation is not None:
        text += f": {ast.unparse(a.annotation)}"
    if default is not None:
        text += (" = " if a.annotation is not None else "=") + ast.unparse(default)
    return text


def args_text(args: ast.arguments) -> str:
    """The parameter list rebuilt from the AST, e.g. `values, p=50, *, strict: bool = False, **kw`."""
    parts: list[str] = []
    positional = [*args.posonlyargs, *args.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for i, (a, d) in enumerate(zip(positional, defaults, strict=True)):
        parts.append(_arg(a, d))
        if args.posonlyargs and i == len(args.posonlyargs) - 1:
            parts.append("/")
    if args.vararg is not None:
        parts.append("*" + _arg(args.vararg, None))
    elif args.kwonlyargs:
        parts.append("*")
    for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        parts.append(_arg(a, d))
    if args.kwarg is not None:
        parts.append("**" + _arg(args.kwarg, None))
    return ", ".join(parts)


def signature_of(node: ast.AST) -> str:
    """`def name(args) -> ret`, `async def ...` or `class Name(bases)`: the header line without the colon."""
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] + [f"{k.arg}={ast.unparse(k.value)}" for k in node.keywords if k.arg]
        return f"class {node.name}" + (f"({', '.join(bases)})" if bases else "")
    assert isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ret = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{'async def' if isinstance(node, ast.AsyncFunctionDef) else 'def'} {node.name}({args_text(node.args)}){ret}"


def first_doc_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node)  # type: ignore[arg-type]
    return doc.strip().splitlines()[0].strip() if doc and doc.strip() else ""


# -- the outline ---------------------------------------------------------------------------------


def _symbols(tree: ast.Module) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(body: list[ast.stmt], prefix: str, in_class: bool) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qual = f"{prefix}{node.name}"
                out.append({"name": node.name, "qualname": qual, "kind": "class", "line": node.lineno,
                            "signature": signature_of(node), "doc": first_doc_line(node)})
                walk(node.body, qual + ".", True)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                kind = "method" if in_class else ("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function")
                out.append({"name": node.name, "qualname": f"{prefix}{node.name}", "kind": kind, "line": node.lineno,
                            "signature": signature_of(node), "doc": first_doc_line(node)})
            elif isinstance(node, ast.If | ast.Try):  # `if TYPE_CHECKING:` / try-import blocks still define things
                for block in (node.body, node.orelse, *(h.body for h in getattr(node, "handlers", []))):
                    walk(block, prefix, in_class)

    walk(tree.body, "", False)
    return out


def outline(root: Path, include_tests: bool = False) -> list[dict[str, Any]]:
    """[{path, symbols: [{name, qualname, kind, line, signature, doc}]}] for each Python file, src first."""
    files = []
    for rel, path in python_files(root):
        if not include_tests and is_test_path(rel):
            continue
        tree = parse(path)
        if tree is None:
            continue
        files.append({"path": rel, "symbols": _symbols(tree)})
    return sorted(files, key=lambda f: (not f["path"].startswith("src/"), f["path"]))


def write_cache(cache: Path, data: dict[str, Any]) -> None:
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def read_cache(cache: Path) -> dict[str, Any] | None:
    try:
        return json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def symbol_index(files: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """(path, qualname) -> symbol, for outline data."""
    return {(f["path"], s["qualname"]): s for f in files for s in f["symbols"]}


def norm_path(path: str) -> str:
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


# -- module names ---------------------------------------------------------------------------------


def module_name(rel: str) -> str:
    """`src/kiln_bench/metrics.py` -> `kiln_bench.metrics`; `pkg/__init__.py` -> `pkg`."""
    parts = rel[:-3].split("/") if rel.endswith(".py") else rel.split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_target(files: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    """Looks a dotted import path up in the outline: `kiln_bench.metrics.percentile`, `pkg.mod.Class.method`.
    Returns {path, symbol, module} or None. A bare module (`kiln_bench.metrics`) resolves with symbol ''."""
    target = target.strip()
    if not target:
        return None
    by_module = {module_name(f["path"]): f for f in files}
    parts = target.split(".")
    for cut in range(len(parts), 0, -1):  # longest module prefix first
        module = ".".join(parts[:cut])
        f = by_module.get(module)
        if f is None:
            continue
        rest = ".".join(parts[cut:])
        if not rest:
            return {"path": f["path"], "symbol": "", "module": module}
        if any(s["qualname"] == rest for s in f["symbols"]):
            return {"path": f["path"], "symbol": rest, "module": module}
    return None


def module_for_where(files: list[dict[str, Any]], where: str) -> str | None:
    """A step's `where` (a module path like `kiln_bench.metrics` or a file path) -> the file path in the outline."""
    where = where.strip()
    if not where:
        return None
    wanted = norm_path(where)
    for f in files:
        if f["path"] == wanted or module_name(f["path"]) == where:
            return f["path"]
    if wanted.endswith(".py"):
        return wanted
    return wanted.replace(".", "/") + ".py" if "/" not in wanted else wanted


# -- call sites ----------------------------------------------------------------------------------


class _Calls(ast.NodeVisitor):
    def __init__(self, names: set[str]):
        self.names, self.stack = names, []
        self.hits: list[tuple[str, str, int]] = []  # (called name, enclosing qualname, line)

    def _scoped(self, node: ast.AST, name: str) -> None:
        self.stack.append(name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scoped(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scoped(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scoped(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name in self.names:
            self.hits.append((name, ".".join(self.stack) or "<module>", node.lineno))
        self.generic_visit(node)


def call_sites(root: Path, symbol: str, defined_in: str | None = None) -> list[dict[str, Any]]:
    """Real call sites of a symbol by its last name: calls whose callee name or attribute matches, anywhere in
    the repo (tests included), minus calls inside the symbol's own body (recursion) and the definition itself.
    [{path, symbol (the caller's qualname), line, test (a test file)}]"""
    last = symbol.rsplit(".", 1)[-1]
    out = []
    for rel, path in python_files(root):
        tree = parse(path)
        if tree is None:
            continue
        visitor = _Calls({last})
        visitor.visit(tree)
        for _, caller, line in visitor.hits:
            if defined_in == rel and (caller == symbol or caller.startswith(symbol + ".")):
                continue
            out.append({"path": rel, "symbol": caller, "line": line, "test": is_test_path(rel)})
    return out


# -- what changed between two trees ---------------------------------------------------------------


def _class_own_source(node: ast.ClassDef) -> str:
    """A class's header and its non-def statements; its methods are listed on their own."""
    body = [n for n in node.body if not isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)]
    shell = ast.ClassDef(name=node.name, bases=node.bases, keywords=node.keywords, body=body or [ast.Pass()],
                         decorator_list=node.decorator_list, type_params=getattr(node, "type_params", []))
    return ast.unparse(ast.fix_missing_locations(shell))


def symbol_sources(text: str) -> dict[str, str]:
    """qualname -> normalised source (ast.unparse) of every function and class in a file, for diffing."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return {}
    out: dict[str, str] = {}

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                out[f"{prefix}{node.name}"] = _class_own_source(node)
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                out[f"{prefix}{node.name}"] = ast.unparse(node)
            elif isinstance(node, ast.If | ast.Try):
                for block in (node.body, node.orelse):
                    walk(block, prefix)

    walk(tree.body, "")
    return out


def changed_symbols(before: str | None, after: str | None) -> list[str]:
    """Qualnames whose source differs, appeared or disappeared (a class counts for its own lines only)."""
    old, new = symbol_sources(before or ""), symbol_sources(after or "")
    return [name for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)]
