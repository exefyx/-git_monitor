# Student Offer Daily Monitor

这个仓库用于每天自动监测学生优惠网站上的交通/旅行类竞品 offer，并把结果发布到 GitHub Pages、发送飞书群通知，同时把品牌页数据归档到飞书多维表格，方便后续查询。

## 一键复制部署

别人可以通过下面入口一键生成自己的仓库：

[![Use this template](https://img.shields.io/badge/Use%20this%20template-GitHub-238636?style=for-the-badge&logo=github)](https://github.com/exefyx/-git_monitor/generate)

注意：这里的“一键部署”只能自动复制代码和 workflow，不能自动复制以下私密配置：

- GitHub Actions Secrets
- 飞书群机器人 webhook
- 飞书自建应用 App ID / App Secret
- 飞书多维表格 token / table id
- UNiDAYS / Student Beans 登录态
- 新仓库的 GitHub Pages 地址

所以别人点完 `Use this template` 后，还需要按“复制/接手这个仓库后如何配置”章节完成初始化。

当前监测两个平台：

- UNiDAYS
- Student Beans

当前目标品牌口径：

- UNiDAYS：TrainPal / Trip.com / Trainline / Omio / Klook / National Express / FlixBus / Eurostar
- Student Beans：TrainPal / Trip.com / Trainline / Omio / Klook / National Express / FlixBus

说明：Student Beans 当前不监测 Eurostar；UNiDAYS 的 dashboard 会固定显示 Eurostar，即使当天品牌页没有 offer，也会显示为空。

## 工作流概览

每天的 GitHub Actions 会按以下顺序运行：

```text
1. 安装 Python 依赖和 Playwright Chromium
2. 运行 UNiDAYS 爬虫
3. 运行 Student Beans 爬虫
4. 校验抓取结果，防止 0 数据污染日报
5. 生成静态 dashboard
6. 提交 docs/ 和输出文件到 GitHub
7. 发送飞书群机器人通知
8. 同步品牌页数据到飞书多维表格
```

对应 workflow 文件：

```text
.github/workflows/daily-monitor.yml
```

当前定时任务：

```text
cron: 17 2 * * *
```

也就是每天 UTC 02:17 运行，约等于北京时间 10:17。

## 主要文件

```text
scripts/unidays_monitor.py
```

抓取 UNiDAYS 页面 offer 和品牌页 offer，输出到 `unidays_outputs/`。

```text
scripts/studentbeans_monitor.py
```

抓取 Student Beans 页面 offer 和品牌页 offer，输出到 `studentbeans_outputs/`。

```text
scripts/validate_crawl_outputs.py
```

在生成 dashboard 前检查当天抓取结果。如果检测到网站拦截、CloudFront 403、或品牌页目标 offer 数量异常偏低，会让 workflow 失败，避免错误数据覆盖正常 dashboard 或写入飞书。

```text
scripts/build_dashboard.py
```

读取最新 clean JSON，生成静态页面：

```text
docs/index.html
docs/dashboard_YYYY-MM-DD.html
dashboard/index.html
```

```text
scripts/notify_feishu.py
```

通过 `FEISHU_WEBHOOK` 给飞书群发送 dashboard 更新通知。

```text
scripts/sync_feishu_bitable.py
```

把每天的品牌页 offer 归档到飞书多维表格。

## 输出文件

每个平台每天会输出：

```text
clean_offers_YYYY-MM-DD.json
page_offers_YYYY-MM-DD.csv
competitor_offers_YYYY-MM-DD.csv
daily_report_YYYY-MM-DD.md
debug_YYYY-MM-DD/
```

其中：

- `page_offers`：首页/分类页抓到的 offer，只用于 dashboard 展示。
- `competitor_offers`：品牌页抓到的 offer，是“今日新增/下线”和飞书归档的核心数据。
- `clean_offers`：页面 offer + 品牌页 offer 的清洗后 JSON。
- `debug_YYYY-MM-DD`：每个页面的截图和正文，方便排查被拦截或解析失败。

## Dashboard 逻辑

GitHub Pages 发布路径：

```text
https://exefyx.github.io/-git_monitor/
```

Dashboard 分成几块：

- 页面 Offer：展示首页/分类页抓到的 offer。
- 今日 vs 昨日变化：只比较品牌页目标品牌 offer。
- 分产品监控情况：按产品线聚合品牌页 offer。
- 竞品 Offer 详情：展示目标品牌的品牌页 offer。

“今日新增/下线”的判断规则：

```text
来源类型 + 页面 + 品牌 + offer 文案
```

如果 offer 文案变化，例如：

```text
15% Off Trains For New Customers
```

变成：

```text
15% Off Trains For New Customers (£5 cap)
```

当前逻辑会视为旧 offer 下线、新 offer 新增。

## 飞书同步逻辑

飞书同步只归档品牌页数据，不归档首页/分类页数据，避免长期表格里出现大量噪音。

飞书多维表格需要两张表：

### OfferRecords

字段：

```text
日期
平台
记录类型
来源类型
页面
区块
品牌
Offer
产品线
RowKey
Dashboard URL
Run ID
写入时间
```

记录类型包括：

```text
全量
新增
下线
```

### DailyRuns

字段：

```text
日期
平台
全量数量
页面Offer数量
品牌页Offer数量
新增数量
下线数量
Dashboard URL
日报摘要
同步状态
Run ID
```

说明：

- `OfferRecords` 只写品牌页目标 offer。
- `DailyRuns` 记录每个平台每次运行的统计摘要。
- 当前同步是追加写入。如果同一天手动跑多次，飞书可能出现同日期同平台多行记录。

## GitHub Secrets

进入仓库：

```text
Settings -> Secrets and variables -> Actions -> Repository secrets
```

需要配置：

```text
FEISHU_WEBHOOK
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_BITABLE_APP_TOKEN
FEISHU_OFFER_TABLE_ID
FEISHU_RUN_TABLE_ID
```

含义：

- `FEISHU_WEBHOOK`：飞书群机器人 webhook，用于发送通知。
- `FEISHU_APP_ID`：飞书自建应用 App ID。
- `FEISHU_APP_SECRET`：飞书自建应用 App Secret。
- `FEISHU_BITABLE_APP_TOKEN`：多维表格 URL 中 `/base/` 后面的 token。
- `FEISHU_OFFER_TABLE_ID`：OfferRecords 表的 table id。
- `FEISHU_RUN_TABLE_ID`：DailyRuns 表的 table id。

可选配置：

- `FEISHU_OFFER_ARCHIVE_TABLE_ID`：OfferRecordsHistory 表的 table id，用于保存同一天重复运行时被替换掉的旧版本。
- `FEISHU_RUN_ARCHIVE_TABLE_ID`：DailyRunsHistory 表的 table id，用于保存同一天重复运行时被替换掉的运行摘要。

如果不配置这两个历史表 ID，脚本会在同步时自动查找或创建 `OfferRecordsHistory` 和 `DailyRunsHistory`。

如果使用 `larkenterprise.com` 租户，默认 API 地址已经适配：

```text
https://open.larkenterprise.com/open-apis
```

如果使用 `feishu.cn` 租户，可以额外设置：

```text
FEISHU_API_BASE=https://open.feishu.cn/open-apis
```

## 复制/接手这个仓库后如何配置

如果别人 fork 或复制这个仓库，不能直接使用原仓库的飞书配置和 GitHub Pages，需要按下面步骤重新配置。

### 1. Fork 或复制仓库

可以直接 fork：

```text
GitHub -> Fork
```

也可以复制到新仓库：

```bash
git clone https://github.com/exefyx/-git_monitor.git
cd -git_monitor
git remote set-url origin <new-repo-url>
git push -u origin main
```

### 2. 开启 GitHub Pages

进入新仓库：

```text
Settings -> Pages
```

选择：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

保存后，dashboard 地址通常会变成：

```text
https://<github-username>.github.io/<repo-name>/
```

如果仓库名不是 `-git_monitor`，需要同步修改这些脚本里的 dashboard URL：

```text
scripts/notify_feishu.py
scripts/sync_feishu_bitable.py
```

把：

```text
https://exefyx.github.io/-git_monitor/
```

改成新仓库自己的 GitHub Pages 地址。

### 3. 开启 GitHub Actions 写权限

进入：

```text
Settings -> Actions -> General
```

确认：

```text
Workflow permissions: Read and write permissions
```

否则 workflow 无法把每日生成的 dashboard 和输出文件 commit 回仓库。

### 4. 配置飞书群机器人

在飞书群里添加自定义机器人，拿到 webhook，然后在 GitHub Secrets 中添加：

```text
FEISHU_WEBHOOK
```

如果不需要群通知，可以不配置。脚本会自动跳过通知。

### 5. 创建飞书自建应用

进入飞书开放平台，创建自建应用，拿到：

```text
App ID
App Secret
```

然后在 GitHub Secrets 中添加：

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
```

应用需要开通多维表格相关权限，并发布版本。之后把这个应用添加到目标多维表格文档中，权限至少需要可编辑。

### 6. 创建飞书多维表格

创建一个多维表格，包含两张表：

```text
OfferRecords
DailyRuns
```

字段参考上面的“飞书同步逻辑”章节。

为了保留同一天多次运行的历史版本，脚本会自动查找或创建两张历史表：

```text
OfferRecordsHistory
DailyRunsHistory
```

历史表字段会分别从 `OfferRecords` 和 `DailyRuns` 自动复制。脚本每次写入新结果前，会先把当天同平台在主表中的旧记录复制到对应历史表，再删除主表旧记录并写入最新记录。这样主表始终是当天最新版本，历史表保留早先版本。

然后从 URL 和表格 URL 参数中取：

```text
FEISHU_BITABLE_APP_TOKEN
FEISHU_OFFER_TABLE_ID
FEISHU_RUN_TABLE_ID
```

示例 URL：

```text
https://xxx.larkenterprise.com/base/TbARb01xxxx?table=tblhChxxxx&view=vewxxxx
```

对应关系：

```text
FEISHU_BITABLE_APP_TOKEN = /base/ 后面的 TbARb01xxxx
FEISHU_OFFER_TABLE_ID = OfferRecords 表 URL 里的 table=tbl...
FEISHU_RUN_TABLE_ID = DailyRuns 表 URL 里的 table=tbl...
```

### 7. 更新登录态

新接手者最好在本地重新生成自己的登录态：

```bash
python scripts/unidays_monitor.py --login
python scripts/studentbeans_monitor.py --login
```

完成后会生成或更新：

```text
unidays_state.json
studentbeans_state.json
```

提交这两个文件后，GitHub Actions 才能使用新的浏览器登录状态。

### 8. 本地测试

第一次正式启用前，建议本地跑一遍：

```bash
pip install -r requirements.txt
playwright install chromium

python scripts/unidays_monitor.py --run
python scripts/studentbeans_monitor.py --run
python scripts/validate_crawl_outputs.py
python scripts/build_dashboard.py
python scripts/sync_feishu_bitable.py --dry-run
```

如果 `validate_crawl_outputs.py` 失败，先检查 debug 截图和 body 文本，确认是不是网站拦截。

### 9. 手动触发 GitHub Actions

进入：

```text
Actions -> Daily Monitor -> Run workflow
```

第一次手动跑成功后，确认：

- `docs/index.html` 已更新。
- GitHub Pages 可以打开。
- 飞书群收到通知。
- 飞书多维表格新增当天记录。

后续会按定时任务每天自动运行。

## 手动运行

本地安装依赖：

```bash
pip install -r requirements.txt
playwright install chromium
```

本地抓取：

```bash
python scripts/unidays_monitor.py --run
python scripts/studentbeans_monitor.py --run
```

校验输出：

```bash
python scripts/validate_crawl_outputs.py
```

生成 dashboard：

```bash
python scripts/build_dashboard.py
```

飞书 dry-run：

```bash
python scripts/sync_feishu_bitable.py --date 2026-06-05 --dry-run
```

飞书正式同步：

```bash
python scripts/sync_feishu_bitable.py --date 2026-06-05
```

## 登录态

仓库中包含：

```text
unidays_state.json
studentbeans_state.json
```

它们是 Playwright 保存的登录/浏览器状态。若网站登录态失效，可以本地重新登录：

```bash
python scripts/unidays_monitor.py --login
python scripts/studentbeans_monitor.py --login
```

登录完成后会更新对应 state 文件。需要提交更新后的 state 文件，GitHub Actions 才能继续使用新的登录态。

## 被拦截时如何判断

如果某次运行抓到 0 条，优先检查：

```text
unidays_outputs/debug_YYYY-MM-DD/
studentbeans_outputs/debug_YYYY-MM-DD/
```

常见拦截页面：

```text
UNiDAYS security checks have blocked this request
403 ERROR
The request could not be satisfied
Request blocked
Generated by cloudfront
```

如果出现这些内容，说明不是 offer 消失，而是 GitHub Actions runner 被网站风控或 CloudFront 拦截。

当前仓库已经加了保护：

```text
scripts/validate_crawl_outputs.py
```

如果当天品牌页目标 offer 数量低于阈值，workflow 会失败，后续不会更新 dashboard、不会发飞书通知、也不会写入飞书表格。

## 如何降低被拦截概率

当前爬虫已经做了基础降频：

- 页面之间随机等待 6-16 秒。
- 页面加载后随机等待。
- 设置正常 Chrome user-agent。
- 设置 `Accept-Language: en-GB`。
- 隐藏部分自动化浏览器特征。

但 GitHub Actions 官方 runner 仍然是云服务器 IP，可能继续被网站风控拦截。

如果需要进一步提高稳定性，推荐改成 self-hosted runner：

```text
GitHub Actions 仍然触发任务
但实际爬虫运行在本地电脑、公司网络或固定服务器上
```

这样可以避免 GitHub 云 IP 被直接拦截。

## 常见问题

### 为什么 dashboard 显示 0 新增/0 下线？

因为“今日 vs 昨日变化”只比较品牌页目标品牌。如果首页/分类页变化，但品牌页 offer 没变，就会显示 0/0。

### 为什么飞书同一天有多行？

当前飞书同步是追加写入。手动跑多次或 re-run workflow 会新增多行同日期记录。

### 为什么 Eurostar 有时是空的？

Eurostar 只从 UNiDAYS 品牌页监测。如果 UNiDAYS 的 Eurostar 品牌页显示“Request a student offer”而不是 offer 卡片，dashboard 会显示 Eurostar，但 offer 列表为空。

### 为什么有时一个 offer 文案变化会变成新增/下线？

当前 `RowKey` 使用完整 offer 文案。只要文案变了，就会被视为一条新记录，同时旧文案被视为下线。
