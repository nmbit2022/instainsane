"""
Diario de operaciones.

Registra cada trade (entrada, stop, take profit, veredicto del sistema y tu
motivo) y, al cerrarlo, calcula tu rendimiento. Con el tiempo te deja ver tu
win rate real y qué setups funcionan — la base para mejorar (y para después
ayudar a los agentes con TUS datos).

Uso:
    python diario.py            # ver el diario + estadísticas
    python diario.py add        # registrar una operación nueva (te pregunta)
    python diario.py cerrar 3   # cerrar la operación #3 (te pregunta salida y P/L)
"""
from __future__ import annotations

import argparse
import csv
import os
from datetime import date

CSV = "data/operaciones.csv"
CAMPOS = ["id", "fecha", "instrumento", "direccion", "entrada", "stop",
          "take_profit", "tamano", "veredicto", "motivo", "estado",
          "fecha_cierre", "salida", "pnl_usd", "resultado"]


def cargar() -> list[dict]:
    if not os.path.exists(CSV):
        return []
    with open(CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(rows)


def preg(texto, defecto=""):
    r = input(f"  {texto}" + (f" [{defecto}]" if defecto else "") + ": ").strip()
    return r or defecto


def add() -> None:
    rows = cargar()
    nid = str(max([int(r["id"]) for r in rows], default=0) + 1)
    print(f"\nNueva operación #{nid}:")
    fila = {
        "id": nid,
        "fecha": preg("Fecha", str(date.today())),
        "instrumento": preg("Instrumento", "XAUUSD"),
        "direccion": preg("Dirección (long/short)").lower(),
        "entrada": preg("Precio de entrada"),
        "stop": preg("Stop-loss"),
        "take_profit": preg("Take profit"),
        "tamano": preg("Tamaño (lotes)", "0.1"),
        "veredicto": preg("Veredicto del sistema (long/short/esperar)"),
        "motivo": preg("Motivo / setup (por qué entraste)"),
        "estado": "abierta",
        "fecha_cierre": "", "salida": "", "pnl_usd": "", "resultado": "",
    }
    rows.append(fila)
    guardar(rows)
    print(f"\n✅ Operación #{nid} registrada (abierta).")


def cerrar(nid: str) -> None:
    rows = cargar()
    fila = next((r for r in rows if r["id"] == str(nid)), None)
    if not fila:
        raise SystemExit(f"No encontré la operación #{nid}.")
    if fila["estado"] == "cerrada":
        print(f"La operación #{nid} ya estaba cerrada. La vuelvo a cargar.")
    print(f"\nCerrando operación #{nid} ({fila['direccion']} {fila['instrumento']}):")
    fila["salida"] = preg("Precio de salida")
    fila["pnl_usd"] = preg("Ganancia/pérdida en USD (de tu plataforma, ej: 240 o -50)")
    fila["fecha_cierre"] = preg("Fecha de cierre", str(date.today()))
    try:
        pnl = float(fila["pnl_usd"])
        fila["resultado"] = "ganada" if pnl > 0 else "perdida" if pnl < 0 else "break-even"
    except ValueError:
        fila["resultado"] = "?"
    fila["estado"] = "cerrada"
    guardar(rows)
    print(f"\n✅ Operación #{nid} cerrada: {fila['resultado']} ({fila['pnl_usd']} USD).")


def ver() -> None:
    rows = cargar()
    if not rows:
        print("Diario vacío. Registrá tu primera operación con: python diario.py add")
        return

    print("=" * 78)
    print("  DIARIO DE OPERACIONES")
    print("=" * 78)
    for r in rows:
        est = "🔵 abierta" if r["estado"] == "abierta" else {
            "ganada": "🟢 ganada", "perdida": "🔴 perdida",
            "break-even": "🟡 break-even"}.get(r["resultado"], "⚪ cerrada")
        linea = (f"#{r['id']} {r['fecha']} · {r['instrumento']} · "
                 f"{r['direccion'].upper():>5} · entrada {r['entrada']}")
        if r["estado"] == "cerrada":
            linea += f" → salida {r['salida']} · {r['pnl_usd']} USD"
        print(f"{est}  {linea}")
        if r["motivo"]:
            print(f"            motivo: {r['motivo']}")

    cerradas = [r for r in rows if r["estado"] == "cerrada"]
    pnls = []
    for r in cerradas:
        try:
            pnls.append(float(r["pnl_usd"]))
        except ValueError:
            pass
    print("-" * 78)
    print(f"  Operaciones: {len(rows)} total · {len(rows)-len(cerradas)} abiertas · {len(cerradas)} cerradas")
    if pnls:
        ganadas = sum(1 for p in pnls if p > 0)
        wr = ganadas / len(pnls) * 100
        print(f"  Win rate: {wr:.0f}% ({ganadas}/{len(pnls)})  ·  "
              f"P/L total: {sum(pnls):+.2f} USD  ·  promedio: {sum(pnls)/len(pnls):+.2f} USD")
    print("=" * 78)
    print("  Datos tuyos. Con más operaciones, veremos qué funciona de verdad.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Diario de operaciones.")
    ap.add_argument("accion", nargs="?", default="ver", choices=["ver", "add", "cerrar"])
    ap.add_argument("id", nargs="?", default=None)
    args = ap.parse_args()
    if args.accion == "add":
        add()
    elif args.accion == "cerrar":
        if not args.id:
            raise SystemExit("Indicá el número: python diario.py cerrar 1")
        cerrar(args.id)
    else:
        ver()


if __name__ == "__main__":
    main()
