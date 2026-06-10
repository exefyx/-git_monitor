# -*- coding: utf-8 -*-
"""Build an iOS 26-inspired glass UI preview without replacing production."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from build_dashboard import SOURCES, prepare_platform


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
LOCAL_DIR = ROOT / "dashboard"


def script_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_preview(data: dict) -> str:
    payload = script_json(data)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Student Offer Monitor - Glass Preview</title>
<style>
:root {{
  --ink:#101828; --muted:#667085; --hair:rgba(16,24,40,.14);
  --glass:rgba(255,255,255,.30); --glass-strong:rgba(255,255,255,.46);
  --blue:#1b6ef3; --cyan:#0e9384; --green:#099250; --red:#e31b54; --amber:#b54708;
  --shadow:0 26px 80px rgba(16,24,40,.20), inset 0 1px 0 rgba(255,255,255,.72), inset 0 -18px 34px rgba(255,255,255,.18);
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{
  margin:0; color:var(--ink);
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:
    linear-gradient(115deg, rgba(47,111,255,.32) 0 18%, transparent 39%),
    linear-gradient(245deg, rgba(5,190,167,.30) 0 20%, transparent 43%),
    linear-gradient(18deg, rgba(255,149,0,.28) 0 15%, transparent 40%),
    linear-gradient(160deg, #f7fbff 0%, #dfeeff 34%, #effbf7 64%, #fff8ec 100%);
  min-height:100vh;
}}
body::before {{
  content:""; position:fixed; inset:0; pointer-events:none;
  background:
    linear-gradient(100deg, transparent 0 12%, rgba(255,255,255,.42) 18%, transparent 31%),
    linear-gradient(72deg, rgba(27,110,243,.24), transparent 28% 62%, rgba(14,147,132,.24)),
    linear-gradient(rgba(255,255,255,.30) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.24) 1px, transparent 1px);
  background-size:100% 100%, 100% 100%, 26px 26px, 26px 26px;
  mask-image:linear-gradient(to bottom, rgba(0,0,0,.9), transparent 82%);
}}
body::after {{
  content:""; position:fixed; inset:0; pointer-events:none;
  background:linear-gradient(120deg, rgba(255,255,255,.0) 0 35%, rgba(255,255,255,.36) 49%, rgba(255,255,255,0) 64%);
  mix-blend-mode:soft-light;
}}
button,input {{ font:inherit; }}
button {{ cursor:pointer; }}
.shell {{ display:grid; grid-template-columns:260px minmax(0,1fr); min-height:100vh; }}
.sidebar {{
  position:sticky; top:0; height:100vh; padding:18px; overflow:auto;
  background:linear-gradient(145deg, rgba(255,255,255,.44), rgba(255,255,255,.18));
  border-right:1px solid rgba(255,255,255,.62);
  backdrop-filter:blur(34px) saturate(1.7); -webkit-backdrop-filter:blur(34px) saturate(1.7);
  box-shadow:inset -1px 0 0 rgba(255,255,255,.38), 16px 0 54px rgba(16,24,40,.08);
}}
.brand {{ display:flex; align-items:center; gap:10px; margin-bottom:18px; }}
.mark {{ width:34px; height:34px; border-radius:8px; display:grid; place-items:center; color:#fff; font-weight:900; background:linear-gradient(135deg,var(--blue),var(--cyan)); box-shadow:0 10px 24px rgba(27,110,243,.24); }}
h1 {{ margin:0; font-size:17px; letter-spacing:0; }}
.sub {{ color:var(--muted); font-size:12px; margin-top:3px; }}
.nav-title {{ color:var(--muted); font-size:11px; font-weight:800; text-transform:uppercase; margin:18px 8px 8px; }}
.nav button {{
  width:100%; border:0; border-radius:8px; padding:10px 11px; margin:3px 0;
  display:flex; align-items:center; gap:10px; color:#344054; background:transparent; text-align:left; font-weight:750;
}}
.nav button.active,.nav button:hover {{ background:rgba(255,255,255,.72); box-shadow:inset 0 0 0 1px rgba(255,255,255,.9); }}
.dot {{ width:9px; height:9px; border-radius:99px; background:var(--blue); flex:0 0 auto; }}
.dot.green {{ background:var(--green); }} .dot.red {{ background:var(--red); }} .dot.cyan {{ background:var(--cyan); }} .dot.amber {{ background:var(--amber); }}
.main {{ padding:18px; min-width:0; }}
.topbar {{
  position:sticky; top:0; z-index:8; display:grid; grid-template-columns:auto minmax(24px,1fr) auto; align-items:center; gap:10px;
  padding:12px; margin-bottom:18px; border-radius:8px;
  background:linear-gradient(135deg, rgba(255,255,255,.48), rgba(255,255,255,.18));
  border:1px solid rgba(255,255,255,.70);
  backdrop-filter:blur(34px) saturate(1.75); -webkit-backdrop-filter:blur(34px) saturate(1.75);
  box-shadow:0 18px 60px rgba(16,24,40,.14), inset 0 1px 0 rgba(255,255,255,.78);
}}
.platforms,.segmented {{ display:flex; gap:6px; flex-wrap:wrap; }}
.platforms {{ grid-column:1; flex-wrap:nowrap; }}
.icon-btn,.platform,.chip {{
  border:1px solid rgba(255,255,255,.66); border-radius:8px; background:rgba(255,255,255,.34);
  backdrop-filter:blur(20px) saturate(1.6); -webkit-backdrop-filter:blur(20px) saturate(1.6);
  color:#344054; min-height:36px; padding:8px 11px; font-weight:800;
}}
.platform.active,.chip.active {{ background:linear-gradient(135deg, rgba(16,24,40,.92), rgba(27,110,243,.76)); color:white; border-color:rgba(255,255,255,.5); }}
.search {{
  grid-column:3; justify-self:end;
  display:flex; align-items:center; gap:6px; width:148px; min-width:148px; padding:0 8px; border-radius:8px;
  background:linear-gradient(135deg, rgba(255,255,255,.54), rgba(255,255,255,.20));
  border:1px solid rgba(255,255,255,.78);
  backdrop-filter:blur(22px) saturate(1.5); -webkit-backdrop-filter:blur(22px) saturate(1.5);
}}
.search input {{ width:100%; min-height:36px; border:0; outline:0; background:transparent; color:var(--ink); }}
.search svg {{ width:16px; height:16px; flex:0 0 16px; }}
.section {{ scroll-margin-top:86px; margin-bottom:18px; }}
.section-head {{ display:flex; justify-content:space-between; align-items:end; gap:16px; margin:0 2px 10px; }}
h2 {{ margin:0; font-size:18px; letter-spacing:0; }}
.hint {{ color:var(--muted); font-size:12px; }}
.grid {{ display:grid; gap:12px; }}
.kpis {{ grid-template-columns:repeat(6,minmax(0,1fr)); }}
.two {{ grid-template-columns:minmax(0,1.05fr) minmax(0,1.3fr); }}
.three {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
.panel,.metric {{
  position:relative; overflow:hidden;
  border-radius:8px;
  background:
    linear-gradient(145deg, rgba(255,255,255,.46), rgba(255,255,255,.18) 44%, rgba(255,255,255,.30)),
    linear-gradient(315deg, rgba(255,255,255,.16), rgba(255,255,255,0));
  border:1px solid rgba(255,255,255,.68);
  backdrop-filter:blur(36px) saturate(1.8); -webkit-backdrop-filter:blur(36px) saturate(1.8);
  box-shadow:var(--shadow);
}}
.panel::before,.metric::before {{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:
    linear-gradient(120deg, rgba(255,255,255,.72), rgba(255,255,255,0) 28%),
    linear-gradient(300deg, rgba(255,255,255,.18), rgba(255,255,255,0) 42%);
  opacity:.72;
}}
.panel > *,.metric > * {{ position:relative; z-index:1; }}
.panel {{ padding:14px; min-width:0; }}
.metric {{ min-height:108px; padding:14px; display:flex; flex-direction:column; justify-content:space-between; }}
.metric-label {{ color:var(--muted); font-size:12px; font-weight:750; }}
.metric-value {{ font-size:29px; font-weight:900; line-height:1; }}
.metric-note {{ color:var(--muted); font-size:11px; }}
.offer-list,.category-list {{ display:grid; gap:8px; max-height:520px; overflow:auto; padding-right:3px; }}
.offer,.row-card {{
  border-radius:8px; padding:10px 11px;
  background:linear-gradient(135deg, rgba(255,255,255,.52), rgba(255,255,255,.18));
  border:1px solid rgba(255,255,255,.70);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.62);
  line-height:1.38; font-size:13px;
}}
.offer b,.row-card b {{ font-weight:900; }}
.change {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.change-box {{
  border-radius:8px; min-height:158px; padding:12px; border:1px solid rgba(255,255,255,.68);
  background:linear-gradient(135deg, rgba(255,255,255,.50), rgba(255,255,255,.18));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.7);
}}
.change-box.good {{ box-shadow:inset 3px 0 0 var(--green); }}
.change-box.bad {{ box-shadow:inset 3px 0 0 var(--red); }}
ul {{ margin:8px 0 0; padding-left:18px; }}
li {{ margin:5px 0; }}
.bar-row {{ display:grid; grid-template-columns:128px minmax(80px,1fr) 34px; gap:8px; align-items:center; font-size:12px; }}
.bar-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bar-bg {{ height:9px; border-radius:99px; background:rgba(16,24,40,.09); overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:99px; background:linear-gradient(90deg,var(--blue),var(--cyan)); }}
.bar-fill.red {{ background:linear-gradient(90deg,var(--red),#f97066); }}
.category-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.brand-offer-card {{
  border-radius:8px;
  background:linear-gradient(135deg, rgba(255,255,255,.52), rgba(255,255,255,.18));
  border:1px solid rgba(255,255,255,.70);
  overflow:hidden;
  margin-bottom:10px;
}}
.brand-offer-head {{ padding:11px 12px; display:flex; justify-content:space-between; gap:10px; font-weight:900; }}
.brand-offer-head button {{ border:0; background:transparent; color:inherit; font:inherit; font-weight:900; padding:0; display:flex; align-items:center; gap:8px; text-align:left; }}
.chevron {{ display:inline-block; transition:transform .18s ease; color:var(--muted); }}
.brand-offer-card.collapsed .chevron {{ transform:rotate(-90deg); }}
.brand-offer-card.collapsed .detail {{ display:none; }}
.count {{ font-size:11px; color:var(--blue); background:rgba(27,110,243,.1); padding:3px 8px; border-radius:99px; }}
.detail {{ border-top:1px solid var(--hair); padding:11px 12px; background:rgba(255,255,255,.48); font-size:13px; }}
.mobile-nav {{ display:none; }}
#trendChart {{ width:100%; height:220px; display:block; }}
@media (max-width:1180px) {{
  .shell {{ grid-template-columns:1fr; }}
  .sidebar {{ display:none; }}
  .mobile-nav {{ display:flex; gap:8px; overflow:auto; padding-bottom:6px; }}
  .kpis,.three {{ grid-template-columns:repeat(3,1fr); }}
}}
@media (max-width:820px) {{
  .main {{ padding:12px; }}
  .topbar {{ grid-template-columns:auto minmax(8px,1fr) auto; align-items:center; }}
  .topbar > .spacer {{ display:block; }}
  .section-head {{ align-items:stretch; flex-direction:column; }}
  .search {{ grid-column:3; justify-self:end; min-width:128px; width:128px; }}
  .kpis,.two,.three,.change,.category-grid {{ grid-template-columns:1fr; }}
  .metric {{ min-height:92px; }}
}}
@media (max-width:560px) {{
  .topbar {{ grid-template-columns:1fr; align-items:stretch; }}
  .topbar > .spacer {{ display:none; }}
  .platforms {{ flex-wrap:wrap; }}
  .search {{ grid-column:auto; justify-self:stretch; min-width:0; width:100%; }}
}}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="brand"><div class="mark">O</div><div><h1>Offer Monitor</h1><div class="sub">Glass preview · iOS style</div></div></div>
    <div class="nav-title">Index</div>
    <div class="nav" id="sideNav"></div>
    <div class="nav-title">Categories</div>
    <div class="nav" id="categoryNav"></div>
  </aside>
  <main class="main">
    <div class="topbar">
      <div class="platforms" id="platformTabs"></div>
      <div class="spacer"></div>
      <label class="search">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m21 21-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input id="brandSearch" placeholder="Search brand" />
      </label>
    </div>
    <div class="mobile-nav" id="mobileNav"></div>

    <section class="section" id="overview">
      <div class="section-head"><div><h2>Overview</h2><div class="hint" id="metaText"></div></div><div class="hint" id="statusText"></div></div>
      <div class="grid kpis" id="kpiGrid"></div>
    </section>

    <section class="section" id="changes">
      <div class="section-head"><div><h2>Daily Changes</h2><div class="hint" id="diffMessage"></div></div></div>
      <div class="panel change"><div class="change-box good"><b id="newTitle"></b><ul id="newList"></ul></div><div class="change-box bad"><b id="removedTitle"></b><ul id="removedList"></ul></div></div>
    </section>

    <section class="section" id="index">
      <div class="section-head"><div><h2>Index & Categories</h2><div class="hint">Product line entry points</div></div></div>
      <div class="panel"><div class="category-list" id="productIndex"></div></div>
    </section>

    <section class="section" id="pages">
      <div class="section-head"><div><h2>Page Offers</h2><div class="hint">Homepage and category page captures</div></div><div class="segmented" id="pageTabs"></div></div>
      <div class="panel"><div class="offer-list" id="pageOfferList"></div></div>
    </section>

    <section class="section" id="analytics">
      <div class="section-head"><div><h2>Analytics</h2><div class="hint">Brand, product and trend distribution</div></div></div>
      <div class="grid three"><div class="panel"><h2>Brands</h2><div class="category-list" id="brandBars"></div></div><div class="panel"><h2>Products</h2><div class="category-list" id="productBars"></div></div><div class="panel"><h2>Trend</h2><svg id="trendChart" viewBox="0 0 360 220" preserveAspectRatio="none"></svg></div></div>
    </section>

    <section class="section" id="products">
      <div class="section-head"><div><h2>Product Detail</h2><div class="hint">Owned brands vs competitors</div></div><div class="segmented" id="productTabs"></div></div>
      <div class="grid two"><div class="panel"><h2>Trip.com / TrainPal</h2><div id="ownedOffers"></div></div><div class="panel"><h2>Competitors</h2><div id="competitorProductOffers"></div></div></div>
    </section>

    <section class="section" id="brands">
      <div class="section-head"><div><h2>Brand Detail</h2><div class="hint">Expandable brand offer archive</div></div></div>
      <div class="panel"><div id="competitorDetails"></div></div>
    </section>
  </main>
</div>
<script>
const DATA = {payload};
const sections = [
  ["overview","Overview","blue"], ["changes","Daily Changes","red"], ["index","Index","cyan"],
  ["pages","Page Offers","green"], ["analytics","Analytics","amber"], ["products","Products","cyan"], ["brands","Brands","blue"]
];
let platform = Object.keys(DATA).find(k => DATA[k].available) || Object.keys(DATA)[0];
let pageTab = "";
let productTab = "";
let search = "";
const $ = id => document.getElementById(id);
function esc(v) {{ return String(v ?? "").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}}[c])); }}
function cur() {{ return DATA[platform] || {{}}; }}
function scrollToId(id) {{ document.getElementById(id)?.scrollIntoView({{block:"start"}}); }}
function renderNav() {{
  const nav = sections.map(([id,label,color]) => `<button onclick="scrollToId('${{id}}')"><span class="dot ${{color}}"></span>${{label}}</button>`).join("");
  $("sideNav").innerHTML = nav;
  $("mobileNav").innerHTML = sections.map(([id,label]) => `<button class="chip" onclick="scrollToId('${{id}}')">${{label}}</button>`).join("");
}}
function renderPlatformTabs() {{
  $("platformTabs").innerHTML = Object.keys(DATA).map(name => `<button class="platform ${{name===platform?'active':''}}" data-platform="${{esc(name)}}">${{esc(name)}}</button>`).join("");
  document.querySelectorAll("[data-platform]").forEach(b => b.onclick = () => {{ platform=b.dataset.platform; pageTab=""; productTab=""; render(); }});
}}
function renderMeta() {{
  const d=cur();
  $("metaText").textContent = `${{platform}} · ${{d.date || "-"}} · Last run ${{d.lastRun || "-"}}`;
  $("statusText").textContent = d.status ? `Status: ${{d.status}}` : "";
}}
function renderKpis() {{
  const k=cur().kpis || {{}};
  const items=[["Page Offers",k.pageOffers||0,"Captured pages"],["Brand Offers",k.competitorOffers||0,"Target brand pages"],["New",k.newOffers||0,"Daily delta"],["Removed",k.removedOffers||0,"Daily delta"],["Owned",k.ownedOffers||0,"Trip.com + TrainPal"],["Other Brands",k.competitorBrands||0,"Competitor count"]];
  $("kpiGrid").innerHTML=items.map(i=>`<div class="metric"><div class="metric-label">${{i[0]}}</div><div class="metric-value">${{i[1]}}</div><div class="metric-note">${{i[2]}}</div></div>`).join("");
}}
function fmtRow(r) {{ return `${{r.brand||""}}: ${{r.offer||""}}`; }}
function renderDiff() {{
  const d=cur().diff || {{new:[],removed:[],message:""}};
  $("diffMessage").textContent=d.message || "";
  $("newTitle").textContent=`New (${{(d.new||[]).length}})`;
  $("removedTitle").textContent=`Removed (${{(d.removed||[]).length}})`;
  $("newList").innerHTML=(d.new||[]).slice(0,12).map(r=>`<li>${{esc(fmtRow(r))}}</li>`).join("") || "<li>None</li>";
  $("removedList").innerHTML=(d.removed||[]).slice(0,12).map(r=>`<li>${{esc(fmtRow(r))}}</li>`).join("") || "<li>None</li>";
}}
function productCount(v) {{ return (v.owned||[]).length + (v.trainpal||[]).length + (v.competitors||[]).length; }}
function renderIndex() {{
  const products = cur().products || {{}};
  $("productIndex").innerHTML = Object.entries(products).map(([name,val]) => `<button class="row-card" onclick="productTab='${{esc(name)}}'; renderProducts(); scrollToId('products')"><b>${{esc(name)}}</b><span class="hint"> · ${{productCount(val)}} offers</span></button>`).join("");
  $("categoryNav").innerHTML = Object.keys(products).map(name => `<button onclick="productTab='${{esc(name)}}'; renderProducts(); scrollToId('products')"><span class="dot green"></span>${{esc(name)}}</button>`).join("");
}}
function renderPages() {{
  const pages=cur().pages || {{}};
  const names=Object.keys(pages);
  if(!pageTab || !pages[pageTab]) pageTab=names[0] || "";
  $("pageTabs").innerHTML=names.map(n=>`<button class="chip ${{n===pageTab?'active':''}}" data-page="${{esc(n)}}">${{esc(n)}} ${{pages[n].length}}</button>`).join("");
  document.querySelectorAll("[data-page]").forEach(b=>b.onclick=()=>{{ pageTab=b.dataset.page; renderPages(); }});
  const rows=pages[pageTab] || [];
  $("pageOfferList").innerHTML=rows.length ? rows.map(r=>`<div class="offer"><b>${{esc(r[0])}}</b><span class="hint"> - </span>${{esc(r[1])}}</div>`).join("") : `<p class="hint">No page offers</p>`;
}}
function bars(id, rows, red=false) {{
  const max=Math.max(1,...rows.map(r=>r.count));
  $(id).innerHTML=rows.map(r=>`<div class="bar-row"><div class="bar-label" title="${{esc(r.label)}}">${{esc(r.label)}}</div><div class="bar-bg"><div class="bar-fill ${{red?'red':''}}" style="width:${{Math.max(4,r.count/max*100)}}%"></div></div><b>${{r.count}}</b></div>`).join("");
}}
function renderAnalytics() {{
  const d=cur();
  bars("brandBars", Object.entries(d.competitors||{{}}).map(([label,offers])=>({{label,count:offers.length}})).sort((a,b)=>b.count-a.count).slice(0,9));
  bars("productBars", Object.entries(d.products||{{}}).map(([label,val])=>({{label,count:productCount(val)}})).sort((a,b)=>b.count-a.count), true);
  trend(d.trend||[]);
}}
function trend(rows) {{
  const svg=$("trendChart");
  if(!rows.length) {{ svg.innerHTML='<text x="20" y="110" fill="#667085">No trend data</text>'; return; }}
  const w=360,h=220,p=30,max=Math.max(1,...rows.flatMap(r=>[r.new||0,r.removed||0])),step=rows.length>1?(w-p*2)/(rows.length-1):1;
  const pts=k=>rows.map((r,i)=>`${{p+i*step}},${{h-p-((r[k]||0)/max)*(h-p*2)}}`).join(" ");
  svg.innerHTML=`<rect x="0" y="0" width="${{w}}" height="${{h}}" rx="8" fill="rgba(255,255,255,.28)"/><line x1="${{p}}" y1="${{h-p}}" x2="${{w-p}}" y2="${{h-p}}" stroke="rgba(16,24,40,.18)"/><polyline points="${{pts('new')}}" fill="none" stroke="#099250" stroke-width="4" stroke-linecap="round"/><polyline points="${{pts('removed')}}" fill="none" stroke="#e31b54" stroke-width="4" stroke-linecap="round"/>${{rows.map((r,i)=>`<text x="${{p+i*step}}" y="${{h-8}}" text-anchor="middle" font-size="10" fill="#667085">${{esc(r.date)}}</text>`).join("")}}`;
}}
function renderProducts() {{
  const products=cur().products||{{}};
  const names=Object.keys(products);
  if(!productTab || !products[productTab]) productTab=names[0] || "";
  $("productTabs").innerHTML=names.map(n=>`<button class="chip ${{n===productTab?'active':''}}" data-product="${{esc(n)}}">${{esc(n)}}</button>`).join("");
  document.querySelectorAll("[data-product]").forEach(b=>b.onclick=()=>{{ productTab=b.dataset.product; renderProducts(); }});
  const p=products[productTab] || {{owned:[],trainpal:[],competitors:[]}};
  const ownedRows = p.owned && p.owned.length ? p.owned : (p.trainpal||[]).map(o=>["TrainPal",o]);
  $("ownedOffers").innerHTML=ownedRows.length ? `<div class="offer-list">${{ownedRows.map(r=>`<div class="offer"><b>${{esc(r[0])}}</b>: ${{esc(r[1])}}</div>`).join("")}}</div>` : `<p class="hint">No owned offers</p>`;
  $("competitorProductOffers").innerHTML=(p.competitors||[]).length ? `<div class="offer-list">${{p.competitors.map(r=>`<div class="offer"><b>${{esc(r[0])}}</b>: ${{esc(r[1])}}</div>`).join("")}}</div>` : `<p class="hint">No competitor offers</p>`;
}}
function renderCompetitors() {{
  const rows=Object.entries(cur().competitors||{{}}).filter(([b])=>b.toLowerCase().includes(search.toLowerCase()));
  $("competitorDetails").innerHTML=rows.length ? rows.map(([b,offers])=>`<div class="brand-offer-card collapsed"><div class="brand-offer-head"><button type="button" data-brand-toggle><span class="chevron">⌄</span><span>${{esc(b)}}</span></button><span class="count">${{offers.length}} offers</span></div><div class="detail"><ul>${{offers.map(o=>`<li>${{esc(o)}}</li>`).join("")}}</ul></div></div>`).join("") : `<p class="hint">No matching brand</p>`;
  document.querySelectorAll("[data-brand-toggle]").forEach(button => {{
    button.onclick = () => button.closest(".brand-offer-card").classList.toggle("collapsed");
  }});
}}
function render() {{ renderNav(); renderPlatformTabs(); renderMeta(); renderKpis(); renderDiff(); renderIndex(); renderPages(); renderAnalytics(); renderProducts(); renderCompetitors(); }}
$("brandSearch").oninput=e=>{{ search=e.target.value; renderCompetitors(); }};
render();
</script>
</body>
</html>"""


def main() -> None:
    data = {}
    dates = []
    for name, folder in SOURCES.items():
        item = prepare_platform(name, folder)
        data[name] = item
        if item.get("date"):
            dates.append(item["date"])

    date = max(dates) if dates else datetime.now().strftime("%Y-%m-%d")
    text = render_preview(data)

    for folder in [DOCS_DIR, LOCAL_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(text, encoding="utf-8")
        (folder / f"dashboard_{date}.html").write_text(text, encoding="utf-8")

    preview = DOCS_DIR / "ios26-preview.html"
    preview.write_text(text, encoding="utf-8")

    print("Glass dashboard generated:")
    print(f"- {DOCS_DIR / 'index.html'}")
    print(f"- {DOCS_DIR / f'dashboard_{date}.html'}")
    print(f"- {preview}")


if __name__ == "__main__":
    main()
