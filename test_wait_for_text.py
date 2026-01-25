"""
Test waiting for actual text content to appear
Gemini share pages load conversation text dynamically
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright

test_url = "https://gemini.google.com/share/279bc5291f81"

print("Testing smart wait for content...")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading page...")
        page.goto(test_url, wait_until="load", timeout=15000)

        print("Waiting for conversation content to appear...")
        # Wait for text content to actually load (up to 10 seconds)
        # Gemini loads content after the page shell
        try:
            # Wait for any substantial text content to appear
            page.wait_for_function(
                "document.body.innerText.length > 500",
                timeout=10000
            )
            print("Content detected!")
        except:
            print("Timeout waiting for content, proceeding anyway...")

        html = page.content()
        text = page.evaluate("document.body.innerText")

        browser.close()

        print(f"\nHTML length: {len(html)} characters")
        print(f"Text length: {len(text)} characters")

        # Check for the actual content
        if "qdrant" in text.lower():
            print("\nSUCCESS! Found 'qdrant' in the text!")
            print("\nFirst 500 characters:")
            print("=" * 60)
            print(text[:500])
            print("=" * 60)
        else:
            print("\nContent not found. First 200 chars of text:")
            print(text[:200])

except Exception as e:
    print(f"Error: {e}")
