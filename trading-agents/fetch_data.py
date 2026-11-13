"""
Descarga datos REALES de oro y los guarda en CSV.

Requiere conexión a internet (corre esto en tu máquina). Por defecto prueba
VARIAS fuentes automáticamente hasta que una funcione, así que normalmente solo
necesitas:

    python fetch_data.py

Mercado objetivo: oro (XAUUSD spot / GC=F futuro; para backtesting son casi
equivalentes).

Opciones:
    python fetch_data.py                       # auto: prueba yfinance y stooq
    python fetch_data.py --source stooq        # forzar Stooq (XAUUSD spot)
    python fetch_data.py --source yfinance     # forzar yfinance
    python fetch_data.py --symbol GC=F         # elegir el ticker a mano
    python fetch_data.py --start 2010-01-01    # desde qué fecha
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request

# Un User-Agent de navegador: sin esto, Stooq y otras webs rechazan al script.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_yfinance(symbol: str, start: str, end: str | None):
    """Descarga desde Yahoo Finance vía la librería yfinance."""
    import yfinance as yf

    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance no devolvió datos para '{symbol}'.")
    # Aplanar columnas MultiIndex si las hay.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    # Asegurar que exista columna Volume.
    if "Volume" not in df.columns:
        df["Volume"] = 0
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def fetch_stooq(symbol: str):
    """Descarga el CSV directo de stooq.com (para oro spot usa 'xauusd')."""
    import pandas as pd

    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")

    first_line = text.splitlines()[0] if text.strip() else ""
    if not text.strip() or "Date" not in first_line:
        # Stooq devuelve "No data" o una página HTML cuando algo falla.
        raise RuntimeError(
            f"Stooq no devolvió datos válidos para '{symbol}'. "
            f"Respuesta: {text[:120]!r}"
        )

    df = pd.read_csv(io.StringIO(text))
    if df.empty or "Close" not in df.columns:
        raise RuntimeError(f"Stooq no devolvió columnas válidas para '{symbol}'.")
    if "Volume" not in df.columns:
        df["Volume"] = 0
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def fetch_auto(start: str, end: str | None):
    """Prueba varias fuentes/símbolos en orden hasta que una funcione."""
    intentos = [
        ("yfinance", "GC=F", lambda: fetch_yfinance("GC=F", start, end)),
        ("yfinance", "XAUUSD=X", lambda: fetch_yfinance("XAUUSD=X", start, end)),
        ("stooq", "xauusd", lambda: fetch_stooq("xauusd")),
        ("stooq", "xauusd.f", lambda: fetch_stooq("xauusd.f")),
    ]
    errores = []
    for fuente, simbolo, fn in intentos:
        try:
            print(f"Probando {fuente} ({simbolo})...", file=sys.stderr)
            df = fn()
            print(f"  -> OK con {fuente} ({simbolo})", file=sys.stderr)
            return df
        except Exception as exc:  # noqa: BLE001
            print(f"  -> falló: {exc}", file=sys.stderr)
            errores.append(f"{fuente}/{simbolo}: {exc}")
    raise RuntimeError(
        "Ninguna fuente funcionó. Detalle:\n  - " + "\n  - ".join(errores)
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Descarga datos reales de oro.")
    ap.add_argument("--symbol", default=None, help="Ticker (p. ej. GC=F o xauusd).")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--source", choices=["auto", "yfinance", "stooq"], default="auto")
    ap.add_argument("--out", default="data/gold.csv")
    args = ap.parse_args()

    try:
        if args.source == "auto" and args.symbol is None:
            df = fetch_auto(args.start, args.end)
        elif args.source == "stooq":
            df = fetch_stooq(args.symbol or "xauusd")
        elif args.source == "yfinance":
            df = fetch_yfinance(args.symbol or "GC=F", args.start, args.end)
        else:  # auto pero con símbolo explícito -> probar yfinance y luego stooq
            try:
                df = fetch_yfinance(args.symbol, args.start, args.end)
            except Exception:  # noqa: BLE001
                df = fetch_stooq(args.symbol)
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR al descargar: {exc}", file=sys.stderr)
        print(
            "\nSugerencias:\n"
            "  1) Revisa tu conexión a internet.\n"
            "  2) Prueba:  python fetch_data.py --source stooq\n"
            "  3) Prueba:  python fetch_data.py --source yfinance --symbol GC=F\n"
            "  4) Si tienes antivirus/firewall o VPN corporativa, puede estar bloqueando.",
            file=sys.stderr,
        )
        return 1

    df.to_csv(args.out, index=False)
    print(f"\nOK: {len(df)} filas guardadas en {args.out}")
    print(df.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
