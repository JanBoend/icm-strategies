# strategies/amd.py
"""
AMD (Accumulation–Manipulation–Distribution) / ICT Overnight Range Sweep.

Concept: Institutional price delivery follows a 3-phase cycle within a session:
  Accumulation — tight range, liquidity builds above/below
  Manipulation — brief stop hunt beyond the range
  Distribution — price delivers to the opposite side

We enter after the manipulation sweep, targeting the distribution leg.

Optimal parameters are not published. Calibrate on your own data.
"""
import pandas as pd
from strategies.base import BaseStrategy


class AMDStrategy(BaseStrategy):

    def default_params(self) -> dict:
        return {
            "initial_capital":      10_000,
            "risk_pct":             None,
            "reward_ratio":         None,
            "sl_buffer":            None,
            "sweep_window_start":   None,   # UTC hour when sweep window opens
            "sweep_window_end":     None,   # UTC hour when sweep window closes
            "entry_window_end":     None,   # UTC hour entries close
            "overnight_range_hours": None,  # hours used to define overnight range
            "daily_loss_limit":     None,
            "commission_pct":       0.0001,
            "slippage_pts":         2.0,
        }

    def build_indicators(self, ltf: pd.DataFrame, htf: pd.DataFrame = None) -> pd.DataFrame:
        df = ltf.copy()
        p  = self.params

        # ATR
        hl  = df["High"] - df["Low"]
        hpc = (df["High"] - df["Close"].shift()).abs()
        lpc = (df["Low"]  - df["Close"].shift()).abs()
        df["atr"] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()

        sw_start = p["sweep_window_start"] or 10
        or_hours  = p["overnight_range_hours"] or 8
        or_open   = (sw_start - or_hours) % 24

        on_mask = df.index.hour.isin(range(or_open, sw_start))
        on_range = df[on_mask].groupby(df[on_mask].index.date).agg(
            on_high=("High", "max"), on_low=("Low", "min")
        )
        on_range.index = pd.to_datetime(on_range.index)
        df["date"] = df.index.normalize()
        df = df.join(on_range, on="date")

        sw_end    = p["sweep_window_end"] or 13
        entry_end = p["entry_window_end"] or 17

        df["in_sweep_window"] = (
            (df.index.hour >= sw_start) & (df.index.hour < sw_end)
        )
        df["in_entry_window"] = (
            (df.index.hour >= sw_end) & (df.index.hour < entry_end)
        )

        return df.dropna()

    def run_backtest(self, df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        p         = self.params
        capital   = p["initial_capital"]
        risk_pct  = p["risk_pct"]  or 0.005
        rr        = p["reward_ratio"] or 3.0
        sl_buf    = p["sl_buffer"] or 0.0
        daily_lim = p["daily_loss_limit"] or 0.06

        equity      = []
        trades      = []
        position    = None
        swept_high  = False
        swept_low   = False
        day_start   = capital
        last_date   = None

        for ts, row in df.iterrows():
            if ts.date() != last_date:
                day_start  = capital
                swept_high = False
                swept_low  = False
                last_date  = ts.date()

            if position:
                if row["Low"] <= position["sl"]:
                    pnl = -position["risk_amt"]
                    capital += pnl
                    trades.append({**position, "pnl": pnl, "result": "SL"})
                    position = None
                elif row["High"] >= position["tp"]:
                    pnl = position["risk_amt"] * rr
                    capital += pnl
                    trades.append({**position, "pnl": pnl, "result": "TP"})
                    position = None

            if row["in_sweep_window"] and not pd.isna(row["on_high"]):
                if row["High"] > row["on_high"]:
                    swept_high = True
                if row["Low"] < row["on_low"]:
                    swept_low = True

            if (position is None
                    and row["in_entry_window"]
                    and (capital - day_start) / day_start > -daily_lim):

                buf = (sl_buf or 0) * row["atr"]
                if swept_high:
                    sl  = row["High"] + buf
                    risk = sl - row["Close"]
                    if risk > 0:
                        tp = row["Close"] - rr * risk
                        position = {"entry": row["Close"], "sl": sl, "tp": tp,
                                    "risk_amt": capital * risk_pct, "side": "short",
                                    "entry_time": ts}
                        swept_high = False
                elif swept_low:
                    sl  = row["Low"] - buf
                    risk = row["Close"] - sl
                    if risk > 0:
                        tp = row["Close"] + rr * risk
                        position = {"entry": row["Close"], "sl": sl, "tp": tp,
                                    "risk_amt": capital * risk_pct, "side": "long",
                                    "entry_time": ts}
                        swept_low = False

            equity.append(capital)

        return pd.Series(equity, index=df.index[:len(equity)]), pd.DataFrame(trades)
