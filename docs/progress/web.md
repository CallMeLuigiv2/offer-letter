# Web agent progress

Vite + React 18 + TypeScript + pnpm in `web/`. Mock-first (`VITE_MOCK=1`); the real client (`src/api/client.ts`) matches ARCHITECTURE §4 line for line and is covered by `client.test.ts`.

Pinned: vite 6.4.3, react 18.3.1, react-router-dom 6.30.6, zustand 5.0.15, motion 12.43.0, react-markdown 10.1.0, remark-gfm 4.0.1, vitest 3.2.7, TypeScript 5.9.3, Playwright 1.63.0 (all at least two weeks old).

## Decisions
- Diff view is a custom renderer over `hunks_text` (src/review/DiffView.tsx, src/lib/diff.ts), not @git-diff-view/react: click-to-comment, old/new-side anchoring, threads and split/unified needed full control.
- Mock is dynamically imported only when `VITE_MOCK=1`.
- Debriefs: the API has no debrief list, so each stage's `debrief_md` is saved to localStorage by ticket and merged with any `debrief_md` found in `stage_results[].detail_json`. See "Asks for the server".

## How to run
- `pnpm dev` (5173, proxies /api and /ws to 127.0.0.1:8765); `pnpm dev:mock` for the mock (`VITE_MOCK=1`; add `?governor=lunch` or `window.__mock.setGovernor('lunch')` to force the banner).
- `pnpm test` (vitest), `pnpm e2e` (Playwright headless chromium, mock mode, own server on 5174), `pnpm typecheck`, `pnpm build`.

## Status (all in mock mode)
| Screen | Status | Evidence |
|---|---|---|
| Careers (filters, kit_ready only joinable) | done | e2e, 01-careers.png |
| Apply + placement note | done | 02-apply.png |
| Offer letter (unfold animation, addressed to name) | done | 03-offer-letter.png |
| Profile + pixel avatar | done | 04-profile.png |
| ID badge flip | done | 05-badge.png |
| Laptop setup + Check | done | 06/07 |
| Workspace shell, channels, DMs, presence, typing, @mention | done | 08/09 |
| Governor banner (lunch/thrifty) | done | 27, unit test |
| Task board, ticket page, stepper with locks | done | 10/11 |
| PR review (tree, split/unified, comments, severity, submit modal, results linked to lines) | done | 12-16 |
| Quiz (mcq, predict_output, which_test) | done | 17-19 |
| Explain (visual-novel, typewriter, rubric) | done | 20/21 |
| Change request + Check my branch | done | 22/23 |
| Own (confirm dialog, never automatic) | done | 24/25 |
| Debriefs | done | 26 |
| Office placeholder (lazy route) | done | 28 |

Screenshots: `web/test-results/screens/*.png`.

## Tests
See the bottom of this file for the latest run.

## Asks for the server (assumptions the web app makes; please confirm or tell me)
1. Quiz answers are sent as the **option string** for mcq/which_test and the typed text for predict_output: `{answers: {qid: value}}`. If you want option indexes or letters, say so.
2. `setup` from accept: accepted as `{title?, steps:[{id,label,path?,command?,detail?}]}` or a bare array. The web finds the clone path from the step with `id: "clone"` (else the first step with a `path`); it uses that for the Change page. Setup is cached in localStorage because `GET /state` does not return it.
3. `POST /tickets/{id}/explain/messages` returns `{turn}`. The web treats it as the **teammate's reply** (author != 'player'). If it returns the player's stored turn instead, the web polls `GET /tickets/{id}/explain` every 1.5 s for up to 60 s. A `teammate.typing` event is not used for explain; the web shows its own "thinking" state.
4. Optional `expression` on explain turns (`neutral`, `thinking`, ...) picks `/portraits/<company>/<persona>/<expression>.png`; falls back to `neutral.png`, then a placeholder bust.
5. Debriefs: suggest `GET /tickets/{id}/debriefs` or `debrief_md` inside `stage_results[].detail_json`. The web reads the latter if present.
6. Message `author` is `player`, a persona id (`kilnworks.dana`), or `system`. Channel ids are used as-is in routes (`/channels/<id>`). DM partner is found from `members_json` (persona ids) or a channel id ending `.<slug>`.
7. `governor.resets_at` may be an ISO string or epoch seconds.
8. Portraits are requested from `/portraits/...` on the same origin; the server (or Vite `public/`) must serve them.
9. The pixel agent replaces `web/src/office/OfficeView.tsx` (default export, props `{personas, onPersonaClick?}`); the route `/office` loads it lazily.

## Latest run (2026-10-19)
- `pnpm typecheck`: clean. `pnpm build`: ok (one 517 kB chunk warning, fine for a local app).
- `pnpm test`: 6 files, 39 tests pass (API client vs §4, stage locking, comment anchoring and split rows, governor banner, @mention logic, mock server stage flow).
- `pnpm e2e`: 1 spec passes headless in mock mode (careers filters, apply, letter, profile, badge, setup check fail then pass, chat + @mention autocomplete, board, locked stepper, review with 4 comments + split/unified + submit modal + results linked to lines, quiz fail then pass, explain with rubric, change fail then pass, own confirm cancel then push, debriefs, governor lunch banner, light theme, 1000px, office placeholder). 30 screenshots in `web/test-results/screens/`.
- Not done / not tested: the real server (not landed yet); portraits (placeholders shown); no syntax highlighting in the diff.
