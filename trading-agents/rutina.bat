@echo off
REM ============================================================
REM  Rutina diaria del oro - doble clic para correr todo.
REM  Debe estar dentro de la carpeta trading-agents.
REM ============================================================
cd /d "%~dp0"

echo.
echo ==== Activando entorno ====
call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo No encontre el entorno .venv. Crealo con: python -m venv .venv
  pause
  exit /b
)

echo.
echo ==== 1/4  Actualizando datos diarios del oro ====
python fetch_data.py --symbol GC=F

echo.
echo ==== 2/4  Actualizando datos de 1 hora ====
python fetch_intraday.py

echo.
echo ==== 3/4  BRIEF DEL DIA ====
python daily_brief.py --data data\gold.csv

echo.
echo ==== 4/4  RECAP: dia y semana anterior ====
python recap.py --period day
echo.
python recap.py --period week

echo.
echo ============================================================
echo  Listo. Sube con la rueda del mouse para leer el brief.
echo  Abre tu panel: el link que te paso Claude.
echo ============================================================
pause
