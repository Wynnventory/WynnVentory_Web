# Self-Service API Keys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users generate a read-only API key from a public web form, reusing the exact mint logic the `create_api_key.py` script already uses.

**Architecture:** Extract the script's mint logic into a small importable service (`modules/services/api_key_service.py`) so the manual script and the new web route share one code path. Add a public `GET`/`POST /developer/api-key` route to the existing `web_bp` blueprint, a Bootstrap template, and a top-level nav link. No new collections — the form writes the same `api_keys` document the script does, plus an optional `email` field.

**Tech Stack:** Python 3, Flask (blueprint `web_bp`), Jinja2, Bootstrap 5, MongoDB (PyMongo), `unittest` + `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-06-05-self-service-api-keys-design.md`

---

## File Structure

- **Create** `modules/services/api_key_service.py` — single source of truth: `SELF_SERVICE_SCOPES` allowlist, `is_valid_email()`, `generate_and_store_key()`.
- **Modify** `scripts/create_api_key.py` — import `generate_and_store_key` from the service instead of defining it (kills drift; removes the import-time `get_collection` call).
- **Create** `modules/routes/web/templates/developer/api_key.html` — the form + result panel, extends `/components/_base.html`.
- **Modify** `modules/routes/web/web.py` — add the `GET`/`POST /developer/api-key` view.
- **Modify** `modules/routes/web/templates/components/_base.html` — add a top-level "API Key" nav item.
- **Create** `tests/test_api_key_service.py` — unit tests for the service.
- **Create** `tests/test_api_key_route.py` — route tests via a minimal Flask test app.

Run all tests with: `python -m pytest tests/ -v` (or `python -m unittest discover tests`).

---

### Task 1: API key service (mint logic + validation)

**Files:**
- Create: `modules/services/api_key_service.py`
- Test: `tests/test_api_key_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_key_service.py`:

```python
import hashlib
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.services import api_key_service


class TestSelfServiceScopes(unittest.TestCase):
    def test_only_read_scopes_are_self_serviceable(self):
        # No write scope may ever appear in the self-service allowlist.
        self.assertTrue(all(s.startswith("read:") for s in api_key_service.SELF_SERVICE_SCOPES))
        self.assertEqual(
            set(api_key_service.SELF_SERVICE_SCOPES),
            {"read:market", "read:market_archive", "read:lootpool", "read:raidpool"},
        )


class TestIsValidEmail(unittest.TestCase):
    def test_accepts_normal_address(self):
        self.assertTrue(api_key_service.is_valid_email("dev@example.com"))

    def test_rejects_blank(self):
        self.assertFalse(api_key_service.is_valid_email(""))
        self.assertFalse(api_key_service.is_valid_email(None))

    def test_rejects_missing_at_or_domain(self):
        self.assertFalse(api_key_service.is_valid_email("notanemail"))
        self.assertFalse(api_key_service.is_valid_email("foo@bar"))


class TestGenerateAndStoreKey(unittest.TestCase):
    def setUp(self):
        self.mock_collection = MagicMock()
        patcher = patch(
            'modules.services.api_key_service.get_collection',
            return_value=self.mock_collection,
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_returns_token_whose_hash_is_stored(self):
        token = api_key_service.generate_and_store_key(
            "alice", "my app", ["read:market"], email="alice@example.com"
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        self.mock_collection.insert_one.assert_called_once()
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["key_hash"], hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(doc["owner"], "alice")
        self.assertEqual(doc["description"], "my app")
        self.assertEqual(doc["scopes"], ["read:market"])
        self.assertEqual(doc["revoked"], False)
        self.assertIn("created_at", doc)

    def test_email_included_when_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"], email="bob@example.com")
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["email"], "bob@example.com")

    def test_email_omitted_when_not_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"])
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertNotIn("email", doc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api_key_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'modules.services.api_key_service'`

- [ ] **Step 3: Write the service**

Create `modules/services/api_key_service.py`:

```python
import hashlib
import re
import secrets
from datetime import datetime, timezone

from modules.db import get_collection
from modules.models.collection_types import Collection

# Read-only scopes a user may grant themselves from the website.
# Write scopes (write:*) stay manual-only and must never be added here.
SELF_SERVICE_SCOPES = [
    "read:market",
    "read:market_archive",
    "read:lootpool",
    "read:raidpool",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Loose, good-enough email shape check (no DNS / deliverability)."""
    return bool(email) and bool(_EMAIL_RE.match(email))


def generate_and_store_key(
    owner: str,
    description: str,
    scopes: list[str],
    email: str | None = None,
) -> str:
    """Mint a token, store its SHA-256 hash in api_keys, return the raw token.

    Single source of truth for both the manual script and the web route.
    The api_keys collection lives in the admin DB (see modules/db.get_collection).
    """
    raw_token = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    doc = {
        "key_hash": key_hash,
        "owner": owner,
        "description": description,
        "scopes": scopes,
        "created_at": datetime.now(timezone.utc),
        "revoked": False,
    }
    if email:
        doc["email"] = email

    get_collection(Collection.API_KEYS).insert_one(doc)
    return raw_token
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api_key_service.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add modules/services/api_key_service.py tests/test_api_key_service.py
git commit -m "feat: add api_key_service with shared mint logic and validation"
```

---

### Task 2: Refactor create_api_key.py to use the service

**Files:**
- Modify: `scripts/create_api_key.py`

- [ ] **Step 1: Rewrite the script to import the shared mint function**

Replace the entire contents of `scripts/create_api_key.py` with:

```python
import base64

from modules.services.api_key_service import generate_and_store_key

# #######################
# # API PARAMS
# #######################
OWNER = "name"
DESCRIPTION = "description"
SCOPES = [
    "read:lootpool",
    # "write:lootpool",
    "read:raidpool",
    # "write:raidpool",
    "read:market",
    # "write:market",
    "read:market_archive",
    # "write:market_archive"
]


def obfuscate_key(raw_key: str) -> str:
    mask = 0x5A
    b = raw_key.encode("utf-8")
    ob = bytes(byte ^ mask for byte in b)
    return base64.b64encode(ob).decode("utf-8")


if __name__ == "__main__":
    token = generate_and_store_key(OWNER, DESCRIPTION, SCOPES)
    print("\n=== NEW API KEY ===")
    print(f"Token:      {token}")
    print(f"Obfuscated: {obfuscate_key(token)}")
    print("===================\n")
```

- [ ] **Step 2: Verify the script imports without touching the DB at import time**

Run: `python -c "import scripts.create_api_key; print(scripts.create_api_key.generate_and_store_key.__module__)"`
Expected output: `modules.services.api_key_service`
(No Mongo connection attempt — `get_collection` is now only called inside the function, not at import.)

- [ ] **Step 3: Commit**

```bash
git add scripts/create_api_key.py
git commit -m "refactor: create_api_key.py imports shared api_key_service mint logic"
```

---

### Task 3: API key form template

**Files:**
- Create: `modules/routes/web/templates/developer/api_key.html`

This template is rendered by the route in Task 4 with these variables:
`scopes` (list of allowed scope strings, always passed), `error` (string or absent),
`token` (raw key string or absent, shown once on success), and `form` (dict with keys
`owner`, `email`, `description`, `selected_scopes` for repopulating inputs; absent on first GET).

- [ ] **Step 1: Create the template**

Create `modules/routes/web/templates/developer/api_key.html`:

```html
{% extends '/components/_base.html' %}

{% block title %}API Key{% endblock %}

{% block content %}
<div class="container py-4" style="max-width: 720px;">
    <h1 class="mb-3">Generate an API Key</h1>
    <p class="text-secondary">
        Create a read-only API key to access the Wynnventory API. The key is shown
        <strong>once</strong> — copy it somewhere safe before leaving the page.
    </p>

    {% if error %}
    <div class="alert alert-danger" role="alert">{{ error }}</div>
    {% endif %}

    {% if token %}
    <div class="alert alert-success" role="alert">
        <p class="mb-2"><strong>Your new API key (shown once — save it now):</strong></p>
        <div class="input-group">
            <input type="text" class="form-control font-monospace" id="generatedToken"
                   value="{{ token }}" readonly>
            <button class="btn btn-outline-secondary" type="button"
                    onclick="navigator.clipboard.writeText(document.getElementById('generatedToken').value)">
                Copy
            </button>
        </div>
        <p class="mt-2 mb-0 small">
            Send it as the <code>X-API-Key</code> header (or <code>Authorization: Api-Key &lt;token&gt;</code>).
        </p>
    </div>
    {% endif %}

    <form method="POST" action="{{ url_for('web.api_key') }}">
        <div class="mb-3">
            <label for="owner" class="form-label">Name</label>
            <input type="text" class="form-control" id="owner" name="owner"
                   value="{{ form.owner if form else '' }}" required>
        </div>

        <div class="mb-3">
            <label for="email" class="form-label">Email</label>
            <input type="email" class="form-control" id="email" name="email"
                   value="{{ form.email if form else '' }}" required>
            <div class="form-text">Used for contact about your key. Not shared.</div>
        </div>

        <div class="mb-3">
            <label for="description" class="form-label">Description / intended use</label>
            <textarea class="form-control" id="description" name="description"
                      rows="2">{{ form.description if form else '' }}</textarea>
        </div>

        <div class="mb-3">
            <label class="form-label">Scopes (read-only)</label>
            {% for scope in scopes %}
            <div class="form-check">
                <input class="form-check-input" type="checkbox" name="scopes"
                       value="{{ scope }}" id="scope_{{ loop.index }}"
                       {% if form and scope in form.selected_scopes %}checked{% endif %}>
                <label class="form-check-label" for="scope_{{ loop.index }}">{{ scope }}</label>
            </div>
            {% endfor %}
        </div>

        <button type="submit" class="btn btn-primary">Generate Key</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add modules/routes/web/templates/developer/api_key.html
git commit -m "feat: add developer API key form template"
```

(The template is rendered/verified by the route tests in Task 4.)

---

### Task 4: API key route (GET form + POST mint)

**Files:**
- Modify: `modules/routes/web/web.py` (imports near top; new view alongside the other `@web_bp.route` views, e.g. after `emerald_calculator` around line 96)
- Test: `tests/test_api_key_route.py`

- [ ] **Step 1: Write the failing route tests**

Create `tests/test_api_key_route.py`:

```python
import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.routes.web.web import web_bp


def make_test_app():
    # web_bp carries its own template_folder, so registering it is enough to
    # render developer/api_key.html and the shared base template.
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(web_bp)
    return app


class TestApiKeyRoute(unittest.TestCase):
    def setUp(self):
        self.app = make_test_app()
        self.client = self.app.test_client()

    def test_get_renders_form_with_scopes(self):
        resp = self.client.get("/developer/api-key")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("read:market", body)
        self.assertIn("Generate an API Key", body)

    @patch("modules.routes.web.web.generate_and_store_key", return_value="TEST-TOKEN-123")
    def test_post_success_shows_token(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "description": "my app",
            "scopes": ["read:market", "read:lootpool"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("TEST-TOKEN-123", resp.get_data(as_text=True))
        mock_gen.assert_called_once_with(
            "alice", "my app", ["read:market", "read:lootpool"], email="alice@example.com"
        )

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_missing_name_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "",
            "email": "alice@example.com",
            "scopes": ["read:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please enter a name", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_invalid_email_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "not-an-email",
            "scopes": ["read:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("valid email", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_write_scope_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "scopes": ["write:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid scope", resp.get_data(as_text=True))
        mock_gen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api_key_route.py -v`
Expected: FAIL — GET returns 404 (route not defined) / `BuildError` for `web.api_key`.

- [ ] **Step 3: Add the service imports to web.py**

In `modules/routes/web/web.py`, add to the import block near the top (after the existing `from modules.services import ...` line at line 8):

```python
from modules.services.api_key_service import (
    SELF_SERVICE_SCOPES,
    generate_and_store_key,
    is_valid_email,
)
```

- [ ] **Step 4: Add the view function**

In `modules/routes/web/web.py`, add this view after the `emerald_calculator` view (around line 96):

```python
@web_bp.route("/developer/api-key", methods=["GET", "POST"])
def api_key():
    if request.method == "GET":
        return render_template("developer/api_key.html", scopes=SELF_SERVICE_SCOPES)

    owner = (request.form.get("owner") or "").strip()
    email = (request.form.get("email") or "").strip()
    description = (request.form.get("description") or "").strip()
    selected_scopes = request.form.getlist("scopes")

    form = {
        "owner": owner,
        "email": email,
        "description": description,
        "selected_scopes": selected_scopes,
    }

    def reject(message):
        return render_template(
            "developer/api_key.html",
            scopes=SELF_SERVICE_SCOPES,
            error=message,
            form=form,
        )

    if not owner:
        return reject("Please enter a name.")
    if not is_valid_email(email):
        return reject("Please enter a valid email address.")
    if not selected_scopes:
        return reject("Please select at least one scope.")
    if any(scope not in SELF_SERVICE_SCOPES for scope in selected_scopes):
        return reject("Invalid scope selected.")

    token = generate_and_store_key(owner, description, selected_scopes, email=email)
    return render_template(
        "developer/api_key.html",
        scopes=SELF_SERVICE_SCOPES,
        token=token,
        form=form,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_api_key_route.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add modules/routes/web/web.py tests/test_api_key_route.py
git commit -m "feat: add /developer/api-key route for self-service API keys"
```

---

### Task 5: Add the top-level nav link

**Files:**
- Modify: `modules/routes/web/templates/components/_base.html` (after the Tools `<li>` that closes at line 114, before `</ul>` at line 115)

- [ ] **Step 1: Add the nav item**

In `modules/routes/web/templates/components/_base.html`, insert this standalone nav item immediately after the closing `</li>` of the Tools group (line 114) and before `</ul>` (line 115):

```html
                <!-- API Key (standalone) -->
                <li class="nav-item nav-group">
                    <a class="nav-link" href="{{ url_for('web.api_key') }}">
                        <i class="icon-minecraft icon-minecraft-tripwire-hook"></i>
                        <span>API Key</span>
                    </a>
                </li>
```

- [ ] **Step 2: Verify the navbar still renders (the API key page includes the navbar via base)**

Run: `python -m pytest tests/test_api_key_route.py::TestApiKeyRoute::test_get_renders_form_with_scopes -v`
Expected: PASS (rendering the page exercises `_base.html`; a bad `url_for` or template syntax error would fail this test).

- [ ] **Step 3: Commit**

```bash
git add modules/routes/web/templates/components/_base.html
git commit -m "feat: add API Key link to navbar"
```

---

### Task 6: Full suite green

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS, including the pre-existing suite.

- [ ] **Step 2: Manual smoke check (optional, requires DB env vars)**

Start the app and visit `/developer/api-key`, submit the form with a valid email and one read scope, confirm a token is shown once. Confirm a `write:*` value submitted manually is rejected.

---

## Notes / Out of Scope (from spec)

- **No rate limiting**, no new collections/tables. Read-only keys are low-risk, so instant issue is acceptable.
- **No CSRF token** — there is no session/cookie to forge against and keys are read-only, so a forged submit has nothing to abuse. Site-wide gap, left as-is.
- The `email` field is a schemaless add to `api_keys`; existing documents without it remain valid.
