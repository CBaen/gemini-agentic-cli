"""
Check what content we actually got from the Gemini share link
"""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.web import fetch_url_browser

test_url = "https://gemini.google.com/share/279bc5291f81"

print("Fetching with wait_for='load'...")
success, html = fetch_url_browser(test_url, wait_for="load", timeout=15000)

if success:
    print(f"\nFetched {len(html)} characters")

    # Extract visible text (very rough - just remove script/style tags and HTML)
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = ' '.join(text.split())  # Normalize whitespace

    print("\nFirst 1000 characters of visible text:")
    print("=" * 60)
    print(text[:1000])
    print("=" * 60)

    # Search for keywords
    keywords = ['qdrant', 'vector', 'database', 'semantic', 'search', 'research', 'embedding']
    print("\nKeyword search:")
    for kw in keywords:
        count = text.lower().count(kw)
        if count > 0:
            print(f"  '{kw}': found {count} times")
else:
    print(f"Failed: {html}")
