"""
Search for a Chinese novel across multiple search engines.
Returns list of found URLs with site information.
Optimized for low-token, fast search.

Usage:
    python search_novel.py <novel_title> [author_name]
    python search_novel.py ""龙傲天绑定嬷嬷系统"" ""执狐""
"""

import requests, re, sys, json, time
from urllib.parse import quote

NOVEL_SITE_KEYWORDS = [
    "30dushu", "28dushu", "fxshu.top", "paowenwu", "tongquet",
    "boshishuwu", "niwuds", "biquge", "jjwxc", "qidian", "fanqie",
    "aiyisw", "bxwx", "shuqu", "fushutxt", "zhiyixs",
    "222shuqu", "blxsw",
    "qianjiawen", "spudnovel", "kunlun", "webnovel", "iqiyi",
    "sttku", "2ge", "wanben", "xiaozhuge", "shu69",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def search_bing(novel_title, author="", timeout=10):
    """Bing search with exact title matching. Fastest engine."""
    links = []
    q = f'"{novel_title}"' + (f' "{author}"' if author else "")
    try:
        r = requests.get(
            f"https://www.bing.com/search?q={quote(q)}&cc=cn&setlang=zh-Hans",
            headers=headers, timeout=timeout
        )
        urls = re.findall(r'https?://[^"\' <>]+', r.text)
        novel_urls = [u for u in urls if any(k in u for k in NOVEL_SITE_KEYWORDS)]
        links.extend(novel_urls)
        print(f"[Bing] Found {len(novel_urls)} novel site links")
    except Exception as e:
        print(f"[Bing] Error: {e}")
    return links

def search_sogou(query, timeout=10):
    """Sogou search. Good for Chinese content but may trigger anti-spider."""
    links = []
    try:
        r = requests.get(
            f"https://www.sogou.com/web?query={quote(query)}",
            headers={**headers, "Accept": "text/html,*/*"}, timeout=timeout
        )
        if "antispider" in r.text or "verify" in r.text:
            print("[Sogou] Anti-spider triggered, skipping")
            print("[Sogou] SUGGEST: use $search skill (Browserbase Search API) or $browser skill for manual search")
        else:
            urls = re.findall(r'https?://[^"\' <>]+', r.text)
            novel_urls = [u for u in urls if any(k in u for k in NOVEL_SITE_KEYWORDS)]
            links.extend(novel_urls)
            print(f"[Sogou] Found {len(novel_urls)} links")
    except Exception as e:
        print(f"[Sogou] Error: {e}")
    return links

def search_novel(novel_title, author="", timeout=10, engines=None):
    """Search for a novel across multiple engines."""
    if engines is None:
        engines = ["bing"]

    all_links = []
    query = f"{novel_title} {author}".strip()

    if "bing" in engines:
        all_links.extend(search_bing(novel_title, author, timeout))
    if "sogou" in engines:
        all_links.extend(search_sogou(query, timeout))

    return list(set(all_links))

def classify_links(links):
    """Classify found links by site and accessibility."""
    classified = {"recommended": [], "available": [], "blocked": [], "unknown": []}
    for url in links:
        if "30dushu.com" in url or "28dushu.com" in url:
            classified["recommended"].append(url)
        elif "fxshu.top" in url:
            classified["recommended"].append(url)
        elif "fushutxt.cc" in url or "fushutxt" in url:
            classified["recommended"].append(url)
        elif "222shuqu" in url:
            classified["recommended"].append(url)
        elif "zhiyixs.cc" in url or "zhiyixs" in url:
            classified["available"].append(url)
        elif "blxsw" in url:
            classified["available"].append(url)
        elif "paowenwu" in url:
            classified["available"].append(url)
        elif "aiyisw" in url:
            classified["available"].append(url)
        elif "jjwxc.net" in url or "jjwxc" in url:
            classified["blocked"].append(url)
        elif "tongquet" in url:
            classified["blocked"].append(url + " (text obfuscation)")
        else:
            classified["unknown"].append(url)
    return classified

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_novel.py <novel_title> [author] [--sogou]")
        sys.exit(1)

    title = sys.argv[1]
    author = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else ""
    engines = ["bing"]
    if "--sogou" in sys.argv:
        engines.append("sogou")

    print(f"Searching for: {title} {author}\n")
    links = search_novel(title, author, engines=engines)

    if links:
        classified = classify_links(links)
        print("\n=== Results ===")
        for category, urls in classified.items():
            if urls:
                print(f"\n[{category.upper()}]:")
                for u in urls[:5]:
                    print(f"  {u}")
        print(f"\nTotal: {len(links)} links found")

        # Output JSON for piping
        if "--json" in sys.argv:
            print("\n--- JSON ---")
            print(json.dumps({"links": links, "classified": {k: v for k, v in classified.items() if v}}, ensure_ascii=False))
    else:
        print("\nNo links found. Try adding --sogou or different search terms.")
