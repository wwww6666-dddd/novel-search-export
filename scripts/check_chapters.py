import requests, re
headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"}
r = requests.get("https://30dushu.com/book/79537/", headers=headers, timeout=15)
text = r.text

# Count all chapter-like entries
chapters = []
for m in re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', text):
    href = m.group(1)
    title = m.group(2).strip()
    if title and ("绗? in title or "鐣" in title or "灏惧０" in title or "鍚庤" in title or "缁堢珷" in title):
        chapters.append((title, href))

print(f"Total matching entries: {len(chapters)}")
for t, h in chapters:
    print(f"  [{t}] -> {h}")
