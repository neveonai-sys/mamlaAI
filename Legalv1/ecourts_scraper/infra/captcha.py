"""
CAPTCHA solving pipeline.
Primary: Capsolver image-to-text when configured.
Fallbacks: EasyOCR and then 2Captcha.
"""
import base64
import re
import io
import logging
import time
from ecourts_scraper.constants import (
    CAPTCHA_SERVICE,
    CAPTCHA_CAPSOLVER_KEY,
    CAPTCHA_2CAPTCHA_KEY,
    CAPTCHA_LENGTH,
    CAPTCHA_MAX_OCR_RETRIES,
)

logger = logging.getLogger("django")

_easyocr_reader = None


def _capsolver_key_hint() -> str:
    if not CAPTCHA_CAPSOLVER_KEY:
        return "unset"
    return f"...{CAPTCHA_CAPSOLVER_KEY[-6:]}"


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


def solve_captcha_capsolver(image_bytes: bytes) -> str | None:
    """Solve CAPTCHA via Capsolver image-to-text API."""
    if not CAPTCHA_CAPSOLVER_KEY:
        return None
    try:
        import requests as req

        payload = {
            "clientKey": CAPTCHA_CAPSOLVER_KEY,
            "task": {
                "type": "ImageToTextTask",
                "module": "common",
                "body": base64.b64encode(image_bytes).decode("utf-8"),
            },
        }
        create_resp = req.post(
            "https://api.capsolver.com/createTask",
            json=payload,
            timeout=30,
        )
        create_data = create_resp.json()
        task_id = create_data.get("taskId")
        if create_data.get("errorId"):
            logger.warning("Capsolver createTask failed: %s", create_data)
            return None

        # ImageToTextTask returns the OCR result directly from createTask.
        if create_data.get("status") == "ready":
            solution = (create_data.get("solution") or {}).get("text", "")
            solution = re.sub(r"[^A-Za-z0-9]", "", solution or "")
            logger.info(
                "Capsolver createTask returned direct result task_id=%s key=%s text_len=%s",
                task_id,
                _capsolver_key_hint(),
                len(solution),
            )
            if len(solution) == CAPTCHA_LENGTH:
                return solution
            return solution or None

        if not task_id:
            logger.warning("Capsolver createTask returned no task_id: %s", create_data)
            return None

        logger.info(
            "Capsolver createTask accepted task_id=%s key=%s",
            task_id,
            _capsolver_key_hint(),
        )

        logger.warning(
            "Capsolver createTask did not return a direct OCR result task_id=%s response=%s",
            task_id,
            create_data,
        )
        return None
    except Exception as e:
        logger.warning("Capsolver solve failed: %s", e)
        return None


def solve_captcha(image_bytes: bytes, attempt: int = 0) -> str | None:
    """
    Unified CAPTCHA solver. Uses EasyOCR first; falls back to 2Captcha
    after CAPTCHA_MAX_OCR_RETRIES failures.
    """
    if CAPTCHA_SERVICE == "capsolver":
        result = solve_captcha_capsolver(image_bytes)
        if result:
            return result

    if CAPTCHA_SERVICE == "2captcha" or attempt >= CAPTCHA_MAX_OCR_RETRIES:
        result = solve_captcha_2captcha(image_bytes)
        if result:
            return result

    return solve_captcha_ocr(image_bytes)


def _fetch_captcha_via_src(page, locator) -> bytes | None:
    """
    Fetch captcha bytes by reading the img src attribute and downloading it
    using the browser's current cookies.  Works even when the img element
    is inside a hidden container (display:none ancestor).
    Returns None if src is unavailable or fetch fails.
    """
    try:
        src = locator.get_attribute("src", timeout=5_000)
        if not src:
            return None
        # Resolve relative URLs against the current page origin
        abs_url = page.evaluate(
            "(src) => new URL(src, document.location.href).href", src
        )
        # Use the browser context's request so it carries the page's session cookies.
        # page.request is a global unauthenticated context; page.context.request shares cookies.
        response = page.context.request.get(abs_url, timeout=10_000)
        if response.ok:
            return response.body()
    except Exception as e:
        logger.debug("captcha src-fetch failed: %s", e)
    return None


def extract_captcha_image_from_page(page, selector_value: str, selector_by: str = "id") -> bytes:
    """
    Extract CAPTCHA image bytes from a Playwright page element.

    Strategy:
    1. Try to locate the element (attached, not necessarily visible).
    2. Attempt canvas-render (requires visibility).
    3. Fall back to fetching the image via its src URL using the page's cookies.
       This works even when the img is inside a display:none ancestor, which
       happens on DC pages where the captcha div is hidden until a tab click
       that the scraper may not have triggered yet.
    """
    if selector_by == "id":
        locator = page.locator(f"#{selector_value}")
    elif selector_by == "xpath":
        locator = page.locator(f"xpath={selector_value}")
    elif selector_by == "css":
        locator = page.locator(selector_value)
    else:
        locator = page.locator(f"#{selector_value}")

    # The HC website renders ALL menu sections into one DOM simultaneously,
    # so the same element ID (e.g. #captcha_image) can match multiple elements
    # with only one visible.  Pick the visible match where possible.
    count = locator.count()
    if count > 1:
        for i in range(count):
            candidate = locator.nth(i)
            try:
                if candidate.is_visible():
                    locator = candidate
                    break
            except Exception:
                pass
        else:
            locator = locator.first

    # Wait for the element to be attached to the DOM (not necessarily visible).
    # We handle the hidden case via src-fetch below.
    locator.wait_for(state="attached", timeout=10_000)

    # Try canvas render first (only works when element is visible)
    if locator.is_visible():
        try:
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
        except Exception as e:
            logger.debug("canvas captcha render failed, falling back to src-fetch: %s", e)

    # Element is hidden — fetch via src URL using the page's cookie session
    data = _fetch_captcha_via_src(page, locator)
    if data:
        return data

    raise RuntimeError(
        f"Could not extract captcha image for selector '{selector_value}': "
        "element is hidden and src-fetch also failed"
    )
