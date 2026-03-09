"""
LLM-based self-healing agent (Layer 3).

When the ScrapeAgent detects repeated selector failures, this module:
  1. Captures the current page HTML and a screenshot
  2. Sends them to OpenAI with the broken selector info
  3. Receives a suggested replacement selector
  4. Upserts it into the ecourts_selectors MongoDB collection
  5. Returns the new selector so the agent can retry
"""
import logging
import base64
from typing import TYPE_CHECKING, Any

from ecourts_scraper.cache.collections import get_selectors_collection

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger("django")


def attempt_self_heal(
    page: "Page",
    site: str,
    page_name: str,
    element_name: str,
    broken_selector: dict,
    error_message: str = "",
) -> dict | None:
    """
    Attempt to heal a broken selector using LLM analysis.

    Args:
        page: The Playwright page in its current state
        site: e.g. "hcservices.ecourts.gov.in"
        page_name: e.g. "case_status" or "causelist"
        element_name: e.g. "captcha_image" or "submit_button"
        broken_selector: {"by": "id", "value": "captcha_image"} that failed
        error_message: The exception text from the failure

    Returns:
        New selector dict {"by": ..., "value": ...} or None on failure.
    """
    from ecourts_scraper.constants import SELF_HEAL_ENABLED
    if not SELF_HEAL_ENABLED:
        return None

    try:
        html_snippet = _capture_html_snippet(page)
        screenshot_b64 = _capture_screenshot(page)

        new_selector = _ask_llm_for_selector(
            site=site,
            page_name=page_name,
            element_name=element_name,
            broken_selector=broken_selector,
            error_message=error_message,
            html_snippet=html_snippet,
            screenshot_b64=screenshot_b64,
        )

        if new_selector:
            _upsert_selector(site, page_name, element_name, new_selector, broken_selector)
            logger.info(
                "Self-heal succeeded for %s/%s/%s: %s -> %s",
                site, page_name, element_name,
                broken_selector, new_selector,
            )
            return new_selector

    except Exception as e:
        logger.error("Self-heal failed for %s/%s/%s: %s", site, page_name, element_name, e)

    return None


def get_selector(site: str, page_name: str, element_name: str, default: dict) -> dict:
    """
    Read a selector from ecourts_selectors collection with fallback to default.
    This is the primary entry point scrapers should use to resolve selectors.
    """
    try:
        col = get_selectors_collection()
        doc = col.find_one(
            {"site": site, "page": page_name, "element": element_name},
            {"_id": 0, "selector": 1},
        )
        if doc and doc.get("selector"):
            return doc["selector"]
    except Exception as e:
        logger.debug("Selector lookup failed, using default: %s", e)

    return default


def _capture_html_snippet(page: "Page", max_chars: int = 8000) -> str:
    """Get a trimmed HTML snapshot of the page body."""
    try:
        html = page.content()
        body_start = html.find("<body")
        if body_start > 0:
            html = html[body_start:]
        if len(html) > max_chars:
            html = html[:max_chars] + "\n<!-- truncated -->"
        return html
    except Exception:
        return ""


def _capture_screenshot(page: "Page") -> str:
    """Take a PNG screenshot and return base64-encoded string."""
    try:
        screenshot_bytes = page.screenshot(type="png", full_page=False)
        return base64.b64encode(screenshot_bytes).decode("ascii")
    except Exception:
        return ""


def _ask_llm_for_selector(
    site: str,
    page_name: str,
    element_name: str,
    broken_selector: dict,
    error_message: str,
    html_snippet: str,
    screenshot_b64: str,
) -> dict | None:
    """Call OpenAI to suggest a replacement selector."""
    from django.conf import settings
    from ecourts_scraper.constants import SELF_HEAL_MODEL

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        logger.warning("Self-heal: OPENAI_API_KEY not configured")
        return None

    import openai
    client = openai.OpenAI(api_key=api_key)

    system_prompt = (
        "You are an expert web scraping engineer. A CSS/XPath selector broke on an Indian eCourts website. "
        "Given the page HTML and the broken selector, suggest a replacement selector. "
        "Respond ONLY with a JSON object: {\"by\": \"css\" | \"id\" | \"xpath\", \"value\": \"<selector>\"}\n"
        "Rules:\n"
        "- Prefer 'id' selectors when possible (most stable)\n"
        "- Prefer 'css' over 'xpath' when both work\n"
        "- The selector must uniquely identify the target element\n"
        "- No explanation, just the JSON object"
    )

    user_content = [
        {
            "type": "text",
            "text": (
                f"Site: {site}\n"
                f"Page: {page_name}\n"
                f"Element: {element_name}\n"
                f"Broken selector: {broken_selector}\n"
                f"Error: {error_message}\n\n"
                f"Page HTML (truncated):\n```html\n{html_snippet}\n```"
            ),
        },
    ]

    if screenshot_b64:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
        })

    try:
        response = client.chat.completions.create(
            model=SELF_HEAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        import json
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

        parsed = json.loads(raw)
        if "by" in parsed and "value" in parsed and parsed["by"] in ("css", "id", "xpath"):
            return {"by": parsed["by"], "value": parsed["value"]}

        logger.warning("Self-heal LLM returned invalid format: %s", raw)

    except Exception as e:
        logger.error("Self-heal LLM call failed: %s", e)

    return None


def _upsert_selector(
    site: str,
    page_name: str,
    element_name: str,
    new_selector: dict,
    old_selector: dict,
):
    """Persist the healed selector to MongoDB."""
    from datetime import datetime, timezone

    col = get_selectors_collection()
    col.update_one(
        {"site": site, "page": page_name, "element": element_name},
        {
            "$set": {
                "selector": new_selector,
                "previous_selector": old_selector,
                "healed_at": datetime.now(timezone.utc),
                "source": "llm_self_heal",
            },
            "$inc": {"heal_count": 1},
        },
        upsert=True,
    )
