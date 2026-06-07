# novel-search-export

A Codex skill for searching Chinese web novels (especially danmei/BL) across multiple mirror sites, downloading full-text chapters, and exporting as styled .docx with clickable table of contents.

## Features

- **Multi-engine search**: Bing and Sogou, with automatic anti-spider detection
- **Multi-site download**: Supports 30dushu, fxshu, fushutxt, zhiyixs, 222shuqu, blxsw, paowenwu, piaotianwxz
- **Anti-scrape intelligence**: Auto-detects Cloudflare, captcha, rate-limit, WAF blocks; suggests the right Browserbase/Playwright skill to bypass
- **JJWXC API fallback**: Extracts free chapters via Android API when a novel is jjwxc-exclusive
- **Styled .docx export**: Cover page, clickable TOC, chapter formatting
- **Post-generation verification**: Checks document integrity and content quality

## Structure

```
novel-search-export/
├── SKILL.md              # Main skill definition
├── requirements.txt      # Python dependencies
├── scripts/              # Core automation scripts
├── references/           # Reference documentation
│   ├── sites.md          # Per-site scraping strategies
│   ├── docx_format.md    # Word export formatting
│   └── js-reverse-engineering.md
├── agents/               # Agent configuration
└── assets/               # (empty)
```

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

This is a [Codex](https://codex.openai.com) skill. Install it and use natural language to search, download, and export Chinese web novels.
