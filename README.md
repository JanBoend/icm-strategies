# icm-strategies

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

10 ICT-based systematic strategies across equities and FX. Walk-forward validated. Combined portfolio Sharpe 4.16.

---

## Performance

| Strategy | Instrument | Ann Return | Sharpe | Max DD | Trades | WFO Pass |
|---|---|---|---|---|---|---|
| FVG | QQQ | 15.94% | 1.02 | -15.63% | 668 | 13/16 |
| ORB | QQQ | 12.93% | 1.14 | -7.56% | 329 | 13/16 |
| AMD | QQQ | 19.74% | 1.36 | -8.2% | ~400 | 15/16 |
| AMD | EURUSD | 16.45% | 1.40 | -5.01% | — | — |
| ORB | EURUSD | 12.4% | 0.92 | -6.36% | — | — |
| FVG | EURUSD | 7.33% | 0.65 | -12.43% | — | — |
| iFVG | EURUSD | — | 1.80 | — | — | — |
| iFVG | GBPUSD | — | 1.07 | — | — | — |
| FVG | XAUUSD | 6.43% | 0.55 | -9.32% | — | — |
| **Portfolio** | **10-strategy** | **110% (2% risk)** | **4.16** | **-7.49%** | — | — |

Full results: [`results/performance_table.csv`](results/performance_table.csv)

---

## Strategies

### Fair Value Gap (FVG)

When institutional participants execute large orders, they create imbalances between candle highs and lows — price moves so quickly that no two-sided trading occurs in that zone. These Fair Value Gaps act as magnets: price often retraces to fill them before continuing in the original direction. This strategy identifies bullish FVGs during the NY session (13:30–20:00 UTC), filters by a 4H trend EMA, and enters long when price pulls back into the gap. A configurable ATR-based stop sits below the gap's lower boundary.

### Opening Range Breakout (ORB)

The first N minutes of the US equity session define a range as institutions and algorithms establish positions. A decisive breakout above or below this range signals directional commitment and often leads to sustained momentum. This strategy waits for the opening range to form, then enters on the first confirmed breakout with a stop at the opposite end of the range. The risk-reward is calibrated to let winners run while keeping losses compact. ORB is the key diversifier in the portfolio — it has low drawdown and low correlation to the other strategies.

### AMD (Accumulation–Manipulation–Distribution)

ICT's AMD model describes how institutional price delivery follows a consistent three-phase cycle within a session: price first accumulates in a tight range (building liquidity above and below), then briefly sweeps beyond the range to trigger retail stops (manipulation), and finally delivers strongly in the opposite direction (distribution). This strategy defines an overnight accumulation range, monitors for a stop-hunt sweep in the early session, and enters counter-trend after the sweep completes — targeting the distribution leg. During the 2022 bear market (QQQ -32%), the AMD strategy returned +45.91% — the stop-hunt reversal concept performs best during high-volatility trending conditions.

### Inverse Fair Value Gap (iFVG)

When a Fair Value Gap is completely filled by price rather than respected, it undergoes a polarity flip: the imbalance zone becomes a support/resistance level. This happens because the participants who were positioned at those levels have now been stopped out, creating a vacuum that future price action tests from the other side. This strategy detects filled FVGs, marks the fill point as an iFVG level, and trades the subsequent reaction — typically entering short from former bullish gaps. iFVG strategies show -0.07 to -0.09 correlation to QQQ — they act as a natural hedge, generating the strongest returns during equity market stress.

---

## Walk-Forward Validation

Each strategy was validated using a 16-window rolling holdout (504 bars in-sample, 126 bars out-of-sample). Pass rate = windows with positive OOS return. This tests whether the strategy generalizes or is simply curve-fit to historical data.

| Strategy | WFO Windows | Pass Rate | Mean OOS Sharpe |
|---|---|---|---|
| FVG (QQQ) | 16 | 81.25% (13/16) | 0.98 |
| ORB (QQQ) | 16 | 81.25% (13/16) | 1.30 |
| AMD (QQQ) | 16 | 93.75% (15/16) | 1.64 |

All three core strategies demonstrate robust out-of-sample performance with mean OOS Sharpe ratios near or above their in-sample values.

---

## 2022 Bear Market

During the 2022 bear market (QQQ -32%), the AMD strategy returned +45.91%. The stop-hunt reversal concept performs best during high-volatility trending conditions — exactly when long-only equity strategies suffer most. This makes AMD a natural diversifier against passive index exposure.

---

## Negative Correlation

iFVG strategies show -0.07 to -0.09 correlation to QQQ. They act as a natural hedge, generating the strongest returns during equity market stress. In the 10-strategy portfolio, this negative correlation is a primary driver of the Sharpe 4.16 result — it is not leverage, it is genuine diversification.

---

## Alpha Protection

Optimal parameters are not published. Strategy files expose all parameters as configurable constructor arguments with `None` defaults. The logic, session windows, and structural concepts are visible — but `sl_buffer`, `reward_ratio`, `fvg_age_bars`, and session hours all default to `None`. Calibrate on your own data using the walk-forward runner.

```python
# Example: strategy runs with None defaults (no signals generated)
strat = FVGStrategy()

# Calibrate your own parameters, then pass them in
strat = FVGStrategy(params={
    "sl_buffer": <your_value>,
    "reward_ratio": <your_value>,
    "fvg_age_bars": <your_value>,
})
```

---

## How to Run

```bash
pip install -r requirements.txt

# Run FVG backtest (illustrative — calibrate params for real results)
python backtests/run_fvg.py

# Run walk-forward validation
python walk_forward/wfo_runner.py
```

---

## Engine

Backtesting engine: [quant-engine](https://github.com/jmboend/quant-engine)

The `metrics.py` and `walk_forward.py` modules are copied from the engine repo and provide `full_report()`, `rolling_holdout()`, and `wfo_summary()`.
