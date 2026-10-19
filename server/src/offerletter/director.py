"""The director (v0.1, mostly rules): who answers, when, and the scripted welcome.

It never decides anything clever. It routes a player message to a fitting teammate with simple keyword
rules, shows "typing", waits a believable time, and posts what the teammate (a `claude -p` run) wrote.
Sometimes nobody answers, on purpose, so the channel doesn't feel like a chatbot.
"""

from __future__ import annotations

import asyncio
import random
import re
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from .config import Settings
from .db import Database, Row, decode, dumps, new_id, now
from .events import EventBus
from .teammates import personas as pm
from .teammates.governor import Governor
from .teammates.personas import Persona
from .teammates.runner import TeammateError, TeammateRunner

HISTORY = 15
MIN_DELAY, MAX_DELAY = 3.0, 20.0
NO_REPLY = "NO_REPLY"

# role substring -> words that make that person the natural responder
ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "engineering manager": ("schedule", "on-call", "oncall", "time off", "vacation", "feedback", "1:1", "team", "promotion",
                "onboarding", "goals", "expectations"),
    "tech lead": ("pr", "review", "ticket", "merge", "test", "tests", "benchmark", "p99", "latency", "design",
                  "branch", "repo", "setup", "bug", "deploy"),
    "senior": ("why", "how does", "gpu", "cache", "batch", "performance", "architecture", "tradeoff", "deep"),
    "product manager": ("customer", "deadline", "when", "priority", "roadmap", "scope", "launch", "users"),
    "intern": ("intern", "pair", "newbie"),
    "engineer": ("code", "function", "bug", "pr", "help", "stuck"),
}
QUESTION_START = re.compile(r"^\s*(how|what|why|when|where|who|can|could|should|do|does|is|are|any)\b", re.I)


def typing_delay(text: str) -> float:
    """Seconds a person would take: 3 s floor, grows with length, 20 s ceiling."""
    return min(MAX_DELAY, max(MIN_DELAY, 2.0 + len(text) / 12))


class Director:
    def __init__(self, db: Database, bus: EventBus, settings: Settings, runner: TeammateRunner,
                 governor: Governor, rng: random.Random | None = None,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.db, self.bus, self.settings, self.runner, self.governor = db, bus, settings, runner, governor
        self.rng, self._sleep = rng or random.Random(), sleep
        self._tasks: set[asyncio.Task[Any]] = set()

    # -- plumbing -------------------------------------------------------------------------------

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def idle(self) -> None:
        """Waits for all background teammate work (tests and shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def pause(self, seconds: float) -> None:
        if seconds > 0:
            await self._sleep(seconds * self.settings.delay_scale)

    def post(self, channel_id: str, author: str, body_md: str, attachments: list[dict] | None = None,
             thread_root_id: str | None = None) -> Row:
        row = self.db.insert("message", id=new_id(), channel_id=channel_id, author=author, body_md=body_md,
                             thread_root_id=thread_root_id, attachments_json=dumps(attachments or []),
                             created_at=now())
        out = decode(row)
        assert out is not None
        self.bus.publish("message.created", out)
        return out

    def typing(self, persona: Persona, channel_id: str, on: bool) -> None:
        self.bus.publish("teammate.typing", {"persona_id": persona.id, "channel_id": channel_id, "typing": on})

    def personas(self, company_id: str) -> list[Persona]:
        return [pm.persona_from_row(r, pm.get_memory(self.db, r["id"]))
                for r in self.db.where("persona", company_id=company_id)]

    def memory_of(self, persona_id: str) -> str:
        return pm.get_memory(self.db, persona_id)

    def note(self, persona_id: str, text: str) -> None:
        """Appends a server-side note to one persona's memory (e.g. 'Luigi caught 4/5 issues in PR #1')."""
        row = self.db.get("persona", persona_id)
        if row:
            pm.append_note(self.db, pm.persona_from_row(row), text)

    # -- welcome --------------------------------------------------------------------------------

    def start_welcome(self, company_id: str, company_name: str, player: Row, first_ticket: Row | None) -> None:
        self.spawn(self._welcome(company_id, company_name, player, first_ticket))

    async def _welcome(self, company_id: str, company_name: str, player: Row, first_ticket: Row | None) -> None:
        people = self.personas(company_id)
        manager, lead = pm.pick_role(people, "engineering manager", "manager"), pm.pick_role(people, "tech lead", "lead")
        channels = self.db.where("channel", company_id=company_id, kind="channel")
        team = channels[0]["id"] if channels else None
        name = player["name"]
        if manager:
            await self._scripted(manager, f"{company_id}.dm.{manager.slug}", 2, (
                f"Hi {name}, welcome to {company_name}. I'm {manager.first_name}, your manager. Your laptop "
                "checklist is in the setup panel: clone the repo, get the tests green, tell me if anything is "
                "stuck. No rush on day one. Ask me anything."))
        if lead and team:
            await self._scripted(lead, team, 3, f"Welcome {name}! {lead.first_name} here, I run the technical side of this team.")
            if first_ticket:
                await self._scripted(lead, team, 3, (
                    f"{name}, I assigned you **{first_ticket['id']}: {first_ticket['title']}**. Start by reviewing "
                    "the open PR. Leave comments right on the lines you doubt. Tell me what you find."),
                    attachments=[{"type": "ticket", "ticket_id": first_ticket["id"]}])

    async def _scripted(self, persona: Persona, channel_id: str, wait: float, body: str,
                        attachments: list[dict] | None = None) -> None:
        await self.pause(wait)
        self.typing(persona, channel_id, True)
        await self.pause(typing_delay(body) / 3)
        self.typing(persona, channel_id, False)
        self.post(channel_id, persona.id, body, attachments)

    # -- clock in -------------------------------------------------------------------------------

    def clock_in(self, company_id: str, minutes: int) -> str:
        """Records the session and has the tech lead post the standup prompt. Returns the team channel id."""
        people = self.personas(company_id)
        lead = pm.pick_role(people, "tech lead", "lead") or (people[0] if people else None)
        channels = self.db.where("channel", company_id=company_id, kind="channel")
        team = channels[0]["id"]
        player = self.db.one("SELECT name FROM player LIMIT 1") or {"name": "there"}
        self.db.insert("work_session", id=new_id(), company_id=company_id, minutes=minutes, started_at=now(),
                       standup_channel_id=team, thanked=0)
        if lead:
            body = (f"Morning {player['name']}. Standup: what are you working on today, and is anything blocking "
                    f"you? You've got {minutes} minutes blocked out, so say what you want done by the end of it.")
            self.spawn(self._scripted(lead, team, 1, body))
        return team

    def _maybe_thank(self, channel: Row) -> None:
        """The manager says a brief thanks to the first standup reply of the day, never more than once a day."""
        today = now()[:10]
        sessions = self.db.all("SELECT * FROM work_session WHERE company_id = ? AND substr(started_at, 1, 10) = ? "
                               "ORDER BY rowid", (channel["company_id"], today))
        if not sessions or any(s["thanked"] for s in sessions) or sessions[-1]["standup_channel_id"] != channel["id"]:
            return
        manager = pm.pick_role(self.personas(channel["company_id"]), "engineering manager", "manager")
        if manager is None:
            return
        self.db.update("work_session", sessions[-1]["id"], thanked=1)
        body = self.rng.choice(["Thanks, sounds good.", "Thanks for the update.", "Got it, thanks."])
        self.spawn(self._scripted(manager, channel["id"], 2, body))

    # -- player messages ------------------------------------------------------------------------

    def choose_responders(self, channel: Row, body: str, people: list[Persona]) -> list[Persona]:
        """DM -> that person. @mention -> the mentioned. Otherwise the best keyword fit, sometimes nobody."""
        if channel["kind"] == "dm":
            members = decode(channel)["members"] or []
            return [p for p in people if p.id in members]
        text = body.casefold()
        mentioned = [
            p for p in people
            if re.search(rf"@{re.escape(p.slug.casefold())}\b|@{re.escape(p.first_name.casefold())}\b", text)
        ]
        if mentioned:
            return mentioned[:2]
        asks = "?" in body or bool(QUESTION_START.match(body))
        scores = []
        for p in people:
            score = 3 if re.search(rf"\b{re.escape(p.first_name.casefold())}\b", text) else 0
            for role, words in ROLE_KEYWORDS.items():
                if re.search(rf"\b{re.escape(role)}\b", p.role, re.I):
                    score += sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", text))
            scores.append((score, p))
        best_score, best = max(scores, key=lambda s: s[0], default=(0, None))
        if best is None:
            return []
        if best_score == 0:
            if not asks:
                return []  # small talk nobody owns: silence is realistic
            lead = pm.pick_role(people, "tech lead", "lead") or best
            return [lead] if self.rng.random() < 0.8 else []
        return [best] if self.rng.random() < 0.9 else []

    def on_player_message(self, channel: Row, message: Row) -> None:
        if channel["kind"] == "channel":
            self._maybe_thank(channel)
        people = self.personas(channel["company_id"])
        for persona in self.choose_responders(channel, message["body_md"], people):
            self.spawn(self._reply(persona, channel, message))

    def prompt_for(self, persona: Persona, channel: Row, player_name: str, people: list[Persona]) -> str:
        names = {p.id: p.name for p in people} | {"player": player_name, "system": "System"}
        recent = self.db.all("SELECT * FROM message WHERE channel_id = ? ORDER BY rowid DESC LIMIT ?",
                             (channel["id"], HISTORY))[::-1]
        chat = "\n".join(f"{names.get(m['author'], m['author'])}: {m['body_md']}" for m in recent)
        where = f"a direct message with {player_name}" if channel["kind"] == "dm" else f"#{channel['name']}"
        return (
            f"Recent messages in {where} (oldest first):\n{chat}\n\n"
            f"Write {persona.first_name}'s next chat message. Chat style: one to three short sentences, natural, "
            "no headings, no lists unless you are really listing things, no preamble, no quotation marks around it. "
            f"If this isn't something {persona.first_name} would answer, reply with exactly {NO_REPLY}."
        )

    async def _reply(self, persona: Persona, channel: Row, message: Row) -> None:
        if self.governor.mode == "lunch":
            self.bus.notice(self.governor.lunch_message())
            return
        player = self.db.one("SELECT name FROM player LIMIT 1") or {"name": "the new hire"}
        people = self.personas(channel["company_id"])
        prompt = self.prompt_for(persona, channel, player["name"], people)
        loop = asyncio.get_running_loop()
        started = loop.time()
        self.typing(persona, channel["id"], True)
        try:
            reply = await self.runner.reply(persona, prompt)
        except TeammateError as exc:
            self.typing(persona, channel["id"], False)
            self.bus.notice(str(exc), "warn")
            return
        pm.save_session(self.db, persona, reply.session_id)
        text = re.sub(rf"^{re.escape(persona.first_name)}\s*:\s*", "", reply.text.strip())
        if not text or text.strip() == NO_REPLY:
            self.typing(persona, channel["id"], False)
            return
        wait = typing_delay(text) * self.settings.delay_scale - (loop.time() - started)
        if wait > 0:
            await self._sleep(wait)
        self.typing(persona, channel["id"], False)
        self.post(channel["id"], persona.id, text, thread_root_id=message["thread_root_id"])
