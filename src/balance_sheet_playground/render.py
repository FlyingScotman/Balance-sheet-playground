from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from html import escape

from .market import MarketData
from .model import RenderProfile, Snapshot, SnapshotLine


@dataclass
class RenderedSnapshot:
    text: str
    html: str

    def __str__(self) -> str:
        return self.text

    def _repr_html_(self) -> str:
        return self.html


def render_snapshot(snapshot: Snapshot, profile: RenderProfile | None = None) -> RenderedSnapshot:
    active = profile or snapshot.profile
    return RenderedSnapshot(
        text=_render_text(snapshot, active),
        html=_render_html(snapshot, active),
    )


def _render_text(snapshot: Snapshot, profile: RenderProfile) -> str:
    blocks = [f"As of {snapshot.timestamp.isoformat(sep=' ', timespec='minutes')}"]
    for book in snapshot.books():
        lines = snapshot.book_lines(book)
        if not lines:
            continue
        width = 44 if profile.compact else 60
        blocks.append(book)
        blocks.append("-" * (width * 2 + 3))
        blocks.append(f"{'Assets'.ljust(width)} | Liabilities")
        assets = [line for line in lines if line.account.side == "asset"]
        liabilities = [line for line in lines if line.account.side == "liability"]
        max_rows = max(len(assets), len(liabilities))
        for index in range(max_rows):
            left = _line_text(assets[index], snapshot.market_data, profile) if index < len(assets) else ""
            right = _line_text(liabilities[index], snapshot.market_data, profile) if index < len(liabilities) else ""
            blocks.append(f"{left.ljust(width)} | {right}")
        if profile.show_ocp:
            blocks.append(f"OCP: {_format_amount_map(snapshot.ocp_by_book(book), profile)}")
        if profile.show_pv:
            pv = snapshot.pv_by_book(book)
            blocks.append(
                f"PV: {_format_money(pv, snapshot.market_data.reporting_currency, profile)}"
            )
        if profile.show_market_data:
            blocks.append(_text_market_data(snapshot.market_data, profile))
        if profile.show_funding:
            blocks.append(_text_funding(snapshot, book, profile))
    return "\n".join(blocks)


def _render_html(snapshot: Snapshot, profile: RenderProfile) -> str:
    sections = [f"<p><strong>As of</strong> {escape(snapshot.timestamp.isoformat(sep=' ', timespec='minutes'))}</p>"]
    for book in snapshot.books():
        lines = snapshot.book_lines(book)
        assets = [line for line in lines if line.account.side == "asset"]
        liabilities = [line for line in lines if line.account.side == "liability"]
        rows = max(len(assets), len(liabilities))
        table_rows = []
        for index in range(rows):
            left = escape(_line_text(assets[index], snapshot.market_data, profile)) if index < len(assets) else ""
            right = escape(_line_text(liabilities[index], snapshot.market_data, profile)) if index < len(liabilities) else ""
            table_rows.append(f"<tr><td>{left}</td><td>{right}</td></tr>")
        extras = []
        if profile.show_ocp:
            extras.append(f"<div><strong>OCP:</strong> {escape(_format_amount_map(snapshot.ocp_by_book(book), profile))}</div>")
        if profile.show_pv:
            extras.append(
                f"<div><strong>PV:</strong> {escape(_format_money(snapshot.pv_by_book(book), snapshot.market_data.reporting_currency, profile))}</div>"
            )
        if profile.show_market_data:
            extras.append(f"<div>{escape(_text_market_data(snapshot.market_data, profile))}</div>")
        if profile.show_funding:
            extras.append(f"<div>{escape(_text_funding(snapshot, book, profile))}</div>")
        sections.append(
            "".join(
                [
                    f"<h3>{escape(book)}</h3>",
                    "<table>",
                    "<thead><tr><th>Assets</th><th>Liabilities</th></tr></thead>",
                    "<tbody>",
                    *table_rows,
                    "</tbody></table>",
                    *extras,
                ]
            )
        )
    return "".join(sections)


def _line_text(line: SnapshotLine, market_data: MarketData, profile: RenderProfile) -> str:
    parts = [
        _format_money(line.quantity * line.market_price, line.account.currency, profile),
        line.account.name if profile.show_identifiers else line.account.description or line.account.name,
    ]
    if profile.show_formulas and line.account.funding_rate != line.account.funding_rate.__class__():
        parts.append(f"@ {line.account.funding_rate.format()}")
    if profile.show_metadata and line.account.metadata:
        meta = ", ".join(f"{key}={value}" for key, value in sorted(line.account.metadata.items()))
        parts.append(f"[{meta}]")
    return " ".join(parts)


def _text_market_data(market_data: MarketData, profile: RenderProfile) -> str:
    parts: list[str] = []
    for (base, quote), value in sorted(market_data.fx_display.items()):
        parts.append(f"{base}/{quote} {_decimal_text(value, profile.precision)}")
    for key, value in sorted(market_data.indices.items()):
        parts.append(f"{key} {_decimal_text(value * Decimal('100'), profile.precision)}%")
    for key, value in sorted(market_data.quotes.items()):
        parts.append(f"{key} {_decimal_text(value, profile.precision)}")
    return "Market data: " + (" | ".join(parts) if parts else "none")


def _text_funding(snapshot: Snapshot, book: str, profile: RenderProfile) -> str:
    funding = snapshot.funding_by_book(book)
    if not funding.by_currency:
        return "Funding: none"
    parts = []
    for currency, expr in funding.by_currency.items():
        segment = f"{currency} {expr.format(percent=False, precision=profile.precision)}"
        if currency in funding.numeric_by_currency:
            segment += f" = {_format_money(funding.numeric_by_currency[currency], currency, profile)}"
        parts.append(segment)
    if funding.translated_total is not None and funding.numeric_by_currency:
        parts.append(
            f"Total {_format_money(funding.translated_total, snapshot.market_data.reporting_currency, profile)}"
        )
    return "Funding: " + " | ".join(parts)


def _format_amount_map(values: dict[str, Decimal], profile: RenderProfile) -> str:
    if not values:
        return "flat"
    return ", ".join(
        f"{currency} {_decimal_text(amount / profile.amount_scale, profile.precision)}"
        for currency, amount in values.items()
    )


def _format_money(amount: Decimal, currency: str, profile: RenderProfile) -> str:
    scaled = amount / profile.amount_scale
    return f"{currency} {_decimal_text(scaled, profile.precision)}"


def _decimal_text(value: Decimal, precision: int) -> str:
    quant = Decimal(1).scaleb(-precision)
    text = f"{value.quantize(quant):f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text
