"""
Cause list scraper for High Court eCourts services.
Navigates to HC cause list page, selects daily list / advocate-wise,
and parses the resulting tables.

HC cause list URL pattern:
  https://hcservices.ecourts.gov.in/hcservices/causelist_main.php
  (varies by high court -- some use /hcservices/causelist/ or similar)
"""
import time
import logging
from typing import TYPE_CHECKING, Any

from ecourts_scraper.scrapers.base import BaseScraper
from ecourts_scraper.constants import HC_CAUSELIST_BASE, HC_SELECTORS

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ecourts_scraper.infra.captcha import (
    extract_captcha_image_from_page,
    solve_captcha,
)
from ecourts_scraper.infra.parsers import (
    get_text_safe,
    get_table_data,
    get_table_as_dicts,
    element_exists,
    click_element,
    fill_input,
    select_option,
)

logger = logging.getLogger("django")

CAUSELIST_URL = "https://hcservices.ecourts.gov.in/hcservices/causelist_main.php"

CAUSELIST_SELECTORS = {
    "state_select": {"by": "id", "value": "sess_state_code"},
    "court_complex_select": {"by": "id", "value": "court_complex_code"},
    "daily_list_radio": {"by": "xpath", "value": "//input[@value='DAILY LIST']"},
    "advocate_wise_radio": {"by": "xpath", "value": "//input[@value='ADVOCATE WISE']"},
    "courtroom_wise_radio": {"by": "xpath", "value": "//input[@value='COURT NO WISE']"},
    "date_input": {"by": "id", "value": "causelist_date"},
    "advocate_input": {"by": "id", "value": "svalue"},
    "court_no_input": {"by": "id", "value": "courtno"},
    "search_button": {"by": "xpath", "value": '//div[@id="advsearch"]/input[2]'},
    "result_tables": {"by": "xpath", "value": "//table"},
}


class CauseListScraper(BaseScraper):
    """Scraper for High Court cause lists."""

    def get_source_site(self) -> str:
        return "hcservices.ecourts.gov.in"

    def get_data_type(self, method: str) -> str:
        return "causelist"

    def build_cache_key(self, method: str, params: dict) -> str:
        court = params.get("high_court_id", "")
        bench = params.get("bench_code", "")
        date = params.get("date", "")
        search_type = params.get("causelist_type", "daily")
        query = params.get("query", "").lower().replace(" ", "_")
        return f"hc:causelist:{court}:{bench}:{date}:{search_type}:{query}"

    def navigate(self, page: "Page", params: dict):
        page.goto(CAUSELIST_URL, wait_until="domcontentloaded")
        time.sleep(2)

        self._dismiss_dialog(page)

        hc_id = params.get("high_court_id")
        bench_code = params.get("bench_code")

        if hc_id:
            sel = CAUSELIST_SELECTORS["state_select"]
            select_option(page, sel["value"], hc_id, sel["by"])
            time.sleep(1)

        if bench_code:
            sel = CAUSELIST_SELECTORS["court_complex_select"]
            select_option(page, sel["value"], bench_code, sel["by"])
            time.sleep(1)

    def solve_captcha(self, page: "Page", attempt: int) -> bool:
        # HC cause list pages typically don't require CAPTCHA
        return True

    def refresh_captcha(self, page: "Page"):
        pass

    def fill_form(self, page: "Page", params: dict):
        causelist_type = params.get("causelist_type", "daily")

        if causelist_type == "advocate":
            sel = CAUSELIST_SELECTORS["daily_list_radio"]
            click_element(page, sel["value"], sel["by"])
            time.sleep(1)

            sel = CAUSELIST_SELECTORS["advocate_wise_radio"]
            click_element(page, sel["value"], sel["by"])
            time.sleep(1)

            query = params.get("query", "")
            if query:
                sel = CAUSELIST_SELECTORS["advocate_input"]
                fill_input(page, sel["value"], query, sel["by"])

        elif causelist_type == "courtroom":
            sel = CAUSELIST_SELECTORS["daily_list_radio"]
            click_element(page, sel["value"], sel["by"])
            time.sleep(1)

            sel = CAUSELIST_SELECTORS["courtroom_wise_radio"]
            click_element(page, sel["value"], sel["by"])
            time.sleep(1)

            court_no = params.get("court_no", "")
            if court_no:
                sel = CAUSELIST_SELECTORS["court_no_input"]
                fill_input(page, sel["value"], court_no, sel["by"])

        else:
            sel = CAUSELIST_SELECTORS["daily_list_radio"]
            click_element(page, sel["value"], sel["by"])
            time.sleep(1)

    def submit_and_check(self, page: "Page") -> str:
        sel = CAUSELIST_SELECTORS["search_button"]
        try:
            click_element(page, sel["value"], sel["by"])
        except Exception:
            pass
        time.sleep(3)

        body_text = get_text_safe(page, "body", "css", timeout=3000) or ""
        if "no list available" in body_text.lower():
            return "not_found"

        if element_exists(page, "table", "css", timeout=5000):
            return "success"

        return "error"

    def parse_results(self, page: "Page", params: dict) -> dict:
        return self._parse_cause_list_tables(page)

    def _parse_cause_list_tables(self, page: "Page") -> dict:
        """Parse cause list tables grouped by bench/court number."""
        entries = []
        current_bench = None

        try:
            tables = page.locator("table").all()
        except Exception:
            return {"entries": [], "total_entries": 0}

        for table in tables:
            try:
                rows = table.locator("tr").all()
                for row in rows:
                    headers = row.locator("th").all()
                    cells = row.locator("td").all()

                    if headers and len(headers) == 1:
                        header_text = headers[0].text_content().strip()
                        if header_text:
                            current_bench = header_text

                    elif cells:
                        cell_texts = [c.text_content().strip() for c in cells]
                        if any(cell_texts):
                            entry = {
                                "bench": current_bench or "",
                                "data": cell_texts,
                            }
                            if len(cell_texts) >= 3:
                                entry["sl_no"] = cell_texts[0]
                                entry["case_number"] = cell_texts[1] if len(cell_texts) > 1 else ""
                                entry["parties"] = cell_texts[2] if len(cell_texts) > 2 else ""
                                entry["advocate"] = cell_texts[3] if len(cell_texts) > 3 else ""
                                entry["purpose"] = cell_texts[4] if len(cell_texts) > 4 else ""
                            entries.append(entry)
            except Exception:
                continue

        grouped = {}
        for e in entries:
            bench = e.get("bench", "Unknown")
            if bench not in grouped:
                grouped[bench] = []
            grouped[bench].append(e)

        result_entries = []
        for bench_name, items in grouped.items():
            result_entries.append({
                "court_no": bench_name,
                "judge": "",
                "items": items,
            })

        return {
            "entries": result_entries,
            "total_entries": len(entries),
        }

    def validate_result(self, result: dict) -> bool:
        if not result:
            return False
        if "entries" in result:
            return True
        return False

    def _dismiss_dialog(self, page: "Page"):
        try:
            page.locator("button.close, .modal .close, button:has-text('OK')").first.click(timeout=2000)
        except Exception:
            pass
