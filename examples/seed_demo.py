"""Seed a couple of fake GranolaDB "records" so Granola's AI has something to
summarize. Run with a real token:

    GRANOLA_TOKEN="your-granola-token" python examples/seed_demo.py

Each batch below becomes ONE Granola note (a "meeting"), so you can open it in
Granola and ask the AI things like:
    - "What happened in this meeting?"
    - "What was the root cause?"
    - "How much did the agent spend?"
"""
import granoladb


def seed_incident(db):
    """A fake AI shopping-agent incident, told as log lines + trace spans."""
    for rec in [
        {"kind": "span", "name": "agent.plan", "level": "INFO", "svc": "shop-agent",
         "msg": "user asked: buy running shoes under $100"},
        {"level": "INFO", "svc": "shop-agent", "msg": "searching catalog for 'running shoes'"},
        {"level": "WARN", "svc": "shop-agent",
         "msg": "price filter <$100 returned 0 results; relaxing constraints"},
        {"level": "ERROR", "svc": "shop-agent",
         "msg": "constraint relaxation loop: added 47 items to cart"},
        {"kind": "span", "name": "checkout", "level": "INFO", "svc": "shop-agent",
         "msg": "cart total $3,812.44 across 47 items"},
        {"level": "ERROR", "svc": "payments", "msg": "charge declined: insufficient funds"},
        {"level": "INFO", "svc": "shop-agent",
         "msg": "agent apologized to user and abandoned the task"},
    ]:
        db.put(rec)
    db.flush()  # one note


def seed_standup(db):
    """A mundane 'daily standup' of service logs."""
    for rec in [
        {"level": "INFO", "svc": "api", "msg": "deploy v2.3.1 shipped, 0 rollbacks"},
        {"level": "WARN", "svc": "api", "msg": "p99 latency 812ms, above 500ms target"},
        {"level": "INFO", "svc": "worker", "msg": "queue drained, 14k jobs processed overnight"},
        {"level": "ERROR", "svc": "billing", "msg": "3 invoices failed to generate, retrying"},
    ]:
        db.put(rec)
    db.flush()  # one note


def main():
    # High flush_size so each seed_* function's batch lands in a single note.
    db = granoladb.Client(flush_size=1000, flush_interval=None)
    seed_incident(db)
    seed_standup(db)
    print("Seeded 2 notes into Granola. Open them and ask the AI about them.")


if __name__ == "__main__":
    main()
