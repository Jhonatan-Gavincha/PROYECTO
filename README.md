# SIMTELE-RISK (Semana 2)
Simulador educativo de Métodos Numéricos. Datos sintéticos; no representa sistemas reales.

## Estructura
- `simtele/`: núcleo numérico (`raices.py`), escenarios, referencias analíticas, `servicio.py` (orquestación e interpretación), `bd.py` (persistencia).
- `web/`: aplicación Flask (`app.py`, plantillas, estilos).
- `db/schema_pg.sql`: esquema PostgreSQL (documentación; la app lo crea sola).
- `tests/`: pruebas con pytest.

## Local (SQLite)
```
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app web.app run --debug                        # http://127.0.0.1:5000
pytest
```

## Con Neon (PostgreSQL)
Copia `.env.example` a `.env` y pega la cadena de conexión de Neon en `DATABASE_URL`. No subas `.env` a GitHub.

## Despliegue en Render
Build: `pip install -r requirements.txt`  ·  Start: `gunicorn web.app:app`
Variables de entorno: `DATABASE_URL` (Neon) y `SECRET_KEY`.

## Cómo agregar un método nuevo
Escribe `f(tipo, params, ref) -> dict` en `simtele/servicio.py` y regístralo en `IMPLEMENTADOS`.
Devuelve: `metodo, convergio, iteraciones[], x, mensaje, tiempo_ms`.

## Reproducibilidad
Cada simulación guarda semilla y `hash_parametros` (parámetros + versión del modelo + versiones de Python/numpy).
"Relanzar" repite la corrida y compara el resultado con la original.
