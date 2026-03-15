from __future__ import annotations

import argparse

from .parser import load_scenario
from .render import render_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Balance sheet playground")
    parser.add_argument("scenario", help="Path to YAML scenario file")
    parser.add_argument("--as-of", dest="as_of", help="ISO timestamp for the snapshot")
    parser.add_argument("--hide-market-data", action="store_true")
    parser.add_argument("--hide-funding", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    profile = scenario.render_profile.merged(
        show_market_data=not args.hide_market_data,
        show_funding=not args.hide_funding,
        compact=args.compact or scenario.render_profile.compact,
    )
    snapshot = scenario.snapshot(args.as_of, profile=profile)
    print(render_snapshot(snapshot, profile).text)


if __name__ == "__main__":
    main()
