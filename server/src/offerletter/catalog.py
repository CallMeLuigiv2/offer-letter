"""The company catalog: content/catalog.json merged with each pack's company.json when it exists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_KEYS = ("id", "name", "pitch", "domain", "stage", "stage_label", "culture", "stack",
                "ticket_count", "first_ticket", "kit_ready")


def load_company_json(content_dir: Path, slug: str) -> dict[str, Any] | None:
    path = content_dir / "companies" / slug / "company.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_catalog(content_dir: Path) -> list[dict[str, Any]]:
    """All catalog companies in file order. The pack's company.json wins over the catalog entry."""
    path = content_dir / "catalog.json"
    entries = json.loads(path.read_text(encoding="utf-8"))["companies"] if path.exists() else []
    out = []
    for entry in entries:
        merged = {**entry, **(load_company_json(content_dir, entry["id"]) or {})}
        item = {k: merged.get(k) for k in CATALOG_KEYS}
        item["stack"] = item["stack"] or []
        item["kit_ready"] = bool(item["kit_ready"])
        item["ticket_count"] = item["ticket_count"] or 0
        out.append(item)
    return out


def find_company(content_dir: Path, slug: str) -> dict[str, Any] | None:
    return next((c for c in load_catalog(content_dir) if c["id"] == slug), None)
