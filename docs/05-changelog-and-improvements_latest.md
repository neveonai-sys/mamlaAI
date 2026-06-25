# 05 — Changelog (Latest)

---

## 2026-06-10 — Email confirmation UX improvements

### Problem
New users who hadn't confirmed their email saw a generic red error on login ("Please verify your email...") with no way to act on it. The error was visually indistinguishable from a wrong-password error, causing confusion and support requests.

### Backend changes

**`Legalv1/users/supabase_views.py`**
- `supabase_login`: Changed the 403 response for unconfirmed email from `{"error": "<message string>"}` to `{"error": "email_not_confirmed", "message": "<human string>"}` so the frontend can detect it by code rather than string-matching.
- Added `resend_confirmation_email` view (`POST users/resend-confirmation/`): calls `supabase.auth.resend({"email": ..., "type": "signup"})`, rate-limited to 5 requests/hr per IP, always returns HTTP 200 to avoid user enumeration.

**`Legalv1/users/urls.py`**
- Registered `resend-confirmation/` route.

### Frontend changes

**`mamlaAI_ground_zero/frontend/src/components/auth/Login.jsx`**
- Detects `403 + error === "email_not_confirmed"` separately from generic errors.
- Shows an amber (not red) callout with inbox + spam folder hint and a "Resend confirmation email" button.
- Button cycles: idle → sending → sent (green tick) / error (retry label). Re-submitting the form resets all state.

### API reference
- `04-api-reference.md` updated: `login-user/` documents the 403 shape; `resend-confirmation/` endpoint added.
