# Student Offer Daily Monitor

This repository hosts a static dashboard for daily student offer monitoring.

## Dashboard

The published dashboard is stored in:

```text
docs/index.html
```

Historical daily dashboards are stored as:

```text
docs/dashboard_YYYY-MM-DD.html
```

## Feishu Bitable Archive

The daily GitHub Actions run can also save every day's data into Feishu
Bitable for long-term search and filtering.

Create two Feishu Bitable tables with these fields:

```text
OfferRecords:
日期, 平台, 记录类型, 来源类型, 页面, 区块, 品牌, Offer, 产品线,
RowKey, Dashboard URL, Run ID, 写入时间

DailyRuns:
日期, 平台, 全量数量, 页面Offer数量, 品牌页Offer数量, 新增数量,
下线数量, Dashboard URL, 日报摘要, 同步状态, Run ID
```

Use an internal Feishu app, grant it Bitable API permissions, and add the app
to the Bitable document. Then configure these GitHub Actions secrets:

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_BITABLE_APP_TOKEN
FEISHU_OFFER_TABLE_ID
FEISHU_RUN_TABLE_ID
```

This repository defaults to the Lark Enterprise OpenAPI host because the
current Bitable URL is under `larkenterprise.com`. For a `feishu.cn` tenant, add
`FEISHU_API_BASE=https://open.feishu.cn/open-apis`.

Local dry run:

```bash
python scripts/sync_feishu_bitable.py --date 2026-06-02 --dry-run
```
