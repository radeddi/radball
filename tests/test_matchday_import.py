import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from matchday_import import FEEDS, import_jobs, save_matchday


class MatchdayImportTest(unittest.TestCase):
    def test_feed_paths_encode_short_name_once(self):
        self.assertEqual(set(FEEDS), {
            "Baden Württemberg", "Bayern", "Deutschland", "Brandenburg",
        })
        self.assertEqual(len(set(FEEDS.values())), len(FEEDS))
        paths = import_jobs("/leagues", [{"shortName": "Liga A/B"}])
        self.assertEqual(paths, ["/leagues/Liga%20A%2FB/matchdays"])
        self.assertEqual(import_jobs(paths[0], [{"number": 3}]), [paths[0] + "/3"])

    def test_html_is_not_a_successful_feed(self):
        with self.assertRaises(ValueError):
            import_jobs("/leagues", "<html></html>")

    def test_cache_accepts_provider_fields_used_by_match_control(self):
        day = {
            "leagueShortName": "OL", "leagueLongName": "Oberliga",
            "number": 1, "start": "2026-12-05T17:00:00.000Z",
            "teams": [{"name": "Alpha"}, {"name": "Beta"}],
            "games": [
                {"number": 1, "teamA": "Alpha", "teamB": "Beta"},
                {"number": 2, "teamA": "Beta", "teamB": "Alpha", "goalsA": 0, "goalsB": 3},
            ],
        }
        with TemporaryDirectory() as folder:
            own = Path(folder) / "spieltage/eigene/own_1.radball"
            own.parent.mkdir(parents=True)
            own.write_text("local")
            path = save_matchday(folder, "Bayern", day)
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["gym"]["city"], "")
            self.assertEqual(loaded["games"][0]["state"], "Open")
            self.assertEqual(loaded["games"][1]["score"]["goalsA"], 0)
            original = path.read_bytes()
            invalid = dict(day, games=[{}])
            with self.assertRaises(KeyError):
                save_matchday(folder, "Bayern", invalid)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(own.read_text(), "local")

    def test_reject_unsafe_league_filename(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_matchday(folder, "Bayern", {"leagueShortName": "../elsewhere"})


if __name__ == "__main__":
    unittest.main()
