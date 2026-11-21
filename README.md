# SIMTELE-RISK

Aplicación web educativa (Flask + Neon PostgreSQL) para experimentación numérica verificable sobre 4 casos hipotéticos inspirados en transporte por cable. **Datos sintéticos; no representa sistemas reales ni mediciones reales.**

## Requisitos cumplidos (implementación técnica)
- 4 módulos: detención, deterioro, oscilaciones, sensores.
- 3 escenarios por módulo: NORMAL, ESTRÉS, MAL CONDICIONADO.
- Métodos: Bisección, Newton-Raphson, Secante, Jacobi, Gauss-Seidel, LU, Gradiente conjugado (SPD), Lagrange, Newton diferencias divididas, Spline cúbico natural, Trapecio compuesto, Simpson 1/3, Romberg, RK2 (Heun), RK4.
- Evidencia por ejecución: datos de entrada, fórmula, sustitución, desarrollo, tabla iteraciones/refinamiento, criterio de parada, estado, verificación, error abs/rel/% (o nota si referencia cero), residual/norma, sensibilidad.
- Conclusión numérica y conclusión del problema por escenario.
- Gráficos Chart.js basados en datos reales de ejecución.
- Persistencia en Neon PostgreSQL/SQLite local con historial, filtros, apertura, relanzado y comparación.

## Estructura
- `web/`: Flask app, templates, static CSS.
- `simtele/`: escenarios, referencias, métodos numéricos, servicio/orquestación, BD.
- `db/schema_pg.sql`: esquema SQL.
- `tests/`: pruebas pytest.

## Ejecución local (SQLite)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # opcional; sin DATABASE_URL usa simtele.db
flask --app web.app run --debug
```

## Ejecución con Neon
En `.env` define:
```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/neondb?sslmode=require
SECRET_KEY=una-clave-segura
```
Luego ejecuta igual con Flask/Gunicorn. La app crea tablas y hace migración aditiva básica.

## Pruebas
```bash
DATABASE_URL=sqlite:////tmp/simtele_test.db ./.venv/bin/python -m pytest -q
```

## Despliegue Render
- Build: `pip install -r requirements.txt`
- Start: `gunicorn web.app:app --bind 0.0.0.0:$PORT --timeout 120`
- Env vars: `DATABASE_URL`, `SECRET_KEY`
- Opcional: `PYTHON_VERSION=3.12.3` (o usar `runtime.txt` incluido)

Incluye `Procfile` y `runtime.txt` para despliegue directo.

## Nota académica
Los escenarios MAL CONDICIONADO se justifican con evidencia matemática (raíz doble, condición de matriz, Lebesgue/nodos, cercanía a resonancia), no solo por exigencia física.
