"""
High Court scraper for hcservices.ecourts.gov.in.
Implements case lookup by CNR and advocate name search.
"""
from __future__ import annotations

import time
import logging
from typing import TYPE_CHECKING, Any

from ecourts_scraper.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from playwright.sync_api import Page
from ecourts_scraper.constants import HC_BASE_URL, HC_SELECTORS
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


def _sel(name: str) -> tuple[str, str]:
    """Get (selector_value, selector_by) from HC_SELECTORS."""
    s = HC_SELECTORS[name]
    return s["value"], s["by"]


class HighCourtScraper(BaseScraper):
    """Scraper for High Court eCourts services."""

    def get_source_site(self) -> str:
        return "hcservices.ecourts.gov.in"

    def get_data_type(self, method: str) -> str:
        return {
            "case_by_cnr": "case_detail",
            "search_advocate": "case_search",
            "causelist": "causelist",
        }.get(method, "case_detail")

    def build_cache_key(self, method: str, params: dict) -> str:
        if method == "case_by_cnr":
            return f"hc:case:{params['cnr']}"
        elif method == "search_advocate":
            court = params.get("high_court_id", "")
            bench = params.get("bench_code", "")
            name = params.get("advocate_name", "").lower().replace(" ", "_")
            return f"hc:search:{court}:{bench}:{name}"
        return f"hc:{method}:{hash(str(params))}"

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, page: Page, params: dict):
        """Navigate to the HC case status page and prepare the form."""
        page.goto(HC_BASE_URL, wait_until="domcontentloaded")
        time.sleep(1)

        val, by = _sel("case_status_menu")
        click_element(page, val, by)
        time.sleep(0.5)

        self._dismiss_dialog(page)

        method = params.get("_method", "case_by_cnr")
        if method == "case_by_cnr":
            self._setup_cnr_form(page, params)
        elif method == "search_advocate":
            self._setup_advocate_form(page, params)

    def _setup_cnr_form(self, page: Page, params: dict):
        """Select the CNR search tab/option on HC site."""
        try:
            click_element(page, "CSCino", "id", timeout=5000)
        except Exception:
            pass
        time.sleep(0.5)

    def _setup_advocate_form(self, page: Page, params: dict):
        """Select state, bench, and open advocate search form."""
        state_val, state_by = _sel("state_select")
        select_option(page, state_val, params["high_court_id"], state_by)
        time.sleep(1)

        court_val, court_by = _sel("court_complex_select")
        select_option(page, court_val, params["bench_code"], court_by)
        time.sleep(0.5)

        adv_val, adv_by = _sel("advocate_name_link")
        click_element(page, adv_val, adv_by)
        time.sleep(0.5)

    # ------------------------------------------------------------------
    # CAPTCHA
    # ------------------------------------------------------------------

    def solve_captcha(self, page: Page, attempt: int) -> bool:
        cap_val, cap_by = _sel("captcha_image")
        try:
            image_bytes = extract_captcha_image_from_page(page, cap_val, cap_by)
        except Exception as e:
            logger.warning("CAPTCHA image extraction failed: %s", e)
            return False

        solution = solve_captcha(image_bytes, attempt=attempt)
        if not solution:
            return False

        inp_val, inp_by = _sel("captcha_input")
        fill_input(page, inp_val, solution, inp_by)
        return True

    def refresh_captcha(self, page: Page):
        cap_val, cap_by = _sel("captcha_image")
        try:
            click_element(page, cap_val, cap_by, timeout=5000)
        except Exception:
            pass
        time.sleep(1)

    # ------------------------------------------------------------------
    # Form filling
    # ------------------------------------------------------------------

    def fill_form(self, page: Page, params: dict):
        method = params.get("_method", "case_by_cnr")
        if method == "case_by_cnr":
            cnr_val, cnr_by = _sel("cnr_input")
            fill_input(page, cnr_val, params["cnr"], cnr_by)
        elif method == "search_advocate":
            adv_val, adv_by = _sel("advocate_name_input")
            fill_input(page, adv_val, params["advocate_name"], adv_by)
            time.sleep(int(params.get("_wait", 2)))

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit_and_check(self, page: Page) -> str:
        sub_val, sub_by = _sel("submit_button")
        click_element(page, sub_val, sub_by)
        time.sleep(2)

        err_val, err_by = _sel("error_span")
        error_text = get_text_safe(page, err_val, err_by, timeout=3000)
        if error_text:
            upper = error_text.upper()
            if "THERE IS AN ERROR" in upper or "INVALID CAPTCHA" in upper:
                return "captcha_error"
            if "RECORD NOT FOUND" in upper or "NO RECORD" in upper:
                return "not_found"

        if element_exists(page, "table.case_details_table", "css", timeout=5000):
            return "success"

        if element_exists(page, "#dispTable", "css", timeout=3000):
            return "success"

        return "error"

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_results(self, page: Page, params: dict) -> dict:
        method = params.get("_method", "case_by_cnr")
        if method == "case_by_cnr":
            return self._parse_case_detail(page)
        elif method == "search_advocate":
            return self._parse_advocate_search(page)
        return {}

    def _parse_case_detail(self, page: Page) -> dict:
        """Parse the full case detail page."""
        result = {}

        # Case details table
        details_table = get_table_data(page, "table.case_details_table", "css", timeout=5000)
        if details_table:
            result["case_details_raw"] = details_table
            result.update(self._extract_case_fields(details_table))

        # Case status
        status_data = get_table_as_dicts(page, "table.case_status_table", "css", timeout=3000)
        if status_data:
            result["case_status_details"] = status_data

        # Petitioner and advocate
        pet_text = get_text_safe(page, "span.Petitioner_Advocate_table", "css", timeout=3000)
        if pet_text:
            result["petitioners_raw"] = pet_text
            result["petitioners"] = self._parse_party_text(pet_text)

        # Respondent and advocate
        resp_text = get_text_safe(page, "span.Respondent_Advocate_table", "css", timeout=3000)
        if resp_text:
            result["respondents_raw"] = resp_text
            result["respondents"] = self._parse_party_text(resp_text)

        # Acts and sections
        acts_data = get_table_as_dicts(page, "#act_table", "css", timeout=3000)
        if acts_data:
            result["acts_and_sections"] = acts_data

        # Hearing history
        history = get_table_as_dicts(page, "table.history_table", "css", timeout=3000)
        if history:
            result["hearing_history"] = history

        # Orders
        orders = get_table_as_dicts(page, "table.order_table", "css", timeout=3000)
        if orders:
            result["orders"] = orders

        # IA details
        ia_data = get_table_as_dicts(page, "table.IAheading", "css", timeout=3000)
        if ia_data:
            result["ia_details"] = ia_data

        # Build case title from petitioners/respondents
        pet_names = [p.get("name", "") for p in result.get("petitioners", [])]
        resp_names = [r.get("name", "") for r in result.get("respondents", [])]
        if pet_names and resp_names:
            result["case_title"] = f"{pet_names[0]} vs {resp_names[0]}"

        return result

    def _extract_case_fields(self, table_data: list[list[str]]) -> dict:
        """Extract structured fields from case_details_table rows."""
        fields = {}
        for row in table_data:
            if len(row) >= 2:
                key = row[0].strip().lower().replace(" ", "_").rstrip(":")
                fields[key] = row[1].strip()
            if len(row) >= 4:
                key2 = row[2].strip().lower().replace(" ", "_").rstrip(":")
                if key2:
                    fields[key2] = row[3].strip()
        # Normalize known fields
        mapping = {
            "case_type": ["case_type"],
            "filing_number": ["filing_number"],
            "filing_date": ["filing_date"],
            "registration_number": ["registration_number"],
            "registration_date": ["registration_date"],
            "cnr_number": ["cnr_number", "cnr"],
        }
        normalized = {}
        for target, sources in mapping.items():
            for src in sources:
                if src in fields:
                    normalized[target] = fields[src]
                    break
        normalized["_raw_fields"] = fields
        return normalized

    def _parse_party_text(self, text: str) -> list[dict]:
        """Parse petitioner/respondent text block into structured list."""
        parties = []
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        current_party = None
        for line in lines:
            lower = line.lower()
            if lower.startswith("advocate") or lower.startswith("adv.") or lower.startswith("adv :"):
                if current_party:
                    adv_name = line.split(":", 1)[-1].strip() if ":" in line else line
                    current_party["advocate"] = adv_name
            elif any(c.isdigit() and ")" in line[:5] for c in line[:3]):
                if current_party:
                    parties.append(current_party)
                name = line.split(")", 1)[-1].strip() if ")" in line else line
                current_party = {"name": name, "advocate": ""}
            else:
                if current_party is None:
                    current_party = {"name": line, "advocate": ""}
                else:
                    current_party["name"] += f" {line}"
        if current_party:
            parties.append(current_party)
        return parties

    def _parse_advocate_search(self, page: Page) -> dict:
        """Parse the advocate search results table."""
        num_text = get_text_safe(
            page, HC_SELECTORS["number_of_cases"]["value"],
            HC_SELECTORS["number_of_cases"]["by"], timeout=5000
        )
        case_list = get_table_as_dicts(page, "#dispTable", "css", timeout=5000)
        return {
            "number_of_cases_text": num_text or "",
            "case_list": case_list,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_result(self, result: dict) -> bool:
        if not result:
            return False
        if result.get("status") == "not_found":
            return True
        if "case_details_raw" in result or "case_list" in result:
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dismiss_dialog(self, page: Page):
        """Dismiss any popup dialog that appears on the HC site."""
        try:
            page.locator("button.close, .modal .close, button:has-text('OK')").first.click(timeout=2000)
        except Exception:
            pass
