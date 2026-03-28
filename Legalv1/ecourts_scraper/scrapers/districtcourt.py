"""
District Court scraper — services.ecourts.gov.in

=== VERIFIED PAGE STRUCTURE (do NOT change without re-verifying live) ===

Base URL: https://services.ecourts.gov.in/ecourtindia_v6/

--- CNR SEARCH ---
• The CNR search form is the DEFAULT view on the base URL (homepage).
  No menu click is needed — div#div_captcha_cnr is already in the DOM.
• DO NOT click #leftPaneMenuCS before CNR search — that opens the
  Case Status / advocate panel and REPLACES the CNR form.
• Captcha container  : div#div_captcha_cnr  (may have hidden ancestor)
• Captcha image      : img#captcha_image inside div#div_captcha_cnr
• Captcha input      : input#fcaptcha_code
• Submit button      : button#searchbtn  (calls funViewCinoHistory() via JS)
• CNR input          : input#cino
• AJAX endpoint only : ?p=cnr_status/searchByCNR/ — NOT a page with a form
• Outcome detection  : URL does not change; results inject into DOM via AJAX.
  Use wait_for_load_state('networkidle') after clicking #searchbtn.

--- ADVOCATE / PARTY SEARCH ---
• Click #leftPaneMenuCS to open Case Status panel (advocate form).
• Select state → wait for district dropdown populated (>1 option)
• Select district  → wait for court complex dropdown populated (>1 option)
• Select court complex → wait_for_load_state('networkidle') — heavy AJAX reload
• Then click #advname-tabMenu to switch to advocate tab
• Captcha container  : div#div_captcha_adv  (verify live if broken)
• Captcha image      : img#captcha_image inside div#div_captcha_adv
• Captcha input      : input#adv_captcha_code
• Submit button      : .Gobtn (CSS)

--- CAPTCHA IMAGE EXTRACTION ---
• Canvas-render approach requires the img to be visible.
• If the img is hidden (display:none ancestor), use _fetch_captcha_via_src():
  reads img.src attribute, fetches bytes via page.request.get() (shares cookies).
  This is implemented in ecourts_scraper/infra/captcha.py.

--- CNR/ADVOCATE DETECTION AT RUNTIME ---
• page._mamla_is_cnr flag is set in navigate() before any form interaction.
  This is the single source of truth for which flow is active — do not use
  URL inspection or DOM probing, both are unreliable after AJAX navigation.

=== END VERIFIED STRUCTURE ===
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

    def _is_cnr_page(self, page: Page) -> bool:
        """True when this browser session is doing a CNR lookup.
        We store a flag on the page object to avoid URL-parsing after AJAX
        navigation changes page.url to the submission endpoint.
        """
        return getattr(page, "_mamla_is_cnr", False)

    def navigate(self, page: Page, params: dict):
        method = params.get("_method", "case_by_cnr")
        page.goto(DC_BASE_URL, wait_until="domcontentloaded")
        time.sleep(2)
        self._dismiss_dialog(page)

        if method == "case_by_cnr":
            page._mamla_is_cnr = True
            self._setup_cnr_form(page, params)
        else:
            page._mamla_is_cnr = False
            self._setup_advocate_form(page, params)

    def _setup_cnr_form(self, page: Page, params: dict):
        # The CNR search form (div#div_captcha_cnr) is the DEFAULT view on the
        # base URL — it is already visible without any menu click.
        # Clicking #leftPaneMenuCS opens the Case Status / advocate panel and
        # REPLACES the CNR form, so we must NOT click any menu here.
        try:
            page.wait_for_selector(
                '#div_captcha_cnr img#captcha_image',
                state="attached",
                timeout=20_000,
            )
        except Exception:
            time.sleep(2)

    def _setup_advocate_form(self, page: Page, params: dict):
        val, by = _sel("case_status_menu")
        click_element(page, val, by)
        time.sleep(1)
        self._dismiss_dialog(page)

        state_val, state_by = _sel("state_select")
        select_option(page, state_val, params["state_id"], state_by)
        # Wait for district dropdown to be populated by state-change AJAX
        try:
            page.wait_for_function(
                "() => document.querySelector('#sess_dist_code') && document.querySelector('#sess_dist_code').options.length > 1",
                timeout=10_000,
            )
        except Exception:
            time.sleep(2)

        dist_val, dist_by = _sel("district_select")
        select_option(page, dist_val, "1", dist_by)
        time.sleep(0.5)
        select_option(page, dist_val, params["district_id"], dist_by)
        # Wait for court complex dropdown to be populated by district-change AJAX
        try:
            page.wait_for_function(
                "() => document.querySelector('#court_complex_code') && document.querySelector('#court_complex_code').options.length > 1",
                timeout=10_000,
            )
        except Exception:
            time.sleep(2)

        court_val, court_by = _sel("court_complex_select")
        select_option(page, court_val, params["court_complex_id"], court_by)
        # After selecting a court complex the site fires an AJAX that reloads the
        # case-search panel (with tabs + captcha).  Wait for networkidle so the
        # panel is fully rendered before we try to click the advocate tab.
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            time.sleep(3)

        adv_val, adv_by = _sel("advocate_tab")
        click_element(page, adv_val, adv_by)

        # Wait for the advocate captcha image to be rendered by JS after tab click.
        try:
            page.wait_for_selector(
                '#div_captcha_adv img#captcha_image',
                state="visible",
                timeout=20_000,
            )
        except Exception:
            # Fallback: plain sleep so solve_captcha still gets a chance
            time.sleep(3)

    # ------------------------------------------------------------------
    # CAPTCHA
    # ------------------------------------------------------------------

    def solve_captcha(self, page: Page, attempt: int) -> bool:
        # Use the flag set during navigate() to pick the right captcha elements.
        if self._is_cnr_page(page):
            cap_val, cap_by = _sel("cnr_captcha_image")  # div_captcha_cnr img
        else:
            cap_val, cap_by = _sel("captcha_image")      # div_captcha_adv img

        try:
            image_bytes = extract_captcha_image_from_page(page, cap_val, cap_by)
        except Exception as e:
            logger.warning("DC CAPTCHA extraction failed: %s", e)
            return False

        solution = solve_captcha(image_bytes, attempt=attempt)
        if not solution:
            return False

        if self._is_cnr_page(page):
            # CNR form elements have hidden ancestors — use JS directly,
            # no Playwright actionability checks (click/scroll/visible).
            page.evaluate(
                "(sol) => {"
                "  var el = document.getElementById('fcaptcha_code');"
                "  if (!el) return;"
                "  el.value = sol;"
                "  el.dispatchEvent(new Event('input',  {bubbles:true}));"
                "  el.dispatchEvent(new Event('change', {bubbles:true}));"
                "}",
                solution,
            )
        else:
            inp_val, inp_by = _sel("captcha_input")      # adv_captcha_code
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
            # CNR input has hidden ancestor — set via JS.
            page.evaluate(
                "(cnr) => {"
                "  var el = document.getElementById('cino');"
                "  if (!el) return;"
                "  el.value = cnr;"
                "  el.dispatchEvent(new Event('input',  {bubbles:true}));"
                "  el.dispatchEvent(new Event('change', {bubbles:true}));"
                "}",
                params["cnr"],
            )
        elif method == "search_advocate":
            adv_val, adv_by = _sel("advocate_name_input")
            fill_input(page, adv_val, params["advocate_name"], adv_by)
            time.sleep(1)

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit_and_check(self, page: Page) -> str:
        if self._is_cnr_page(page):
            # CNR submit button has hidden ancestor — call the onclick JS directly.
            page.evaluate("() => funViewCinoHistory()")
        else:
            sub_val, sub_by = _sel("submit_button")
            click_element(page, sub_val, sub_by)

        # Wait for AJAX response to land before inspecting the DOM.
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            time.sleep(3)

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
