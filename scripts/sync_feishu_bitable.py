# -*- coding: utf-8 -*-
"""
Sync daily student-offer snapshots into Feishu Bitable.

Reads:
- unidays_outputs/clean_offers_YYYY-MM-DD.json
- studentbeans_outputs/clean_offers_YYYY-MM-DD.json

Writes:
- OfferRecords: one row per full snapshot offer, plus daily new/removed rows
- DailyRuns: one summary row per platform per run

Required environment variables for live sync:
- FEISHU_APP_ID
- FEISHU_APP_SECRET
- FEISHU_BITABLE_APP_TOKEN
- FEISHU_OFFER_TABLE_ID
- FEISHU_RUN_TABLE_ID
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_URL = "https://exefyx.github.io/-git_monitor/"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
BATCH_SIZE = 1000

SOURCES = {
    "UNiDAYS": ROOT / "unidays_outputs",
    "Student Beans": ROOT / "studentbeans_outputs",
}

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


def compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


TARGET_BRAND_KEYS = {compact_text(brand) for brand in TARGET_BRANDS}


def is_target_brand(brand: str) -> bool:
    return compact_text(brand) in TARGET_BRAND_KEYS


def clean_files(folder: Path) -> list[Path]:
    return sorted(folder.glob("clean_offers_*.json"))


def date_from_file(path: Path) -> str:
    return path.stem.replace("clean_offers_", "")


def latest_clean_file(folder: Path) -> Path | None:
    files = clean_files(folder)
    return files[-1] if files else None


def clean_file_for_date(folder: Path, run_date: str | None) -> Path | None:
    if run_date:
        path = folder / f"clean_offers_{run_date}.json"
        return path if path.exists() else None
    return latest_clean_file(folder)


def previous_file(folder: Path, current: Path | None) -> Path | None:
    if not current:
        return None
    files = [path for path in clean_files(folder) if path < current]
    return files[-1] if files else None


def read_rows(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def row_key(row: dict) -> str:
    parts = (
        str(row.get("source_type", "")),
        str(row.get("page", "")),
        str(row.get("brand", "")),
        " ".join(str(row.get("offer", "")).lower().split()),
    )
    return "|".join(parts)


def filter_diff_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if is_target_brand(str(row.get("brand", "")).strip())]


def make_diff(folder: Path, current: Path | None, rows: list[dict]) -> dict[str, list[dict]]:
    previous = previous_file(folder, current)
    if not previous:
        return {"new": [], "removed": []}

    old_rows = filter_diff_rows(read_rows(previous))
    today_rows = filter_diff_rows(rows)

    old_map = {row_key(row): row for row in old_rows}
    today_map = {row_key(row): row for row in today_rows}

    old_keys = set(old_map)
    today_keys = set(today_map)

    return {
        "new": [today_map[key] for key in sorted(today_keys - old_keys)],
        "removed": [old_map[key] for key in sorted(old_keys - today_keys)],
    }


def offer_record_fields(
    *,
    platform: str,
    record_type: str,
    run_date: str,
    run_id: str,
    synced_at: str,
    row: dict,
) -> dict:
    return {
        "日期": run_date,
        "平台": platform,
        "记录类型": record_type,
        "来源类型": str(row.get("source_type", "")),
        "页面": str(row.get("page", "")),
        "区块": str(row.get("section", "")),
        "品牌": str(row.get("brand", "")),
        "Offer": str(row.get("offer", "")),
        "产品线": str(row.get("product_type", "")),
        "RowKey": row_key(row),
        "Dashboard URL": DASHBOARD_URL,
        "Run ID": run_id,
        "写入时间": synced_at,
    }


def read_report_summary(folder: Path, run_date: str) -> str:
    report = folder / f"daily_report_{run_date}.md"
    if not report.exists():
        return ""
    text = report.read_text(encoding="utf-8").strip()
    return text[:3000]


def source_type_counts(rows: list[dict]) -> tuple[int, int]:
    page_count = sum(1 for row in rows if str(row.get("source_type", "")) == "页面")
    brand_count = sum(1 for row in rows if str(row.get("source_type", "")) == "品牌页")
    return page_count, brand_count


def run_record_fields(
    *,
    platform: str,
    folder: Path,
    run_date: str,
    run_id: str,
    rows: list[dict],
    diff: dict[str, list[dict]],
) -> dict:
    page_count, brand_count = source_type_counts(rows)
    return {
        "日期": run_date,
        "平台": platform,
        "全量数量": len(rows),
        "页面Offer数量": page_count,
        "品牌页Offer数量": brand_count,
        "新增数量": len(diff["new"]),
        "下线数量": len(diff["removed"]),
        "Dashboard URL": DASHBOARD_URL,
        "日报摘要": read_report_summary(folder, run_date),
        "同步状态": "成功",
        "Run ID": run_id,
    }


def batched(items: list[dict], size: int = BATCH_SIZE) -> Iterable[list[dict]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_tenant_access_token() -> str:
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": get_required_env("FEISHU_APP_ID"),
        "app_secret": get_required_env("FEISHU_APP_SECRET"),
    }
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Failed to get Feishu tenant token: {data}")
    return data["tenant_access_token"]


def batch_create_records(
    *,
    token: str,
    app_token: str,
    table_id: str,
    fields_list: list[dict],
) -> None:
    if not fields_list:
        return

    url = (
        f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}"
        f"/tables/{table_id}/records/batch_create"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    for batch in batched(fields_list):
        payload = {"records": [{"fields": fields} for fields in batch]}
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to create Feishu records: {data}")


def prepare_payload(run_date: str | None) -> tuple[str, list[dict], list[dict]]:
    synced_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    effective_dates: list[str] = []
    offer_records: list[dict] = []
    run_records: list[dict] = []

    for platform, folder in SOURCES.items():
        current = clean_file_for_date(folder, run_date)
        if not current:
            print(f"No clean offer file found for {platform}, skip.")
            continue

        current_date = date_from_file(current)
        effective_dates.append(current_date)
        rows = read_rows(current)
        diff = make_diff(folder, current, rows)
        run_id = f"{current_date}-{platform.replace(' ', '_')}-{synced_at}"

        offer_records.extend(
            offer_record_fields(
                platform=platform,
                record_type="全量",
                run_date=current_date,
                run_id=run_id,
                synced_at=synced_at,
                row=row,
            )
            for row in rows
        )
        offer_records.extend(
            offer_record_fields(
                platform=platform,
                record_type="新增",
                run_date=current_date,
                run_id=run_id,
                synced_at=synced_at,
                row=row,
            )
            for row in diff["new"]
        )
        offer_records.extend(
            offer_record_fields(
                platform=platform,
                record_type="下线",
                run_date=current_date,
                run_id=run_id,
                synced_at=synced_at,
                row=row,
            )
            for row in diff["removed"]
        )
        run_records.append(
            run_record_fields(
                platform=platform,
                folder=folder,
                run_date=current_date,
                run_id=run_id,
                rows=rows,
                diff=diff,
            )
        )

    if not effective_dates:
        raise RuntimeError("No clean offer files found to sync.")

    return max(effective_dates), offer_records, run_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        help="Sync a specific YYYY-MM-DD output. Defaults to the latest clean file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build payload and print counts without calling Feishu.",
    )
    args = parser.parse_args()

    run_date, offer_records, run_records = prepare_payload(args.date)

    print(f"Prepared Feishu payload for {run_date}:")
    print(f"- OfferRecords: {len(offer_records)}")
    print(f"- DailyRuns: {len(run_records)}")

    if args.dry_run:
        for item in run_records:
            print(
                f"- {item['平台']}: 全量 {item['全量数量']}, "
                f"新增 {item['新增数量']}, 下线 {item['下线数量']}"
            )
        return

    app_token = get_required_env("FEISHU_BITABLE_APP_TOKEN")
    offer_table_id = get_required_env("FEISHU_OFFER_TABLE_ID")
    run_table_id = get_required_env("FEISHU_RUN_TABLE_ID")
    token = get_tenant_access_token()

    batch_create_records(
        token=token,
        app_token=app_token,
        table_id=offer_table_id,
        fields_list=offer_records,
    )
    batch_create_records(
        token=token,
        app_token=app_token,
        table_id=run_table_id,
        fields_list=run_records,
    )

    print("Feishu Bitable sync completed.")


if __name__ == "__main__":
    main()
