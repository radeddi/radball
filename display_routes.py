"""LAN display discovery, explicit selection and per-display transmission."""
import ipaddress
import json
from uuid import UUID

MODES = {"off": "Aus", "game": "Spiel", "mirror": "Spiel gespiegelt", "results": "Ergebnisse"}


class Displays:
    def __init__(self, controller, choices):
        self.controller = controller
        self.choices = dict(choices)
        self.seen = {}

    def discover(self, raw, address, now):
        if raw == b"Hello, I need data":
            if any(d["address"] == address and not d["legacy"] for d in self.seen.values()):
                return
            modes = ("game", "mirror")
            key, name, port, owner, legacy = "ip:" + address, "Ältere Tafel", 5005, "", True
        else:
            try:
                d = json.loads(raw)
                kind = d["type"]
                protocols = d.get("protocols", [])
                if kind != "radball-display/2" and not (
                    isinstance(kind, str) and kind.startswith("radball-display/") and
                    isinstance(protocols, list) and 2 in protocols
                ):
                    return
                features = d.get("modes", ["game", "mirror", "results"] if kind == "radball-display/2" else ["game"])
                if not isinstance(features, list) or "game" not in features:
                    return
                modes = tuple(m for m in ("game", "mirror", "results") if m in features)
                key = UUID(d["id"]).hex
                name, port, owner = d["name"], d["port"], d["owner"]
                if (not isinstance(name, str) or not 1 <= len(name) <= 64 or type(port) is not int
                        or not 1024 <= port <= 65535 or not isinstance(owner, str) or len(owner) > 40):
                    return
            except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
                return
            legacy = False
            self.seen.pop("ip:" + address, None)
        if key not in self.seen and len(self.seen) >= 64:
            return
        self.seen[key] = dict(name=name, address=address, port=port, owner=owner, at=now, legacy=legacy, modes=modes)

    def available(self, now):
        self.seen = {k: d for k, d in self.seen.items() if d["legacy"] or now - d["at"] < 7}
        return self.seen

    def routes(self, now):
        return [[d["address"], d["port"], mode if mode in d["modes"] else "game", k] for k, d in self.available(now).items()
                if (mode := self.choices.get(k)) in ("game", "mirror", "results")
                and d["owner"] in ("", self.controller)]


def result_page(games, sequence, current, home_goals, away_goals, now):
    pages = max(1, (len(sequence) + 3) // 4)
    page = int(now // 7) % pages
    rows = []
    for i in sequence[4 * page:4 * page + 4]:
        game = games[i]
        score = game.get("score") or game
        if i == current:
            result = f"{home_goals}:{away_goals}"
        elif type(score.get("goalsA")) is int and type(score.get("goalsB")) is int:
            result = f"{score['goalsA']}:{score['goalsB']}"
        else:
            result = "–"
        rows.append([str(game["teamA"])[:70], result, str(game["teamB"])[:70]])
    return {"page": page + 1, "pages": pages, "rows": rows}


def send_displays(sock, frame):
    routes = frame.get("routes", ())
    base = {k: v for k, v in frame.items() if k not in ("routes", "overview", "event_id", "rem")}
    if not isinstance(routes, (list, tuple)):
        return
    for route in routes[:64]:
        if not isinstance(route, (list, tuple)) or len(route) != 4:
            continue
        address, port, mode, key = route
        if mode not in ("game", "mirror", "results") or type(port) is not int or not 1024 <= port <= 65535:
            continue
        packet = dict(base, display=key, view=mode)
        if mode == "mirror" and all(k in base for k in ("team1","team2","tore1","tore2")):
            packet["team1"], packet["team2"] = base["team2"], base["team1"]
            packet["tore1"], packet["tore2"] = base["tore2"], base["tore1"]
            packet["next"] = "\n".join(reversed(base.get("next", "").splitlines()))
        elif mode == "results":
            if isinstance(frame.get("overview"), dict):
                packet.update(overview=frame["overview"], event_id=frame.get("event_id"))
            else:
                packet["view"] = "game"
        try:
            ipaddress.IPv4Address(address)
            sock.sendto(json.dumps(packet, ensure_ascii=False).encode(), (address, port))
        except (ValueError, OverflowError, TypeError, OSError):
            continue
