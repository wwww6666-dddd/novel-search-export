# JavaScript Reverse Engineering for Novel Sites

## When to Use

Some Chinese novel sites use JavaScript to:
1. **Encrypt/obfuscate article content** - stores encrypted text, decrypts in browser
2. **Anti-scrape detection** - uses fingerprinting, WebDriver detection
3. **Dynamic rendering** - uses SPA frameworks (React/Vue) to load content
4. **CAPTCHA / verification** - slider, click, or code verification

## Detection

Before scraping, check if site requires JS:
\\\python
import requests
r = requests.get(url, headers=headers)

# Signs of JS-rendered content:
if len(r.text) < 2000 and ('window.' in r.text or 'document.' in r.text):
    print("Likely JS-rendered")
elif 'antispider' in r.text or 'verify' in r.text:
    print("Anti-scrape detection")
elif not re.search(r'<p[^>]*>.*[\u4e00-\u9fff]{10}', r.text):
    print("No visible Chinese text - might be encrypted")
\\\

## Strategy 1: obfuscator.io / javascript-obfuscator

Most common obfuscation tool for Chinese novel sites. Characterized by:
- Hex/unicode string arrays: \x48\x65\x6c\x6c\x6f  
- Base64-encoded strings
- String array rotation: ar _0xa1b2 = ["\u89e3\u5bc6", ...]
- Control flow flattening via switch statements

**Tool: synchrony** (npm package)
\\\ash
npm install -g deobfuscator
synchrony deobfuscate ./obfuscated.js
# Produces: obfuscated.cleaned.js
\\\

**Manual approach in Node REPL:**
\\\javascript
// If using the js-reverse-engineer skill:
// 1. Get the obfuscated JS file
// 2. Use obfuscator-io-deobfuscator or synchrony
// 3. Extract the decryption/content-loading function
// 4. Run it in Node to get clean text
\\\

## Strategy 2: WebCrack (Webpack/Module Bundles)

For sites using Webpack/Vite to bundle:
- Install: 
pm install -g webcrack
- Run: webcrack input.js -o output/
- Each module becomes a separate file

## Strategy 3: Playwright / Browserbase (Full Rendered Content)

When deobfuscation is too complex, just render the page:

\\\python
# playwright approach
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector("div#BookText, div.co-bay, div.content", timeout=10000)
    html = page.content()
\\\

\\\python  
# Browserbase approach (for sites with strong anti-bot)
# Use rowserbase-browser skill or:
# browse open url --stealth
\\\

## Strategy 4: Node.js REPL with obfuscator-io-deobfuscator

For programmatic deobfuscation within the workflow:
\\\javascript
// In node_repl MCP:
const { deobfuscate } = await import("obfuscator-io-deobfuscator");
const cleanCode = deobfuscate(obfuscatedSource);
// Then analyze the clean code to find:
// 1. Content loading API endpoints
// 2. Decryption functions
// 3. Anti-scrape token generation
\\\

## Common Novel Site Encryption Patterns

### Pattern: Reverse String + Base64
\\\python
import base64
# Site stores content as: reversed base64
encrypted = "..."
text = base64.b64decode(encrypted[::-1]).decode("utf-8")
\\\

### Pattern: XOR with Static Key
\\\python
key = b"somekey"
encrypted = bytes.fromhex("...")
text = bytes(a ^ key[i % len(key)] for i, a in enumerate(encrypted)).decode()
\\\

### Pattern: Unicode Private Area Scrambling (tongquet.com style)
Content looks like readable text but has U+E000-U+FFFF codepoints mixed in.
These sites are generally NOT worth the effort to clean.

## References

- synchrony: https://github.com/relative/synchrony (javascript-obfuscator deobfuscator)
- webcrack: https://github.com/j4k0xb/webcrack (webpack unbundler)
- obfuscator-io-deobfuscator: https://github.com/nicolo-ribaudo/obfuscator-io-deobfuscator
- D:\小说\study\ - Local study materials including synchrony and webcrack
