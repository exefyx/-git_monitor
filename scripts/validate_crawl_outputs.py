# -*- coding: utf-8 -*-
"""
Validate crawler outputs before building the dashboard.

This catches blocked/empty runs so they do not overwrite the dashboard or
sync false removals into Feishu.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAND_PAGE = "\u54c1\u724c\u9875"

TARGET_BRANDS = [
    "TrainPal",
    "Trip.com",
    "Trainline",
    "Omio",
    "Klook",
    "National Express",
    "FlixBus",
    "Eurostar",
]

SOURCES = {
    "UNiDAYS": {
        "folder": ROOT / "unidays_outputs",
        "brands": TARGET_BRANDS,
        "min_brand_page_offers": 10,
    },
    "Student Beans": {
        "folder": ROOT / "studentbeans_outputs",
        "brands": [brand for brand in TARGET_BRANDS if brand != "Eurostar"],
        "min_brand_page_offers": 10,
    },
}

BLOCKED_MARKERS = [
    "403 ERROR",
    "The request could not be satisfied",
    "Request blocked",
    "security checks have blocked this request",
    "CloudFront",
]


def compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def latest_clean_file(folder: Path) -> Path | None:
    files = sorted(folder.glob("clean_offers_*.json"))
    return files[-1] if files else None


def date_from_file(path: Path) -> str:
    return path.stem.replace("clean_offers_", "")


def read_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_block_markers(folder: Path, run_date: str) -> list[str]:
    debug_dir = folder / f"debug_{run_date}"
    if not debug_dir.exists():
        return []

    hits: list[str] = []
    for path in debug_dir.glob("*_body.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in BLOCKED_MARKERS:
            if marker.lower() in text.lower():
                hits.append(f"{path.name}: {marker}")
                break
    return hits


def validate_source(name: str, config: dict) -> bool:
    folder: Path = config["folder"]
    current = latest_clean_file(folder)
    if not current:
        print(f"[FAIL] {name}: no clean_offers file found")
        return False

    run_date = date_from_file(current)
    rows = read_rows(current)
    target_keys = {compact_text(brand) for brand in config["brands"]}
    target_brand_rows = [
        row
        for row in rows
        if str(row.get("source_type", "")).strip() == BRAND_PAGE
        and compact_text(row.get("brand", "")) in target_keys
    ]

    print(
        f"[CHECK] {name} {run_date}: total={len(rows)}, "
        f"target_brand_page={len(target_brand_rows)}"
    )

    blocked_hits = find_block_markers(folder, run_date)
    for hit in blocked_hits[:5]:
        print(f"[BLOCKED] {name}: {hit}")

    if len(target_brand_rows) < config["min_brand_page_offers"]:
        print(
            f"[FAIL] {name}: target brand-page offers below threshold "
            f"({len(target_brand_rows)} < {config['min_brand_page_offers']})"
        )
        return False

    if blocked_hits:
        print(f"[FAIL] {name}: blocked-page markers found in debug body text")
        return False

    return True


def main() -> None:
    ok = True
    for name, config in SOURCES.items():
        ok = validate_source(name, config) and ok

    if not ok:
        print("Crawler output validation failed. Skip dashboard/Feishu updates.")
        sys.exit(1)

    print("Crawler output validation passed.")


if __name__ == "__main__":
    main()
