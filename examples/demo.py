"""Live GranolaDB demo, paced for screen recording.

Writes a readable log note to Granola so a note visibly appears while recording.
Run:  python examples/demo.py
Then cut to Granola to show the note, and open the demo folder to query the AI.
"""
import time

from granoladb.backend_granola import GranolaBackend


def line(text="", pause=0.8):
    print(text)
    time.sleep(pause)


def main():
    be = GranolaBackend()
    line("GranolaDB — a database that runs on your meeting notes.", 1.2)
    line("Storing this app's backend logs... in Granola.\n", 1.2)

    body = "\n".join([
        "backend service — live logs", "",
        "2026-08-31T10:02:01Z INFO  api      POST /v1/checkout 200 (38ms)",
        "2026-08-31T10:02:03Z WARN  api      p99 latency 771ms above target",
        "2026-08-31T10:02:05Z ERROR payments charge declined user_id=2 (card_declined)",
        "2026-08-31T10:02:06Z INFO  api      order 1005 shipped $78.25",
    ])

    line("→ granoladb: writing 4 log lines...", 1.4)
    be.create_document("backend — live demo", body)
    line("✓ stored as a Granola note.\n", 1.2)
    line("Open Granola. Your logs are now a meeting.", 0.4)


if __name__ == "__main__":
    main()
