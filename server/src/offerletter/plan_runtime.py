"""Helpers that the generated plan-example tests use. SELF-CONTAINED: standard library + pytest only.

`plan_examples.py` pastes this file's source (below the marker) into the generated test file, so the same tests
run on the server (against a temp checkout) and in his repo after "write to branch" (`tests/plan/...`).
Nothing here may import from the `offerletter` package.
"""
# --- generated-tests runtime: everything below this line is copied into the test file ---
import builtins
import importlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

SHOW = 500  # characters of a value or of output quoted in a message


def _short(value, limit=SHOW):
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + " ..."


def _fail(message):
    pytest.fail("FAIL: " + message, pytrace=False)


def _error(message):
    pytest.fail("ERROR: " + message, pytrace=False)


def _resolve(target):
    """Imports a dotted path: the longest importable module prefix, then attributes. Returns (object, module)."""
    parts = target.split(".")
    last_error = None
    for cut in range(len(parts), 0, -1):
        try:
            module = importlib.import_module(".".join(parts[:cut]))
        except ImportError as exc:
            last_error = exc
            continue
        obj = module
        try:
            for name in parts[cut:]:
                obj = getattr(obj, name)
        except AttributeError:
            _error(f"{target} does not exist yet: {parts[cut]!r} is not in {'.'.join(parts[:cut])}.")
        return obj, module
    _error(f"I can't import {target}: {last_error}")


def _within(seconds, fn):
    """Runs fn() in a daemon thread. Returns ('ok', value), ('raised', exception) or ('timeout', None)."""
    box = {}

    def work():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001  (we report whatever the code under test raised)
            box["raised"] = exc

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(seconds)
    if thread.is_alive():
        return "timeout", None
    if "raised" in box:
        return "raised", box["raised"]
    return "ok", box.get("value")


def run_call(target, args, expect, compare, timeout):
    obj, module = _resolve(target)
    scope = {**vars(builtins), **vars(module), "__plan_target__": obj}
    try:
        expected = eval(expect, dict(scope)) if expect.strip() else None
    except Exception as exc:  # noqa: BLE001
        _error(f"I can't evaluate your expected value ({_short(expect, 80)}): {type(exc).__name__}: {exc}")
    state, got = _within(timeout, lambda: eval(f"__plan_target__({args})", dict(scope)))
    if state == "timeout":
        _error(f"The call took longer than {timeout} seconds.")
    if compare == "raises":
        if state == "ok":
            _fail(f"expected {_short(expect, 80)} to be raised, but it returned {_short(got)}")
        if not (isinstance(expected, type) and isinstance(got, expected)):
            _fail(f"expected {_short(expect, 80)}, but it raised {type(got).__name__}: {_short(str(got), 200)}")
        return
    if state == "raised":
        _error(f"it raised {type(got).__name__}: {_short(str(got), 300)}")
    if compare == "truthy":
        if not got:
            _fail(f"expected something truthy, got {_short(got)}")
    elif compare == "approx":
        if got != pytest.approx(expected):
            _fail(f"expected about {_short(expected)}, got {_short(got)}")
    elif got != expected:
        _fail(f"expected {_short(expected)}, got {_short(got)}")


# -- fixtures (a fake server the CLI examples talk to) ----------------------------------------------


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _kill(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        pass


def program_env(root):
    extra = os.pathsep.join([str(root / "src"), str(root)])
    return {**os.environ, "PYTHONPATH": extra + os.pathsep + os.environ.get("PYTHONPATH", ""),
            "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}


def start_fixture(fixture, extra_args, root, python=None, ready_s=10.0):
    """Starts a fixture process; returns (process, url) once it is ready. `python` replaces the argv token 'python'.
    Calls pytest.fail with an ERROR when it won't start or isn't ready in ready_s seconds."""
    port = free_port()
    python = python or [sys.executable]
    tokens = list(fixture["start"])
    if tokens[:3] == ["uv", "run", "python"]:  # we are already inside the project's environment
        tokens = tokens[2:]
    argv = []
    for token in tokens:
        argv += python if token == "python" else [token.replace("{port}", str(port))]
    argv += [a.replace("{port}", str(port)) for a in shlex.split(extra_args or "")]
    url = fixture.get("url_template", "http://127.0.0.1:{port}").replace("{port}", str(port))
    proc = subprocess.Popen(argv, cwd=root, env=program_env(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    lines = []

    def pump():
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))

    threading.Thread(target=pump, daemon=True).start()
    ready = fixture.get("ready") or {"kind": "http", "path": "/"}
    deadline = time.monotonic() + ready_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            time.sleep(0.2)
            _error(f"The {fixture.get('label', fixture.get('id', 'fixture'))} stopped right after starting: "
                   + _short("\n".join(lines[-8:]), 400))
        if ready.get("kind") == "line":
            if any(re.search(ready.get("regex", ""), line) for line in lines):
                return proc, url
        else:
            try:
                urllib.request.urlopen(url + ready.get("path", "/"), timeout=1).close()
                return proc, url
            except urllib.error.HTTPError:
                return proc, url  # it answered, so it is listening
            except (urllib.error.URLError, OSError):
                pass
        time.sleep(0.1)
    _kill(proc)
    _error(f"The {fixture.get('label', fixture.get('id', 'fixture'))} wasn't ready after {int(ready_s)} seconds.")


def _dig(node, path):
    """Follows a dotted string or a list of keys. Dotted keys like p99.9 work: the longest matching key wins."""
    parts = list(path) if isinstance(path, (list, tuple)) else str(path).split(".")
    while parts:
        if isinstance(node, dict):
            for cut in range(len(parts), 0, -1):
                key = parts[0] if cut == 1 else ".".join(parts[:cut])
                if key in node:
                    node, parts = node[key], parts[cut:]
                    break
            else:
                raise KeyError(".".join(parts))
        elif isinstance(node, list) and parts[0].lstrip("-").isdigit():
            node, parts = node[int(parts[0])], parts[1:]
        else:
            raise KeyError(".".join(parts))
    return node


def _json_of(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            raise
        return json.JSONDecoder().raw_decode(text[start:])[0]


def _apply_check(check, done):
    kind, path, value = check.get("kind"), check.get("path"), check.get("value")
    if kind == "exit":
        want = int(value) if str(value or "").strip() else 0
        if done.returncode != want:
            _fail(f"expected exit code {want}, got {done.returncode}. {_short((done.stderr or done.stdout).strip(), 300)}")
    elif kind in ("stdout_contains", "stderr_contains"):
        text = done.stdout if kind == "stdout_contains" else done.stderr
        if str(value or "") not in (text or ""):
            _fail(f"{'stdout' if kind == 'stdout_contains' else 'stderr'} doesn't contain {_short(str(value), 80)}. "
                  f"It has: {_short((text or '').strip(), 300)}")
    else:
        try:
            data = _json_of(done.stdout or "")
        except json.JSONDecodeError:
            _fail(f"stdout isn't JSON, so I can't look at {path}. It starts: {_short((done.stdout or '').strip(), 200)}")
        try:
            got = _dig(data, path)
        except (KeyError, IndexError, TypeError):
            if kind == "json_has":
                _fail(f"the JSON has no {path if isinstance(path, str) else '.'.join(path)}")
            _fail(f"the JSON has no {path if isinstance(path, str) else '.'.join(path)}, so I can't compare it")
        if kind == "json_eq":
            try:
                want = json.loads(str(value))
            except json.JSONDecodeError:
                want = value
            if got != want and str(got) != str(value):
                _fail(f"{path} is {_short(got, 120)}, you expected {_short(value, 120)}")
        elif kind in ("json_gt", "json_lt"):
            try:
                a, b = float(got), float(value)
            except (TypeError, ValueError):
                _fail(f"{path} is {_short(got, 80)}, which isn't a number I can compare with {_short(value, 80)}")
            if kind == "json_gt" and not a > b:
                _fail(f"{path} is {got}, you expected more than {value}")
            if kind == "json_lt" and not a < b:
                _fail(f"{path} is {got}, you expected less than {value}")


def run_cli(package, args, fixture, fixture_args, checks, root, timeout, python=None):
    """Runs `python -m <package> <args>` (with the fixture's URL injected) and applies the checks."""
    proc = None
    argv = shlex.split(args or "")
    try:
        if fixture:
            proc, url = start_fixture(fixture, fixture_args, root, python=python)
            inject = fixture.get("inject") or {"kind": "arg", "flag": "--url"}
            if inject.get("kind") == "arg" and inject.get("flag"):
                argv += [inject["flag"], url]
        cmd = [*(python or [sys.executable]), "-m", package, *argv]
        try:
            done = subprocess.run(cmd, cwd=root, env=program_env(root), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            _error(f"The command ran longer than {timeout} seconds.")
        except OSError as exc:
            _error(f"I couldn't start the command: {exc}")
        for check in checks or [{"kind": "exit", "value": "0"}]:
            _apply_check(check, done)
    finally:
        if proc is not None:
            _kill(proc)
