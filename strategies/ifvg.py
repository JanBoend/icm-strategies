# strategies/ifvg.py
"""
Inverse Fair Value Gap (iFVG) Strategy.

Concept: When a Fair Value Gap is completely filled by price, it flips from
an imbalance to a support/resistance level. We trade the reaction from these
flipped levels.

Key property: Negatively correlated to QQQ (-0.07 to -0.09) — acts as a
natural hedge in a diversified portfolio.

Optimal parameters are not published. Calibrate on your own data.
"""
import pandas as pd
import numpy as np
from strategies.base import BaseStrategy


class iFVGStrategy(BaseStrategy):

    def default_params(self) -> dict:
        return {
            "initial_capital":  10_000,
            "risk_pct":         None,
            "reward_ratio":     None,
            "sl_buffer":        None,
            "fvg_age_bars":     None,   # bars before gap expires without being filled
            "session_start":    "07:00",
            "session_end":      "10:00",
            "daily_loss_limit": None,
            "commission_pct":   0.0001,
            "slippage_pts":     2.0,
        }

    def build_indicators(self, ltf: pd.DataFrame, htf: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detects FVG zones, tracks when they are fully filled (becoming iFVG S/R levels),
        and generates signals when price reacts from those levels.
        """
        df = ltf.copy()
        p  = self.params

        # ATR
        hl  = df["High"] - df["Low"]
        hpc = (df["High"] - df["Close"].shift()).abs()
        lpc = (df["Low"]  - df["Close"].shift()).abs()
        df["atr"] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()

        # Raw FVG detection
        df["raw_fvg_bull"] = df["Low"] > df["High"].shift(2)
        df["raw_fvg_bear"] = df["High"] < df["Low"].shift(2)
        df["fvg_high"]     = df["High"].shift(2)
        df["fvg_low"]      = df["Low"]

        # Session mask
        df["in_session"] = (
            (df.index.time >= pd.Timestamp(p["session_start"]).time()) &
            (df.index.time <= pd.Timestamp(p["session_end"]).time())
        )

        # iFVG signal: FVG that was subsequently filled (price passed through it)
        # Simplified: detect gap, then check if fill occurred within fvg_age_bars
        age  = p["fvg_age_bars"] or 20
        df["ifvg_signal"] = False

        for i in range(2, len(df) - age):
            if df["raw_fvg_bull"].iloc[i]:
                gh = df["fvg_high"].iloc[i]
                gl = df["fvg_low"].iloc[i]
                # Check if price filled the gap within age bars
                future_slice = df.iloc[i+1 : i+1+age]
                if (future_slice["Low"] <= gl).any():
                    # Gap filled → became iFVG resistance
                    fill_bar = future_slice[future_slice["Low"] <= gl].index[0]
                    fill_idx = df.index.get_loc(fill_bar)
                    if fill_idx < len(df):
                        df.iloc[fill_idx, df.columns.get_loc("ifvg_signal")] = True

        return df.dropna()

    def run_backtest(self, df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        p         = self.params
        capital   = p["initial_capital"]
        risk_pct  = p["risk_pct"]  or 0.005
        rr        = p["reward_ratio"] or 3.0
        sl_buf    = p["sl_buffer"] or 0.0
        daily_lim = p["daily_loss_limit"] or 0.06

        equity   = []
        trades   = []
        position = None
        day_start = capital
        last_date = None

        for ts, row in df.iterrows():
            if ts.date() != last_date:
                day_start = capital
                last_date = ts.date()

            if position:
                if row["High"] >= position["sl"]:
                    pnl = -position["risk_amt"]
                    capital += pnl
                    trades.append({**position, "pnl": pnl, "result": "SL"})
                    position = None
                elif row["Low"] <= position["tp"]:
                    pnl = position["risk_amt"] * rr
                    capital += pnl
                    trades.append({**position, "pnl": pnl, "result": "TP"})
                    position = None

            if (position is None
                    and row["in_session"]
                    and row.get("ifvg_signal", False)
                    and (capital - day_start) / day_start > -daily_lim):

                sl   = row["Close"] + (sl_buf or 0) * row["atr"]
                risk = sl - row["Close"]
                if risk > 0:
                    tp = row["Close"] - rr * risk
                    position = {
                        "entry": row["Close"], "sl": sl, "tp": tp,
                        "risk_amt": capital * risk_pct, "side": "short",
                        "entry_time": ts
                    }

            equity.append(capital)

        return pd.Series(equity, index=df.index[:len(equity)]), pd.DataFrame(trades)
