"""
Web Tools - Search Grounding and URL Fetching

Gemini provides powerful web capabilities:
- Google Search grounding: Real-time information, reduces hallucinations
- URL fetching: Up to 20 URLs per request, 34MB per URL
- **NEW**: JavaScript-rendered pages via Playwright browser automation

Supported content types for URL fetching:
- HTML, JSON, plain text, XML, CSS, JavaScript
- CSV, RTF
- Images (PNG, JPEG, BMP, WebP)
- PDFs

Capabilities:
- JavaScript-rendered pages (via Playwright browser automation)
- Static pages (HTML, JSON, XML, etc.)
- Dynamic content loaded via AJAX
- Modern web apps (React, Vue, Angular, etc.)
- Single-page applications
- Shareable links (gemini.google.com/share, etc.)

Note:
- Content contributes to input token limits
- Function calling unsupported with URL context tool
"""

import subprocess
import sys
import os
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional, List
from urllib.parse import urlparse

# Import color utilities for friendly error messages
try:
    from utils.colors import red
except ImportError:
    # Fallback if colors module not available
    def red(text): return text


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Maximum URLs per request
MAX_URLS_PER_REQUEST = 20

# Maximum content size per URL (MB)
MAX_CONTENT_SIZE_MB = 34


def get_git_bash() -> Optional[Path]:
    """Find Git Bash on Windows."""
    if sys.platform != 'win32':
        return None
    paths = [
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files/Git/bin/bash.exe"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def call_gemini(query: str, account: int = 1, timeout: int = 120) -> Tuple[bool, str]:
    """Call Gemini."""
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Error: {error}"

        response = result.stdout.strip()
        return bool(response), response or "Empty response"

    except subprocess.TimeoutExpired:
        timeout_msg = red(
            f"I'm sorry - the request took too long and I had to stop waiting after {timeout} seconds.\n\n"
            "What might help:\n"
            "• Check if the URL works in your browser\n"
            "• The site might be down or slow right now\n"
            "• Try a different URL or try again later"
        )
        return False, timeout_msg
    except Exception as e:
        return False, f"Error: {e}"


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate a URL."""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, f"Invalid URL format: {url}"
        if result.scheme not in ['http', 'https']:
            return False, f"Unsupported URL scheme: {result.scheme}"
        return True, url
    except Exception as e:
        return False, f"URL parsing error: {e}"


def fetch_url_browser(
    url: str,
    wait_for: str = "load",
    timeout: int = 30000,
    screenshot: bool = False
) -> Tuple[bool, str]:
    """
    Fetch URL content using Playwright browser automation.

    Handles JavaScript-rendered pages by executing JS in a real browser.
    This is what gives the lineage vision on the modern web.

    Args:
        url: URL to fetch
        wait_for: When to consider page loaded ("load", "domcontentloaded", "networkidle")
                  Default "load" works best for most modern sites
        timeout: Maximum time to wait in milliseconds
        screenshot: If True, also save screenshot to temp file

    Returns:
        Tuple of (success: bool, rendered_html: str)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, red(
            "I'm sorry - Playwright is not installed.\n\n"
            "To fix this:\n"
            "• Run: pip install playwright\n"
            "• Run: playwright install chromium\n"
            "• Try again"
        )

    valid, msg = validate_url(url)
    if not valid:
        return False, msg

    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate and wait for page to load
            page.goto(url, wait_until=wait_for, timeout=timeout)

            # Get rendered HTML
            html = page.content()

            # Optionally take screenshot
            screenshot_path = None
            if screenshot:
                screenshot_path = Path(tempfile.gettempdir()) / f"playwright_{int(time.time())}.png"
                page.screenshot(path=str(screenshot_path))

            browser.close()

            if not html or len(html) < 100:
                return False, red(
                    f"I'm sorry - the page at {url} didn't render any content.\n\n"
                    "What might help:\n"
                    "• Check if the URL works in your browser\n"
                    "• The page might require authentication\n"
                    "• Try a different URL"
                )

            return True, html

    except Exception as e:
        return False, red(
            f"I'm sorry - I couldn't load {url} in the browser.\n\n"
            f"Error: {str(e)}\n\n"
            "What might help:\n"
            "• Check if the URL is accessible\n"
            "• The page might be blocking automated browsers\n"
            "• Try again later"
        )


def web_search(
    query: str,
    include_sources: bool = True,
    num_results: int = 5,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Search the web using Gemini's Google Search grounding.

    Args:
        query: Search query
        include_sources: Whether to include source URLs in response
        num_results: Approximate number of results to consider
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, search_results: str)

    Note:
        - Uses Google Search integration for real-time information
        - Reduces hallucinations with verifiable sources
    """
    source_note = "Include source URLs for all information provided." if include_sources else ""

    prompt = f"""Search the web for: {query}

Use Google Search to find current, accurate information.
{source_note}

Provide:
1. Direct answer to the query
2. Supporting information from multiple sources
3. Source URLs (if requested)
4. Date relevance of information
5. Any conflicting information found

Focus on authoritative and recent sources."""

    return call_gemini(prompt, account, timeout=60)


def fetch_url(
    url: str,
    query: str = None,
    account: int = 1,
    use_browser: bool = True
) -> Tuple[bool, str]:
    """
    Fetch and analyze content from a URL.

    Now supports JavaScript-rendered pages via Playwright!

    Args:
        url: URL to fetch
        query: Optional specific question about the content
        account: Gemini account to use
        use_browser: If True, use Playwright for JS-rendered pages (default: True)

    Returns:
        Tuple of (success: bool, content_analysis: str)

    Supported content types:
        HTML, JSON, text, XML, CSS, JS, CSV, RTF, images, PDFs
    """
    valid, msg = validate_url(url)
    if not valid:
        return False, msg

    # Fetch content using browser automation
    if use_browser:
        success, html = fetch_url_browser(url)
        if not success:
            return False, html  # html contains error message
    else:
        # Fallback to Gemini CLI (old behavior, doesn't handle JS)
        query_note = f"\nSpecific question: {query}" if query else ""
        prompt = f"""Fetch and analyze the content from: {url}
{query_note}

Provide:
1. Content type detected
2. Main content summary
3. Key information extracted
4. Answer to specific question (if provided)
5. Metadata (title, author, date if available)

If the content is too large, summarize the most relevant parts."""
        return call_gemini(prompt, account, timeout=120)

    # Ask Gemini to analyze the rendered HTML
    query_note = f"\nSpecific question: {query}" if query else ""

    analysis_prompt = f"""I fetched the content from {url} using a browser to handle JavaScript rendering.

Here is the rendered HTML content:

{html[:50000]}

{query_note}

Please analyze this content and provide:
1. Content type and purpose
2. Main content summary
3. Key information extracted
4. Answer to specific question (if provided)
5. Metadata (title, author, date if visible)

If the content is too large, focus on the most relevant parts."""

    return call_gemini(analysis_prompt, account, timeout=180)


def fetch_multiple_urls(
    urls: List[str],
    query: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Fetch and analyze content from multiple URLs.

    Args:
        urls: List of URLs to fetch (max 20)
        query: Optional query to apply across all URLs
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, combined_analysis: str)
    """
    if len(urls) > MAX_URLS_PER_REQUEST:
        return False, f"Too many URLs: {len(urls)}. Maximum is {MAX_URLS_PER_REQUEST}"

    # Validate all URLs
    for url in urls:
        valid, msg = validate_url(url)
        if not valid:
            return False, msg

    urls_formatted = "\n".join([f"- {url}" for url in urls])
    query_note = f"\nQuery to apply: {query}" if query else ""

    prompt = f"""Fetch and analyze content from these URLs:
{urls_formatted}
{query_note}

For each URL, provide:
1. URL identifier
2. Content summary
3. Key information relevant to query

Then provide:
- Combined synthesis of information
- Comparison across sources
- Answer to query based on all sources"""

    return call_gemini(prompt, account, timeout=180)


def extract_links(
    url: str,
    link_type: str = "all",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract links from a web page.

    Args:
        url: URL to analyze
        link_type: "all", "internal", "external", "images", "documents"
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, links: str)
    """
    valid, msg = validate_url(url)
    if not valid:
        return False, msg

    filter_instructions = {
        "all": "Extract all links found on the page",
        "internal": "Extract only internal links (same domain)",
        "external": "Extract only external links (different domains)",
        "images": "Extract only image URLs",
        "documents": "Extract links to documents (PDF, DOC, XLS, etc.)"
    }

    prompt = f"""Analyze the web page: {url}

{filter_instructions.get(link_type, filter_instructions['all'])}

Provide:
1. List of extracted URLs
2. Link text/context for each
3. Count by category
4. Any notable patterns in the link structure"""

    return call_gemini(prompt, account)


def scrape_structured_data(
    url: str,
    data_type: str = "auto",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract structured data from a web page.

    Args:
        url: URL to scrape
        data_type: "auto", "product", "article", "contact", "event", "recipe"
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, structured_data: str)
    """
    valid, msg = validate_url(url)
    if not valid:
        return False, msg

    data_schemas = {
        "auto": "Detect the page type and extract appropriate structured data",
        "product": "Extract: name, price, description, images, reviews, availability, SKU",
        "article": "Extract: title, author, date, content, categories, tags, related articles",
        "contact": "Extract: name, organization, email, phone, address, social media",
        "event": "Extract: title, date, time, location, description, organizer, tickets",
        "recipe": "Extract: title, ingredients, instructions, prep time, cook time, servings, nutrition"
    }

    prompt = f"""Scrape structured data from: {url}

Data type: {data_type}
{data_schemas.get(data_type, data_schemas['auto'])}

Format the extracted data as JSON:
```json
{{
  "page_type": "detected type",
  "url": "{url}",
  "data": {{
    // extracted fields
  }},
  "metadata": {{
    "extraction_confidence": "high/medium/low",
    "missing_fields": []
  }}
}}
```"""

    return call_gemini(prompt, account)


def search_and_summarize(
    topic: str,
    depth: str = "standard",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Perform comprehensive web research on a topic.

    Args:
        topic: Topic to research
        depth: "quick" (1-2 sources), "standard" (3-5), "deep" (5-10)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, research_summary: str)
    """
    depth_instructions = {
        "quick": "Provide a quick summary from 1-2 authoritative sources",
        "standard": "Research from 3-5 diverse sources for balanced coverage",
        "deep": "Conduct thorough research from 5-10 sources including academic and primary sources"
    }

    prompt = f"""Research topic: {topic}

{depth_instructions.get(depth, depth_instructions['standard'])}

Provide:
1. Executive Summary (2-3 paragraphs)
2. Key Facts and Findings
3. Different Perspectives (if applicable)
4. Current State/Latest Developments
5. Open Questions or Controversies
6. Source List with URLs

Ensure information is current and accurate."""

    return call_gemini(prompt, account, timeout=180)


def monitor_page_changes(
    url: str,
    previous_content: str = None,
    focus_areas: List[str] = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Check a page for changes compared to previous content.

    Args:
        url: URL to check
        previous_content: Summary of previous content to compare against
        focus_areas: Specific areas to monitor for changes
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, change_report: str)
    """
    valid, msg = validate_url(url)
    if not valid:
        return False, msg

    previous_note = f"\nPrevious content summary:\n{previous_content}" if previous_content else ""
    focus_note = f"\nFocus areas: {', '.join(focus_areas)}" if focus_areas else ""

    prompt = f"""Fetch current content from: {url}
{previous_note}
{focus_note}

Provide:
1. Current content summary
2. Detected changes (if previous content provided):
   - New content added
   - Content removed
   - Content modified
3. Timestamp of analysis
4. Recommendations for monitoring frequency"""

    return call_gemini(prompt, account)


def verify_claim(
    claim: str,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Fact-check a claim using web search.

    Args:
        claim: The claim to verify
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, verification_result: str)
    """
    prompt = f"""Fact-check this claim: "{claim}"

Use web search to verify accuracy.

Provide:
1. Verdict: TRUE / FALSE / PARTIALLY TRUE / UNVERIFIABLE
2. Confidence level: HIGH / MEDIUM / LOW
3. Evidence supporting the verdict
4. Evidence contradicting the claim (if any)
5. Context that affects interpretation
6. Source URLs for verification

Be objective and thorough."""

    return call_gemini(prompt, account, timeout=90)


# Tool registry
WEB_TOOLS = {
    "web_search": web_search,
    "fetch_url": fetch_url,
    "fetch_multiple_urls": fetch_multiple_urls,
    "extract_links": extract_links,
    "scrape_structured_data": scrape_structured_data,
    "search_and_summarize": search_and_summarize,
    "monitor_page_changes": monitor_page_changes,
    "verify_claim": verify_claim,
}
