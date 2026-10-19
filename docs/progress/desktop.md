# desktop agent progress

2026-10-19 spike S5 done. `desktop/` holds a Tauri 2 shell (pinned, 2-week-old crates): uv child server in a kill-on-close Job Object, tray with governor tooltip, Ctrl+Alt+Space logging to `.data/ptt.log`, always-on-top frameless call window (local placeholder), notification plugin registered, pixel-badge icon. Cold start to server page loaded 2.0 s; kill leaves no python. Details, numbers and caveats: `docs/spikes/S5.md`.

Open items for others: server needs an SPA fallback and the `/office` static mount collides with the `/office` route (S5.md finding 1). Not verified without real input: tray clicks, call window, hotkey (S6, Luigi by hand), toast (needs installed build).
