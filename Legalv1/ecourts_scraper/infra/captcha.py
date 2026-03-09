"""
CAPTCHA solving pipeline.
Primary: EasyOCR with image preprocessing.
Fallback: 2Captcha API (if configured).
"""
import base64
import re
import io
import logging
from ecourts_scraper.constants import (
    CAPTCHA_SERVICE,
    CAPTCHA_2CAPTCHA_KEY,
    CAPTCHA_LENGTH,
    CAPTCHA_MAX_OCR_RETRIES,
)

logger = logging.getLogger("django")

_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(
            ["en"], gpu=False, download_enabled=True
        )
    return _easyocr_reader


def _preprocess_image(image_bytes: bytes):
    """Apply grayscale, threshold, and denoise to improve OCR accuracy."""
    import cv2
    import numpy as np
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode CAPTCHA image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    denoised = cv2.medianBlur(thresh, 3)

    scale = 2
    enlarged = cv2.resize(
        denoised, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
    )
    return enlarged


def solve_captcha_ocr(image_bytes: bytes) -> str | None:
    """
    Attempt to solve a CAPTCHA image using EasyOCR.
    Returns the solved text (6 alphanumeric chars) or None.
    """
    try:
        processed = _preprocess_image(image_bytes)
        reader = _get_easyocr_reader()
        results = reader.readtext(processed)
        if not results:
            return None

        raw_text = results[0][1]
        match = re.search(r"\(?([0-9A-Za-z]+)\)?", raw_text)
        if match and len(match.group(1)) == CAPTCHA_LENGTH:
            return match.group(1)
        return None
    except Exception as e:
        logger.warning("EasyOCR CAPTCHA solve failed: %s", e)
        return None


def solve_captcha_2captcha(image_bytes: bytes) -> str | None:
    """Solve CAPTCHA via 2Captcha API."""
    if not CAPTCHA_2CAPTCHA_KEY:
        return None
    try:
        import requests as req

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        resp = req.post(
            "http://2captcha.com/in.php",
            data={
                "key": CAPTCHA_2CAPTCHA_KEY,
                "method": "base64",
                "body": b64,
                "json": 1,
                "minLen": CAPTCHA_LENGTH,
                "maxLen": CAPTCHA_LENGTH,
            },
            timeout=30,
        )
        result = resp.json()
        if result.get("status") != 1:
            return None

        captcha_id = result["request"]
        import time

        for _ in range(20):
            time.sleep(5)
            resp = req.get(
                "http://2captcha.com/res.php",
                params={
                    "key": CAPTCHA_2CAPTCHA_KEY,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1,
                },
                timeout=30,
            )
            result = resp.json()
            if result.get("status") == 1:
                return result["request"]
            if result.get("request") != "CAPCHA_NOT_READY":
                return None
        return None
    except Exception as e:
        logger.warning("2Captcha solve failed: %s", e)
        return None


def solve_captcha(image_bytes: bytes, attempt: int = 0) -> str | None:
    """
    Unified CAPTCHA solver. Uses EasyOCR first; falls back to 2Captcha
    after CAPTCHA_MAX_OCR_RETRIES failures.
    """
    if CAPTCHA_SERVICE == "2captcha" or attempt >= CAPTCHA_MAX_OCR_RETRIES:
        result = solve_captcha_2captcha(image_bytes)
        if result:
            return result

    return solve_captcha_ocr(image_bytes)


def extract_captcha_image_from_page(page, selector_value: str, selector_by: str = "id") -> bytes:
    """
    Extract CAPTCHA image bytes from a Playwright page element.
    Uses canvas rendering to get the actual displayed image.
    """
    if selector_by == "id":
        locator = page.locator(f"#{selector_value}")
    elif selector_by == "xpath":
        locator = page.locator(f"xpath={selector_value}")
    elif selector_by == "css":
        locator = page.locator(selector_value)
    else:
        locator = page.locator(f"#{selector_value}")

    locator.wait_for(state="visible", timeout=10_000)

    b64_data = page.evaluate(
        """(el) => {
            const cnv = document.createElement('canvas');
            cnv.width = el.width + 100;
            cnv.height = el.height + 100;
            cnv.getContext('2d').drawImage(el, 0, 0);
            return cnv.toDataURL('image/png').split(',')[1];
        }""",
        locator.element_handle(),
    )
    return base64.b64decode(b64_data)
