"""
Save the fetched content to file for inspection
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
    print(f"SUCCESS! Fetched {len(html)} characters")

    # Save full HTML
    with open("fetched_content.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to: fetched_content.html")

    # Extract and save visible text
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = ' '.join(text.split())

    with open("fetched_content.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Visible text saved to: fetched_content.txt")

    # Search for keywords
    keywords = ['qdrant', 'vector', 'database', 'semantic', 'search', 'research', 'embedding']
    print("\nKeyword search in visible text:")
    for kw in keywords:
        count = text.lower().count(kw)
        if count > 0:
            print(f"  '{kw}': found {count} times")

    if text.lower().count('qdrant') > 0 or len(text) > 1000:
        print("\nVISION CONFIRMED! The lineage can see JavaScript-rendered pages!")
else:
    print(f"Failed: {html}")
