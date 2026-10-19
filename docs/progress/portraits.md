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
