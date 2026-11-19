"""
Análisis macro: ¿qué mueve al oro?

Las noticias internacionales afectan al oro a través de variables medibles. Este
script mide la correlación de los retornos del oro con:
  - El dólar (DXY): el oro suele subir cuando el dólar baja (correlación negativa).
  - Las tasas a 10 años (^TNX): oro sube cuando bajan las tasas.
  - El miedo (^VIX): oro como refugio cuando hay pánico.
  - La bolsa (SPY).

Correlación: +1 = se mueven igual; -1 = se mueven al revés; 0 = sin relación.

Uso (en tu máquina, con internet):
    python macro_analysis.py
    python macro_analysis.py --start 2018-01-01
"""
from __future__ import annotations

import argparse
import sys

SERIES = {
    "Dólar (DXY)": "DX-Y.NYB",
    "Tasa 10a (^TNX)": "^TNX",
    "Miedo (^VIX)": "^VIX",
    "Bolsa (SPY)": "SPY",
}


def _download(symbol, start):
    import yfinance as yf

    df = yf.download(symbol, start=start, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    return df["Close"].rename(symbol)


def main() -> None:
    ap = argparse.ArgumentParser(description="Qué mueve al oro (análisis macro).")
    ap.add_argument("--gold", default="GC=F", help="Símbolo del oro.")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--roll", type=int, default=90, help="Ventana de correlación móvil.")
    args = ap.parse_args()

    import pandas as pd

    try:
        gold = _download(args.gold, args.start)
        if gold is None:
            raise RuntimeError(f"No pude bajar el oro ({args.gold}).")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Revisa tu conexión. Esto necesita internet (córrelo en tu PC).",
              file=sys.stderr)
        return

    gold_ret = gold.pct_change()

    print(f"Activo: {args.gold}  |  desde {args.start}  |  {len(gold)} días\n")
    print("=" * 78)
    print(f"{'Variable':>18} | {'Correlación':>11} | {'Relación':>10} | {'Rango móvil (min..max)':>24}")
    print("-" * 78)

    for nombre, symbol in SERIES.items():
        try:
            serie = _download(symbol, args.start)
            if serie is None:
                raise RuntimeError("sin datos")
            ret = serie.pct_change()
            joined = pd.concat([gold_ret, ret], axis=1, sort=False).dropna()
            if len(joined) < 30:
                raise RuntimeError("pocos datos")
            corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
            roll = joined.iloc[:, 0].rolling(args.roll).corr(joined.iloc[:, 1]).dropna()
            rel = _relacion(nombre, corr)
            print(f"{nombre:>18} | {corr:>+11.2f} | {rel:>10} | "
                  f"{roll.min():>+10.2f} .. {roll.max():>+8.2f}")
        except Exception as exc:  # noqa: BLE001
            print(f"{nombre:>18} | {'(falló: '+str(exc)+')':>49}")

    print("=" * 78)
    print("\nLectura:")
    print("  +1 = se mueven igual · −1 = se mueven al revés · 0 = sin relación.")
    print("  El 'Rango móvil' muestra que la correlación CAMBIA con el tiempo (no es fija).")
    print("\nOjo: correlación NO es causalidad, y puede debilitarse. Es contexto, no señal.")


def _relacion(nombre, corr):
    if corr <= -0.3:
        return "inversa"
    if corr >= 0.3:
        return "directa"
    return "débil"


if __name__ == "__main__":
    main()
