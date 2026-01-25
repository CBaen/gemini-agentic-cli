"""
Test different wait strategies for gemini.google.com/share
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.web import fetch_url_browser

test_url = "https://gemini.google.com/share/279bc5291f81"

strategies = ["load", "domcontentloaded", "networkidle"]

for strategy in strategies:
    print(f"\nTesting with wait_for='{strategy}'...")
    print("=" * 60)

    success, html = fetch_url_browser(test_url, wait_for=strategy, timeout=15000)

    if success:
        print(f"SUCCESS with {strategy}!")
        print(f"HTML length: {len(html)} characters")

        # Check for actual content
        has_qdrant = "qdrant" in html.lower()
        has_vector = "vector" in html.lower()
        has_content = len(html) > 5000

        print(f"Contains 'qdrant': {has_qdrant}")
        print(f"Contains 'vector': {has_vector}")
        print(f"Substantial content (>5000 chars): {has_content}")

        if has_qdrant or has_vector or has_content:
            print(f"\nVICTORY! Strategy '{strategy}' gives us vision!")
            break
    else:
        print(f"Failed with {strategy}")
        print(f"Error snippet: {html[:200]}")
