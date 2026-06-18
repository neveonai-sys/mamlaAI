# 09 — Pricing & Billing Plan

> **Status:** Phase A + Phase A.5 COMPLETE. Phase B (Razorpay gateway) is the next sprint.
> Last updated: 2026-06-09

---

## TL;DR

Three user types × tiered plans, priced for Indian small-town affordability. eCourts deep scraping is a separate paid add-on. A new `billing` Django app extends the existing `entitlements.py` framework. The payment gateway is wired in a separate sprint once confirmed.

**Current state (2026-06-09):** No payment gateway is live yet. Users can see their wallet balance in INR equivalent, and admins can manually credit wallets via API or management command when payment arrives via UPI/bank transfer. Full Razorpay integration is Phase B.

---

## 1. Three User Types

| Type | Who | What they need |
|------|-----|----------------|
| **Nagrik (Citizen)** | Litigants, common people | Legal Q&A, read their documents, simple drafts, check case status |
| **Vakil (Solo Lawyer)** | District/HC lawyers | Full platform — drafting, case registry, eCourts, calendar, agents |
| **Nyaya Firm** | 2–10 lawyer offices | Shared case pool, multi-seat, admin dashboard |

Citizens can sign up directly **or** be invited by a lawyer (both flows supported).

**Nagrik does NOT get:** case registry, client management, hearing agents, cause list, eCourts deep scraping, calendar hearing management.

---

## 2. Pricing Plans

### 2.1 Nagrik (Citizen)

| Plan | Price | Legal Chat | Doc Analysis | AI Drafts | CNR Lookup |
|------|-------|:----------:|:------------:|:---------:|:----------:|
| **Nagrik Free** (7-day trial) | ₹0 | 5 | 2 | 1 | 5 |
| **Nagrik Basic** | ₹79/month | 30 | 8 | 5 | 15 |

### 2.2 Vakil (Solo Lawyer)

| Plan | Price | Legal Chat | Doc Analysis | AI Drafts | Drafting Actions | Case Companion |
|------|-------|:----------:|:------------:|:---------:|:----------------:|:--------------:|
| **Free Trial** (30 days) | ₹0 | 24 | 8 | 20 | 12 | 2 |
| **Vakil Starter** | ₹299/month | 50 | 15 | 30 | 20 | 3 |
| **Vakil Pro** | ₹699/month | 150 | 40 | 70 | 60 | 10 |
| **Vakil Power** | ₹1,299/month | 400 | 100 | 150 | 150 | 30 |

### 2.3 Nyaya Firm (Law Firm)

| Plan | Price | Seats | Per-seat quotas | Shared wallet |
|------|-------|:-----:|:---------------:|:-------------:|
| **Seat-based** | ₹499/seat/month (min 2) | Up to 10 | = Vakil Pro | ₹500 |
| **Firm Basic** | ₹1,999/month flat | Up to 3 | = Vakil Pro | ₹500 |
| **Firm Pro** | ₹4,499/month flat | Up to 8 | = Vakil Power | ₹2,000 |
| **Enterprise** | Custom | Unlimited | Custom | Custom |

Both seat-based and flat org billing offered. Firm plans include an admin dashboard.

---

## 3. Feature Gate Map (Vakil Plans)

| Feature | Starter ₹299 | Pro ₹699 | Power ₹1,299 |
|---------|:------------:|:--------:|:------------:|
| General Legal Chat | 50/month | 150/month | 400/month |
| TalkDoc — Document Q&A | 15/month | 40/month | 100/month |
| AI Draft Generation | 30/month | 70/month | 150/month |
| Drafting Actions (edits, AI suggestions) | 20/month | 60/month | 150/month |
| Case Companion (Mamla Brain) | 3/month | 10/month | 30/month |
| AI Suggestions | 0 | 20/month | 60/month |
| Case Registry (active cases) | 20 | 100 | Unlimited |
| Calendar (hearings, events) | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited |
| Client Onboarding | 5/month | Unlimited | Unlimited |
| eCourts CNR Lookup | 30/month | Unlimited | Unlimited |
| eCourts Advocate / Party Search | ❌ | ✅ | ✅ |
| eCourts Order PDF Download | ❌ | 30/month | 100/month |
| eCourts Cause List | ❌ | ✅ | ✅ |
| AI Hearing Prep Agent | ❌ | 15/month | 50/month |
| AI Post-Hearing / Closure Agents | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ❌ | ✅ |
| Wallet Overage (top-up credits) | ✅ | ✅ | ✅ |

---

## 4. eCourts Scraping Add-ons

For **Vakil Starter** users who need eCourts depth without upgrading their main plan.
Pro and Power already include eCourts — these add-ons are only meaningful for Starter.

| Add-on | Price | Includes |
|--------|-------|---------|
| **eCourts Basic** | ₹299/month | +20 order downloads, basic advocate search |
| **eCourts Pro** | ₹249/month | +100 order downloads, full advocate search, cause list |

Add-ons renew monthly independently and can be cancelled anytime.

---

## 5. Credit / Wallet Top-up Packs

Pre-purchase credits to cover feature overage mid-cycle. Auto-top-up supported: user sets balance threshold.

| Pack | Price | Credits | Per-credit |
|------|-------|:-------:|:----------:|
| Mini | ₹99 | 60 | ₹1.65 |
| Regular | ₹199 | 150 | ₹1.33 |
| Plus | ₹499 | 450 | ₹1.11 |
| Bulk | ₹999 | 1,000 | ₹1.00 |

**Overage cost per feature use** (from `core/entitlements.py`):

| Feature | Credits deducted |
|---------|:----------------:|
| General legal chat | 1 |
| Document analysis | 2 |
| Drafting action / suggestion | 2 |
| AI Draft generation | 4 |
| Case Companion session | 5 |
| eCourts CNR / case lookup | 1 |
| eCourts order PDF download | 3 |

---

## 6. Extension & Upgrade Flows

1. **Mid-cycle upgrade** — prorated charge for remaining days; new plan activates immediately
2. **Auto-renewal** — gateway subscription webhook triggers quota reset + plan extension on billing anchor date
3. **Wallet auto-top-up** — optional threshold: "top up ₹199 when balance drops below 20 credits"
4. **Grace period** — 7 days after plan expiry: `locked` plan code (user can view all data, no AI actions)
5. **Downgrade** — takes effect at end of current billing cycle; current plan stays active until then
6. **eCourts add-on** — purchased and renewed separately from main plan subscription

---

## 7. Affordability Check (Why These Prices Work)

| Income bracket | Lawyer type | Recommended plan | % of monthly income |
|----------------|-------------|:----------------:|:-------------------:|
| ₹15K–20K/month | Junior district court lawyer | Vakil Starter ₹299 | ~1.5–2% ✅ |
| ₹40K–60K/month | Mid-level court lawyer | Vakil Pro ₹699 | ~1.2–1.75% ✅ |
| ₹80K–1.5L/month | Senior / busy lawyer | Vakil Power ₹1,299 | ~0.9–1.6% ✅ |
| ₹25K avg income | Citizen litigant | Nagrik Basic ₹79 | ~0.3% ✅ |

**Platform margin at these prices:** ~40–50% over LLM + infra costs, with headroom to absorb Razorpay's ~2.36% effective GST-inclusive transaction fee.

---

## 8. Implementation Phases

### Phase A — Plan Definitions ✅ DONE (2026-04-18)

**`Legalv1/core/entitlements.py`** — implemented:
- Added 7 new plan codes to `PLAN_FEATURES`: `nagrik_free`, `nagrik_basic`, `vakil_starter`, `vakil_pro`, `vakil_power`, `firm_basic`, `firm_pro`
- Added 2 new feature codes to `FEATURE_ORDER`: `ecourts_case_lookup`, `ecourts_order_download` (with per-plan quotas for all plans)
- Added `PAID_PLANS` set — paid plan codes never hit trial→locked expiry check in Phase A
- Updated `_effective_plan_code()` to handle all new plan codes via `PAID_PLANS`
- Added **dev-mode bypass** in `authorize_feature_use()`: when `DEBUG=True`, all users are always allowed — no blocks in local development
- Added `trial.days_remaining` to `get_entitlement_summary()` response

**`Legalv1/Legalv1/settings.py`** — implemented:
- Added `BRAIN_ADMIN_EMAILS = os.getenv('BRAIN_ADMIN_EMAILS', '')` — resolves to `internal` plan (unlimited, no blocks)
- Set in `legalenv.dev` (not committed): `BRAIN_ADMIN_EMAILS=mems650@gmail.com,robin.mondal@gmail.com,neveon.ai@gmail.com`

**Trial plan quotas** (what new users get on signup for 30 days):

| Feature | Included | Hard block when 0? |
|---------|:--------:|:------------------:|
| Doc Analysis | 8 | No (wallet fallback) |
| Legal Chat | 24 | No |
| Drafting Actions | 12 | No |
| Case Companion | 2 | No |
| AI Suggestions | 0 | No |
| AI Draft Generation | 20 | No |
| eCourts CNR Lookup | 30 | No |
| eCourts Order Download | 0 | **Yes** |

Trial expires whichever comes first: **30 days elapsed** OR **wallet exhausted** (wallet top-up allowed during trial). After expiry, plan code becomes `locked` — wallet credits still work as soft grace.

**Deferred to Phase B:**
- Enforce `ecourts_order_download` quota in `ecourts_api/views.py`
- Enforce `ecourts_case_lookup` quota in `ecourts_api/views.py`

### Phase A.5 — Wallet UI & Manual Admin Top-up ✅ DONE (2026-06-09)

Builds the pre-gateway wallet experience: users see their credit balance in INR equivalent, understand the value their trial has delivered, and admins can credit wallets manually. No Razorpay integration needed.

**`Legalv1/core/entitlements.py`** — updated:
- Added `DISPLAY_CREDIT_RATE_INR = 1.33` (Regular pack reference rate, display-only, never stored)
- Added `log_wallet_transaction(user_id, email, type, credits, *, amount_inr, note, added_by)` — writes to `wallet_transactions` collection
- Added `_wallet_tx_collection()` helper
- Extended `get_entitlement_summary()` response:
  - `wallet.inr_equivalent` — `balance × 1.33`, rounded to 2dp
  - `usage_summary.total_credits_consumed` — Σ `used_count × overage_credit_cost` across all features this cycle
  - `usage_summary.trial_value_inr` — same converted to INR; shown as "Your trial delivered ≈ ₹X"
- `consume_feature_use()` now calls `log_wallet_transaction()` on every wallet deduction (type=`deduction`)

**`Legalv1/core/admin_views.py`** — new file:
- `POST /api/admin/wallet/top-up/` — admin-only (checked via `is_internal_user()`), body: `{ target_email, credits, note, amount_inr }`, increments `wallet_credits_balance`, logs top-up transaction

**`Legalv1/core/management/commands/add_wallet_credits.py`** — new management command:
```
python manage.py add_wallet_credits --email user@x.com --credits 150 --note "UPI ref ABC123" --amount-inr 199
```
Use this when a user pays via UPI/bank transfer and you need to credit their wallet without the API.

**`Legalv1/users/supabase_views.py`** — updated:
- Added `GET /api/users/wallet/transactions/?limit=20` — returns user's own transaction history sorted by date desc

**`Legalv1/Legalv1/urls.py`** — updated:
- Wired `api/admin/wallet/top-up/` from `core.admin_views`

**MongoDB — `wallet_transactions` collection** (now live, ahead of Phase B):

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | str | Supabase user ID |
| `email` | str | For human readability in admin queries |
| `type` | str | `top_up` or `deduction` |
| `credits` | int | Credits added or deducted |
| `amount_inr` | float\|null | INR received (top-ups only; null for deductions) |
| `note` | str | UPI ref, bank ref, or feature code for deductions |
| `added_by` | str | Admin email, `management_command`, or `system` |
| `created_at` | datetime | UTC |

**Frontend:**

| File | Change |
|------|--------|
| `features/entitlementsSlice.js` | Added `wallet.inrEquivalent`, `usageSummary.{totalCreditsConsumed, trialValueInr}` to state and all reducers |
| `components/billing/WalletPage.jsx` | New page at `/wallet`: balance card with ₹ display, trial value banner, per-feature usage table with INR cost, UPI top-up instructions, transaction history |
| `components/dashboard/Dashboard.jsx` | Wallet MetricCard is now a clickable button → `/wallet`; shows `≈ ₹{inrEquivalent}` and trial value sub-stats; "Top Up Credits" CTA renamed to "Add Credits" and navigates to `/wallet` |
| `AppContent.js` | Added `/wallet` protected route |

**Manual top-up workflow (pre-gateway):**
1. User contacts team and sends payment via UPI/bank transfer
2. Admin runs: `python manage.py add_wallet_credits --email X --credits 150 --note "UPI ref" --amount-inr 199`
   OR calls `POST /api/admin/wallet/top-up/` with admin JWT
3. User's wallet balance updates immediately; transaction visible in `/wallet` page history
4. User can now use overage features against the new balance

### Phase B — Billing Backend

New Django app `Legalv1/billing/`:

```
billing/
├── __init__.py
├── urls.py
├── views.py          # order creation, webhook, subscription mgmt
├── constants.py      # plan codes, INR prices, pack sizes
└── services/
    ├── payment_client.py   # gateway-agnostic interface (Razorpay adapter first)
    ├── subscription.py     # create/cancel/upgrade subscription logic
    └── wallet.py           # top-up, deduct, transaction log
```

Register in `Legalv1/Legalv1/settings.py` (`INSTALLED_APPS`) and `Legalv1/Legalv1/urls.py`.

**New MongoDB collections** (✅ = already created in Phase A.5):

| Collection | Status | Purpose |
|-----------|--------|---------|
| `subscriptions` | Phase B | user_id → plan_code, amount, start/end, gateway sub ID, status |
| `payment_orders` | Phase B | each gateway order created (for signature verification traceability) |
| `wallet_transactions` | ✅ Live | credit additions and deductions with reason + timestamp |
| `ecourts_addons` | Phase B | user_id → addon_code, activated_at, renews_at, status |

**New API endpoints under `/api/billing/`:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `plans/` | No auth | List all plans, prices, features (used by public pricing page) |
| POST | `create-order/` | Supabase | Create payment gateway order for plan or wallet top-up |
| POST | `verify-payment/` | Supabase | Verify gateway signature; activate plan or add credits |
| POST | `webhook/` | HMAC sig | Gateway webhook (subscription renewal, payment failure) — CSRF exempt |
| GET | `subscription/` | Supabase | Current plan, next billing date, wallet balance |
| POST | `cancel-subscription/` | Supabase | Schedule cancellation at cycle end |
| POST | `upgrade-plan/` | Supabase | Immediate plan upgrade + prorated charge |
| POST | `add-ecourts-addon/` | Supabase | Purchase eCourts scraping add-on |
| GET | `wallet/` | Supabase | Wallet balance + transaction history |
| POST | `wallet/top-up/` | Supabase | Create wallet top-up order |

Also extend `GET /api/users/entitlements/summary/` to include:
- `subscription` block: `{plan_code, display_name, renewal_date, status}`
- `ecourts_addon` block: `{active, addon_code, renews_at}`

### Phase C — Frontend Billing UI

Files in `mamlaAI_ground_zero/frontend/src/` (✅ = already built in Phase A.5):

| File | Status | Purpose |
|------|--------|---------|
| `components/billing/WalletPage.jsx` | ✅ Live | Balance card with ₹ equivalent, trial value banner, per-feature usage table, UPI top-up instructions, transaction history |
| `components/billing/PricingPage.jsx` | Phase C | Public pricing table (Nagrik / Vakil / Firm tabs) |
| `components/billing/BillingSettings.jsx` | Phase C | Dashboard billing tab: current plan, upgrade, cancel |
| `components/billing/UpgradeModal.jsx` | Phase C | Triggered on quota exhaustion from any feature page |
| `components/billing/PlanBadge.jsx` | Phase C | Small badge in Navbar/profile showing current plan |
| `features/billingSlice.js` | Phase C | Redux slice for Razorpay order flow and subscription state |

Route additions in `AppContent.js`:
- `/wallet` — ✅ Live, protected (Supabase auth) — wallet balance + usage + transaction history
- `/pricing` — Phase C, public, no auth required
- `/settings/billing` — Phase C, protected (Supabase auth)

---

## 9. Out of Scope (This Sprint)

- Payment gateway SDK wiring (gateway finalized separately; Razorpay adapter is first target)
- Annual / discounted billing cycles
- Invoice PDF generation
- GST / TDS computation
- WhatsApp billing notifications
- Firm admin seat-management UI (backend supports firms; admin UI deferred)
