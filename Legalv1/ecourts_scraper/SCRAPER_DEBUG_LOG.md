# DC Scraper — Debug Log (Tried & Failed / Tried & Confirmed)

Keep this file updated. Before making any change to `districtcourt.py`, `constants.py`,
`captcha.py`, or `parsers.py` — read this first.

---

## CONFIRMED WORKING (do not change)

### CNR Search Navigation
- **Base URL:** `https://services.ecourts.gov.in/ecourtindia_v6/`
- CNR form (`div#div_captcha_cnr`) is the **DEFAULT view on the homepage** — visible without any click.
- **DO NOT** click `#leftPaneMenuCS` before CNR search — that opens the advocate/party panel and replaces the CNR form entirely.
- `?p=cnr_status/searchByCNR/` = AJAX submission endpoint only, not a renderable page. Navigating there gives a blank page with no form.
- `?p=home/` = also wrong, no form rendered there.

### CNR Form Selectors (verified 2026-03-22 from live browser inspector)
| Purpose | Selector |
|---|---|
| Captcha image | `img#captcha_image` inside `div#div_captcha_cnr` |
| Captcha input | `input#fcaptcha_code` |
| CNR input | `input#cino` |
| Submit button | `button#searchbtn` (`onclick="funViewCinoHistory()"`) |

### Captcha Image Extraction
- `div#div_captcha_cnr` and its children may have a **hidden ancestor** (`display:none`).
- Canvas-render (`drawImage`) fails when element is hidden.
- **Fix:** `_fetch_captcha_via_src()` in `captcha.py` — reads `img.src`, fetches bytes via `page.context.request.get()` which shares the browser context's session cookies.
- **CRITICAL:** Use `page.context.request.get()` NOT `page.request.get()`. `page.request` is a global unauthenticated context — it does NOT carry the browser's cookies so the securimage server rejects it. Only `page.context.request` shares cookies.
- `wait_for(state="attached")` is correct; `wait_for(state="visible")` will always time out.

### Filling / Clicking CNR Form Fields (confirmed 2026-03-22)
- ALL CNR form elements (`#cino`, `#fcaptcha_code`, `#searchbtn`) have hidden ancestors.
- Playwright's `click()`, `fill()`, `scroll_into_view_if_needed()` ALL fail — even with `force=True`.
- **Fix:** Pure `page.evaluate()` for every CNR interaction:
  - Fill `#cino`: `el.value = cnr; el.dispatchEvent(new Event('input/change'))`
  - Fill `#fcaptcha_code`: same pattern
  - Submit: call `funViewCinoHistory()` directly (the button's `onclick` function)

### Advocate Search Navigation
- Click `#leftPaneMenuCS` to open Case Status panel.
- Select state → wait for `#sess_dist_code` options > 1.
- Select district → wait for `#court_complex_code` options > 1.
- Select court complex → `wait_for_load_state('networkidle')` (AJAX-heavy).
- Click `#advname-tabMenu`.
- Captcha: `div#div_captcha_adv` → `img#captcha_image`, input `#adv_captcha_code`.

### CNR vs Advocate Detection at Runtime
- `page._mamla_is_cnr` flag set in `navigate()` — only reliable signal.
- URL changes after AJAX submit — do not use URL inspection.
- DOM probing (`offsetParent`, `querySelector('#cino')`) — unreliable, both forms share element IDs.

---

## FAILED APPROACHES (never try these again)

| Date | What was tried | Why it failed |
|---|---|---|
| 2026-03-21 | `wait_for(state="visible")` on `div_captcha_cnr img` | Element has hidden ancestor; `visible` check always timed out (logged `25 × resolved to hidden`) |
| 2026-03-21 | Navigate to `?p=cnr_status/searchByCNR/` | AJAX endpoint only — blank page, no form, no `div_captcha_cnr` in DOM |
| 2026-03-21 | Navigate to `?p=home/` | No form rendered there either |
| 2026-03-21 | Click `#leftPaneMenuCS` before CNR form setup | Opens advocate panel, completely replaces CNR form; `div_captcha_cnr` disappears |
| 2026-03-21 | Detect CNR vs advocate via `querySelector('#cino') !== null` | `#cino` exists in DOM on both tabs (just hidden); always returned true |
| 2026-03-21 | Detect CNR via `div_captcha_cnr.offsetParent !== null` | Both tabs render in same DOM; `offsetParent` unreliable during AJAX transitions |
| 2026-03-22 | `scroll_into_view_if_needed()` on `input#fcaptcha_code` | Element in DOM but has hidden ancestor; scroll check hangs for 30s then times out |
| 2026-03-22 | `fill_input` with `wait_for(state="visible")` on captcha input | Same hidden-ancestor problem; never becomes visible |
| 2026-03-22 | `page.request.get(captcha_src_url)` | `page.request` is a global unauthenticated context — no cookies, server rejects; always returns non-ok. Use `page.context.request.get()` instead |

---

## SIDEBAND PATTERN (LangGraph)
LangGraph shallow-copies `config["configurable"]` per node call. Direct key assignments
like `cfg["scraper"] = ...` are lost in the next node.
**Fix:** Single `sideband = {}` dict passed as `config["configurable"]["sideband"]`.
Mutations inside any node (`sb["scraper"] = ...`) are visible to all nodes because the
dict object reference survives the shallow copy.

---

*Update this file whenever a new confirmed path or failed attempt is found.*
