"""Regenerate every office asset, then validate the map.

    uv run --with pillow --with pytiled-parser python tools/pixel/build_all.py

Order matters: the map reads the tileset's tile names, and the contact
sheet reads everything.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["gen_tileset.py", "build_map.py", "gen_characters.py", "contact_sheet.py", "check_map.py"]

if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    for step in STEPS:
        print(f"== {step}")
        sys.argv = [str(HERE / step)]
        runpy.run_path(str(HERE / step), run_name="__main__")
