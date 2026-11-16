"""
Brief diario del oro: tu agente acompañante.

Junta en un solo reporte todo lo que necesitas mirar antes de operar:
  1) MACRO   — dirección del dólar (el driver #1 del oro).
  2) SESIÓN  — qué sesión está activa ahora y cuál conviene.
  3) NIVELES — precio, soportes/resistencias, zona de volumen (POC).
  4) SEÑALES — qué dicen los agentes de estrategia hoy (informativo).
  5) CHECKLIST — para no operar a ciegas.

Córrelo cada mañana:
    python daily_brief.py --data data/gold.csv

Nota honesta: esto es CONTEXTO para decidir mejor, no una orden de compra/venta.
Las señales de los agentes, en el oro, no le ganaron a aguantar; son un dato más.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from agents import Breakout, Coordinator, MeanReversion, RiskManager, TrendFollower
from engine.data_loader import load_csv
from levels import pivots, volume_profile

SESIONES = [("Asia", 0, 8), ("Londres", 8, 13), ("NuevaYork", 13, 21)]
POS = {1.0: "LARGO ▲ (alcista)", 0.0: "FUERA — (plano)", -1.0: "CORTO ▼ (bajista)"}


def macro_companion(start="2024-01-01") -> str:
    """Dirección reciente del dólar (DXY): viento a favor o en contra del oro."""
    try:
        import yfinance as yf
        dxy = yf.download("DX-Y.NYB", start=start, progress=False, auto_adjust=False)
        if dxy is None or dxy.empty:
            raise RuntimeError
        if hasattr(dxy.columns, "nlevels") and dxy.columns.nlevels > 1:
            dxy.columns = dxy.columns.get_level_values(0)
        c = dxy["Close"].dropna()
        chg = (c.iloc[-1] / c.iloc[-20] - 1) * 100  # cambio ~1 mes
        if chg < -0.5:
            return f"Dólar (DXY) BAJANDO {chg:+.1f}% (~1 mes) → viento A FAVOR del oro ✅"
        if chg > 0.5:
            return f"Dólar (DXY) SUBIENDO {chg:+.1f}% (~1 mes) → viento EN CONTRA del oro ⚠️"
        return f"Dólar (DXY) plano ({chg:+.1f}%) → sin sesgo claro"
    except Exception:  # noqa: BLE001
        return ("No pude bajar el dólar (DXY). Míralo manualmente: si el dólar cae, "
                "ayuda al oro; si sube, lo frena.")


def session_companion() -> str:
    """Qué sesión está activa ahora (UTC) y recomendación."""
    now = datetime.now(timezone.utc)
    h = now.hour
    activa = next((n for n, a, b in SESIONES if a <= h < b), "fuera de sesión")
    linea = f"Ahora: {now:%H:%M} UTC → sesión activa: {activa}."
    reco = ("Mejor operar en Londres (08-13 UTC, limpio) o el solape con NY "
            "(13-17 UTC, volumen). Evita Asia (ruidosa).")
    return linea + "\n   " + reco


def levels_companion(df: pd.DataFrame) -> str:
    price = df["Close"].iloc[-1]
    lo, hi = float(df["Low"].min()), float(df["High"].max())
    pos = (price - lo) / (hi - lo) * 100 if hi > lo else 50
    highs, lows = pivots(df, 10)
    res = sorted({round(float(p), 2) for _, p in highs if p > price})[:2]
    sup = sorted({round(float(p), 2) for _, p in lows if p < price}, reverse=True)[:2] or [round(lo, 2)]
    centers, vp = volume_profile(df)
    poc = float(centers[int(np.argmax(vp))])
    d = lambda x: f"{x:,.2f} ({(x-price)/price*100:+.1f}%)"
    out = [f"Precio: {price:,.2f}  (en el {pos:.0f}% del rango de {len(df)} días)"]
    out.append("   Resistencias: " + (", ".join(d(x) for x in res) if res else "en máximos"))
    out.append("   Soportes:     " + ", ".join(d(x) for x in sup))
    out.append(f"   POC (volumen): {d(poc)}  — zona imán")
    return "\n   ".join(out)


def signals_companion(df: pd.DataFrame) -> str:
    """Qué señala hoy cada agente (último dato) y el consenso del equipo."""
    agents = [TrendFollower(), MeanReversion(), Breakout()]
    lines = []
    for a in agents:
        last = a.generate_signals(df).iloc[-1]
        lines.append(f"{a.name:>10}: {POS.get(np.sign(last)*1.0, 'FUERA')}")
    team = Coordinator(agents=agents).ensemble_signal(df).iloc[-1]
    sesgo = "alcista ▲" if team > 0.1 else "bajista ▼" if team < -0.1 else "neutral —"
    lines.append(f"{'EQUIPO':>10}: consenso {sesgo} ({team:+.2f})")
    return "\n   ".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Brief diario del oro.")
    ap.add_argument("--data", default="data/gold.csv")
    args = ap.parse_args()
    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data)
    hoy = datetime.now(timezone.utc).date()

    print("=" * 66)
    print(f"  BRIEF DIARIO DEL ORO — {hoy}")
    print("=" * 66)
    print("\n1) MACRO (¿qué mueve al oro?)")
    print("   " + macro_companion())
    print("\n2) SESIÓN (¿cuándo operar?)")
    print("   " + session_companion())
    print("\n3) NIVELES (¿dónde está el precio?)")
    print("   " + levels_companion(df.tail(250)))  # niveles sobre el último año
    print("\n4) SEÑALES DE LOS AGENTES (informativo, no es orden)")
    print("   " + signals_companion(df))
    print("\n5) CHECKLIST antes de operar")
    for item in [
        "¿El dólar está a favor o en contra hoy?",
        "¿Hay noticia fuerte de EE.UU. (Fed / CPI / empleo)?",
        "¿Estoy en sesión de Londres o NY (no Asia)?",
        "¿Dónde está el precio vs soporte/resistencia?",
        "¿Definí mi stop y tamaño (riesgo ≤ 1-2% por operación)?",
    ]:
        print(f"   [ ] {item}")

    print("\n" + "=" * 66)
    print("⚠️  CONTEXTO, no una orden de compra/venta. Tú decides, con gestión")
    print("    de riesgo. Ningún agente garantiza nada; el mercado tiene riesgo real.")
    print("=" * 66)


if __name__ == "__main__":
    main()
