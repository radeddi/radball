"""Relay the local Kivy clock to hall displays, including during screen sleep."""
import json
import socket
import time
from display_routes import send_displays


def clock_text(seconds):
    if seconds <= 0:
        return "0", "00"
    minutes, remainder = divmod(int(seconds * 10), 600)
    value = f"{remainder / 10:04.1f}" if seconds < 10 else f"{remainder // 10:02d}"
    return f"{minutes:02d}", value


def serve():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM
    ) as sender:
        receiver.bind(("127.0.0.1", 5066))
        receiver.settimeout(0.1)
        current = None
        while True:
            try:
                raw, _ = receiver.recvfrom(16384)
                message = json.loads(raw)
                if not isinstance(message, dict):
                    continue
                if message.get("idle") is True:
                    current = None
                    continue
                if not isinstance(message["routes"], list):
                    continue
                hours, minutes, seconds = message["rem"].split(":")
                remaining = max(0, int(hours) * 3600 + int(minutes) * 60 + float(seconds))
                received = time.monotonic()
                current = message
            except (KeyError, AttributeError, UnicodeError, ValueError, TypeError):
                continue
            except socket.timeout:
                if current is None:
                    continue
                elapsed = time.monotonic() - received
                running = current.get("status") == 1
                if elapsed > (remaining if running else 0) + 5:
                    current = None
                    continue
                if running:
                    current["minutes"], current["seconds"] = clock_text(remaining - elapsed)
            send_displays(sender, current)


if __name__ == "__main__":
    serve()
