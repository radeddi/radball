from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

from matchday_import import FEEDS
from portal_import import PORTAL_NAME, SWISS_PORTAL_NAME, cache_portal_plan
from test_digital_results import app_methods


class SwissPortalTest(TestCase):
    def test_archive_migrates_out_of_testserver_and_keeps_match_identity(self):
        self.assertNotIn(SWISS_PORTAL_NAME, FEEDS)
        day = {
            "id": 17, "date": "2026-01-17", "phase": "Liga-Spieltag",
            "event": "CH 2026 · NLA · Mosnang · Liga-Spieltag",
            "games": [{"status": "planned", "court": 2, "id": 33, "order": 1,
                       "home": "Rot", "away": "Blau", "revision": 1}],
        }
        with TemporaryDirectory() as folder:
            legacy = Path(folder) / "spieltage" / PORTAL_NAME / "portal-2_17.radball"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}")
            self.assertEqual(cache_portal_plan(folder, "/api/v1/matchdays/17", day), 1)
            self.assertFalse(legacy.exists())
            cached = json.loads(legacy.parent.with_name(SWISS_PORTAL_NAME).joinpath(legacy.name).read_text())
            self.assertEqual(cached["portal_court"], 2)
            self.assertEqual(cached["games"][0]["portal_game_id"], 33)

    def test_empty_sequence_starts_no_callbacks(self):
        schedule = mock.Mock()
        warning = mock.Mock()
        page = app_methods("GamePage", {"load_GamePage"}, {
            "rad_app": SimpleNamespace(textpopup=warning), "Clock": SimpleNamespace(schedule_interval=schedule),
        })
        page.load_GamePage({"games": []}, [], "eigene", 1, "own")
        schedule.assert_not_called()
        warning.assert_called_once()

    def test_preview_uses_playable_sequence(self):
        class PreviewObserved(Exception):
            pass

        class StopAfterPreview:
            def __eq__(self, value):
                raise PreviewObserved

        games = mock.MagicMock(wraps=[
            {"teamA": "Rot", "teamB": "Blau"},
            {"teamA": "Grün", "teamB": "Gelb"},
            {"teamA": "Lila", "teamB": "Orange"},
        ])
        page = app_methods("GamePage", {"refreshTime"}, {"timedelta": timedelta})
        page.game_json = {"games": games}
        page.gameStatus = StopAfterPreview()
        page.timeLeft = timedelta(0)
        page.gameNr, page.sequence = 2, [2]
        with self.assertRaises(PreviewObserved):
            page.refreshTime(None)
        games.__getitem__.assert_not_called()
        page.gameNr, page.sequence = 0, [0, 2, 1]
        with self.assertRaises(PreviewObserved):
            page.refreshTime(None)
        games.__getitem__.assert_called_once_with(2)

    def test_swiss_pin_goes_to_the_portal_with_the_selected_court(self):
        request = mock.Mock()
        page = app_methods("PinPage", {"goFurther"}, {
            "rad_app": SimpleNamespace(portal_queue=mock.Mock()), "PORTAL_REGIONS": (PORTAL_NAME, SWISS_PORTAL_NAME),
            "PORTAL_URL": "http://testportal", "UrlRequest": request, "json": json,
        })
        page.land = SWISS_PORTAL_NAME
        page.gameId, page.portal_scope = 17, "17:2"
        page.day_url = "http://testportal/api/v1/matchdays/17"
        page.digital_url = None
        page.textinput = SimpleNamespace(text="a123")
        page.furtherButton = SimpleNamespace(disabled=False)
        page.placeholder = SimpleNamespace(text="")
        page.portal_pin_failed = mock.Mock()
        page.goFurther(None)
        self.assertEqual(request.call_args.args, ("http://testportal/api/v1/matchdays/17/access/redeem",))
        self.assertEqual(json.loads(request.call_args.kwargs["req_body"]), {"pin": "A123", "court": 2})

    def test_empty_fixture_is_not_written(self):
        prompt = mock.Mock()
        write = mock.Mock()
        page = app_methods("NewGameStep3Screen", {"save_matchday"}, {
            "rad_app": SimpleNamespace(textpopup=prompt, temp_matchday_data={}), "open": write,
        })
        page.gamesContainer = SimpleNamespace(children=[])
        page.save_matchday(None)
        prompt.assert_called_once()
        write.assert_not_called()
