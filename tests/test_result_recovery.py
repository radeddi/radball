import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock
from test_digital_results import app_methods
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from portal_results import ResultQueue


class ResultRecoveryTest(unittest.TestCase):
    def test_corrupt_queue_keeps_original_and_allows_offline_start(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "portal-results.json"
            for contents in ('{', '[]', '{"tokens":{},"authorization_failed":[],"results":{"3":{}}}'):
                file.write_text(contents)
                queue = ResultQueue(tmp)
                self.assertTrue(queue.storage_error)
                self.assertIsNone(queue.next_result())
                self.assertEqual(queue.overview(), (0, 0, 0))
                with self.assertRaises(OSError):
                    queue.set_token("1:1", "token")
                with self.assertRaises(OSError):
                    queue.enqueue("1:1", {"portal_game_id": 3, "portal_revision": 1}, 0, 0)
                self.assertEqual(file.read_text(), contents)

    def test_portal_saved_pin_follows_day_and_token_follows_court(self):
        with TemporaryDirectory() as tmp:
            url = "https://test.invalid/api/v1/matchdays/14"
            queue = ResultQueue(tmp)
            app = SimpleNamespace(portal_queue=queue, screen_manager=SimpleNamespace(current="Pin"))
            request = SimpleNamespace(resp_status=403)
            network = Mock(return_value=request)
            page = app_methods("PinPage", {"show_saved_access", "goFurther", "accept_portal_pin",
                               "portal_pin_failed", "discard_rejected_pin"}, dict(rad_app=app,
                               PORTAL_REGIONS=("Schweiz",), json=json, datetime=datetime, UrlRequest=network))
            page.land, page.day_url, page.portal_scope, page.digital_url = "Schweiz", url, "14:1", None
            page.textinput, page.placeholder, page.furtherButton = (SimpleNamespace() for _ in range(3))
            page.open_portal_day = Mock()
            page.show_saved_access()
            self.assertEqual(page.textinput.text, "")
            page.textinput.text = "00ab"
            page.goFurther(None)
            args = network.call_args.kwargs
            self.assertEqual(json.loads(args["req_body"]), {"court": 1, "pin": "00AB"})
            args["on_failure"](request, {})
            self.assertEqual(ResultQueue(tmp).saved_pin(url), "")
            page.textinput.text = "00ab"
            page.goFurther(None)
            reply = {"token": "a" * 42, "expires_at": "2100-01-01T00:00:00+00:00"}
            network.call_args.kwargs["on_success"](request, reply)
            app.portal_queue = ResultQueue(tmp)
            network.reset_mock()
            page.show_saved_access()
            self.assertEqual(page.textinput.text, "00AB")
            page.goFurther(None)
            network.assert_not_called()
            self.assertEqual(page.open_portal_day.call_count, 2)
            page.portal_scope = "14:2"
            page.show_saved_access()
            page.goFurther(None)
            self.assertEqual(json.loads(network.call_args.kwargs["req_body"]), {"court": 2, "pin": "00AB"})
            network.call_args.kwargs["on_error"](request, TimeoutError())
            self.assertEqual(ResultQueue(tmp).saved_pin(url), "00AB")
            page.show_saved_access()
            page.goFurther(None)
            network.call_args.kwargs["on_failure"](request, {})
            self.assertEqual(ResultQueue(tmp).saved_pin(url), "")
            page.day_url, page.portal_scope = url + "0", "140:1"
            page.show_saved_access()
            self.assertEqual(page.textinput.text, "")

    def test_expiry_rotation_and_legacy_token(self):
        with TemporaryDirectory() as tmp:
            Path(tmp, "portal-results.json").write_text(json.dumps(
                {"tokens": {"1:1": "legacy"}, "authorization_failed": [], "results": {}}))
            queue = ResultQueue(tmp)
            self.assertEqual(queue.token("1:1"), "legacy")
            queue.set_token("1:1", "expired", "day", "0123", 1)
            self.assertIsNone(queue.token("1:1"))
            queue.set_token("1:1", "new", "day", "0456", 4102444800)
            queue.fail_authorization("1:1", "expired")
            self.assertEqual(queue.token("1:1"), "new")
            queue.fail_authorization("1:1", "new")
            self.assertIsNone(ResultQueue(tmp).token("1:1"))
            self.assertEqual(ResultQueue(tmp).saved_pin("day"), "0456")
