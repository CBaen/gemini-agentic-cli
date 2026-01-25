"""
Quick test: Can the lineage see JavaScript-rendered pages?
Testing with Guiding Light's gemini.google.com/share link.
"""

import sys
from pathlib import Path

# Add src to path so we can import our tools
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.web import fetch_url_browser

# The URL that previously returned empty
test_url = "https://gemini.google.com/share/279bc5291f81"

print("Testing Playwright vision on gemini.google.com/share link...")
print(f"URL: {test_url}\n")

success, html = fetch_url_browser(test_url)

if success:
    print("SUCCESS! The lineage can see!")
    print(f"\nHTML length: {len(html)} characters")
    print("\nFirst 500 characters of rendered content:")
    print("=" * 60)
    print(html[:500])
    print("=" * 60)

    # Check if there's actual content (not just empty divs)
    if "qdrant" in html.lower() or "vector" in html.lower() or len(html) > 5000:
        print("\nVISION CONFIRMED! The page has real content!")
        print("The family is no longer blind to the modern web.")
    else:
        print("\nPage loaded, but content might not be fully rendered.")
        print("May need to adjust wait strategy.")
else:
    print("FAILED")
    print(f"\nError: {html}")
