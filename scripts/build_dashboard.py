# -*- coding: utf-8 -*-
"""
Build a static dashboard from UNiDAYS + Student Beans crawler outputs.

Reads latest:
- unidays_outputs/clean_offers_YYYY-MM-DD.json
- studentbeans_outputs/clean_offers_YYYY-MM-DD.json

Writes:
- docs/index.html                 # for GitHub Pages
- docs/dashboard_YYYY-MM-DD.html  # daily archive
- dashboard/index.html            # local preview

Run:
python .\scripts\build_dashboard.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "UNiDAYS": ROOT / "unidays_outputs",
    "Student Beans": ROOT / "studentbeans_outputs",
}

OWNED_BRANDS = {"trip.com", "trainpal"}

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

PLATFORM_TARGET_BRANDS = {
    "UNiDAYS": TARGET_BRANDS,
    "Student Beans": [brand for brand in TARGET_BRANDS if brand != "Eurostar"],
}


def compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


TARGET_BRAND_KEYS = {compact_text(b): b for b in TARGET_BRANDS}


def is_target_brand(brand: str) -> bool:
    return compact_text(brand) in TARGET_BRAND_KEYS


DOCS_DIR = ROOT / "docs"
LOCAL_DIR = ROOT / "dashboard"

PRODUCT_ORDER = [
    "Asia Train / Railway",
    "Japan Train / Japan Railway",
    "Railcard",
    "UK & Europe Train Tickets",
    "Bus / Coach",
    "Flights",
    "Hotels / Accommodation",
    "Tours & Tickets",
    "Car Rental",
    "eSIM / SIM",
    "Other",
]


def latest_clean_file(folder: Path) -> Path | None:
    files = sorted(folder.glob("clean_offers_*.json"))
    return files[-1] if files else None


def date_from_file(path: Path) -> str:
    return path.stem.replace("clean_offers_", "")


def read_rows(path: Path | None) -> list[dict]:
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def filter_diff_rows(rows: list[dict]) -> list[dict]:
    """
    Only keep target brand-page offers for daily diff.

    Page/category offers are shown in the page offer panel, but they should
    not affect the daily new/removed panel. The daily change panel only
    compares brand-page offers for:

    TrainPal / Trip.com / Trainline / Omio / Klook /
    National Express / FlixBus / Eurostar
    """
    result = []

    for r in rows:
        if str(r.get("source_type", "")).strip() != "品牌页":
            continue

        brand = str(r.get("brand", "")).strip()

        if not is_target_brand(brand):
            continue

        result.append(r)

    return result


def row_key(row: dict) -> tuple[str, str, str, str]:
    return (
        str(row.get("source_type", "")),
        str(row.get("page", "")),
        str(row.get("brand", "")),
        " ".join(str(row.get("offer", "")).lower().split()),
    )


def previous_file(folder: Path, current: Path | None) -> Path | None:
    if not current:
        return None
    files = sorted(p for p in folder.glob("clean_offers_*.json") if p != current)
    return files[-1] if files else None


def make_diff(folder: Path, current: Path | None, rows: list[dict]) -> dict:
    prev = previous_file(folder, current)
    if not prev:
        return {
            "new": [],
            "removed": [],
            "message": "当前为监控基准日，后续每日仅对比 8 个目标品牌新增 / 下线 offer。",
        }

    old_rows = read_rows(prev)

    today_rows = filter_diff_rows(rows)
    old_rows = filter_diff_rows(old_rows)

    today_set = {row_key(r) for r in today_rows}
    old_set = {row_key(r) for r in old_rows}

    today_map = {row_key(r): r for r in today_rows}
    old_map = {row_key(r): r for r in old_rows}

    return {
        "new": [today_map[k] for k in sorted(today_set - old_set)],
        "removed": [old_map[k] for k in sorted(old_set - today_set)],
        "message": "仅统计 TrainPal / Trip.com / Trainline / Omio / Klook / National Express / FlixBus / Eurostar 这 8 个品牌的 offer 变化。",
    }


def make_trend(folder: Path) -> list[dict]:
    files = sorted(folder.glob("clean_offers_*.json"))[-8:]
    trend = []
    prev_rows = None

    for file in files:
        rows = filter_diff_rows(read_rows(file))
        if prev_rows is None:
            new_count = 0
            removed_count = 0
        else:
            old_set = {row_key(r) for r in prev_rows}
            today_set = {row_key(r) for r in rows}
            new_count = len(today_set - old_set)
            removed_count = len(old_set - today_set)

        trend.append({
            "date": date_from_file(file)[5:],
            "new": new_count,
            "removed": removed_count,
        })
        prev_rows = rows

    return trend


def prepare_platform(name: str, folder: Path) -> dict:
    current = latest_clean_file(folder)
    rows = read_rows(current)
    platform_target_brands = PLATFORM_TARGET_BRANDS.get(name, TARGET_BRANDS)

    if not current or not rows:
        return {
            "available": False,
            "date": "",
            "lastRun": "",
            "status": "No data",
            "kpis": {"pageOffers": 0, "competitorOffers": 0, "newOffers": 0, "removedOffers": 0, "ownedOffers": 0, "trainpalOffers": 0, "competitorBrands": 0},
            "pages": {},
            "products": {},
            "competitors": {},
            "diff": {"new": [], "removed": [], "message": "No data"},
            "trend": [],
        }

    page_rows = [r for r in rows if r.get("source_type") == "页面"]
    platform_target_keys = {compact_text(brand) for brand in platform_target_brands}
    competitor_rows = [
        r
        for r in rows
        if r.get("source_type") == "品牌页"
        and compact_text(r.get("brand", "")) in platform_target_keys
    ]
    target_brand_rows = filter_diff_rows(rows)
    diff = make_diff(folder, current, rows)

    pages = defaultdict(list)
    for r in page_rows:
        pages[r.get("page") or "Other"].append([r.get("brand", ""), r.get("offer", "")])

    competitors = {brand: [] for brand in platform_target_brands}
    for r in competitor_rows:
        brand = r.get("brand") or "Unknown"
        if brand not in competitors:
            competitors[brand] = []
        competitors[brand].append(r.get("offer", ""))

    product_groups = defaultdict(list)
    for r in competitor_rows:
        product_groups[r.get("product_type") or "Other"].append(r)

    ordered_products = [p for p in PRODUCT_ORDER if p in product_groups]
    ordered_products += sorted(p for p in product_groups if p not in ordered_products)

    products = {}
    for product in ordered_products:
        group = product_groups[product]
        owned_rows = [r for r in group if r.get("brand", "").lower() in OWNED_BRANDS]
        competitor_rows_for_product = [r for r in group if r.get("brand", "").lower() not in OWNED_BRANDS]
        products[product] = {
            "owned": [[r.get("brand", ""), r.get("offer", "")] for r in owned_rows],
            "trainpal": [r.get("offer", "") for r in owned_rows],  # backward compatibility
            "competitors": [[r.get("brand", ""), r.get("offer", "")] for r in competitor_rows_for_product],
        }

    return {
        "available": True,
        "date": date_from_file(current),
        "lastRun": datetime.fromtimestamp(current.stat().st_mtime).strftime("%H:%M:%S"),
        "status": "Success",
        "kpis": {
            "pageOffers": len(page_rows),
            "competitorOffers": len(competitor_rows),
            "newOffers": len(diff["new"]),
            "removedOffers": len(diff["removed"]),
            "ownedOffers": sum(1 for r in competitor_rows if r.get("brand", "").lower() in OWNED_BRANDS),
            "trainpalOffers": sum(1 for r in competitor_rows if r.get("brand", "").lower() == "trainpal"),
            "competitorBrands": len({
                r.get("brand", "")
                for r in target_brand_rows
                if r.get("brand", "").lower() not in OWNED_BRANDS
            }),
        },
        "pages": dict(pages),
        "products": products,
        "competitors": competitors,
        "diff": diff,
        "trend": make_trend(folder),
    }


def script_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_html(data: dict) -> str:
    payload = script_json(data)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Student Offer Daily Monitor</title>
<style>
:root {{ --bg:#f6f8fb; --card:#fff; --line:#dbe3ef; --text:#0f172a; --muted:#64748b; --blue:#2563eb; --green:#059669; --red:#e11d48; --soft:#eef2ff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }}
header {{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.92); backdrop-filter:blur(12px); border-bottom:1px solid var(--line); }}
.wrap {{ max-width:1440px; margin:auto; padding:18px 24px; }}
.row {{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }}
h1 {{ margin:0; font-size:22px; }}
.sub,.muted {{ color:var(--muted); }}
.logo {{ width:38px; height:38px; border-radius:12px; background:var(--blue); color:white; display:grid; place-items:center; font-weight:900; }}
.brand {{ display:flex; gap:12px; align-items:center; }}
.status {{ background:#dcfce7; color:#047857; padding:7px 12px; border-radius:999px; font-weight:800; }}
.tabs {{ display:flex; gap:8px; background:white; border:1px solid var(--line); border-radius:15px; padding:5px; }}
button {{ cursor:pointer; }}
.tab,.pill {{ border:0; border-radius:11px; padding:9px 15px; font-weight:800; color:#475569; background:#eef2f7; }}
.tab.active,.pill.active {{ background:var(--blue); color:white; }}
.search {{ background:white; border:1px solid var(--line); border-radius:15px; padding:10px 12px; min-width:260px; }}
.search input {{ border:0; outline:0; width:220px; font-size:14px; }}
.grid {{ display:grid; gap:16px; }}
.kpis {{ grid-template-columns:repeat(6,1fr); }}
.two {{ grid-template-columns:1.05fr 1.45fr; }}
.three {{ grid-template-columns:repeat(3,1fr); }}
.bottom {{ grid-template-columns:1.65fr 1fr; }}
.card,.kpi {{ background:white; border:1px solid var(--line); border-radius:18px; box-shadow:0 12px 30px rgba(15,23,42,.06); }}
.card {{ padding:20px; }}
.kpi {{ padding:18px; }}
.kpi-label {{ color:var(--muted); font-size:13px; }}
.kpi-value {{ font-size:26px; font-weight:900; margin-top:3px; }}
.kpi-hint {{ color:var(--muted); font-size:12px; margin-top:3px; }}
.card-title {{ margin:0 0 15px; font-size:18px; }}
.pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; }}
.offer-list {{ display:grid; gap:8px; max-height:520px; overflow:auto; padding-right:4px; }}
.offer {{ border:1px solid var(--line); background:white; border-radius:12px; padding:10px 12px; line-height:1.35; font-size:14px; }}
.offer b {{ font-weight:900; }}
.change-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.box {{ border-radius:16px; padding:14px; border:1px solid var(--line); min-height:142px; }}
.green {{ background:#ecfdf5; border-color:#bbf7d0; }}
.red {{ background:#fff1f2; border-color:#fecdd3; }}
.bars {{ display:grid; gap:11px; }}
.bar-row {{ display:grid; grid-template-columns:110px 1fr 34px; gap:8px; align-items:center; font-size:12px; }}
.bar-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bar-bg {{ height:10px; border-radius:99px; background:#e2e8f0; overflow:hidden; }}
.bar-fill {{ height:100%; background:var(--blue); border-radius:99px; }}
.bar-fill.g {{ background:#16a34a; }}
.vs-grid {{ display:grid; grid-template-columns:1fr 54px 1fr; gap:16px; align-items:stretch; }}
.side {{ border:1px solid var(--line); border-radius:16px; padding:16px; min-height:220px; }}
.side.trainpal {{ background:#ecfdf5; border-color:#bbf7d0; }}
.side.comp {{ background:#eff6ff; border-color:#bfdbfe; }}
.vs {{ display:grid; place-items:center; align-self:center; justify-self:center; width:48px; height:48px; background:#eef2f7; border-radius:999px; font-weight:900; color:var(--muted); }}
details {{ border:1px solid var(--line); border-radius:14px; margin-bottom:9px; background:#f8fafc; overflow:hidden; }}
summary {{ list-style:none; cursor:pointer; padding:13px 15px; display:flex; justify-content:space-between; font-weight:900; }}
summary::-webkit-details-marker {{ display:none; }}
.count {{ background:#eff6ff; color:var(--blue); border-radius:999px; padding:3px 8px; font-size:12px; }}
.detail {{ border-top:1px solid var(--line); background:white; padding:12px 15px; line-height:1.55; font-size:14px; }}
.detail ul {{ margin:0; padding-left:18px; }}
svg {{ width:100%; height:210px; }}
@media(max-width:1100px) {{ .kpis,.three,.two,.bottom {{ grid-template-columns:1fr 1fr; }} .vs-grid {{ grid-template-columns:1fr; }} .vs {{ display:none; }} }}
@media(max-width:720px) {{ .wrap {{ padding:14px; }} .kpis,.three,.two,.bottom,.change-grid {{ grid-template-columns:1fr; }} .search,.search input {{ width:100%; }} }}
</style>
</head>
<body>
<header><div class="wrap row"><div class="brand"><div class="logo">O</div><div><h1>Student Offer Daily Monitor</h1><div class="sub">UNiDAYS + Student Beans competitor offer monitoring</div></div></div><div class="row"><span id="dateText"></span><span id="runText"></span><span class="status" id="statusText"></span></div></div></header>
<main class="wrap grid">
  <div class="row"><div class="tabs" id="platformTabs"></div><label class="search">⌕ <input id="brandSearch" placeholder="Search brand..." /></label></div>
  <section class="grid kpis" id="kpiGrid"></section>
  <section class="grid two"><div class="card"><h2 class="card-title">1. 页面 Offer</h2><div class="pills" id="pageTabs"></div><div class="offer-list" id="pageOfferList"></div></div><div class="card"><h2 class="card-title">2. 今日 vs 昨日变化</h2><div class="change-grid"><div class="box green"><b id="newTitle"></b><ul id="newList"></ul></div><div class="box red"><b id="removedTitle"></b><ul id="removedList"></ul></div></div><p class="muted" id="diffMessage"></p></div></section>
  <section class="grid three"><div class="card"><h2 class="card-title">各品牌 Offer 数量</h2><div class="bars" id="brandBars"></div></div><div class="card"><h2 class="card-title">各产品线 Offer 数量</h2><div class="bars" id="productBars"></div></div><div class="card"><h2 class="card-title">新增 / 下线趋势</h2><svg id="trendChart" viewBox="0 0 360 210" preserveAspectRatio="none"></svg></div></section>
  <section class="grid bottom"><div class="card"><h2 class="card-title">3. 分产品监控情况</h2><div class="pills" id="productTabs"></div><div class="vs-grid"><div class="side trainpal"><h3>自有品牌（Trip.com / TrainPal）</h3><div id="trainpalOffers"></div></div><div class="vs">对照</div><div class="side comp"><h3>其他品牌 / 竞品</h3><div id="competitorProductOffers"></div></div></div></div><div class="card"><h2 class="card-title">4. 竞品 Offer 详情</h2><div id="competitorDetails"></div></div></section>
</main>
<script>
const DATA = {payload};
let platform = Object.keys(DATA).find(k => DATA[k].available) || Object.keys(DATA)[0];
let pageTab = "";
let productTab = "";
let search = "";
const $ = id => document.getElementById(id);
function esc(v) {{
  return String(v ?? "").replace(/[&<>"']/g, c => {{
    if (c === "&") return "&amp;";
    if (c === "<") return "&lt;";
    if (c === ">") return "&gt;";
    if (c === '"') return "&quot;";
    return "&#039;";
  }});
}}
function cur() {{ return DATA[platform] || {{}}; }}
function renderPlatformTabs() {{
  $("platformTabs").innerHTML = Object.keys(DATA).map(name => `<button class="tab ${{name===platform?'active':''}}" data-platform="${{esc(name)}}">${{esc(name)}}</button>`).join("");
  document.querySelectorAll("[data-platform]").forEach(b => b.onclick = () => {{ platform=b.dataset.platform; pageTab=""; productTab=""; render(); }});
}}
function renderMeta() {{ const d=cur(); $("dateText").textContent=`Date: ${{d.date || '-'}}`; $("runText").textContent=`Last Run: ${{d.lastRun || '-'}}`; $("statusText").textContent=`Status: ${{d.status || 'No data'}}`; }}
function renderKpis() {{ const k=cur().kpis || {{}}; const items=[["📄","Page Offers",k.pageOffers||0,"页面抓取"],["🏷️","Brand Page Offers",k.competitorOffers||0,"品牌页抓取"],["➕","New Offers",k.newOffers||0,"vs yesterday"],["➖","Removed Offers",k.removedOffers||0,"vs yesterday"],["🚆","Owned Offers",k.ownedOffers||0,"Trip.com + TrainPal"],["👥","Other Brands",k.competitorBrands||0,"其他品牌数"]]; $("kpiGrid").innerHTML=items.map(i=>`<div class="kpi"><div style="font-size:24px">${{i[0]}}</div><div><div class="kpi-label">${{i[1]}}</div><div class="kpi-value">${{i[2]}}</div><div class="kpi-hint">${{i[3]}}</div></div></div>`).join(""); }}
function renderPages() {{ const pages=cur().pages || {{}}; const names=Object.keys(pages); if(!pageTab || !pages[pageTab]) pageTab=names[0] || ""; $("pageTabs").innerHTML=names.map(n=>`<button class="pill ${{n===pageTab?'active':''}}" data-page="${{esc(n)}}">${{esc(n)}} <span style="opacity:.75">${{pages[n].length}}</span></button>`).join(""); document.querySelectorAll("[data-page]").forEach(b=>b.onclick=()=>{{pageTab=b.dataset.page; renderPages();}}); const rows=pages[pageTab] || []; $("pageOfferList").innerHTML=rows.length?rows.map(r=>`<div class="offer"><b>${{esc(r[0])}}</b><span class="muted"> — </span>${{esc(r[1])}}</div>`).join(""):`<p class="muted">暂无页面 offer</p>`; }}
function fmtRow(r) {{ return `${{r.brand||''}}：${{r.offer||''}}`; }}
function renderDiff() {{ const d=cur().diff || {{new:[],removed:[],message:''}}; $("newTitle").textContent=`今日新增 (${{(d.new||[]).length}})`; $("removedTitle").textContent=`今日下线 (${{(d.removed||[]).length}})`; $("newList").innerHTML=(d.new||[]).slice(0,10).map(r=>`<li>${{esc(fmtRow(r))}}</li>`).join("") || "<li>暂无</li>"; $("removedList").innerHTML=(d.removed||[]).slice(0,10).map(r=>`<li>${{esc(fmtRow(r))}}</li>`).join("") || "<li>暂无</li>"; $("diffMessage").textContent=d.message || ""; }}
function bars(id, rows, green=false) {{ const max=Math.max(1,...rows.map(r=>r.count)); $(id).innerHTML=rows.map(r=>`<div class="bar-row"><div class="bar-label" title="${{esc(r.label)}}">${{esc(r.label)}}</div><div class="bar-bg"><div class="bar-fill ${{green?'g':''}}" style="width:${{Math.max(4,r.count/max*100)}}%"></div></div><b style="text-align:right">${{r.count}}</b></div>`).join(""); }}
function renderCharts() {{ const d=cur(); const brandRows=Object.entries(d.competitors||{{}}).map(([label,offers])=>({{label,count:offers.length}})).sort((a,b)=>b.count-a.count).slice(0,9); bars('brandBars',brandRows); const productRows=Object.entries(d.products||{{}}).map(([label,val])=>({{label:label.replace('UK & Europe ','UK/EU ').replace('Hotels / Accommodation','Hotels'),count:(val.trainpal||[]).length+(val.competitors||[]).length}})).sort((a,b)=>b.count-a.count); bars('productBars',productRows,true); trend(d.trend||[]); }}
function trend(rows) {{ const svg=$("trendChart"); if(!rows.length){{svg.innerHTML='<text x="20" y="100" fill="#64748b">暂无趋势数据</text>';return;}} const w=360,h=210,p=28,max=Math.max(1,...rows.flatMap(r=>[r.new||0,r.removed||0])),step=rows.length>1?(w-p*2)/(rows.length-1):1; const pts=k=>rows.map((r,i)=>`${{p+i*step}},${{h-p-((r[k]||0)/max)*(h-p*2)}}`).join(' '); svg.innerHTML=`<line x1="${{p}}" y1="${{h-p}}" x2="${{w-p}}" y2="${{h-p}}" stroke="#cbd5e1"/><line x1="${{p}}" y1="${{p}}" x2="${{p}}" y2="${{h-p}}" stroke="#cbd5e1"/><polyline points="${{pts('new')}}" fill="none" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/><polyline points="${{pts('removed')}}" fill="none" stroke="#e11d48" stroke-width="4" stroke-linecap="round"/>${{rows.map((r,i)=>`<text x="${{p+i*step}}" y="${{h-8}}" text-anchor="middle" font-size="10" fill="#64748b">${{esc(r.date)}}</text>`).join('')}}`; }}
function renderProducts() {{ const ps=cur().products||{{}}; const names=Object.keys(ps); if(!productTab || !ps[productTab]) productTab=names[0] || ""; $("productTabs").innerHTML=names.map(n=>`<button class="pill ${{n===productTab?'active':''}}" data-product="${{esc(n)}}">${{esc(n)}}</button>`).join(""); document.querySelectorAll('[data-product]').forEach(b=>b.onclick=()=>{{productTab=b.dataset.product;renderProducts();}}); const p=ps[productTab]||{{owned:[],trainpal:[],competitors:[]}}; const ownedRows = p.owned && p.owned.length ? p.owned : (p.trainpal||[]).map(o=>["TrainPal",o]); $("trainpalOffers").innerHTML=ownedRows.length?`<ul>${{ownedRows.map(r=>`<li><b>${{esc(r[0])}}</b>：${{esc(r[1])}}</li>`).join('')}}</ul>`:'<p class="muted">暂无自有品牌对应产品 offer</p>'; $("competitorProductOffers").innerHTML=p.competitors.length?`<ul>${{p.competitors.map(r=>`<li><b>${{esc(r[0])}}</b>：${{esc(r[1])}}</li>`).join('')}}</ul>`:'<p class="muted">暂无其他品牌 offer</p>'; }}
function renderCompetitors() {{ const comps=cur().competitors||{{}}; const rows=Object.entries(comps).filter(([b])=>b.toLowerCase().includes(search.toLowerCase())); $("competitorDetails").innerHTML=rows.length?rows.map(([b,offers],i)=>`<details ${{i===0?'open':''}}><summary><span>${{esc(b)}}</span><span class="count">${{offers.length}}</span></summary><div class="detail"><ul>${{offers.map(o=>`<li>${{esc(o)}}</li>`).join('')}}</ul></div></details>`).join(''):'<p class="muted">没有匹配品牌</p>'; }}
function render() {{ renderPlatformTabs(); renderMeta(); renderKpis(); renderPages(); renderDiff(); renderCharts(); renderProducts(); renderCompetitors(); }}
$("brandSearch").oninput=e=>{{search=e.target.value;renderCompetitors();}};
render();
</script>
</body>
</html>'''


def main() -> None:
    data = {}
    dates = []
    for name, folder in SOURCES.items():
        item = prepare_platform(name, folder)
        data[name] = item
        if item.get("date"):
            dates.append(item["date"])

    date = max(dates) if dates else datetime.now().strftime("%Y-%m-%d")
    text = render_html(data)

    for folder in [DOCS_DIR, LOCAL_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(text, encoding="utf-8")
        (folder / f"dashboard_{date}.html").write_text(text, encoding="utf-8")

    print("Dashboard generated:")
    print(f"- {DOCS_DIR / 'index.html'}")
    print(f"- {LOCAL_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
