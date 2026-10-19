"""The built web app is a single-page app: page routes fall back to index.html, misses elsewhere stay 404."""

from __future__ import annotations

import dataclasses
import random
from pathlib import Path

from fastapi.testclient import TestClient

from offerletter.app import create_app
from offerletter.config import Settings
from offerletter.teammates.runner import FakeRunner


def test_page_routes_fall_back_to_the_app_but_api_and_asset_misses_stay_404(settings: Settings, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Offer Letter</title>", encoding="utf-8")
    office = tmp_path / "office"
    office.mkdir()
    (office / "tileset.png").write_bytes(b"\x89PNG")
    app = create_app(dataclasses.replace(settings, web_dist=dist, office_dir=office),
                     runner=FakeRunner(), rng=random.Random(1))
    with TestClient(app) as c:
        for page in ("/", "/tickets", "/tickets/KLN-01", "/office", "/channels/kilnworks.serving"):
            r = c.get(page)
            assert r.status_code == 200, page
            assert "Offer Letter" in r.text, page
        assert c.get("/office/tileset.png").status_code == 200
        for miss in ("/api/nope", "/office/missing.png", "/portraits/kilnworks/theo/nope.webp"):
            r = c.get(miss)
            assert r.status_code == 404, miss
            assert r.headers["content-type"].startswith("application/json"), miss
