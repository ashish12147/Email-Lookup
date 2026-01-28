from dotenv import load_dotenv
load_dotenv()

import os
from typing import Any, Dict

import requests
from flask import Flask, jsonify, render_template, request

APP_TITLE = "IntelBase Email Lookup (Learning Project)"
INTELBASE_API_URL = "https://api.intelbase.is/lookup/email"

# Do NOT hardcode secrets in real projects. Prefer an environment variable.
INTELBASE_API_KEY = "in_73fMpUhFwq8ZuC44GqtB"


app = Flask(__name__)


def _intelbase_lookup_email(
    email: str,
    include_data_breaches: bool = True,
    timeout_ms: int = 5000,
    exclude_modules=None,
) -> Dict[str, Any]:
    """Call IntelBase /lookup/email and return parsed JSON."""
    if not INTELBASE_API_KEY:
        raise RuntimeError(
            "Missing INTELBASE_API_KEY. Set it as an environment variable before running."
        )

    payload = {
        "email": email,
        "timeout_ms": int(timeout_ms),
        "include_data_breaches": bool(include_data_breaches),
    }
    if exclude_modules:
        payload["exclude_modules"] = exclude_modules

    headers = {
        "Content-Type": "application/json",
        "x-api-key": INTELBASE_API_KEY,
    }

    # requests timeout is in seconds; add a cushion
    requests_timeout = max(1, int(timeout_ms) // 1000 + 3)

    resp = requests.post(
        INTELBASE_API_URL,
        json=payload,
        headers=headers,
        timeout=requests_timeout,
    )

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"raw": resp.text}
        raise RuntimeError(f"IntelBase error {resp.status_code}: {detail}")

    return resp.json()


def _minimize_response(data):
    """
    Convert IntelBase response into a UI-friendly structure:
    - cards[] for each found account/module
    - breaches[] summary (if present)
    """
    ui = {
        "email": None,
        "breach_count": 0,
        "breaches": [],
        "cards": [],
        "raw": data,  # keep raw for "View raw" button in UI
    }

    # identifier can be a dict (as in your output)
    identifier = data.get("identifier")
    if isinstance(identifier, dict):
        # try best guess
        ui["email"] = identifier.get("email") or None

        accounts = identifier.get("accounts", [])
        if isinstance(accounts, list):
            for item in accounts:
                if not isinstance(item, dict):
                    continue

                module = item.get("module") or {}
                mdata = item.get("data") or {}

                name = module.get("name_formatted") or module.get("name") or "Module"
                domain = module.get("domain") or ""
                module_key = module.get("name") or ""

                # Build a clean “title” and “subtitle”
                title = name
                subtitle = domain if domain else ""

                # Pick avatar/icon if available
                avatar = (
                    mdata.get("avatar_url")
                    or mdata.get("profile_image")
                    or mdata.get("image")
                    or ""
                )

                # Build a small set of fields for each module type
                fields = []
                def add_field(label, value):
                    if value is None or value == "" or value == [] or value == {}:
                        return
                    fields.append({"label": label, "value": value})

                if module_key == "github":
                    add_field("Username", mdata.get("username"))
                    add_field("Profile", mdata.get("profile_url"))
                    add_field("GitHub ID", mdata.get("id"))
                elif module_key == "google":
                    add_field("Profile", mdata.get("profile_url"))
                    add_field("Last seen", mdata.get("last_seen_date"))
                    add_field("Enterprise user", mdata.get("enterprise_user"))
                    add_field("Active apps", mdata.get("active_google_apps"))
                elif module_key == "domain":
                    add_field("Provider", mdata.get("email_provider"))
                    add_field("Can receive email", mdata.get("can_receive_email"))
                    add_field("MX hosts", mdata.get("mx_hosts"))
                else:
                    # generic fallback: show a few safe keys
                    for k in ("username", "profile_url", "id"):
                        add_field(k.replace("_", " ").title(), mdata.get(k))

                ui["cards"].append({
                    "module": module_key,
                    "title": title,
                    "subtitle": subtitle,
                    "avatar": avatar,
                    "fields": fields
                })

    # breaches (if IntelBase includes them)
    breaches = data.get("data_breaches", [])
    if isinstance(breaches, list):
        ui["breach_count"] = len(breaches)
        for b in breaches:
            if not isinstance(b, dict):
                continue
            ui["breaches"].append({
                "name": b.get("name") or b.get("title"),
                "date": b.get("breach_date") or b.get("date"),
                "verified": b.get("verified"),
                "description": (b.get("description") or "")[:240],
            })

    # keep raw_keys if you want
    ui["raw_keys"] = sorted(list(data.keys()))
    return ui



@app.get("/")
def index():
    return render_template("index.html", title=APP_TITLE)


@app.post("/api/lookup")
def api_lookup():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()

    # Simple consent gate to discourage misuse.
    if not bool(body.get("consent")):
        return jsonify({"ok": False, "error": "Consent required."}), 400

    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "Please enter a valid email."}), 400

    include_data_breaches = bool(body.get("include_data_breaches", True))
    timeout_ms = int(body.get("timeout_ms", 5000))

    try:
        data = _intelbase_lookup_email(
            email=email,
            include_data_breaches=include_data_breaches,
            timeout_ms=timeout_ms,
        )
        return jsonify({"ok": True, "result": _minimize_response(data)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Run locally: python app.py
    # Open: http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
