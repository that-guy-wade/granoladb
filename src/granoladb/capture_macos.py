"""Capture the Granola access token by intercepting the app's own traffic.

Granola's network client ignores every proxy (system, env, VPN), so the only way
to see its token is to capture the app's traffic at the OS level. mitmproxy's
`local` mode does exactly that via an approved macOS network extension.

This is macOS-only, needs `granoladb[capture]`, and grabs a short-lived session
token (it expires in a few hours — rerun when it does). Yes, this means GranolaDB
MITMs your own Granola to get a token Granola won't hand out. That's the joke.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from .auth import GranolaAuthError

WORKSPACES_URL = "https://api.granola.ai/v1/get-workspaces"


def _granola_pids():
    out = subprocess.run(["pgrep", "-i", "granola"], capture_output=True, text=True)
    return [p for p in out.stdout.split() if p.strip().isdigit()]


def _extension_waiting_for_approval():
    try:
        out = subprocess.run(
            ["systemextensionsctl", "list"], capture_output=True, text=True, timeout=10
        ).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False
    return "mitmproxy" in out and "waiting for user" in out


def _latest_bearer(flow_path):
    """Return the most recent Bearer token in the capture (local mode already
    scopes to Granola's processes, so any Bearer we see is Granola's)."""
    from mitmproxy.io import FlowReader
    token = None
    try:
        with open(flow_path, "rb") as fh:
            for flow in FlowReader(fh).stream():
                r = getattr(flow, "request", None)
                # local mode also yields DNS flows, whose request has no headers
                if r is None or not hasattr(r, "headers"):
                    continue
                auth = r.headers.get("Authorization") or ""
                if auth.lower().startswith("bearer "):
                    token = auth.split(" ", 1)[1]
    except (FileNotFoundError, ValueError):
        pass
    return token


def _token_is_valid(token):
    from .backend_granola import api_headers

    req = urllib.request.Request(
        WORKSPACES_URL, data=b"{}",
        headers=api_headers(token),
    )
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return isinstance(data, dict) and bool(data.get("workspaces"))
    except Exception:  # noqa: BLE001
        return False


# Process names to capture: the app plus its helper processes. Granola's authed
# api.granola.ai calls come from the "Granola Helper" NetworkService, so we must
# target it by name — that way it's caught the instant it spawns after a restart,
# before the startup burst (which carries the token) fires.
GRANOLA_PROCESS_NAMES = "Granola,Granola Helper"


def _ca_cert_path():
    return Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"


def _ca_is_trusted(cert):
    """True if the mitmproxy CA already validates against the system trust store."""
    return subprocess.run(
        ["security", "verify-cert", "-c", str(cert)],
        capture_output=True,
    ).returncode == 0


def _trust_ca(cert, out):
    """Add the mitmproxy CA to the System keychain as a trusted root (needs sudo)."""
    out("Trusting mitmproxy's certificate so Granola's TLS can be read "
        "(sudo — macOS will ask for your password)...")
    ok = subprocess.run(
        ["sudo", "security", "add-trusted-cert", "-d", "-r", "trustRoot",
         "-k", "/Library/Keychains/System.keychain", str(cert)],
    ).returncode == 0
    if not ok:
        raise GranolaAuthError("could not trust the mitmproxy certificate (sudo declined?)")


def _untrust_ca(cert):
    """Remove the trust we added, so mitmproxy can no longer intercept anything."""
    subprocess.run(["sudo", "security", "remove-trusted-cert", "-d", str(cert)],
                   capture_output=True)


def _wait_for_ca(timeout=8):
    cert = _ca_cert_path()
    for _ in range(int(timeout * 2)):
        if cert.exists():
            return cert
        time.sleep(0.5)
    return cert  # may not exist; caller handles


def _restart_granola(out):
    """Quit Granola fully and reopen it, so its authenticated startup sync fires."""
    out("Restarting Granola to trigger its sync (this reopens the app)...")
    subprocess.run(["osascript", "-e", 'quit app "Granola"'], capture_output=True)
    time.sleep(2)
    subprocess.Popen(["open", "-a", "Granola"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def capture_token(timeout=75, prompt=input, out=print, restart=True, confirm=True):
    """Capture, validate, and return a Granola access token. Raises on failure.

    The token only rides Granola's authenticated startup REST burst, so we attach
    mitmproxy by process NAME first (catching the NetworkService the moment it
    spawns), then restart Granola so that burst happens under capture. A mitmproxy
    addon writes the token to a sentinel file atomically.
    """
    if sys.platform != "darwin":
        raise GranolaAuthError("`--capture` is macOS-only (uses mitmproxy local mode)")
    try:
        import mitmproxy  # noqa: F401
    except ImportError:
        raise GranolaAuthError("install the capture extra first: pip install 'granoladb[capture]'")
    mitmdump = shutil.which("mitmdump") or str(Path(sys.executable).with_name("mitmdump"))
    if not Path(mitmdump).exists():
        raise GranolaAuthError("mitmdump not found; pip install 'granoladb[capture]'")

    if confirm:
        out(
            "\n`granoladb login --capture` needs your Granola token, which Granola\n"
            "encrypts on disk and won't expose through any proxy or API. The only way\n"
            "to get it is to read it off Granola's own network request. This will:\n\n"
            "  • run mitmproxy's official, code-signed redirector (a macOS network\n"
            "    extension), scoped to ONLY Granola — it cannot see your other traffic\n"
            "  • temporarily trust mitmproxy's certificate so Granola's TLS can be\n"
            "    read (sudo password), then REMOVE that trust as soon as it's done\n"
            "  • restart the Granola app to trigger its authenticated sync\n"
            "  • read the Authorization token from Granola's request to its own API\n"
            "  • store that token in your macOS Keychain, then shut everything down\n\n"
            "Everything happens locally. Nothing is sent anywhere. The certificate is\n"
            "trusted only for the few seconds of capture. Source:\n"
            "  granoladb/capture_macos.py\n"
        )
        answer = prompt("Continue? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            raise GranolaAuthError("cancelled")

    sentinel = tempfile.NamedTemporaryFile(suffix=".tok", delete=False).name
    stats_path = tempfile.NamedTemporaryFile(suffix=".stats", delete=False).name
    hosts_path = tempfile.NamedTemporaryFile(suffix=".hosts", delete=False).name
    os.unlink(sentinel)  # addon (re)creates it atomically when it sees the token
    addon = str(Path(__file__).with_name("_capture_addon.py"))
    env = dict(os.environ, GRANOLADB_TOKEN_OUT=sentinel,
               GRANOLADB_STATS_OUT=stats_path, GRANOLADB_HOSTS_OUT=hosts_path)
    proc = subprocess.Popen(
        [mitmdump, "--mode", f"local:{GRANOLA_PROCESS_NAMES}", "-q", "-s", addon],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )

    def _stats():
        try:
            return json.loads(open(stats_path).read())
        except (OSError, ValueError):
            return {"reqs": 0, "bearer": 0}

    ca_installed = False
    try:
        time.sleep(3)
        if _extension_waiting_for_approval():
            out("\nmacOS blocked the capture extension. Approve 'Mitmproxy Redirector' in\n"
                "System Settings > General > Login Items & Extensions > Network Extensions,\n"
                "then press Enter here.")
            prompt()
        # Granola must trust mitmproxy's CA or its TLS won't decrypt (0 requests).
        cert = _wait_for_ca()
        if cert.exists() and not _ca_is_trusted(cert):
            _trust_ca(cert, out)
            ca_installed = True
        # mitmproxy is now capturing by name; restarting Granola makes the fresh
        # NetworkService (and its token-bearing startup burst) appear under capture.
        if restart:
            _restart_granola(out)
        elif not _granola_pids():
            raise GranolaAuthError("Granola isn't running — open the Granola app first")
        out("Waiting for Granola's sync to carry the token...")
        deadline = time.time() + timeout
        nudged = False
        while time.time() < deadline:
            if os.path.exists(sentinel):
                token = open(sentinel).read().strip()
                if token and _token_is_valid(token):
                    return token
            if not nudged and time.time() > deadline - timeout * 0.4:
                out("Still waiting — click one of your EXISTING notes in Granola to help it along.")
                nudged = True
            time.sleep(1)
        s = _stats()
        if s["reqs"] == 0:
            hint = ("mitmproxy captured 0 Granola requests — the 'Mitmproxy Redirector' "
                    "extension is likely not approved (System Settings > General > Login "
                    "Items & Extensions > Network Extensions).")
        elif s["bearer"] == 0:
            hint = (f"mitmproxy saw {s['reqs']} Granola requests but none carried a token "
                    "(those were background/websocket traffic) — open an EXISTING note, "
                    "or force quit Granola and retry if it stays in the background.")
        else:
            hint = f"saw a token in {s['bearer']} request(s) but it didn't validate — try again."
        try:
            hosts = open(hosts_path).read().strip()
        except OSError:
            hosts = ""
        if hosts:
            out("\n[debug] requests mitmproxy captured from Granola:\n" + hosts + "\n")
        raise GranolaAuthError(f"no token captured. {hint}")
    finally:
        if ca_installed:
            out("Removing the temporary certificate trust...")
            _untrust_ca(_ca_cert_path())
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        for p in (sentinel, stats_path, hosts_path):
            try:
                os.unlink(p)
            except OSError:
                pass
