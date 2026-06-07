import requests, re

headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"}
r = requests.get(
    "https://www.bing.com/search?q=%22%E6%81%B6%E6%AF%92%E7%99%BD%E6%9C%88%E5%85%89%E7%94%9F%E5%AD%98%E6%8C%87%E5%8D%97%22+%22%E5%87%9B%E6%98%A5%E9%A3%8E%22&cc=cn&setlang=zh-Hans",
    headers=headers, timeout=15
)
text = r.text

# Find all URLs
urls = re.findall(r'https?://[^"\' <>]+', text)

# Filter for novel sites
novel_urls = [u for u in urls if any(k in u for k in [
    "30dushu", "28dushu", "paowenwu", "tongquet",
    "boshishuwu", "niwuds", "biquge", "jjwxc"
])]

unique = sorted(set(novel_urls))
print(f"Found {len(unique)} novel site links:")
for u in unique:
    print(f"  {u}")
