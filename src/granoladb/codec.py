import json

MARKER = "GRANOLADB v1"


def encode(records):
    """records: non-empty list[dict] -> (title, body)."""
    first = records[0]
    ts = first.get("_ts", "")
    level = first.get("level", "LOG")
    tag = first.get("svc") or first.get("logger") or ""
    title = f"[gdb] {ts} {level} {tag}".rstrip()
    lines = [MARKER, "```json"]
    for r in records:
        lines.append(json.dumps(r, separators=(",", ":"), sort_keys=True))
    lines.append("```")
    return title, "\n".join(lines)


def decode(body):
    """document body -> list[dict], or None if not a GranolaDB document."""
    if not body or MARKER not in body:
        return None
    records = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line == MARKER or line.startswith("```"):
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records
