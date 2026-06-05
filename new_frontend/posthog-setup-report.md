<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog into the Mamla.AI React frontend. The app now initialises `posthog-js` at startup, wraps the app with `PostHogProvider` and `PostHogErrorBoundary` for automatic error capture, and fires targeted capture events across all major user flows — authentication, case management, AI drafting, document uploads, eCourts searches, and feedback. Users are identified by email on login and signup so all events are correlated to real individuals.

**Changes summary:**
- `src/index.js` — PostHog initialised, `PostHogProvider` and `PostHogErrorBoundary` added around the app tree.
- `webpack.dev.js` / `webpack.prod.js` — `REACT_APP_POSTHOG_KEY` and `REACT_APP_POSTHOG_HOST` exposed via `DefinePlugin`.
- `.env` — PostHog token and host written (gitignore covered).
- `src/components/common/ErrorBoundary.jsx` — `posthog.captureException()` added in `componentDidCatch`.
- Eight component files updated with `usePostHog` hook and `posthog?.capture()` calls.

| Event | Description | File |
|-------|-------------|------|
| `user_signed_up` | User successfully completes account registration | `src/components/auth/Signup.jsx` |
| `user_logged_in` | User successfully authenticates and logs in | `src/components/auth/Login.jsx` |
| `case_created` | Lawyer creates a new case in the case registry | `src/components/cases/CaseRegistry.jsx` |
| `case_updated` | Lawyer updates an existing case's details | `src/components/cases/CaseRegistry.jsx` |
| `draft_created` | User starts a new legal document draft | `src/components/drafting/DraftingWorkspace.jsx` |
| `draft_saved` | User saves a draft document | `src/components/drafting/DraftingWorkspace.jsx` |
| `ai_suggestion_requested` | User requests an AI-generated suggestion in the drafting workspace | `src/components/drafting/DraftingWorkspace.jsx` |
| `guided_draft_started` | User begins the guided document drafting flow | `src/components/drafting/GuidedDraftingPage.jsx` |
| `document_uploaded` | User uploads a document for analysis or review | `src/components/documents/DocumentWorkspace.jsx` |
| `ecourts_case_searched` | User searches for a district court case via eCourts | `src/components/ecourt_scrapper/CaseStatusTerminal.jsx` |
| `cause_list_searched` | User browses the cause list for a district court | `src/components/ecourt_scrapper/CauseListTerminal.jsx` |
| `hc_case_searched` | User searches for a High Court case | `src/components/ecourt_scrapper/HCCaseStatusTerminal.jsx` |
| `feedback_submitted` | User submits product feedback | `src/components/feedback/Feedback.jsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) — Dashboard](https://eu.posthog.com/project/194847/dashboard/728502)
- [New signups](https://eu.posthog.com/project/194847/insights/Y6ugN6b7) — Daily signup trend
- [Signup to login funnel](https://eu.posthog.com/project/194847/insights/nbnLTqqD) — Conversion from signup to first login
- [Case & draft creation trend](https://eu.posthog.com/project/194847/insights/FMvoUXZR) — How often lawyers create cases and drafts
- [AI drafting engagement](https://eu.posthog.com/project/194847/insights/B7LJYRXH) — AI suggestion requests and guided draft starts
- [eCourts search activity](https://eu.posthog.com/project/194847/insights/pLpMDkY8) — District court and High Court case searches

### Agent skill

We've left an agent skill folder in your project. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
