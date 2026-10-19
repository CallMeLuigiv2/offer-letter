# 05 — Tech feasibility: does the decided architecture work, and which parts to pick

Status: COMPLETE (all sections written). Date: 2026-10-19. Author: tech-feasibility
research agent. "From memory" / "unverified" marks are kept inline and collected in §11.

Architecture under test (decided, not re-litigated): React web UI + local Python server
(FastAPI + websockets + SQLite), browser first, Tauri wrap when voice lands; pixel-art office
home screen + anime VN portraits; teammates on Claude Code (subscription, never API billing);
voice = Silero VAD → faster-whisper large-v3-turbo → Kokoro; in-harness git + review UI;
whiteboard; Docker sandboxes; UI animation.

## 0. Top findings

1. **Teammates: use the `claude` CLI, not the Agent SDK, and never `--bare`.** Anthropic's
   docs explicitly allow "an end user … signing in to the unmodified Claude Code binary with
   their own Claude subscription"; the Agent SDK page says it is governed by the Commercial
   Terms and tells developers to use API keys. grokbot's `claude -p` stream-json runner +
   its plan guard is the right base. `--bare` "will become the default for `-p` in a future
   release" and in bare mode "Claude Code never reads OAuth credentials", which would
   silently break every teammate. Guard against it. `/usage` in `-p` returns the 5-hour and
   weekly meters with `resets_at`, enough for a usage governor. Luigi is on Max
   (`subscriptionType=max`).
2. **Machine probes: GPU yes, KVM no, cgroup v2 no.** `nvidia-smi` and PyTorch CUDA work in
   WSL (RTX 4070, driver 610.88, sm_89). `/dev/kvm` exists but dmesg says "kvm: no hardware
   support / has_svm: svm not available" → **BLJ-03 (Firecracker) blocked**. cgroups are
   hybrid with zero v2 controllers → **BLJ-02 blocked** until WSL is updated or reconfigured
   (his call). NVML has no per-process data in WSL → **CPL-05 needs simulated telemetry**.
   An `LD_PRELOAD` shim is plausible (WSL `libcuda.so.1` is an ordinary ELF exporting
   `cuGetProcAddress`), but a stray Ubuntu `libnvidia-compute-580` libcuda is installed
   against NVIDIA's guidance and could be loaded by mistake.
3. **Keep audio in Python.** Reusing grokbot's capture → VAD → whisper → Kokoro avoids WebView2
   mic permissions and works the same in browser v0.1 and Tauri. Tauri's global-shortcut
   plugin delivers `Pressed`/`Released` (hold-to-talk works). Windows notifications "Only
   work for installed apps" and have no action buttons. Launch the server with `uv run` as
   the sidecar; skip PyInstaller/Nuitka.
4. **Licences steer three picks.** LimeZu: "CAN'T resell or distribute the asset" → fine
   locally, never in a public repo (gitignore + import script; Kenney CC0 for public). tldraw
   "will work in production only when provided with a valid and active license key" →
   **Excalidraw** (MIT) + Mermaid/skeleton JSON from the LLM. GSAP is free but proprietary
   with a Webflow-competition clause → **Motion**. Illustrious-family checkpoints use the Fair
   AI Public License (open derivatives) → prefer **Animagine XL 4.0** (OpenRAIL++-M).
5. **Faces and voices are feasible with sprite swaps, not rigs.** Use face-only inpainting
   from one approved bust per character (consistent outfit/hair), 3 mouth × 2 eye overlays,
   and amplitude lip-flap in v0.1. The PyTorch `kokoro` package exposes per-phoneme
   `pred_dur` for visemes later. Kokoro has 28 English voices but only ~16 decent ones
   (11 F / 5 M), so male teammates need blended voices (averaging is built in). Spike S4
   checks whether the blends sound distinct.

## 1. Tauri 2 shell

**Recommendation: Tauri 2, with audio capture and playback kept in Python (reuse grokbot),
and the Python server launched as a sidecar *launcher* that runs `uv run` against a locked
project, not a frozen PyInstaller/Nuitka binary.** The machine already has everything Tauri
needs on Windows: Rust 1.92 (MSVC toolchain), Visual Studio 2022/18, WebView2 runtime
155.0.4283.62, Node 22 (§9.1). Tauri itself: GitHub's licence API reports Apache-2.0
for [tauri-apps/tauri](https://api.github.com/repos/tauri-apps/tauri/license); the repo is
dual MIT/Apache-2.0 (MIT half from memory).

### 1.1 Python server as a sidecar

- Mechanism ([Tauri sidecar docs](https://v2.tauri.app/develop/sidecar/)): list the binary
  in `bundle.externalBin`; "a binary with the same name and a `-$TARGET_TRIPLE` suffix must
  exist" (here `-x86_64-pc-windows-msvc.exe`); spawn with `app.shell().sidecar("name")`
  (Rust) or `Command.sidecar(...)` (JS); grant `shell:allow-spawn` with `"sidecar": true`.
  The docs name "Python CLI applications or API servers bundled using `pyinstaller`" as the
  common case. The docs say nothing about killing the sidecar on exit.
- Packaging options:

| Option | Fit for Offer Letter | Licence |
|---|---|---|
| **uv-run launcher** (tiny Rust or `.cmd` sidecar → `uv run --frozen --project <dir> offer-letter-server`) | **Best.** Personal app on one machine; the env (faster-whisper + CUDA wheels + kokoro + FastAPI) is multi-GB and changes often. No freeze step, no antivirus false positives, same env as `uv run pytest`. | uv: MIT/Apache-2.0 |
| PyInstaller `--onedir` | Use only if Offer Letter is ever shipped to others. Avoid `--onefile`: it unpacks to a temp dir on every start (slow with CUDA libs) and runs as a bootloader parent + Python child, so killing the sidecar can orphan the child. | GPL-2.0 with exception: "The executable bundles generated by PyInstaller from your source code can be shipped with whatever license you want" ([licence page](https://pyinstaller.org/en/stable/license.html)) |
| Nuitka | Compiles to C; slow builds, fragile with torch/onnxruntime/ctranslate2 native libs. No benefit here. | **AGPL-3.0** — [LICENSE.txt](https://github.com/Nuitka/Nuitka/blob/develop/LICENSE.txt) is the plain "GNU AFFERO GENERAL PUBLIC LICENSE Version 3" text, with no exception for compiled output in that file (Nuitka's own statement on output licensing not found → **unverified**). Another reason to skip it |
| Bundled `python-build-standalone` + uv | The "ship it" variant of option 1 (uv itself uses these builds). Revisit at distribution time. | not checked |

- **Lifecycle (must do on Windows):** put the server in a Windows Job Object with
  `KILL_ON_JOB_CLOSE`, or have the server exit when its stdin closes / a parent-PID check
  fails, so a crashed Tauri shell never leaves a GPU-holding Python process behind. Port
  handshake: the server binds `127.0.0.1:0`, prints `PORT=<n>` on stdout, Tauri reads it and
  injects it into the webview. Same server runs unchanged in browser mode for v0.1.

### 1.2 Push-to-talk while another app is focused

- [`tauri-plugin-global-shortcut`](https://v2.tauri.app/plugin/global-shortcut/): the Rust
  handler receives `ShortcutState::Pressed` and `ShortcutState::Released` (the docs'
  example prints "Ctrl-N Pressed!" / "Ctrl-N Released!"), which is exactly hold-to-talk.
  Needs Rust ≥ 1.90 (have 1.92). Permissions `global-shortcut:allow-register` etc.; "No
  features are enabled by default."
- Not documented and **unverified**: key-repeat behaviour while held, whether the
  focused app (VS Code, a game) still sees the key, modifier-only shortcuts (hold Right
  Ctrl). Windows `RegisterHotKey`, which hotkey libraries usually wrap, does not support
  modifier-only hotkeys and swallows the combo from the focused app. Pick a combo nobody
  else uses (e.g. `Ctrl+Alt+Space`, or F13–F24 if his keyboard/macro software can send
  one). Fallback: a passive low-level keyboard hook in Python (`pynput`) — reads keys, never
  synthesises them.
- **Testing rule:** Luigi presses the keys himself. Do not synthesise OS input to test this
  (he may be screen-sharing; see memory "No Real-Desktop Driving").

### 1.3 Notifications, tray, mini call window

- Notifications: [`tauri-plugin-notification`](https://v2.tauri.app/plugin/notification/)
  on Windows: "Only works for installed apps. Shows powershell name & icon in development."
  "The Actions API is only available on mobile platforms" → **no Accept/Decline buttons on
  Windows toasts.** A teammate "calling" him = toast + tray flash + the mini window, with
  the buttons inside the mini window. Spike S5 must run from an installed MSI/NSIS build.
- Tray: Tauri 2 core `TrayIconBuilder` (`tray-icon` feature) — standard, low risk.
- Always-on-top mini call window: a second `WebviewWindow` with `alwaysOnTop: true`,
  `decorations: false`, custom drag region (`data-tauri-drag-region` "will only work on the
  element to which it is directly applied", [window customization](https://v2.tauri.app/learn/window-customization/)).
  The same React bundle can render a `/call` route in that window.

### 1.4 Microphone: WebView2 `getUserMedia` vs. Python capture

**Capture and play audio in Python.** Reasons:
1. grokbot already has the tuned pipeline (Silero VAD, barge-in, echo heuristics,
   faster-whisper on the 4070, Kokoro, device selection by name) in Python.
2. It works identically in browser mode (v0.1) and Tauri mode; no permission UX at all
   beyond Windows' "let desktop apps access your microphone".
3. In WebView2 the page origin is Tauri's custom protocol; `getUserMedia` raises WebView2's
   permission prompt, and wry/Tauri do not expose a documented per-app permission handler
   to auto-grant it. Whether the grant persists across launches is **unverified**. Avoid
   the question entirely.
- What goes to the UI: transcript events, "speaking/listening" state, and for lip-flap
  either a 60 Hz RMS envelope or a viseme timeline, each stamped with the playback start
  time (§3.4). Optional later: stream TTS PCM to the webview and play through WebAudio, then
  drive the mouth from an `AnalyserNode` for perfect sync.

### 1.5 WebGL in WebView2

WebView2 is Chromium (Edge) — runtime 155 here — so WebGL2 and the GPU process behave like
desktop Chrome/Edge; Phaser/Pixi at 1080p with a few hundred sprites is far below what it
can do. Risk is small; spike S5 measures FPS in the Tauri window vs. Chrome with the same
map. One known foot-gun: hardware acceleration can be disabled by enterprise policy or
driver blocklists (check `edge://gpu`-equivalent via `chrome://gpu` in the browser build).

### 1.6 Electron, briefly

Electron would also work: Chromium bundled (~100+ MB installer vs. a few MB for Tauri),
higher idle RAM, Node main process (no Rust). Its `session.setPermissionRequestHandler`
makes mic permissions trivial, and `globalShortcut` has the same no-key-up limitation as
`RegisterHotKey` (**unverified** for current Electron). Since audio stays in Python and Rust
is already installed, Tauri's advantages (size, RAM, one less JS runtime next to the
whisper/kokoro process) win. Decision stays as made.

## 2. Pixel office

**Recommendation: Phaser 4 (current stable 4.2.1) inside React via the official
`template-react-ts` EventBus pattern; maps authored in Tiled and loaded as Tiled JSON;
grid A* (easystar.js) on a collision layer for teammate walking. LimeZu Modern Interiors +
Modern Office for Luigi's local build, kept out of any public repo; Kenney CC0 packs as the
public/fallback skin.**

### 2.1 Engine choice

| | Phaser 4 | Phaser 3 | PixiJS v8 |
|---|---|---|---|
| Status | **v4.0.0 stable 2026-04-10; v4.2.1 2026-07-09** ([releases](https://api.github.com/repos/phaserjs/phaser/releases)) | Maintenance; the docs/examples corpus is still the biggest | v8.22.0, 2026-10-01 ([releases](https://api.github.com/repos/pixijs/pixijs/releases)) |
| What it is | Game framework: scenes, cameras, input, tweens, arcade physics, **Tiled JSON loader**, tilemap collision | Same | Renderer only; tilemaps (`@pixi/tilemap`), Tiled loading, cameras, input maps are add-ons you assemble |
| Renderer | "a ground-up rebuild of the WebGL renderer"; v3 pipelines → "node-based renderer"; FX+Masks → one "Filter system"; `TilemapGPULayer` renders "an entire tilemap layer as a single quad" ([v4.0.0 notes](https://github.com/phaserjs/phaser/releases/tag/v4.0.0)) | WebGL1/2 + Canvas | WebGL / WebGPU |
| React | Official [`template-react-ts`](https://github.com/phaserjs/template-react-ts): Phaser 4 + React 19 + Vite 6, EventBus + `PhaserGame` `forwardRef` component, MIT | Same pattern (older template) | `@pixi/react` |
| Licence | MIT | MIT | MIT |

Why Phaser 4: the office is a small top-down RPG (walk, collide, click a teammate, walk to
a meeting room). Phaser gives all of that plus Tiled loading out of the box; Pixi would mean
rebuilding half a game framework. Phaser 4 over 3: it is the stable line now, the official
React template targets it, and tilemaps got a GPU fast path. Risk: fewer v4-specific
community answers; most Phaser 3 tilemap/arcade code ports with small changes (the
v3→v4 migration guide is linked from the release; breaking changes are in rendering
pipelines/FX, which the office does not need). **React owns all UI (chat, PR review,
panels); Phaser owns only the canvas.** Talk across the EventBus: `teammate-clicked`,
`walk-to(room)`, `presence-changed`.

### 2.2 Tiled workflow

1. Author in [Tiled](https://www.mapeditor.org/). Its
   [COPYING](https://github.com/mapeditor/tiled/blob/master/COPYING) lists the editor
   (`src/tiled`) and plugins as "GPL" (version not stated there) and `libtiled`,
   `tmxviewer`, `tmxrasterizer` as "BSD 2-clause license". COPYING says nothing about maps;
   the usual reading is that maps you author are yours (**interpretation**). The editor
   is only a tool here, nothing from it ships. Tile size 16×16 to match
   LimeZu Modern Office; render with `pixelArt: true` and integer zoom ×3.
2. Layers: `floor`, `walls` (custom bool property `collides`), `furniture-below`,
   `furniture-above` (depth-sorted over characters), and an object layer `spots` with
   named points: `desk:<persona>`, `seat:meeting-1..n`, `whiteboard`, `coffee`, `door`.
3. Embed tilesets in the map (or ship `.tsj` next to it) and export JSON; load with
   `this.load.tilemapTiledJSON` and `map.addTilesetImage`.
4. Characters: LimeZu's Character Generator (included with the paid Modern Interiors)
   exports 4-direction walk/idle sheets; one per persona, matching the VN portrait's hair
   and clothes colours.

### 2.3 Pathfinding

Office maps are tiny (≈ 60×40 tiles). Grid A* is enough: build a walkability grid from
the `walls`/`collides` tiles, run A* (easystar.js, MIT per [GitHub](https://api.github.com/repos/prettymuchbryce/easystarjs/license),
async/iterative; or pathfinding.js)
from the persona's tile to a `spots` target, and tween along the path. Teammates walking
to the meeting room when a call starts, or to his desk when they "drop by" with a PR,
is cheap ambient life. Spike S3 checks it.

### 2.4 LimeZu licence (quoted)

- [Modern Interiors](https://limezu.itch.io/moderninteriors) — "Complete version LICENSE
  (paying at least 1.50$)": may edit and use in commercial or non-commercial projects;
  may **not** resell or distribute the asset to others, nor edit and resell it; "Credits
  required" (link to limezu.itch.io). Tile sizes 16/32/48. "The official Character
  generator tool is included with the complete version." A user comment says the minimum
  is now $3 (unverified). No AI clause; the page is tagged "No generative AI was used".
- [Modern Office](https://limezu.itch.io/modernoffice): "You **CAN** use the asset in any
  commercial or non commercial project", "You **CAN'T** resell or distribute the asset to
  others", "You **CAN'T** edit and resell the asset to others", "Credits required". $2.50
  (50 % off $5). Characters come from Modern Interiors, not this pack.

What that means for Offer Letter (interpretation):
- **Personal use on his machine:** allowed (it is "use in a project").
- **Private git repo:** fine as storage for his own project (no one else receives it).
  Collaborators on the private repo would be receiving the files → treat as distribution;
  keep it to him.
- **Public git repo:** **no.** Raw PNGs in a public repo are distributing the asset. Put
  them under `assets/vendor/limezu/` in `.gitignore`, with an `import-assets` script that
  copies from his itch download and checks file hashes; the public repo ships Kenney art
  plus the Tiled maps (maps reference tileset filenames, which is fine).
- **A public web demo / released build:** using assets inside a shipped game is the normal
  allowed case, but a web app serves the PNGs as files anyone can save. Low risk for a
  game-like app, but ask LimeZu before publishing a hosted version (**unverified**).
- Credit line "Art: LimeZu (limezu.itch.io)" on the About screen in every build.

### 2.5 CC0 fallback

[Kenney](https://kenney.nl/support): "all game assets on the [asset pages] are public
domain licensed (CC0)", "You're free to use them, even in commercial projects",
"Attribution is not required"; do not use the Kenney logo. Kenney's top-down packs
(e.g. Roguelike Indoors, RPG Urban) are a different, chunkier style than LimeZu; fine for
the public repo and for CI screenshots. Exact pack names/tile sizes **not re-checked**.

## 3. Anime portraits

**Recommendation: plain layered sprite swaps (Ren'Py-style), generated locally in ComfyUI
on the 4070 with Animagine XL 4.0 (cleanest licence) or an Illustrious-based checkpoint
(better quality, stricter licence on derivatives). Get consistency by *inpainting only the
face* of one approved base bust per character, not by regenerating whole images. Lip-flap
from audio amplitude in v0.1, phoneme visemes from Kokoro durations in v0.2. No Live2D.**

### 3.1 Generation on a 12 GB RTX 4070

- SDXL-class inference at 1024² in fp16 fits comfortably in ~10.9 GB of free VRAM
  (§9.4) with ComfyUI. The text encoders + UNet + VAE need roughly 7–9 GB; ComfyUI offloads
  as needed (**figures from general experience, not measured here** → spike S7 measures).
- Models and licences:

| Model | Base | Licence (quoted) | Notes |
|---|---|---|---|
| [Animagine XL 4.0](https://huggingface.co/cagliostrolab/animagine-xl-4.0) | SDXL 1.0 | **CreativeML Open RAIL++-M**, "taken unmodified from Stability AI's SDXL license"; commercial use, modification, distribution permitted; use-based restrictions (no harmful/illegal content) | Danbooru-tag prompts ("1girl/1boy, … , masterpiece, high score, great score, absurdres"); 1024×1024 or 896×1152 portrait; Euler a, CFG ≈ 5, 28 steps |
| [Illustrious XL (early release v0)](https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0) | Kohaku XL beta5 (SDXL) | **fair-ai-public-license-1.0-sd**. Card: derivatives must "Openly share details of any derived models"; monetizing a closed-source fine-tune/merge is prohibited; authors "do not restrict any upload or spread of the generation results" | Most community anime checkpoints (incl. NoobAI) descend from it; a private character LoRA kept on his disk is not distributed, so open-sourcing duties should not trigger (**interpretation**) |
| Pony Diffusion V6 XL | SDXL | Modified Fair AI Public License with extra Pony terms — **not re-fetched** (Civitai page) | Uses `score_9…` tags; more western/furry bias; no reason to pick it here |

ComfyUI itself is GPL-3.0 ([GitHub licence API](https://api.github.com/repos/comfyanonymous/ComfyUI/license)),
which is fine: it is a local tool, not shipped.

### 3.2 A consistent cast with 5–8 expressions each

The realistic pipeline (about 1–2 h per character once the workflow exists):
1. **Character sheet prompt** from the persona card (age band, hair, eyes, outfit, one
   signature item). Generate ~20 neutral half-body busts at 896×1152, same seed family;
   Luigi picks one. That image is the canonical character.
2. **Expressions by face inpainting**: mask only the face (eyes, brows, mouth) of the
   canonical bust and inpaint at denoise ≈ 0.4–0.6 with expression tags (`smile`,
   `frown`, `surprised`, `thinking, hand on chin` needs a larger mask, `embarrassed,
   blush`, `serious`, `laughing`). Hair, outfit and lighting stay pixel-identical because
   they are outside the mask. This beats IP-Adapter/reference-only for consistency.
3. **Mouth and blink frames**: for each expression, inpaint just the mouth (closed /
   half / open) and the eyes (open / closed). Export as separate transparent overlays
   aligned to the bust so the runtime composites `base + eyes[i] + mouth[j]`.
4. Optional: **character LoRA** when a character needs new poses or outfits (e.g. a
   standing sprite for a design review). kohya sd-scripts: "The LoRA training can be done
   with 8GB GPU memory (10GB recommended)" with "Train U-Net only", gradient checkpointing,
   `--cache_text_encoder_outputs` + latent caching, 8-bit optimizer or Adafactor
   ([train_SDXL-en.md](https://github.com/kohya-ss/sd-scripts/blob/main/docs/train_SDXL-en.md)).
   Train on the 15–30 approved images from steps 1–3. Fits the 4070.
5. IP-Adapter (SDXL Plus / anime "reference" nodes) is useful for new outfits but drifts
   on anime faces; treat as optional.

Quality gate: background removal (rembg or the model's own `simple background, white
background` + a matting node), 2× upscale for crisp 1080p display, and a human pick for
every final frame. **Budget ~10 characters per company × 7 expressions ×
(3 mouth + 2 eye) overlays ≈ 350 small images per company**, which is why
face-inpainting (deterministic, batchable in ComfyUI via its API) matters.

### 3.3 Rigged vs. sprite swaps

| | Live2D Cubism | Inochi2D | Layered sprite swaps |
|---|---|---|---|
| Licence | SDK: "Individuals and Small-Scale Enterprises are exempted from the license and payment (except Expandable Application)"; "License only required upon releasing your content" ([Live2D SDK licence](https://www.live2d.com/en/sdk/license/)). Core is proprietary (Live2D Proprietary Software License); framework is under the Live2D Open Software License. Editor FREE vs PRO differ in features | BSD-2-Clause ([GitHub licence API](https://api.github.com/repos/Inochi2D/inochi2d/license)) | n/a (your images) |
| Authoring cost | Each character needs a PSD split into dozens of parts and a hand rig in Cubism Editor: days per character for a beginner. AI images are flat, so parts must be painted/separated by hand | Same rigging work in Inochi Creator; web runtime immature (**unverified**) | Inpainting workflow above; batchable |
| Look | Breathing, head turns — best | Similar | Static bust + blink + mouth + expression swap; with a small CSS/Motion bob and cross-fade it reads as a VN |

Sprite swaps are what most indie VNs ship; Live2D is a v2 luxury for maybe one hero
character (the manager) if Luigi ever wants to learn rigging.

### 3.4 Lip-flap

- **v0.1, amplitude**: Python computes the RMS envelope of each TTS chunk at 60 Hz and
  sends it with the chunk's playback start time; the UI picks `mouth[closed|half|open]` by
  thresholds with ~40 ms hysteresis, plus random blinks every 2–6 s. This is the classic VN
  approach, needs no phonemes, and survives any TTS.
- **v0.2, visemes**: the PyTorch `kokoro` pipeline exposes `Result.phonemes` and
  `Result.pred_dur` (per-phoneme durations) and word `start_ts`/`end_ts` (§5.3). Map
  phonemes to Rhubarb's mouth set — A closed (P/B/M), B slightly open (most consonants,
  "EE"), C open ("EH", "AE"), D wide ("AA"), E rounded ("AO", "ER"), F puckered ("UW",
  "OW", "W"), optional G (F/V), H (long L), X idle
  ([Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync)) — and draw 6
  mouth overlays per expression instead of 3. No speech recognition needed because the
  TTS already knows its phonemes.
- Rhubarb itself (audio → mouth cues, WAV/OGG, better with dialog text) is the fallback
  for pre-recorded lines. "Rhubarb Lip Sync is released under the MIT license"
  ([LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md));
  bundled parts are BSD (PocketSphinx/sphinxbase, Flite, libogg/vorbis, WebRTC), Boost,
  WTFPL and Unicode-licensed data — all permissive. It is
  too slow for live replies (**unverified**), so use it only offline.

## 4. Teammates on Claude Code

**Recommendation: drive the unmodified `claude` CLI as a subprocess (`claude -p
--input-format stream-json --output-format stream-json --verbose`), exactly as grokbot
already does, signed in with Luigi's own claude.ai login. Do not build on the Python Agent
SDK for v0.1.** Keep a thin `TeammateRunner` interface so the SDK can be swapped in later
if Anthropic's wording changes.

### 4.1 What the official docs say (quoted)

- Claude Code's [Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
  page, "Authentication and credential use":
  - "**OAuth authentication** is intended exclusively for purchasers of Claude Free, Pro,
    Max, Team, and Enterprise subscription plans and is designed to support ordinary use of
    Claude Code and other native Anthropic applications."
  - "**Developers** building products or services that interact with Claude's
    capabilities, including those using the Agent SDK, should use API key authentication
    … Anthropic does not permit third-party developers to offer Claude.ai login into their
    own applications, or to route requests through Free, Pro, or Max plan credentials on
    behalf of their users. Moreover, developers may not collect, store, or intermediate
    Claude.ai credentials or session tokens."
  - "Nor does it prevent an end user from signing in to the unmodified Claude Code binary
    with their own Claude subscription…"
  - Usage policy: "Advertised usage limits for Pro and Max plans assume ordinary,
    individual usage of Claude Code and the Agent SDK."
  - "Anthropic reserves the right to take measures to enforce these restrictions and may
    do so without prior notice."
- [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview): "Unless
  previously approved, Anthropic does not allow third party developers to offer claude.ai
  login or rate limits for their products, including agents built on the Claude Agent
  SDK." And: "Use of the Claude Agent SDK is governed by Anthropic's Commercial Terms of
  Service." The SDK is "A library that runs the Claude Code binary."
- [Help center, logging in](https://support.claude.com/en/articles/13189465-logging-in-to-your-claude-account):
  "Subscription plans can only be used by subscribers"; usage "is designed to support
  ordinary use of native Anthropic applications"; Anthropic "may at its discretion allow
  paid subscribers who have enabled usage credits to use certain third-party tools" and
  "reserves the right to draw use of such third-party tools from usage credits rather than
  subscription limits"; tools that "misrepresent their identity to Anthropic's servers" or
  "route third-party traffic against subscription limits" are prohibited.
- [Usage with Pro/Max](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan):
  "Both Pro and Max plans have a five-hour session limit and a weekly limit." "These limits
  are shared across Claude and Claude Code." Max plans also have "a separate weekly limit
  for Fable."

### 4.2 Reading of the terms for Offer Letter (my interpretation, not legal advice)

- **Fits:** one person (Luigi), his own subscription, signing in through Anthropic's own
  `/login` flow, the published `claude` binary unmodified, his own machine, nobody else's
  traffic. This matches the "end user signing in to the unmodified Claude Code binary"
  carve-out and "ordinary, individual usage".
- **Gray:** the Python Agent SDK. It also runs the Claude Code binary and its auth docs list
  "Agent SDK logins" among the paths that honour `forceLoginOrgUUID`
  ([Authentication](https://code.claude.com/docs/en/authentication)), so it technically
  works with a claude.ai login. But the SDK's own page says it is governed by the
  Commercial Terms and tells developers to use API keys. For a personal tool that is never
  distributed this is probably fine, but the CLI route is the one the docs explicitly
  allow, so pick it.
- **Never:** reading or copying `%USERPROFILE%\.claude\.credentials.json`, minting a
  `setup-token` and storing it in the harness, distributing Offer Letter with a shared
  login, or adding other users on Luigi's plan. If Offer Letter is ever shared, each user
  signs in to their own `claude` and the harness only spawns the binary.
- **Hard guard (copy from grokbot `claude.py`):** strip `ANTHROPIC_API_KEY`,
  `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_USE_*` from the child environment; run
  `claude auth status` at startup and refuse unless `authMethod == "claude.ai"`; log
  `apiKeySource` from every `system/init` event.

### 4.3 Mechanics

| Need | How (doc) |
|---|---|
| Per-persona memory | One session per (persona, company). Capture `session_id` from the `result` message, then `--resume <id>`. Sessions live in `~/.claude/projects/<encoded-cwd>/*.jsonl`. Since v2.1.223 resume finds an ID from any directory ([headless](https://code.claude.com/docs/en/headless), [sessions](https://code.claude.com/docs/en/agent-sdk/sessions)). |
| Branch a conversation (e.g. replay a 1:1) | `--fork-session` with `--resume` (SDK: `fork_session=True`). Forks history only, not files. |
| Long-term memory that survives transcript bloat | Do not rely on resume alone. The sessions doc itself suggests: "Capture the results you need … as application state and pass them into a fresh session's prompt." Store a per-persona `memory.md` in SQLite and inject it with `--append-system-prompt-file`. |
| Model per call | `--model haiku|sonnet|opus` (or a full ID) on each `claude -p`. In a live streaming session, `/model sonnet` as a prompt switches model; the SDK has `setModel()`. Suggested split: Haiku for chatter, standups, Slack-style pings and quiz grading; Sonnet for PR authoring and reviews; Opus only for design reviews and the "senior" teammate. |
| Persona voice / role | `--append-system-prompt-file personas/<id>.md` (keeps Claude Code's tools) or `--system-prompt` to replace (drops the git status snapshot). |
| Lock down tools | `--allowedTools`, `--permission-mode dontAsk` for teammates that only talk, `acceptEdits` inside the teammate's own repo worktree; `--permission-prompts none` for unattended runs (v2.1.259+). |
| Structured output (quiz JSON, review comments) | `--output-format json --json-schema '<schema>'` → `structured_output`. |
| Usage meter | `/usage` inside a `-p` session emits a `usage_report` whose `rate_limits.limits[]` rows have `kind` (`session`, `weekly_all`, `weekly_scoped`), `percent` and `resets_at` — only for a claude.ai credential ([TS SDK reference](https://code.claude.com/docs/en/agent-sdk/typescript)). A `setup-token` token lacks the scope, another reason not to use one. |
| Retries | `system/api_retry` events carry `error: "rate_limit"` vs `"overloaded"` (429 vs 529) ([headless](https://code.claude.com/docs/en/headless)). |

**Local check (2026-10-19, read-only):** `claude auth status` → `authMethod=claude.ai`,
`subscriptionType=max`, `ANTHROPIC_API_KEY` not set. `claude --help` (v2.1.303) lists
`--fork-session`, `--no-session-persistence` ("sessions will not be saved to disk and
cannot be resumed (only works with --print)"), `--permission-prompts`,
`--setting-sources <sources>` ("Comma-separated list of setting sources to load (user,
project, local)"), `--json-schema`, `--max-budget-usd`, `--append-system-prompt[-file]`,
`--agents`, `--strict-mcp-config`, `--disable-slash-commands`. Its `--bare` text: "Anthropic
auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are
never read)". So everything in the table above exists in the installed CLI.

**Risk to plan around now — `--bare`.** The headless doc says "`--bare` is the recommended
mode for scripted and SDK calls, and will become the default for `-p` in a future release",
and "In bare mode, Claude Code never reads OAuth credentials". If that default flips, every
teammate call silently stops using the subscription (and fails, since there is no API key).
The harness must: (1) never pass `--bare`; (2) pin a known-good `claude` version in its
doctor check; (3) assert `apiKeySource`/`authMethod` on every `system/init`; (4) watch the
[CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) for the
opt-out flag when the default changes.

### 4.4 Concurrency and keeping inside the 5-hour window

- No documented per-subscription concurrency cap for parallel `claude -p` processes
  (**unverified**). Every process draws on the same 5-hour and weekly meters, shared with
  claude.ai chat. Luigi's own experience (memory: 3 parallel agents hit the 5-hour limit and
  were cut mid-write; now max 2) is the best data point.
- Design rules:
  1. **One "speaking" teammate at a time.** A scheduler queue in the Python server; at most
     2 Claude processes in flight (one foreground conversation + one background job such as
     PR generation).
  2. **Pre-generate offline content in cheap bursts.** Planted-bug PRs, decision notes,
     and onboarding docs are generated once per company (Sonnet), stored in git/SQLite, and
     replayed. Live calls are only for conversation and review.
  3. **Haiku by default**; escalate to Sonnet/Opus by task type.
  4. **Budget governor:** poll `/usage` at most every few minutes; above ~70 % of the
     `session` row, downgrade to Haiku and pause background jobs; above ~90 %, the harness
     tells him "the team is out to lunch until <resets_at>" (diegetic) and switches to
     offline work (reading, quizzes graded by code, benchmarks).
  5. **Keep prompts small:** `--allowedTools` minimal, short persona files, no huge MCP
     tool lists, avoid loading the user's global `~/.claude` skills into teammate sessions
     (use a dedicated `CLAUDE_CONFIG_DIR`? — **careful**: a separate config dir means a
     separate login, i.e. Luigi signs in once more through `/login`; that is allowed,
     tokens are never touched by the harness).
- Note `claude -p` loads hooks/skills/CLAUDE.md from the working directory and `~/.claude`
  unless `--bare` (and `--bare` is ruled out because it drops OAuth). Isolation without
  bare: run teammates with `--setting-sources project` from a harness-owned working
  directory (its own `.claude/`), `--strict-mcp-config` with an explicit MCP list,
  `--disable-slash-commands`, and `--append-system-prompt-file` for the persona. Auto
  memory is keyed by working directory, so a harness cwd gets its own memory folder.
  Whether `--setting-sources project` also stops `~/.claude/CLAUDE.md` (Luigi's mentor
  instructions) from loading is **unverified** — spike S1 checks it by asking the teammate
  to repeat any instructions it sees about "Luigi" or "quiz".

## 5. Voices (Kokoro)

**Recommendation: keep Kokoro-82M. Use the ~16 English voices graded C- or better as the
base cast, and give the rest of the roster blended voices (weighted average of two style
vectors) plus a per-persona speed. Cap the roster at about 12 voiced teammates per company
(that is plenty: manager, tech lead, 2–3 peers, PM, junior, a senior for design reviews)
and reuse voices across companies, never inside one.**

### 5.1 The voice list ([VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md))

- **English total: 28 voices.** American English 20 (11 F, 9 M), British English 8 (4 F,
  4 M). Other languages: Japanese 5, Mandarin 8, Spanish 3, French 1, Hindi 4, Italian 2,
  Brazilian Portuguese 3.
- Quality grades are uneven. Overall grade ≥ C-: `af_heart` (A), `af_bella` (A-),
  `af_nicole` (B-), `bf_emma` (B-), `af_aoede`, `af_kore`, `af_sarah`, `am_fenrir`,
  `am_michael`, `am_puck` (all C+), `af_alloy`, `af_nova`, `bf_isabella`, `bm_fable`,
  `bm_george` (C), `af_sky` (C-). That is **16 usable voices: 11 female, 5 male**.
- Weak voices: `am_adam` F+, `am_santa` D-, several D-grade voices (`am_echo`, `am_eric`,
  `am_liam`, `am_onyx`, `bm_daniel`, `bm_lewis`, `bf_alice`, `bf_lily`, `af_jessica`,
  `af_river`).
- VOICES.md notes: "Weakness on short utterances, especially less than 10-20 tokens", and
  voices do best in a "goldilocks range" of 100–200 tokens. That matters for one-word
  teammate replies ("Yep.", "LGTM"); pad or merge short lines.

**Does it cover ~15 distinct teammates?** Female roles yes; **male roles are the gap** (5
decent male voices, 2 of them British). Fixes, in order of quality:
1. **Blending.** The PyTorch `kokoro` package averages voices when given a comma-separated
   name: `load_voice` "If multiple voices are requested, they are averaged"
   (`torch.mean(torch.stack(packs), dim=0)`,
   [pipeline.py](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py)). With
   `kokoro-onnx` (what grokbot uses, v0.6.1) a voice is a NumPy style array, so a weighted
   blend is one line (`0.7*a + 0.3*b`). Blends like `am_michael`+`bm_george` give new,
   stable voices. How distinct they sound is **unverified** → spike S4.
2. **Speed per persona** (0.9–1.2) — cheap, adds a lot of perceived identity.
3. **Cross-language voices speaking English phonemes** (e.g. a Hindi or Spanish voice fed
   `en-us` phonemes): yields accented English; quality **unverified**, test in S4 before
   using it, and only with care (accent as character, never as joke).
4. Pitch shifting after synthesis: last resort (artifacts).

### 5.2 Licences

- Kokoro weights: **Apache 2.0**; kokoro-onnx: **MIT**
  ([kokoro-onnx README](https://github.com/thewh1teagle/kokoro-onnx), "kokoro model: Apache
  2.0", "kokoro-onnx: MIT").
- grokbot's lockfile pulls `espeakng-loader 0.2.4` (bundles espeak-ng for out-of-vocabulary
  words). espeak-ng is **GPL-3.0** ([repo](https://github.com/espeak-ng/espeak-ng)). Fine for
  personal use; matters only if Offer Letter is ever distributed as a binary.

### 5.3 Phoneme timings for lip-flap (feeds §3.4)

- The PyTorch `kokoro` package returns, for English, `Result.tokens` (misaki `MToken`s, i.e.
  words) with `start_ts`/`end_ts` filled by `join_timestamps` (`MAGIC_DIVISOR = 80`), plus
  `Result.pred_dur` (predicted duration per phoneme) and `Result.phonemes` (the phoneme
  string) ([pipeline.py](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py)).
  So **per-phoneme timings exist** in the PyTorch path: zip `phonemes` with `pred_dur`.
- `kokoro-onnx` does not document durations or timestamps (README silent) — **unverified**
  whether its ONNX graph exposes them. If not, either switch the TTS worker to the PyTorch
  `kokoro` package (GPU, same weights) or use amplitude lip-flap, which needs nothing.

## 6. Review UI + git

**Recommendation: `@git-diff-view/react` for the PR review screen (GitHub-like split/
unified diff with inline comment widgets), Monaco only for "open this file" and for the
unaided-change editor if he edits in-app; plain `subprocess` git for every write and most
reads, with pygit2 optional for fast read-only queries later.**

### 6.1 Diff viewer

| | `@git-diff-view/react` | `react-diff-view` | Monaco `DiffEditor` | diff2html |
|---|---|---|---|---|
| Licence | MIT ([repo](https://github.com/MrWangJustToDo/git-diff-view)) | MIT ([licence API](https://api.github.com/repos/otakustay/react-diff-view/license)) | MIT ([licence API](https://api.github.com/repos/microsoft/monaco-editor/license)) | MIT ([licence API](https://api.github.com/repos/rtfpessoa/diff2html/license)) |
| Inline comments | Built for it: per-line "add widget" button, `renderWidgetLine`, `extendData` + `renderExtendLine` to show existing comments under a line | `widgets` prop keyed by change — works, more assembly | Possible via view zones / content widgets, all DIY | Static HTML; no widget model |
| Views | split + unified; highlight via lowlight, Shiki or Lezer; Web Worker mode; "range mode" for big diffs | split + unified; tokenize via refractor | side-by-side + inline; full editor features | side-by-side + line-by-line |
| Input | hunks (`oldFile`/`newFile`/`hunks`) or `generateDiffFile(old, new)` | parses unified diff (`gitdiff-parser`) | two full texts | unified diff string |
| Fit | **Best for PR review** | Fine second choice | Best for editing; heavy bundle + worker setup in Vite | Read-only reports (e.g. the postmortem page) |

Review UI features to build on top: comment threads stored in SQLite keyed by
`(pr_id, path, side, line, commit_sha)`; "suggest a change" blocks; inline quiz widgets
rendered with the same widget slot; planted-bug scoring compares his comment anchors to
the answer key (same file, line within ±3, category matches) and asks a follow-up quiz to
make sure he did not guess.

### 6.2 Git from Python

| | subprocess `git` | pygit2 | dulwich | GitPython |
|---|---|---|---|---|
| Licence | git: GPL-2.0, used as a separate program | "GPLv2 with linking exception" ([repo](https://github.com/libgit2/pygit2)) | "Apache-2.0 OR GPL-2.0-or-later" ([PyPI](https://pypi.org/project/dulwich/), v1.2.17) | "3-Clause BSD License" ([repo](https://github.com/gitpython-developers/GitPython)) |
| Fidelity | 100 % (it *is* git: hooks, worktrees, `range-diff`, `format-patch`) | libgit2 subset; no hooks; some features lag | pure Python subset; slow on big repos | wraps the CLI |
| Long-running server | Fine (one short process per call) | Fine | Fine | **"GitPython is not suited for long-running processes (like daemons) as it tends to leak system resources"**; "in maintenance mode" |
| Fit | **Default** — the same commands Luigi types, so the harness can show "here is the command we ran" as a teaching aid | Optional, for hot read paths (blame, tree walks) | Skip | **Avoid** (our server is a daemon) |

Windows/WSL note: ticket repos that build in WSL (C/CUDA/Go cards) should live on the WSL
filesystem (`\\wsl$\Ubuntu\home\luigi\...`) and be driven with `wsl.exe git -C …`, or the
Python server should run inside WSL for those companies. Crossing `/mnt/c` is slow and
mixes CRLF/permissions. Decide in spike S2.

### 6.3 Persona-authored commits, presented truthfully

- **Author identity is synthetic and labelled:** `GIT_AUTHOR_NAME="Priya Raman (AI
  teammate)"`, `GIT_AUTHOR_EMAIL="priya@<company>.offer-letter.invalid"`. `.invalid` is a
  reserved TLD (RFC 2606), so GitHub never links it to a real account. **Committer =
  the harness** (`Offer Letter <harness@offer-letter.invalid>`), so `git log
  --format='%an | %cn'` always shows who wrote vs. who recorded.
- **Trailers on every AI commit:** `Persona: priya`, `Generated-by: Claude Code
  (claude-sonnet-…)` and the model from the `system/init` event. Never fake timestamps
  beyond the simulated clock; if the simulated clock is used, add `Simulated-date: yes`.
- **Planted bugs:** the answer key lives in the harness DB, never in git (a trailer would
  spoil the review). After the review, the harness adds `REVIEW-NOTES.md` listing the
  planted bugs, which he found, and the fix commits.
- **Luigi's commits use his real identity**, so on GitHub his work is distinguishable at a
  glance. When an owned repo is pushed to his GitHub, the README gets a generated
  "Provenance" section: which commits are AI-written (by trailer), which are his, and that
  the repo came from a simulated job. That keeps the portfolio honest for recruiters.
- Claude Code adds its own `Co-Authored-By` lines when it commits; keep them.

## 7. Whiteboard and diagrams

**Recommendation: Excalidraw (MIT) as the whiteboard; the AI teammate emits Mermaid for
standard diagrams (converted to editable Excalidraw elements with
`@excalidraw/mermaid-to-excalidraw`) or Excalidraw element skeleton JSON for free-form
architecture sketches. Do not use tldraw.**

- **tldraw** ([licence page](https://tldraw.dev/community/license)): SDK under the "tldraw
  license"; default terms allow use "only in development"; "The tldraw SDK will work in
  production only when provided with a valid and active license key." Licences: 100-day
  trial (sends a key hash to tldraw's servers), Commercial (via sales), Hobby
  ("discretionary", non-commercial, "made with tldraw" watermark must appear on the
  canvas). A locally run personal app is arguably "development", but that is a grey area
  and the licence can change; Excalidraw avoids the question.
- **Excalidraw**: MIT. Two LLM-friendly inputs:
  1. `parseMermaidToExcalidraw(definition, config?)` → `{elements, files}`; throws on parse
     errors (wrap in try/catch); config limited to `startOnLoad`, `flowchart.curve`,
     `themeVariables.fontSize`, `maxEdges` (500), `maxTextSize` (50000)
     ([mermaid-to-excalidraw](https://github.com/excalidraw/mermaid-to-excalidraw), MIT).
     Which Mermaid types convert natively vs. as an image is not stated on the README —
     flowcharts are the known-good case (**verify others in spike S8**).
  2. `convertToExcalidrawElements(skeletons, {regenerateIds})` — skeletons need only
     `type, x, y` for shapes, `text` for text, `label.text` for labelled containers; arrows
     bind with `start`/`end` by `id` or `type`, and positions are computed from the bound
     shapes ([skeleton API](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/excalidraw-element-skeleton)).
     Have Claude emit this with `--json-schema` so it is always valid JSON; the harness
     does layout (grid columns per tier: clients → edge → services → data) so the model
     never has to invent coordinates.
- **Mermaid** (MIT, [licence API](https://api.github.com/repos/mermaid-js/mermaid/license))
  and **D2** (MPL-2.0, [licence API](https://api.github.com/repos/terrastruct/d2/license);
  its optional TALA layout engine is proprietary — **from memory**) are good as read-only
  rendered diagrams in design docs. Excalidraw's MIT licence is confirmed by the
  [licence API](https://api.github.com/repos/excalidraw/excalidraw/license). D2 renders to
  SVG only; it can be dropped onto the Excalidraw canvas as an image but is not editable.
- Design-review flow: senior teammate's diagram appears on the board → Luigi edits it
  (adds a cache, moves a queue) → the harness diffs the element graph (added/removed nodes
  and edges by label) and feeds the change summary to the reviewer persona. Scene JSON is
  stored per session in SQLite for later replay.

## 8. Animation

**Recommendation: Motion (formerly Framer Motion) for React UI transitions; CSS for
trivial hovers; Phaser tweens inside the office canvas; Lottie (lottie-web/dotLottie) for
a handful of pre-made flourishes (offer-letter confetti, "PR merged" stamp). Skip GSAP for
licence reasons and Rive unless he wants to author state machines.**

- **Motion**: MIT ([licence API](https://api.github.com/repos/motiondivision/motion/license)).
  Layout animations, `AnimatePresence` for the call window and panel enter/exit, springs.
  Best React fit.
- **GSAP** ([standard licence](https://gsap.com/standard-license/)): free, including
  commercial use and the former Club plugins (SplitText, MorphSVG). But it is
  **proprietary** (Webflow keeps the IP) and prohibits use "in tools that allow users to
  build visual animations without code" that compete with Webflow, plus no reverse
  engineering to build competitive products. Offer Letter is not that kind of tool, so it
  would be allowed; still, Motion covers the need under MIT, so there is no reason to take
  on a proprietary dependency.
- **CSS**: hover/focus states, the "typing…" dots, toasts. Zero cost.
- **Lottie**: lottie-web is MIT ([licence API](https://api.github.com/repos/airbnb/lottie-web/license));
  dotLottie players MIT (**from memory**); animations come
  from LottieFiles (check each file's licence; many are "Lottie Simple License", free to
  use without attribution — **unverified**).
- **Rive**: web runtime MIT ([licence API](https://api.github.com/repos/rive-app/rive-wasm/license)),
  editor is a hosted proprietary app with a free tier (editor terms **from
  memory**). Nice for an interactive mascot; not needed.
- VN portrait polish: Motion handles the subtle idle bob (2 px, 4 s loop), the cross-fade
  between expressions (120 ms), and the "speaking" glow; mouth/eye frames are swapped by
  the lip-flap clock, not by Motion.

## 9. Machine probes

All read-only, run 2026-10-19 ~03:27 local. No installs, no sudo, no config edits. Docker
Desktop was **not running** (`AutoStart: false`), and I did not start it, so Docker-side
checks are partial. Probe scripts:
`C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner\276d98f4-67bb-4270-8ff2-2985ea76655d\scratchpad\probes\`.

### 9.1 Environment

```
$ wsl.exe --version
WSL version: 2.4.13.0
Kernel version: 5.15.167.4-1
WSLg version: 1.0.65
Windows version: 10.0.26200.9711
$ wsl.exe -l -v
* Ubuntu            Stopped         2
  docker-desktop    Stopped         2
$ cat /etc/wsl.conf          # (Ubuntu)
[boot]
systemd=true
[user]
default=luigi
$ cat C:\Users\Owner\.wslconfig
No such file or directory     # → all WSL2 VM settings are defaults
```

Windows toolchain (relevant to Tauri): node v22.15.1, npm 11.4.0, uv 0.11.26, Python 3.12.7,
rustc/cargo 1.92.0 (`stable-x86_64-pc-windows-msvc`), git 2.49.0, Claude Code 2.1.303,
**WebView2 runtime 155.0.4283.62**, Visual Studio folders `18`, `2022` and `2019` present
(MSVC is there; Kablooey builds with it). Docker Desktop **4.55.0.213807**, settings:
`"IntegratedWslDistros": ["Ubuntu"]`, `"UseContainerdSnapshotter": true`,
`"InferenceCanUseGPUVariant": true`.

### 9.2 KVM / nested virtualization (Firecracker)

```
$ ls -l /dev/kvm
crw-rw---- 1 root kvm 10, 232 Oct 19 03:26 /dev/kvm
$ cat /sys/module/kvm_amd/parameters/nested
1
$ grep -c -w -E 'svm|vmx' /proc/cpuinfo
0
$ lscpu | grep -i -E 'virtuali|hypervisor'
Hypervisor vendor:   Microsoft
Virtualization type: full
$ dmesg | grep -i -E 'kvm|svm'
[    0.136990] kvm: no hardware support
[    0.136992] has_svm: svm not available
[    0.136993] kvm: no hardware support
$ python3 -c 'os.open("/dev/kvm", os.O_RDWR) …'
open failed: PermissionError(13, 'Permission denied')   # luigi is not in group kvm
$ id
uid=1000(luigi) … groups=…,27(sudo),…,1001(docker)
```

**Verdict: KVM does not work in this WSL2 VM.** The `/dev/kvm` node exists only because the
kernel has KVM built in; Hyper-V is not passing AMD-V (`svm`) through to the WSL VM, so the
kernel logs "no hardware support". Even with the flag, `luigi` is not in group `kvm`.
Microsoft documents `nestedVirtualization` as a Windows-11-only `.wslconfig` key whose
**default is already `true`** ("Boolean to turn on or off nested virtualization, enabling
other nested VMs to run inside WSL 2",
[WSL config docs](https://learn.microsoft.com/en-us/windows/wsl/wsl-config), updated
2026-10-16). So the default is on and the guest still has no `svm`: setting the key
explicitly is unlikely to help by itself. Candidate causes (**all unverified**): the old
WSL build (2.4.13 with kernel 5.15.167; current WSL ships newer kernels), or Hyper-V not
exposing AMD-V nesting on this host. Next steps for Luigi to approve (config changes, not
done): `wsl --update`, `wsl --shutdown`, re-run `dmesg | grep -i svm`; if `svm` appears,
`sudo usermod -aG kvm luigi`. If it still fails, Firecracker is off the table on this PC.

### 9.3 cgroups

```
$ stat -fc %T /sys/fs/cgroup
tmpfs                                  # NOT cgroup2fs
$ mount | grep cgroup
tmpfs on /sys/fs/cgroup type tmpfs (ro,…)
cgroup2 on /sys/fs/cgroup/unified type cgroup2 (rw,…,nsdelegate)
cgroup on /sys/fs/cgroup/cpuset type cgroup (…cpuset)
cgroup on /sys/fs/cgroup/cpu type cgroup (…cpu)
cgroup on /sys/fs/cgroup/memory type cgroup (…memory)
… (blkio, devices, freezer, net_cls, perf_event, net_prio, hugetlb, pids, rdma, misc)
$ cat /sys/fs/cgroup/unified/cgroup.controllers
                                       # (empty: every controller is bound to v1)
$ cat /proc/self/cgroup
0::/init.scope
5:memory:/init.scope
…
```

**Verdict: hybrid v1/v2 mode; the v2 hierarchy has zero controllers.** `memory.max`,
`pids.max`, `cpu.max` cannot be set through cgroup v2 in this Ubuntu distro as configured.
All WSL2 distros share one kernel, so Docker Desktop's VM is probably in the same state, but
I could not check (`docker info` needs the daemon). Current Microsoft docs list a
`wsl.conf` key `cgroups` ("Selects the cgroup hierarchy to mount in WSL 2. Available values
are `v1` and `v2`", **default `v2`**) and a `.wslconfig` key `isolateDistroCgroup`
("Requires cgroup v2") ([WSL config docs](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)).
This machine's WSL 2.4.13 still mounts hybrid, so the v2 default most likely arrived in a
later WSL release (**unverified** which one). Fix options for Luigi to approve (not done):
(a) `wsl --update` then re-probe; (b) add `cgroups=v2` under `[automount]` in
`/etc/wsl.conf` on a WSL version that supports the key; (c) the older community
workaround `.wslconfig` → `kernelCommandLine = cgroup_no_v1=all`
(**from memory, not re-verified**). Then `wsl --shutdown` and re-run
`stat -fc %T /sys/fs/cgroup` (want `cgroup2fs`).

### 9.4 GPU inside WSL2

```
$ nvidia-smi                       # /usr/lib/wsl/lib/nvidia-smi
| NVIDIA-SMI 610.57.01   KMD Version: 610.88   CUDA UMD Version: 13.3 |
|   0  NVIDIA GeForce RTX 4070  On | 00000000:07:00.0 On | 1349MiB / 12282MiB | 2% |
| Processes: No running processes found |
$ nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv
NVIDIA GeForce RTX 4070, 610.88, 12282 MiB, 8.9
$ python3 -c "import torch;print(torch.__version__, torch.cuda.is_available())"
2.12.0+cu130 True
$ nvcc --version
Cuda compilation tools, release 12.0, V12.0.140        # Ubuntu apt toolkit, /usr/bin/nvcc
```

Windows-side `nvidia-smi` agrees: `NVIDIA GeForce RTX 4070, 610.88, 1325 MiB, 12282 MiB`
(~1.3 GB already used by the desktop, so ~10.9 GB is really free for workloads).

### 9.5 libcuda location and LD_PRELOAD plausibility (CPL-04)

```
$ ls -la /usr/lib/wsl/lib/libcuda.so*
-r-xr-xr-x 4 root root 187984 Aug 18 09:53 libcuda.so / libcuda.so.1 / libcuda.so.1.1
$ readelf -d /usr/lib/wsl/lib/libcuda.so.1 | grep -E 'NEEDED|SONAME'
 NEEDED libc.so.6, libdl.so.2, libpthread.so.0;  SONAME libcuda.so.1
$ nm -D /usr/lib/wsl/lib/libcuda.so.1 | grep -E ' T (cuMemAlloc|cuGetProcAddress|cuMemGetInfo)'
T cuGetProcAddress   T cuGetProcAddress_v2   T cuMemAlloc   T cuMemAlloc_v2
T cuMemAllocAsync    T cuMemAllocManaged     T cuMemGetInfo T cuMemGetInfo_v2 …
# which libcuda a real PyTorch process maps (/proc/self/maps after torch.zeros(1,device="cuda")):
/usr/lib/wsl/lib/libcuda.so.1
/usr/lib/wsl/drivers/nv_dispig.inf_amd64_cc526ccc3287f5cd/libcuda.so.1.1
/usr/lib/wsl/lib/libdxcore.so
/home/luigi/.local/lib/python3.12/site-packages/nvidia/cu13/lib/libcudart.so.13
$ ldconfig -p | grep libcuda
libcuda.so.1 => /usr/lib/wsl/lib/libcuda.so.1
libcuda.so.1 => /lib/x86_64-linux-gnu/libcuda.so.1     # ← second copy!
$ dpkg -S /usr/lib/x86_64-linux-gnu/libcuda.so.1
libnvidia-compute-580:amd64: /usr/lib/x86_64-linux-gnu/libcuda.so.1   # 96 MB native Linux driver lib
```

**Verdict: an LD_PRELOAD shim is plausible.** The WSL `libcuda.so.1` is a small (188 KB)
ordinary ELF loader that exports the full driver API and then loads the real implementation
from `/usr/lib/wsl/drivers/…/libcuda.so.1.1`. Interposing its exported symbols with
`LD_PRELOAD` is ordinary ELF symbol interposition. The catch is not WSL-specific: CUDA ≥ 11.3
runtimes resolve driver entry points through `cuGetProcAddress`, so a shim that only defines
`cuMemAlloc_v2` will miss PyTorch's calls. It must also hook `cuGetProcAddress(_v2)` (and
usually `dlsym`), which is what HAMi-core does. **Unverified until spike S10 runs.**

**Hazard found:** Ubuntu package `libnvidia-compute-580` is installed inside WSL and puts a
native Linux `libcuda.so.580.178.04` in `/usr/lib/x86_64-linux-gnu`. NVIDIA's WSL guide:
"Do not install any Linux display driver in WSL" and "users must not install any NVIDIA GPU
Linux driver within WSL 2"
([CUDA on WSL user guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)). Today it
is harmless because `/usr/lib/wsl/lib` comes first in the ldconfig order and PyTorch maps the
WSL copy, but a shim or a build that links `-L/usr/lib/x86_64-linux-gnu -lcuda`, or a
container that bind-mounts the wrong copy, will load a driver library that cannot talk to the
GPU. The spike must print `/proc/self/maps` to prove which copy is loaded.

### 9.6 NVML per-process accounting

`nvidia-smi` in WSL prints `No running processes found` even while the Windows desktop holds
1.3 GB. NVIDIA's WSL guide, "Features Not Yet Supported": "NVML (nvidia-smi) does not
support all the queries yet", listing "GPU utilization, active compute process" as
unsupported, and ECC/compute-mode/persistence-mode changes "will not be supported". It
also lists Unified Memory as limited ("UVM full features will not be available") and
pinned memory as limited
([CUDA on WSL user guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)).
The same guide lists Docker as supported ("CLI and Docker Desktop Supported").

### 9.7 Docker GPU

Not testable today: the daemon was down (`failed to connect to the docker API at
npipe:////./pipe/dockerDesktopLinuxEngine`), and there is no `nvidia-ctk` /
`nvidia-container-runtime` inside Ubuntu. Docker Desktop's WSL2 backend has its own GPU path
(`docker run --gpus all …`, [Docker Desktop GPU docs](https://docs.docker.com/desktop/features/gpu/),
not re-fetched), so the toolkit is not needed in the distro; NVIDIA's WSL guide lists
"CLI and Docker Desktop Supported". Local image list: unknown (daemon down).

### 9.8 What each result unblocks or blocks (catalog 02)

| Probe | Result | Cards affected |
|---|---|---|
| `/dev/kvm` + `svm` | **Blocked** (no svm in guest; dmesg "no hardware support") | **BLJ-03** Firecracker warm pools/snapshots: blocked → run the CRIU or container-checkpoint fallback, or Luigi approves the `.wslconfig` nested-virt change and we re-probe. **BLJ-08** (design review) unaffected: whiteboard only. |
| cgroup v2 | **Blocked as configured** (hybrid; v2 has no controllers) | **BLJ-02** cgroup-v2 limits: blocked until `cgroup_no_v1=all` (his approval) or until Docker Desktop's VM is shown to be v2. seccomp and egress parts of BLJ-02 are unaffected. |
| `nvidia-smi` in WSL | **Works** (4070, driver 610.88, CUDA UMD 13.3, sm_89) | Unblocks every GPU card that runs in WSL: KLN-01…09 with vLLM, LPL-04/07, MTH-03 (INT8 part), PLB-04 GPU rescoring. Compute capability 8.9 confirms Ada for **KLN-04** FP8 (FP8 kernels themselves still unverified). |
| PyTorch CUDA in WSL | **Works** (torch 2.12.0+cu130) | Same as above; harness Python can use the GPU directly. |
| libcuda + `cuGetProcAddress` exports | **Plausible** | **CPL-04** stays assignable, gated on spike S10. Warn about the second `libcuda` from `libnvidia-compute-580`. |
| NVML per-process | **Not available in WSL** | **CPL-05** (idle reaper / chargeback): must read a simulated or recorded per-process telemetry feed, not live NVML. CPL-04's NVML hooks can only be tested on the device-wide queries. |
| Docker GPU | **Unknown** (daemon down) | Per-ticket sandboxes that need the GPU (vLLM compose kit in §5 of 02) wait on spike S9. |
| TensorRT, CRIU, gVisor | Not installed (`which criu firecracker` empty) | MTH-03 TensorRT path and BLJ-03 CRIU fallback both need a spike before assignment. |

## 10. Spike plan

Ordered by how much of the build each one could invalidate. Times are first-try
estimates. "He" = Luigi; spikes that touch his desktop input are run by him, not
automated.

| # | Spike | Steps | Pass condition | Unblocks |
|---|---|---|---|---|
| **S1** | **Teammates on the subscription** (1 h) | Python asyncio runner spawns 2 concurrent `claude -p --input-format stream-json --output-format stream-json --verbose --model haiku --setting-sources project --strict-mcp-config --append-system-prompt-file persona.md` from a harness-owned cwd with `ANTHROPIC_*` stripped. Turn 1 tells each persona a fact; process exits; `--resume <id>` asks for it; `--fork-session` branches; send `/usage`. | `claude auth status` = `claude.ai` and init event shows no API key source; both personas stay in character and **do not** echo anything from Luigi's `~/.claude/CLAUDE.md`; resumed session recalls the fact; fork gets a new id; `/usage` returns `session`/`weekly_*` rows with `resets_at`; no `rate_limit` retry events; spike costs < 2 % of the session meter. | All of §4 |
| **S2** | **Review loop core** (2 h) | Server makes a repo; persona commit via `subprocess` git with synthetic author + trailers; Sonnet writes a small PR with 2 planted bugs from a spec (`--json-schema` for the answer key); `@git-diff-view/react` renders split view with comment widgets; comments saved in SQLite; scorer matches anchors to the key. Time `git status` on a 10k-file repo on `/mnt/c` vs. WSL ext4. | His two comments on the planted lines score, a decoy comment does not; `git log --format='%an | %cn | %(trailers:only)'` shows honest provenance; repo-location decision recorded with numbers. | §6, review-to-own |
| **S3** | **Pixel office** (2 h) | Vite + React + Phaser 4 template; a 40×30 Tiled map with LimeZu Modern Office 16 px at ×3; collision layer, `spots` objects; 6 NPCs walk with easystar.js to a meeting room; clicking an NPC opens a React panel via EventBus. | 60 fps at 1080p in Chrome (`performance` panel); A* path < 5 ms; no tile seams/bleeding at ×3; `git ls-files` lists no LimeZu PNG. | §2 |
| **S4** | **Voice cast** (1 h) | Render 3 lines (long, short "Yep, LGTM.", technical) with the 16 base voices, 8 blends (`0.6a+0.4b`), and speed variants. He does a blind "same person or different?" test on 12 random pairs and rates acceptability. | ≥ 12 voices he rates distinct and acceptable, including ≥ 5 male; real-time factor < 0.3 on the 4070; short-line artifacts noted with a fix (padding/merging). | §5 |
| **S5** | **Tauri shell** (2 h) | Wrap the S3 app in Tauri 2; sidecar launcher → `uv run` FastAPI; port handshake over stdout; tray icon; always-on-top `/call` window; notification from an **installed** NSIS/MSI build; server in a Job Object. | Cold start < 5 s to interactive; killing the Tauri process (Task Manager) leaves **no** `python.exe` behind; toast shows the app name (not PowerShell); Phaser fps in Tauri within 10 % of Chrome. | §1.1, §1.3, §1.5 |
| **S6** | **Push-to-talk** (45 min) | Register `Ctrl+Alt+Space` with the global-shortcut plugin; log `Pressed`/`Released` with timestamps; forward to Python, which gates the mic (grokbot VAD/STT). He holds the key 20 times while VS Code is focused. | Exactly 20 Pressed + 20 Released (no repeat storm); key-down → mic-open < 50 ms; transcript arrives; note whether VS Code also received the combo. | §1.2 |
| **S7** | **Portrait pipeline** (3 h) | ComfyUI + Animagine XL 4.0: canonical bust → 7 expressions by face-only inpainting → mouth ×3 + eyes ×2 overlays, all via the ComfyUI HTTP API; amplitude lip-flap demo in the browser driven by a Kokoro clip. | Peak VRAM < 11 GB (`nvidia-smi` during the run); in a flip-book of the 7 expressions he sees no hair/outfit drift; < 20 min GPU time per character; overlays align to the pixel; mouth motion visibly matches the audio. | §3 |
| **S8** | **Whiteboard** (1.5 h) | Excalidraw in React; Claude emits (a) a Mermaid flowchart → `parseMermaidToExcalidraw`, (b) an 8-node architecture as element skeletons via `--json-schema` → `convertToExcalidrawElements`. Also try a sequence and a class diagram. He edits; the harness diffs the element graph. | 10/10 generated diagrams load without exceptions; all arrows bound; the diff names added/removed nodes and edges correctly; record which Mermaid types stay editable. | §7, design-review |
| **S9** | **Docker sandboxes** (1.5 h; needs Docker Desktop started and one image pull — ask first) | `docker info` (cgroup version, runtimes); CPU sandbox with `--memory 512m --pids-limit 256 --network none` runs a ticket's tests and returns JUnit XML; `docker run --rm --gpus all <cuda image> nvidia-smi`. | Memory hog is OOM-killed inside the container only; no network from inside; warm start < 2 s; GPU visible in the container. Records Docker's cgroup version for BLJ-02. | per-ticket runs, BLJ-02, GPU cards in Docker |
| **S10** | **CUDA interception shim** (1.5 h; catalog-specific) | ~80-line C `LD_PRELOAD` library in WSL hooking `cuGetProcAddress(_v2)`, `cuMemAlloc_v2`, `cuMemGetInfo_v2`; run PyTorch allocating 256 MB then 2 GB under a 1 GB cap; print `/proc/self/maps`. | Shim logs PyTorch's allocations; the 2 GB allocation fails with a clean CUDA OOM; maps show `/usr/lib/wsl/lib/libcuda.so.1`, not the `libnvidia-compute-580` copy. | CPL-04 go/no-go |
| S11 | (optional, needs his OK) WSL update re-probe | `wsl --update`, `wsl --shutdown`, re-run §9.2/§9.3 probes. | `svm` present + KVM ioctl works → BLJ-03 Firecracker; `cgroup2fs` → BLJ-02 in WSL. | BLJ-02, BLJ-03 |

## 11. Unverified items

- Whether `--setting-sources project` keeps `~/.claude/CLAUDE.md` and Luigi's auto memory
  out of teammate sessions (S1).
- Concurrency limits for parallel `claude -p` on a Max plan (none documented).
- When `--bare` becomes the `-p` default, and what opt-out flag will exist.
- Whether the Python Agent SDK on a claude.ai login is acceptable for a personal,
  undistributed tool (docs conflict in tone; avoided by using the CLI).
- Tauri global-shortcut key-repeat behaviour, whether the focused app still sees the
  combo, modifier-only shortcuts (S6). Whether WebView2 remembers a mic grant in Tauri.
- Electron `globalShortcut` key-up support (not checked).
- Blended Kokoro voice distinctness; cross-language voices speaking English; whether
  `kokoro-onnx` exposes durations (S4).
- SDXL VRAM figures on the 4070 (S7); Pony V6 licence text (not re-fetched).
- Licences **re-checked 2026-10-19** via GitHub's licence API / licence files / PyPI:
  Motion MIT, Monaco MIT, react-diff-view MIT, diff2html MIT, Excalidraw MIT, Mermaid MIT,
  lottie-web MIT, rive-wasm MIT, easystar.js MIT, ComfyUI GPL-3.0, Inochi2D BSD-2-Clause,
  D2 MPL-2.0, Rhubarb MIT (+ permissive bundled parts), dulwich "Apache-2.0 OR
  GPL-2.0-or-later", Tiled editor "GPL" / libtiled BSD-2. **Correction:** Nuitka is
  **AGPL-3.0**, not Apache-2.0 as first written from memory.
- Still **from memory / not re-checked**: Tauri's MIT half of the dual licence, D2's
  proprietary TALA engine, dotLottie player licence, LottieFiles "Lottie Simple License",
  Rive editor terms, Nuitka's position on compiled-output licensing, Tiled's GPL version,
  git GPL-2.0.
- LimeZu: whether a hosted public web demo counts as distribution (ask the author); the
  "$3 minimum" user comment.
- Which Mermaid diagram types `mermaid-to-excalidraw` converts natively (S8).
- Why nested virtualization is off in WSL despite the documented default; which WSL
  release made cgroup v2 the default; Docker Desktop VM's cgroup version (S9/S11).
- Docker GPU passthrough on this machine (daemon was down; S9).
- WebSearch budget for the session ran out early in this task, so several "from memory"
  items above could not be checked by search; official pages were fetched directly instead
  where it mattered (Anthropic, Tauri, LimeZu, Kenney, tldraw, GSAP, Live2D, NVIDIA,
  Microsoft, model cards).
