"""
Abstract base class for all eCourts scrapers.
Concrete implementations must provide site-specific logic for
navigation, form filling, CAPTCHA handling, and result parsing.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page


class BaseScraper(ABC):
    """
    Interface contract that every scraper must implement.
    The ScrapeAgent calls these methods in order during state transitions.
    """

    @abstractmethod
    def get_source_site(self) -> str:
        """Return the base domain (e.g. 'hcservices.ecourts.gov.in')."""

    @abstractmethod
    def get_data_type(self, method: str) -> str:
        """Map a scraper method name to a cache data_type key."""

    @abstractmethod
    def build_cache_key(self, method: str, params: dict) -> str:
        """Build a unique cache key for the given method + params."""

    @abstractmethod
    def navigate(self, page: "Page", params: dict):
        """Navigate to the correct page on the eCourts site."""

    @abstractmethod
    def solve_captcha(self, page: "Page", attempt: int) -> bool:
        """
        Attempt to solve the CAPTCHA and enter the solution.
        Returns True if CAPTCHA text was entered, False to retry.
        """

    @abstractmethod
    def refresh_captcha(self, page: "Page"):
        """Click the CAPTCHA refresh button/image to get a new one."""

    @abstractmethod
    def fill_form(self, page: "Page", params: dict):
        """Fill in the search/lookup form fields (after CAPTCHA is solved)."""

    @abstractmethod
    def submit_and_check(self, page: "Page") -> str:
        """
        Submit the form and detect the outcome.
        Returns one of: 'success', 'captcha_error', 'blocked', 'not_found', 'error'
        """

    @abstractmethod
    def parse_results(self, page: "Page", params: dict) -> dict:
        """Parse the results page into a structured dict."""

    @abstractmethod
    def validate_result(self, result: dict) -> bool:
        """Return True if the parsed result looks complete and valid."""
