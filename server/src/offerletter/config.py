"""Paths and settings. Everything the server touches on disk is derived from one home directory."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HOME = Path(r"C:\Users\Owner\OfferLetter")


@dataclass
class Settings:
    """Runtime settings. Tests build one with a temp home and fast, in-process commands."""

    home: Path
    content_dir: Path
    port: int = 8765
    web_dist: Path | None = None
    office_dir: Path | None = None  # web/public/office, served at /office when running without Vite
    # tools/build_kit.py, used only when it exists and we serve the repo's own content
    build_kit_script: Path | None = None
    # how we run pytest for the hidden grader (Python repos only in v0.1)
    pytest_cmd: list[str] = field(default_factory=lambda: ["uv", "run", "--with", "pytest", "pytest"])
    gh_cmd: str = "gh"
    # scales teammate typing delays; 0 in tests
    delay_scale: float = 1.0
    command_timeout_s: float = 180.0
    # renders "your plan, played out" (ARCHITECTURE 9.2); the server appends --plan/--context/--out
    plan_video_cmd: list[str] = field(default_factory=lambda: [
        "uv", "run", "--project", str(REPO_ROOT / "tools" / "explainer"), "python", "-m", "explainer.plan_video"])
    plan_video_timeout_s: float = 360.0
    # tools/explainer isn't an installed package (uv `package = false`), so `-m explainer...` runs from its folder
    plan_video_cwd: Path = REPO_ROOT / "tools" / "explainer"

    @property
    def data_dir(self) -> Path:
        return self.home / ".data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "offerletter.db"

    @property
    def remotes_dir(self) -> Path:
        return self.data_dir / "remotes"

    @property
    def teammates_dir(self) -> Path:
        return self.data_dir / "teammates"

    @property
    def kits_dir(self) -> Path:
        return self.data_dir / "kits"

    @property
    def work_dir(self) -> Path:
        return self.home / "work"

    @classmethod
    def load(cls, home: Path | None = None, content: Path | None = None, port: int = 8765) -> Settings:
        home = Path(home or os.environ.get("OFFERLETTER_HOME") or DEFAULT_HOME)
        default_content = REPO_ROOT / "content"
        content_dir = Path(content or os.environ.get("OFFERLETTER_CONTENT") or default_content)
        script = REPO_ROOT / "tools" / "build_kit.py"
        use_script = script.exists() and content_dir.resolve() == default_content.resolve()
        dist = REPO_ROOT / "web" / "dist"
        return cls(
            home=home, content_dir=content_dir, port=port,
            web_dist=dist if dist.is_dir() else None,
            office_dir=(REPO_ROOT / "web" / "public" / "office") if (REPO_ROOT / "web" / "public" / "office").is_dir() else None,
            build_kit_script=script if use_script else None,
        )
