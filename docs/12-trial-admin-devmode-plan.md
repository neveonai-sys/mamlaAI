# 12 — Trial System, Admin Emails, Dev Mode & Pricing Fixes

> **Status:** PLANNING — Approved. Ready for implementation.
> Last updated: 2026-04-18

---

## TL;DR

The 30-day Free Trial already exists on the landing page and backend (`trial` plan code). This sprint wires it up correctly end-to-end — reactive UI countdown, credits-exhaustion detection, dev bypass, admin emails via env var, new plan codes (Phase A), and eCourts Basic ₹99→₹299. No payment gateway changes.

---

## Phase 1 — Backend (`entitlements.py` + `settings.py`)

### Step 1 — Add 7 new plan codes to `PLAN_FEATURES`

File: `Legalv1/core/entitlements.py`

| Plan | doc_analysis | legal_chat | drafting_actions | case_companion | ai_suggestions | ai_draft |
|------|:------------:|:----------:|:----------------:|:--------------:|:--------------:|:--------:|
| `vakil_starter` | 15 | 50 | 20 | 3 | 0 | 30 |
| `vakil_pro` | 40 | 150 | 60 | 10 | 20 | 70 |
| `vakil_power` | 100 | 400 | 150 | 30 | 60 | 150 |
| `nagrik_free` | 2 | 5 | 0 | 0 | 0 | 1 |
| `nagrik_basic` | 8 | 30 | 0 | 0 | 0 | 5 |
| `firm_basic` | = vakil_pro | = vakil_pro | = vakil_pro | = vakil_pro | = vakil_pro | = vakil_pro |
| `firm_pro` | = vakil_power | = vakil_power | = vakil_power | = vakil_power | = vakil_power | = vakil_power |

`nagrik_free` and `nagrik_basic` have `hard_block: True` on `brain_drafting_actions`, `case_companion`, `ai_suggestions` (Nagrik users cannot access lawyer-only features even via wallet).

### Step 2 — Add `ecourts_case_lookup` + `ecourts_order_download` to `FEATURE_ORDER` and all plans

File: `Legalv1/core/entitlements.py`

| Plan | ecourts_case_lookup | ecourts_order_download |
|------|:-------------------:|:---------------------:|
| `trial` | 30 | 0 (hard_block) |
| `nagrik_free` | 5 | 0 (hard_block) |
| `nagrik_basic` | 15 | 0 (hard_block) |
| `vakil_starter` | 30 | 0 (hard_block) |
| `vakil_pro` | 1 000 000 (∞) | 30 |
| `vakil_power` | 1 000 000 (∞) | 100 |
| `firm_basic` | 1 000 000 (∞) | 30 |
| `firm_pro` | 1 000 000 (∞) | 100 |
| `pro` | 1 000 000 (∞) | 30 |
| `enterprise` / `internal` | 1 000 000 (∞) | 1 000 000 (∞) |
| `locked` | 0 (hard_block) | 0 (hard_block) |

Overage credit costs: `ecourts_case_lookup` = 1 credit, `ecourts_order_download` = 3 credits.

### Step 3 — Update `_effective_plan_code()` for new plan codes

Add a `PAID_PLANS` set at module level:

```python
PAID_PLANS = {
    'pro', 'vakil_starter', 'vakil_pro', 'vakil_power',
    'nagrik_basic', 'firm_basic', 'firm_pro',
}
```

In `_effective_plan_code()`, before the trial check:

```python
if plan_code in PAID_PLANS:
    return plan_code   # paid plans don't expire in Phase A
```

`nagrik_free` still falls through to the trial→locked path (uses same `trial_ends_at` field; 7-day expiry TODO when Nagrik user type is launched).

### Step 4 — Dev mode bypass in `authorize_feature_use()`

After `ensure_user_entitlements()` call, before any quota checks:

```python
if getattr(settings, 'DEBUG', False):
    quota = _feature_payload(document, feature_code, next_cta='continue', message_key='dev_mode_bypass')
    return {
        'allowed': True,
        'charge_source': 'included',
        'wallet_credits_charged': 0,
        'quota': quota,
    }
```

This means nobody is ever blocked in development (`DEBUG=True`). Does not affect production (`DEBUG=False`).

### Step 5 — Add `trial.days_remaining` to `get_entitlement_summary()`

In the `trial` dict:

```python
'days_remaining': max((trial_ends_at - current).days, 0)
    if (trial_ends_at and trial_ends_at > current) else 0,
```

### Step 6 — Add `BRAIN_ADMIN_EMAILS` to `settings.py`

File: `Legalv1/Legalv1/settings.py`

```python
BRAIN_ADMIN_EMAILS = os.getenv('BRAIN_ADMIN_EMAILS', '')
```

The `is_internal_user()` function in `core/entitlements.py` already parses this as a comma-separated list — it just needs the settings attribute to exist.

**Local `.env` file** (not committed — add manually):

```
BRAIN_ADMIN_EMAILS=mems650@gmail.com,robin.mondal@gmail.com,neveon.ai@gmail.com
```

These three addresses will always resolve to the `internal` plan (unlimited quotas, no blocks).

---

## Phase 2 — Frontend: Reactive Trial UI

### Step 7 — `features/entitlementsSlice.js`

- Add `daysRemaining: 0` to `trial` in `initialState`
- In `setEntitlements` reducer, map `payload.trial.days_remaining` → `state.trial.daysRemaining`
- In `updateFeatureQuota` reducer, sync `daysRemaining` from `payload.trial.days_remaining` when present

### Step 8 — `components/dashboard/Dashboard.jsx` — trial banner

The existing banner block checks `trial?.active`. Extend it:

| Condition | Banner message |
|-----------|---------------|
| `trial.active && daysRemaining > 3` | "Trial active — X days remaining" |
| `trial.active && daysRemaining <= 3` | "Trial ending soon — X days left" (amber) |
| `!trial.active && planCode === 'locked'` | "Trial expired" (red) + "Upgrade Now" CTA |
| Any plan, `allFeaturesExhausted` | "Credits used up for this cycle — top up or upgrade" |

Derive `allFeaturesExhausted` client-side:

```js
const allFeaturesExhausted = Object.values(features).every(
  (f) => (f.remaining_included ?? 1) === 0
);
```

CTA button logic: `trial.active ? 'Review Trial Limits' : planCode === 'locked' ? 'Upgrade Now' : 'Review Plan Limits'`

### Step 9 — `components/layout/TopBar.jsx` — plan label

Update `planLabel`:

```js
const planLabel = trial?.active
  ? `Trial (${trial.daysRemaining ?? ''}d)`
  : (planCode || 'Plan').replace(/_/g, ' ');
```

Add urgency class when `trial.active && (trial.daysRemaining ?? 99) <= 3`: apply `text-amber-600` to the plan label pill.

---

## Phase 3 — Pricing & Docs

### Step 10 — `components/landing/LandingPage.jsx` — Free Trial card

Add to the `items` array for the `Free Trial` plan:
- `'2 Case Companion sessions'`
- `'eCourts CNR Lookup (30/month)'` — already present as `'CNR Lookup (30/month)'`, rename for clarity

No changes to paid plan cards.

### Step 11 — `docs/09-pricing-and-billing-plan.md`

- Update Phase A status: "In Progress"
- Add trial quota breakdown table (matching actual `PLAN_FEATURES['trial']`)
- Update eCourts Basic add-on: ₹99 → ₹299
- Add admin emails env var config note under Phase A
- Add dev-mode bypass note under Phase A
- Reference `BRAIN_ADMIN_EMAILS` in env vars section

---

## Relevant Files

| File | Change |
|------|--------|
| `Legalv1/core/entitlements.py` | Steps 1–5 |
| `Legalv1/Legalv1/settings.py` | Step 6 |
| `frontend/src/features/entitlementsSlice.js` | Step 7 |
| `frontend/src/components/dashboard/Dashboard.jsx` | Step 8 |
| `frontend/src/components/layout/TopBar.jsx` | Step 9 |
| `frontend/src/components/landing/LandingPage.jsx` | Step 10 |
| `docs/09-pricing-and-billing-plan.md` | Step 11 |

---

## Verification Checklist

1. **New user** → `GET /api/users/entitlements/summary/` → `trial.active=true`, `trial.days_remaining=30`, `trial.ends_at` = signup date + 30 days
2. **Admin email** → Login as `mems650@gmail.com` → `plan_code: "internal"` (after adding env var to `.env`)
3. **Dev bypass** → `DEBUG=True`, any feature call on a quota-exhausted user → `allowed: true`
4. **Credits exhausted** → In MongoDB, set `used_count = included_limit` for all features on a trial user → Dashboard shows "Credits used up" banner
5. **Time expired** → In MongoDB, set `trial_ends_at` to a past date → Dashboard shows "Trial expired" + "Upgrade Now" CTA
6. **Paid plan** → In MongoDB, set `plan_code: 'vakil_pro'` → `_effective_plan_code` returns `'vakil_pro'`, summary shows 150 chat quota
7. **eCourts order download blocked for Starter** → `authorize_feature_use(user, 'ecourts_order_download')` for a `vakil_starter` user → `allowed: false`, `next_cta: 'upgrade_plan'`

---

## Scope Boundaries

| In Scope | Out of Scope |
|----------|-------------|
| Trial enforcement + reactive countdown UI | Payment gateway (Razorpay) |
| Admin emails via env var | `billing` Django app |
| Dev-mode quota bypass | Wallet top-up UI widget |
| New plan codes — Phase A definitions only | eCourts view enforcement hookup |
| eCourts features in `FEATURE_ORDER` | UpgradeModal component |
| Landing page trial card fix | Firm admin seat-management UI |
| eCourts Basic add-on price fix | Annual billing cycles |

---

## Notes

- `nagrik_free` uses the same 30-day `trial_ends_at` field for Phase A simplicity. A proper 7-day cap is a TODO for when the Nagrik user type is publicly launched.
- Admin emails are **never hardcoded** — env var only. Not committed to source control.
- `PAID_PLANS` set gates the new plan codes from expiry logic. In Phase B (billing backend), subscription status from the `subscriptions` collection will replace this set.
- Wallet top-up is permitted during the free trial period (user's preference). Overage credits can be purchased and used before the trial ends.
