"""Indicadores técnicos usados por los agentes."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Media móvil simple."""
    return series.rolling(window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Media móvil exponencial."""
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Índice de fuerza relativa (0-100)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range: mide la volatilidad (rango) del precio."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def donchian(df: pd.DataFrame, window: int = 20) -> tuple[pd.Series, pd.Series]:
    """Canal de Donchian: máximo y mínimo de las últimas `window` barras previas."""
    upper = df["High"].shift(1).rolling(window, min_periods=window).max()
    lower = df["Low"].shift(1).rolling(window, min_periods=window).min()
    return upper, lower


def realized_vol(series: pd.Series, window: int = 20) -> pd.Series:
    """Volatilidad realizada anualizada a partir de retornos log."""
    log_ret = np.log(series / series.shift(1))
    return log_ret.rolling(window, min_periods=window).std() * np.sqrt(252)
