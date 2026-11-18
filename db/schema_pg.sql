-- Esquema equivalente en PostgreSQL (Neon). La app lo crea sola con SQLAlchemy (init_db);
-- este archivo sirve como documentación y para ejecutarlo a mano en el editor SQL de Neon.
CREATE TABLE IF NOT EXISTS caso_estudio (
  id SERIAL PRIMARY KEY, nombre VARCHAR(100) NOT NULL UNIQUE, modelo_version VARCHAR(50) NOT NULL);
CREATE TABLE IF NOT EXISTS escenario (
  id SERIAL PRIMARY KEY, caso_id INTEGER NOT NULL REFERENCES caso_estudio(id),
  tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('NORMAL','ESTRES','MAL_CONDICIONADO')),
  parametros_json TEXT NOT NULL, fuente_datos VARCHAR(200) NOT NULL, UNIQUE (caso_id, tipo));
CREATE TABLE IF NOT EXISTS simulacion (
  id SERIAL PRIMARY KEY, escenario_id INTEGER NOT NULL REFERENCES escenario(id),
  fecha VARCHAR(30) NOT NULL, usuario_equipo VARCHAR(100),
  estado VARCHAR(20) NOT NULL CHECK (estado IN ('PENDIENTE','COMPLETADA','ERROR')),
  semilla INTEGER, hash_parametros VARCHAR(64));
CREATE TABLE IF NOT EXISTS ejecucion_metodo (
  id SERIAL PRIMARY KEY, simulacion_id INTEGER NOT NULL REFERENCES simulacion(id) ON DELETE CASCADE,
  metodo VARCHAR(60) NOT NULL, tolerancia DOUBLE PRECISION, paso DOUBLE PRECISION, max_iter INTEGER,
  convergio BOOLEAN NOT NULL, tiempo_ms DOUBLE PRECISION);
CREATE TABLE IF NOT EXISTS iteracion_resultado (
  id SERIAL PRIMARY KEY, ejecucion_id INTEGER NOT NULL REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
  numero INTEGER NOT NULL, aproximacion_json TEXT NOT NULL,
  residual DOUBLE PRECISION, error_abs DOUBLE PRECISION, error_rel DOUBLE PRECISION,  -- NULL si referencia ~ 0
  UNIQUE (ejecucion_id, numero));
CREATE TABLE IF NOT EXISTS resultado_resumen (
  id SERIAL PRIMARY KEY, ejecucion_id INTEGER NOT NULL UNIQUE REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
  referencia TEXT, valor_json TEXT, metrica_error_json TEXT, interpretacion TEXT);
CREATE INDEX IF NOT EXISTS idx_escenario_caso ON escenario(caso_id);
CREATE INDEX IF NOT EXISTS idx_sim_escenario ON simulacion(escenario_id);
CREATE INDEX IF NOT EXISTS idx_ejec_sim ON ejecucion_metodo(simulacion_id);
CREATE INDEX IF NOT EXISTS idx_iter_ejec ON iteracion_resultado(ejecucion_id);
