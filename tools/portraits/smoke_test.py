"""Smoke test: one txt2img run against a local ComfyUI server using Animagine XL 4.0.

Posts an API-format workflow to http://127.0.0.1:8188/prompt, polls /history,
downloads the PNG into tools/portraits/smoke/dana_smoke.png, and reports the
wall time and peak GPU memory sampled with nvidia-smi during the run.

Standard library only. Run with the ComfyUI venv:
    C:\\Users\\Owner\\tools\\ComfyUI\\.venv\\Scripts\\python.exe smoke_test.py
"""

import json
import random
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
CHECKPOINT = "animagine-xl-4.0.safetensors"
OUT_DIR = Path(__file__).resolve().parent / "smoke"
OUT_FILE = OUT_DIR / "dana_smoke.png"

# Model card: 1girl/1boy/1other, character, series, rating, everything else,
# then quality tags last. Card settings: 832x1216, CFG 5, 28 steps, Euler a.
POSITIVE = (
    "1girl, solo, mature female, early 40s, short black hair, silver streak in hair, "
    "round tortoiseshell glasses, olive cardigan, upper body, portrait, bust, "
    "looking at viewer, simple background, closed mouth, safe, "
    "masterpiece, high score, great score, absurdres"
)
NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, low score, bad score, "
    "average score, signature, watermark, username, blurry"
)


def build_workflow(seed: int) -> dict:
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POSITIVE, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["4", 1]}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 832, "height": 1216, "batch_size": 1},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "portraits_smoke", "images": ["8", 0]},
        },
    }


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        COMFY + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_json(path: str) -> dict:
    with urllib.request.urlopen(COMFY + path, timeout=30) as resp:
        return json.loads(resp.read())


class VramSampler:
    """Samples nvidia-smi memory.used on a background thread until stopped."""

    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.peak_mib = 0
        self.samples = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _read_mib(self) -> int:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return int(out.strip().splitlines()[0])

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak_mib = max(self.peak_mib, self._read_mib())
            self.samples += 1
            self._stop.wait(self.interval)

    def __enter__(self):
        self.peak_mib = self._read_mib()
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


def main() -> None:
    seed = random.randint(1, 2**32 - 1)
    workflow = build_workflow(seed)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with VramSampler() as vram:
        start = time.monotonic()
        queued = post_json("/prompt", {"prompt": workflow, "client_id": "portraits-smoke"})
        prompt_id = queued["prompt_id"]
        print(f"queued prompt_id={prompt_id} seed={seed}")

        entry = None
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            history = get_json(f"/history/{prompt_id}")
            if prompt_id in history:
                entry = history[prompt_id]
                break
            time.sleep(1)
        elapsed = time.monotonic() - start

    if entry is None:
        raise SystemExit("timed out waiting for /history")

    status = entry.get("status", {})
    if status.get("status_str") != "success":
        raise SystemExit(f"generation failed: {json.dumps(status, indent=2)}")

    image = None
    for node_output in entry["outputs"].values():
        for img in node_output.get("images", []):
            image = img
    if image is None:
        raise SystemExit("no images in history outputs")

    query = urllib.parse.urlencode(
        {"filename": image["filename"], "subfolder": image["subfolder"], "type": image["type"]}
    )
    with urllib.request.urlopen(f"{COMFY}/view?{query}", timeout=60) as resp:
        OUT_FILE.write_bytes(resp.read())

    print(f"saved {OUT_FILE}")
    print(f"generation_seconds={elapsed:.1f} (includes queue wait and model load)")
    print(f"peak_gpu_memory_used_mib={vram.peak_mib} (whole GPU, samples={vram.samples})")


if __name__ == "__main__":
    main()
