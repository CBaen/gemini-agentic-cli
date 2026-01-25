"""
Test with real browser user agent
Some sites detect headless browsers and block them
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.sync_api import sync_playwright

test_url = "https://gemini.google.com/share/279bc5291f81"

print("Testing with real browser user agent...")

try:
    with sync_playwright() as p:
        # Launch with more realistic browser settings
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled'
            ]
        )

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )

        page = context.new_page()

        # Hide automation signals
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("Loading page...")
        page.goto(test_url, wait_until="load", timeout=15000)

        print("Waiting for content...")
        page.wait_for_timeout(8000)  # Wait 8 seconds for dynamic load

        text = page.evaluate("document.body.innerText")

        browser.close()

        print(f"\nText length: {len(text)} characters")

        if "qdrant" in text.lower():
            print("\nSUCCESS! Found 'qdrant'!")
            print("\nFirst 800 characters:")
            print("=" * 60)
            print(text[:800])
            print("=" * 60)
        else:
            print("\nStill not loading. First 300 chars:")
            print(text[:300])

            if len(text) < 500:
                print("\nGemini may be blocking automated browsers.")
                print("The content requires authentication or anti-bot measures.")

except Exception as e:
    print(f"Error: {e}")
