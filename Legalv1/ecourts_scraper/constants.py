"""
eCourts scraper constants: URLs, selectors, court codes, TTLs.
Selectors here are defaults -- the self-healing agent can override them
via the ecourts_selectors MongoDB collection.
"""
import os

# ---------------------------------------------------------------------------
# Target site URLs
# ---------------------------------------------------------------------------
HC_BASE_URL = "https://hcservices.ecourts.gov.in/hcservices/main.php"
DC_BASE_URL = "https://services.ecourts.gov.in/ecourtindia_v6/"

HC_CAUSELIST_BASE = "https://hcservices.ecourts.gov.in/hcservices/"
DC_CAUSELIST_BASE = "https://services.ecourts.gov.in/ecourtindia_v6/"

# ---------------------------------------------------------------------------
# Environment-driven configuration
# ---------------------------------------------------------------------------
CAPTCHA_SERVICE = os.getenv("ECOURTS_CAPTCHA_SERVICE", "easyocr")
CAPTCHA_2CAPTCHA_KEY = os.getenv("ECOURTS_2CAPTCHA_API_KEY", "")
MAX_CONCURRENT_BROWSERS = int(os.getenv("ECOURTS_MAX_CONCURRENT_BROWSERS", "3"))
PROXY_POOL_URL = os.getenv("ECOURTS_PROXY_POOL_URL", "")
HC_RATE_LIMIT_PER_MIN = int(os.getenv("ECOURTS_HC_RATE_LIMIT_PER_MIN", "10"))
DC_RATE_LIMIT_PER_MIN = int(os.getenv("ECOURTS_DC_RATE_LIMIT_PER_MIN", "10"))
CACHE_DEFAULT_TTL_HOURS = int(os.getenv("ECOURTS_CACHE_DEFAULT_TTL_HOURS", "24"))
SELF_HEAL_ENABLED = os.getenv("ECOURTS_SELF_HEAL_ENABLED", "true").lower() in ("true", "1")

# ---------------------------------------------------------------------------
# Cache TTLs (hours)
# ---------------------------------------------------------------------------
CACHE_TTL = {
    "case_detail": 24,
    "case_search": 12,
    "causelist": 6,
    "court_structure": 720,   # 30 days
    "display_board": 0.083,   # ~5 minutes
    "order_pdf": 168,         # 7 days
}

# ---------------------------------------------------------------------------
# Self-healing agent configuration
# ---------------------------------------------------------------------------
SELF_HEAL_MODEL = os.getenv("ECOURTS_SELF_HEAL_MODEL", "gpt-4o-mini")
SELF_HEAL_MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# CAPTCHA configuration
# ---------------------------------------------------------------------------
CAPTCHA_LENGTH = 6
CAPTCHA_MAX_OCR_RETRIES = 5
CAPTCHA_MAX_TOTAL_RETRIES = 10

# ---------------------------------------------------------------------------
# ScrapeAgent configuration
# ---------------------------------------------------------------------------
MAX_AGENT_RETRIES = 3
BROWSER_NAVIGATION_TIMEOUT_MS = 30_000
BROWSER_ACTION_TIMEOUT_MS = 15_000

# ---------------------------------------------------------------------------
# Default CSS/XPath selectors for High Court site
# These can be overridden by ecourts_selectors collection
# ---------------------------------------------------------------------------
HC_SELECTORS = {
    "case_status_menu": {"by": "id", "value": "leftPaneMenuCS"},
    "state_select": {"by": "id", "value": "sess_state_code"},
    "court_complex_select": {"by": "id", "value": "court_complex_code"},
    "advocate_name_link": {"by": "id", "value": "CSAdvName"},
    "advocate_name_input": {
        "by": "xpath",
        "value": "/html/body/div[1]/div/div[1]/div[2]/div/div[2]/div[14]/div[2]/div[2]/input",
    },
    "captcha_image": {"by": "id", "value": "captcha_image"},
    "captcha_input": {"by": "id", "value": "captcha"},
    "submit_button": {"by": "css", "value": ".Gobtn"},
    "error_span": {"by": "id", "value": "errSpan1"},
    "cnr_input": {"by": "id", "value": "cino"},
    "cnr_submit": {"by": "id", "value": "searchbtn"},
    # Case detail page
    "case_details_table": {"by": "css", "value": "table.case_details_table"},
    "case_status_table": {"by": "css", "value": "table.case_status_table"},
    "petitioner_table": {"by": "css", "value": "span.Petitioner_Advocate_table"},
    "respondent_table": {"by": "css", "value": "span.Respondent_Advocate_table"},
    "acts_table": {"by": "id", "value": "act_table"},
    "history_table": {"by": "css", "value": "table.history_table"},
    "orders_table": {"by": "css", "value": "table.order_table"},
    "ia_table": {"by": "css", "value": "table.IAheading"},
    "case_list_table": {"by": "id", "value": "dispTable"},
    "number_of_cases": {
        "by": "xpath",
        "value": '//*[@id="showList2"]/div[1]/h4',
    },
    "back_button": {
        "by": "xpath",
        "value": '/html/body/div[1]/div/div[1]/div[2]/div/div[2]/div[48]/input',
    },
}

# ---------------------------------------------------------------------------
# Default selectors for District Court site
# ---------------------------------------------------------------------------
DC_SELECTORS = {
    "case_status_menu": {"by": "id", "value": "leftPaneMenuCS"},
    "state_select": {"by": "id", "value": "sess_state_code"},
    "district_select": {"by": "id", "value": "sess_dist_code"},
    "court_complex_select": {"by": "id", "value": "court_complex_code"},
    "advocate_tab": {"by": "id", "value": "advname-tabMenu"},
    "advocate_name_input": {"by": "id", "value": "advocate_name"},
    "captcha_image": {
        "by": "xpath",
        "value": '//div[@id="div_captcha_adv"]//img[@id="captcha_image"]',
    },
    "captcha_input": {"by": "id", "value": "adv_captcha_code"},
    "submit_button": {
        "by": "xpath",
        "value": '/html/body/div[1]/div/main/div[2]/div/div/div[4]/div[1]/form/div[3]/div[2]/button',
    },
    "cnr_tab": {"by": "id", "value": "cino-tabMenu"},
    "cnr_input": {"by": "id", "value": "cino"},
    "cnr_captcha_image": {
        "by": "xpath",
        "value": '//div[@id="div_captcha_cino"]//img[@id="captcha_image"]',
    },
    "cnr_captcha_input": {"by": "id", "value": "cino_captcha_code"},
    "cnr_submit": {"by": "id", "value": "searchCino"},
    "invalid_captcha_dialog": {
        "by": "xpath",
        "value": '/html/body/div[9]/div/div/div[1]/button',
    },
    "case_details_table": {"by": "css", "value": "table.case_details_table"},
    "case_status_table": {"by": "css", "value": "table.case_status_table"},
    "petitioner_table": {"by": "css", "value": "table.Petitioner_Advocate_table"},
    "respondent_table": {"by": "css", "value": "table.Respondent_Advocate_table"},
    "acts_table": {"by": "css", "value": "table.acts_table"},
    "history_table": {"by": "css", "value": "table.history_table"},
    "orders_table": {"by": "css", "value": "table.order_table"},
    "fir_table": {"by": "css", "value": "table.FIR_details_table"},
    "case_list_table": {"by": "id", "value": "dispTable"},
    "back_button": {"by": "id", "value": "main_back_AdvName"},
}

# ---------------------------------------------------------------------------
# High Court codes (state_code -> bench codes)
# Source: hcservices.ecourts.gov.in dropdown values
# ---------------------------------------------------------------------------
HIGH_COURT_CODES = {
    "1": {"name": "Allahabad High Court", "benches": [
        {"code": "1", "name": "Principal Seat, Allahabad"},
        {"code": "2", "name": "Lucknow Bench"},
    ]},
    "2": {"name": "High Court of Andhra Pradesh", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "3": {"name": "High Court of Bombay", "benches": [
        {"code": "1", "name": "Appellate Side, Bombay"},
        {"code": "2", "name": "Original Side, Bombay"},
        {"code": "3", "name": "Bench at Aurangabad"},
        {"code": "4", "name": "Bench at Nagpur"},
        {"code": "5", "name": "Bench at Goa"},
    ]},
    "5": {"name": "Delhi High Court", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "7": {"name": "The Gauhati High Court", "benches": [
        {"code": "1", "name": "Principal Seat, Guwahati"},
        {"code": "2", "name": "Kohima Bench"},
        {"code": "3", "name": "Aizawl Bench"},
        {"code": "4", "name": "Itanagar Bench"},
    ]},
    "9": {"name": "High Court of Gujarat", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "12": {"name": "High Court of Karnataka", "benches": [
        {"code": "1", "name": "Principal Bench, Bengaluru"},
        {"code": "2", "name": "Dharwad Bench"},
        {"code": "3", "name": "Kalaburagi Bench"},
    ]},
    "13": {"name": "High Court of Kerala", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "14": {"name": "Madhya Pradesh High Court", "benches": [
        {"code": "1", "name": "Principal Seat, Jabalpur"},
        {"code": "2", "name": "Bench at Gwalior"},
        {"code": "3", "name": "Bench at Indore"},
    ]},
    "15": {"name": "Madras High Court", "benches": [
        {"code": "1", "name": "Principal Bench, Chennai"},
        {"code": "2", "name": "Madurai Bench"},
    ]},
    "18": {"name": "High Court of Orissa", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "19": {"name": "Patna High Court", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "20": {"name": "Punjab and Haryana High Court", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "21": {"name": "Rajasthan High Court", "benches": [
        {"code": "1", "name": "Principal Seat, Jodhpur"},
        {"code": "2", "name": "Bench at Jaipur"},
    ]},
    "24": {"name": "Calcutta High Court", "benches": [
        {"code": "1", "name": "Appellate Side"},
        {"code": "2", "name": "Original Side"},
        {"code": "3", "name": "Circuit Bench, Jalpaiguri"},
        {"code": "4", "name": "Circuit Bench, Port Blair"},
    ]},
    "25": {"name": "High Court of Chhattisgarh", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "26": {"name": "High Court of Jharkhand", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "27": {"name": "High Court of Uttarakhand", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "28": {"name": "High Court for State of Telangana", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "29": {"name": "High Court of Manipur", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "30": {"name": "High Court of Meghalaya", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "31": {"name": "High Court of Tripura", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "32": {"name": "High Court of Sikkim", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "33": {"name": "High Court of Himachal Pradesh", "benches": [
        {"code": "1", "name": "Principal Bench"},
    ]},
    "34": {"name": "High Court of J&K and Ladakh", "benches": [
        {"code": "1", "name": "Jammu Wing"},
        {"code": "2", "name": "Srinagar Wing"},
    ]},
}

# ---------------------------------------------------------------------------
# User-Agent rotation pool
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
