"""Validate the synthetic leveraged-ETF model against real ETF history.

Run from apps/api:  python -m scripts.validate_synthetic

Compares model daily returns (L x QQQ - costs) against real TQQQ/QLD returns
over their full overlap, and reports the extended coverage the backtests get.
"""

import asyncio

from app.services.market_data import (
    LEVERAGED_SPECS,
    extend_with_synthetic,
    fetch_provider_history,
    synthetic_overlap_report,
)

PROVIDER = "yahoo"


async def main() -> None:
    base_rows = await fetch_provider_history("QQQ", PROVIDER)
    print(f"QQQ history: {base_rows[0].date} .. {base_rows[-1].date} ({len(base_rows)} rows)")

    for symbol, spec in LEVERAGED_SPECS.items():
        real_rows = await fetch_provider_history(symbol, PROVIDER)
        report = synthetic_overlap_report(
            base_rows, real_rows, spec.leverage, spec.expense_ratio
        )
        merged, synthetic_until = extend_with_synthetic(
            base_rows, real_rows, spec.leverage, spec.expense_ratio
        )
        print(f"\n=== {symbol} (L={spec.leverage}) ===")
        print(f"real inception:       {real_rows[0].date}")
        print(f"extended start:       {merged[0].date}")
        print(f"synthetic until:      {synthetic_until}")
        for key, value in report.items():
            print(f"{key:28} {value}")


if __name__ == "__main__":
    asyncio.run(main())
