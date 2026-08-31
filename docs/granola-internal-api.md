# Granola internal API (reverse-engineered)

Source: strings + request wrapper extracted from the Granola macOS app bundle
(`/Applications/Granola.app/Contents/Resources/app.asar`, build dated 2026-08-26).
No live traffic capture was needed — the endpoints and request shape are in the
bundled JS. (A mitmproxy attempt captured nothing: Granola is Electron and Node
uses its own CA bundle, so a system-keychain-trusted mitmproxy cert is bypassed.)

## Base

`https://api.granola.ai`

## Request wrapper (from `api-*.js`)

```js
function z(client, path, { input, method, ... }) {
  fetch(getAPIEndpoint(path), {
    method: method ?? "POST",
    headers: { ...authHeaders, ...(input ? {"Content-Type": "application/json"} : {}) },
    body: input ? JSON.stringify(input) : null,
  })
}
```

- The `input` object is sent as the **raw JSON body** (no `{input: ...}` envelope).
- Auth header: **`Authorization: Bearer <accessToken>`**.

## Write (confirmed by live capture, 2026-08-28)

The desktop app creates a note in **two calls**: an empty skeleton, then a content
fill. GranolaDB mirrors this exactly.

**1. Resolve workspace** — `POST /v1/get-workspaces` with body `{}`. Response:
`{ "workspaces": [ { "workspace": { "workspace_id": "<uuid>", ... }, "role", "plan_type" } ] }`.
Use `workspaces[0].workspace.workspace_id`.

**2. Create empty document** — `POST /v1/create-document`. The primary key is `id`
(a client-generated uuid), **not** `document_id`. On create, `title`/`notes*` are
`null`; the app sends this skeleton (constant values observed):

```json
{
  "id": "<client uuid>",
  "created_at": "<iso>", "updated_at": "<iso>",
  "type": "meeting",
  "creation_source": "macOS",
  "meeting_end_count": 0,
  "public": false,
  "show_private_notes": false,
  "transcribe": true,
  "sharing_link_visibility": "public",
  "workspace_id": "<uuid from step 1>"
}
```

Response: `{ "id": "<id>" }`, status 200. (GranolaDB sends `transcribe: false` — it
never records audio.)

**3. Fill content** — `POST /v1/update-document`:

```json
{
  "id": "<id>", "title": "<title>",
  "notes": { "type": "doc", "content": [ { "type": "paragraph", "attrs": {"id": "<uuid>"},
             "content": [ {"type": "text", "text": "<line>"} ] }, ... ] },
  "notes_plain": "<body>", "notes_markdown": "<body>", "updated_at": "<iso>"
}
```

`notes` is a ProseMirror document (paragraph nodes with a uuid `id` + text). Setting
it makes the note **render in the editor and be readable by Granola's AI** — the
`notes_markdown`/`notes_plain` fields alone are invisible to both.

The app also sends `ydoc_state` (a Yjs CRDT). GranolaDB **does not**: as of 2026-09
Granola rejects a client-supplied `ydoc_state` with HTTP 400, and `notes` alone is
sufficient for rendering + AI. (Earlier builds accepted `ydoc_state`; this changed.)

`document_id` (seen 536× in the bundle) is the field name on *read/reference*
endpoints; the create/update primary key is `id`.

## Read

- `POST /v1/get-documents` — returns the caller's documents. (A `/v2/get-documents`
  also exists in older reverse-engineering notes.) Response is normalized in code
  by reading `docs`/`documents` and each doc's `notes_markdown`/`notes_plain`.

## Auth (decided: env token)

The app sends `Authorization: Bearer <accessToken>`. In this build the token is
**not** stored in plaintext:

- `cache-v6.json.enc` — encrypted via Electron safeStorage (macOS Keychain-derived
  key). Not JSON, not readable without the Keychain secret.
- Chromium `Cookies` DB — also safeStorage-encrypted on macOS.
- WorkOS AuthKit (`user_management/sessions`) is the identity provider.

Because there is no plaintext token on disk, **GranolaDB v1 takes the token from
the `GRANOLA_TOKEN` environment variable** and uses it as the Bearer token. No
WorkOS exchange and no `client_id` are needed — we reuse the app's existing access
token. (A future `granoladb login` could decrypt safeStorage for zero-config auth;
out of scope for v1.)

## Never commit token values

Only endpoint/field/key *names* are recorded here. No access token, refresh token,
or cookie value has been read into or written to this repo.
