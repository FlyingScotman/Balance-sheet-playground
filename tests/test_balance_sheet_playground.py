from __future__ import annotations

import tempfile
import textwrap
import unittest
from decimal import Decimal

from balance_sheet_playground.expressions import RateExpression
from balance_sheet_playground.market import MarketData
from balance_sheet_playground.model import Account, Posting, RenderProfile, Scenario, Transaction
from balance_sheet_playground.parser import load_scenario
from balance_sheet_playground.render import render_snapshot


class BalanceSheetPlaygroundTests(unittest.TestCase):
    def make_scenario(self) -> Scenario:
        market = MarketData("RUB")
        market.set_fx("USD", "RUB", Decimal("80"))
        market.set_index("LIBOR", Decimal("0.035"))
        scenario = Scenario(market_data=market)
        scenario.add_account(
            Account(
                name="BOND1",
                book="BND",
                side="asset",
                currency="USD",
                carrying_price=Decimal("100"),
                market_key="BOND1",
                funding_rate=RateExpression.parse("0.07"),
            )
        )
        scenario.add_account(
            Account(
                name="USD_LOAN",
                book="BND",
                side="liability",
                currency="USD",
                carrying_price=Decimal("1"),
                funding_rate=RateExpression.parse("LIBOR + 0.01"),
            )
        )
        scenario.market_data.set_quote("BOND1", Decimal("101"))
        scenario.add_transaction(
            Transaction.create(
                "2026-03-15T10:00:00",
                "Open",
                [Posting("BOND1", "100"), Posting("USD_LOAN", "10000")],
            )
        )
        return scenario

    def test_rate_expression_parse_and_evaluate(self) -> None:
        expr = RateExpression.parse("LIBOR + 2% - 0.5%")
        self.assertEqual(expr.coefficients["LIBOR"], Decimal("1"))
        self.assertEqual(expr.evaluate({"LIBOR": Decimal("0.035")}), Decimal("0.05"))

    def test_snapshot_ocp_and_pv(self) -> None:
        scenario = self.make_scenario()
        snapshot = scenario.snapshot("2026-03-15T12:00:00")
        self.assertEqual(snapshot.ocp_by_book("BND"), {"USD": Decimal("100")})
        self.assertEqual(snapshot.pv_by_book("BND"), Decimal("8000"))

    def test_funding_numeric_translation(self) -> None:
        scenario = self.make_scenario()
        snapshot = scenario.snapshot("2026-03-15T12:00:00")
        funding = snapshot.funding_by_book("BND")
        self.assertEqual(funding.numeric_by_currency["USD"], Decimal("257"))
        self.assertEqual(funding.translated_total, Decimal("20560"))

    def test_render_snapshot_text_and_html(self) -> None:
        scenario = self.make_scenario()
        rendered = render_snapshot(scenario.snapshot("2026-03-15T12:00:00"))
        self.assertIn("BND", rendered.text)
        self.assertIn("Funding:", rendered.text)
        self.assertIn("USD/RUB 80", rendered.text)
        self.assertIn("<table>", rendered.html)

    def test_render_profile_override(self) -> None:
        scenario = self.make_scenario()
        scenario.set_render_profile(RenderProfile(show_market_data=False, compact=True))
        rendered = scenario.render(
            "2026-03-15T12:00:00",
            profile=scenario.render_profile.merged(show_funding=False),
        )
        self.assertNotIn("Market data", rendered.text)
        self.assertNotIn("Funding:", rendered.text)

    def test_yaml_loader(self) -> None:
        raw = textwrap.dedent(
            """
            market_data:
              reporting_currency: RUB
              fx_rates:
                USD/RUB: 80
              indices:
                LIBOR: 0.035
              quotes:
                BOND1: 101
            render_profile:
              compact: true
            accounts:
              - name: BOND1
                book: BND
                side: asset
                currency: USD
                carrying_price: 100
                market_key: BOND1
                funding_rate: 7%
              - name: USD_LOAN
                book: BND
                side: liability
                currency: USD
                carrying_price: 1
                funding_rate: LIBOR + 1%
            transactions:
              - timestamp: 2026-03-15T10:00:00
                description: Open
                postings:
                  - account: BOND1
                    quantity: 100
                  - account: USD_LOAN
                    quantity: 10000
            """
        )
        with tempfile.NamedTemporaryFile("w+", suffix=".yml") as handle:
            handle.write(raw)
            handle.flush()
            scenario = load_scenario(handle.name)
        snapshot = scenario.snapshot("2026-03-15T12:00:00")
        self.assertTrue(snapshot.profile.compact)
        self.assertEqual(snapshot.pv_by_book("BND"), Decimal("8000"))


if __name__ == "__main__":
    unittest.main()
