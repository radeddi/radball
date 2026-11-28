import json
import unittest
from unittest.mock import Mock

from display_routes import Displays, result_page, send_displays

ID_A = "a" * 32
ID_B = "b" * 32
DEVICE = "1" * 32


class DisplayRoutesTest(unittest.TestCase):
    def test_selections_are_explicit_and_busy_displays_are_excluded(self):
        devices = Displays(DEVICE, {})
        def announce(key, owner, now):
            raw = json.dumps(dict(type="radball-display/2", id=key, name=key[:3], owner=owner, port=5005))
            devices.discover(raw, "127.0.0.1" if key == ID_A else "127.0.0.2", now)
        announce(ID_A, "", 0)
        announce(ID_B, "", 0)
        self.assertEqual(devices.routes(1), [])
        devices.choices.update({ID_A: "game", ID_B: "mirror"})
        self.assertEqual([r[2] for r in devices.routes(1)], ["game", "mirror"])
        announce(ID_A, "2" * 32, 2)
        self.assertEqual([r[3] for r in devices.routes(3)], [ID_B])
        announce(ID_A, DEVICE, 4)
        self.assertEqual([r[3] for r in devices.routes(8)], [ID_A])
        self.assertEqual(devices.routes(12), [])

    def test_mirror_keeps_score_and_name_together_and_results_are_scoped(self):
        sock = Mock()
        frame = dict(team1="Rot", team2="Blau", tore1="3", tore2="1", next="C\nD", rem="0:01:00",
                     controller=DEVICE, event_id=7, overview={"rows":[]},
                     routes=[["127.0.0.1",5005,"mirror",ID_A],["127.0.0.2",5005,"results",ID_B]])
        send_displays(sock,frame)
        first, second = [json.loads(call.args[0]) for call in sock.sendto.call_args_list]
        self.assertEqual((first["team1"], first["tore1"], first["next"]), ("Blau","1","D\nC"))
        self.assertNotIn("overview", first)
        self.assertNotIn("routes", second)
        self.assertEqual((second["event_id"], second["display"]), (7, ID_B))

    def test_offline_results_page_uses_pairing_order(self):
        games = [dict(teamA="A", teamB="B", score={"goalsA":1,"goalsB":2}) for _ in range(6)]
        page = result_page(games, [0,1,2,3,4,5], 4, 3, 0, 7)
        self.assertEqual(page, {"page":2,"pages":2,"rows":[["A","3:0","B"],["A","1:2","B"]]})
