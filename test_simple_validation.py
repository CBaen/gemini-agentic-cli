"""
Simple validation: Can we see JavaScript-rendered content?
Testing with a public React demo site
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.web import fetch_url_browser

# Public React demo - definitely JS-rendered
test_url = "https://reactjs.org"

print("Testing vision on reactjs.org (JavaScript-rendered site)...")
print(f"URL: {test_url}\n")

success, html = fetch_url_browser(test_url, wait_for="load", timeout=15000)

if success:
    print(f"SUCCESS! Fetched {len(html)} characters")

    # Check for React-specific content
    text = html.lower()
    has_react = "react" in text
    has_substantial = len(html) > 10000

    if has_react and has_substantial:
        print("\nVISION CONFIRMED!")
        print("The lineage can see JavaScript-rendered pages.")
        print(f"Found 'react' in content: {has_react}")
        print(f"Substantial content (>10KB): {has_substantial}")
        print("\nReady to meet Gemini.")
    else:
        print("\nPartial success - content loaded but might be incomplete")
else:
    print(f"Failed: {html}")
