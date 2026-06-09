# -*- coding: utf-8 -*-
"""
Sync daily student-offer snapshots into Feishu Bitable.

Reads:
- unidays_outputs/clean_offers_YYYY-MM-DD.json
- studentbeans_outputs/clean_offers_YYYY-MM-DD.json

Writes:
- OfferRecords: one row per full snapshot offer, plus daily new/removed rows
- DailyRuns: one summary row per platform per run

Before writing, the script moves existing rows for the same date + platform
from the main Feishu tables into archive tables, then writes the latest rows
back to the main tables. This keeps the main tables current while preserving
each earlier same-day run as history.

Required environment variables for live sync:
- FEISHU_APP_ID
- FEISHU_APP_SECRET
- FEISHU_BITABLE_APP_TOKEN
- FEISHU_OFFER_TABLE_ID
- FEISHU_RUN_TABLE_ID

Optional environment variables:
- FEISHU_OFFER_ARCHIVE_TABLE_ID
- FEISHU_RUN_ARCHIVE_TABLE_ID

If the archive table IDs are not provided, the script will use or create
tables named OfferRecordsHistory and DailyRunsHistory in the same Bitable.
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
FEISHU_API_BASE = os.getenv(
    "FEISHU_API_BASE",
    "https://open.larkenterprise.com/open-apis",
).rstrip("/")
BATCH_SIZE = 1000
OFFER_ARCHIVE_TABLE_NAME = "OfferRecordsHistory"
RUN_ARCHIVE_TABLE_NAME = "DailyRunsHistory"

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


def feishu_date_value(value: str) -> int:
    dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def filter_diff_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if str(row.get("source_type", "")).strip() == "品牌页"
        and is_target_brand(str(row.get("brand", "")).strip())
    ]


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
        "日期": feishu_date_value(run_date),
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
        "日期": feishu_date_value(run_date),
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


def feishu_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def raise_for_feishu_error(response: requests.Response, action: str) -> dict:
    if response.status_code >= 400:
        print(response.text)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"{action} failed: {data}")
    return data


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
    headers = feishu_headers(token)

    for batch in batched(fields_list):
        payload = {"records": [{"fields": fields} for fields in batch]}
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        raise_for_feishu_error(response, "Create Feishu records")


def list_tables(
    *,
    token: str,
    app_token: str,
) -> list[dict]:
    url = f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}/tables"
    headers = feishu_headers(token)
    tables: list[dict] = []
    page_token = ""

    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        response = requests.get(url, headers=headers, params=params, timeout=60)
        data = raise_for_feishu_error(response, "List Feishu tables")
        page = data.get("data", {})
        tables.extend(page.get("items", []))

        if not page.get("has_more"):
            return tables
        page_token = page.get("page_token", "")
        if not page_token:
            return tables


def list_fields(
    *,
    token: str,
    app_token: str,
    table_id: str,
) -> list[dict]:
    url = (
        f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}"
        f"/tables/{table_id}/fields"
    )
    headers = feishu_headers(token)
    fields: list[dict] = []
    page_token = ""

    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        response = requests.get(url, headers=headers, params=params, timeout=60)
        data = raise_for_feishu_error(response, "List Feishu fields")
        page = data.get("data", {})
        fields.extend(page.get("items", []))

        if not page.get("has_more"):
            return fields
        page_token = page.get("page_token", "")
        if not page_token:
            return fields


def create_table_like(
    *,
    token: str,
    app_token: str,
    source_table_id: str,
    table_name: str,
) -> str:
    fields = []
    for field in list_fields(token=token, app_token=app_token, table_id=source_table_id):
        new_field = {
            "field_name": field["field_name"],
            "type": field["type"],
        }
        if "property" in field:
            new_field["property"] = field["property"]
        fields.append(new_field)

    url = f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}/tables"
    payload = {
        "table": {
            "name": table_name,
            "default_view_name": "Grid",
            "fields": fields,
        }
    }
    response = requests.post(
        url,
        headers=feishu_headers(token),
        json=payload,
        timeout=60,
    )
    data = raise_for_feishu_error(response, f"Create Feishu table {table_name}")
    result = data.get("data", {})
    table_id = result.get("table_id") or result.get("table", {}).get("table_id")
    if not table_id:
        raise RuntimeError(f"Create Feishu table returned no table_id: {data}")
    return table_id


def resolve_archive_table_id(
    *,
    token: str,
    app_token: str,
    source_table_id: str,
    table_name: str,
    configured_table_id: str | None,
) -> str:
    if configured_table_id:
        return configured_table_id

    for table in list_tables(token=token, app_token=app_token):
        if table.get("name") == table_name:
            table_id = table.get("table_id")
            if table_id:
                return table_id

    table_id = create_table_like(
        token=token,
        app_token=app_token,
        source_table_id=source_table_id,
        table_name=table_name,
    )
    print(f"Created Feishu archive table: {table_name}")
    return table_id


def list_records(
    *,
    token: str,
    app_token: str,
    table_id: str,
) -> list[dict]:
    url = (
        f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}"
        f"/tables/{table_id}/records"
    )
    headers = feishu_headers(token)
    records: list[dict] = []
    page_token = ""

    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        response = requests.get(url, headers=headers, params=params, timeout=60)
        data = raise_for_feishu_error(response, "List Feishu records")
        page = data.get("data", {})
        records.extend(page.get("items", []))

        if not page.get("has_more"):
            return records
        page_token = page.get("page_token", "")
        if not page_token:
            return records


def batch_delete_records(
    *,
    token: str,
    app_token: str,
    table_id: str,
    record_ids: list[str],
) -> None:
    if not record_ids:
        return

    url = (
        f"{FEISHU_API_BASE}/bitable/v1/apps/{app_token}"
        f"/tables/{table_id}/records/batch_delete"
    )
    headers = feishu_headers(token)

    for batch in batched(record_ids, 500):
        response = requests.post(
            url,
            headers=headers,
            json={"records": batch},
            timeout=60,
        )
        raise_for_feishu_error(response, "Delete Feishu records")


def normalize_feishu_date(value: object) -> str:
    if value in (None, ""):
        return ""

    if isinstance(value, (int, float)):
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    text = str(value).strip()
    if re.fullmatch(r"\d{13}", text):
        timestamp = int(text) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    return text[:10]


def existing_records_for_scope(
    *,
    token: str,
    app_token: str,
    table_id: str,
    scopes: set[tuple[str, str]],
) -> list[dict]:
    if not scopes:
        return []

    records: list[dict] = []
    for record in list_records(token=token, app_token=app_token, table_id=table_id):
        fields = record.get("fields", {})
        run_date = normalize_feishu_date(fields.get("日期"))
        platform = str(fields.get("平台", "")).strip()

        if (run_date, platform) in scopes:
            records.append(record)

    return records


def record_ids(records: list[dict]) -> list[str]:
    return [record["record_id"] for record in records if record.get("record_id")]


def field_type_map(fields: list[dict]) -> dict[str, int]:
    return {field["field_name"]: field["type"] for field in fields}


def normalize_archive_value(value: object, field_type: int | None) -> object:
    if value in (None, ""):
        return value

    if field_type == 2 and isinstance(value, str):
        text = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d+", text):
            return float(text)

    if field_type == 5 and isinstance(value, str):
        normalized = normalize_feishu_date(value)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            return feishu_date_value(normalized)

    return value


def record_fields(records: list[dict], field_types: dict[str, int]) -> list[dict]:
    normalized_records: list[dict] = []
    for record in records:
        fields = record.get("fields", {})
        if not fields:
            continue

        normalized_records.append(
            {
                name: normalize_archive_value(value, field_types.get(name))
                for name, value in fields.items()
            }
        )

    return normalized_records


def replace_records_for_scope(
    *,
    token: str,
    app_token: str,
    offer_table_id: str,
    run_table_id: str,
    offer_archive_table_id: str | None,
    run_archive_table_id: str | None,
    scopes: set[tuple[str, str]],
    offer_records: list[dict],
    run_records: list[dict],
) -> None:
    existing_offer_records = existing_records_for_scope(
        token=token,
        app_token=app_token,
        table_id=offer_table_id,
        scopes=scopes,
    )
    existing_run_records = existing_records_for_scope(
        token=token,
        app_token=app_token,
        table_id=run_table_id,
        scopes=scopes,
    )

    print(
        "Existing Feishu records for this date/platform: "
        f"OfferRecords={len(existing_offer_records)}, "
        f"DailyRuns={len(existing_run_records)}"
    )

    if existing_offer_records:
        offer_archive_field_types = field_type_map(
            list_fields(
                token=token,
                app_token=app_token,
                table_id=offer_archive_table_id,
            )
        )
        batch_create_records(
            token=token,
            app_token=app_token,
            table_id=offer_archive_table_id,
            fields_list=record_fields(existing_offer_records, offer_archive_field_types),
        )
    if existing_run_records:
        run_archive_field_types = field_type_map(
            list_fields(
                token=token,
                app_token=app_token,
                table_id=run_archive_table_id,
            )
        )
        batch_create_records(
            token=token,
            app_token=app_token,
            table_id=run_archive_table_id,
            fields_list=record_fields(existing_run_records, run_archive_field_types),
        )

    batch_delete_records(
        token=token,
        app_token=app_token,
        table_id=offer_table_id,
        record_ids=record_ids(existing_offer_records),
    )
    batch_delete_records(
        token=token,
        app_token=app_token,
        table_id=run_table_id,
        record_ids=record_ids(existing_run_records),
    )

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


def prepare_payload(run_date: str | None) -> tuple[str, list[dict], list[dict]]:
    synced_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    seen_dates: list[str] = []
    effective_dates: list[str] = []
    offer_records: list[dict] = []
    run_records: list[dict] = []

    for platform, folder in SOURCES.items():
        current = clean_file_for_date(folder, run_date)
        if not current:
            print(f"No clean offer file found for {platform}, skip.")
            continue

        current_date = date_from_file(current)
        seen_dates.append(current_date)
        rows = read_rows(current)
        if not rows:
            print(
                f"{platform} {current_date} clean offer file is empty; "
                "skip Feishu archive to avoid false diff records."
            )
            continue

        effective_dates.append(current_date)
        archive_rows = filter_diff_rows(rows)
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
            for row in archive_rows
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
                rows=archive_rows,
                diff=diff,
            )
        )

    if not effective_dates:
        if seen_dates:
            return max(seen_dates), [], []
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
    if not offer_records and not run_records:
        print("No non-empty clean offer files found; skip Feishu Bitable sync.")
        return

    if args.dry_run:
        for item in run_records:
            print(
                f"- {item['平台']}: 全量 {item['全量数量']}, "
                f"新增 {item['新增数量']}, 下线 {item['下线数量']}"
            )
        return

    try:
        app_token = get_required_env("FEISHU_BITABLE_APP_TOKEN")
        offer_table_id = get_required_env("FEISHU_OFFER_TABLE_ID")
        run_table_id = get_required_env("FEISHU_RUN_TABLE_ID")
        offer_archive_table_id = os.getenv("FEISHU_OFFER_ARCHIVE_TABLE_ID")
        run_archive_table_id = os.getenv("FEISHU_RUN_ARCHIVE_TABLE_ID")
        token = get_tenant_access_token()
        offer_archive_table_id = resolve_archive_table_id(
            token=token,
            app_token=app_token,
            source_table_id=offer_table_id,
            table_name=OFFER_ARCHIVE_TABLE_NAME,
            configured_table_id=offer_archive_table_id,
        )
        run_archive_table_id = resolve_archive_table_id(
            token=token,
            app_token=app_token,
            source_table_id=run_table_id,
            table_name=RUN_ARCHIVE_TABLE_NAME,
            configured_table_id=run_archive_table_id,
        )
        scopes = {
            (normalize_feishu_date(item["日期"]), str(item["平台"]).strip())
            for item in run_records
        }

        replace_records_for_scope(
            token=token,
            app_token=app_token,
            offer_table_id=offer_table_id,
            run_table_id=run_table_id,
            offer_archive_table_id=offer_archive_table_id,
            run_archive_table_id=run_archive_table_id,
            scopes=scopes,
            offer_records=offer_records,
            run_records=run_records,
        )
    except Exception as exc:
        print(f"Feishu Bitable sync skipped: {exc}")
        return

    print("Feishu Bitable sync completed.")


if __name__ == "__main__":
    main()
