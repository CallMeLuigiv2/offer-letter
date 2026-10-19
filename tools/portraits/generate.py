"""Kilnworks cast portrait pipeline (spike S7), driven through the ComfyUI HTTP API.

Stages, run in order, each with its own subcommand:

    base    4 txt2img seeds per character; grids for picking one
    pick    record the chosen seed per character (cast_prompts.json, base.png)
    masks   find the face box (lbpcascade_animeface) and write face/mouth masks
    expr    inpaint only the face mask for each expression, composite onto base
    talk    inpaint only the mouth mask for each expression -> <expr>_talk
    sheets  downscale to 512 px into content/, build contact sheets

Run with the ComfyUI venv (it has torch-free deps: cv2, Pillow, numpy):

    C:\\Users\\Owner\\tools\\ComfyUI\\.venv\\Scripts\\python.exe generate.py base
"""

import argparse
import glob
import io
import json
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(r"C:\Users\Owner\projects\offer-letter")
PORTRAITS = ROOT / "tools" / "portraits"
CONTENT = ROOT / "content" / "companies" / "kilnworks" / "portraits"
COMFY_DIR = Path(r"C:\Users\Owner\tools\ComfyUI")
COMFY_OUT = COMFY_DIR / "output" / "offerletter"
COMFY_IN = COMFY_DIR / "input" / "offerletter"
COMFY = "http://127.0.0.1:8188"
CHECKPOINT = "animagine-xl-4.0.safetensors"
CASCADE = PORTRAITS / "lbpcascade_animeface.xml"
PROMPTS = PORTRAITS / "cast_prompts.json"
TIMINGS = PORTRAITS / "timings.json"
MASKS = PORTRAITS / "masks"
DEBUG = PORTRAITS / "debug"
GRIDS = PORTRAITS / "grids"

CHAR_IDS = ["dana", "kenji", "ines", "theo", "amara", "leo"]
SEEDS = [1001, 1002, 1003, 1004]

STYLE = (
    "anime, visual novel, anime coloring, bust, upper body, portrait, "
    "looking at viewer, simple background, white background, soft studio lighting"
)
QUALITY = "masterpiece, high score, great score, absurdres, safe"
NEUTRAL = "closed mouth, light smile"
TALK = "open mouth, talking"
EXPRESSIONS = {
    "happy": "smile, happy",
    "skeptical": "raised eyebrow, frown, narrowed eyes",
    "thinking": "thinking, looking to the side, hand not visible, pursed lips",
    "concerned": "worried, furrowed brow, frown",
    "surprised": "surprised, wide-eyed, open mouth",
    "laughing": "laughing, open mouth, closed eyes",
}
EXPR_ORDER = ["neutral"] + list(EXPRESSIONS)

# Card negative prompt from cagliostrolab/animagine-xl-4.0 (widget version), plus SFW guards.
CARD_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, low score, bad score, "
    "average score, signature, watermark, username, blurry"
)
NEGATIVE = CARD_NEGATIVE + ", nsfw, cleavage, revealing clothes"
# Per-character negatives: stop the model drifting back to its default look.
EXTRA_NEGATIVE = {
    "amara": "light skin, pale skin, blonde hair, brown hair, large breasts, cleavage",
}


def negative_for(cid: str) -> str:
    extra = EXTRA_NEGATIVE.get(cid)
    return f"{NEGATIVE}, {extra}" if extra else NEGATIVE

CHARS = {
    "dana": (
        "1girl, solo, mature female, adult woman, middle-aged, early 40s, "
        "black hair, streaked hair, white streak, grey streak, multicolored hair, "
        "short hair, round eyewear, brown-framed eyewear, olive cardigan, white t-shirt"
    ),
    "kenji": (
        "1boy, solo, male focus, mature male, adult, mid 30s, black hair, undercut, "
        "headphones around neck, charcoal hoodie, grey hoodie"
    ),
    "ines": (
        "1girl, solo, adult, late 20s, long hair, red hair, dark red hair, low ponytail, "
        "freckles, green flannel shirt, plaid shirt"
    ),
    "theo": (
        "1boy, solo, male focus, young man, early 20s, messy hair, blond hair, "
        "oversized mustard t-shirt, one earbud, wireless earbuds"
    ),
    "amara": (
        "1girl, solo, dark skin, dark-skinned female, black hair, box braids, "
        "braided bun, high bun, hoop earrings, gold earrings, mustard blazer, "
        "white shirt, mature female, upper body, looking at viewer"
    ),
    "leo": (
        "1boy, solo, male focus, young, 20 years old, black hair, bowl cut, "
        "blue lanyard, backpack, backpack strap"
    ),
}


def prompt_for(cid: str, expression_tags: str) -> str:
    """Model-card order: subject, style, expression, quality tags last."""
    return f"{CHARS[cid]}, {STYLE}, {expression_tags}, {QUALITY}"


def expression_prompt(cid: str, expr: str) -> str:
    if expr == "neutral":
        return prompt_for(cid, NEUTRAL)
    return prompt_for(cid, EXPRESSIONS[expr])


# ---------- ComfyUI API helpers ----------

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


def ksampler(seed, denoise, model, positive, negative, latent):
    return {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": 28,
            "cfg": 5,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": denoise,
            "model": model,
            "positive": positive,
            "negative": negative,
            "latent_image": latent,
        },
    }


def txt2img_workflow(prompt: str, negative: str, seed: int, prefix: str) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": ksampler(seed, 1, ["1", 0], ["2", 0], ["3", 0], ["4", 0]),
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["6", 0]}},
    }


def inpaint_workflow(image: str, mask: str, prompt: str, negative: str, seed: int, denoise: float, prefix: str) -> dict:
    """Load image + mask from ComfyUI's input folder, noise-mask the latent, resample."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image}},
        "3": {"class_type": "LoadImage", "inputs": {"image": mask}},
        "4": {"class_type": "ImageToMask", "inputs": {"image": ["3", 0], "channel": "red"}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "6": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["5", 0], "mask": ["4", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "9": ksampler(seed, denoise, ["1", 0], ["7", 0], ["8", 0], ["6", 0]),
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["10", 0]}},
    }


def run(workflow: dict) -> tuple[Image.Image, float]:
    """Queue a workflow, wait for it, return the first output image and wall seconds."""
    t0 = time.monotonic()
    queued = post_json("/prompt", {"prompt": workflow, "client_id": "portraits-pipeline"})
    prompt_id = queued["prompt_id"]
    deadline = time.monotonic() + 900
    entry = None
    while time.monotonic() < deadline:
        history = get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            break
        time.sleep(0.5)
    seconds = time.monotonic() - t0
    if entry is None:
        raise SystemExit("timed out waiting for /history")
    status = entry.get("status", {})
    if status.get("status_str") != "success":
        raise SystemExit(f"generation failed: {json.dumps(status, indent=2)}")
    image = None
    for node_output in entry["outputs"].values():
        for img in node_output.get("images", []):
            image = img
    query = urllib.parse.urlencode(
        {"filename": image["filename"], "subfolder": image["subfolder"], "type": image["type"]}
    )
    with urllib.request.urlopen(f"{COMFY}/view?{query}", timeout=60) as resp:
        pil = Image.open(io.BytesIO(resp.read())).convert("RGB")
    return pil, seconds


class VramSampler:
    """Samples whole-GPU memory.used with nvidia-smi on a background thread."""

    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.peak_mib = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @staticmethod
    def _read_mib() -> int:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True,
        ).stdout
        return int(out.strip().splitlines()[0])

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak_mib = max(self.peak_mib, self._read_mib())
            self._stop.wait(self.interval)

    def __enter__(self):
        self.peak_mib = self._read_mib()
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


def log_stage(name: str, seconds: float, peak_mib: int, gens: int) -> None:
    entries = json.loads(TIMINGS.read_text(encoding="utf-8")) if TIMINGS.exists() else []
    entries.append({
        "stage": name,
        "started": datetime.now().isoformat(timespec="seconds"),
        "seconds": round(seconds, 1),
        "generations": gens,
        "peak_gpu_mib_whole_gpu": peak_mib,
    })
    TIMINGS.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"[{name}] {seconds:.1f}s, {gens} generations, peak {peak_mib} MiB")


def load_prompts() -> dict:
    return json.loads(PROMPTS.read_text(encoding="utf-8")) if PROMPTS.exists() else {}


def save_prompts(data: dict) -> None:
    PROMPTS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


# ---------- stages ----------

def make_grid(tiles: list[tuple[int, Image.Image]], tile_w: int = 416, per_row: int = 3) -> Image.Image:
    """Seeds in rows of three, each labelled, so one view shows every candidate."""
    tiles_resized = []
    for seed, img in tiles:
        h = round(img.height * tile_w / img.width)
        tiles_resized.append((seed, img.resize((tile_w, h), Image.LANCZOS)))
    h = tiles_resized[0][1].height
    rows = -(-len(tiles_resized) // per_row)
    sheet = Image.new("RGB", (tile_w * min(per_row, len(tiles_resized)), rows * (h + 28)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (seed, img) in enumerate(tiles_resized):
        x, y = (i % per_row) * tile_w, (i // per_row) * (h + 28)
        sheet.paste(img, (x, y + 28))
        draw.text((x + 8, y + 8), f"seed {seed}", fill="black")
    return sheet


def stage_base(chars: list[str], seeds: list[int]) -> None:
    ensure_dirs(GRIDS)
    gens = 0
    with VramSampler() as vram:
        t0 = time.monotonic()
        for cid in chars:
            tiles = []
            for seed in seeds:
                wf = txt2img_workflow(
                    expression_prompt(cid, "neutral"), negative_for(cid), seed, f"offerletter/{cid}/seed_{seed}",
                )
                img, secs = run(wf)
                gens += 1
                print(f"  {cid} seed {seed}: {secs:.1f}s")
                tiles.append((seed, img))
            make_grid(tiles).save(GRIDS / f"{cid}_seeds.png")
        total = time.monotonic() - t0
    log_stage("base", total, vram.peak_mib, gens)


def stage_pick(choices: list[str]) -> None:
    data = load_prompts()
    for item in choices:
        cid, seed_text = item.split("=")
        seed = int(seed_text)
        matches = sorted(glob.glob(str(COMFY_OUT / cid / f"seed_{seed}_*.png")))
        if not matches:
            raise SystemExit(f"no output for {cid} seed {seed}")
        base = Image.open(matches[-1]).convert("RGB")
        base.save(COMFY_OUT / cid / "base.png")
        data[cid] = {
            "seed": seed,
            "base_prompt": expression_prompt(cid, "neutral"),
            "negative": negative_for(cid),
            "expression_tags": EXPRESSIONS,
            "talk_tags": TALK,
            "neutral_tags": NEUTRAL,
        }
        print(f"picked {cid} seed {seed} from {matches[-1]}")
    save_prompts(data)


def ellipse(size, cx, cy, rx, ry, blur) -> Image.Image:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))


def detect_face_box(base: Image.Image) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(np.array(base), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(str(CASCADE))
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return int(x), int(y), int(w), int(h)


def stage_masks(chars: list[str]) -> None:
    data = load_prompts()
    ensure_dirs(MASKS, DEBUG)
    for cid in chars:
        base = Image.open(COMFY_OUT / cid / "base.png").convert("RGB")
        size = base.size
        box = data.get(cid, {}).get("face_box")
        source = "manual override" if box else "lbpcascade_animeface"
        if box is None:
            found = detect_face_box(base)
            if found is None:
                raise SystemExit(f"{cid}: no face detected; set face_box in cast_prompts.json")
            box = list(found)
        x, y, w, h = box
        cx = x + w / 2
        # Face: ellipse grown ~15% around the detected box.
        face = ellipse(size, cx, y + h / 2, w / 2 * 1.15, h / 2 * 1.15, max(4, 0.04 * w))
        # Mouth: low on the box, narrower. Centre at 0.74h, not the lower-30% middle,
        # because the cascade box runs down past the chin (Dana's mouth sits at ~0.68h).
        mouth = ellipse(size, cx, y + 0.74 * h, 0.18 * w, 0.13 * h, max(3, 0.02 * w))
        face.save(MASKS / f"{cid}_face.png")
        mouth.save(MASKS / f"{cid}_mouth.png")
        # Debug overlay: face in red, mouth in blue, plus the raw box in green.
        overlay = base.copy()
        overlay = Image.composite(Image.new("RGB", size, (255, 0, 0)), overlay, face.point(lambda v: v // 3))
        overlay = Image.composite(Image.new("RGB", size, (0, 80, 255)), overlay, mouth.point(lambda v: v // 2))
        ImageDraw.Draw(overlay).rectangle([x, y, x + w, y + h], outline=(0, 200, 0), width=4)
        overlay.resize((416, 608), Image.LANCZOS).save(DEBUG / f"{cid}_masks.png")
        data.setdefault(cid, {})["face_box"] = box
        print(f"{cid}: box {box} ({source})")
    save_prompts(data)


def stage_expr(chars: list[str], exprs: list[str], denoise: float) -> None:
    data = load_prompts()
    ensure_dirs(COMFY_IN, COMFY_OUT)
    gens = 0
    with VramSampler() as vram:
        t0 = time.monotonic()
        for cid in chars:
            d = COMFY_IN / cid
            ensure_dirs(d, COMFY_OUT / cid)
            base = Image.open(COMFY_OUT / cid / "base.png").convert("RGB")
            face = Image.open(MASKS / f"{cid}_face.png").convert("L")
            base.save(d / "base.png")
            face.convert("RGB").save(d / "face_mask.png")
            base.save(COMFY_OUT / cid / "neutral.png")
            base.save(d / "neutral.png")
            for expr in exprs:
                prompt = prompt_for(cid, EXPRESSIONS[expr])
                wf = inpaint_workflow(
                    f"offerletter/{cid}/base.png", f"offerletter/{cid}/face_mask.png",
                    prompt, negative_for(cid), data[cid]["seed"], denoise, f"offerletter/{cid}/raw_{expr}",
                )
                gen, secs = run(wf)
                gens += 1
                comp = Image.composite(gen, base, face)
                comp.save(COMFY_OUT / cid / f"{expr}.png")
                comp.save(d / f"{expr}.png")
                print(f"  {cid} {expr}: {secs:.1f}s")
            data[cid]["expression_tags"] = EXPRESSIONS
        total = time.monotonic() - t0
    save_prompts(data)
    log_stage(f"expr {','.join(exprs)} @denoise {denoise}", total, vram.peak_mib, gens)


def stage_talk(chars: list[str], exprs: list[str]) -> None:
    data = load_prompts()
    gens = 0
    with VramSampler() as vram:
        t0 = time.monotonic()
        for cid in chars:
            d = COMFY_IN / cid
            mouth_img = Image.open(MASKS / f"{cid}_mouth.png").convert("L")
            mouth_img.convert("RGB").save(d / "mouth_mask.png")
            for expr in exprs:
                src = Image.open(COMFY_OUT / cid / f"{expr}.png").convert("RGB")
                wf = inpaint_workflow(
                    f"offerletter/{cid}/{expr}.png", f"offerletter/{cid}/mouth_mask.png",
                    prompt_for(cid, TALK), negative_for(cid), data[cid]["seed"], 0.45,
                    f"offerletter/{cid}/raw_{expr}_talk",
                )
                gen, secs = run(wf)
                gens += 1
                comp = Image.composite(gen, src, mouth_img)
                comp.save(COMFY_OUT / cid / f"{expr}_talk.png")
                print(f"  {cid} {expr}_talk: {secs:.1f}s")
        total = time.monotonic() - t0
    log_stage("talk", total, vram.peak_mib, gens)


def stage_sheets(chars: list[str]) -> None:
    thumb_w = 256
    for cid in chars:
        out_dir = CONTENT / cid
        ensure_dirs(out_dir)
        thumbs = []
        for expr in EXPR_ORDER:
            for suffix in ("", "_talk"):
                name = f"{expr}{suffix}"
                full = Image.open(COMFY_OUT / cid / f"{name}.png").convert("RGB")
                small = full.resize((512, round(full.height * 512 / full.width)), Image.LANCZOS)
                small.save(out_dir / f"{name}.webp", "WEBP", quality=85, method=6)
                thumbs.append((name, small.resize((thumb_w, round(small.height * thumb_w / small.width)), Image.LANCZOS)))
        h = thumbs[0][1].height
        cols = len(EXPR_ORDER)
        sheet = Image.new("RGB", (cols * thumb_w, 2 * (h + 24)), "white")
        draw = ImageDraw.Draw(sheet)
        # thumbs alternate expr, expr_talk: row 0 = plain, row 1 = talking.
        for i, (name, img) in enumerate(thumbs):
            col, row = i // 2, i % 2
            x, y = col * thumb_w, row * (h + 24)
            sheet.paste(img, (x, y + 24))
            draw.text((x + 6, y + 6), name, fill="black")
        sheet.save(out_dir / "contact_sheet.png")
        print(f"{cid}: {out_dir / 'contact_sheet.png'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="stage", required=True)

    p_base = sub.add_parser("base")
    p_base.add_argument("--chars", nargs="*", default=CHAR_IDS)
    p_base.add_argument("--seeds", nargs="*", type=int, default=SEEDS)

    p_pick = sub.add_parser("pick")
    p_pick.add_argument("choices", nargs="+", help="cid=seed, e.g. dana=1002")

    p_masks = sub.add_parser("masks")
    p_masks.add_argument("--chars", nargs="*", default=CHAR_IDS)

    p_expr = sub.add_parser("expr")
    p_expr.add_argument("--chars", nargs="*", default=CHAR_IDS)
    p_expr.add_argument("--exprs", nargs="*", default=list(EXPRESSIONS), choices=list(EXPRESSIONS))
    p_expr.add_argument("--denoise", type=float, default=0.55)

    p_talk = sub.add_parser("talk")
    p_talk.add_argument("--chars", nargs="*", default=CHAR_IDS)
    p_talk.add_argument("--exprs", nargs="*", default=EXPR_ORDER, choices=EXPR_ORDER)

    p_sheets = sub.add_parser("sheets")
    p_sheets.add_argument("--chars", nargs="*", default=CHAR_IDS)

    args = parser.parse_args()
    if args.stage == "base":
        stage_base(args.chars, args.seeds)
    elif args.stage == "pick":
        stage_pick(args.choices)
    elif args.stage == "masks":
        stage_masks(args.chars)
    elif args.stage == "expr":
        stage_expr(args.chars, args.exprs, args.denoise)
    elif args.stage == "talk":
        stage_talk(args.chars, args.exprs)
    elif args.stage == "sheets":
        stage_sheets(args.chars)


if __name__ == "__main__":
    main()
