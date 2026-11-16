"""
Descarga datos INTRADÍA (velas de 1 hora) del oro, para el análisis de sesiones.

Yahoo solo da ~2 años de datos de 1 hora, suficiente para analizar en qué sesión
(Asia / Londres / Nueva York) se mueve más y más limpio el oro.

Uso:
    python fetch_intraday.py                    # oro (GC=F), 1h, ~2 años
    python fetch_intraday.py --symbol QQQ       # otro activo
    python fetch_intraday.py --interval 30m     # otra granularidad
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Descarga datos intradía.")
    ap.add_argument("--symbol", default="GC=F")
    ap.add_argument("--interval", default="60m", help="60m, 30m, 15m, 5m...")
    ap.add_argument("--period", default="730d", help="Yahoo: máx 730d para 1h.")
    ap.add_argument("--out", default="data/gold_1h.csv")
    args = ap.parse_args()

    try:
        import yfinance as yf

        df = yf.download(args.symbol, period=args.period, interval=args.interval,
                         progress=False, auto_adjust=False)
        if df is None or df.empty:
            raise RuntimeError("yfinance no devolvió datos intradía.")
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        # La 1ra columna es la fecha-hora (Datetime o Date).
        tcol = df.columns[0]
        df = df.rename(columns={tcol: "Datetime"})
        # Normalizar a UTC para que las sesiones sean comparables.
        df["Datetime"] = _to_utc(df["Datetime"])
        if "Volume" not in df.columns:
            df["Volume"] = 0
        df = df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR al descargar intradía: {exc}", file=sys.stderr)
        print("Nota: Yahoo limita 1h a ~730 días y 5m a ~60 días.", file=sys.stderr)
        return 1

    df.to_csv(args.out, index=False)
    print(f"OK: {len(df)} velas guardadas en {args.out}")
    print(df.tail(3).to_string(index=False))
    return 0


def _to_utc(s):
    import pandas as pd

    dt = pd.to_datetime(s, utc=True, errors="coerce")
    return dt


if __name__ == "__main__":
    raise SystemExit(main())
