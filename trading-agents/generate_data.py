"""
Genera datos sintéticos de oro (OHLCV diario) para poder correr el proyecto
sin conexión a internet.

Los datos son FICTICIOS pero con comportamiento realista (tendencias, rangos,
volatilidad variable). Para datos REALES usa `fetch_data.py`.

Uso:
    python generate_data.py                # crea data/gold_sample.csv
    python generate_data.py --years 10     # 10 años de datos
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd


def generate_gold(years: int = 10, start: str = "2015-01-01", seed: int = 42,
                  start_price: float = 1180.0) -> pd.DataFrame:
    """Simula precios de oro con regímenes de tendencia y rango."""
    rng = np.random.default_rng(seed)
    n = years * 252  # días hábiles aproximados
    dates = pd.bdate_range(start=start, periods=n)

    # Deriva (drift) que cambia por "regímenes" para imitar tendencias y rangos.
    drift = np.zeros(n)
    i = 0
    while i < n:
        regime_len = rng.integers(40, 160)
        # tendencia alcista, bajista o lateral
        mu = rng.choice([0.0008, -0.0006, 0.0001, 0.0004], p=[0.35, 0.2, 0.25, 0.2])
        drift[i:i + regime_len] = mu
        i += regime_len

    # Volatilidad variable (clustering): paseo sobre la vol diaria.
    vol = np.zeros(n)
    v = 0.010
    for t in range(n):
        v = max(0.004, min(0.03, v + rng.normal(0, 0.0008)))
        vol[t] = v

    # Retornos log y precio de cierre.
    rets = drift + vol * rng.standard_normal(n)
    close = start_price * np.exp(np.cumsum(rets))

    # Deriva OHLC alrededor del cierre.
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1] * (1 + rng.normal(0, 0.002, n - 1))
    intraday = np.abs(rng.normal(0, 1, n)) * vol * close
    high = np.maximum(open_, close) + intraday * 0.6
    low = np.minimum(open_, close) - intraday * 0.6
    volume = rng.integers(80_000, 320_000, n)

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": open_.round(2),
            "High": high.round(2),
            "Low": low.round(2),
            "Close": close.round(2),
            "Volume": volume,
        }
    )
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera datos sintéticos de oro.")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/gold_sample.csv")
    args = ap.parse_args()

    df = generate_gold(years=args.years, seed=args.seed)
    df.to_csv(args.out, index=False)
    print(f"OK: {len(df)} filas escritas en {args.out}")
    print(df.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
