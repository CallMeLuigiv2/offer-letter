"""What a teammate actually gets to see: author notes stay hidden, the explain opening is in the chat."""

from __future__ import annotations

from pathlib import Path

from offerletter import explain
from offerletter.teammates.personas import Persona


def test_author_notes_never_reach_the_persona(tmp_path: Path) -> None:
    sheet = tmp_path / "kenji.md"
    sheet.write_text(
        "# Kenji\n"
        "## What you believe (sincerely)\n"
        "- Closed-loop load is fine for capacity planning.\n"
        "  <!-- author: this is the planted wrong belief; concede only to a measurement. -->\n"
        "<!--\nmulti-line author note:\nthe correction lives here\n-->\n"
        "## Style\nTerse.\n",
        encoding="utf-8",
    )
    p = Persona(id="kilnworks.kenji", company_id="kilnworks", name="Kenji Mori", role="Tech lead", sheet_path=sheet)
    prompt = p.system_prompt()
    assert "Closed-loop load is fine for capacity planning." in prompt
    assert "Terse." in prompt
    assert "author" not in prompt and "<!--" not in prompt and "correction lives here" not in prompt


def test_explain_chat_includes_the_opening_line_before_his_turns() -> None:
    p = Persona(id="kilnworks.theo", company_id="kilnworks", name="Theo Lindqvist", role="Engineer")
    turns = [{"author": "player", "body_md": "The p99 hides stalls because the loop waits."}]
    prompt = explain.chat_prompt(p, "Luigi", None, [{"point": "closed loop hides stalls"}], turns,
                                 opening_md="Walk me through what's wrong with my PR?")
    chat = prompt.split("The chat so far:\n", 1)[1]
    assert chat.index("Theo: Walk me through") < chat.index("Luigi: The p99 hides stalls")
