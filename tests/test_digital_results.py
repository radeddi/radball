import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from portal_results import ResultQueue
from types import SimpleNamespace
import unittest

from digital_results import VerifiedMatchday, matchday_url, scored


URL = matchday_url("Deutschland", "1RB27", 5)
PLAN = {"leagueShortName": "1RB27", "number": 5, "pin": "0427", "games": [
    {"number": 7}, {"number": 8, "goalsA": 4, "goalsB": 2},
]}
SCORE = {"goalsA": 3, "goalsB": 1, "bothLost": False}


def app_methods(class_name, names, namespace):
    tree = ast.parse((Path(__file__).resolve().parents[1] / "main.py").read_text())
    original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    original.body = [node for node in original.body if isinstance(node, ast.FunctionDef) and node.name in names]
    original.bases = []
    exec(compile(ast.Module(body=[original], type_ignores=[]), "main.py", "exec"), namespace)
    return namespace[class_name]()


class DigitalResultsTest(unittest.TestCase):
    def test_public_get_and_wrong_pin_do_not_enable_upload(self):
        for invalid in ({}, {**PLAN, "pin": None}, {**PLAN, "pin": "wrong"}, {**PLAN, "number": 9}):
            self.assertIsNone(VerifiedMatchday.from_response(URL, "1RB27", 5, "0427", invalid))
        self.assertIsNone(matchday_url("Schweiz", "NL/A", 5))
        self.assertIsNone(matchday_url("Testserver", "portal-1", 5))

    def test_no_running_game_existing_result_or_wrong_matchday_is_sent(self):
        access = VerifiedMatchday.from_response(URL, "1RB27", 5, "0427", PLAN)
        for url, number, state in ((URL, 7, "running"), (URL, 8, "finished"), (URL + "1", 7, "finished")):
            self.assertIsNone(access.final_request(url, {"number": number, "state": state, "score": SCORE}, set()))

    def test_actual_kivy_completion_sends_one_put_only_after_validated_pin(self):
        calls, alerts = [], []
        app = SimpleNamespace(digital_access=None, digital_attempted=set(),
                              screen_manager=SimpleNamespace(current="Pin"), textpopup=lambda **kw: alerts.append(kw))

        tmp = self.enterContext(TemporaryDirectory())
        app.portal_queue = ResultQueue(tmp)

        def network(url, **kwargs):
            call = SimpleNamespace(url=url, **kwargs)
            calls.append(call)
            return call

        env = dict(rad_app=app, PORTAL_NAME="Testserver", PORTAL_REGIONS=("Testserver", "Schweiz"), UrlRequest=network, VerifiedMatchday=VerifiedMatchday,
                   matchday_url=matchday_url, scored=scored)
        pin = app_methods("PinPage", {"goFurther", "accept_digital_pin", "digital_pin_failed", "discard_rejected_pin", "show_saved_access"}, env)
        pin.digital_url, pin.gameId, pin.league_short = URL, 5, "1RB27"
        pin.day_url, pin.land = URL, "Deutschland"
        pin.textinput, pin.placeholder = SimpleNamespace(text="0427"), SimpleNamespace(text="")
        pin.furtherButton = SimpleNamespace(disabled=False)
        pin.open_portal_day = lambda: setattr(app.screen_manager, "current", "Present")
        pin.goFurther(None)
        check = calls[-1]
        self.assertEqual((check.method, check.req_headers["x-pin"]), ("GET", "0427"))
        check.on_success(check, {k: v for k, v in PLAN.items() if k != "pin"})
        self.assertIsNone(app.digital_access)
        self.assertEqual(ResultQueue(tmp).saved_pin(URL), "")
        pin.textinput.text = "0427"
        pin.goFurther(None)
        check = calls[-1]
        check.on_success(check, PLAN)
        self.assertEqual(app.screen_manager.current, "Present")
        app.portal_queue = ResultQueue(tmp)
        pin.show_saved_access()
        self.assertEqual(pin.textinput.text, "0427")
        self.assertEqual(app.portal_queue.saved_pin(matchday_url("Bayern", "1RB27", 5)), "")
        game = app_methods("GamePage", {"save_current_result", "result_is_final", "send_digital_result"}, env)
        game.land, game.gameId, game.league_short, game.gameNr = "Deutschland", 5, "1RB27", 0
        game.game_json = {"games": [{"number": 7, "state": "running"}]}
        game.startStopButton = SimpleNamespace(disabled=False)
        game.pauseButton = SimpleNamespace(disabled=False)
        game.match_drafts = {}
        self.assertEqual(len(calls), 2)
        self.assertTrue(game.save_current_result(SCORE))
        write = calls[-1]
        self.assertEqual((write.method, write.url, write.req_headers["x-pin"]), ("PUT", URL + "/games/7", "0427"))
        self.assertEqual(json.loads(write.req_body), SCORE)
        write.on_error(write, TimeoutError())
        self.assertEqual(len(alerts), 1)
        game.save_current_result(SCORE)
        self.assertEqual(len(calls), 3)
