"""
Deobfuscate JavaScript-encrypted novel content.
Supports common patterns found on Chinese novel sites.

Usage:
    python decode_js_obfuscation.py <obfuscated_js_file>
    python decode_js_obfuscation.py <url>

Requires: Node.js with synchrony installed globally.
"""

import subprocess, sys, re, os, tempfile
import requests

def deobfuscate_with_synchrony(js_path):
    """Run synchrony deobfuscator on a JS file."""
    output = js_path.replace(".js", ".cleaned.js")
    try:
        subprocess.run(
            ["synchrony", "deobfuscate", js_path],
            check=True, capture_output=True, text=True, timeout=30
        )
        if os.path.exists(output):
            with open(output, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"synchrony error: {e}")
    return None

def download_js(url):
    """Fetch JS from URL."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "zh-CN,zh;q=0.9"}
    r = requests.get(url, headers=headers, timeout=15)
    return r.text

def extract_strings(js_code):
    """Extract string array from obfuscated code ('_0x...' pattern)."""
    # Match: var _0xa1b2 = ["str1", "str2", ...]
    match = re.search(r'(_0x[a-f0-9]+)\s*=\s*\\[(.*?)\\];', js_code, re.DOTALL)
    if match:
        var_name = match.group(1)
        arr_body = match.group(2)
        # Parse the array strings
        strings = re.findall(r'["\\']([^"\\']*)["\\'],', arr_body)
        return var_name, strings
    return None, []

def find_content_patterns(js_code):
    """Search for common content-loading patterns."""
    patterns = {
        "base64_decode": r"atob\\([^)]*\\)",
        "xor_decrypt": r"\\^\\s*0x[a-f0-9]+",
        "reverse_string": r"\\[\\]\\[\\"reverse\\"\\]\\(",
        "content_div": r"[\\"\\'](?:BookText|content|chapter)[\\"\\']",
        "decrypt_func": r"function\\s+(?:decrypt|decode|dec|a\\w)\\(",
    }
    found = {}
    for name, pat in patterns.items():
        matches = re.findall(pat, js_code)
        if matches:
            found[name] = len(matches)
    return found

def analyze(js_path_or_url):
    """Analyze JS for obfuscation pattern."""
    if js_path_or_url.startswith("http"):
        code = download_js(js_path_or_url)
    else:
        with open(js_path_or_url, "r", encoding="utf-8") as f:
            code = f.read()

    print(f"JS size: {len(code):,} chars")

    # Detect obfuscation type
    if "javascript-obfuscator" in code.lower() or re.search(r"_0x[a-f0-9]{4,6}\\s*=\\s*\\[", code):
        print("Detected: javascript-obfuscator / obfuscator.io")
        print("Action: Run synchrony deobfuscate <file>")
    elif "webpack" in code.lower() or re.search(r"\\(function\\(modules\\)", code[:1000]):
        print("Detected: Webpack bundle")
        print("Action: Run webcrack <file> -o output/")
    elif "eval(" in code[:5000]:
        print("Detected: eval()-based encoding")
        print("Action: Extract eval content and re-analyze")
    else:
        print("No known obfuscation pattern detected")

    # Show content clues
    patterns = find_content_patterns(code)
    if patterns:
        print(f"\nContent-related patterns found: {patterns}")

    return code

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decode_js_obfuscation.py <js_file_or_url>")
        sys.exit(1)

    analyze(sys.argv[1])
