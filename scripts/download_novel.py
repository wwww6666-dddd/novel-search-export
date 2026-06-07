"""
Download novel chapters from 30dushu.com and DedeCMS sites.
Optimized for speed with async concurrent downloads.
Supports UTF-8 and GBK encoding.

Usage:
    python download_novel.py <book_url> [output_path]
    python download_novel.py https://30dushu.com/book/76152/
    python download_novel.py https://fxshu.top/book/12345/ --merge
"""

import asyncio, aiohttp, re, sys, json, os, argparse
from html import unescape
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
sem = asyncio.Semaphore(8)

# === Anti-Scrape Detection ===

# Pattern categories for anti-scrape page detection.
# Each category maps to a recommended skill/tool for bypassing the block.
ANTI_SCRAPE_SIGNALS = {
    "cloudflare": [
        r"cf-browser-verification", r"challenge-platform", r"_cf_chl_opt",
        r"Checking your browser", r"Just a moment", r"ray id",
        r"cf-wrapper", r"cfl-v2",
    ],
    "captcha": [
        r"captcha", r"verifyCode", r"g-recaptcha",
        "验证码", "请输入验证码", "点击验证",
    ],
    "rate_limit": [
        "访问太频繁", "操作太频繁", "您的IP暂时被限制",
        r"too many requests", r"rate limit", r"429",
    ],
    "login_required": [
        "请先登录", "登录后查看", "未登录", r"login required",
    ],
    "js_rendered": [
        r"enable JavaScript", "请启用JavaScript",
        r"noscript", r"You need to enable JavaScript",
    ],
    "waf_block": [
        "安全检查", "安全验证",
        r"security check", r"blocked", r"access denied",
        "请求被拦截", "暂时关闭",
    ],
}

# Block type -> (recommended skill, example action, severity)
SKILL_ROUTING = {
    "cloudflare":    ("browserbase-cli",  "use Browserbase with residential proxy", "hard"),
    "captcha":       ("browser",          "use Playwright headful to solve CAPTCHA", "hard"),
    "rate_limit":    ("browser",          "add delay + retry, or use browser with cookie-sync", "soft"),
    "login_required":("browser+cookie-sync", "sync cookies from local Chrome, then browse", "hard"),
    "js_rendered":   ("playwright",       "use Playwright to render JS and extract text", "soft"),
    "waf_block":     ("browserbase-cli",  "use Browserbase residential proxy to bypass WAF", "hard"),
}

def diagnose_block(response_text, status_code=200):
    """Analyze response for anti-scrape signals. Returns (block_type, signals_found) or (None, [])."""
    if status_code in (403, 503):
        return ("waf_block", [f"HTTP {status_code}"])
    if status_code == 429:
        return ("rate_limit", ["HTTP 429 Too Many Requests"])
    # Pattern matching — run on any non-empty response (even short pages)
    if response_text and len(response_text.strip()) >= 2:
        for block_type, patterns in ANTI_SCRAPE_SIGNALS.items():
            results = []
            for pat in patterns:
                if re.search(pat, response_text, re.IGNORECASE):
                    results.append(pat)
            if results:
                return (block_type, results)
    # Truly empty (under 3 chars stripped) with no patterns = JS-rendered stub
    if not response_text or len(response_text.strip()) < 3:
        return ("js_rendered", ["empty or near-empty response (likely JS-rendered)"])
    return (None, [])

def print_diagnostic(block_type, signals, context=""):
    """Print a structured diagnostic and skill recommendation."""
    if not block_type:
        return False

    route = SKILL_ROUTING.get(block_type, (None, "manual investigation", "unknown"))
    skill, action, severity = route

    print(f"\n{'='*60}")
    print(f"  ANTI-SCRAPE DETECTED [{severity.upper()}]")
    print(f"  Type:   {block_type}")
    print(f"  Signal: {signals[0]}")
    if context:
        print(f"  Where:  {context}")
    print(f"  Action: {action}")
    print(f"  Skill:  ${skill}" if skill else "")
    print(f"{'='*60}\n")
    return True

# === 30dushu.com pattern ===

async def get_chapter_list_30dushu(session, base_url, book_path):
    """Fetch and parse 30dushu TOC page, return sorted chapter list."""
    async with session.get(base_url + book_path, timeout=15) as resp:
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    chapters = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if re.match(r"第d+章", text) or any(kw in text for kw in ["番外", "尾声", "后记", "终章"]):
            href = a["href"]
            if not href.startswith("http"):
                # Handle relative paths: /read/{bid}/{cid}.html
                if href.startswith("/"):
                    href = base_url + href
                else:
                    href = base_url + "/" + href
            chapters.append({"title": text, "url": href})

    # Deduplicate by title
    seen = set()
    unique = []
    for ch in chapters:
        if ch["title"] not in seen:
            seen.add(ch["title"])
            unique.append(ch)

    def sort_key(ch):
        m = re.search(r"第s*(d+)s*章", ch["title"])
        return int(m.group(1)) if m else 9999
    unique.sort(key=sort_key)
    return unique

async def download_chapter_30dushu(session, ch):
    """Download a single chapter, handling multi-page content."""
    async with sem:
        try:
            async with session.get(ch["url"], timeout=15) as resp:
                html = await resp.text()
            bt, sigs = diagnose_block(html, resp.status)
            if bt:
                print_diagnostic(bt, sigs, ch["title"])
                return {"title": ch["title"], "content": "", "num": 0, "_blocked": True, "_block_type": bt}
            match = re.search(r'<div[^>]*id="(?:BookText|content)"[^>]*>(.*?)</div>', html, re.DOTALL)
            page_match = re.search(r"(d+)s*/s*(d+)", html)
            total_pages = int(page_match.group(2)) if page_match else 1

            all_text = []
            if match:
                text = match.group(1)
                text = re.sub(r"<[^>]*>", "", text)
                text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&ldquo;", "\u201c").replace("&rdquo;", "\u201d").replace("&mdash;", "\u2014").replace("&hellip;", "\u2026")
                all_text.append(text.strip())

            for pn in range(2, total_pages + 1):
                page_url = re.sub(r".html$", f"_{pn}.html", ch["url"])
                async with session.get(page_url, timeout=15) as resp:
                    p_html = await resp.text()
                p_match = re.search(r'<div[^>]*id="BookText"[^>]*>(.*?)</div>', p_html, re.DOTALL)
                if p_match:
                    p_text = p_match.group(1)
                    p_text = re.sub(r"<[^>]*>", "", p_text)
                    p_text = p_text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
                    all_text.append(p_text.strip())

            num = 0
            m = re.search(r"第s*(d+)s*章", ch["title"])
            if m: num = int(m.group(1))
            return {"title": ch["title"], "content": "\n".join(all_text), "num": num}
        except Exception as e:
            print(f"  Error: {ch['title']}: {e}")
            return {"title": ch["title"], "content": "", "num": 0}

# === DedeCMS pattern (fxshu.top) ===

async def download_dedecms(session, book_url, book_id):
    """DedeCMS: merge all pages then split by chapter headers."""
    all_text = []
    page = 1
    while True:
        url = f"{book_url}{book_id}.html" if page == 1 else f"{book_url}{book_id}_{page}.html"
        try:
            async with session.get(url, timeout=15) as resp:
                html = await resp.text()
        except:
            print(f"  Page {page} failed, stopping")
            break

        # Extract <div class=""co-bay"">
        match = re.search(r'<div[^>]*class="co-bay"[^>]*>(.*?)</div>', html, re.DOTALL)
        if not match:
            print(f"  Page {page}: no co-bay div, stopping")
            break

        text = match.group(1)
        text = re.sub(r"<[^>]*>", "", text)
        text = unescape(text)
        text = text.replace("&nbsp;", " ").replace("r", "")
        # Strip nav text
        text = re.sub(r"上一章s*目录s*下一章", "", text)
        text = re.sub(r"s*", " ", text).strip()
        all_text.append(text)

        # Check if there are more pages
        pages_match = re.search(r"共s*(d+)s*页", html)
        if not pages_match:
            # Alternative: look for 下一页 link
            if '下一页' not in html and page > 1:
                break

        max_pages = int(pages_match.group(1)) if pages_match else page
        if page >= max_pages:
            break
        page += 1

    full_text = "\n".join(all_text)

    # Strip everything before first chapter header
    first_ch = re.search(r"第s*d+s*章", full_text)
    if first_ch:
        full_text = full_text[first_ch.start():]

    # Split into chapters
    parts = re.split(r"(第s*d+s*章[^\n]*)", full_text)
    chapters = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i+1].strip() if i+1 < len(parts) else ""
        chapters.append({"title": title, "content": content, "num": i//2 + 1})

    return chapters

async def download_all_30dushu(base_url, book_path):
    async with aiohttp.ClientSession(headers=headers) as session:
        print("Fetching chapter list...")
        chapters = await get_chapter_list_30dushu(session, base_url, book_path)
        print(f"Found {len(chapters)} chapters")

        if not chapters:
            print("No chapters found!")
            return []

        print(f"Downloading {len(chapters)} chapters (8 concurrent)...")
        tasks = [download_chapter_30dushu(session, ch) for ch in chapters]
        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            if result:
                results.append(result)
                status = f"{len(result['content']):>6} chars" if result["content"] else "EMPTY"
                print(f"  [{i+1}/{len(chapters)}] {result['title']}: {status}")

        results.sort(key=lambda x: x["num"])
        total = sum(len(r["content"]) for r in results)
        print(f"\nDownload complete: {len(results)} chapters, {total} total chars")
        return results


# === fushutxt.cc pattern ===
# === fushutxt.cc pattern (unicode-safe, from working dl_novel3.py) ===

# \u-escaped Chinese constants (safe across file encodings)
_FQMFYD = "\u5168\u6587\u514d\u8d39\u9605\u8bfb"  # 全文免费阅读
_XHLY = "\u7384\u5e7b\u7075\u5f02"  # 玄幻灵异
_PL = "\u8bc4\u8bba"  # 评论
_SYY = "\u4e0a\u4e00\u9875"  # 上一页
_FHML = "\u8fd4\u56de\u76ee\u5f55"  # 返回目录
_XYZ = "\u4e0b\u4e00\u7ae0"  # 下一章
_XYY = "\u4e0b\u4e00\u9875"  # 下一页

async def download_fushutxt(session, base_url, book_id, category):
    """Download from m.fushutxt.cc: sequential _N.html pages.
    Each page has inline content after the marker; pages are NOT chapter-aligned
    (same novel's chapters are spread across pages). Merge all pages first,
    then split by chapter heading regex."""
    content_pages = []
    page = 0
    while True:
        url = f"{base_url}/{category}/{book_id}_{page}.html"
        try:
            async with session.get(url, timeout=15) as resp:
                html = await resp.text()
                if resp.status != 200:
                    bt, sigs = diagnose_block(html, resp.status)
                    if bt:
                        print_diagnostic(bt, sigs, f"Page {page}")
                    break
        except Exception as e:
            print(f"  Page {page}: {e}")
            break

        # Strip style/script, then all HTML tags
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = text.replace("\r", "")

        # Find content after the marker
        idx = text.find(_FQMFYD)
        if idx > 0:
            text = text[idx:]
        else:
            print(f"  Page {page}: no content marker, stopping")
            break

        # Strip navigation and category blocks
        text = re.sub(r".*?" + _XHLY + r".*?" + _PL, "", text, count=1, flags=re.DOTALL)
        text = re.sub(_SYY + r"\s*" + _FHML + r"\s*" + _XYZ + r"?" + _XYY + r"?\s*", "", text)
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        text = text.strip()
        content_pages.append(text)
        print(f"  Page {page}: {len(text)} chars")
        page += 1

    if not content_pages:
        print("  No content pages found!")
        return []

    full_text = "\n\n".join(content_pages)
    full_text = full_text.replace("\ufeff", "")
    print(f"  Merged: {len(full_text)} total chars")

    # Skip preamble before first chapter heading
    first_ch = re.search(r"第\s*\d+\s*章", full_text)
    if first_ch:
        full_text = full_text[first_ch.start():]

    parts = re.split(r"\n+(第\s*\d+\s*章\s*[^\n]*)", full_text)
    chapters = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i+1].strip() if i+1 < len(parts) else ""
        if title and re.match(r"第\s*\d+\s*章", title):
            chapters.append({"title": title, "content": content, "num": i//2 + 1})

    print(f"  Extracted {len(chapters)} chapters")
    return chapters

# === 222shuqu.com pattern ===

async def download_222shuqu(session, book_url, book_id):
    """Download from 222shuqu.com: fetch TOC at /index/{id}/,
    then download each /index/{id}/{ch}.html page."""
    toc_url = f"{book_url}/index/{book_id}/"
    try:
        async with session.get(toc_url, timeout=15) as resp:
            toc_html = await resp.text()
    except Exception as e:
        print(f"  TOC fetch failed: {e}")
        return []

    ch_pattern = re.escape(f"/index/{book_id}/") + r"(\d+)\.html"
    ch_ids = sorted(set(int(x) for x in re.findall(ch_pattern, toc_html)))
    if not ch_ids:
        print("  No chapters found in TOC!")
        return []

    print(f"  Found {len(ch_ids)} chapters")

    chapters = []
    for i, cid in enumerate(ch_ids):
        try:
            async with session.get(f"{book_url}/index/{book_id}/{cid}.html", timeout=15) as resp:
                html = await resp.text()

            title_m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
            title = title_m.group(1).strip() if title_m else f"第{i+1}章"
            title = re.sub(r"\s*[-|_].*", "", title)

            body_m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
            if body_m:
                text = body_m.group(1)
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", "\n", text)
                text = unescape(text)
                text = re.sub(r"&nbsp;", " ", text)
                text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
                text = text.strip()
            else:
                text = ""

            chapters.append({"title": title, "content": text, "num": i + 1})
            status = f"{len(text):>6} chars" if text else "EMPTY"
            print(f"  [{i+1}/{len(ch_ids)}] {title}: {status}")
        except Exception as e:
            print(f"  [{i+1}/{len(ch_ids)}] Error: {e}")
            chapters.append({"title": f"第{i+1}章", "content": "", "num": i + 1})

    total = sum(len(c["content"]) for c in chapters)
    print(f"  Download complete: {len(chapters)} chapters, {total} total chars")
    return chapters

# === zhiyixs.cc pattern ===

async def download_zhiyixs(session, book_url, book_id):
    """Download from zhiyixs.cc: paginated chapters grouped by chapter number.
    
    NOTE: zhiyixs now requires Referer header for chapter pages.
    TOC links use .html suffix (not trailing /).
    """
    referer = f"{book_url}/book/{book_id}/"
    
    async with session.get(f"{book_url}/book/{book_id}/", timeout=15) as resp:
        toc_html = await resp.text()

    # Extract all page links (zhiyixs uses .html suffix in TOC; match both)
    page_ids = re.findall(r"/read/" + re.escape(book_id) + r"/(\d+)", toc_html)
    page_ids = list(dict.fromkeys(page_ids))  # deduplicate preserving order
    
    if not page_ids:
        print("  WARNING: no page links found on TOC page")
        return []

    pages = []
    summary = {"ok": 0, "no_content": 0, "error": 0}
    for pid in page_ids:
        try:
            async with session.get(f"{book_url}/read/{book_id}/{pid}.html",
                                   timeout=15, headers={"Referer": referer}) as resp:
                html = await resp.text()

            content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*?)</div>', html, re.DOTALL)
            if not content_match:
                summary["no_content"] += 1
                continue

            text = content_match.group(1)
            text = re.sub(r"<[^>]*>", "", text)
            text = unescape(text)
            text = text.replace("&nbsp;", " ").strip()

            # Extract chapter title: 第X章 第Y页
            title_match = re.search(r"第\s*(\d+)\s*章\s*第\s*(\d+)\s*页", html)
            if title_match:
                chap_num = int(title_match.group(1))
                page_num = int(title_match.group(2))
            else:
                # Fallback: try 第X章 or simple title
                title_match = re.search(r"第\s*(\d+)\s*章", html)
                chap_num = int(title_match.group(1)) if title_match else 0
                page_num = 1

            pages.append({
                "text": text,
                "chapter_num": chap_num,
                "page_num": page_num,
                "title": f"第{chap_num}章 第{page_num}页" if title_match else f"Page {pid}"
            })
            summary["ok"] += 1
            print(f"  Page {pid}: ch{chap_num} p{page_num} ({len(text)} chars)")
        except Exception as e:
            summary["error"] += 1
            print(f"  Error page {pid}: {e}")

    print(f"  Summary: {summary['ok']} ok, {summary['no_content']} no-content, {summary['error']} errors")

    # Group by chapter number
    from collections import defaultdict
    groups = defaultdict(list)
    for p in pages:
        groups[p["chapter_num"]].append(p)

    chapters = []
    for ch_num in sorted(groups.keys()):
        group_pages = sorted(groups[ch_num], key=lambda x: x["page_num"])
        content = "\n".join(p["text"] for p in group_pages)
        title = f"第{ch_num}章" if ch_num > 0 else "未知"
        chapters.append({"title": title, "content": content, "num": ch_num if ch_num > 0 else len(chapters) + 1})

    return chapters

def detect_site_type(url):
    """Detect site type from URL."""
    if any(k in url for k in ["30dushu.com", "28dushu.com"]):
        return "30dushu"
    if any(k in url for k in ["fxshu.top"]):
        return "dedecms"
    if any(k in url for k in ["fushutxt.cc"]):
        return "fushutxt"
    if any(k in url for k in ["zhiyixs.cc"]):
        return "zhiyixs"
    if any(k in url for k in ["222shuqu.com", "222shuqu"]):
        return "222shuqu"
    if any(k in url for k in ["blxsw.cc", "blxsw"]):
        return "blxsw"
    return "unknown"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download novel chapters")
    parser.add_argument("url", help="Book URL")
    parser.add_argument("output", nargs="?", help="Output JSON file")
    parser.add_argument("--merge", action="store_true", help="Use DedeCMS merge mode")
    args = parser.parse_args()

    url = args.url.rstrip("/")
    site_type = "dedecms" if args.merge else detect_site_type(url)

    if site_type == "dedecms":
        # Extract book ID
        m = re.search(r"/book/(d+)", url)
        book_url = re.sub(r"/book/d+.*$", "/book/", url) if m else url.rsplit("/", 1)[0] + "/"
        book_id = m.group(1) if m else ""
        if not book_id:
            print(f"Cannot extract book ID from {url}")
            sys.exit(1)
        results = asyncio.run(download_dedecms(
            aiohttp.ClientSession(headers=headers), book_url, book_id
        ))
    elif site_type == "30dushu":
        m = re.search(r"30dushu\.com(/book/d+/?)$", url)
        if not m:
            m = re.search(r"30dushu\.com(/[^/]+/d+/?)$", url)
        if not m:
            print(f"Unrecognized URL pattern: {url}")
            sys.exit(1)
        book_path = m.group(1).rstrip("/") + "/" if not m.group(1).endswith("/") else m.group(1)
        base_url = "https://30dushu.com"
        results = asyncio.run(download_all_30dushu(base_url, book_path))
    elif site_type == "fushutxt":
        # URL: https://m.fushutxt.cc/{category}/{book_id}.html or _{N}.html
        m = re.search(r"fushutxt\.cc/(\w+?)/(\d+?)(?:_\d+)?\.html", url)
        if not m:
            print(f"Unrecognized fushutxt URL pattern: {url}")
            sys.exit(1)
        cat, bid = m.group(1), m.group(2)
        base_url = re.match(r"https?://[^/]+", url).group(0)
        async def _run_fushutxt():
            async with aiohttp.ClientSession(headers=headers) as session:
                return await download_fushutxt(session, base_url, bid, cat)
        results = asyncio.run(_run_fushutxt())
    elif site_type == "zhiyixs":
        # URL: https://www.zhiyixs.cc/book/{id}/
        m = re.search(r"zhiyixs\.cc/book/(\d+)", url)
        if not m:
            print(f"Unrecognized zhiyixs URL pattern: {url}")
            sys.exit(1)
        bid = m.group(1)
        base_url = re.match(r"https?://[^/]+", url).group(0)
        async def _run_zhiyixs():
            async with aiohttp.ClientSession(headers=headers) as session:
                return await download_zhiyixs(session, base_url, bid)
        results = asyncio.run(_run_zhiyixs())
    elif site_type == "222shuqu":
        # URL: https://www.222shuqu.com/index/{id}/
        m = re.search(r"222shuqu\.com/index/(\d+)", url)
        if not m:
            print(f"Unrecognized 222shuqu URL pattern: {url}")
            sys.exit(1)
        bid = m.group(1)
        base_url = re.match(r"https?://[^/]+", url).group(0)
        async def _run_222shuqu():
            async with aiohttp.ClientSession(headers=headers) as session:
                return await download_222shuqu(session, base_url, bid)
        results = asyncio.run(_run_222shuqu())
    elif site_type == "blxsw":
        # URL: https://www.blxsw.cc/book/{id}/
        m = re.search(r"blxsw\.cc/book/(\d+)", url)
        if not m:
            print(f"Unrecognized blxsw URL pattern: {url}")
            sys.exit(1)
        bid = m.group(1)
        base_url = re.match(r"https?://[^/]+", url).group(0)
        # blxsw uses same per-chapter TOC <a> tag pattern as 30dushu.
        # Note: content container is <div id="content"> (vs 30dushu's <div id="BookText">),
        # so chapter content extraction may need a dedicated downloader for full accuracy.
        results = asyncio.run(download_all_30dushu(base_url, f"/book/{bid}/"))
    else:
        print(f"Unknown site type for URL: {url}")
        print("Use --merge for DedeCMS sites")
        sys.exit(1)

    if results and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False)
        print(f"Saved to {args.output}")

