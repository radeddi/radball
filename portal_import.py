"""Convert public portal plans into offline Kivy play lists."""

from collections import defaultdict
from datetime import date
from pathlib import Path
import re

from matchday_import import save_matchday


PORTAL_NAME = "Testserver"
SWISS_PORTAL_NAME = "Schweiz"
PORTAL_REGIONS = (PORTAL_NAME, SWISS_PORTAL_NAME)
PORTAL_URL = "https://radball.groff.ch"
CATALOG = "/api/v1/events"


def portal_jobs(catalog):
    check_version(catalog)
    ids = {
        positive_id(day["id"])
        for event in catalog["events"]
        for day in event["matchdays"]
    }
    return [f"/api/v1/matchdays/{day_id}" for day_id in sorted(ids)]


def check_version(payload):
    if not isinstance(payload, dict) or type(payload.get("api_version", 1)) is not int or payload.get("api_version", 1) != 1:
        raise ValueError("Diese Portalversion wird nicht unterstützt.")


def positive_id(value):
    if type(value) is not int or value < 1:
        raise ValueError("Ungültige Kennung")
    return value


def cache_portal_plan(folder, route, plan):
    check_version(plan)
    day_id = positive_id(plan["id"])
    if route != f"/api/v1/matchdays/{day_id}":
        raise ValueError("Antwort gehört zu einem anderen Spieltag")
    day_date = date.fromisoformat(plan["date"]).isoformat()
    title = plan["event"].strip()
    phase = plan["phase"].strip()
    if not title or not phase or not isinstance(plan["games"], list):
        raise ValueError("Ungültiger Portal-Spielplan")
    courts = defaultdict(list)
    for game in plan["games"]:
        if game["status"] != "planned":
            continue
        court = positive_id(game["court"])
        home, away = game["home"].strip(), game["away"].strip()
        if not home or not away or home == away:
            raise ValueError("Ungültige Paarung")
        courts[court].append((positive_id(game["order"]), positive_id(game["id"]), home, away, positive_id(game["revision"])))
    region = SWISS_PORTAL_NAME if title.startswith("CH 2026 · ") else PORTAL_NAME
    active = set()
    for court, matches in sorted(courts.items()):
        games = [
            {"number": index, "portal_game_id": game_id, "portal_revision": revision,
             "teamA": home, "teamB": away, "state": "Open"}
            for index, (_, game_id, home, away, revision) in enumerate(sorted(matches), 1)
        ]
        names = sorted({value for game in games for value in (game["teamA"], game["teamB"])})
        target = save_matchday(folder, region, {
            "number": day_id, "portal_event_id": plan.get("event_id"), "leagueShortName": f"portal-{court}",
            "leagueLongName": f"{title} – {phase} · Fläche {court}",
            "welcome": str(plan.get("welcome") or "")[:140], "phase_name": phase, "portal_court": court, "start": day_date, "gym": {"city": f"Spielfläche {court}"},
            "teams": [{"name": name, "present": True, "players": []} for name in names],
            "games": games, "incidents": [],
        })
        active.add(target)
    for cache_region in PORTAL_REGIONS:
        directory = Path(folder) / "spieltage" / cache_region
        for old in directory.glob(f"portal-*_{day_id}.radball"):
            if old not in active and re.fullmatch(r"portal-[0-9]+_[0-9]+\.radball", old.name):
                old.unlink()
    return len(active)
