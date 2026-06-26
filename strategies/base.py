# strategies/base.py
"""Abstract base class for all ICM strategies."""
from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, params: dict = None):
        self.params = self.default_params()
        if params:
            self.params.update(params)

    @abstractmethod
    def default_params(self) -> dict:
        """Return dict of default parameters. Optimal values are not published."""
        raise NotImplementedError

    @abstractmethod
    def build_indicators(self, ltf: pd.DataFrame, htf: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def run_backtest(self, df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        raise NotImplementedError
