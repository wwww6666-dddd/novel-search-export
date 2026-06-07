# Novel Site Scraping Strategies

## 30dushu.com / 28dushu.com - RECOMMENDED (Primary)

| Item | Detail |
|------|--------|
| Content container | <div id="BookText"> |
| Chapter list | TOC page: /book/{id}/ - parse <a> tags with "?N?" |
| Chapter URL | /read/{book_id}/{ch_id}.html |
| Multi-page | Suffix _2.html, _3.html detected by "N/M" pattern on page |
| Encoding | UTF-8 |
| Anti-scrape | None significant, direct GET works |
| Speed | ~1s per chapter, use async with semaphore(8) |
| Chapter titles | "?N?" only, no subtitles |

## m.fushutxt.cc - RECOMMENDED (Secondary)

| Item | Detail |
|------|--------|
| Content container | No dedicated div ? content is inline after "??????" marker |
| TOC page | /{category}/{book_id}.html ? shows page count "?N?" |
| Chapter URL | /{category}/{book_id}_{N}.html for sequential pages 0..N |
| Multi-page | Sequential _0.html, _1.html, ... _N.html |
| Chapter detection | Split content by ?\s*\d+\s*? regex after extracting text |
| Text extraction | Remove header/nav HTML before "??????", then split |
| Encoding | UTF-8 |
| Anti-scrape | Minimal; standard GET works |
| Speed | ~1s per page; batch download all pages sequentially |
| Notes | Good for danmei/BL novels; chapter detection may need regex tuning |

## zhiyixs.cc - zhiyixs.cc Pattern

| Item | Detail |
|------|--------|
| Content container | `<div id="content">` |
| TOC page | `/book/{book_id}/` -- lists all page IDs as links |
| Chapter URL | `/read/{book_id}/{page_id}.html` -- **uses .html suffix** (not trailing /) |
| Pagination | Each chapter split into "?X? ?Y?" titled pages |
| Chapter grouping | Group pages by chapter number X, concatenate to form full chapter |
| Encoding | UTF-8 |
| Anti-scrape | **Requires Referer header** (`Referer: {book_url}`) for chapter pages; without it, pages redirect to TOC |
| Speed | ~1s per page, async with semaphore(16) |
| Notes | TOC links use `.html`; chapter fetch must include Referer. Regex: `<title>?(\d+)?\s*?(\d+)?`. Fallback: `<title>?(\d+)?` |

## fxshu.top (???) - DedeCMS Pattern

| Item | Detail |
|------|--------|
| Content container | <div class="co-bay"> |
| Page pattern | /book/{id}.html + _{N}.html for pages |
| Navigation | <div class="dede_pages"> shows "?N?" |
| Chapter detection | Pages are NOT chapter-aligned; merge all first |
| Split method | Merge all pages -> split by ?\s*\d+\s*? regex |
| Encoding | UTF-8 (check per site) |
| Anti-scrape | Minimal; if blocked try adding Referer |

## fanqienovel.com - JS-Rendered / Font Obfuscated

| Item | Detail |
|------|--------|
| Content container | JS-rendered, custom @font-face with woff2 glyph scrambling |
| Access method | Requires Playwright or browser rendering for readable text |
| Font deobfuscation | Custom woff2 fonts scramble glyph mapping; need JS reverse engineering |
| Title variation | Mirror sites often use different titles than jjwxc originals |
| Verdict | LAST RESORT ? use only if no other site has the novel |
| Tools | Playwright for rendering; js-reverse-engineer skill for font deobfuscation |

## paowenwu3.com - TXT Download

| Item | Detail |
|------|--------|
| Content container | <div id="content"> (per-chapter) |
| TXT download | /modules/article/packdown.php?id={id}&type=txt |
| Requirements | Need session cookie + Referer: https://www.paowenwu3.com/book/{id} |
| Encoding | Chapter titles: "?N?" only |
| Speed | Can be slow, set timeout=15s |
| Fallback | Use only when 30dushu/fxshu fail |

## aiyisw.com

| Item | Detail |
|------|--------|
| Search | /search?keyword={novel_title} |
| Content container | <div id="content"> |
| Chapter URL | /book/{id}/{ch_id}.html |
| Encoding | UTF-8 |
| Notes | Good chapter counts, check accessibility first |

## tongquet.com / ??? - AVOID

| Item | Detail |
|------|--------|
| Content container | <div class="reader-content"> |
| Obfuscation | Unicode private area (U+E000-U+FFFF) mixed in text |
| Verdict | **DO NOT USE** - text reconstruction is unreliable |

## jjwxc.net / ????? - INFO ONLY

| Item | Detail |
|------|--------|
| Access | Mobile: m.jjwxc.net (no WAF), Desktop: GBK encoding |
| Content | Login required; free chapters readable, paid chapters require purchase |
| Use case | Find novel ID and author info only |
| Verdict | Not suitable for bulk download; many novels are jjwxc-exclusive with no free mirrors |

## boshishuwu.net / niwuds.com / biquge series

| Item | Detail |
|------|--------|
| Notes | Content exists but may need Referer or JS rendering |
| Use case | Backup when primary sites fail |



## 222shuqu.com

| Item | Detail |
|------|--------|
| Content container | Chapter body text (<body> inner) after stripping scripts/styles |
| TOC page | /index/{book_id}/ |
| Chapter URL | /index/{book_id}/{ch_id}.html |
| Title extraction | <title> tag, strip site suffix after `-`, `|`, or `_` |
| Text extraction | Re.findall all /index/{id}/{n}.html links, sort by n |
| Search | /search/?keyword=xxx |
| Encoding | UTF-8 |
| Anti-scrape | Minimal |
| Notes | Good danmei coverage; chapter titles in <title> tags; body text after stripping HTML |

## blxsw.cc (耽美小说网) - Danmei Exclusive

| Item | Detail |
|------|--------|
| Content container | <div id="content"> |
| TOC page | /book/{id}/ (redirects from /{cat}/{id}.html) |
| Search | POST /e/search/index.php (often returns "暂时关闭") |
| Categories | BLtongren, xiandaidushi, gudaijiakong, chuanyuechongsheng, xuanhuanlingyi, wangyoujingji, tuilixuanyi |
| Category pagination | /{cat}/index_{N}.html |
| Homepage books | /{cat}/{id}.html (style format, redirects to /book/{id}/) |
| Encoding | UTF-8 |
| Anti-scrape | Search function often disabled; direct access and category browsing work |
| Notes | Dedicated danmei/BL site. When search is down, browse categories or use site:blxsw.cc on Bing |
| Verdict | Good source when search is functional; otherwise requires category scanning |

## General Strategy Update

9. **222shuqu.com** - good danmei mirror, quick to check
10. **blxsw.cc** - danmei-exclusive, try category browsing when search down
11. **m.fushutxt.cc** - inline content with sequential pages, good for danmei

**Danmei/BL novels special notes:**
- Mirror sites often rename titles (e.g. "皇文" -> "嬷嬷" or "黄文")
- Author name is more reliable for cross-referencing
- jjwxc novel IDs help find original info even if mirror title differs
## m.piaotianwxz.com (???) - Paginated TOC, Sequential Chapter IDs

| Item | Detail |
|------|--------|
| Content container | <div id="nr_body" class="Readarea ReadAjax_content"> |
| TOC page | /ptwx/{id}/index.html ? redirects to index_1.html (50 chapters/pg) |
| TOC pagination | /ptwx/{id}/index_2.html, index_3.html, ? |
| Chapter URL | /ptwx/{book_id}/{ch_id}.html (sequential numeric IDs) |
| Search | /so/?t={query}&369koolearn=1 ? often returns default recs, NOT actual matches |
| Content regex | Use broad class="Readarea[^\""]*"[^>]*>(.*?)</div> ? div has id="nr_body" attr before class |
| Encoding | UTF-8 |
| Anti-scrape | Minimal; standard GET works for direct chapter access |
| Speed | ~0.3s per chapter with polite delay |
| Notes | Paginated TOC needs index_N.html iteration. Chapter IDs grow monotonically. |
| Caveat | **Site search often fails to index all content.** When user provides a direct URL, try it even if search returns nothing. |

## General Strategy

1. **Always try 30dushu first** - cleanest, fastest, most reliable
2. **m.fushutxt.cc as secondary** - good for danmei/BL novels, inline content extraction
3. **zhiyixs.cc as tertiary** - paginated chapter grouping, reliable but more work
4. **fxshu.top as backup** - DedeCMS merge works well for most novels
5. **paowenwu3.com** - when TXT download is preferred
6. **piaotianwxz.com** - paginated TOC with direct chapter links, try when user provides a URL
7. **Skip JS-rendered sites** unless the novel is ONLY available there
8. **Skip tongquet.com** - obfuscation is not worth the effort
9. **fanqienovel.com** - last resort, requires Playwright + font deobfuscation

## Encoding Notes

- Most modern sites: UTF-8
- Some older biquge/boshishuwu sites: GBK/GB2312
- jjwxc.net desktop: GBK
- Always try UTF-8 first, fall back to GBK
- Detect with: .apparent_encoding or try both

## Title Variation Note

Novel titles on mirror sites often differ from jjwxc originals:
- Same novel may appear under slightly different titles
- Author name is more reliable for cross-referencing
- Search with multiple title variations when original search fails
