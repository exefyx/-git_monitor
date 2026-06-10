# -*- coding: utf-8 -*-
"""
UNiDAYS Offer Monitor v4

本版输出重点：
- 不再生成 Excel
- 直接生成文字版日报 daily_report_YYYY-MM-DD.md
- 页面 offer 和竞品 offer 都在 md 里直接展示
- 每条只展示：品牌：offer
- 不展示网页链接
"""

import argparse
import csv
import json
import os
import random
import re
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


TODAY = str(date.today())

STATE_FILE = Path("unidays_state.json")
OUTPUT_DIR = Path("unidays_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

CRAWL_DELAY_MIN = float(os.getenv("CRAWL_DELAY_MIN", "6"))
CRAWL_DELAY_MAX = float(os.getenv("CRAWL_DELAY_MAX", "16"))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def pause_between_pages(label: str = "") -> None:
    delay = random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX)
    if label:
        print(f"Waiting {delay:.1f}s before next page: {label}")
    time.sleep(delay)


def random_page_wait(page, min_seconds: float, max_seconds: float) -> None:
    page.wait_for_timeout(int(random.uniform(min_seconds, max_seconds) * 1000))


def install_stealth(context) -> None:
    context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """
    )


PAGE_URLS = {
    "首页": "https://www.myunidays.com/GB/en-GB/campaigns/summer-sorted?rd=true",
    "Travel & Entertainment": "https://www.myunidays.com/GB/en-GB/categories/travel-entertainment",
    "Transport": "https://www.myunidays.com/GB/en-GB/categories/travel-entertainment_travel-entertainment-transport",
}


BRAND_URLS = {
    "Trip.com": "https://www.myunidays.com/GB/en-GB/partners/d5a26c48-2f9b-4f05-9beb-c5b55a930fb4/view",
    "Trainline": "https://www.myunidays.com/GB/en-GB/partners/70e4ad70-1abf-4f74-8a2e-b0e8e2b55f3d/view",
    "TrainPal": "https://www.myunidays.com/GB/en-GB/partners/4dbf516a-3ebe-4f5b-bc9e-c6d46cbd8062/view",
    "FlixBus": "https://www.myunidays.com/GB/en-GB/partners/39c1c5bc-a33b-4087-9354-9b7a57608ceb/view",
    "Omio": "https://www.myunidays.com/GB/en-GB/partners/27750706-57ee-4812-835c-89ca79f14383/view",
    "National Express": "https://www.myunidays.com/GB/en-GB/partners/74b98579-a25b-4b56-a95d-3c89c015c537/view",
    "Klook": "https://www.myunidays.com/GB/en-GB/partners/216af2f7-8367-4cd2-bc96-1f0f5605a88d/view",
    "Eurostar": "https://www.myunidays.com/GB/en-GB/partners/2c1aad9c-8703-4f59-a5db-5570b9275927/view",
}


KNOWN_BRANDS = [
    "Trip.com",
    "Trainline",
    "TrainPal",
    "FlixBus",
    "Omio",
    "National Express",
    "Klook",
    "Eurostar",
    "Dyson",
    "GHD",
    "ghd",
    "Boots",
    "LOOKFANTASTIC",
    "The Perfume Shop",
    "Shark",
    "SharkNinja",
    "Shark Beauty",
    "Charlotte Tilbury",
    "Cult Beauty",
    "Laser Clinics",
    "Alton Towers Resort",
    "Thorpe Park",
    "LEGOLAND Windsor Resort",
    "Chessington World of Adventures Resort",
    "Merlin Entertainments",
    "M&S Food",
    "Black Sheep Coffee",
    "Hostelworld",
    "loveholidays",
    "Macdonald Hotels",
    "Macdonald Hotel & Resorts",
    "Lastminute.com",
    "Viator",
    "Virgin Atlantic",
    "Emirates",
    "Airalo",
    "Qatar Airways",
    "ASOS",
    "Gymshark",
    "Amazon",
    "PrettyLittleThing",
    "Currys",
    "Deliveroo",
    "Sephora",
    "KFC",
    "OnePlus",
    "Audible",
    "Weekday",
    "Wowcher",
    "Avanti West Coast",
    "Greyhound Australia",
]


PRODUCT_KEYWORDS = {
    "eSIM / SIM": [
        "esim",
        "eSIM",
        "sim",
    ],
    "Flights": [
        "flight",
        "flights",
        "airline",
        "airways",
        "emirates",
        "virgin atlantic",
        "qatar airways",
    ],
    "Car Rental": [
        "car rental",
        "car hire",
    ],
    "Japan Train / Japan Railway": [
        "japan railway",
        "japan train",
        "japan travel",
        "jr pass",
    ],
    "Railcard": [
        "railcard",
        "16-25 railcard",
        "26-30 railcard",
        "saver railcard",
    ],
    "UK & Europe Train Tickets": [
        "train",
        "trains",
        "rail",
        "uk train",
        "eu train",
        "europe train",
        "train tickets",
        "avanti west coast",
    ],
    "Bus / Coach": [
        "bus",
        "buses",
        "coach",
        "coaches",
        "flixbus",
        "national express",
        "greyhound",
    ],
    "Hotels / Accommodation": [
        "hotel",
        "hotels",
        "hostel",
        "stay",
        "holiday",
        "holidays",
        "accommodation",
    ],
    "Tours & Tickets": [
        "tour",
        "tours",
        "ticket",
        "tickets",
        "attraction",
        "activities",
        "alton towers",
        "thorpe park",
        "legoland",
        "chessington",
        "merlin",
        "viator",
    ],
}


OFFER_PATTERN = re.compile(
    r"("
    r"\d+(?:\.\d+)?\s*%\s*(off|discount)?|"
    r"£\s*\d+(?:\.\d+)?|"
    r"\boff\b|"
    r"\bdiscount\b|"
    r"\bsave\b|"
    r"\bup\s+to\b|"
    r"\bfree\b|"
    r"\bsale\b|"
    r"\bdeal\b"
    r")",
    re.IGNORECASE,
)


NOISE_EXACT = {
    "get now",
    "save",
    "saved",
    "terms",
    "terms and conditions",
    "log in",
    "join",
    "unidays",
    "all",
    "online",
    "in-store",
    "view all",
    "request student offer",
    "request a student offer",
    "book airport transfers",
}


NOISE_CONTAINS = [
    "privacy policy",
    "cookie",
    "download the app",
    "sign in",
    "create account",
    "accessibility",
    "terms of service",
    "skip to footer",
    "request student offer",
    "request a student offer",
    "book airport transfers",
]


STOP_HEADINGS = [
    "similar brands",
    "similar offers",
    "related brands",
    "popular offers",
    "recommended",
    "about ",
    "more from",
    "you may also like",
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def normal_key(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^\w£%]+", " ", text)
    return clean_text(text)


def strip_common_prefixes(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"^Online\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^In-store\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Get now\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Saved\s+", "", text, flags=re.IGNORECASE)
    return clean_text(text)


def is_noise(text: str) -> bool:
    text = clean_text(text)
    lower = text.lower()

    if not text:
        return True

    if len(text) <= 2:
        return True

    if lower in NOISE_EXACT:
        return True

    return any(part in lower for part in NOISE_CONTAINS)


def looks_like_offer(text: str) -> bool:
    text = strip_common_prefixes(text)

    if is_noise(text):
        return False

    if len(text) < 4 or len(text) > 180:
        return False

    return bool(OFFER_PATTERN.search(text))


def remove_duplicate_phrase(text: str) -> str:
    text = clean_text(text)

    # 完全重复的半句：A A
    words = text.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if normal_key(" ".join(words[:half])) == normal_key(" ".join(words[half:])):
            return " ".join(words[:half])

    # 形如：Offer Brand Offer
    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        pattern = re.compile(rf"\s+{re.escape(brand)}\s+", re.IGNORECASE)
        match = pattern.search(text)

        if not match:
            continue

        left = text[: match.start()].strip(" ,;-")
        right = text[match.end() :].strip(" ,;-")

        if left and right and normal_key(left) == normal_key(right):
            return left

    return text


def split_brand_and_offer(
    raw_text: str,
    fallback_brand: str = "",
) -> Tuple[str, str]:
    text = strip_common_prefixes(raw_text)
    text = remove_duplicate_phrase(text)

    brand = clean_text(fallback_brand)
    offer = text

    # 形如：Brand, Offer
    if "," in text:
        left, right = text.split(",", 1)
        left = clean_text(left)
        right = clean_text(right)

        if 2 <= len(left) <= 45 and not looks_like_offer(left) and looks_like_offer(right):
            brand = left
            offer = right

    # 形如：Brand Offer
    if not brand:
        for known_brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
            if text.lower().startswith(known_brand.lower() + " "):
                possible_offer = clean_text(text[len(known_brand) :])
                if looks_like_offer(possible_offer):
                    brand = known_brand
                    offer = possible_offer
                    break

    offer = remove_duplicate_phrase(strip_common_prefixes(offer))
    offer = clean_text(offer)

    if brand:
        # 防止 offer 里再次以品牌开头
        offer = re.sub(rf"^{re.escape(brand)}\s+", "", offer, flags=re.IGNORECASE).strip(" ,;-")

    return brand, offer


def classify_product(brand: str, offer: str) -> str:
    combined = f"{brand} {offer}".lower()

    for product_type, keywords in PRODUCT_KEYWORDS.items():
        if any(keyword.lower() in combined for keyword in keywords):
            return product_type

    return "Other"


def discount_score(offer: str) -> float:
    text = str(offer).lower()

    percent_values = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
    if percent_values:
        return max(float(x) for x in percent_values)

    pound_values = re.findall(r"£\s*(\d+(?:\.\d+)?)", text)
    if pound_values:
        return max(float(x) for x in pound_values)

    return 0.0


def save_login_state():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            locale="en-GB",
        )

        page = context.new_page()
        page.goto("https://www.myunidays.com/GB/en-GB", wait_until="domcontentloaded")

        print("请在弹出的浏览器里手动登录 UNiDAYS。")
        print("登录完成并确认页面正常显示后，回到终端按 Enter。")
        input("按 Enter 保存登录状态：")

        context.storage_state(path=str(STATE_FILE))
        browser.close()

    print(f"登录状态已保存：{STATE_FILE}")


def dismiss_popups(page):
    for text in [
        "Accept all",
        "Accept All",
        "I agree",
        "Agree",
        "Got it",
        "Close",
        "No thanks",
    ]:
        try:
            locator = page.get_by_text(text, exact=True)
            if locator.count() > 0:
                locator.first.click(timeout=1200)
                page.wait_for_timeout(500)
        except Exception:
            pass


def scroll_to_bottom(page, max_rounds: int = 40):
    last_height = 0
    stable_count = 0

    for _ in range(max_rounds):
        page.mouse.wheel(0, 2200)
        page.wait_for_timeout(900)

        current_height = page.evaluate("document.body.scrollHeight")

        if current_height == last_height:
            stable_count += 1
        else:
            stable_count = 0
            last_height = current_height

        if stable_count >= 4:
            break


def extract_headings(page) -> List[Dict[str, object]]:
    js = """
    () => {
        const visible = (el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();

            return (
                rect.width > 20 &&
                rect.height > 8 &&
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                style.opacity !== '0'
            );
        };

        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();

        const nodes = Array.from(
            document.querySelectorAll('h1,h2,h3,h4,[role="heading"]')
        );

        return nodes
            .filter(visible)
            .map(el => {
                const rect = el.getBoundingClientRect();

                return {
                    text: clean(el.innerText || el.textContent || ''),
                    top: rect.top + window.scrollY,
                    left: rect.left
                };
            })
            .filter(x => x.text && x.text.length <= 100);
    }
    """

    try:
        data = page.evaluate(js)
    except Exception:
        return []

    headings = []
    seen = set()

    for item in data:
        text = clean_text(item.get("text", ""))
        lower = text.lower()

        if not text:
            continue

        if lower in NOISE_EXACT:
            continue

        if "unidays" in lower:
            continue

        key = (text, round(float(item.get("top", 0))))
        if key in seen:
            continue

        seen.add(key)
        headings.append(item)

    return headings


def find_section(card_top: float, headings: List[Dict[str, object]]) -> str:
    before = [
        h for h in headings
        if float(h.get("top", 0)) <= card_top - 5
    ]

    if not before:
        return ""

    before = sorted(before, key=lambda x: float(x.get("top", 0)))
    section = clean_text(before[-1].get("text", ""))

    if section.lower() in {
        "the summer edit",
        "student offers",
        "offers",
        "travel & entertainment",
    }:
        return ""

    return section


def extract_offer_items(page) -> List[Dict[str, object]]:
    js = """
    () => {
        const offerRe = /(off|discount|save|£\\s*\\d+(?:\\.\\d+)?|\\d+(?:\\.\\d+)?\\s*%|free|deal|sale|up\\s+to)/i;

        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();

        const visible = (el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();

            return (
                rect.width > 20 &&
                rect.height > 8 &&
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                style.opacity !== '0'
            );
        };

        const elements = Array.from(
            document.querySelectorAll('a, article, li, div, section, button, p, span, h1, h2, h3, h4')
        );

        const items = [];
        const seen = new Set();

        for (const el of elements) {
            if (!visible(el)) continue;

            const text = clean(el.innerText || el.textContent || '');

            if (!text) continue;
            if (text.length < 4 || text.length > 220) continue;
            if (!offerRe.test(text)) continue;

            const lineCount = (el.innerText || '').split('\\n').filter(Boolean).length;
            if (lineCount > 3) continue;

            let card =
                el.closest('a') ||
                el.closest('article') ||
                el.closest('li') ||
                el.parentElement ||
                el;

            for (let i = 0; i < 4 && card && card.parentElement; i++) {
                const rect = card.getBoundingClientRect();
                const imgCount = card.querySelectorAll ? card.querySelectorAll('img').length : 0;

                if (imgCount > 0 && rect.width >= 80 && rect.height >= 40 && rect.height <= 650) {
                    break;
                }

                card = card.parentElement;
            }

            const rect = el.getBoundingClientRect();

            const imgs = Array.from(card.querySelectorAll ? card.querySelectorAll('img') : [])
                .map(img => ({
                    alt: clean(img.alt || ''),
                    title: clean(img.title || ''),
                    src: img.currentSrc || img.src || ''
                }));

            const cardText = clean(card.innerText || card.textContent || '');

            const key = [
                Math.round(rect.top + window.scrollY),
                Math.round(rect.left),
                text
            ].join('|');

            if (seen.has(key)) continue;
            seen.add(key);

            items.push({
                offer: text,
                top: rect.top + window.scrollY,
                left: rect.left,
                cardText: cardText,
                images: imgs
            });
        }

        items.sort((a, b) => {
            if (a.top !== b.top) return a.top - b.top;
            return a.left - b.left;
        });

        return items;
    }
    """

    try:
        return page.evaluate(js) or []
    except Exception:
        return []


def infer_brand_from_item(item: Dict[str, object]) -> str:
    combined = ""
    combined += " " + str(item.get("cardText", ""))
    combined += " " + str(item.get("offer", ""))

    for img in item.get("images", []) or []:
        combined += " " + str(img.get("alt", ""))
        combined += " " + str(img.get("title", ""))
        combined += " " + str(img.get("src", ""))

    combined_lower = combined.lower()

    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        if brand.lower() in combined_lower:
            return brand

    for img in item.get("images", []) or []:
        for candidate in [img.get("alt", ""), img.get("title", "")]:
            candidate = clean_text(candidate)
            candidate = re.sub(r"\blogo\b", "", candidate, flags=re.IGNORECASE).strip()

            if 2 <= len(candidate) <= 40 and not OFFER_PATTERN.search(candidate):
                return candidate

    return ""


def parse_page_items(
    page_name: str,
    url: str,
    items: List[Dict[str, object]],
    headings: List[Dict[str, object]],
) -> List[Dict[str, str]]:
    rows = []
    seen = set()

    for item in items:
        raw_offer = clean_text(item.get("offer", ""))
        inferred_brand = infer_brand_from_item(item)
        brand, offer = split_brand_and_offer(raw_offer, inferred_brand)

        if not looks_like_offer(offer):
            continue

        if is_noise(brand) or brand.lower() in {"exclusive", "27 days", "skip to footer"}:
            brand = ""

        if not brand:
            continue

        section = find_section(float(item.get("top", 0)), headings)
        product_type = classify_product(brand, offer)

        key = (
            page_name,
            section.lower(),
            normal_key(brand),
            normal_key(offer),
        )

        if key in seen:
            continue

        seen.add(key)

        rows.append(
            {
                "date": TODAY,
                "source_type": "页面",
                "page": page_name,
                "section": section,
                "brand": brand,
                "offer": offer,
                "product_type": product_type,
            }
        )

    return rows


def extract_brand_offers_from_body(
    page_name: str,
    body_text: str,
) -> List[Dict[str, str]]:
    lines = [
        clean_text(x)
        for x in body_text.splitlines()
        if clean_text(x)
    ]

    rows = []
    seen = set()

    started = False
    found_heading = False

    for line in lines:
        lower = line.lower()

        if "student offers from" in lower or "offers from" in lower or "offers for everyone" in lower:
            started = True
            found_heading = True
            continue

        if found_heading and any(stop in lower for stop in STOP_HEADINGS):
            break

        if not found_heading:
            started = True

        if not started:
            continue

        brand, offer = split_brand_and_offer(line, page_name)

        if not looks_like_offer(offer):
            continue

        if is_noise(offer):
            continue

        if brand.lower() != page_name.lower():
            brand = page_name

        key = (normal_key(page_name), normal_key(offer))
        if key in seen:
            continue

        seen.add(key)

        rows.append(
            {
                "date": TODAY,
                "source_type": "品牌页",
                "page": page_name,
                "section": "",
                "brand": page_name,
                "offer": offer,
                "product_type": classify_product(page_name, offer),
            }
        )

    return rows


def capture_page(context, page_name: str, url: str, source_type: str, save_debug: bool = True):
    print(f"正在抓取：[{source_type}] {page_name}")

    page = context.new_page()

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass

        random_page_wait(page, 2.0, 4.5)
        dismiss_popups(page)
        scroll_to_bottom(page)
        random_page_wait(page, 1.0, 3.0)

        if save_debug:
            debug_dir = OUTPUT_DIR / f"debug_{TODAY}"
            debug_dir.mkdir(exist_ok=True)
            safe_name = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", page_name)

            try:
                page.screenshot(path=str(debug_dir / f"{safe_name}.png"), full_page=True)
            except Exception:
                pass

        body_text = page.locator("body").inner_text(timeout=10000)

        if source_type == "品牌页":
            rows = extract_brand_offers_from_body(page_name, body_text)
        else:
            headings = extract_headings(page)
            items = extract_offer_items(page)
            rows = parse_page_items(page_name, url, items, headings)

        print(f"完成：{page_name}，抓到 {len(rows)} 条 offer")
        return rows

    except Exception as exc:
        print(f"失败：{page_name}，原因：{exc}")
        return []

    finally:
        page.close()


def write_csv(path: Path, rows: List[Dict[str, str]]):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    columns = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def get_previous_clean_file() -> Optional[Path]:
    files = sorted(OUTPUT_DIR.glob("clean_offers_*.json"))
    today_file = OUTPUT_DIR / f"clean_offers_{TODAY}.json"
    files = [file for file in files if file != today_file]

    if not files:
        return None

    return files[-1]


def make_diff_text(today_rows: List[Dict[str, str]]) -> List[str]:
    previous_file = get_previous_clean_file()

    if not previous_file:
        return [
            "• 新增 Offer：今日为文字版清洗脚本首日基准，暂不进行环比判断",
            "• 下线 Offer：今日为文字版清洗脚本首日基准，暂不进行环比判断",
            "• 折扣力度提升：需结合后续每日数据判断",
            "• 折扣力度下降：需结合后续每日数据判断",
        ]

    previous_rows = json.loads(previous_file.read_text(encoding="utf-8"))

    today_set = {
        (
            row.get("source_type", ""),
            row.get("page", ""),
            row.get("brand", ""),
            normal_key(row.get("offer", "")),
        )
        for row in today_rows
    }

    previous_set = {
        (
            row.get("source_type", ""),
            row.get("page", ""),
            row.get("brand", ""),
            normal_key(row.get("offer", "")),
        )
        for row in previous_rows
    }

    today_map = {
        (
            row.get("source_type", ""),
            row.get("page", ""),
            row.get("brand", ""),
            normal_key(row.get("offer", "")),
        ): row
        for row in today_rows
    }

    previous_map = {
        (
            row.get("source_type", ""),
            row.get("page", ""),
            row.get("brand", ""),
            normal_key(row.get("offer", "")),
        ): row
        for row in previous_rows
    }

    new_items = [today_map[key] for key in sorted(today_set - previous_set)]
    removed_items = [previous_map[key] for key in sorted(previous_set - today_set)]

    if new_items:
        new_text = "；".join(
            f"{item.get('brand', '')}：{item.get('offer', '')}"
            for item in new_items[:10]
        )
    else:
        new_text = "暂无"

    if removed_items:
        removed_text = "；".join(
            f"{item.get('brand', '')}：{item.get('offer', '')}"
            for item in removed_items[:10]
        )
    else:
        removed_text = "暂无"

    return [
        f"• 新增 Offer：{new_text}",
        f"• 下线 Offer：{removed_text}",
        "• 折扣力度提升：需结合具体文案复核",
        "• 折扣力度下降：需结合具体文案复核",
    ]


def group_by_page(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {}

    for row in rows:
        result.setdefault(row.get("page", ""), []).append(row)

    return result


def group_by_brand(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {}

    for row in rows:
        result.setdefault(row.get("brand", ""), []).append(row)

    return result


def group_by_product(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {}

    for row in rows:
        result.setdefault(row.get("product_type", "Other"), []).append(row)

    return result


def format_offer_line(row: Dict[str, str]) -> str:
    return f"{row.get('brand', '')}：{row.get('offer', '')}"


def make_product_summary_lines(competitor_rows: List[Dict[str, str]]) -> List[str]:
    product_order = [
        "UK & Europe Train Tickets",
        "Japan Train / Japan Railway",
        "Railcard",
        "Bus / Coach",
        "Flights",
        "Hotels / Accommodation",
        "Tours & Tickets",
        "Car Rental",
        "eSIM / SIM",
        "Other",
    ]

    grouped = group_by_product(competitor_rows)
    lines = []

    for product in product_order:
        rows = grouped.get(product, [])

        if not rows:
            continue

        trainpal_rows = [
            row for row in rows
            if row.get("brand", "").lower() == "trainpal"
        ]

        competitor_only_rows = [
            row for row in rows
            if row.get("brand", "").lower() != "trainpal"
        ]

        competitor_only_rows = sorted(
            competitor_only_rows,
            key=lambda row: discount_score(row.get("offer", "")),
            reverse=True,
        )

        trainpal_text = "；".join(row["offer"] for row in trainpal_rows[:5]) or "暂无"
        competitor_text = "；".join(format_offer_line(row) for row in competitor_only_rows[:5]) or "暂无"

        lines.append(f"- {product}")
        lines.append(f"  TrainPal：{trainpal_text}")
        lines.append(f"  竞品重点：{competitor_text}")

        if trainpal_rows:
            lines.append("  关注点：已覆盖 TrainPal 对应产品，需持续跟踪竞品折扣变化。")
        else:
            lines.append("  关注点：TrainPal 暂无对应产品 offer，需关注竞品覆盖情况。")

    return lines


def make_key_competitor_lines(competitor_rows: List[Dict[str, str]]) -> List[str]:
    grouped = group_by_product(
        [
            row for row in competitor_rows
            if row.get("brand", "").lower() != "trainpal"
        ]
    )

    product_order = [
        "UK & Europe Train Tickets",
        "Japan Train / Japan Railway",
        "Railcard",
        "Bus / Coach",
        "Flights",
        "Hotels / Accommodation",
        "Tours & Tickets",
        "Car Rental",
        "eSIM / SIM",
        "Other",
    ]

    lines = []

    for product in product_order:
        rows = grouped.get(product, [])

        if not rows:
            continue

        rows = sorted(
            rows,
            key=lambda row: discount_score(row.get("offer", "")),
            reverse=True,
        )

        offers = "；".join(format_offer_line(row) for row in rows[:3])
        lines.append(f"• {product}：{offers}")

    return lines


def make_report(
    page_rows: List[Dict[str, str]],
    competitor_rows: List[Dict[str, str]],
    all_rows: List[Dict[str, str]],
) -> str:
    lines = []

    lines.append("一、UNiDAYS")
    lines.append("")
    lines.append(f"日报日期：{TODAY}")
    lines.append("")

    lines.append("1. 页面offer")

    if not page_rows:
        lines.append("暂无抓取到页面 offer。")
    else:
        page_grouped = group_by_page(page_rows)

        for page_name in PAGE_URLS.keys():
            rows = page_grouped.get(page_name, [])
            if not rows:
                continue

            lines.append(f"- {page_name}")

            for row in rows:
                lines.append(f"  {format_offer_line(row)}")

    lines.append("")
    lines.append("2. 竞品offer监控")
    lines.append("")
    lines.append("2.1 分产品监控情况")
    lines.extend(make_product_summary_lines(competitor_rows))
    lines.append("")
    lines.append("2.2 今日 vs 昨日对比")
    lines.extend(make_diff_text(all_rows))
    lines.append("")
    lines.append("2.3 竞品offer")

    if not competitor_rows:
        lines.append("暂无抓取到竞品 offer。")
    else:
        brand_grouped = group_by_brand(competitor_rows)

        for brand_name in BRAND_URLS.keys():
            rows = brand_grouped.get(brand_name, [])
            if not rows:
                continue

            lines.append(f"- {brand_name}")

            for row in rows:
                lines.append(f"  {row.get('offer', '')}")

    return "\n".join(lines)


def dedupe_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped = []
    seen = set()

    for row in rows:
        key = (
            row.get("source_type", ""),
            row.get("page", ""),
            normal_key(row.get("brand", "")),
            normal_key(row.get("offer", "")),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    return deduped


def run_monitor(show: bool = False, no_debug: bool = False):
    if not STATE_FILE.exists():
        raise FileNotFoundError(
            "没有找到 unidays_state.json，请先运行：python .\\scripts\\unidays_monitor.py --login"
        )

    page_rows: List[Dict[str, str]] = []
    competitor_rows: List[Dict[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not show,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        context = browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1600, "height": 1000},
            locale="en-GB",
            timezone_id="Europe/London",
            user_agent=random.choice(USER_AGENTS),
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
        )
        install_stealth(context)

        for page_name, url in PAGE_URLS.items():
            pause_between_pages(page_name)
            rows = capture_page(
                context=context,
                page_name=page_name,
                url=url,
                source_type="页面",
                save_debug=not no_debug,
            )
            page_rows.extend(rows)

        for brand_name, url in BRAND_URLS.items():
            pause_between_pages(brand_name)
            rows = capture_page(
                context=context,
                page_name=brand_name,
                url=url,
                source_type="品牌页",
                save_debug=not no_debug,
            )
            competitor_rows.extend(rows)

        browser.close()

    page_rows = dedupe_rows(page_rows)
    competitor_rows = dedupe_rows(competitor_rows)
    all_rows = page_rows + competitor_rows

    clean_json = OUTPUT_DIR / f"clean_offers_{TODAY}.json"
    page_csv = OUTPUT_DIR / f"page_offers_{TODAY}.csv"
    competitor_csv = OUTPUT_DIR / f"competitor_offers_{TODAY}.csv"
    report_file = OUTPUT_DIR / f"daily_report_{TODAY}.md"

    clean_json.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_csv(page_csv, page_rows)
    write_csv(competitor_csv, competitor_rows)

    report = make_report(
        page_rows=page_rows,
        competitor_rows=competitor_rows,
        all_rows=all_rows,
    )

    report_file.write_text(report, encoding="utf-8")

    print("\n输出完成：")
    print(f"- 文字日报：{report_file}")
    print(f"- 页面 offer CSV：{page_csv}")
    print(f"- 竞品 offer CSV：{competitor_csv}")
    print(f"- 清洗数据 JSON：{clean_json}")


def main():
    parser = argparse.ArgumentParser(
        description="UNiDAYS Offer Monitor v4",
    )

    parser.add_argument(
        "--login",
        action="store_true",
        help="手动登录 UNiDAYS 并保存登录状态",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="运行每日抓取",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="显示浏览器窗口，方便调试",
    )

    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="不保存截图",
    )

    args = parser.parse_args()

    if args.login:
        save_login_state()
        return

    if args.run:
        run_monitor(
            show=args.show,
            no_debug=args.no_debug,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
