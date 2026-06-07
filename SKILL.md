---
name: novel-search-export
description: >-
  Search Chinese web novels (especially danmei/BL) across multiple mirror sites,
  download full-text chapters with automatic anti-scrape detection and skill routing,
  and export as styled .docx with clickable TOC. Use when the user asks to
  find a Chinese web novel, download novel chapters, convert a novel to Word,
  export a novel as .docx, search for danmei/BL fiction online, or handle
  anti-scrape blocks on Chinese novel sites. Covers 30dushu, fxshu, fushutxt,
  zhiyixs, 222shuqu, blxsw, paowenwu, and piaotianwxz.
---

# Chinese Novel Search & Word Export

Search Chinese web novels and export as styled .docx with clickable TOC.

**Core flow:** Search ? Verify site ? Download ? Merge & Split ? Generate docx ? Verify

## Work Directory

Default: `D:/??/`. Subdirs: `??/` (final .docx), `_temp/` (temp/scripts/cache).

## Quick Search (Low-Token)

When token budget is tight, run `scripts/search_novel.py`:

```bash
python scripts/search_novel.py "novel_title" "author" [--sogou] [--json]
```

Classifies results as: recommended > available > blocked > unknown.
If Sogou triggers anti-spider, use `$search` skill (Browserbase Search API).

## Search Strategy

| Engine | Best for | Notes |
|--------|----------|-------|
| **Bing** | General, fast | Exact phrase match |
| **Sogou** | Chinese coverage | May trigger anti-spider ? use `$search` or `$browser` |

**Site ranking (prefer top):**
1. 30dushu.com ? clean per-chapter, UTF-8
2. 222shuqu.com ? danmei coverage, per-chapter HTML
3. m.fushutxt.cc ? sequential pages, inline after marker
4. fxshu.top ? DedeCMS merge, general novels
5. zhiyixs.cc ? paginated chapters, group by chapter (needs `.html` + Referer)
6. blxsw.cc ? danmei-exclusive, similar to 30dushu
7. paowenwu3.com ? TXT download, needs Referer
8. JS-rendered (fanqie etc.) ? last resort, use playwright/browserbase
9. m.piaotianwxz.com ? /ptwx/{id}/, paginated TOC, 50 ch/pg
10. Skip: tongquet.com (U+E000+ obfuscation), jjwxc.net (WAF + login)

## Download: `scripts/download_novel.py`

```bash
python scripts/download_novel.py <book_url> [output.json] [--merge]
```

Auto-detects site type from URL. Supported: `30dushu`, `dedecms` (fxshu), `fushutxt`, `zhiyixs`, `222shuqu`, `blxsw`.

### Site-Specific Patterns

Detailed per-site strategies (content containers, selectors, URL patterns) live in `references/sites.md`. Load it when debugging a specific site.

**30dushu.com:** `/book/{id}/` ? parse `<a>` with "?N?" ? download `/read/{bid}/{cid}.html` with multi-page support (`_2.html`). Container: `<div id="BookText">`.

**DedeCMS (fxshu.top):** `/book/{id}.html` + `_{N}.html` pages. Merge all `<div class="co-bay">` content, split by `?\s*\d+\s*?` regex.

**fushutxt:** Sequential `_{N}.html` pages. Content after marker `??????`. Strip nav breadcrumbs, split merged text by chapter headings.

**zhiyixs:** `/read/{id}/{pid}.html` pages (**.html required**). **Requires Referer header** for chapter fetch. `<title>?X? ?Y?</title>`. Group pages by chapter number, concatenate.

**222shuqu:** `/index/{id}/` TOC ? `/index/{id}/{ch}.html` chapters. Title from `<title>`, strip site suffix. Body inner text from `<body>`.

**blxsw:** Delegates to 30dushu downloader pattern. Content container differs (`id="content"` vs `id="BookText"`).

**piaotianwxz:** Book page: /ptwx/{id}/. TOC paginated: /ptwx/{id}/index_1.html (50 chapters/pg), index_2.html, index_3.html etc. Chapter URL: /ptwx/{book_id}/{ch_id}.html.
Content container: <div id="nr_body" class="Readarea ReadAjax_content">. Use broad regex class="Readarea[^"]*" --
the div has an id="nr_body" attr before the class, and exact class-string matching will fail.

**?? piaotianwxz search caveat:** The site search (/so/?t=...) uses its own index and may return only
default recommendations even when the novel exists on the site. If a user provides a direct piaotianwxz URL,
always try it regardless of search results. See exhaustion checklist step 7.

### Anti-Scrape Detection & Automatic Skill Routing

`download_novel.py` includes `diagnose_block()` which matches response HTML against 30+ regex patterns across 6 categories. On detection, it prints a structured diagnostic with the recommended skill.

| Block Type | Signal Example | Skill to Use | Severity |
|-----------|---------------|-------------|----------|
| **cloudflare** | cf-browser-verification, _cf_chl_opt | `$browserbase-cli` + residential proxy | Hard |
| **captcha** | ???, g-recaptcha | `$browser` (Playwright headful) | Hard |
| **rate_limit** | ?????, HTTP 429 | `$browser` + delay/retry | Soft |
| **login_required** | ????, ??? | `$browser` + `$cookie-sync` | Hard |
| **js_rendered** | <noscript>, empty body | `$playwright` (render JS) | Soft |
| **waf_block** | HTTP 403/503, ???? | `$browserbase-cli` residential | Hard |

**Workflow on block:**
1. `download_novel.py` detects block ? prints `ANTI-SCRAPE DETECTED [HARD] Type: cloudflare`
2. Agent reads diagnostic ? invokes suggested skill
3. Retry download using skill tools (Playwright page, Browserbase session)

## Docx Generation: `scripts/create_docx.py`

```bash
python scripts/create_docx.py <chapters.json> <output.docx>
```

Generates styled .docx with: cover page, clickable TOC (grouped by main/extra), chapter content with page breaks. Formatting details in `references/docx_format.md`.

## Verification: `scripts/verify_docx.py`

Run after generation. Checks: cover non-empty, TOC ? 5 hyperlinks, chapter headers match pattern, total text ? 10k chars.

## Content Clean-up

- HTML entities: `&ldquo;` ? `"`, `&mdash;` ? `?`, `&hellip;` ? `?`, `&nbsp;` ? space
- Remove `\r`, collapse 3+ newlines to 2
- Strip nav text and author-note blocks
- Verify: ?(U+964D) vs ?(U+9648), ?(U+7CFB) vs ?(U+7EDF)

## JJWXC API Fallback

When a novel is jjwxc-exclusive (no mirrors found), the jjwxc Android API can still
provide metadata and free-chapter content without a login:

- **Book info:** GET https://app.jjwxc.net/androidapi/novelbasicinfo?novelId={id}
  Returns title, author, intro, chapter count, first-vip-chapter-id (ipChapterid), tags.
- **Chapter list (public):** GET https://app.jjwxc.net/androidapi/chapterList?novelId={id}
  Returns first ~5 and last ~5 free chapters; not exhaustive but gives chapter numbering.
- **Chapter content:** GET https://app.jjwxc.net/androidapi/chapterContent?novelId={id}&chapterId={ch}
  Works for chapters before ipChapterid (usually 1-22). VIP chapters return code: 1004.
  Save partial download even if complete novel is unavailable.

## Failure Modes

**Site-specific gotchas (check first when a site fails):**
- **zhiyixs.cc:** Chapter pages return TOC without `Referer` header. TOC links use `.html` suffix.
  If download returns 0 pages: check Referer and `.html` in URL.
- **fxshu.top:** May need Referer if blocked.

**JJWXC-exclusive novel:** Only jjwxc.net links appear across Bing + Sogou. Zero hits on mirrors. Novel is new (<6 months) or small readership.

**Title mismatch:** Mirror sites rename danmei titles. When original title returns nothing, search by **author name only**.

**Exhaustion checklist (before declaring "not found"):**
1. Bing: `"title" "author"` exact phrase
2. Sogou: same query
3. Direct site search: `site:30dushu.com "title"`, `site:222shuqu.com "title"`
4. Author-only search if title returns nothing
5. Category browsing on blxsw.cc for danmei
6. After 3+ passes across Bing + Sogou + 5+ direct searches with 0 mirror URLs ? report JJWXC-exclusive
7. **User-suggested alternative sites:** If the user names a mirror site not in the default list
   (e.g. piaotianwxz), try it -- especially if they provide a direct URL. Some sites have
   search indexes that lag behind actual content; direct URL patterns may succeed where search fails.
8. Use jjwxc API fallback to extract at least free chapters and metadata.

## Danmei-Specific Tips

Danmei/BL novels from jjwxc often have renamed titles on mirrors. Author name is more reliable.
Keyword mutation: ?? ? ??, ?? ? ?T.

**blxsw.cc search workaround** (POST search returns "????"):
1. Bing: `site:blxsw.cc "title"`
2. Browse categories: `/BLtongren/`, `/xiandaidushi/`, etc.
3. Book URL: `/{cat}/{id}.html` ? `/book/{id}/`

## Output Archive

```
D:/??/
  ??? ??/
  ?     ??? ??.docx    (final)
  ??? _temp/
        ??? *.json       (chapter cache)
        ??? *.txt        (raw text)
```

Cleanup temp files after verification passes via `scripts/cleanup.py`.

## Resources

### scripts/
- **search_novel.py**: Multi-engine search, returns classified site list
- **download_novel.py**: Async downloader with anti-scrape detection + 7 site types
- **create_docx.py**: Styled .docx with clickable TOC and content-type formatting
- **verify_docx.py**: Post-generation QA check
- **cleanup.py**: Archive and organize output files
- **search_step.py**: Single-search-step helper
- **check_chapters.py**: Chapter count/quality check
- **decode_js_obfuscation.py**: Deobfuscate JS-encrypted novel content

### references/
- **sites.md**: Per-site scraping strategies (containers, encoding, URL patterns)
- **docx_format.md**: Word export formatting reference (fonts, styles, layout)
- **js-reverse-engineering.md**: JS deobfuscation for fanqie/tongquet protected content
