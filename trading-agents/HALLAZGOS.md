# Hallazgos — Equipo de agentes de trading sobre oro (XAUUSD / GC=F)

Resumen honesto de lo que construimos, probamos y aprendimos. Datos reales de
oro 2010-2026 (futuro GC=F, ~4243 días).

> ⚠️ Esto es una herramienta educativa de backtesting. **No es asesoría
> financiera.** Los resultados pasados no garantizan resultados futuros.

---

## 1. Qué construimos

Un **equipo de agentes**, cada uno una estrategia con un rol:

- 🏇 **Tendencia** — cruce de medias (EMA).
- ↩️ **Reversión** — comprar sobreventa / vender sobrecompra (RSI).
- 🚀 **Ruptura** — entrar al romper máximos/mínimos (Donchian).
- 🛡️ **Gestor de riesgo** — tamaño por volatilidad, stop-loss por ATR, kill-switch por drawdown.
- 🎯 **Coordinador** — combina a los tres por consenso (el "EQUIPO").

Más un motor de backtest sin *lookahead* (con costos, stops y kill-switch) y
herramientas de validación: prueba fuera de muestra (`--split`) y walk-forward
(`walkforward.py`).

---

## 2. Un bug real que encontramos y arreglamos

El stop-loss dejaba la posición plana **hasta que la señal cambiara de signo**.
En una tendencia larga (señal constante), un solo stop dejaba al agente fuera de
**todo** el movimiento siguiente. Por eso el seguidor de tendencia *perdía* en un
mercado alcista (resultado imposible para un trend-follower sano).

**Arreglo:** tras un stop, solo unos días de enfriamiento y luego se permite
reentrar. El seguidor de tendencia pasó de **-18.2%** a **+27.4%**.

> Lección: un backtest puede verse mal por un **bug**, no por la estrategia.
> Siempre revisa que el motor haga lo que crees.

---

## 3. Resultados (oro real, solo largos)

### Backtest de una sola pasada (2010-2026)

| Estrategia | Retorno | Sharpe | MaxDD |
|---|---|---|---|
| tendencia | +27.4% | 0.27 | -20.2% |
| reversión | +26.9% | 0.30 | -15.8% |
| ruptura | +33.2% | 0.28 | -22.0% |
| EQUIPO | +13.1% | 0.18 | -20.2% |
| **comprar y mantener** | **+248%** | **0.52** | -44.4% |

Comprar y mantener gana en retorno; los agentes solo reducen la caída máxima.

### Prueba fuera de muestra (`--split 0.6`)

Las estrategias **se dieron vuelta** entre la Parte 1 y la Parte 2:

| Estrategia | Sharpe Parte 1 (2010-2020) | Sharpe Parte 2 (2020-2026) |
|---|---|---|
| tendencia | 0.34 👍 | -0.08 📉 |
| ruptura | 0.36 👍 | 0.01 📉 |
| reversión | 0.04 👎 | 0.84 🚀 |
| **EQUIPO** | 0.24 | **0.85** (positivo en ambas) |

Las "mejores" del pasado fueron las peores del futuro, y viceversa. El **EQUIPO
(diversificar)** fue lo único positivo en las dos mitades.

### Walk-forward (elegir cada año la mejor config con solo el pasado)

| | Retorno (12 años) | Sharpe |
|---|---|---|
| WALK-FORWARD (sistema adaptativo) | **-7.4%** | -0.03 |
| comprar y mantener | **+271.6%** | 0.79 |

El `Sharpe train` (lo que prometía) **no predijo** el `Sharpe test` (lo que
resultó). El sistema "inteligente" **perdió dinero** en 12 años.

### Regímenes: lateral (2013-2019) vs alcista (2019-2026)

| | Lateral (Sharpe) | Alcista (Sharpe) |
|---|---|---|
| reversión | 0.20 | 0.80 |
| tendencia | -0.25 | 0.25 |
| ruptura | -0.36 | 0.26 |
| EQUIPO (simple) | -0.12 | 0.96 |
| comprar y mantener | 0.12 | 0.87 |

- La **reversión** fue positiva en ambos regímenes (la más robusta).
- En el lateral, el oro no fue a ningún lado (buy&hold +4%); ahí la **reversión le
  ganó** a aguantar, con la mitad de caída.
- En el alcista, el **EQUIPO simple** incluso superó a buy&hold en Sharpe (0.96 vs
  0.87) con la mitad de drawdown — aunque buy&hold ganó mucho más en retorno bruto.

### Coordinador ADAPTATIVO (ponderar por rendimiento reciente): FALLÓ

| | EQUIPO simple | EQUIPO adaptativo |
|---|---|---|
| Lateral 2013-2019 | Sharpe -0.12 | **-0.71** (peor) |
| Alcista 2019-2026 | Sharpe 0.96 | **0.28** (peor) |

Ponderar por rendimiento reciente = perseguir al ganador de ayer. Como el
rendimiento de una estrategia revierte, el adaptativo cargaba peso en el agente
equivocado justo antes del giro del mercado. **El promedio simple resultó más
robusto que el "inteligente".** Principio real: la diversificación ingenua (1/N)
es muy difícil de superar.

### Estrategias de gráfico (análisis técnico clásico)

Probamos golden cross, MACD, Bollinger y patrón envolvente (engulfing).

- Fuera de muestra (`--split`) **ninguna fue consistente**: la que brillaba en la
  Parte 1 fallaba en la Parte 2 (p. ej. golden cross 0.14 → -0.39).
- En el **walk-forward** (`--set chart`) dieron +99% / Sharpe 0.57 en 12 años...
  pero **por debajo de comprar y mantener** (+272% / 0.79), y con dos matices
  demoledores:
  1. El `Sharpe train` **no predijo** el `Sharpe test` (una config con train -0.15
     dio el mejor test +1.76): elegir "la mejor del pasado" no aportó nada.
  2. **Un solo año parabólico** (2025-2026, +65.7%) cargó con casi todo el
     resultado; sin ese año, ~+20% en 11 años (casi plano).
- Golden cross y MACD son seguidores de tendencia: capturaron parte de la subida
  del oro ("beta"), no un edge predictivo.

**Conclusión (oro):** el análisis técnico de gráfico, probado con rigor, no mostró
una ventaja fiable sobre comprar y mantener.

**En el Nasdaq** las de gráfico mejoraron (hay tendencia): el **Golden Cross** fue
consistente fuera de muestra (Sharpe 0.86 y 0.85), la primera en no darse vuelta. El
walk-forward de gráfico dio +159% / Sharpe 0.71 — positivo, pero **peor que el
conjunto clásico** (+337%) y por debajo de comprar y mantener (0.88). El `engulfing`
se veía genial en entrenamiento (train ~1.4), el selector lo elegía, y colapsó en
2022 (-15%): overfitting puro.

> De todo el análisis técnico, lo único con mérito repetible es **seguir tendencia**
> (golden cross, MACD), y solo en mercados que tienden. Los patrones (velas,
> Bollinger) no mostraron edge fiable. Y ni lo que funciona le gana a aguantar en
> retorno: su valor es reducir la caída.

### Otro mercado: NASDAQ (QQQ) — las conclusiones NO generalizan

Repetimos todo en el Nasdaq-100 (QQQ), 2010-2026. Resultado muy distinto al oro:

**Fuera de muestra (`--split 0.6`):** el EQUIPO simple fue **consistente** en ambas
mitades (Sharpe 1.04 y 0.95), igualó o superó a comprar y mantener en Sharpe, y con
mucha menos caída (DD -13% a -15% vs -23% a -36%).

**Walk-forward (el juez definitivo):**

| | Retorno (12 años) | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|
| WALK-FORWARD | +337% | 13.1% | 0.87 | **-20.8%** |
| comprar y mantener | +625% | 18.0% | 0.88 | -35.6% |

- A diferencia del oro (walk-forward **-7.4%**), aquí dio **+337%** y el `train` SÍ
  predijo el `test` la mayoría de los años.
- Empató en Sharpe con aguantar, pero con **~40% menos de caída máxima** (esquivó
  parte del crash de 2022).
- Aguantar ganó más en retorno bruto; tuvo un año malo (2022, -16%).

**Por qué:** el Nasdaq tiene tendencias fuertes y persistentes; el seguimiento de
tendencia (ruptura/tendencia) tiene ahí una ventaja más real que en el oro, que es
más caótico. **El activo importa muchísimo.**

> Conclusión transversal: no hay un "funciona / no funciona" universal. En activos
> con tendencia fuerte, un equipo diversificado + gestión de riesgo puede dar un
> retorno similar ajustado por riesgo con la mitad de la caída. En activos caóticos,
> mejor aguantar. Depende del activo y de tu objetivo (máximo retorno vs no sufrir).

---

## 4. Las lecciones (lo más importante)

1. **Un backtest bonito de una sola pasada no vale casi nada.** Hay que probarlo
   fuera de muestra y walk-forward.
2. **Optimizar sobre el pasado = sobreajuste.** Ajustar parámetros hasta que se
   vea perfecto en la historia suele ser ajustarse al ruido. El pasado no predijo
   el futuro.
3. **Ganarle al mercado es genuinamente difícil.** Estrategias técnicas simples,
   probadas con honestidad, no le ganaron a aguantar el oro. Es la norma, no un
   fracaso personal.
4. **Diversificar (el "equipo") es más robusto que apostar a una sola estrategia**,
   porque no se puede saber de antemano cuál funcionará.
5. **El resultado depende del régimen** del mercado (lateral vs tendencia), y el
   régimen no se puede predecir. La reversión ayuda en laterales; aguantar gana en
   tendencias.
6. **Lo "más inteligente" no suele ganar.** El coordinador adaptativo (una mejora
   obvia) empeoró todo. El promedio simple (1/N) fue más robusto. La complejidad
   se paga cara y rara vez compensa.
7. **El activo lo cambia todo.** Lo que falla en el oro (caótico) funciona en el
   Nasdaq (tendencia fuerte). El seguimiento de tendencia necesita tendencias. No
   hay conclusión universal: hay que probar en CADA mercado.
8. **El valor suele estar en el riesgo, no en el retorno.** Cuando el equipo
   "ganó", fue dando un retorno parecido con **mucha menos caída**, no ganando más.

---

## 5. Qué me llevo (lo útil de verdad)

Más que un sistema para ganar dinero, construí la **capacidad de distinguir una
estrategia real de un espejismo**. Eso es un escudo anti-estafas: cuando alguien
venda un bot "con 90% de aciertos", sé pedir prueba **fuera de muestra**.

---

## 6. Cómo reproducir

```bash
python fetch_data.py --symbol GC=F                      # bajar oro real
python run.py --data data/gold.csv --no-short --plot    # backtest
python run.py --data data/gold.csv --no-short --split 0.6   # fuera de muestra
python walkforward.py --data data/gold.csv --no-short --plot # walk-forward
```

*Documento vivo — se irá actualizando a medida que sigamos probando.*
