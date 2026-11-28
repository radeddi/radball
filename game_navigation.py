"""Rules for advancing a game without implicitly starting or finishing it."""


def expired_during_play(remaining, second_half):
    return second_half and remaining.total_seconds() <= 0


def may_finalize_on_navigation(expired, already_finished):
    return expired and not already_finished


def quick_game_plan(home, away):
    home, away = home.strip(), away.strip()
    if not home or not away or home.casefold() == away.casefold():
        raise ValueError("Bitte zwei unterschiedliche Mannschaften eingeben.")
    return {"games": [{"number": 1, "teamA": home, "teamB": away, "state": "Open"}]}
