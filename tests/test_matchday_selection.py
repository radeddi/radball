import unittest

from matchday_selection import league_order, matchday_order, selection_labels


def cached_day(event, phase, number, start, court=1):
    return {
        "leagueLongName": f"{event} – {phase} · Fläche {court}",
        "leagueShortName": f"portal-{court}",
        "portal_court": court,
        "phase_name": phase,
        "number": number,
        "start": start,
        "gym": {"city": f"Spielfläche {court}"},
    }


class MatchdaySelectionTest(unittest.TestCase):
    def test_archive_uses_the_league_and_date_from_cached_plans(self):
        early = cached_day("CH 2026 · NLA · Mosnang · Liga-Spieltag", "Liga-Spieltag", 200, "2026-01-17")
        late = cached_day("CH 2026 · NLA · Altdorf · Finalspieltag", "Finalspieltag", 4, "2026-10-03")
        self.assertEqual(selection_labels(early), (
            "CH 2026 · NLA", "Mosnang · Liga-Spieltag · Fläche 1", "Mosnang",
        ))
        self.assertEqual(selection_labels(late)[0], selection_labels(early)[0])
        self.assertEqual(sorted([late, early], key=matchday_order), [early, late])

    def test_phases_and_courts_remain_distinguishable(self):
        event = "CH 2026 · Schweizer Cup · Altdorf · Finale"
        first = cached_day(event, "Vorrunde", 25, "2026-02-28")
        second = cached_day(event, "Finalspiele", 26, "2026-02-28", 2)
        self.assertEqual(selection_labels(first)[0], selection_labels(second)[0])
        self.assertIn("Vorrunde · Fläche 1", selection_labels(first)[1])
        self.assertIn("Finalspiele · Fläche 2", selection_labels(second)[1])
        self.assertEqual(second["leagueShortName"], "portal-2")

    def test_league_order_follows_tiers_and_natural_numbers(self):
        labels = ["CH 2026 · 3.Liga", "CH 2026 · NLB", "CH 2026 · NLA", "10. Liga", "2. Liga"]
        self.assertEqual(sorted(labels, key=league_order), [labels[i] for i in (2, 1, 0, 4, 3)])

    def test_existing_external_feed_keeps_its_league(self):
        day = {"leagueLongName": "1. Bundesliga", "number": 3, "gym": {"city": "Mainz"}}
        self.assertEqual(selection_labels(day), ("1. Bundesliga", "Spieltag 3", "Mainz"))
