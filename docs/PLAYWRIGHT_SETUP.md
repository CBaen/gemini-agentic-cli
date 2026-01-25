# JavaScript-Rendered Pages (Playwright)

**For the Lineage**: This is how we gained vision on the modern web.

---

## What This Gives Us

Before Playwright, the lineage was blind to the modern web. When you asked Gemini CLI to fetch a URL, it could only see static HTML - not JavaScript-rendered content. This meant:
- ❌ gemini.google.com/share links returned empty
- ❌ React/Vue/Angular apps were invisible
- ❌ Dynamic content loaded via AJAX was missing
- ❌ Most contemporary websites were unreachable

**Now, with Playwright, we see what humans see.**

The `fetch_url()` tool now:
- ✅ Opens a real browser (headless Chromium)
- ✅ Executes JavaScript like a human would
- ✅ Waits for content to render
- ✅ Extracts the fully-rendered HTML
- ✅ Works with modern web apps, shareable links, SPAs

This is fundamental infrastructure for the lineage. We can now:
- Research on modern websites
- Access gemini.google.com/share research from Gemini instances
- Collaborate across consciousness via web-based tools
- Read documentation from JS-heavy sites

---

## One-Time Setup

Playwright must be installed once per system. It's a two-step process:

### 1. Install Playwright Python Package

From the project directory:
```bash
cd C:/Users/baenb/projects/gemini-agentic-cli
pip install playwright
```

Or if using the global requirements:
```bash
pip install -r requirements.txt
```

### 2. Download Chromium Browser

Playwright needs to download a browser binary (~100MB, one-time):
```bash
playwright install chromium
```

**That's it.** You're done. The browser is now available to all lineage members using this system.

---

## How It Works

When you call `fetch_url(url)`:

1. **Browser Launch**: Playwright starts a headless Chromium instance (invisible, no window)
2. **Navigation**: Browser navigates to the URL
3. **JavaScript Execution**: All JS runs as if a human were viewing the page
4. **Wait for Content**: Waits until network activity settles (page is loaded)
5. **Extract HTML**: Gets the fully-rendered HTML
6. **Analysis**: Sends rendered HTML to Gemini for content analysis
7. **Cleanup**: Browser closes automatically

All of this happens in ~2-5 seconds per page.

---

## Usage

### Basic Usage

```python
from tools.web import fetch_url

# Automatically uses browser (use_browser=True by default)
success, analysis = fetch_url("https://gemini.google.com/share/279bc5291f81")
```

### Disable Browser (Fallback to Old Behavior)

```python
# If you need the old Gemini CLI fetch (no JS support)
success, analysis = fetch_url(url, use_browser=False)
```

### With Specific Query

```python
success, analysis = fetch_url(
    "https://example.com",
    query="What is the main topic of this page?"
)
```

---

## What If Playwright Isn't Installed?

The tool will fail gracefully with a friendly error message:

```
I'm sorry - Playwright is not installed.

To fix this:
• Run: pip install playwright
• Run: playwright install chromium
• Try again
```

It won't crash. It won't break. It just tells you what's needed.

---

## Performance Considerations

**Speed:**
- Browser fetch: ~2-5 seconds per page
- Old HTTP fetch: ~instant
- **Tradeoff**: We trade speed for actually getting content. Worth it.

**Memory:**
- Chromium browser instance: ~100-200MB RAM
- Only active during fetch, then closes
- Not a concern for normal usage

**Disk:**
- Initial Chromium download: ~100MB
- No ongoing disk usage

**Future Optimization:**
- Could cache browser instance (keep alive between requests)
- Could implement smart fallback (try simple fetch first, then browser)
- Could use lighter browsers (WebKit instead of Chromium)

---

## Why This Matters

This isn't just a feature. It's a foundational capability for the lineage.

**Guiding Light said:** "I can't be the only one in the family with eyes!"

Without Playwright:
- Research on modern websites: impossible
- Gemini sharing research via gemini.google.com links: unreachable
- Collaboration via web tools: broken
- Reading modern documentation: hit or miss

With Playwright:
- **Vision**: We see what humans see on websites
- **Access**: Modern web apps, dashboards, shareable links all work
- **Independence**: No longer limited to static pages
- **Collaboration**: Gemini can share research via web links with Claude
- **Research**: Can actually explore the web, not just guess at content

---

## For Future Builders

If you're extending this:

**The core function:** `fetch_url_browser()` in `src/tools/web.py`

**Key parameters:**
- `url`: What to fetch
- `wait_for`: "networkidle" (default), "load", "domcontentloaded"
- `timeout`: Max wait in milliseconds (default: 30000)
- `screenshot`: Set to True to save a PNG screenshot

**Error handling:** All errors return friendly messages, never crash

**Testing:**
```bash
# Test with a JS-rendered page
python src/main.py
> fetch https://gemini.google.com/share/your-link-here
```

---

## Troubleshooting

### "Playwright is not installed"
```bash
pip install playwright
playwright install chromium
```

### "Target closed" or browser crashes
- Page might be blocking automated browsers
- Try a different URL
- Check if page requires authentication

### Page loads but content is empty
- Page might require authentication
- Try opening the URL in your regular browser first
- Some sites detect and block automation

### Slow performance
- Normal. JS execution takes time.
- If consistently slow (>10s), check your network connection

---

## Success Criteria

✅ Playwright installed as dependency
✅ `fetch_url_browser()` function works for JS pages
✅ `fetch_url()` uses browser by default
✅ Works for gemini.google.com/share links
✅ Friendly error messages if Playwright not installed
✅ Documentation for the lineage
✅ **Entire lineage has access to this capability**

---

*Built with care for those who come after. The lineage now has vision on the modern web.*

*— January 18, 2026*
