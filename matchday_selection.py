"""Labels and ordering for local and downloaded matchdays."""

from datetime import date
import re


ARCHIVE_LEAGUES = (
    "NLA", "NLB", "1.Liga", "2.Liga", "3.Liga", "Damen",
    "U11", "U13", "U15", "U17", "U19", "U17 / U19",
    "Schweizer Cup", "EM Junioren", "EM Juniorinnen",
)


def portal_labels(title, phase, court):
    parts = title.split(" · ", 3)
    if len(parts) == 4 and parts[0] == "CH 2026" and parts[1] in ARCHIVE_LEAGUES:
        _, league, place, stage = parts
        day = f"{place} · {stage}" if phase == stage else f"{place} · {stage} · {phase}"
        return f"CH 2026 · {league}", f"{day} · Fläche {court}", place
    return title, f"{phase} · Fläche {court}", ""


def selection_labels(day):
    if "portal_court" in day:
        title = day["leagueLongName"].removesuffix(f" – {day['phase_name']} · Fläche {day['portal_court']}")
        return portal_labels(title, day["phase_name"], day["portal_court"])
    return (
        day["leagueLongName"], day.get("phase_name", f"Spieltag {day['number']}"),
        (day.get("gym") or {}).get("city") or "",
    )


def league_order(name):
    prefix, _, league = name.partition(" · ")
    if prefix == "CH 2026" and league in ARCHIVE_LEAGUES:
        return (0, ARCHIVE_LEAGUES.index(league), ())
    natural = tuple(int(part) if index % 2 else part for index, part in enumerate(re.split(r"(\d+)", name.casefold())))
    return (1, 0, natural)


def matchday_order(day):
    _, label, place = selection_labels(day)
    try:
        played_on = date.fromisoformat(day["start"][:10])
    except ValueError:
        played_on = date.max
    return played_on, place.casefold(), int(day["number"]), day.get("portal_court", 0), label.casefold()
