# GranolaDB

> The database that runs on your meeting notes.

Stop paying for S3, CloudWatch, and Datadog. GranolaDB stores your logs and agent
traces in [Granola](https://granola.ai) — the AI meeting-notes app — as meeting
notes. Infinitely scalable*. Fully searchable**. Your traces finally get an AI
summary.

> [!NOTE]
> **Satire.** GranolaDB is a joke — not affiliated with Granola, and not meant for
> production or any real data. It runs locally on your own account. We're open to
> collaborating with Granola ([@meetgranola](https://x.com/meetgranola)).

## Install

```bash
pip install granoladb            # core
pip install granoladb[otel]      # + OpenTelemetry span exporter
pip install granoladb[capture]   # + `granoladb login --capture` (macOS)
```

Then get your Granola access token. On macOS, GranolaDB grabs it for you:

```bash
granoladb login --capture
```

This intercepts your own Granola app's traffic (via mitmproxy's local mode) and
lifts the `Authorization: Bearer` token out of it — because Granola encrypts the
token on disk and its network client ignores every proxy, so there's genuinely no
politer way to get it. You'll approve a one-time macOS network-extension prompt,
then click around a couple of notes so the app makes a request. Yes: **GranolaDB
MITMs your own Granola to obtain a token Granola won't hand out.** That is the joke,
and it is load-bearing.

The token is a short-lived session JWT (expires in a few hours) — rerun `--capture`
when it does. Or, if you have a token another way, cache it directly:

```bash
granoladb login <YOUR_TOKEN>     # store it (OS keychain)
export GRANOLA_TOKEN="..."       # or per-shell, nothing stored
granoladb logout                 # forget the stored token
```

(There's also an experimental `granoladb login --auto` that tries to decrypt the
token straight from the app's local store, but Granola's on-disk crypto changes
often, so don't count on it.)

### Exactly how `--capture` works (no hidden magic)

We think you should know precisely what this does before running it:

1. It launches **mitmproxy in "local mode"** pointed at the **Granola process** only.
   mitmproxy installs a **macOS network extension** ("Mitmproxy Redirector") that you
   approve once — it reroutes *only Granola's* traffic through mitmproxy.
2. **Why intercept at all:** Granola encrypts the token on disk and its API client
   ignores every proxy (system, env, VPN) — it even disables remote debugging — so
   there is no file to read or setting to flip. Intercepting the app's own traffic
   is the only way to obtain it.
3. **What it reads:** `--capture` first **asks for your confirmation**, then
   temporarily **trusts mitmproxy's certificate** (sudo) so Granola's TLS can be
   decrypted, **restarts Granola** so its authenticated startup sync fires, reads
   the `Authorization: Bearer <token>` header off that request, and extracts
   **only** that value (via a mitmproxy addon, written to a local file
   atomically). The redirector is scoped to the Granola process only, and the
   certificate trust added by capture is **removed when capture finishes**. If
   Granola does not quit when requested, close it fully and rerun capture so the
   startup sync occurs.
4. **Where it goes:** stored **locally only** — in your **OS keychain** (macOS
   Keychain / Windows Credential Manager / Freedesktop Secret Service) via the
   `keyring` library. If no keychain backend exists, it falls back to a `0600` file
   at `~/.granoladb/token` and tells you it did so. **Nothing is sent anywhere.**
   The mitmproxy process and its temporary capture file are torn down immediately.
5. **What the token is:** your own short-lived Granola **session JWT** — not your
   password, not a refresh token. `granoladb logout` deletes it.

The whole capture flow is in [`src/granoladb/capture_macos.py`](src/granoladb/capture_macos.py)
and storage is in [`src/granoladb/auth.py`](src/granoladb/auth.py) — read them.

## Quickstart

```python
import logging, granoladb

logging.getLogger().addHandler(granoladb.GranolaHandler())
logging.error("payment failed")   # this is now a meeting
```

```python
from granoladb import Client
db = Client()
db.put({"level": "ERROR", "msg": "payment failed", "svc": "api"})
print(db.query(contains="payment"))
```

## vs. legacy databases

| Feature            | Postgres | S3   | GranolaDB               |
| ------------------ | -------- | ---- | ----------------------- |
| Durability         | Yes      | Yes  | "probably"              |
| Query latency      | ms       | ms   | one flush interval      |
| AI summary of rows | No       | No   | **Yes**                 |
| Retention policy   | You set  | You  | when Granola archives it|
| Production ready   | Yes      | Yes  | **absolutely not**      |

\* limited by Granola's rate limits, which we call horizontal scaling.
\** limited by Granola's search bar.

## How it works

Records are batched into "meetings." Each batch becomes one Granola document — JSON
lines under a `GRANOLADB v1` marker, written via Granola's internal
`/v1/create-document` endpoint and read back via `/v1/get-documents`. Reads decode
the records out. This is a joke. Do not put anything real in it.

Auth: `granoladb login --capture` (see above) stores your token in the OS keychain,
or set `GRANOLA_TOKEN`. Set `GRANOLADB_DRY_RUN=1` to print calls instead of writing
to Granola.

## License

MIT
