# Self-Service API Key Generation — Design

**Status:** Approved — all open items signed off; ready for implementation plan
**Date:** 2026-06-05 (revised 2026-06-09)
**Author:** Tim Killenberger (with Claude)

## Problem

API keys are currently generated manually by a maintainer running
`scripts/create_api_key.py`. We want users to obtain a **read-only** key
directly from the website via a form, without manual intervention — doing
exactly what the script already does, just from the browser.

## Scope

- **In scope:** A public web form that mints a read-only API key on submit,
  reusing the existing mint logic.
- **Out of scope:** Rate limiting, abuse throttling, new collections/tables,
  accounts/sessions. (Read-only scopes are low-risk, so instant issue without
  limits is the accepted trade-off for simplicity.) An **email** is captured on
  the key document for contact/support, but it adds no new table and is not
  used for throttling.

## Current System (as explored)

- `scripts/create_api_key.py` mints a token with `secrets.token_urlsafe(32)`,
  stores its SHA-256 hash in the `api_keys` collection with fields:
  `key_hash`, `owner`, `description`, `scopes`, `created_at`, `revoked`.
  It prints the raw token (and an obfuscated form) once.
- `modules/auth.py` authenticates requests by hashing the presented token and
  looking up the non-revoked hash in `api_keys`. Scopes gate each endpoint via
  `require_scope`.
- `api_keys` lives in the **admin** Mongo DB (see `db.py` `get_collection`);
  collection name from `Collection.API_KEYS`.
- Frontend: Flask + Jinja + Bootstrap 5, blueprint `web_bp` in
  `modules/routes/web/web.py`, templates under
  `modules/routes/web/templates/`, base layout `components/_base.html`.
- The web blueprint is **public** (only the API blueprints attach
  `require_api_key`), so a new web route needs no API key — correct for this.
- Read-only scopes: `read:market`, `read:market_archive`, `read:lootpool`,
  `read:raidpool`. Write scopes (`write:*`) allow injecting/polluting data and
  remain **manual-only**, never selectable from the website.

## Design

No new collections. The form writes the same document the script does, plus an
optional `email` field on the `api_keys` document (existing docs without it are
fine — it's a schemaless add, not a new table).

### 1. Shared mint helper (avoid drift)

Extract the mint logic into a small reusable function so the script and the
route can't diverge. Lightest option: keep it in
`scripts/create_api_key.py`, but the module currently runs
`get_collection(...)` at import time. To make it safely importable, move
`generate_and_store_key(owner, description, scopes, email=None)` (and the
`SELF_SERVICE_SCOPES` read-only allowlist) into a tiny module —
e.g. `modules/services/api_key_service.py` — and have the script import from
it. The body is unchanged from today's script aside from writing the optional
`email` field; the script keeps calling it without an email.

```python
SELF_SERVICE_SCOPES = [
    "read:market", "read:market_archive", "read:lootpool", "read:raidpool",
]

def generate_and_store_key(owner, description, scopes, email=None) -> str:
    # identical to the current script: token_urlsafe(32), sha256 hash,
    # insert_one({key_hash, owner, description, scopes, created_at, revoked,
    #             email})  # email only included when provided
    ...
```

### 2. Routes in `web.py` (public web blueprint)

- `GET /developer/api-key` → render the form.
- `POST /developer/api-key` → validate name present + valid email format +
  scopes ⊆ `SELF_SERVICE_SCOPES` (reject any non-read scope server-side, never
  trust the form), mint the key, re-render with the token shown **once** (copy
  button +
  "save this now, it won't be shown again" warning). On bad input, re-render
  with an inline error and preserved input.

### 3. Template `developer/api_key.html`

Extends `_base.html`, Bootstrap 5. Fields: **Name** (owner), **Email**,
**Description / intended use**, read-only **scope checkboxes**, plus a result
panel for the generated key.

### 4. Navigation

Add "API Key" as its own **top-level nav item** in `_base.html` (a standalone
`nav-item` link alongside Lootpool/Raidpool), not under the Tools dropdown.

## Error Handling

Friendly inline messages for missing name, invalid email, no scope selected,
and unexpected server errors. Form preserves user input on error.

## Known Limitation (flagged, not fixing)

No CSRF protection exists anywhere on the site (no `flask-wtf`; existing forms
are GET). The new POST form inherits this gap. Since keys are read-only and
there's no session to anchor a CSRF token to, this is left out of scope.

## Testing

- Unit (`api_key_service`): scope allowlist enforcement (write scopes
  rejected), minted-key hash retrievable like the script.
- Route: GET render, successful POST returns a token (and persists `email`),
  rejected POST (missing name / invalid email / non-read scope).

## Open Items (sign-off before implementation)

- [x] Route path `/developer/api-key` approved.
- [x] Nav: standalone top-level "API Key" item (not in Tools dropdown).
- [x] CSRF left out of scope — no session/cookies to forge against and keys are
      read-only, so there's nothing for a forged request to abuse.
- [x] Extract mint logic to `modules/services/api_key_service.py` — approved.

## Next Step

Once open items are signed off: invoke the writing-plans skill to produce the
implementation plan.
