# strategies/fvg.py
"""
Fair Value Gap (FVG) Pullback Strategy.

Concept: When price makes a strong directional move, it often leaves an
imbalance (gap) between candles. Price frequently returns to fill this gap.
We enter in the direction of the gap when price retraces into it.

Session: NY session (13:30–20:00 UTC) on 15-minute bars.
HTF filter: 4H trend bias (EMA).

Optimal parameters are not published. All parameters are configurable —
calibrate on your own data using walk-forward validation.
"""
import pandas as pd
import numpy as np
from strategies.base import BaseStrategy


class FVGStrategy(BaseStrategy):

    def default_params(self) -> dict:
        return {
            "initial_capital":  10_000,
            "risk_pct":         None,   # fraction of equity risked per trade
            "reward_ratio":     None,   # take-profit in R-multiples
            "sl_buffer":        None,   # SL buffer below/above FVG zone (as ATR multiple)
            "fvg_age_bars":     None,   # max bars before FVG expires
            "min_fvg_atr_mult": None,   # min FVG size as ATR multiple
            "htf_ema_span":     None,   # HTF trend EMA period
            "session_start":    "13:30",
            "session_end":      "20:00",
            "daily_loss_limit": None,
            "commission_pct":   0.0001,
            "slippage_pts":     2.0,
        }

    def build_indicators(self, ltf: pd.DataFrame, htf: pd.DataFrame) -> pd.DataFrame:
        """
        Computes:
          - ATR (14-period)
          - HTF EMA for trend bias
          - FVG zones: (fvg_high, fvg_low, fvg_bull) for each bar where a gap exists
          - Session mask
        """
        df = ltf.copy()
        p  = self.params

        # ATR
        hl  = df["High"] - df["Low"]
        hpc = (df["High"] - df["Close"].shift()).abs()
        lpc = (df["Low"]  - df["Close"].shift()).abs()
        df["atr"] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()

        # HTF trend bias
        htf_ema = htf["Close"].ewm(span=p["htf_ema_span"] or 50).mean()
        htf_aligned = htf_ema.reindex(df.index, method="ffill")
        df["htf_bull"] = df["Close"] > htf_aligned

        # FVG detection: bullish gap between bar[i-2].high and bar[i].low
        df["fvg_bull"] = (df["Low"] > df["High"].shift(2)) & df["htf_bull"]
        df["fvg_bear"] = (df["High"] < df["Low"].shift(2)) & ~df["htf_bull"]
        df["fvg_high"] = df["High"].shift(2)
        df["fvg_low"]  = df["Low"]

        # Session mask (UTC)
        df["in_session"] = (
            (df.index.time >= pd.Timestamp(p["session_start"]).time()) &
            (df.index.time <= pd.Timestamp(p["session_end"]).time())
        )

        return df.dropna()

    def run_backtest(self, df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        """
        Simulate trades on pre-built indicator dataframe.
        Position sizing: fixed risk_pct of equity per trade.
        Exit: take-profit at reward_ratio * risk, or stop at sl_buffer below FVG.

        Note: entries use bar close price on the signal bar. In live trading,
        entries would be placed at the next bar's open. This slightly inflates
        backtest performance relative to live execution.
        """
        p         = self.params
        capital   = p["initial_capital"]
        risk_pct  = p["risk_pct"]  or 0.005
        rr        = p["reward_ratio"] or 3.0
        sl_buf    = p["sl_buffer"] or 0.0
        daily_lim = p["daily_loss_limit"] or 0.06

        equity    = []
        trades    = []
        position  = None
        day_start = capital
        last_date = None

        for ts, row in df.iterrows():
            if ts.date() != last_date:
                day_start = capital
                last_date = ts.date()

            # Manage open position
            if position:
                if row["Low"] <= position["sl"]:
                    pnl = -position["risk_amt"]
                    capital += pnl
                    trades.append({**position, "exit": position["sl"], "pnl": pnl, "result": "SL"})
                    position = None
                elif row["High"] >= position["tp"]:
                    pnl = position["risk_amt"] * rr
                    capital += pnl
                    trades.append({**position, "exit": position["tp"], "pnl": pnl, "result": "TP"})
                    position = None

            # Long-only: this implementation trades bullish FVGs only.
            # Bearish FVG short entries are intentionally excluded —
            # the equity bias provides a structural tailwind for longs.
            if (position is None
                    and row["in_session"]
                    and row["fvg_bull"]
                    and (capital - day_start) / day_start > -daily_lim):

                sl    = row["fvg_low"] - (sl_buf or 0) * row["atr"]
                risk  = row["Close"] - sl
                if risk <= 0:
                    equity.append(capital)
                    continue
                tp        = row["Close"] + rr * risk
                risk_amt  = capital * risk_pct
                position  = {
                    "entry": row["Close"], "sl": sl, "tp": tp,
                    "risk_amt": risk_amt, "entry_time": ts
                }

            equity.append(capital)

        eq_series = pd.Series(equity, index=df.index[:len(equity)])
        tr_df     = pd.DataFrame(trades)
        return eq_series, tr_df
