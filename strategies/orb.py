# strategies/orb.py
"""
Opening Range Breakout (ORB) Strategy.

Concept: The first N minutes of the US market session define a range.
A breakout above/below that range signals directional momentum.
We enter on the breakout with a stop at the opposite end of the range.

Session: NY open 13:30–14:30 UTC (range formation), entries 14:30–20:00 UTC.

Optimal parameters are not published. Calibrate on your own data.
"""
import pandas as pd
from strategies.base import BaseStrategy


class ORBStrategy(BaseStrategy):

    def default_params(self) -> dict:
        return {
            "initial_capital":  10_000,
            "risk_pct":         None,
            "reward_ratio":     None,
            "sl_buffer":        None,
            "range_minutes":    None,   # duration of opening range in minutes
            "session_end":      "20:00",
            "daily_loss_limit": None,
            "commission_pct":   0.0001,
            "slippage_pts":     2.0,
        }

    def build_indicators(self, ltf: pd.DataFrame, htf: pd.DataFrame = None) -> pd.DataFrame:
        df = ltf.copy()
        p  = self.params
        range_min = p["range_minutes"] or 60

        # ATR
        hl  = df["High"] - df["Low"]
        hpc = (df["High"] - df["Close"].shift()).abs()
        lpc = (df["Low"]  - df["Close"].shift()).abs()
        df["atr"] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()

        # Opening range high/low per day (first `range_min` minutes from 13:30)
        or_open = pd.Timestamp("13:30").time()
        or_end  = (pd.Timestamp("13:30") + pd.Timedelta(minutes=range_min)).time()

        or_data = df[
            (df.index.time >= or_open) & (df.index.time < or_end)
        ].groupby(df.index.date).agg(or_high=("High", "max"), or_low=("Low", "min"))

        or_data.index = pd.to_datetime(or_data.index)
        df["date"]    = df.index.normalize()
        df = df.join(or_data, on="date")

        df["in_session"] = (
            (df.index.time >= or_end) &
            (df.index.time <= pd.Timestamp(p["session_end"]).time())
        )

        return df.dropna()

    def run_backtest(self, df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        p        = self.params
        capital  = p["initial_capital"]
        risk_pct = p["risk_pct"]  or 0.005
        rr       = p["reward_ratio"] or 3.0
        sl_buf   = p["sl_buffer"] or 0.0
        daily_lim = p["daily_loss_limit"] or 0.06

        equity   = []
        trades   = []
        position = None
        day_start = capital
        traded_today = False
        last_date = None

        for ts, row in df.iterrows():
            if ts.date() != last_date:
                day_start    = capital
                traded_today = False
                last_date    = ts.date()

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

            if (position is None
                    and not traded_today
                    and row["in_session"]
                    and (capital - day_start) / day_start > -daily_lim):

                buf = (sl_buf or 0) * row["atr"]
                if row["Close"] > row["or_high"]:   # long breakout
                    sl  = row["or_low"] - buf
                    risk = row["Close"] - sl
                    if risk > 0:
                        tp = row["Close"] + rr * risk
                        position = {"entry": row["Close"], "sl": sl, "tp": tp,
                                    "risk_amt": capital * risk_pct, "side": "long",
                                    "entry_time": ts}
                        traded_today = True

            equity.append(capital)

        return pd.Series(equity, index=df.index[:len(equity)]), pd.DataFrame(trades)
