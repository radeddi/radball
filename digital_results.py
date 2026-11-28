"""PIN-gated submission of individual Radball.digital results."""

from dataclasses import dataclass, field
from hmac import compare_digest
import json

from matchday_import import DIGITAL_API, FEEDS, league_path


def matchday_url(region, league, number):
    origin = FEEDS.get(region, "")
    if not origin.startswith(DIGITAL_API + "/"):
        return None
    return f"{origin}{league_path(league)}/{int(number)}"


def scored(game):
    score = game.get("score", game)
    return isinstance(score, dict) and all(type(score.get(key)) is int for key in ("goalsA", "goalsB"))


@dataclass
class VerifiedMatchday:
    url: str
    pin: str = field(repr=False)
    open_games: frozenset

    @classmethod
    def from_response(cls, url, league, number, pin, response):
        # The same GET is publicly readable. HTTP 200 alone does not verify a PIN.
        if not isinstance(response, dict):
            return None
        echoed = response.get("pin")
        if (not isinstance(echoed, (str, int)) or not pin.isascii()
                or not str(echoed).isascii() or not compare_digest(str(echoed), pin)
                or response.get("number") != number or response.get("leagueShortName") != league
                or not isinstance(response.get("games"), list)):
            return None
        return cls(url, pin, frozenset(
            g["number"] for g in response["games"]
            if isinstance(g, dict) and type(g.get("number")) is int and g["number"] > 0
            and ("score" not in g or isinstance(g["score"], dict)) and not scored(g)
        ))

    def final_request(self, url, game, attempted):
        number = game["number"]
        if self.url != url or game["state"] != "finished" or number not in self.open_games:
            return None
        destination = f"{url}/games/{number}"
        if destination in attempted or not scored(game):
            return None
        score = game["score"]
        attempted.add(destination)
        return destination, {"x-pin": self.pin, "Content-Type": "application/json"}, json.dumps({
            "goalsA": score["goalsA"], "goalsB": score["goalsB"], "bothLost": score["bothLost"],
        })
