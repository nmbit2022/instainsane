"""Carga de datos OHLCV desde CSV."""
from __future__ import annotations

import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """
    Carga un CSV con columnas Date, Open, High, Low, Close, Volume.

    Acepta también el formato que descarga yfinance (columna 'Date' o índice
    de fechas). Devuelve un DataFrame ordenado por fecha y con índice de fecha.
    """
    df = pd.read_csv(path)

    # Buscar la columna de fecha.
    date_col = next((c for c in df.columns if c.lower() in ("date", "datetime", "time")), None)
    if date_col is None:
        raise ValueError(f"No encontré columna de fecha en {path}. Columnas: {list(df.columns)}")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).set_index(date_col)

    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas {missing} en {path}.")
    if "Volume" not in df.columns:
        df["Volume"] = 0

    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    df = df.dropna(subset=["Close"])
    return df
