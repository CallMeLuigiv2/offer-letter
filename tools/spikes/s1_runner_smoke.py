"""Spike S1: the real runner makes one Haiku call as a persona, then a --resume call that recalls a fact.

Costs well under a cent on the Claude plan. Run from the repo root:
    cd server && uv run python ../tools/spikes/s1_runner_smoke.py
Prints the auth gate, both replies, the session ids and the governor state read from rate_limit_event.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from offerletter.db import Database
from offerletter.events import EventBus
from offerletter.teammates.governor import Governor
from offerletter.teammates.personas import Persona
from offerletter.teammates.runner import ClaudeRunner, GovernedRunner, check_auth

SHEET = """# Kenji Mori
Tech lead on the Serving team. Terse and benchmark-driven: "show me the p99". Fair, decides fast.
Writes chat messages in lowercase, one or two sentences.
"""


async def main() -> None:
    auth = check_auth()
    print(f"auth: ok={auth.ok} loggedIn={auth.logged_in} method={auth.auth_method} {auth.message}")
    if not auth.ok:
        return
    with tempfile.TemporaryDirectory(prefix="s1-") as tmp:
        tmp_dir = Path(tmp)
        sheet = tmp_dir / "kenji.md"
        sheet.write_text(SHEET, encoding="utf-8")
        persona = Persona(id="kilnworks.kenji", company_id="kilnworks", name="Kenji Mori", role="Tech lead",
                          model="haiku", sheet_path=sheet)
        governor = Governor(Database(":memory:"), EventBus())
        runner = GovernedRunner(ClaudeRunner(tmp_dir / "teammates"), governor)

        first = await runner.reply(
            persona, "Luigi, the new hire, wrote in #serving: \"fyi the Friday demo is codenamed otter-7, "
                     "put it in your notes\". Write Kenji's chat reply.", timeout_s=120)
        print(f"call 1 (haiku): {first.text!r}\n  session={first.session_id} cost=${first.cost_usd}")
        second = await runner.reply(
            persona, "Luigi wrote: \"sorry, what was the demo codename again?\". Write Kenji's one-sentence reply.",
            resume=first.session_id, timeout_s=120)
        print(f"call 2 (--resume): {second.text!r}\n  session={second.session_id} cost=${second.cost_usd}")
        print("recalled fact:", "otter-7" in second.text)
        row = governor.row()
        print(f"governor: mode={row['mode']} five_hour={row['five_hour_util']} seven_day={row['seven_day_util']} "
              f"resets_at={row['resets_at']}")
        print("last rate_limit_info:", second.rate_limit)


if __name__ == "__main__":
    asyncio.run(main())
