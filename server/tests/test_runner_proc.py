"""The real runner against a stub `claude` (a Python script): flags, env, parsing, timeouts, auth gate."""

from __future__ import annotations

import asyncio
import json
import sys
import textwrap
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from offerletter.app import create_app
from offerletter.config import Settings
from offerletter.teammates.personas import Persona
from offerletter.teammates.runner import (
    AuthStatus, ClaudeRunner, GovernedRunner, TeammateError, check_auth,
)

STUB = textwrap.dedent('''
    import json, os, sys, time
    args = sys.argv[1:]
    if args[:2] == ["auth", "status"]:
        print(json.dumps({"loggedIn": True, "authMethod": os.environ.get("STUB_AUTH", "claude.ai")}))
        sys.exit(0)
    msg = json.loads(sys.stdin.readline())
    if os.environ.get("STUB_MODE") == "hang":
        time.sleep(60)
    sheet = args[args.index("--append-system-prompt-file") + 1]
    info = {"args": args, "prompt": msg["message"]["content"], "sheet": open(sheet, encoding="utf-8").read(),
            "has_key": "ANTHROPIC_API_KEY" in os.environ, "cwd": os.getcwd()}
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-1"}))
    print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "rateLimitType": "five_hour",
          "unifiedWindows": {"five_hour": {"utilization": 0.32, "resetsAt": 1792401000}}}}))
    result = {"type": "result", "subtype": "success", "result": json.dumps(info), "session_id": "sess-1",
              "total_cost_usd": 0.001}
    if "--json-schema" in args:
        result["structured_output"] = {"ok": True}
    print(json.dumps(result))
''')


@pytest.fixture
def stub(tmp_path: Path) -> list[str]:
    path = tmp_path / "stub_claude.py"
    path.write_text(STUB, encoding="utf-8")
    return [sys.executable, str(path)]


PERSONA = Persona(id="co.kenji", company_id="co", name="Kenji Mori", role="Tech lead", memory_md="- earlier note")


def test_runner_flags_env_cwd_and_parse(tmp_path: Path, stub: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-stripped")
    runner = ClaudeRunner(tmp_path / "teammates", command=stub)
    reply = asyncio.run(runner.reply(PERSONA, "hello there", model="haiku", resume="old-sess"))
    info = json.loads(reply.text)
    args = info["args"]
    assert reply.session_id == "sess-1" and reply.cost_usd == 0.001 and reply.structured is None
    assert reply.rate_limit["unifiedWindows"]["five_hour"]["utilization"] == 0.32
    assert info["has_key"] is False  # billing env var was stripped
    assert "--bare" not in args
    for flag in ("-p", "--verbose", "--strict-mcp-config", "--disable-slash-commands"):
        assert flag in args
    assert args[args.index("--input-format") + 1] == "stream-json" and args[args.index("--output-format") + 1] == "stream-json"
    assert args[args.index("--model") + 1] == "haiku" and args[args.index("--resume") + 1] == "old-sess"
    assert args[args.index("--setting-sources") + 1] == "project" and args[args.index("--tools") + 1] == ""
    assert args[args.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert info["prompt"] == "hello there" and "earlier note" in info["sheet"] and "Kenji Mori" in info["sheet"]
    assert Path(info["cwd"]).resolve() == (tmp_path / "teammates" / "co" / "kenji").resolve()
    assert not list((tmp_path / "teammates" / "co" / "kenji").glob("sheet-*"))  # temp sheet cleaned up


def test_runner_json_schema_returns_structured(tmp_path: Path, stub: list[str]) -> None:
    runner = ClaudeRunner(tmp_path / "t", command=stub)
    reply = asyncio.run(runner.reply(PERSONA, "grade", json_schema={"type": "object"}))
    assert reply.structured == {"ok": True}
    assert "--json-schema" in json.loads(reply.text)["args"] and "--resume" not in json.loads(reply.text)["args"]


def test_runner_timeout_kills_and_reports(tmp_path: Path, stub: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUB_MODE", "hang")
    runner = ClaudeRunner(tmp_path / "t", command=stub)
    started = time.time()
    with pytest.raises(TeammateError, match="didn't answer"):
        asyncio.run(runner.reply(PERSONA, "hi", timeout_s=1))
    assert time.time() - started < 15


def test_runner_limits_concurrency_to_two(tmp_path: Path) -> None:
    active, peak = 0, 0

    class Counting(ClaudeRunner):
        def _run(self, *a, **k):  # type: ignore[no-untyped-def]
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            time.sleep(0.15)
            active -= 1
            from offerletter.teammates.runner import TeammateReply
            return TeammateReply("x", None, "s", None)

    async def go() -> None:
        r = Counting(tmp_path / "t")
        await asyncio.gather(*(r.reply(PERSONA, "p") for _ in range(6)))

    asyncio.run(go())
    assert peak == 2


def test_missing_command_is_a_clear_error(tmp_path: Path) -> None:
    runner = ClaudeRunner(tmp_path / "t", command=["definitely-not-a-real-command-xyz"])
    with pytest.raises(TeammateError, match="Couldn't start"):
        asyncio.run(runner.reply(PERSONA, "hi"))


def test_auth_gate(stub: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    assert check_auth(stub).ok
    monkeypatch.setenv("STUB_AUTH", "api_key")
    bad = check_auth(stub)
    assert not bad.ok and bad.logged_in and "not a Claude plan" in bad.message
    assert not check_auth(["definitely-not-a-real-command-xyz"]).ok


def test_health_reports_disabled_teammates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import offerletter.app as app_module
    monkeypatch.setattr(app_module, "check_auth", lambda: AuthStatus(False, True, "api_key", "Teammates are off: use /login."))
    settings = Settings(home=tmp_path / "h", content_dir=Path(__file__).parent / "fixtures" / "content")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health").json()
        assert health["teammates"] is False and health["claude"]["authMethod"] == "api_key"
        assert "Teammates are off" in health["claude"]["message"]
        client.post("/api/onboarding/player", json={"name": "L"})
        # chat still posts; the teammate side says why nobody answers
        assert client.post("/api/onboarding/accept", json={"company_id": "testco"}).status_code == 200
        client.post("/api/channels/testco.dm.peer/messages", json={"body_md": "hi"})
        deadline = time.time() + 5
        svc = client.app.state.services
        while time.time() < deadline and not any(e["type"] == "notice" and "Teammates are off" in e["data"]["text"] for e in svc.bus.history):
            time.sleep(0.05)
        assert any(e["type"] == "notice" and e["data"]["level"] == "warn" for e in svc.bus.history)


def test_governed_runner_wraps_inner(tmp_path: Path) -> None:
    from offerletter.db import Database
    from offerletter.events import EventBus
    from offerletter.teammates.governor import Governor
    from offerletter.teammates.runner import FakeRunner, TeammatesUnavailable
    db, bus = Database(":memory:"), EventBus()
    gov = Governor(db, bus, clock=lambda: 1.0)
    fake = FakeRunner(rate_limit={"unifiedWindows": {"five_hour": {"utilization": 0.95, "resetsAt": 4102444800}}})
    governed = GovernedRunner(fake, gov)
    asyncio.run(governed.reply(PERSONA, "one"))
    assert gov.mode == "lunch"
    with pytest.raises(TeammatesUnavailable, match="out to lunch"):
        asyncio.run(governed.reply(PERSONA, "two"))
    assert len(fake.calls) == 1
