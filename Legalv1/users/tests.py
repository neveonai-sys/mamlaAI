"""
Unit tests for users app — consent versioning, legal-doc-versions.

Uses SimpleTestCase (no SQL DB required — project uses MongoDB only).

Run:
    conda run -n myenv python manage.py test users --verbosity=2
"""
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from users import supabase_views


def _make_user(user_id="u1", user_type="Lawyer"):
    return {"user_id": user_id, "user_type": user_type, "email": "test@example.com"}


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/users/legal-doc-versions/ — public view, no auth needed
# ──────────────────────────────────────────────────────────────────────────────

class LegalDocVersionsTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_versions_dict(self):
        request = self.factory.get("/api/users/legal-doc-versions/")
        response = supabase_views.legal_doc_versions(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("versions", data)
        self.assertIn("terms_of_service", data["versions"])
        self.assertIn("privacy_policy", data["versions"])
        self.assertIn("cookie_preferences", data["versions"])

    def test_versions_are_strings(self):
        request = self.factory.get("/api/users/legal-doc-versions/")
        response = supabase_views.legal_doc_versions(request)
        data = json.loads(response.content)
        for key, val in data["versions"].items():
            self.assertIsInstance(val, str, f"Version for {key} should be a string")

    def test_all_known_doc_types_present(self):
        from core.legal_versions import LEGAL_DOC_VERSIONS
        request = self.factory.get("/api/users/legal-doc-versions/")
        response = supabase_views.legal_doc_versions(request)
        data = json.loads(response.content)
        for doc_type in LEGAL_DOC_VERSIONS:
            self.assertIn(doc_type, data["versions"])


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/users/consent-events/ — server-authoritative versioning
# (no @supabase_required on this view — works for unauthenticated users too)
# ──────────────────────────────────────────────────────────────────────────────

class SaveConsentEventVersioningTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch("core.init_clients.get_mongo_db")
    def test_terms_version_is_server_authoritative(self, mock_db_fn):
        from core.legal_versions import LEGAL_DOC_VERSIONS

        mock_consent_col = MagicMock()
        mock_consent_col.insert_one.return_value = MagicMock(inserted_id="fake_id")
        mock_db_fn.return_value = {
            "consent_events": mock_consent_col,
            "user_details": MagicMock(),
        }

        request = self.factory.post(
            "/api/users/consent-events/",
            data=json.dumps({
                "consent_type": "terms_of_service",
                "version": "0.0",   # client tries to send stale version
                "preferences": {"agreed": True},
            }),
            content_type="application/json",
        )
        request.supabase_user = _make_user()

        response = supabase_views.save_consent_event(request)
        self.assertEqual(response.status_code, 200)

        doc = mock_consent_col.insert_one.call_args[0][0]
        self.assertEqual(
            doc["version"],
            LEGAL_DOC_VERSIONS["terms_of_service"],
            "Server must override client-supplied version for terms_of_service",
        )

    @patch("core.init_clients.get_mongo_db")
    def test_privacy_policy_version_is_server_authoritative(self, mock_db_fn):
        from core.legal_versions import LEGAL_DOC_VERSIONS

        mock_consent_col = MagicMock()
        mock_consent_col.insert_one.return_value = MagicMock(inserted_id="fake_id")
        mock_db_fn.return_value = {
            "consent_events": mock_consent_col,
            "user_details": MagicMock(),
        }
        request = self.factory.post(
            "/api/users/consent-events/",
            data=json.dumps({"consent_type": "privacy_policy", "preferences": {}}),
            content_type="application/json",
        )
        request.supabase_user = _make_user()
        supabase_views.save_consent_event(request)

        doc = mock_consent_col.insert_one.call_args[0][0]
        self.assertEqual(doc["version"], LEGAL_DOC_VERSIONS["privacy_policy"])

    @patch("core.init_clients.get_mongo_db")
    def test_cookie_prefs_uses_client_version(self, mock_db_fn):
        mock_consent_col = MagicMock()
        mock_consent_col.insert_one.return_value = MagicMock(inserted_id="fake_id")
        mock_db_fn.return_value = {
            "consent_events": mock_consent_col,
            "user_details": MagicMock(),
        }
        request = self.factory.post(
            "/api/users/consent-events/",
            data=json.dumps({
                "consent_type": "cookie_preferences",
                "version": "2.5",
                "preferences": {"analytics": True},
            }),
            content_type="application/json",
        )
        request.supabase_user = _make_user()
        supabase_views.save_consent_event(request)
        doc = mock_consent_col.insert_one.call_args[0][0]
        # cookie_preferences is NOT in SERVER_AUTHORITATIVE_TYPES — client version kept
        self.assertEqual(doc["version"], "2.5")

    @patch("core.init_clients.get_mongo_db")
    def test_missing_consent_type_returns_400(self, _mock):
        request = self.factory.post(
            "/api/users/consent-events/",
            data=json.dumps({}),
            content_type="application/json",
        )
        response = supabase_views.save_consent_event(request)
        self.assertEqual(response.status_code, 400)

    @patch("core.init_clients.get_mongo_db")
    def test_consent_doc_includes_required_fields(self, mock_db_fn):
        mock_consent_col = MagicMock()
        mock_consent_col.insert_one.return_value = MagicMock(inserted_id="fake_id")
        mock_db_fn.return_value = {
            "consent_events": mock_consent_col,
            "user_details": MagicMock(),
        }
        request = self.factory.post(
            "/api/users/consent-events/",
            data=json.dumps({
                "consent_type": "cookie_preferences",
                "preferences": {"necessary": True, "analytics": False},
                "source": "web",
            }),
            content_type="application/json",
        )
        request.supabase_user = _make_user("user_abc")
        supabase_views.save_consent_event(request)
        doc = mock_consent_col.insert_one.call_args[0][0]
        self.assertEqual(doc["consent_type"], "cookie_preferences")
        self.assertIn("created_at", doc)
        self.assertIn("version", doc)
        self.assertEqual(doc.get("user_id"), "user_abc")
