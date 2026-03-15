# Balance-sheet-playground

Tool for building toy trading-book balance sheets, replaying transactions through time,
and rendering snapshots in both CLI and notebooks.

## Features

- Python API and YAML scenario file input
- Timestamped postings and snapshot reconstruction
- OCP and mark-to-market PV by book
- Symbolic funding-rate formulas with numeric evaluation
- Shared CLI and notebook renderers with configurable representation profiles

## Quick start

```python
from decimal import Decimal

from balance_sheet_playground import Account, MarketData, Posting, RateExpression, Scenario, Transaction
from balance_sheet_playground.render import render_snapshot

market = MarketData("RUB")
market.set_fx("USD", "RUB", 80)
market.set_index("LIBOR", Decimal("0.035"))
market.set_quote("BOND1", 101)

scenario = Scenario(market_data=market)
scenario.add_account(Account(name="BOND1", book="BND", side="asset", currency="USD", carrying_price=100, market_key="BOND1", funding_rate=RateExpression.parse("7%")))
scenario.add_account(Account(name="USD_LOAN", book="BND", side="liability", currency="USD", funding_rate=RateExpression.parse("LIBOR + 1%")))
scenario.add_transaction(Transaction.create("2026-03-15T10:00:00", "Open", [Posting("BOND1", 100), Posting("USD_LOAN", 10000)]))

snapshot = scenario.snapshot("2026-03-15T12:00:00")
rendered = render_snapshot(snapshot)
print(rendered.text)
rendered
```

Use the CLI with:

```bash
python3 -m balance_sheet_playground example.yml --as-of 2026-03-15T12:00:00
```
