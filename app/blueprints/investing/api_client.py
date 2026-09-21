"""Declarative registry of Investing API endpoints, plus the client that
calls them. Each Action describes one endpoint so the test-harness template
can render its form and the route can make the call without a handler per
endpoint (see routes.py)."""

import json
from dataclasses import dataclass, field

import requests
from flask import current_app


@dataclass
class Field:
    name: str
    label: str
    type: str = "text"  # text | number | date | select
    required: bool = False
    options: list[str] | None = None


@dataclass
class Action:
    id: str
    label: str
    method: str
    path: str
    auth: bool = True
    fields: list[Field] = field(default_factory=list)


ACTIONS = [
    Action(id="health", label="Health check", method="GET", path="/health", auth=False),
    Action(
        id="health_db",
        label="Health check (database)",
        method="GET",
        path="/health/db",
        auth=False,
    ),
    Action(
        id="portfolio",
        label="Get portfolio",
        method="GET",
        path="/portfolio",
        fields=[Field("as_of", "As of date (optional)", type="date")],
    ),
    Action(
        id="portfolio_history",
        label="Get portfolio history",
        method="GET",
        path="/portfolio/history",
        fields=[
            Field("start", "Start date", type="date", required=True),
            Field("end", "End date", type="date", required=True),
        ],
    ),
    Action(
        id="recommendations",
        label="Get recommendations",
        method="GET",
        path="/recommendations",
        fields=[Field("as_of", "As of date (optional)", type="date")],
    ),
    Action(
        id="contributions",
        label="Log a contribution",
        method="POST",
        path="/contributions",
        fields=[
            Field("amount", "Amount", type="number", required=True),
            Field("contributed_date", "Contributed date (optional)", type="date"),
            Field("note", "Note (optional)"),
        ],
    ),
    Action(
        id="trades_confirm",
        label="Confirm a trade",
        method="POST",
        path="/trades/confirm",
        fields=[
            Field("ticker", "Ticker", required=True),
            Field("side", "Side", type="select", options=["BUY", "SELL"], required=True),
            Field("shares", "Shares", type="number", required=True),
            Field("price", "Price", type="number", required=True),
            Field("trade_date", "Trade date (optional)", type="date"),
            Field("contribution_id", "Contribution ID (optional)", type="number"),
            Field("lot_id", "Lot ID (optional)", type="number"),
            Field("note", "Note (optional)"),
        ],
    ),
    Action(
        id="tax_summary",
        label="Get tax summary",
        method="GET",
        path="/tax-summary",
        fields=[Field("tax_year", "Tax year (optional)", type="number")],
    ),
]

_ACTIONS_BY_ID = {action.id: action for action in ACTIONS}


def get_action(action_id: str) -> Action | None:
    return _ACTIONS_BY_ID.get(action_id)


def call_action(action: Action, form) -> dict:
    """Make the actual HTTP call for an action, using field values pulled
    from a submitted form. Blank optional fields are omitted entirely
    rather than sent empty, since the API's optional params/fields expect
    to be absent, not empty strings, to fall back to their defaults."""
    base_url = current_app.config["INVESTING_API_URL"].rstrip("/")
    url = f"{base_url}{action.path}"

    headers = {}
    if action.auth:
        headers["X-API-Key"] = current_app.config.get("INVESTING_API_KEY") or ""

    values = {}
    for f in action.fields:
        raw = (form.get(f.name) or "").strip()
        if raw:
            values[f.name] = raw

    try:
        if action.method == "GET":
            response = requests.get(url, headers=headers, params=values, timeout=10)
        else:
            response = requests.post(url, headers=headers, json=values, timeout=10)
    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "error": f"Could not reach Investing API at {url}: {exc}",
            "body_json": None,
        }

    try:
        body = response.json()
    except ValueError:
        body = response.text

    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "error": None,
        "body_json": json.dumps(body, indent=2, default=str),
    }
