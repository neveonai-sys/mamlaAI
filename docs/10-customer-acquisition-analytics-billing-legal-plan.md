# Customer Acquisition, Analytics, Billing & Legal Compliance Plan

## Objective

Create the missing product telemetry, usage accounting, billing, consent, and privacy controls needed to measure customer traction, token cost, profitability, and legal compliance.

---

## What this plan covers

- Product usage tracking and analytics
- Token-level cost accounting and profitability metrics
- Subscription billing integration (Razorpay first)
- Cookie consent and Terms/Privacy acceptance
- Data export/delete privacy endpoints
- Owner dashboards and operational alerts
- Legal document versioning, consent audit, and compliance controls

---

## High-level requirements

1. Track who uses which feature, when, and how much token cost each use consumes.
2. Record token usage, estimated provider cost, and link costs to users/usage features.
3. Build billing infrastructure so revenue is tracked and profitability can be calculated.
4. Add cookie consent and explicit T&C/Privacy acceptance flows.
5. Provide privacy endpoints for data export and deletion.
6. Expose owner-facing dashboards for active users, DAU/MAU, token spend, revenue, and P&L.
7. Include an operational monitoring and alerting layer for spikes, failed payments, and consent gaps.

---

## Analytics architecture — two layers

These two layers are **intentionally separate** and complement each other:

| Layer | Tool | What it tracks | Where stored |
|---|---|---|---|
| UX journey | PostHog (EU) | signups, logins, feature opens, page views, consent | PostHog cloud |
| Cost accounting | MongoDB `usage_events` | token counts, model, estimated provider cost per AI call | Self-hosted MongoDB |

PostHog tracks the user journey so you can answer "which features do users use, where do they drop off."
MongoDB tracks the economics so you can answer "what did each user cost us."

---

## Current gaps discovered

- ~~No cookie consent banner or consent categories~~ — done
- ~~Signup T&C/Privacy links broken~~ — done
- No billing/payment backend or checkout integration
- No privacy export/delete APIs
- Quota checks not fully tied to token consumption
- No owner-level reporting for revenue, cost, or profitability

---

## Current progress

### Sprint 1 — complete

Cookie consent banner, consent categories, signup T&C checkbox fix, backend consent audit persistence.

### Sprint 2 — complete

- Backend: request telemetry middleware, usage analytics service, backend aggregation endpoints — all done
- Frontend: PostHog installed and wired; analytics wrapper migrated from Mixpanel to PostHog

**PostHog live dashboards (EU region):**
- [Main dashboard](https://eu.posthog.com/project/194847/dashboard/728502)
- [New signups](https://eu.posthog.com/project/194847/insights/Y6ugN6b7)
- [Signup → login funnel](https://eu.posthog.com/project/194847/insights/nbnLTqqD)
- [Case & draft creation trend](https://eu.posthog.com/project/194847/insights/FMvoUXZR)
- [AI drafting engagement](https://eu.posthog.com/project/194847/insights/B7LJYRXH)
- [eCourts search activity](https://eu.posthog.com/project/194847/insights/pLpMDkY8)

**Events tracked in frontend:**
- `user_signed_up` — Signup.jsx
- `user_logged_in` — Login.jsx
- `case_created`, `case_updated` — CaseRegistry.jsx
- `draft_created`, `draft_saved`, `ai_suggestion_requested` — DraftingWorkspace.jsx
- `guided_draft_started` — GuidedDraftingPage.jsx
- `document_uploaded` — DocumentWorkspace.jsx
- `ecourts_case_searched`, `cause_list_searched`, `hc_case_searched` — eCourts components
- `feedback_submitted` — Feedback.jsx
- `$pageview` — AppContent.js (every route change)
- `consent_changed` — CookieConsentBanner.jsx

**PostHog config (performance-first):**
- `autocapture: false` — no mouse/scroll/hover noise
- `capture_pageview: false` — manual page views only
- `disable_session_recording: true` — enable when traffic justifies cost

**Remaining Sprint 2 work:**
- Run `python manage.py initialize_analytics_indexes` to create MongoDB indexes
- Wire `record_usage_event()` into AI endpoints (ai_draft, talkdoc, mamla_brain) with prompt/completion token counts and model name

---

## Sprint backlog

### Sprint 0 — Prep & Safety (done)

### Sprint 1 — Instrumentation & Consent UX (done)

### Sprint 2 — Server Telemetry & Usage Events (done except MongoDB index init and AI endpoint wiring)

### Sprint 3 — Cost Accounting, Quota Wiring & Alerts (2 weeks)

- Add configurable model pricing and cost calculator.
- Save `estimated_provider_cost` per usage event.
- Wire entitlement authorization to real token costs.
- Implement soft warning at 80% and hard block at 100% usage thresholds.
- Add overage/billing alerts.
- Output: true metering, quota enforcement, and notifications.

### Sprint 4 — Billing & Checkout (2 weeks)

- Build `billing` Django app with models: `Subscription`, `Invoice`, `PaymentOrder`, `PaymentTransaction`.
- Integrate Razorpay payment gateway with order creation and webhook handling.
- Add subscription management UI in frontend.
- Link payments to `daily_pnl` aggregation.
- Output: working sandbox checkout and payment lifecycle.

### Sprint 5 — Dashboards, Reporting & Privacy APIs (done)

- ~~Build owner dashboard endpoints and UI: active users, feature adoption, token costs, revenue, daily P&L.~~ — done (`analytics/views.py` `owner_dashboard`, `OwnerDashboard.jsx`)
- Privacy endpoints: `/api/privacy/export-data` and `/api/privacy/delete-data` — deferred (Sprint 5 tail, no immediate requirement)
- ~~Add legal document versioning and show consent version in user records.~~ — done (`core/legal_versions.py`, `SERVER_AUTHORITATIVE_TYPES`, `GET /api/users/legal-doc-versions/`)
- ~~Add retention job for raw usage data.~~ — done (`core/management/commands/purge_old_usage_events.py`, dry-run by default, `--execute --days 730`)
- ~~Frontend: record T&C + Privacy consent on signup~~ — done (`Signup.jsx` posts to `/api/users/consent-events/`)

### Future — Proper `owner` user_type plan (not started)

Currently admin dashboard access is gated by `BRAIN_ADMIN_EMAILS` env var (same list used for quota bypass). This is intentional for the testing phase — any email in that list gets full analytics access without needing a special `user_type`.

When moving to production, replace with Option A:
- Block `user_type: "owner"/"admin"` at the signup endpoint (reject with 400)
- Manually set `user_type: "owner"` in MongoDB for trusted accounts
- Update `_is_owner` in `analytics/views.py` to drop the email-list check
- Update `CaseHub.jsx:isLawyer` to include `owner`/`admin` so case editing works
- Update `Sidebar.jsx` (already handles owner — no change needed)

### Sprint 6 — Hardening, Monitoring & Go-live (done)

- ~~Add audit logs for consent and admin actions.~~ — done (`core/audit_log.py`, `write_audit_log()`, `audit_from_request()`; wired into `delete_user_data`, `analytics_usage_by_user_read`, `owner_dashboard_read`)
- ~~Add alerts for cost spikes.~~ — done (`core/management/commands/check_cost_spikes.py`; compares today vs 7-day rolling avg, configurable `--multiplier`, exits 1 on spike)
- ~~Update model pricing dict.~~ — done (`core/analytics.py`; added `gpt-4o-mini`, `claude-3-5-haiku`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `gemini-1.5-flash`)
- Automated tests for telemetry/billing/privacy workflows — deferred (view-layer tests skipped; pure-unit tests exist in `analytics/tests.py` and `users/tests.py`)

---

## Detailed implementation areas

### 1. Telemetry & analytics

#### Frontend (PostHog)

- PostHog SDK installed via npm (`posthog-js`, `@posthog/react`).
- Initialised in `mamlaAI_ground_zero/frontend/src/index.js` with `PostHogProvider`.
- Wrapper service at `mamlaAI_ground_zero/frontend/src/services/analytics.js` exports: `initializeAnalytics`, `setAnalyticsUser`, `clearAnalyticsUser`, `trackPageView`, `trackFeatureUse`, `trackConsentChange`, `trackCheckout`, `trackError`.
- Env vars: `REACT_APP_POSTHOG_KEY`, `REACT_APP_POSTHOG_HOST` (set in `.env`).
- Track business events only — no `mouse_move`, `scroll`, `hover`, or `keypress`.

#### Backend (MongoDB usage_events)

- `Legalv1/core/telemetry_middleware.py` — attaches `request_id`, `user_id`, `session_id` to every request.
- `Legalv1/core/analytics.py` — `record_usage_event()` and `calculate_estimated_cost()`.
- Expose aggregation endpoints:
  - `/api/analytics/usage/summary`
  - `/api/analytics/usage/by-user`
  - `/api/analytics/usage/by-feature`

### 2. Cost accounting

- Configurable model pricing already embedded in `Legalv1/core/analytics.py`.
- Store `estimated_provider_cost` on every `usage_event`.
- Aggregate daily cost by user, feature, and plan.

### 3. Billing

- Build billing app with collections:
  - `subscriptions`
  - `payment_orders`
  - `payment_transactions`
  - `invoices`
- Integrate Razorpay sandbox.
- Add routes:
  - `/api/billing/create-order`
  - `/api/billing/webhook`
  - `/api/billing/cancel`
  - `/api/billing/invoice/:id`
- Add frontend checkout UI and subscription management screens.

### 4. Consent & legal UX

- Cookie consent banner: `mamlaAI_ground_zero/frontend/src/components/common/CookieConsentBanner.jsx` — done.
- Backend consent audit: `Legalv1/users/supabase_views.py` `POST /api/users/consent-events/` — done.
- Signup T&C checkbox: `mamlaAI_ground_zero/frontend/src/components/auth/Signup.jsx` — done.

### 5. Privacy & data rights

- Implement data export API for user accounts, usage events, payments, and consents.
- Implement delete workflow for user data with admin review if billing/legal hold exists.
- Add retention policy for raw usage data (e.g. 2 years).

### 6. Owner dashboards & monitoring

- Add owner dashboard endpoints and UI.
- Track metrics: active users, DAU/MAU, feature adoption, token consumption, daily provider cost, daily revenue, gross margin / P&L, churn and conversion funnel.
- Add alerts for cost spikes, overage, failed payments, webhook issues.

### 7. Legal & compliance controls

- Version terms and privacy docs.
- Save consent versions in `consent_events`.
- Add grievance officer/contact details.
- Document encryption-at-rest limitations.

---

## File-level implementation guide

### Backend files to create or update

- `Legalv1/core/telemetry_middleware.py` — done
- `Legalv1/core/analytics.py` — done
- `Legalv1/analytics/views.py` — done
- `Legalv1/analytics/urls.py` — done
- `Legalv1/billing/` — new app (Sprint 4)
- `Legalv1/privacy/views.py` — Sprint 5
- `Legalv1/core/entitlements.py` — Sprint 3
- `Legalv1/Legalv1/urls.py` — updated
- `Legalv1/Legalv1/settings.py` — updated
- `Legalv1/core/management/commands/initialize_analytics_indexes.py` — done (run once)

### Frontend files (active frontend: `mamlaAI_ground_zero/frontend/src/`)

- `services/analytics.js` — done (PostHog wrapper)
- `index.js` — done (PostHogProvider)
- `AppContent.js` — done (initializeAnalytics, setAnalyticsUser, trackPageView)
- `components/common/CookieConsentBanner.jsx` — done
- `components/auth/Signup.jsx` — done (user_signed_up event)
- `components/auth/Login.jsx` — done (user_logged_in event)
- `components/cases/CaseRegistry.jsx` — done (case_created, case_updated)
- `components/drafting/DraftingWorkspace.jsx` — done (draft_created, draft_saved, ai_suggestion_requested)
- `components/drafting/GuidedDraftingPage.jsx` — done (guided_draft_started)
- `components/documents/DocumentWorkspace.jsx` — done (document_uploaded)
- `components/ecourt_scrapper/` — done (search events)
- `components/feedback/Feedback.jsx` — done (feedback_submitted)
- `features/entitlementsSlice.js` — Sprint 3
- `components/dashboard/OwnerDashboard.jsx` — done (owner/admin only, day selector, KPI cards, bar chart, feature adoption table)

---

## Acceptance criteria

- Cookie banner appears and stores category preferences.
- Consent is recorded in DB under `consent_events`.
- Signup checkbox requires T&C acceptance and links are clickable.
- AI usage events are persisted with token and cost details (MongoDB).
- PostHog dashboard shows signups, logins, and feature usage events.
- Billing sandbox flow creates payment records and webhook updates subscription state.
- Privacy export returns expected user data.
- Daily P&L aggregates provider cost vs revenue.
- Alerts fire for spikes or failed payment flows.

---

## Implementation notes

- Use Razorpay for first-stage billing. Keep integration encapsulated so Stripe can be added later.
- PostHog session recording is disabled by default — enable only when traffic grows past ~1000 DAU to manage cost.
- Use PostHog feature flags instead of separate tools (LaunchDarkly / Split) for Sprint 3 rollout.
- Record every consent change as an audit event with `user_id`, `ip_address`, `user_agent`.
- If MongoDB tier is Atlas M0, document encryption-at-rest limitation and plan to upgrade for production.

---

## Next steps

1. ~~Implement cookie consent banner and consent audit endpoint.~~ — done
2. ~~Add server telemetry and usage events.~~ — done
3. Run `python manage.py initialize_analytics_indexes` to create MongoDB indexes.
4. Wire `record_usage_event()` into AI endpoints (ai_draft, talkdoc, mamla_brain) — Sprint 2 tail.
5. Add billing/app plan integrations once payment flow is ready — Sprint 4.
6. ~~Build dashboards and privacy endpoints after usage data is available — Sprint 5.~~ — done
7. ~~Harden with alerts and rollout controls — Sprint 6.~~ — done
8. Remaining deferred items: wire `record_usage_event()` into AI endpoints (ai_draft, talkdoc, mamla_brain), privacy export/delete API, billing/Razorpay integration.
