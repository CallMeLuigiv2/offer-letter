"""Generate the explainer backgrounds with ComfyUI + Animagine XL 4.0 (decision D4, ARCHITECTURE §9.2).

Same model, sampler and API as the cast portraits (tools/portraits/generate.py), so the
places match the people. Each background is a txt2img pass at an SDXL size (1344x768)
followed by a light img2img pass at 1920x1088 (a "hires fix": more detail than a plain
upscale), then centre-cropped to 1920x1080.

    # ComfyUI must be running: C:\\Users\\Owner\\tools\\ComfyUI\\.venv\\Scripts\\python main.py --listen 127.0.0.1 --port 8188
    uv run --project tools/explainer python tools/explainer/gen_backgrounds.py candidates   # 3 seeds each + a grid
    uv run --project tools/explainer python tools/explainer/gen_backgrounds.py pick bakery-front=2003 ...
    uv run --project tools/explainer python tools/explainer/gen_backgrounds.py all          # regenerate the picked seeds

Picked seeds and the prompts live in assets/backgrounds/backgrounds.json. Candidates go to
cache/backgrounds/ (gitignored); only the picked PNGs are kept in assets/backgrounds/.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets" / "backgrounds"
CANDIDATES = HERE / "cache" / "backgrounds"
INDEX = OUT / "backgrounds.json"
COMFY = "http://127.0.0.1:8188"
CHECKPOINT = "animagine-xl-4.0.safetensors"
SEEDS = [2001, 2002, 2003]
MAX_BYTES = 2_000_000

# Model-card order: subject tags, then style, quality tags last (as tools/portraits/generate.py).
STYLE = "anime, anime coloring, scenery, no humans, indoors, wide shot, depth of field, soft lighting, detailed background"
QUALITY = "masterpiece, high score, great score, absurdres, safe"
NEGATIVE = (
    "1girl, 1boy, people, person, humans, crowd, character, face, hands, "
    "text, english text, sign, signboard, logo, letters, writing, menu board, "
    "lowres, bad anatomy, error, cropped, worst quality, low quality, low score, bad score, "
    "average score, signature, watermark, username, blurry, jpeg artifacts, cluttered, messy"
)

PLACES = {
    "bakery-front": (
        "bakery, bakery shop interior, storefront, wooden counter, glass display case, bread, baguette, "
        "croissant, wooden shelves with bread loaves, glass door, shop entrance, large window, "
        "warm daylight, sunlight, light rays, potted plant, wooden floor, cream walls, cozy, calm, spacious"
    ),
    "bakery-kitchen": (
        "bakery kitchen, commercial kitchen, large oven, deck oven, stainless steel, baking trays, "
        "bread on trays, metal rack, cooling rack, flour, wooden workbench, tiled wall, "
        "warm lighting, orange glow, spacious, calm"
    ),
    "back-office": (
        "small office, back office, wooden desk, open book, ledger, stack of papers, pen, desk lamp, "
        "wall clock, bookshelf, binders, window, afternoon, warm sunlight, plant, "
        "plain wall, cozy, quiet, calm, spacious"
    ),
    "test-kitchen": (
        "small kitchen, test kitchen, clean kitchen, white tiles, small oven, countertop, cutting board, "
        "measuring cups, shelf, window, bright, soft daylight, pastel colors, minimalist, tidy, empty room, calm"
    ),
}


def prompt_for(place: str) -> str:
    return f"{PLACES[place]}, {STYLE}, {QUALITY}"


# ---------- ComfyUI API (same calls as tools/portraits/generate.py) ----------

def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_json(path: str) -> dict:
    with urllib.request.urlopen(COMFY + path, timeout=30) as resp:
        return json.loads(resp.read())


def ksampler(seed: int, steps: int, denoise: float, latent: list) -> dict:
    return {"class_type": "KSampler", "inputs": {
        "seed": seed, "steps": steps, "cfg": 5, "sampler_name": "euler_ancestral", "scheduler": "normal",
        "denoise": denoise, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": latent}}


def workflow(prompt: str, seed: int, prefix: str) -> dict:
    """txt2img 1344x768, then upscale to 1920x1088 and resample lightly (hires fix)."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
        "5": ksampler(seed, 28, 1.0, ["4", 0]),
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "ImageScale", "inputs": {"image": ["6", 0], "upscale_method": "lanczos",
                                                      "width": 1920, "height": 1088, "crop": "disabled"}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["7", 0], "vae": ["1", 2]}},
        "9": ksampler(seed + 1, 20, 0.38, ["8", 0]),
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["10", 0]}},
    }


def run(wf: dict) -> tuple[Image.Image, float]:
    t0 = time.monotonic()
    prompt_id = post_json("/prompt", {"prompt": wf, "client_id": "explainer-backgrounds"})["prompt_id"]
    deadline = time.monotonic() + 900
    entry = None
    while time.monotonic() < deadline:
        history = get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            break
        time.sleep(0.5)
    if entry is None:
        raise SystemExit("timed out waiting for ComfyUI")
    if entry.get("status", {}).get("status_str") != "success":
        raise SystemExit(f"generation failed: {json.dumps(entry.get('status'), indent=2)}")
    image = [img for out in entry["outputs"].values() for img in out.get("images", [])][-1]
    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image["subfolder"],
                                    "type": image["type"]})
    with urllib.request.urlopen(f"{COMFY}/view?{query}", timeout=60) as resp:
        pil = Image.open(io.BytesIO(resp.read())).convert("RGB")
    return pil, time.monotonic() - t0


def finish(img: Image.Image) -> Image.Image:
    """Centre-crop to exactly 1920x1080."""
    if img.size != (1920, 1088):
        img = img.resize((1920, 1088), Image.LANCZOS)
    return img.crop((0, 4, 1920, 1084))


def save_small(img: Image.Image, path: Path) -> int:
    """PNG under MAX_BYTES: full size if it fits, else stepped down (the stage scales it back up)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for width in (1920, 1760, 1600, 1440):
        out = img if width == 1920 else img.resize((width, round(width * 9 / 16)), Image.LANCZOS)
        out.save(path, optimize=True)
        if path.stat().st_size <= MAX_BYTES:
            return width
    return width


def load_index() -> dict:
    return json.loads(INDEX.read_text("utf-8")) if INDEX.exists() else {"places": {}}


def save_index(data: dict) -> None:
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(data, indent=2), encoding="utf-8")


def grid(place: str, tiles: list[tuple[int, Image.Image]]) -> None:
    w = 640
    h = round(w * 9 / 16)
    sheet = Image.new("RGB", (w * len(tiles), h + 28), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (seed, img) in enumerate(tiles):
        sheet.paste(img.resize((w, h), Image.LANCZOS), (i * w, 28))
        draw.text((i * w + 8, 8), f"{place} seed {seed}", fill="black")
    sheet.save(CANDIDATES / f"{place}_grid.png")


def cmd_candidates(places: list[str], seeds: list[int]) -> None:
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    for place in places:
        tiles = []
        for seed in seeds:
            img, secs = run(workflow(prompt_for(place), seed, f"offerletter-explainer/{place}_{seed}"))
            img = finish(img)
            img.save(CANDIDATES / f"{place}_{seed}.png")
            tiles.append((seed, img))
            print(f"  {place} seed {seed}: {secs:.1f}s", flush=True)
        grid(place, tiles)
        print(f"{place}: grid at {CANDIDATES / (place + '_grid.png')}", flush=True)


def cmd_pick(choices: list[str]) -> None:
    data = load_index()
    for item in choices:
        place, seed_text = item.split("=")
        seed = int(seed_text)
        src = CANDIDATES / f"{place}_{seed}.png"
        if not src.exists():
            raise SystemExit(f"no candidate {src}; run `candidates` first")
        width = save_small(Image.open(src).convert("RGB"), OUT / f"{place}.png")
        data["places"][place] = {"seed": seed, "prompt": prompt_for(place), "negative": NEGATIVE,
                                 "size": [width, round(width * 9 / 16)], "checkpoint": CHECKPOINT,
                                 "pass1": "1344x768, 28 steps, cfg 5, euler_ancestral",
                                 "pass2": "lanczos to 1920x1088, 20 steps, denoise 0.38, seed+1"}
        print(f"{place}: seed {seed} -> {OUT / (place + '.png')} ({(OUT / (place + '.png')).stat().st_size // 1024} KB)")
    save_index(data)


def cmd_all() -> None:
    data = load_index()
    for place, info in data["places"].items():
        img, secs = run(workflow(info["prompt"], info["seed"], f"offerletter-explainer/{place}_{info['seed']}"))
        width = save_small(finish(img), OUT / f"{place}.png")
        print(f"{place}: {secs:.1f}s, saved at {width} px wide")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--places", nargs="*", default=list(PLACES))
    c.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    p = sub.add_parser("pick")
    p.add_argument("choices", nargs="+", help="place=seed")
    sub.add_parser("all")
    args = ap.parse_args()
    try:
        get_json("/system_stats")
    except OSError:
        sys.exit("ComfyUI is not running on 127.0.0.1:8188 (see the docstring for the start command)")
    if args.cmd == "candidates":
        cmd_candidates(args.places, args.seeds)
    elif args.cmd == "pick":
        cmd_pick(args.choices)
    else:
        cmd_all()


if __name__ == "__main__":
    main()
