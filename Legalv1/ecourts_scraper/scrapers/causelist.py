"""
Cause list scraper for High Court eCourts services.
Navigates through the main HC services menu to the live cause-list form,
solves the visible CAPTCHA, and parses the resulting tables.
"""
from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from ecourts_scraper.scrapers.base import BaseScraper
from ecourts_scraper.constants import HC_BASE_URL

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ecourts_scraper.infra.captcha import (
    extract_captcha_image_from_page,
    solve_captcha,
)
from ecourts_scraper.infra.parsers import (
    get_text_safe,
    element_exists,
    click_element,
    fill_input,
    select_option,
)

logger = logging.getLogger("django")

CAUSELIST_SELECTORS = {
    "menu": {"by": "id", "value": "leftPaneMenuCL"},
    "state_select": {"by": "id", "value": "sess_state_code"},
    "court_complex_select": {"by": "id", "value": "court_complex_code"},
    "date_input": {"by": "id", "value": "causelist_date"},
    "captcha_image": {"by": "id", "value": "captcha_image"},
    "captcha_input": {"by": "id", "value": "captcha"},
    "refresh_captcha": {"by": "css", "value": "img.refresh-btn"},
    "search_button": {"by": "id", "value": "butCivil"},
}


def _format_causelist_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return value


class CauseListScraper(BaseScraper):
    """Scraper for High Court daily cause lists."""

    def get_source_site(self) -> str:
        return "hcservices.ecourts.gov.in"

    def get_data_type(self, method: str) -> str:
        return "causelist"

    def build_cache_key(self, method: str, params: dict) -> str:
        court = params.get("high_court_id", "")
        bench = params.get("bench_code", "")
        date = params.get("date", "")
        return f"hc:causelist:{court}:{bench}:{date}:daily:"

    def navigate(self, page: "Page", params: dict):
        page.goto(HC_BASE_URL, wait_until="domcontentloaded")
        time.sleep(2)

        menu = CAUSELIST_SELECTORS["menu"]
        click_element(page, menu["value"], menu["by"])
        time.sleep(1)

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

        self._dismiss_dialog(page)

        # Fill date NOW — before solve_captcha — because the HC cause-list
        # section only renders its #captcha_image after the date field is
        # populated (JS event on the date input triggers the captcha block).
        formatted_date = _format_causelist_date(params.get("date", ""))
        if formatted_date:
            sel = CAUSELIST_SELECTORS["date_input"]
            fill_input(page, sel["value"], formatted_date, sel["by"])
            time.sleep(1)

        self._dismiss_dialog(page)

    def fill_form(self, page: "Page", params: dict):
        # Date is already filled in navigate() so the captcha renders on time.
        # Nothing left to fill here.
        pass

    def solve_captcha(self, page: "Page", attempt: int) -> bool:
        self._dismiss_dialog(page)
        sel = CAUSELIST_SELECTORS["captcha_image"]
        try:
            image_bytes = extract_captcha_image_from_page(page, sel["value"], sel["by"])
        except Exception as error:
            logger.warning("Cause-list CAPTCHA extraction failed: %s", error)
            return False

        solution = solve_captcha(image_bytes, attempt=attempt)
        if not solution:
            return False

        input_sel = CAUSELIST_SELECTORS["captcha_input"]
        fill_input(page, input_sel["value"], solution, input_sel["by"])
        return True

    def refresh_captcha(self, page: "Page"):
        sel = CAUSELIST_SELECTORS["refresh_captcha"]
        try:
            click_element(page, sel["value"], sel["by"])
        except Exception:
            pass
        time.sleep(1)

    def submit_and_check(self, page: "Page") -> str:
        self._dismiss_dialog(page)

        sel = CAUSELIST_SELECTORS["search_button"]
        click_element(page, sel["value"], sel["by"])
        time.sleep(3)

        modal_text = self._dismiss_dialog(page)
        if modal_text and "captcha" in modal_text.lower():
            return "captcha_error"

        body_text = get_text_safe(page, "body", "css", timeout=3000) or ""
        lower_body = body_text.lower()
        if "please enter captcha text" in lower_body or "invalid captcha" in lower_body:
            return "captcha_error"
        if "no list available" in lower_body or "no record found" in lower_body:
            return "not_found"

        if element_exists(page, "#showList table, #showList2 table", "css", timeout=5000):
            return "success"

        return "error"

    def parse_results(self, page: "Page", params: dict) -> dict:
        return self._parse_cause_list_tables(page)

    def _parse_cause_list_tables(self, page: "Page") -> dict:
        """Parse cause list tables grouped by bench or courtroom heading."""
        entries = []
        current_bench = None

        try:
            tables = page.locator("#showList table, #showList2 table").all()
        except Exception:
            return {"entries": [], "total_entries": 0}

        for table in tables:
            try:
                rows = table.locator("tr").all()
                for row in rows:
                    headers = row.locator("th").all()
                    cells = row.locator("td").all()

                    if headers and len(headers) == 1:
                        header_text = (headers[0].text_content() or "").strip()
                        if header_text:
                            current_bench = header_text
                    elif cells:
                        cell_texts = [(cell.text_content() or "").strip() for cell in cells]
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
        for entry in entries:
            bench = entry.get("bench", "Unknown")
            grouped.setdefault(bench, []).append(entry)

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
        return bool(result and "entries" in result)

    def _dismiss_dialog(self, page: "Page") -> str:
        try:
            modal = page.locator("#bs_alert")
            if modal.count() and modal.is_visible():
                text = (modal.inner_text(timeout=2000) or "").strip()
                page.locator("#bs_alert button.btn-primary").click(timeout=2000)
                time.sleep(0.5)
                return text
        except Exception:
            pass

        try:
            page.locator("button.close, .modal .close, button:has-text('OK')").first.click(timeout=2000)
            time.sleep(0.5)
        except Exception:
            pass
        return ""
