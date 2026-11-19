"""
¿Long o short AHORA? — veredicto del momento.

Junta varias "opiniones" (tendencia de fondo, agentes de estrategia, momentum,
flujo de órdenes reciente y el dólar) y las suma en un veredicto claro:
LONG, SHORT o ESPERAR. También marca el nivel clave y una zona de stop sugerida.

NO es una orden garantizada: las señales no aseguran acertar. Es una lectura
ponderada del contexto. Vos decidís, siempre con stop y riesgo ≤ 1-2%.

Uso:
    python senal.py --data data/gold.csv
    python senal.py --data data/gold.csv --intra data/gold_1h.csv
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from agents import Breakout, Coordinator, MeanReversion, TrendFollower
from engine.data_loader import load_csv
from engine.indicators import sma


def voto(nombre, señal, detalle):
    return {"factor": nombre, "voto": señal, "detalle": detalle}


def flujo_ordenes(path: str) -> int:
    """+1 si dominan compradores, -1 si vendedores, 0 si no hay datos."""
    if not path or not os.path.exists(path):
        return 0
    df = pd.read_csv(path)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Close"]).tail(120)
    if len(df) < 10:
        return 0
    presion = (df["Volume"] * np.sign(df["Close"] - df["Open"])).sum()
    return 1 if presion > 0 else -1 if presion < 0 else 0


def _mom_pct(symbol: str) -> float:
    """Cambio % (~1 mes) del cierre de un símbolo."""
    import yfinance as yf
    s = yf.download(symbol, period="3mo", progress=False, auto_adjust=False)
    if s is None or s.empty:
        raise RuntimeError("sin datos")
    if hasattr(s.columns, "nlevels") and s.columns.nlevels > 1:
        s.columns = s.columns.get_level_values(0)
    c = s["Close"].dropna()
    return (c.iloc[-1] / c.iloc[-20] - 1) * 100


def dolar_bias() -> tuple[int, str]:
    """Dólar subiendo => bias short para el ORO (-1). Bajando => long (+1)."""
    try:
        chg = _mom_pct("DX-Y.NYB")
        if chg > 0.5:
            return -1, f"dólar subiendo {chg:+.1f}% (en contra del oro)"
        if chg < -0.5:
            return 1, f"dólar bajando {chg:+.1f}% (a favor del oro)"
        return 0, f"dólar plano ({chg:+.1f}%)"
    except Exception:  # noqa: BLE001
        return 0, "dólar no disponible (míralo manual)"


def vix_bias() -> tuple[int, str]:
    """VIX subiendo => miedo => bias short para un ÍNDICE (-1). Bajando => long (+1)."""
    try:
        chg = _mom_pct("^VIX")
        if chg > 5:
            return -1, f"VIX subiendo {chg:+.1f}% (miedo, en contra del índice)"
        if chg < -5:
            return 1, f"VIX bajando {chg:+.1f}% (calma, a favor del índice)"
        return 0, f"VIX plano ({chg:+.1f}%)"
    except Exception:  # noqa: BLE001
        return 0, "VIX no disponible (míralo manual)"


def detectar_mercado(path: str, override: str | None) -> str:
    """Detecta si es índice (Nasdaq/S&P...) por el nombre del archivo de datos."""
    if override:
        return override
    low = path.lower()
    claves = ("nasdaq", "us100", "nq", "spx", "sp500", "us500", "us30", "dow", "index", "indice")
    return "indice" if any(k in low for k in claves) else "oro"


def main() -> None:
    ap = argparse.ArgumentParser(description="¿Long o short ahora? Veredicto del momento.")
    ap.add_argument("--data", default="data/gold.csv")
    ap.add_argument("--intra", default="data/gold_1h.csv")
    ap.add_argument("--market", choices=["oro", "indice"], default=None,
                    help="oro = usa el dólar; indice = usa el VIX. Por defecto se detecta solo.")
    args = ap.parse_args()
    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data)
    price = df["Close"].iloc[-1]
    votos = []

    # 1) Tendencia de fondo (precio vs media 200).
    s200 = sma(df["Close"], 200).iloc[-1]
    v = 1 if price > s200 else -1
    votos.append(voto("Tendencia de fondo (200)", v,
                      f"precio {price:,.0f} {'sobre' if v>0 else 'bajo'} la media 200 ({s200:,.0f})"))

    # 2) Tendencia media (50 vs 200).
    s50 = sma(df["Close"], 50).iloc[-1]
    v = 1 if s50 > s200 else -1
    votos.append(voto("Cruce de medias (50/200)", v,
                      f"media 50 {'sobre' if v>0 else 'bajo'} la 200"))

    # 3) Consenso de los agentes de estrategia.
    team = Coordinator(agents=[TrendFollower(), MeanReversion(), Breakout()]).ensemble_signal(df).iloc[-1]
    v = 1 if team > 0.1 else -1 if team < -0.1 else 0
    votos.append(voto("Equipo de agentes", v, f"consenso {team:+.2f}"))

    # 4) Momentum corto (precio vs media 20).
    s20 = sma(df["Close"], 20).iloc[-1]
    v = 1 if price > s20 else -1
    votos.append(voto("Momentum corto (20)", v,
                      f"precio {'sobre' if v>0 else 'bajo'} la media 20 ({s20:,.0f})"))

    # 5) Flujo de órdenes reciente (intradía).
    v = flujo_ordenes(args.intra)
    votos.append(voto("Flujo de órdenes (1h)", v,
                      {1: "dominan compradores", -1: "dominan vendedores", 0: "sin datos intradía"}[v]))

    # 6) Macro: dólar para el oro, VIX para índices (se detecta solo).
    mercado = detectar_mercado(args.data, args.market)
    if mercado == "indice":
        v, det = vix_bias()
        votos.append(voto("VIX / miedo (macro)", v, det))
    else:
        v, det = dolar_bias()
        votos.append(voto("Dólar (macro)", v, det))

    # Veredicto.
    score = sum(x["voto"] for x in votos)
    activos = sum(1 for x in votos if x["voto"] != 0)
    if score >= 2:
        verdicto, emoji = "LONG (comprar)", "🟢"
    elif score <= -2:
        verdicto, emoji = "SHORT (vender)", "🔴"
    else:
        verdicto, emoji = "ESPERAR (sin ventaja clara)", "🟡"

    # Stop sugerido (fuera del rango reciente de 10 días).
    hi10 = df["High"].tail(10).max()
    lo10 = df["Low"].tail(10).min()

    print("=" * 60)
    print(f"  ¿LONG o SHORT ahora?  ·  precio {price:,.2f}")
    print("=" * 60)
    print(f"{'Factor':>26} | Voto")
    print("-" * 60)
    for x in votos:
        flecha = "▲ long" if x["voto"] > 0 else "▼ short" if x["voto"] < 0 else "— neutral"
        print(f"{x['factor']:>26} | {flecha:>9}  ({x['detalle']})")
    print("-" * 60)
    print(f"  VEREDICTO: {emoji} {verdicto}   (score {score:+d} de {activos} votos)")
    print("=" * 60)
    if "SHORT" in verdicto:
        print(f"  Si entrás SHORT: stop sugerido por encima de ~{hi10:,.2f} (máximo 10 días).")
    elif "LONG" in verdicto:
        print(f"  Si entrás LONG: stop sugerido por debajo de ~{lo10:,.2f} (mínimo 10 días).")
    else:
        print("  Mayoría dividida: quizá mejor esperar a que se alinee el contexto.")
    print("\n  ⚠️ No es una orden garantizada. Es contexto ponderado. Usá SIEMPRE stop")
    print("     y arriesgá ≤ 1-2% por operación. Vos tomás la decisión final.")


if __name__ == "__main__":
    main()
