# walk_forward/wfo_runner.py
"""Run walk-forward holdout evaluation for a strategy and print summary."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from walk_forward import rolling_holdout, wfo_summary


def run_wfo(strategy_cls, ticker, start, end, params=None, train_bars=504, test_bars=126):
    print(f"Running WFO holdout: {strategy_cls.__name__} on {ticker}")

    raw = yf.download(ticker, start=start, end=end, interval="1h", progress=False)
    htf = raw.resample("4h").last().dropna()

    strat = strategy_cls(params)
    df    = strat.build_indicators(raw, htf)

    def run_fn(data, p):
        s = strategy_cls(p)
        return s.run_backtest(data)

    results = rolling_holdout(df, run_fn, train_bars=train_bars, test_bars=test_bars, params=strat.params)
    summary = wfo_summary(results)

    print(f"  Windows    : {summary.get('windows', 0)}")
    print(f"  Pass rate  : {summary.get('pass_rate', 0):.0%}")
    print(f"  Mean Sharpe: {summary.get('mean_sharpe', 0):.2f}")
    print(f"  Mean return: {summary.get('mean_ann_return', 0):.1%}")
    return summary


if __name__ == "__main__":
    from strategies.fvg import FVGStrategy
    run_wfo(FVGStrategy, "QQQ", "2018-01-01", "2024-12-31")
