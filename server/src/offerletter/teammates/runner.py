"""Runs teammates as headless `claude -p` processes on the learner's Claude plan (never API billing).

Hard rules (CLAUDE.md): strip the API-billing env vars, refuse unless `claude auth status` says
authMethod claude.ai, never pass --bare, at most 2 claude processes at once.

Each call is one process: the prompt goes in as one stream-json user message, stdin closes, and we
read the stream-json lines it prints. The process runs in a worker thread so this works on any
asyncio loop (Windows included).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .governor import Governor
from .personas import Persona

API_BILLING_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)
MAX_CONCURRENT = 2


class TeammateError(RuntimeError):
    """A teammate call failed; the message is safe to show the learner."""


class TeammatesUnavailable(TeammateError):
    """Teammates are off: not signed in on a Claude plan, or out to lunch."""


@dataclass
class TeammateReply:
    text: str  # final assistant text (the JSON string when json_schema was given)
    structured: dict | None
    session_id: str
    rate_limit: dict | None  # the last rate_limit_event's rate_limit_info
    cost_usd: float | None = None


class TeammateRunner(Protocol):
    async def reply(
        self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
        timeout_s: float = 120, resume: str | None = None,
    ) -> TeammateReply: ...


# -- plan check and environment -----------------------------------------------------------------


def plan_env() -> dict[str, str]:
    """Child environment: no API-billing vars, and Claude Code's auto-memory off.

    With --tools "" the model still sees the auto-memory instructions, and on "remember this" prompts Haiku
    writes memory-file tool calls that can't run ("tool call could not be parsed"). Our own persona_memory
    table is the only memory teammates get.
    """
    env = {k: v for k, v in os.environ.items() if k not in API_BILLING_VARS}
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


@dataclass
class AuthStatus:
    ok: bool
    logged_in: bool
    auth_method: str | None
    message: str  # empty when ok


def check_auth(command: list[str] | None = None, timeout_s: float = 60) -> AuthStatus:
    """Runs `claude auth status`. Only authMethod claude.ai passes."""
    cmd = command or [shutil.which("claude") or "claude"]
    try:
        done = subprocess.run(
            [*cmd, "auth", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=plan_env(), timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired):
        return AuthStatus(False, False, None, "Teammates are off: the `claude` command wasn't found or didn't "
                          "answer. Install Claude Code and sign in with your Claude account.")
    try:
        status = json.loads(done.stdout)
    except json.JSONDecodeError:
        return AuthStatus(False, False, None, "Teammates are off: `claude auth status` gave an unexpected answer.")
    logged_in, method = bool(status.get("loggedIn")), status.get("authMethod")
    if not logged_in:
        return AuthStatus(False, False, method, "Teammates are off: run `claude`, type /login, and pick your "
                          "Claude account.")
    if method != "claude.ai":
        return AuthStatus(False, True, method, f"Teammates are off: Claude Code is signed in with {method!r}, not "
                          "a Claude plan, so it would bill an API account. Run `claude`, type /login and choose "
                          "your Claude subscription.")
    return AuthStatus(True, True, method, "")


# -- stream-json parsing ------------------------------------------------------------------------


@dataclass
class ParsedRun:
    session_id: str = ""
    text: str = ""
    structured: dict | None = None
    rate_limit: dict | None = None
    cost_usd: float | None = None
    is_error: bool = False
    subtype: str = ""
    saw_result: bool = False


def parse_stream(lines: Iterable[str]) -> ParsedRun:
    """Folds stream-json lines into one result. Unknown or malformed lines are skipped."""
    run = ParsedRun()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue
        kind = msg.get("type")
        if msg.get("session_id"):
            run.session_id = msg["session_id"]
        if kind == "rate_limit_event":
            run.rate_limit = msg.get("rate_limit_info") or run.rate_limit
        elif kind == "result":
            run.saw_result = True
            run.subtype = msg.get("subtype", "")
            run.is_error = bool(msg.get("is_error")) or run.subtype not in ("success", "")
            run.text = msg.get("result") or ""
            structured = msg.get("structured_output")
            run.structured = structured if isinstance(structured, dict) else None
            run.cost_usd = msg.get("total_cost_usd")
    return run


# -- the real runner ----------------------------------------------------------------------------


def kill_tree(proc: subprocess.Popen[Any]) -> None:
    """Kills the process and its children (claude spawns helpers). taskkill on Windows."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


class ClaudeRunner:
    """Spawns `claude -p` per call. `command` is injectable so tests can point at a stub script."""

    def __init__(self, teammates_dir: Path, command: list[str] | None = None, max_concurrent: int = MAX_CONCURRENT):
        self._dir = teammates_dir
        self._command = command or [shutil.which("claude") or "claude"]
        self._sem = asyncio.Semaphore(max_concurrent)

    def build_args(self, model: str, prompt_file: Path, json_schema: dict | None, resume: str | None) -> list[str]:
        """Exactly the flags ARCHITECTURE section 6 lists (and never --bare)."""
        args = [
            "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            "--model", model, "--setting-sources", "project", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--disable-slash-commands", "--tools", "",
            "--append-system-prompt-file", str(prompt_file),
        ]
        if resume:
            args += ["--resume", resume]
        if json_schema is not None:
            args += ["--json-schema", json.dumps(json_schema)]
        return args

    async def reply(
        self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
        timeout_s: float = 120, resume: str | None = None,
    ) -> TeammateReply:
        cwd = self._dir / persona.company_id / persona.slug
        cwd.mkdir(parents=True, exist_ok=True)
        async with self._sem:
            for attempt in (1, 2):
                try:
                    return await asyncio.to_thread(
                        self._run, persona, prompt, cwd, model or persona.model, json_schema, timeout_s, resume,
                    )
                except TeammateError as exc:
                    if attempt == 2 or "could not be parsed" not in str(exc):
                        raise  # only the model's occasional malformed tool call is worth one more try
            raise AssertionError("unreachable")

    def _run(self, persona: Persona, prompt: str, cwd: Path, model: str, json_schema: dict | None,
             timeout_s: float, resume: str | None) -> TeammateReply:
        fd, name = tempfile.mkstemp(prefix="sheet-", suffix=".md", dir=cwd)
        prompt_file = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(persona.system_prompt())
        message = json.dumps({"type": "user", "message": {"role": "user", "content": prompt}}) + "\n"
        try:
            proc = subprocess.Popen(
                [*self._command, *self.build_args(model, prompt_file, json_schema, resume)], cwd=cwd,
                env=plan_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
        except OSError as exc:
            prompt_file.unlink(missing_ok=True)
            raise TeammateError(f"Couldn't start Claude Code: {exc}") from exc
        try:
            try:
                out, err = proc.communicate(message, timeout=timeout_s)
            except subprocess.TimeoutExpired:
                kill_tree(proc)
                proc.communicate()
                raise TeammateError(f"{persona.first_name} didn't answer within {int(timeout_s)} seconds.") from None
        finally:
            prompt_file.unlink(missing_ok=True)
        run = parse_stream(out.splitlines())
        if not run.saw_result:
            raise TeammateError(f"Claude Code ended without an answer. {err.strip()[:300]}".strip())
        if run.is_error:
            raise TeammateError(f"Claude Code reported an error ({run.subtype}): {run.text[:300]}")
        return TeammateReply(run.text, run.structured, run.session_id, run.rate_limit, run.cost_usd)


class DisabledRunner:
    """Used when the CLI isn't signed in on a Claude plan; every call explains why."""

    def __init__(self, message: str):
        self.message = message

    async def reply(self, persona: Persona, prompt: str, **_: Any) -> TeammateReply:
        raise TeammatesUnavailable(self.message)


class FakeRunner:
    """Test double. `responder(persona, prompt)` returns the reply text; `structured` answers schema calls."""

    def __init__(self, responder: Callable[[Persona, str], str] | None = None, structured: dict | None = None,
                 rate_limit: dict | None = None):
        self.responder = responder or (lambda persona, prompt: f"{persona.first_name} here. Got it.")
        self.structured = structured
        self.rate_limit = rate_limit
        self.calls: list[dict[str, Any]] = []

    async def reply(
        self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
        timeout_s: float = 120, resume: str | None = None,
    ) -> TeammateReply:
        self.calls.append({"persona": persona, "prompt": prompt, "model": model or persona.model,
                           "json_schema": json_schema, "resume": resume})
        if json_schema is not None:
            return TeammateReply(json.dumps(self.structured), self.structured, "fake-session", self.rate_limit, 0.0)
        return TeammateReply(self.responder(persona, prompt), None, "fake-session", self.rate_limit, 0.0)


class GovernedRunner:
    """Wraps a runner with the governor: refuse at lunch, force Haiku when thrifty, learn from every run."""

    def __init__(self, inner: TeammateRunner, governor: Governor):
        self.inner, self.governor = inner, governor

    async def reply(
        self, persona: Persona, prompt: str, *, model: str | None = None, json_schema: dict | None = None,
        timeout_s: float = 120, resume: str | None = None,
    ) -> TeammateReply:
        if self.governor.mode == "lunch":
            raise TeammatesUnavailable(self.governor.lunch_message())
        wanted = self.governor.model_for(model or persona.model)
        result = await self.inner.reply(persona, prompt, model=wanted, json_schema=json_schema,
                                        timeout_s=timeout_s, resume=resume)
        self.governor.update(result.rate_limit)
        return result
