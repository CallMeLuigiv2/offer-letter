# Offer Letter

A desktop app that hires you into a fictional software company. AI teammates
write code, review yours, push back, and expect you to explain your reasoning.
You own code only after you prove you understand it.

Design doc: `DESIGN.html` (also at https://claude.ai/artifact/PR5LQiyiaMQGXWExFMASb7).

## Start it

Double-click **`Start Offer Letter.cmd`**, or from PowerShell:

```powershell
.\start.ps1           # real teammates on your Claude plan
.\start.ps1 -Fake     # canned teammates, no plan usage (for a look around)
```

It builds the web app, starts the server and opens http://127.0.0.1:8765.
Your data lives in `C:\Users\Owner\OfferLetter` (your clone of the company
repo ends up in `C:\Users\Owner\OfferLetter\work\kilnworks\kiln-bench`; open
that in your editor when a ticket asks you to change code).

Teammates use your Claude plan through the `claude` CLI (never API billing).
When the 5-hour window passes 70% they get thriftier; past 90% the team is
"out to lunch" until the window resets, and you can still read code, take
quizzes and run tests.

## What's in v0.1

- Careers page with 15 researched companies (Kilnworks is open for hiring).
- Offer letter, ID badge, laptop setup, a daily badge-in with a standup.
- A Slack-style workspace with six teammates, DMs, a task board and a pixel office.
- Your first ticket, **KLN-01**: review Theo's PR (6 planted issues), quiz,
  explain it to Theo, make Amara's change on your own branch (hidden tests
  decide), then own it on your GitHub (only when you click).

## Two things for you to do (about 30 minutes)

1. **Voice blind test (D5):** `uv run python tools/voice/serve.py`, then open
   http://127.0.0.1:8770. About 15 minutes of "same person or different?"
   and ratings. It decides each teammate's voice.
2. **Decision D6:** should your first job be limited to growth-stage
   companies? (Research says juniors do best there.)

Push-to-talk (S6) gets tested together when voice calls land in v0.2.

## For developers (and agents)

Rules: `CLAUDE.md`. Contract: `docs/ARCHITECTURE.md`. Where things stand:
`docs/PROGRESS.md`. Decisions: `docs/DECISIONS.md`. Tests:
`cd server; uv run pytest` · `cd web; pnpm test; pnpm e2e; pnpm e2e:real` ·
`python tools/verify_kit.py kilnworks`.
