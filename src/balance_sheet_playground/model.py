from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from .expressions import RateExpression, _to_decimal
from .market import MarketData


@dataclass(frozen=True)
class Account:
    name: str
    book: str
    side: str
    currency: str
    quantity_kind: str = "units"
    carrying_price: Decimal = Decimal("1")
    market_key: str | None = None
    funding_rate: RateExpression = field(default_factory=RateExpression)
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def market_price(self, market_data: MarketData) -> Decimal:
        if self.market_key and self.market_key in market_data.quotes:
            return market_data.quotes[self.market_key]
        return self.carrying_price


@dataclass(frozen=True)
class Posting:
    account: str
    quantity: Decimal
    carrying_price: Decimal | None = None
    note: str = ""

    def __init__(
        self,
        account: str,
        quantity: object,
        carrying_price: object | None = None,
        note: str = "",
    ) -> None:
        object.__setattr__(self, "account", account)
        object.__setattr__(self, "quantity", _to_decimal(quantity))
        if carrying_price is None:
            object.__setattr__(self, "carrying_price", None)
        else:
            object.__setattr__(self, "carrying_price", _to_decimal(carrying_price))
        object.__setattr__(self, "note", note)


@dataclass(frozen=True)
class Transaction:
    timestamp: datetime
    description: str
    postings: tuple[Posting, ...]

    @classmethod
    def create(
        cls, timestamp: datetime | str, description: str, postings: Iterable[Posting]
    ) -> "Transaction":
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(timestamp, description, tuple(postings))


@dataclass(frozen=True)
class RenderProfile:
    name: str = "default"
    show_market_data: bool = True
    show_funding: bool = True
    show_ocp: bool = True
    show_pv: bool = True
    show_formulas: bool = True
    show_identifiers: bool = True
    show_metadata: bool = False
    compact: bool = False
    amount_scale: Decimal = Decimal("1")
    precision: int = 2

    def merged(self, **overrides: object) -> "RenderProfile":
        return replace(self, **{k: v for k, v in overrides.items() if v is not None})


@dataclass
class FundingBreakdown:
    by_currency: dict[str, RateExpression] = field(default_factory=dict)
    numeric_by_currency: dict[str, Decimal] = field(default_factory=dict)
    translated_total: Decimal | None = None


@dataclass
class SnapshotLine:
    account: Account
    quantity: Decimal
    carrying_price: Decimal
    market_price: Decimal

    @property
    def signed_native_value(self) -> Decimal:
        sign = Decimal("1") if self.account.side == "asset" else Decimal("-1")
        return sign * self.quantity * self.market_price

    @property
    def carrying_native_value(self) -> Decimal:
        sign = Decimal("1") if self.account.side == "asset" else Decimal("-1")
        return sign * self.quantity * self.carrying_price


@dataclass
class Snapshot:
    timestamp: datetime
    lines: list[SnapshotLine]
    market_data: MarketData
    profile: RenderProfile

    def book_lines(self, book: str) -> list[SnapshotLine]:
        return [line for line in self.lines if line.account.book == book and line.quantity != 0]

    def books(self) -> list[str]:
        return sorted({line.account.book for line in self.lines if line.quantity != 0})

    def ocp_by_book(self, book: str) -> dict[str, Decimal]:
        exposures: dict[str, Decimal] = defaultdict(Decimal)
        for line in self.book_lines(book):
            exposures[line.account.currency] += line.signed_native_value
        return dict(sorted(exposures.items()))

    def pv_by_book(self, book: str) -> Decimal:
        total = Decimal("0")
        for line in self.book_lines(book):
            total += self.market_data.translate(
                line.signed_native_value,
                line.account.currency,
                self.market_data.reporting_currency,
            )
        return total

    def funding_by_book(self, book: str) -> FundingBreakdown:
        by_currency: dict[str, RateExpression] = defaultdict(RateExpression)
        numeric: dict[str, Decimal] = defaultdict(Decimal)
        translated_total = Decimal("0")
        for line in self.book_lines(book):
            if line.quantity == 0:
                continue
            sign = Decimal("1") if line.account.side == "asset" else Decimal("-1")
            notion = line.quantity * line.market_price
            expr = line.account.funding_rate * (sign * notion)
            by_currency[line.account.currency] = by_currency[line.account.currency] + expr
            try:
                amount = expr.evaluate(self.market_data.indices)
            except KeyError:
                continue
            numeric[line.account.currency] += amount
            translated_total += self.market_data.translate(
                amount, line.account.currency, self.market_data.reporting_currency
            )
        return FundingBreakdown(dict(sorted(by_currency.items())), dict(sorted(numeric.items())), translated_total)

    def render(self, profile: RenderProfile | None = None):
        from .render import render_snapshot

        active = profile or self.profile
        return render_snapshot(self, active)


@dataclass
class Scenario:
    accounts: dict[str, Account] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
    market_data: MarketData = field(default_factory=lambda: MarketData("USD"))
    render_profile: RenderProfile = field(default_factory=RenderProfile)

    def add_account(self, account: Account) -> None:
        self.accounts[account.name] = account

    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions.append(transaction)
        self.transactions.sort(key=lambda item: item.timestamp)

    def set_render_profile(self, profile: RenderProfile) -> None:
        self.render_profile = profile

    def snapshot(
        self, as_of: datetime | str | None = None, profile: RenderProfile | None = None
    ) -> Snapshot:
        if as_of is None:
            relevant = list(self.transactions)
            timestamp = relevant[-1].timestamp if relevant else datetime.min
        else:
            if isinstance(as_of, str):
                as_of = datetime.fromisoformat(as_of)
            relevant = [txn for txn in self.transactions if txn.timestamp <= as_of]
            timestamp = as_of

        quantities: dict[str, Decimal] = defaultdict(Decimal)
        carrying_prices: dict[str, Decimal] = {}
        for txn in relevant:
            for posting in txn.postings:
                if posting.account not in self.accounts:
                    raise KeyError(f"Unknown account: {posting.account}")
                quantities[posting.account] += posting.quantity
                if posting.carrying_price is not None:
                    carrying_prices[posting.account] = posting.carrying_price

        lines: list[SnapshotLine] = []
        for name, account in sorted(self.accounts.items()):
            qty = quantities.get(name, Decimal("0"))
            carrying_price = carrying_prices.get(name, account.carrying_price)
            lines.append(
                SnapshotLine(
                    account=account,
                    quantity=qty,
                    carrying_price=carrying_price,
                    market_price=account.market_price(self.market_data),
                )
            )
        return Snapshot(timestamp, lines, self.market_data, profile or self.render_profile)

    def render(self, as_of: datetime | str | None = None, profile: RenderProfile | None = None):
        return self.snapshot(as_of, profile=profile).render(profile)
