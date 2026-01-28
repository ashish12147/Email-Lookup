import os
from typing import Any, Dict, List

import requests
from flask import Flask, jsonify, render_template, request

# Application metadata
APP_TITLE = "IntelBase Lookup Web App"
INTELBASE_EMAIL_LOOKUP_URL = "https://api.intelbase.is/lookup/email"

# Load API key from environment variable; this should be set before running the app.
INTELBASE_API_KEY = os.getenv("INTELBASE_API_KEY")

# Create Flask app
app = Flask(__name__)


def _call_intelbase_email_lookup(email: str, include_data_breaches: bool = True, timeout_ms: int = 5000) -> Dict[str, Any]:
    """Make a request to the IntelBase email lookup API."""
    if not INTELBASE_API_KEY:
        raise RuntimeError(
            "Missing INTELBASE_API_KEY. Set it as an environment variable before running."
        )

    payload = {
        "email": email,
        "timeout_ms": int(timeout_ms),
        "include_data_breaches": bool(include_data_breaches),
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": INTELBASE_API_KEY,
    }
    # Timeout for requests library uses seconds; convert ms to seconds plus a small buffer
    req_timeout = max(1, int(timeout_ms) // 1000 + 3)
    response = requests.post(
        INTELBASE_EMAIL_LOOKUP_URL, json=payload, headers=headers, timeout=req_timeout
    )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = {"raw": response.text}
        raise RuntimeError(f"IntelBase error {response.status_code}: {detail}")
    return response.json()


def _minimize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert IntelBase response into a UI-friendly structure.

    The returned dict has keys:
      - email: the requested email if available
      - breach_count: number of breaches returned
      - breaches: list of breach summaries (each with name, date, verified, description)
      - cards: list of modules/accounts with title, subtitle, avatar, module key, and key-value fields
      - raw: the full original data (for debugging / view raw)
      - raw_keys: sorted list of top-level keys from the original data
    """
    ui: Dict[str, Any] = {
        "email": None,
        "breach_count": 0,
        "breaches": [],
        "cards": [],
        "raw": data,
        "raw_keys": sorted(list(data.keys())),
    }

    # Extract email identifier and accounts from the 'identifier' field if present
    identifier = data.get("identifier")
    if isinstance(identifier, dict):
        # Save email if provided directly
        ui["email"] = identifier.get("email") or None

        accounts = identifier.get("accounts", [])
        if isinstance(accounts, list):
            for item in accounts:
                if not isinstance(item, dict):
                    continue
                module = item.get("module") or {}
                mdata = item.get("data") or {}

                # Module key (e.g., 'github', 'google', 'domain')
                module_key = module.get("name") or module.get("id") or ""

                # Title and subtitle for the card
                title = module.get("name_formatted") or module.get("name") or "Module"
                subtitle = module.get("domain") or ""

                # Avatar/icon URL
                avatar = (
                    mdata.get("avatar_url")
                    or mdata.get("profile_image")
                    or mdata.get("image")
                    or ""
                )

                # Collect key-value fields specific to module type
                fields: List[Dict[str, Any]] = []

                def add_field(label: str, value: Any) -> None:
                    if value is None or value == "" or value == [] or value == {}:
                        return
                    fields.append({"label": label, "value": value})

                # Populate fields based on known module keys
                mk = module_key.lower()
                if mk == "github":
                    add_field("Username", mdata.get("username"))
                    add_field("Profile", mdata.get("profile_url"))
                    add_field("ID", mdata.get("id"))
                elif mk == "google":
                    add_field("Profile", mdata.get("profile_url"))
                    add_field("Last seen", mdata.get("last_seen_date"))
                    add_field("Enterprise user", mdata.get("enterprise_user"))
                    add_field("Active apps", mdata.get("active_google_apps"))
                elif mk == "domain":
                    add_field("Provider", mdata.get("email_provider"))
                    add_field("Can receive email", mdata.get("can_receive_email"))
                    add_field("MX hosts", mdata.get("mx_hosts"))
                else:
                    # Generic fallback: display basic known fields
                    for key in ("username", "profile_url", "id"):
                        add_field(key.replace("_", " ").title(), mdata.get(key))

                ui["cards"].append(
                    {
                        "module": mk,
                        "title": title,
                        "subtitle": subtitle,
                        "avatar": avatar,
                        "fields": fields,
                    }
                )

    # Extract breach data
    breaches = data.get("data_breaches")
    if isinstance(breaches, list):
        ui["breach_count"] = len(breaches)
        for b in breaches:
            if not isinstance(b, dict):
                continue
            ui["breaches"].append(
                {
                    "name": b.get("name") or b.get("title") or b.get("source"),
                    "date": b.get("breach_date") or b.get("date"),
                    "verified": b.get("verified"),
                    "description": (b.get("description") or "")[:240],
                }
            )

    return ui


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html", title=APP_TITLE)


@app.post("/api/lookup")
def api_lookup() -> Any:
    """Handle lookup requests from the frontend."""
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    consent = body.get("consent", False)
    include_data_breaches = body.get("include_data_breaches", True)
    timeout_ms = int(body.get("timeout_ms", 5000))

    # Consent gate: require user to confirm they have permission to search this email
    if not consent:
        return jsonify({"ok": False, "error": "Consent required."}), 400

    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "Please enter a valid email."}), 400

    try:
        intel_data = _call_intelbase_email_lookup(
            email=email,
            include_data_breaches=include_data_breaches,
            timeout_ms=timeout_ms,
        )
        ui_data = _minimize_response(intel_data)
        return jsonify({"ok": True, "result": ui_data})
    except Exception as err:
        return jsonify({"ok": False, "error": str(err)}), 500


if __name__ == "__main__":
    # Run the Flask development server
    app.run(host="127.0.0.1", port=5000, debug=True)