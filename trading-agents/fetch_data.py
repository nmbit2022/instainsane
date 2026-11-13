"""
Descarga datos REALES de oro y los guarda en CSV.

Requiere conexión a internet (corre esto en tu máquina, no hace falta en el
entorno de la nube si está restringido). Prueba varias fuentes gratuitas.

Uso:
    python fetch_data.py                       # oro (GC=F) a data/gold.csv
    python fetch_data.py --symbol GLD          # ETF de oro
    python fetch_data.py --start 2010-01-01
    python fetch_data.py --source stooq        # fuente alternativa
"""
from __future__ import annotations

import argparse
import sys


def fetch_yfinance(symbol: str, start: str, end: str | None):
    import yfinance as yf

    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance no devolvió datos.")
    # Aplanar columnas MultiIndex si las hay.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    return df


def fetch_stooq(symbol: str):
    """Fuente alternativa: stooq.com (CSV directo). Para oro usa 'xauusd'."""
    import pandas as pd

    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)
    if df.empty or "Close" not in df.columns:
        raise RuntimeError(f"Stooq no devolvió datos para '{symbol}'.")
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def main() -> int:
    ap = argparse.ArgumentParser(description="Descarga datos reales de oro.")
    ap.add_argument("--symbol", default=None, help="Ticker (por defecto GC=F o xauusd).")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--source", choices=["yfinance", "stooq"], default="yfinance")
    ap.add_argument("--out", default="data/gold.csv")
    args = ap.parse_args()

    try:
        if args.source == "yfinance":
            symbol = args.symbol or "GC=F"
            df = fetch_yfinance(symbol, args.start, args.end)
        else:
            symbol = args.symbol or "xauusd"
            df = fetch_stooq(symbol)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR al descargar: {exc}", file=sys.stderr)
        print("Sugerencia: prueba --source stooq, o revisa tu conexión.", file=sys.stderr)
        return 1

    df.to_csv(args.out, index=False)
    print(f"OK: {len(df)} filas guardadas en {args.out}")
    print(df.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
