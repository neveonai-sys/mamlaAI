"""
District Court scraper for services.ecourts.gov.in.
Implements case lookup by CNR and advocate name search.
"""
from __future__ import annotations

import time
import logging
from typing import TYPE_CHECKING, Any

from ecourts_scraper.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from playwright.sync_api import Page
from ecourts_scraper.constants import DC_BASE_URL, DC_SELECTORS
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
    s = DC_SELECTORS[name]
    return s["value"], s["by"]


class DistrictCourtScraper(BaseScraper):
    """Scraper for District Court eCourts services."""

    def get_source_site(self) -> str:
        return "services.ecourts.gov.in"

    def get_data_type(self, method: str) -> str:
        return {
            "case_by_cnr": "case_detail",
            "search_advocate": "case_search",
        }.get(method, "case_detail")

    def build_cache_key(self, method: str, params: dict) -> str:
        if method == "case_by_cnr":
            return f"dc:case:{params['cnr']}"
        elif method == "search_advocate":
            state = params.get("state_id", "")
            district = params.get("district_id", "")
            court = params.get("court_complex_id", "")
            name = params.get("advocate_name", "").lower().replace(" ", "_")
            return f"dc:search:{state}:{district}:{court}:{name}"
        return f"dc:{method}:{hash(str(params))}"

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, page: Page, params: dict):
        page.goto(DC_BASE_URL, wait_until="domcontentloaded")
        time.sleep(2)

        self._dismiss_dialog(page)

        method = params.get("_method", "case_by_cnr")
        if method == "case_by_cnr":
            self._setup_cnr_form(page, params)
        elif method == "search_advocate":
            self._setup_advocate_form(page, params)

    def _setup_cnr_form(self, page: Page, params: dict):
        val, by = _sel("case_status_menu")
        click_element(page, val, by)
        time.sleep(1)
        self._dismiss_dialog(page)

        try:
            click_element(page, DC_SELECTORS["cnr_tab"]["value"], DC_SELECTORS["cnr_tab"]["by"], timeout=5000)
        except Exception:
            pass
        time.sleep(0.5)

    def _setup_advocate_form(self, page: Page, params: dict):
        val, by = _sel("case_status_menu")
        click_element(page, val, by)
        time.sleep(1)
        self._dismiss_dialog(page)

        state_val, state_by = _sel("state_select")
        select_option(page, state_val, params["state_id"], state_by)
        time.sleep(2)

        dist_val, dist_by = _sel("district_select")
        select_option(page, dist_val, "1", dist_by)
        time.sleep(1)
        select_option(page, dist_val, params["district_id"], dist_by)
        time.sleep(1)

        court_val, court_by = _sel("court_complex_select")
        select_option(page, court_val, params["court_complex_id"], court_by)
        time.sleep(1)

        adv_val, adv_by = _sel("advocate_tab")
        click_element(page, adv_val, adv_by)
        time.sleep(1)

    # ------------------------------------------------------------------
    # CAPTCHA
    # ------------------------------------------------------------------

    def solve_captcha(self, page: Page, attempt: int) -> bool:
        method = page.evaluate("() => document.querySelector('#cino') !== null")
        if method:
            cap_val, cap_by = _sel("cnr_captcha_image")
            inp_val, inp_by = _sel("cnr_captcha_input")
        else:
            cap_val, cap_by = _sel("captcha_image")
            inp_val, inp_by = _sel("captcha_input")

        try:
            image_bytes = extract_captcha_image_from_page(page, cap_val, cap_by)
        except Exception as e:
            logger.warning("DC CAPTCHA extraction failed: %s", e)
            return False

        solution = solve_captcha(image_bytes, attempt=attempt)
        if not solution:
            return False

        click_element(page, inp_val, inp_by, timeout=5000)
        fill_input(page, inp_val, solution, inp_by)
        return True

    def refresh_captcha(self, page: Page):
        try:
            cap_val, cap_by = _sel("captcha_image")
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
            time.sleep(1)

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit_and_check(self, page: Page) -> str:
        is_cnr = page.evaluate("() => document.querySelector('#cino') !== null")
        if is_cnr:
            sub_val, sub_by = _sel("cnr_submit")
        else:
            sub_val, sub_by = _sel("submit_button")

        click_element(page, sub_val, sub_by)
        time.sleep(2)

        # Check for invalid captcha dialog
        try:
            dialog_val, dialog_by = _sel("invalid_captcha_dialog")
            dialog_text = get_text_safe(page, dialog_val, dialog_by, timeout=2000)
            if dialog_text and "invalid captcha" in (dialog_text or "").lower():
                click_element(page, dialog_val, dialog_by, timeout=2000)
                return "captcha_error"
        except Exception:
            pass

        page_text = get_text_safe(page, "body", "css", timeout=1000) or ""
        page_upper = page_text.upper()

        if "INVALID CAPTCHA" in page_upper:
            return "captcha_error"
        if "RECORD NOT FOUND" in page_upper or "NO RECORD" in page_upper:
            return "not_found"
        if "INVALID REQUEST" in page_upper:
            return "error"

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
        result = {}

        details = get_table_data(page, "table.case_details_table", "css", timeout=5000)
        if details:
            result["case_details_raw"] = details
            result.update(self._extract_fields(details))

        status = get_table_as_dicts(page, "table.case_status_table", "css", timeout=3000)
        if status:
            result["case_status_details"] = status

        pet = get_table_as_dicts(page, "table.Petitioner_Advocate_table", "css", timeout=3000)
        if pet:
            result["petitioners"] = self._normalize_party_table(pet)

        resp = get_table_as_dicts(page, "table.Respondent_Advocate_table", "css", timeout=3000)
        if resp:
            result["respondents"] = self._normalize_party_table(resp)

        acts = get_table_as_dicts(page, "table.acts_table", "css", timeout=3000)
        if acts:
            result["acts_and_sections"] = acts

        fir = get_table_as_dicts(page, "table.FIR_details_table", "css", timeout=3000)
        if fir:
            result["fir_details"] = fir

        history = get_table_as_dicts(page, "table.history_table", "css", timeout=3000)
        if history:
            result["hearing_history"] = history

        orders = get_table_as_dicts(page, "table.order_table", "css", timeout=3000)
        if orders:
            result["orders"] = orders

        pet_list = result.get("petitioners", [])
        resp_list = result.get("respondents", [])
        if pet_list and resp_list:
            p_name = pet_list[0].get("name", "")
            r_name = resp_list[0].get("name", "")
            result["case_title"] = f"{p_name} vs {r_name}"

        return result

    def _extract_fields(self, table_data: list[list[str]]) -> dict:
        fields = {}
        for row in table_data:
            if len(row) >= 2:
                key = row[0].strip().lower().replace(" ", "_").rstrip(":")
                fields[key] = row[1].strip()
            if len(row) >= 4:
                key2 = row[2].strip().lower().replace(" ", "_").rstrip(":")
                if key2:
                    fields[key2] = row[3].strip()

        normalized = {}
        field_map = {
            "case_type": "case_type",
            "filing_number": "filing_number",
            "filing_date": "filing_date",
            "registration_number": "registration_number",
            "registration_date": "registration_date",
            "cnr_number": "cnr_number",
        }
        for target, src in field_map.items():
            if src in fields:
                normalized[target] = fields[src]
        normalized["_raw_fields"] = fields
        return normalized

    def _normalize_party_table(self, table_data: list[dict]) -> list[dict]:
        """Normalize party table rows from DC format."""
        parties = []
        for row in table_data:
            name = row.get("data", [""])[0] if isinstance(row.get("data"), list) else ""
            advocate = row.get("data", ["", ""])[1] if isinstance(row.get("data"), list) and len(row.get("data", [])) > 1 else ""
            if not name:
                name = " ".join(str(v) for v in row.values())
            parties.append({"name": name.strip(), "advocate": advocate.strip()})
        return parties

    def _parse_advocate_search(self, page: Page) -> dict:
        case_list = get_table_as_dicts(page, "#dispTable", "css", timeout=5000)
        return {"case_list": case_list}

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
        for _ in range(2):
            try:
                page.locator(
                    "button.close, .modal .close, button:has-text('OK'), button:has-text('×')"
                ).first.click(timeout=2000)
                time.sleep(0.5)
            except Exception:
                break
