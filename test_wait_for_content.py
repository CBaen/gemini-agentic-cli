"""
Test waiting for actual conversation content to load
Gemini share links load content dynamically after page load
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright

test_url = "https://gemini.google.com/share/279bc5291f81"

print("Testing with additional wait for content...")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading page...")
        page.goto(test_url, wait_until="load", timeout=15000)

        print("Waiting 5 seconds for content to load...")
        page.wait_for_timeout(5000)  # Wait 5 more seconds for dynamic content

        html = page.content()
        browser.close()

        print(f"\nFetched {len(html)} characters after waiting")

        # Save it
        with open("fetched_with_wait.html", "w", encoding="utf-8") as f:
            f.write(html)

        # Check for content
        if "qdrant" in html.lower():
            print("FOUND 'qdrant' in the content!")
        elif len(html) > 500000:
            print("Large content fetched - might have conversation data")

            # Try to find any conversation-like patterns
            import re
            # Look for common message patterns
            if re.search(r'message|response|query|answer', html, re.I):
                print("Found message-related content")
        else:
            print("Content might still be loading dynamically")

except Exception as e:
    print(f"Error: {e}")
