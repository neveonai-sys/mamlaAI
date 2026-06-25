# 13 — Feature Charges by Plan

> **Reference doc.** Reflects `Legalv1/core/entitlements.py` `PLAN_FEATURES` as of 2026-04-19.
> Update this whenever `PLAN_FEATURES` changes.

---

## eCourts Implementation Note

Only **`ecourt_scrapped` v2** (FastAPI-based scraper proxy at `ECOURTS_SCRAPER_BASE_URL`) is active in production.

| App | Status | Notes |
|---|---|---|
| `ecourt_scrapped` | ✅ **ACTIVE** | FastAPI scraper proxy — all eCourts traffic goes here |
| `ecourts_scraper` | ⛔ DORMANT | Old Python scraper — disabled due to CAPTCHA issues |
| `ecourts_api` | ⛔ DEPRECATED | Partner API reference — kept for code history only, not in runtime |

eCourts features (`ecourts_case_lookup`, `ecourts_order_download`) cost **compute only** (CAPTCHA solving in the FastAPI layer). There are no per-call third-party charges, so quotas are intentionally generous.

---

## User Type Feature Separation

Plans are split across two user types. Certain features are **hard-blocked** on Nagrik (citizen) plans because they are only useful to lawyers:

| Feature | Vakil / Firm plans | Nagrik plans |
|---|---|---|
| Legal Chat | ✅ Available | ✅ Available |
| Doc Analysis | ✅ Available | ✅ Available |
| AI Draft Generation | ✅ Available | ✅ Available (limited quota) |
| eCourts CNR Lookup | ✅ Available | ✅ Available (limited quota) |
| eCourts Order Download | ✅ Available | ✅ Basic+ only (3/month); Free = blocked |
| **Drafting Actions** | ✅ Available | ❌ Hard-blocked (lawyer workflow) |
| **AI Suggestions** | ✅ Available | ❌ Hard-blocked (lawyer drafting tool) |
| **Case Companion** | ✅ Available | ❌ Hard-blocked (case-registry/hearing workflow) |

---

## How Charging Works

Every AI action goes through two functions in `core/entitlements.py`:

1. **`authorize_feature_use(user, feature_code)`** — checks if the action is allowed. Returns `charge_source: 'included'` (from plan quota) or `charge_source: 'wallet'` (from credits).
2. **`consume_feature_use(user, feature_code, decision)`** — actually records the use and optionally deducts wallet credits.

### Charge priority order
```
1. Included quota (included_limit)  →  free, from plan
2. Wallet credits (overage_credit_cost × 1 use)  →  deducted from balance
3. Hard block  →  rejected (403/429), no charge
```

If `hard_block: true` AND `included_limit: 0`, the feature is **completely unavailable** on that plan — wallet credits cannot unlock it.

### Dev mode
When `DEBUG=True`, **all calls to `authorize_feature_use` and `consume_feature_use` are bypassed**. No quota is checked, no counter is incremented. This applies to all users.

### Admin / Internal emails
Emails in `BRAIN_ADMIN_EMAILS` env var resolve to the `internal` plan on every request. All features are unlimited (1 000 000 cap), overage cost = 0.

---

## Feature Codes & Overage Costs

| Feature code | Human label | Wallet credits deducted per extra use |
|---|---|:---:|
| `general_legal_chat` | Legal Chat | 1 |
| `brain_doc_analysis` | Document Analysis | 2 |
| `brain_drafting_actions` | Drafting Actions | 2 |
| `ai_suggestions` | AI Suggestions | 1 |
| `ai_draft_generation` | AI Draft Generation | 4 |
| `case_companion` | Case Companion | 5 |
| `ecourts_case_lookup` | eCourts CNR / Case Lookup | 1 |
| `ecourts_order_download` | eCourts Order PDF Download | 3 |

Overage only kicks in when the plan's `included_limit` is exhausted **and** `hard_block: false`. If `hard_block: true`, wallet credits cannot substitute.

---

## Plan Quotas — Included Limits per Month

### Free Trial (30 days — expires by time OR by credits, whichever first)

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 24 | No |
| Doc Analysis | 8 | No |
| Drafting Actions | 12 | No |
| AI Suggestions | **5** | No |
| AI Draft Generation | 20 | No |
| Case Companion | 2 | No |
| eCourts CNR Lookup | **50** | No |
| eCourts Order Download | **5** | No |

> Trial wallet top-up: allowed. Overage credits can be purchased and used before the trial ends.
> After trial expires: plan becomes `locked`. Wallet credits still work as soft grace for features with `hard_block: false`.

---

### Nagrik Free (citizen — trial-style 30-day expiry)

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 5 | No |
| Doc Analysis | 2 | No |
| Drafting Actions | 0 | **Yes** (lawyer-only) |
| AI Suggestions | 0 | **Yes** (lawyer-only) |
| AI Draft Generation | 1 | No |
| Case Companion | 0 | **Yes** (lawyer-only) |
| eCourts CNR Lookup | **10** | No |
| eCourts Order Download | 0 | **Yes** |

---

### Nagrik Basic ₹79/month

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 30 | No |
| Doc Analysis | 8 | No |
| Drafting Actions | 0 | **Yes** (lawyer-only) |
| AI Suggestions | 0 | **Yes** (lawyer-only) |
| AI Draft Generation | 5 | No |
| Case Companion | 0 | **Yes** (lawyer-only) |
| eCourts CNR Lookup | **30** | No |
| eCourts Order Download | **3** | No |

---

### Vakil Starter ₹299/month

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 50 | No |
| Doc Analysis | 15 | No |
| Drafting Actions | 20 | No |
| AI Suggestions | **10** | No |
| AI Draft Generation | 30 | No |
| Case Companion | 3 | No |
| eCourts CNR Lookup | **60** | No |
| eCourts Order Download | **15** | No |

---

### Vakil Pro ₹699/month

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 150 | No |
| Doc Analysis | 40 | No |
| Drafting Actions | 60 | No |
| AI Suggestions | **25** | No |
| AI Draft Generation | 70 | No |
| Case Companion | 10 | No |
| eCourts CNR Lookup | ∞ Unlimited | No |
| eCourts Order Download | **50** | No |

---

### Vakil Power ₹1,299/month

| Feature | Included | Hard block? |
|---|:---:|:---:|
| Legal Chat | 400 | No |
| Doc Analysis | 100 | No |
| Drafting Actions | 150 | No |
| AI Suggestions | **75** | No |
| AI Draft Generation | 150 | No |
| Case Companion | 30 | No |
| eCourts CNR Lookup | ∞ Unlimited | No |
| eCourts Order Download | **150** | No |

---

### Firm Basic ₹1,999/month (up to 3 seats — Vakil Pro quotas per seat)

Same per-seat quotas as Vakil Pro (AI Suggestions: 25, eCourts Order Download: 50). Shared wallet: ₹500.

---

### Firm Pro ₹4,499/month (up to 8 seats — Vakil Power quotas per seat)

Same per-seat quotas as Vakil Power (AI Suggestions: 75, eCourts Order Download: 150). Shared wallet: ₹2,000.

---

### Pro (legacy plan code — kept for backward compatibility)

| Feature | Included |
|---|:---:|
| Legal Chat | 120 |
| Doc Analysis | 30 |
| Drafting Actions | 40 |
| AI Suggestions | **20** |
| AI Draft Generation | 60 |
| Case Companion | 8 |
| eCourts CNR Lookup | ∞ Unlimited |
| eCourts Order Download | **40** |

---

### Enterprise / Internal (∞ Unlimited)

All features: `included_limit: 1 000 000`, `overage_credit_cost: 0`, `hard_block: false`.
Internal = admin emails in `BRAIN_ADMIN_EMAILS` env var. Enterprise = manually assigned via MongoDB.

---

### Locked (trial expired, no active plan)

| Feature | Included | Wallet fallback? |
|---|:---:|:---:|
| All features | 0 | Yes (soft grace via wallet) |

Wallet credits still work on `locked` — user can top up and pay per-use until they upgrade. No feature has `hard_block: true` in the `locked` plan itself, so wallet is the only recourse.

---

## Wallet Credit Packs

| Pack | Price | Credits | Per-credit |
|---|---|:---:|:---:|
| Mini | ₹99 | 60 | ₹1.65 |
| Regular | ₹199 | 150 | ₹1.33 |
| Plus | ₹499 | 450 | ₹1.11 |
| Bulk | ₹999 | 1,000 | ₹1.00 |

Auto-top-up: user sets a balance threshold, gateway charges automatically when balance drops below it.

---

## Quick Reference: "Can I use this feature?"

```
User calls a feature
│
├─ DEBUG=True?  →  ✅ Always allowed (dev mode, no tracking)
│
├─ is_internal_user? (email in BRAIN_ADMIN_EMAILS, admin flag, or role)
│      →  ✅ Always allowed (plan_code auto-set to 'internal')
│
├─ launch_access blocks?  →  ❌ 403 launch_restricted
│
├─ feature not in plan?  →  ❌ 403 feature_not_in_plan
│
├─ remaining_included > 0  →  ✅ Charge from included quota
│
├─ hard_block = true  →  ❌ 403 feature_not_in_plan (wallet cannot help)
│
├─ wallet_balance >= overage_credit_cost  →  ✅ Charge from wallet
│
└─ else  →  ❌ 429 included_quota_exhausted_upgrade_required
```
