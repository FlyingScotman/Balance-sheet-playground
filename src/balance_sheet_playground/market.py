from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .expressions import _to_decimal


@dataclass
class MarketData:
    reporting_currency: str
    fx_rates: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    fx_display: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    quotes: dict[str, Decimal] = field(default_factory=dict)
    indices: dict[str, Decimal] = field(default_factory=dict)

    def set_fx(self, base: str, quote: str, value: object) -> None:
        rate = _to_decimal(value)
        self.fx_rates[(base, quote)] = rate
        self.fx_display[(base, quote)] = rate
        if rate != 0:
            self.fx_rates[(quote, base)] = Decimal("1") / rate

    def get_fx(self, base: str, quote: str) -> Decimal:
        if base == quote:
            return Decimal("1")
        try:
            return self.fx_rates[(base, quote)]
        except KeyError as exc:
            raise KeyError(f"Missing FX rate {base}/{quote}") from exc

    def translate(self, amount: Decimal, base: str, quote: str) -> Decimal:
        return amount * self.get_fx(base, quote)

    def set_quote(self, key: str, value: object) -> None:
        self.quotes[key] = _to_decimal(value)

    def set_index(self, name: str, value: object) -> None:
        self.indices[name] = _to_decimal(value)
