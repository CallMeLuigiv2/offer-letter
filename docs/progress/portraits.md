# Portraits setup: ComfyUI + Animagine XL 4.0

Agent: portraits-setup. Scope: install, model download, one smoke test. No git commits.

## Environment

- GPU: NVIDIA GeForce RTX 4070, 12282 MiB total. Driver 610.88, CUDA UMD 13.3.
- Baseline GPU memory before the run: 1330 MiB used by other desktop apps.
- C: free space before install: about 191.7 GB.

## Installed

- ComfyUI: `v0.42.1` (commit `63be2f9b82ad0dac88a7ceaa28a9cf3154125a18`, 2026-10-18). Cloned from `https://github.com/comfyanonymous/ComfyUI` into `C:\Users\Owner\tools\ComfyUI`. Latest tag at the time of install.
- Python: 3.12.7 in `C:\Users\Owner\tools\ComfyUI\.venv` (uv 0.11.26). Created with `uv venv --python 3.12 .venv`. Global Python was not changed.
- PyTorch: `torch 2.14.1+cu130`, `torchvision 0.29.1+cu130`, `torchaudio 2.11.0+cu130`, from `https://download.pytorch.org/whl/cu130`. cu130 was the newest CUDA build offered that the 610.88 driver supports.
- `torch.cuda.is_available()` returns True. Device: `NVIDIA GeForce RTX 4070`.
- ComfyUI requirements from `requirements.txt`, including `comfyui-frontend-package==1.55.18`, `comfy-kitchen==0.2.39`, `comfy-aimdo==0.5.6`. Installed with `uv pip install --python .venv -r requirements.txt`.

## Model

- File: `C:\Users\Owner\tools\ComfyUI\models\checkpoints\animagine-xl-4.0.safetensors`
- Source: `https://huggingface.co/cagliostrolab/animagine-xl-4.0` (file `animagine-xl-4.0.safetensors`, the base 4.0 release)
- Size: 6,938,434,056 bytes. Matches the size on the file page.
- SHA-256: `1d5b43ff75b6ab598502d4c779d2fbfa3dceca51c60c3b609640a60772333916`. Matches the LFS oid on Hugging Face.
- Licence: CreativeML Open RAIL++-M (`license: openrail++` in the card metadata).
- Gated: no (`"gated": false` in the Hugging Face API).
- The repo also has `animagine-xl-4.0-opt.safetensors` (6,938,350,040 bytes), the "Opt" refinement from 2025-02-13. It is not installed. The base file was used per the brief.

## Recommended settings (from the model card)

- Prompt structure: `1girl/1boy/1other, character name, from which series, rating, everything else in any order`, then quality tags at the end.
- Quality tags: `masterpiece, high score, great score, absurdres`
- Negative prompt: `lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry`
- CFG: 4 to 7 (5 recommended)
- Steps: 25 to 28 (28 recommended)
- Sampler: Euler Ancestral (`euler_ancestral`)
- Portrait resolutions: 832 x 1216 (2:3), 768 x 1344, 640 x 1536, 896 x 1152.
- Rating tags: `safe`, `sensitive`, `nsfw`, `explicit`.

## Smoke test

- Script: `C:\Users\Owner\projects\offer-letter\tools\portraits\smoke_test.py` (standard library only)
- Workflow: CheckpointLoaderSimple, CLIPTextEncode x2, EmptyLatentImage 832x1216, KSampler (28 steps, CFG 5, euler_ancestral, normal scheduler), VAEDecode, SaveImage.
- Prompt: `1girl, solo, mature female, early 40s, short black hair, silver streak in hair, round tortoiseshell glasses, olive cardigan, upper body, portrait, bust, looking at viewer, simple background, closed mouth, safe, masterpiece, high score, great score, absurdres`
- Output: `C:\Users\Owner\projects\offer-letter\tools\portraits\smoke\dana_smoke.png`
- Generation time: 13.4 s wall clock. This includes the first model load into VRAM, since the server had just started.
- Peak GPU memory: 10,620 MiB whole-GPU, sampled with `nvidia-smi` every 0.5 s. That includes the 1,330 MiB baseline from other apps, so ComfyUI accounts for roughly 9.3 GB.
- Visual check: black hair, round glasses and an olive cardigan match the prompt. The silver streak is not clearly visible in the image. This is a prompt-adherence note for the pipeline designer, not an install problem.

## Server

- Started headless: `.venv\Scripts\python main.py --listen 127.0.0.1 --port 8188`. Logs are in `C:\Users\Owner\tools\ComfyUI\server.log` and `server.err.log`.
- Ready check: `/system_stats` returned the device list with the RTX 4070.
- Stopped after the smoke test. Only the process this agent started (PID 49352) was stopped. `/system_stats` no longer responds and GPU memory is back to 1330 MiB.

## Problems

- None blocking.
- ComfyUI started before the checkpoint existed. It picked up the new file without a restart, as `/object_info` listed it.

## S7: cast portrait pipeline (Kilnworks, 6 characters, 14 images each)

Script: `tools/portraits/generate.py` (stages `base`, `pick`, `masks`, `expr`, `talk`, `sheets`). Timings in `tools/portraits/timings.json`. Prompts and seeds in `tools/portraits/cast_prompts.json`. Full-size originals in `C:\Users\Owner\tools\ComfyUI\output\offerletter\<id>\`. Face and mouth masks in `tools/portraits/masks/`, overlays in `tools/portraits/debug/`.

Shared settings: checkpoint `animagine-xl-4.0.safetensors`, 832x1216, 28 steps, CFG 5, euler_ancestral. Style tags: `anime, visual novel, anime coloring, bust, upper body, portrait, looking at viewer, simple background, white background, soft studio lighting`. Quality tags last: `masterpiece, high score, great score, absurdres, safe`. Negative: the card negative plus `nsfw, cleavage, revealing clothes`.

Timing and VRAM (whole GPU, sampled with nvidia-smi; baseline about 1330 MiB from other apps):

| Stage | Generations | Wall time | Per generation | Peak VRAM |
|---|---|---|---|---|
| base (4 seeds x 6) | 24 | 224.9 s | about 9.1 s | 10848 MiB |
| expr (face inpaint, 6 x 6) | 36 | 347.5 s | about 9.3 s | 10880 MiB |
| talk (mouth inpaint, 7 x 6) | 42 | 412.9 s | about 9.6 s | 10876 MiB |

### Chosen seed per character

| id | Seed | Why |
|---|---|---|
| dana | 1002 | Clearest silver-white streak, brown round frames, clean cardigan and tee |
| kenji | 1002 | Centred, headphones around neck, hoodie; the other seeds were off-centre or cut off |
| ines | 1001 | Low ponytail, green plaid shirt, freckles visible |
| theo | 1001 | Mustard tee, earbud visible, messy blond hair |
| amara | 1004 | Mustard blazer, gold hoops, high bun (hair is blonde, the card does not specify colour) |
| leo | 1002 | Blue lanyard with badge, backpack strap, bowl cut, clean framing |

### Masks

- The lbpcascade_animeface detector found Dana, Ines and Leo. It missed Kenji, Theo and Amara, so I set their face boxes by eye (recorded in `cast_prompts.json` as `face_box`).
- Mouth centre moved from 0.85h to 0.74h of the box. The cascade box runs past the chin, so 0.85h put the mouth mask on the chin for Dana. The overlays for Dana, Ines and Leo still look a little low. The outputs did not show a visible mouth problem, but this was not measured.

### QA findings (contact sheets, all viewed)

Fixed or met:
- Hair, outfit and glasses are pixel-identical outside the face mask (PIL composite). Identity holds across all 14 images for each character.
- No extra fingers, broken glasses, or NSFW content. The SFW negatives held.
- Silver streak is visible for Dana. Glasses read as round brown frames.
- Ages read correctly: Dana and Kenji look mature, Ines and Amara adult, Theo and Leo young.

Not met (not regenerated):
- Headroom: the head reaches the top edge on Dana, Kenji, Ines and Theo. Leo and Amara have some room. The brief asked for headroom and the prompt tags did not produce it. A fix needs either a taller canvas cropped down, or a prompt/seed pass with tags that push the head lower. I did not regenerate this because it changes the base for every character.
- Weak expressions: `skeptical`, `concerned` and `thinking` read as near-neutral for Dana, Theo and Amara at denoise 0.55. A denoise of about 0.65 for those three, or a stronger expression tag, would probably fix it. I did not regenerate.
- Leo `surprised`: the eyes show bright white highlight blobs. Minor, but visible.
- Kenji `surprised`: mouth is open but the expression is only mildly surprised.

### Contact sheets

- `content/companies/kilnworks/portraits/dana/contact_sheet.png`
- `content/companies/kilnworks/portraits/kenji/contact_sheet.png`
- `content/companies/kilnworks/portraits/ines/contact_sheet.png`
- `content/companies/kilnworks/portraits/theo/contact_sheet.png`
- `content/companies/kilnworks/portraits/amara/contact_sheet.png`
- `content/companies/kilnworks/portraits/leo/contact_sheet.png`

Each character folder holds 14 PNGs at 512 px wide: `<expr>.png` and `<expr>_talk.png` for neutral, happy, skeptical, thinking, concerned, surprised and laughing.

### Environment added for S7

- OpenCV pinned to `opencv-python-headless 4.14.0.94` in the ComfyUI venv. 5.0.0 has no `CascadeClassifier`.
- `tools/portraits/lbpcascade_animeface.xml` (MIT, from nagadomi/lbpcascade_animeface).
- ComfyUI server started and stopped by this agent (PID 53228). No commits made.

## S7 round 2: Amara redo, stronger weak expressions

Changes to `generate.py`: per-character negatives (`EXTRA_NEGATIVE`), `base --seeds`, `expr --exprs --denoise`, `talk --exprs`, and the stronger tags for skeptical, concerned and thinking.

### Amara (full redo)

- Look: dark-skinned female, black box braids in a high bun, mustard blazer over white shirt, gold hoops. Negative adds `light skin, pale skin, blonde hair, brown hair, large breasts, cleavage`.
- Seeds 2001 to 2006 generated. 2001 and 2005 were close, but 2004 gave the clearest high bun, mustard blazer and hoops. 2003 had stray caption text in the image, so it was rejected.
- Chosen seed: 2004. Face box by eye, `[255, 330, 310, 500]`, after the cascade missed. The first hand-set box sat too far left.
- All 6 expressions at denoise 0.55, then the talk set. Skeptical, concerned and thinking were then redone at 0.65.
- Skin tone is the same across all 14 frames. The high bun and hoops hold.
- Known carry-over: the base has a white rectangle behind her, which stays in every frame.

### Dana and Theo

- Skeptical, concerned and thinking redone at denoise 0.65 with the new tags, then their talk variants. Other expressions untouched.
- Frowns now read clearly on both. Thinking is still subtle on both.

### Timings and VRAM

- Amara base: 58.5 s for 6 generations. Peak 10844 MiB.
- Amara expr (6 at 0.55): 57.7 s. Peak 10876 MiB.
- Amara talk (7 generations): 68.9 s. Peak 10876 MiB.
- Weak redo (dana, theo, amara; 9 generations at 0.65): 88.6 s. Peak 10876 MiB.
- Talk redo (9 generations): 89.0 s. Peak 10876 MiB.

### Contact sheets (updated)

- `content/companies/kilnworks/portraits/amara/contact_sheet.png`
- `content/companies/kilnworks/portraits/dana/contact_sheet.png`
- `content/companies/kilnworks/portraits/theo/contact_sheet.png`

Headroom was left as is, per the lead's instruction. ComfyUI was stopped after the run (PID 31528).

## S7 round 3: WebP output

- Per-character images are now WebP, quality 85, method 6, 512 px wide: `<expr>.webp` and `<expr>_talk.webp` for all 7 expressions, for 6 characters. 84 files.
- The matching PNGs were deleted from `content/companies/kilnworks/portraits/<id>/`. The contact sheets stay as PNG.
- Full-size originals are still in `C:\Users\Owner\tools\ComfyUI\output\offerletter\<id>\`.
- `generate.py` `sheets` stage now writes WebP.
- Size: WebP images total 3.7 MB (3740.5 KB). Contact sheets total 4.6 MB. Everything in the portraits folder is about 8.4 MB, down from 44 MB of PNGs.
