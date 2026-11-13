"""
Estrategias de gráfico (análisis técnico clásico) como agentes.

Cada una implementa una señal famosa de los libros de trading, para poder
probarlas con honestidad (backtest + fuera de muestra) y ver si de verdad
funcionan en el oro o son mito.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.indicators import bollinger, macd, sma
from .base import BaseAgent


class GoldenCross(BaseAgent):
    """
    Golden Cross / Death Cross: la señal más famosa.

    'Golden cross' = la media de 50 días cruza por encima de la de 200 (alcista).
    'Death cross' = la de 50 cruza por debajo de la de 200 (bajista).
    """

    name = "golden_cross"
    description = "Cruce de medias 50/200."

    def __init__(self, fast: int = 50, slow: int = 200, allow_short: bool = True):
        self.fast, self.slow, self.allow_short = fast, slow, allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast, slow = sma(df["Close"], self.fast), sma(df["Close"], self.slow)
        pos = pd.Series(0.0, index=df.index)
        pos[fast > slow] = 1.0
        pos[fast < slow] = -1.0 if self.allow_short else 0.0
        return pos.fillna(0.0)


class MACDCross(BaseAgent):
    """MACD: comprar cuando la línea MACD cruza por encima de su señal."""

    name = "macd"
    description = "Cruce de la línea MACD con su señal."

    def __init__(self, allow_short: bool = True):
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        macd_line, signal_line, _ = macd(df["Close"])
        pos = pd.Series(0.0, index=df.index)
        pos[macd_line > signal_line] = 1.0
        pos[macd_line < signal_line] = -1.0 if self.allow_short else 0.0
        return pos.fillna(0.0)


class BollingerBounce(BaseAgent):
    """
    Bandas de Bollinger (rebote): comprar al tocar la banda inferior
    (sobrevendido) y cerrar/vender al volver a la media o tocar la superior.
    """

    name = "bollinger"
    description = "Rebote en Bandas de Bollinger."

    def __init__(self, window: int = 20, k: float = 2.0, allow_short: bool = True):
        self.window, self.k, self.allow_short = window, k, allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["Close"]
        mid, upper, lower = bollinger(close, self.window, self.k)
        pos = pd.Series(np.nan, index=df.index)
        pos[close <= lower] = 1.0                      # toca banda inferior -> largo
        if self.allow_short:
            pos[close >= upper] = -1.0                 # toca banda superior -> corto
        # Cerrar al volver a la media.
        pos[(close >= mid) & (close.shift(1) < mid)] = 0.0
        pos[(close <= mid) & (close.shift(1) > mid)] = 0.0
        return pos.ffill().fillna(0.0)


class Engulfing(BaseAgent):
    """
    Patrón de velas envolvente (engulfing).

    Envolvente alcista: tras una vela bajista, una vela alcista cuyo cuerpo
    'engulle' al de la anterior -> señal de compra. La bajista, al revés.
    """

    name = "engulfing"
    description = "Patrón de velas envolvente (bullish/bearish engulfing)."

    def __init__(self, allow_short: bool = True):
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        o, c = df["Open"], df["Close"]
        po, pc = o.shift(1), c.shift(1)

        prev_bear = pc < po
        prev_bull = pc > po
        today_bull = c > o
        today_bear = c < o

        bull_engulf = prev_bear & today_bull & (o <= pc) & (c >= po)
        bear_engulf = prev_bull & today_bear & (o >= pc) & (c <= po)

        pos = pd.Series(np.nan, index=df.index)
        pos[bull_engulf] = 1.0
        pos[bear_engulf] = -1.0 if self.allow_short else 0.0
        return pos.ffill().fillna(0.0)
