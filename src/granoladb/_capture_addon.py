"""mitmproxy addon for `granoladb login --capture`.

On each Granola request, count it; when one carries a Bearer token, write that
token atomically to $GRANOLADB_TOKEN_OUT. Also write running counts to
$GRANOLADB_STATS_OUT so a failed capture can report where it broke (nothing
captured at all vs. captured-but-no-token).
"""
import json
import os

OUT = os.environ.get("GRANOLADB_TOKEN_OUT")
STATS = os.environ.get("GRANOLADB_STATS_OUT")
HOSTS = os.environ.get("GRANOLADB_HOSTS_OUT")

_counts = {"reqs": 0, "bearer": 0}
_seen = []


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)


def request(flow):
    _counts["reqs"] += 1
    auth = flow.request.headers.get("Authorization", "")
    has_bearer = auth.lower().startswith("bearer ")
    if has_bearer:
        _counts["bearer"] += 1
        if OUT:
            _atomic_write(OUT, auth.split(" ", 1)[1])
    if STATS:
        try:
            _atomic_write(STATS, json.dumps(_counts))
        except OSError:
            pass
    if HOSTS:
        # host + path only (no query string, no header values)
        mark = "AUTH " if has_bearer else "     "
        _seen.append(f"{mark}{flow.request.method} {flow.request.host}{flow.request.path.split('?')[0]}")
        try:
            _atomic_write(HOSTS, "\n".join(_seen[-40:]))
        except OSError:
            pass
