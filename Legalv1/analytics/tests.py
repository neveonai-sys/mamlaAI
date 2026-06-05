"""
Unit tests for analytics helpers.

Uses SimpleTestCase (no SQL DB required — project uses MongoDB only).

Run:
    conda run -n myenv python manage.py test analytics --verbosity=2
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, RequestFactory

from analytics import views as analytics_views
from core.analytics import calculate_estimated_cost, record_usage_event


# ──────────────────────────────────────────────────────────────────────────────
# core/analytics.py — calculate_estimated_cost
# ──────────────────────────────────────────────────────────────────────────────

class CalculateEstimatedCostTests(SimpleTestCase):

    def test_known_model_gpt4o(self):
        cost = calculate_estimated_cost("gpt-4o", 1000, 500)
        self.assertGreater(cost, 0)

    def test_known_model_gpt4o_mini(self):
        cost = calculate_estimated_cost("gpt-4o-mini", 1000, 500)
        self.assertGreater(cost, 0)

    def test_gpt4o_more_expensive_than_mini(self):
        cost_4o = calculate_estimated_cost("gpt-4o", 1000, 500)
        cost_mini = calculate_estimated_cost("gpt-4o-mini", 1000, 500)
        self.assertGreater(cost_4o, cost_mini)

    def test_unknown_model_falls_back(self):
        cost = calculate_estimated_cost("my-custom-model-xyz", 1000, 500)
        self.assertGreaterEqual(cost, 0)

    def test_zero_tokens_returns_zero(self):
        cost = calculate_estimated_cost("gpt-4o", 0, 0)
        self.assertEqual(cost, 0.0)

    def test_proportional_to_tokens(self):
        cost_low = calculate_estimated_cost("gpt-4o", 100, 50)
        cost_high = calculate_estimated_cost("gpt-4o", 10000, 5000)
        self.assertGreater(cost_high, cost_low)


# ──────────────────────────────────────────────────────────────────────────────
# core/analytics.py — record_usage_event
# ──────────────────────────────────────────────────────────────────────────────

class RecordUsageEventTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch("core.analytics.get_analytics_db")
    def test_inserts_document(self, mock_db_fn):
        mock_collection = MagicMock()
        mock_db_fn.return_value = MagicMock(usage_events=mock_collection)

        request = self.factory.get("/fake/")
        request.supabase_user = {"user_id": "lawyer1", "user_type": "Lawyer", "email": "l@x.com"}
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        record_usage_event(request, "talkdoc", "gpt-4o-mini", 100, 50)

        mock_collection.insert_one.assert_called_once()
        doc = mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["feature"], "talkdoc")
        self.assertEqual(doc["prompt_tokens"], 100)
        self.assertEqual(doc["completion_tokens"], 50)
        self.assertEqual(doc["total_tokens"], 150)
        self.assertIn("estimated_cost", doc)
        self.assertIn("timestamp", doc)

    @patch("core.analytics.get_analytics_db")
    def test_does_not_raise_on_db_error(self, mock_db_fn):
        mock_db_fn.side_effect = Exception("DB down")
        request = self.factory.get("/fake/")
        request.supabase_user = {"user_id": "u1", "user_type": "Lawyer", "email": "x@x.com"}
        try:
            record_usage_event(request, "talkdoc", "gpt-4o", 10, 5)
        except Exception:
            self.fail("record_usage_event should not raise on DB error")

    @patch("core.analytics.get_analytics_db")
    def test_user_id_from_supabase_user(self, mock_db_fn):
        mock_collection = MagicMock()
        mock_db_fn.return_value = MagicMock(usage_events=mock_collection)
        request = self.factory.get("/fake/")
        request.supabase_user = {"user_id": "target_user", "user_type": "Lawyer", "email": "x@x.com"}
        record_usage_event(request, "ai_draft", "gpt-4o", 50, 25)
        doc = mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc.get("user_id"), "target_user")


# ──────────────────────────────────────────────────────────────────────────────
# analytics/views.py — _is_owner helper
# ──────────────────────────────────────────────────────────────────────────────

class IsOwnerHelperTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _req(self, user_type):
        req = self.factory.get("/")
        req.supabase_user = {"user_id": "u1", "user_type": user_type}
        return req

    def test_owner_returns_true(self):
        self.assertTrue(analytics_views._is_owner(self._req("owner")))

    def test_admin_returns_true(self):
        self.assertTrue(analytics_views._is_owner(self._req("admin")))

    def test_lawyer_returns_false(self):
        self.assertFalse(analytics_views._is_owner(self._req("Lawyer")))

    def test_client_returns_false(self):
        self.assertFalse(analytics_views._is_owner(self._req("Client")))

    def test_no_supabase_user_returns_false(self):
        req = self.factory.get("/")
        self.assertFalse(analytics_views._is_owner(req))


# ──────────────────────────────────────────────────────────────────────────────
# core/audit_log.py
# ──────────────────────────────────────────────────────────────────────────────

class AuditLogTests(SimpleTestCase):

    @patch("core.audit_log.get_mongo_db")
    def test_inserts_audit_record(self, mock_db_fn):
        mock_collection = MagicMock()
        mock_db_fn.return_value = {"audit_logs": mock_collection}

        from core.audit_log import write_audit_log
        write_audit_log("delete_user_data", "user123", actor_type="owner", metadata={"key": "val"})

        mock_collection.insert_one.assert_called_once()
        doc = mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["action"], "delete_user_data")
        self.assertEqual(doc["actor_id"], "user123")
        self.assertEqual(doc["actor_type"], "owner")
        self.assertEqual(doc["metadata"], {"key": "val"})
        self.assertIn("timestamp", doc)

    @patch("core.audit_log.get_mongo_db")
    def test_does_not_raise_on_db_error(self, mock_db_fn):
        mock_db_fn.side_effect = Exception("DB down")
        from core.audit_log import write_audit_log
        try:
            write_audit_log("some_action", "user1")
        except Exception:
            self.fail("write_audit_log must swallow DB errors")

    def test_audit_from_request_extracts_actor(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.supabase_user = {"user_id": "u99", "user_type": "admin"}
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        request.META["HTTP_USER_AGENT"] = "TestAgent/1"

        from core.audit_log import audit_from_request
        with patch("core.audit_log.get_mongo_db") as mock_db_fn:
            mock_col = MagicMock()
            mock_db_fn.return_value = {"audit_logs": mock_col}
            audit_from_request(request, "test_action", metadata={"extra": 1})

        doc = mock_col.insert_one.call_args[0][0]
        self.assertEqual(doc["actor_id"], "u99")
        self.assertEqual(doc["actor_type"], "admin")
        self.assertEqual(doc["ip_address"], "10.0.0.1")
        self.assertEqual(doc["action"], "test_action")
