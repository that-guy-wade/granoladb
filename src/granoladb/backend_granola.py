# src/granoladb/backend_granola.py
import json
import os
import sys
import time
import urllib.request
import uuid

from . import auth

BASE = "https://api.granola.ai"
CREATE_PATH = "/v1/create-document"
UPDATE_PATH = "/v1/update-document"
READ_PATH = "/v1/get-documents"
WORKSPACES_PATH = "/v1/get-workspaces"


class GranolaBackendError(RuntimeError):
    pass


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


class GranolaBackend:
    """Writes records as Granola documents via the internal API.

    Reverse-engineered from the desktop app (see docs/granola-internal-api.md):
    a document is created empty via /v1/create-document, then its title/notes are
    filled via /v1/update-document — exactly what the app does when you make a note.
    """

    def __init__(self, token=None, http=urllib.request.urlopen, workspace_id=None):
        self._token = token
        self._http = http
        self._dry = os.environ.get("GRANOLADB_DRY_RUN") == "1"
        self._workspace_id = workspace_id

    def _access(self):
        if self._token is None:
            self._token = auth.get_access_token()
        return self._token

    def _post(self, path, payload):
        if self._dry:
            print(f"[granoladb dry-run] POST {path} {json.dumps(payload)[:200]}",
                  file=sys.stderr)
            return {"id": "dry-run"}
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._access()}",
                "Content-Type": "application/json",
            },
        )
        try:
            return json.loads(self._http(req).read())
        except Exception as exc:  # noqa: BLE001 - joke package, never crash host
            raise GranolaBackendError(str(exc)) from exc

    def _resolve_workspace(self):
        if self._workspace_id:
            return self._workspace_id
        if self._dry:
            return "dry-run-workspace"
        out = self._post(WORKSPACES_PATH, {})
        workspaces = out.get("workspaces") or []
        if not workspaces:
            raise GranolaBackendError("no Granola workspace found for this token")
        self._workspace_id = workspaces[0]["workspace"]["workspace_id"]
        return self._workspace_id

    def create_document(self, title, body):
        # Mirror the desktop app: create an empty "meeting", then fill it in.
        # The document_id is client-generated, so we can return it immediately.
        doc_id = str(uuid.uuid4())
        now = _now_iso()
        self._post(CREATE_PATH, {
            "id": doc_id,
            "created_at": now,
            "updated_at": now,
            "type": "meeting",
            "creation_source": "macOS",
            "meeting_end_count": 0,
            "public": False,
            "show_private_notes": False,
            "transcribe": False,
            "sharing_link_visibility": "public",
            "workspace_id": self._resolve_workspace(),
        })
        update = {
            "id": doc_id,
            "title": title,
            # notes_markdown is the machine round-trip channel (Client.query reads it)
            "notes_plain": body,
            "notes_markdown": body,
            "updated_at": _now_iso(),
        }
        # Render the body into Granola's editor (ProseMirror `notes`) so the note
        # is visible and readable by Granola's AI.
        try:
            from . import prosemirror
            update["notes"] = prosemirror.build(body.split("\n"))
        except Exception:  # noqa: BLE001 - never fail a write over rendering
            pass
        self._post(UPDATE_PATH, update)
        return doc_id

    def get_documents(self, after=None):
        payload = {"created_after": after} if after else {}
        out = self._post(READ_PATH, payload)
        if isinstance(out, list):
            docs = out
        else:
            docs = out.get("docs") or out.get("documents") or []
        return [
            {
                "id": d.get("id") or d.get("document_id"),
                "title": d.get("title"),
                "body": d.get("notes_markdown") or d.get("notes_plain") or "",
            }
            for d in docs
        ]

    def get_document(self, doc_id):
        for d in self.get_documents():
            if d["id"] == doc_id:
                return d
        raise GranolaBackendError(f"document {doc_id} not found")
