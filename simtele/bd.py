"""Persistencia: SQLAlchemy Core. SQLite en local, PostgreSQL (Neon) si existe DATABASE_URL."""
from __future__ import annotations
import os, json, hashlib, platform
from datetime import datetime, timezone
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Text, Float, Boolean, delete,
                        ForeignKey, UniqueConstraint, CheckConstraint, select, func, insert, text)
from simtele.escenarios import CASOS, ESCENARIOS, MODELO_VERSION

MAX_ITER_GUARDADAS = 500
_engine = None
md = MetaData()

caso_estudio = Table("caso_estudio", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False, unique=True),
    Column("modelo_version", String(50), nullable=False))
escenario = Table("escenario", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("caso_id", Integer, ForeignKey("caso_estudio.id"), nullable=False, index=True),
    Column("tipo", String(20), nullable=False),
    Column("parametros_json", Text, nullable=False),
    Column("fuente_datos", String(200), nullable=False),
    UniqueConstraint("caso_id", "tipo"),
    CheckConstraint("tipo IN ('NORMAL','ESTRES','MAL_CONDICIONADO')", name="ck_tipo"))
simulacion = Table("simulacion", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("escenario_id", Integer, ForeignKey("escenario.id"), nullable=False, index=True),
    Column("fecha", String(30), nullable=False),
    Column("usuario_equipo", String(100)),
    Column("estado", String(20), nullable=False),
    Column("semilla", Integer),
    Column("hash_parametros", String(64)),
    Column("conclusiones_json", Text),
    Column("comparacion_json", Text),
    Column("sensibilidad_json", Text),
    Column("metadatos_json", Text),
    CheckConstraint("estado IN ('PENDIENTE','COMPLETADA','ERROR')", name="ck_estado"))
ejecucion_metodo = Table("ejecucion_metodo", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("simulacion_id", Integer, ForeignKey("simulacion.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("metodo", String(60), nullable=False),
    Column("tolerancia", Float), Column("paso", Float), Column("max_iter", Integer),
    Column("convergio", Boolean, nullable=False), Column("tiempo_ms", Float),
    Column("estado", String(40)), Column("criterio_parada", Text),
    Column("procedimiento_json", Text), Column("datos_entrada_json", Text),
    Column("grafico_json", Text), Column("error_pct", Float))
iteracion_resultado = Table("iteracion_resultado", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ejecucion_id", Integer, ForeignKey("ejecucion_metodo.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("numero", Integer, nullable=False),
    Column("aproximacion_json", Text, nullable=False),
    Column("residual", Float), Column("error_abs", Float), Column("error_rel", Float),
    UniqueConstraint("ejecucion_id", "numero"))
resultado_resumen = Table("resultado_resumen", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ejecucion_id", Integer, ForeignKey("ejecucion_metodo.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("referencia", Text), Column("valor_json", Text),
    Column("metrica_error_json", Text), Column("interpretacion", Text))


def get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "").strip()
        kw = {"pool_pre_ping": True}
        if not url:
            raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            url = "sqlite:///" + os.path.join(raiz, "simtele.db")
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        if url.startswith("sqlite"):
            kw = {"connect_args": {"check_same_thread": False}}
        _engine = create_engine(url, **kw)
        if url.startswith("sqlite"):
            from sqlalchemy import event
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    return _engine


def reset_engine():
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def _ensure_columns(eng):
    """Migración aditiva segura para BD existente."""
    stmts = [
        "ALTER TABLE simulacion ADD COLUMN IF NOT EXISTS conclusiones_json TEXT",
        "ALTER TABLE simulacion ADD COLUMN IF NOT EXISTS comparacion_json TEXT",
        "ALTER TABLE simulacion ADD COLUMN IF NOT EXISTS sensibilidad_json TEXT",
        "ALTER TABLE simulacion ADD COLUMN IF NOT EXISTS metadatos_json TEXT",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS estado VARCHAR(40)",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS criterio_parada TEXT",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS procedimiento_json TEXT",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS datos_entrada_json TEXT",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS grafico_json TEXT",
        "ALTER TABLE ejecucion_metodo ADD COLUMN IF NOT EXISTS error_pct FLOAT",
    ]
    dialect = eng.dialect.name
    with eng.begin() as c:
        for s in stmts:
            try:
                if dialect == "sqlite":
                    # SQLite no soporta IF NOT EXISTS en ADD COLUMN viejo; intentar simple
                    col = s.split(" ADD COLUMN IF NOT EXISTS ")[1]
                    table = s.split(" ALTER TABLE ")[-1].split(" ADD COLUMN")[0] if " ALTER TABLE " in s else s.split("ALTER TABLE ")[1].split(" ADD COLUMN")[0]
                    # better parse
                    parts = s.replace("ALTER TABLE ", "").split(" ADD COLUMN IF NOT EXISTS ")
                    table = parts[0]
                    col_def = parts[1]
                    c.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
                else:
                    c.execute(text(s))
            except Exception:
                pass


LEGACY_NOMBRES = {
    "Detención de emergencia": "detencion",
    "Deterioro y mantenimiento": "deterioro",
    "Oscilaciones por viento": "oscilaciones",
    "Reconstrucción de sensores": "sensores",
}


def _slug_por_nombre(nombre):
    for slug, caso in CASOS.items():
        if caso["nombre"] == nombre:
            return slug
    return LEGACY_NOMBRES.get(nombre)


def _resolver_caso_id(conn, slug):
    nombre = CASOS[slug]["nombre"]
    row = conn.execute(select(caso_estudio.c.id).where(caso_estudio.c.nombre == nombre)).first()
    if row:
        conn.execute(caso_estudio.update().where(caso_estudio.c.id == row.id).values(modelo_version=MODELO_VERSION))
        return row.id
    # compatibilidad con BD vieja
    for viejo, s in LEGACY_NOMBRES.items():
        if s == slug:
            row = conn.execute(select(caso_estudio.c.id).where(caso_estudio.c.nombre == viejo)).first()
            if row:
                conn.execute(caso_estudio.update().where(caso_estudio.c.id == row.id).values(nombre=nombre, modelo_version=MODELO_VERSION))
                return row.id
    return conn.execute(insert(caso_estudio).values(nombre=nombre, modelo_version=MODELO_VERSION)).inserted_primary_key[0]


def _resolver_escenario_id(conn, caso_id, slug, tipo):
    row = conn.execute(select(escenario.c.id).where(escenario.c.caso_id == caso_id, escenario.c.tipo == tipo)).first()
    if row:
        return row.id
    esc = ESCENARIOS[slug][tipo]
    return conn.execute(insert(escenario).values(
        caso_id=caso_id, tipo=tipo, parametros_json=json.dumps(esc["params"]),
        fuente_datos="Supuesto sintético (Sec. 9 del informe)")).inserted_primary_key[0]


def init_db():
    eng = get_engine()
    md.create_all(eng)
    _ensure_columns(eng)
    with eng.begin() as c:
        # sincronización aditiva/idempotente (incluye BD vieja con nombres distintos)
        for slug, caso in CASOS.items():
            cid = _resolver_caso_id(c, slug)
            for tipo, esc in ESCENARIOS[slug].items():
                _resolver_escenario_id(c, cid, slug, tipo)


def hash_parametros(slug, tipo, params, semilla):
    import numpy
    payload = json.dumps({"caso": slug, "tipo": tipo, "params": params, "semilla": semilla,
                          "modelo": MODELO_VERSION, "numpy": numpy.__version__,
                          "python": platform.python_version()}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _j(v):
    if v is None:
        return None
    return json.dumps(v, default=_json_default, allow_nan=False)


def _json_default(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (float,)):
        return o if math.isfinite(o) else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def guardar_simulacion(slug, tipo, params, semilla, ejecuciones, usuario="equipo", conclusiones=None, comparacion=None, sensibilidad=None, metadatos=None):
    eng = get_engine()
    with eng.begin() as c:
        cid = _resolver_caso_id(c, slug)
        eid = _resolver_escenario_id(c, cid, slug, tipo)
        valores_sim = dict(
            escenario_id=eid, fecha=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            usuario_equipo=usuario, estado="COMPLETADA", semilla=semilla,
            hash_parametros=hash_parametros(slug, tipo, params, semilla))
        # columnas extra si existen
        _try_set_extra(c, simulacion, valores_sim, {
            "conclusiones_json": _j(conclusiones),
            "comparacion_json": _j(comparacion),
            "sensibilidad_json": _j(sensibilidad),
            "metadatos_json": _j(metadatos),
        })
        sid = c.execute(insert(simulacion).values(**valores_sim)).inserted_primary_key[0]
        for ej in ejecuciones:
            metricas = ej.get("metrica_error") or {}
            vals_ej = dict(
                simulacion_id=sid, metodo=ej["metodo"], tolerancia=ej.get("tolerancia"),
                paso=ej.get("paso"), max_iter=ej.get("max_iter"),
                convergio=bool(ej.get("convergio")), tiempo_ms=ej.get("tiempo_ms"))
            _try_set_extra(c, ejecucion_metodo, vals_ej, {
                "estado": ej.get("estado"),
                "criterio_parada": ej.get("criterio_parada"),
                "procedimiento_json": _j({"formula": ej.get("formula"), "sustitucion": ej.get("sustitucion"), "desarrollo": ej.get("desarrollo"), "pasos": ej.get("pasos"), "matrices": ej.get("matrices"), "tabla_romberg": ej.get("tabla_romberg"), "coeficientes": ej.get("coeficientes"), "tabla_diferencias": ej.get("tabla_diferencias"), "coeficientes_tramos": ej.get("coeficientes_tramos"), "detalles": ej.get("detalles"), "variante": ej.get("variante")}),
                "datos_entrada_json": _j(ej.get("datos_entrada")),
                "grafico_json": _j(ej.get("grafico")),
                "error_pct": _num(metricas.get("error_pct") if metricas.get("error_pct") is not None else metricas.get("error_pct_max")),
            })
            xid = c.execute(insert(ejecucion_metodo).values(**vals_ej)).inserted_primary_key[0]
            filas = []
            for it in ej.get("iteraciones", [])[:MAX_ITER_GUARDADAS]:
                filas.append({
                    "ejecucion_id": xid, "numero": it.get("numero", len(filas)+1),
                    "aproximacion_json": _j(it.get("aproximacion", it.get("y", it.get("x")))),
                    "residual": _num(it.get("residual_norma", it.get("residual"))),
                    "error_abs": _num(it.get("error_abs")),
                    "error_rel": _num(it.get("error_rel")),
                })
            if filas:
                c.execute(insert(iteracion_resultado), filas)
            interpretacion = ej.get("interpretacion")
            if not isinstance(interpretacion, dict):
                interpretacion = {"texto": interpretacion} if interpretacion else {}
            interpretacion.setdefault("conclusion_numerica", ej.get("conclusion_numerica"))
            interpretacion.setdefault("conclusion_problema", ej.get("conclusion_problema"))
            c.execute(insert(resultado_resumen).values(
                ejecucion_id=xid, referencia=_j(ej.get("referencia")),
                valor_json=_j({"x": ej.get("x"), "n_iter": len(ej.get("iteraciones", [])),
                               "mensaje": ej.get("mensaje"), "estado": ej.get("estado"), "estado_detalle": ej.get("estado_detalle")}),
                metrica_error_json=_j(metricas),
                interpretacion=_j(interpretacion)))
    return sid


def _num(v):
    try:
        if v is None: return None
        f = float(v)
        if f != f or abs(f) == float('inf'): return None
        return f
    except Exception:
        return None


def _try_set_extra(conn, table, vals, extra):
    # solo setear si columna existe en tabla metadata/reflection simplificado: intentar con columnas conocidas
    for k, v in extra.items():
        if k in table.c:
            vals[k] = v


def listar_simulaciones(limite=50, caso=None, tipo=None, q=None):
    eng = get_engine()
    j = simulacion.join(escenario, simulacion.c.escenario_id == escenario.c.id)\
                  .join(caso_estudio, escenario.c.caso_id == caso_estudio.c.id)
    stmt = select(simulacion.c.id, simulacion.c.fecha, simulacion.c.estado, simulacion.c.hash_parametros,
                  escenario.c.tipo, caso_estudio.c.nombre).select_from(j)
    if caso:
        stmt = stmt.where(caso_estudio.c.nombre == caso)
    if tipo:
        stmt = stmt.where(escenario.c.tipo == tipo)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((caso_estudio.c.nombre.like(like)) | (escenario.c.tipo.like(like)) | (simulacion.c.hash_parametros.like(like)))
    stmt = stmt.order_by(simulacion.c.id.desc()).limit(limite)
    with eng.connect() as c:
        return [dict(r._mapping) for r in c.execute(stmt)]


def eliminar_simulacion(sid):
    eng = get_engine()
    with eng.begin() as c:
        row = c.execute(select(simulacion.c.id).where(simulacion.c.id == sid)).first()
        if not row:
            return False
        c.execute(delete(simulacion).where(simulacion.c.id == sid))
        return True


def obtener_simulacion(sid):
    eng = get_engine()
    with eng.connect() as c:
        j = simulacion.join(escenario, simulacion.c.escenario_id == escenario.c.id)\
                      .join(caso_estudio, escenario.c.caso_id == caso_estudio.c.id)
        srow = c.execute(select(simulacion, escenario.c.tipo, escenario.c.parametros_json,
                                caso_estudio.c.nombre).select_from(j)
                         .where(simulacion.c.id == sid)).first()
        if srow is None:
            return None
        s = dict(srow._mapping)
        s["params"] = json.loads(s.pop("parametros_json"))
        for k in ["conclusiones_json", "comparacion_json", "sensibilidad_json", "metadatos_json"]:
            if k in s and s[k]:
                try: s[k.replace("_json", "")] = json.loads(s[k])
                except Exception: s[k.replace("_json", "")] = None
        ejs = []
        for erow in c.execute(select(ejecucion_metodo).where(ejecucion_metodo.c.simulacion_id == sid)
                              .order_by(ejecucion_metodo.c.id)):
            e = dict(erow._mapping)
            e["iteraciones"] = [dict(i._mapping, aproximacion=json.loads(i.aproximacion_json))
                                for i in c.execute(select(iteracion_resultado)
                                                   .where(iteracion_resultado.c.ejecucion_id == e["id"])
                                                   .order_by(iteracion_resultado.c.numero))]
            for k in ["procedimiento_json", "datos_entrada_json", "grafico_json"]:
                if k in e and e[k]:
                    try: e[k.replace("_json", "")] = json.loads(e[k])
                    except Exception: e[k.replace("_json", "")] = None
            rrow = c.execute(select(resultado_resumen).where(resultado_resumen.c.ejecucion_id == e["id"])).first()
            if rrow:
                e["referencia"] = json.loads(rrow.referencia) if rrow.referencia else None
                e["valor"] = json.loads(rrow.valor_json) if rrow.valor_json else None
                e["metrica_error"] = json.loads(rrow.metrica_error_json) if rrow.metrica_error_json else None
                e["interpretacion"] = json.loads(rrow.interpretacion) if rrow.interpretacion else None
            if isinstance(e.get("interpretacion"), dict):
                e.setdefault("conclusion_numerica", e["interpretacion"].get("conclusion_numerica"))
                e.setdefault("conclusion_problema", e["interpretacion"].get("conclusion_problema"))
            ejs.append(e)
        s["ejecuciones"] = ejs
        s["slug"] = _slug_por_nombre(s.get("nombre"))
        return s
