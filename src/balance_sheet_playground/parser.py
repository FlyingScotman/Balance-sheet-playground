from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import yaml

from .expressions import RateExpression
from .market import MarketData
from .model import Account, Posting, RenderProfile, Scenario, Transaction


def load_scenario(path: str | Path) -> Scenario:
    data = yaml.safe_load(Path(path).read_text()) or {}
    market_raw = data.get("market_data", {})
    scenario = Scenario(
        market_data=_load_market_data(market_raw),
        render_profile=_load_render_profile(data.get("render_profile", {})),
    )
    for raw in data.get("accounts", []):
        scenario.add_account(_load_account(raw))
    for raw in data.get("transactions", []):
        scenario.add_transaction(_load_transaction(raw))
    return scenario


def _load_market_data(raw: dict) -> MarketData:
    market = MarketData(raw.get("reporting_currency", "USD"))
    for pair, value in (raw.get("fx_rates") or {}).items():
        base, quote = pair.split("/")
        market.set_fx(base, quote, value)
    for key, value in (raw.get("quotes") or {}).items():
        market.set_quote(key, value)
    for key, value in (raw.get("indices") or {}).items():
        market.set_index(key, value)
    return market


def _load_render_profile(raw: dict) -> RenderProfile:
    if not raw:
        return RenderProfile()
    values = dict(raw)
    if "amount_scale" in values:
        values["amount_scale"] = Decimal(str(values["amount_scale"]))
    return RenderProfile(**values)


def _load_account(raw: dict) -> Account:
    return Account(
        name=raw["name"],
        book=raw["book"],
        side=raw["side"],
        currency=raw["currency"],
        quantity_kind=raw.get("quantity_kind", "units"),
        carrying_price=Decimal(str(raw.get("carrying_price", "1"))),
        market_key=raw.get("market_key"),
        funding_rate=RateExpression.parse(raw.get("funding_rate")),
        description=raw.get("description", ""),
        metadata=raw.get("metadata", {}),
    )


def _load_transaction(raw: dict) -> Transaction:
    timestamp = raw["timestamp"]
    if not isinstance(timestamp, datetime):
        timestamp = datetime.fromisoformat(str(timestamp))
    postings = [
        Posting(
            account=posting["account"],
            quantity=posting["quantity"],
            carrying_price=posting.get("carrying_price"),
            note=posting.get("note", ""),
        )
        for posting in raw.get("postings", [])
    ]
    return Transaction.create(timestamp, raw.get("description", ""), postings)
