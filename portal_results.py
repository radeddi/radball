"""Durable device credentials and one receipt per completed portal game."""

import time
import json
import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile


class ResultQueue:
    def __init__(self, folder):
        self.file = Path(folder) / "portal-results.json"
        self.storage_error = False
        self.state = {"tokens": {}, "authorization_failed": [], "results": {}}
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            if (not isinstance(data, dict) or not isinstance(data.get("tokens"), dict)
                    or not isinstance(data.get("authorization_failed"), list)
                    or not isinstance(data.get("results"), dict)
                    or not isinstance(data.get("pins", {}), dict)
                    or not isinstance(data.get("expires", {}), dict)):
                raise ValueError
            for row in data["results"].values():
                if (not isinstance(row, dict) or not isinstance(row.get("scope"), str)
                        or row.get("status") not in ("pending", "sent", "conflict")
                        or not isinstance(row.get("body"), dict)
                        or not isinstance(row["body"].get("request_id"), str)
                        or type(row["body"].get("revision")) is not int):
                    raise ValueError
            self.state = data
        except FileNotFoundError:
            pass
        except (OSError, ValueError, RecursionError):
            # Preserve the original for recovery. Local matches and UDP remain available.
            self.storage_error = True

    def ensure_writable(self):
        if self.storage_error:
            raise OSError("Der lokale Ergebnisspeicher muss wiederhergestellt werden.")

    def save(self):
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.file.parent, delete=False) as output:
            path = output.name
            try:
                json.dump(self.state, output)
                output.flush()
                os.fsync(output.fileno())
                output.close()
                os.replace(path, self.file)
            finally:
                if os.path.exists(path):
                    os.unlink(path)

    @staticmethod
    def scope(day, court):
        return f"{int(day)}:{int(court)}"

    def saved_pin(self, day_url):
        value = self.state.get("pins", {}).get(day_url)
        return value if isinstance(value, str) else ""

    def update_access(self, **changes):
        self.ensure_writable()
        previous = self.state
        self.state = {**previous, **changes}
        try:
            self.save()
        except OSError:
            self.state = previous
            raise

    def remember_pin(self, day_url, pin):
        if self.saved_pin(day_url) != pin:
            self.update_access(pins={**self.state.get("pins", {}), day_url: pin})

    def forget_pin(self, day_url, rejected):
        if rejected and self.saved_pin(day_url) == rejected:
            self.update_access(pins={k: v for k, v in self.state["pins"].items() if k != day_url})

    def set_token(self, scope, token, day_url=None, pin=None, expires_at=None):
        changes = dict(tokens={**self.state["tokens"], scope: token},
                       expires={**self.state.get("expires", {}), scope: expires_at},
                       authorization_failed=[s for s in self.state["authorization_failed"] if s != scope])
        if day_url and pin:
            changes["pins"] = {**self.state.get("pins", {}), day_url: pin}
        self.update_access(**changes)

    def fail_authorization(self, scope, token):
        if self.token(scope) == token:
            self.update_access(authorization_failed=[*self.state["authorization_failed"], scope])

    def token(self, scope):
        expiry = self.state.get("expires", {}).get(scope)
        if expiry is not None and (not isinstance(expiry, (int, float)) or expiry <= time.time()):
            return None
        if scope not in self.state["authorization_failed"]:
            return self.state["tokens"].get(scope)

    def enqueue(self, scope, game, home, away):
        self.ensure_writable()
        key = str(game["portal_game_id"])
        results = self.state["results"]
        previous = results.get(key)
        if previous and previous["body"]["revision"] >= game["portal_revision"]:
            return False
        results[key] = {"scope": scope, "status": "pending", "body": {
            "request_id": str(uuid.uuid4()), "revision": game["portal_revision"],
            "home_goals": home, "away_goals": away,
        }}
        try:
            self.save()
        except OSError:
            if previous:
                results[key] = previous
            else:
                del results[key]
            raise
        return True

    def next_result(self):
        for key, row in self.state["results"].items():
            token = self.token(row["scope"])
            if row["status"] == "pending" and token:
                return key, row, token
        return None

    def mark(self, key, status, request_id=None):
        row = self.state["results"][key]
        if request_id is not None and row["body"]["request_id"] != request_id:
            return
        row["status"] = status
        self.save()

    def already_finished(self, game):
        revision = game.get("portal_revision")
        row = self.state["results"].get(str(game.get("portal_game_id")))
        return row is not None and revision is not None and row["body"]["revision"] >= revision

    def overview(self):
        rows = tuple(self.state["results"].values())
        pending = sum(row["status"] == "pending" for row in rows)
        sent = sum(row["status"] == "sent" for row in rows)
        conflicts = sum(row["status"] == "conflict" for row in rows)
        return pending, sent, conflicts
