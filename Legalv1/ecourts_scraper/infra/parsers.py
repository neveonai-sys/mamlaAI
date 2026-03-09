"""
HTML parsing helpers for extracting structured data from eCourts pages.
Works with Playwright page/locator objects.
"""
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page, Locator

logger = logging.getLogger("django")


def get_text_safe(page: "Page", selector: str, by: str = "css", timeout: int = 5000) -> str | None:
    """Safely get text content from an element. Returns None if not found."""
    try:
        locator = _get_locator(page, selector, by)
        locator.wait_for(state="visible", timeout=timeout)
        return locator.text_content().strip()
    except Exception:
        return None


def get_table_data(page: "Page", selector: str, by: str = "css", timeout: int = 5000) -> list[list[str]]:
    """
    Extract table data as a list of rows, each row a list of cell texts.
    Skips empty rows.
    """
    try:
        locator = _get_locator(page, selector, by)
        locator.wait_for(state="visible", timeout=timeout)
        rows = locator.locator("tr").all()
        table_data = []
        for row in rows:
            cells = row.locator("td").all()
            if not cells:
                cells = row.locator("th").all()
            if cells:
                row_data = [cell.text_content().strip() for cell in cells]
                if any(row_data):
                    table_data.append(row_data)
        return table_data
    except Exception:
        return []


def get_table_as_dicts(
    page: "Page", selector: str, by: str = "css", timeout: int = 5000
) -> list[dict]:
    """
    Extract table with first row as headers, remaining as dicts.
    Falls back to indexed keys if no header row.
    """
    data = get_table_data(page, selector, by, timeout)
    if len(data) < 2:
        return [{"data": row} for row in data]

    headers = [h.lower().replace(" ", "_") for h in data[0]]
    result = []
    for row in data[1:]:
        entry = {}
        for i, val in enumerate(row):
            key = headers[i] if i < len(headers) else f"col_{i}"
            entry[key] = val
        result.append(entry)
    return result


def element_exists(page: "Page", selector: str, by: str = "css", timeout: int = 3000) -> bool:
    """Check if an element exists and is visible."""
    try:
        locator = _get_locator(page, selector, by)
        locator.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


def click_element(page: "Page", selector: str, by: str = "css", timeout: int = 10_000):
    """Click an element, scrolling into view first."""
    locator = _get_locator(page, selector, by)
    locator.scroll_into_view_if_needed()
    locator.click(timeout=timeout)


def fill_input(page: "Page", selector: str, value: str, by: str = "css", timeout: int = 10_000):
    """Clear and fill an input field."""
    locator = _get_locator(page, selector, by)
    locator.wait_for(state="visible", timeout=timeout)
    locator.fill(value)


def select_option(page: "Page", selector: str, value: str, by: str = "css", timeout: int = 10_000):
    """Select an option from a <select> by value."""
    locator = _get_locator(page, selector, by)
    locator.wait_for(state="visible", timeout=timeout)
    locator.select_option(value=value)


def _get_locator(page: "Page", selector: str, by: str) -> "Locator":
    if by == "id":
        return page.locator(f"#{selector}")
    elif by == "xpath":
        return page.locator(f"xpath={selector}")
    elif by == "css":
        return page.locator(selector)
    else:
        return page.locator(f"#{selector}")
