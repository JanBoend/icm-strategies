# backtests/run_fvg.py
"""Run FVG backtest on QQQ. Requires data/QQQ_15m.csv or internet access."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from strategies.fvg import FVGStrategy
from metrics import full_report

print("FVG Strategy — QQQ 15-minute backtest")
print("Note: optimal parameters are not published. Defaults used here are illustrative.")

ticker = "QQQ"
raw = yf.download(ticker, start="2019-01-01", end="2024-12-31", interval="1h", progress=False)
htf = raw.resample("4h").last().dropna()

strat = FVGStrategy()
df    = strat.build_indicators(raw, htf)
equity, trades = strat.run_backtest(df)

if len(trades) > 0:
    report = full_report(equity, trades)
    print(f"\n  Ann return : {report['ann_return']:.1%}")
    print(f"  Sharpe     : {report['sharpe']:.2f}")
    print(f"  Max DD     : {report['max_drawdown']:.1%}")
    print(f"  Trades     : {report['n_trades']}")
    print(f"  Win rate   : {report['win_rate']:.1%}")
else:
    print("No trades generated with default (None) parameters.")
    print("Calibrate parameters on your own data to produce signals.")
