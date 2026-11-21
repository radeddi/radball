"""Read and cache matchdays from the public league feeds."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote


SWISS_API = "https://rmva.groff.de/api"
DIGITAL_API = "https://rest.radball.digital"
FEEDS = {
    "Baden Württemberg": f"{DIGITAL_API}/689f53bb-44d4-4be0-b5e1-aa2d66177459",
    "Bayern": f"{DIGITAL_API}/8570f08a-4a57-42ef-a3b9-4fb237620315",
    "Deutschland": f"{DIGITAL_API}/e897552b-f7c2-4dd1-8cae-5830c3ab8244",
    "Brandenburg": f"{DIGITAL_API}/8893c1bf-213f-4291-b200-99482e24b427",
    "Schweiz": SWISS_API,
}


def league_path(short_name):
    return f"/leagues/{quote(short_name, safe='')}/matchdays"


def import_jobs(path, payload):
    if not isinstance(payload, list):
        raise ValueError("Erwartet wurde eine JSON-Liste")
    if path == "/leagues":
        return [league_path(league["shortName"]) for league in payload]
    return [f"{path}/{int(day['number'])}" for day in payload]


def save_matchday(folder, region, day):
    league = day["leagueShortName"]
    if not isinstance(league, str) or not league or "/" in league or "\\" in league:
        raise ValueError("Ungültiger Liga-Kurzname")
    number = int(day["number"])
    if not isinstance(day["leagueLongName"], str) or not isinstance(day["start"], str):
        raise ValueError("Ungültige Spieltagsdaten")
    if not isinstance(day["teams"], list) or not isinstance(day["games"], list):
        raise ValueError("Ungültige Mannschafts- oder Spieleliste")
    if day.get("gym") is None:
        day["gym"] = {}
    day["gym"].setdefault("city", "")
    for team in day["teams"]:
        if not isinstance(team["name"], str):
            raise ValueError("Ungültiger Mannschaftsname")
    for game in day["games"]:
        if not all(isinstance(game[key], str) for key in ("teamA", "teamB")):
            raise ValueError("Ungültige Spielpaarung")
        int(game["number"])
        game.setdefault("state", "Open")
        if game.get("goalsA") is not None and game.get("goalsB") is not None:
            game.setdefault("score", {
                "goalsA": game["goalsA"], "goalsB": game["goalsB"],
                "bothLost": game.get("bothLost", False),
            })

    directory = Path(folder) / "spieltage" / region
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{league}_{number}.radball"
    # Keep incomplete downloads out of the directory scanned by the selector.
    output = NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False)
    temporary = output.name
    try:
        with output:
            json.dump(day, output, indent=4, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination
