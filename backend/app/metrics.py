from collections import deque
from dataclasses import dataclass, field
from statistics import pstdev

import numpy as np
import pandas as pd

from .models import MarketTick, MetricSnapshot


@dataclass
class SymbolWindow:
    prices: deque[float] = field(default_factory=deque)
    volumes: deque[float] = field(default_factory=deque)
    bid_sizes: deque[float] = field(default_factory=deque)
    ask_sizes: deque[float] = field(default_factory=deque)


class MetricsCalculator:
    def __init__(self, window_size: int = 60) -> None:
        self.window_size = window_size
        self.windows: dict[str, SymbolWindow] = {}

    def update(self, tick: MarketTick) -> MetricSnapshot:
        window = self.windows.setdefault(tick.symbol, SymbolWindow())
        self._append(window.prices, tick.price)
        self._append(window.volumes, tick.volume)
        self._append(window.bid_sizes, tick.bid_size)
        self._append(window.ask_sizes, tick.ask_size)

        return calculate_metrics(tick, list(window.prices), list(window.volumes), list(window.bid_sizes), list(window.ask_sizes))

    def _append(self, values: deque[float], value: float) -> None:
        values.append(value)
        if len(values) > self.window_size:
            values.popleft()


def calculate_metrics(
    tick: MarketTick,
    prices: list[float],
    volumes: list[float],
    bid_sizes: list[float],
    ask_sizes: list[float],
) -> MetricSnapshot:
    spread = max(tick.ask - tick.bid, 0.0)
    mid_price = (tick.ask + tick.bid) / 2 if tick.ask and tick.bid else tick.price
    spread_ratio = spread / mid_price if mid_price else 0.0

    price_series = pd.Series(prices, dtype="float64")
    returns = price_series.pct_change().dropna().to_numpy()
    volatility = float(np.std(returns)) if len(returns) else 0.0

    volume_sum = float(np.sum(volumes))
    vwap = float(np.dot(prices, volumes) / volume_sum) if volume_sum else tick.price

    rolling_price_change = ((prices[-1] - prices[0]) / prices[0]) if len(prices) > 1 and prices[0] else 0.0
    bid_depth = float(np.mean(bid_sizes)) if bid_sizes else tick.bid_size
    ask_depth = float(np.mean(ask_sizes)) if ask_sizes else tick.ask_size
    depth = bid_depth + ask_depth
    liquidity_score = max(0.0, min(100.0, (depth / 250.0) * 100.0 * (1.0 - min(spread_ratio * 50.0, 0.9))))

    latest_depth = tick.bid_size + tick.ask_size
    volume_imbalance = (tick.bid_size - tick.ask_size) / latest_depth if latest_depth else 0.0

    return MetricSnapshot(
        symbol=tick.symbol,
        price=tick.price,
        volatility=round(volatility, 6),
        spread=round(spread_ratio, 6),
        spread_bps=round(spread_ratio * 10_000, 2),
        vwap=round(vwap, 2),
        rolling_price_change=round(rolling_price_change, 6),
        liquidity_score=round(liquidity_score, 2),
        volume_imbalance=round(volume_imbalance, 6),
        source=tick.source,
        timestamp=tick.timestamp,
    )


def sample_volatility(prices: list[float]) -> float:
    if len(prices) < 2:
        return 0.0
    returns = [(prices[index] - prices[index - 1]) / prices[index - 1] for index in range(1, len(prices))]
    return pstdev(returns) if len(returns) > 1 else 0.0
