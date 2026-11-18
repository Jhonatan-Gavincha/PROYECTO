"""Persistencia: SQLAlchemy Core. SQLite en local, PostgreSQL (Neon) si existe DATABASE_URL."""
import os, json, hashlib, platform
from datetime import datetime, timezone
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Text, Float, Boolean,
                        ForeignKey, UniqueConstraint, CheckConstraint, select, func, insert)
from simtele.escenarios import CASOS, ESCENARIOS, MODELO_VERSION

MAX_ITER_GUARDADAS = 200
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
    CheckConstraint("estado IN ('PENDIENTE','COMPLETADA','ERROR')", name="ck_estado"))
ejecucion_metodo = Table("ejecucion_metodo", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("simulacion_id", Integer, ForeignKey("simulacion.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("metodo", String(60), nullable=False),
    Column("tolerancia", Float), Column("paso", Float), Column("max_iter", Integer),
    Column("convergio", Boolean, nullable=False), Column("tiempo_ms", Float))
iteracion_resultado = Table("iteracion_resultado", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ejecucion_id", Integer, ForeignKey("ejecucion_metodo.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("numero", Integer, nullable=False),
    Column("aproximacion_json", Text, nullable=False),
    Column("residual", Float), Column("error_abs", Float), Column("error_rel", Float),   # error_rel NULL si ref ~ 0
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
        kw = {"pool_pre_ping": True}            # Neon se suspende por inactividad: reconecta solo
        if not url:
            raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            url = "sqlite:///" + os.path.join(raiz, "simtele.db")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("sqlite"):
            kw = {}
        _engine = create_engine(url, **kw)
    return _engine


def reset_engine():
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_db():
    eng = get_engine()
    md.create_all(eng)
    with eng.begin() as c:
        if c.execute(select(func.count()).select_from(caso_estudio)).scalar() == 0:
            for slug, caso in CASOS.items():
                cid = c.execute(insert(caso_estudio).values(
                    nombre=caso["nombre"], modelo_version=MODELO_VERSION)).inserted_primary_key[0]
                for tipo, esc in ESCENARIOS[slug].items():
                    c.execute(insert(escenario).values(
                        caso_id=cid, tipo=tipo, parametros_json=json.dumps(esc["params"]),
                        fuente_datos="Supuesto sintético (Sec. 9 del informe)"))


def hash_parametros(slug, tipo, params, semilla):
    """Hash reproducible: parámetros + versión del modelo + versiones de Python/numpy."""
    import numpy
    payload = json.dumps({"caso": slug, "tipo": tipo, "params": params, "semilla": semilla,
                          "modelo": MODELO_VERSION, "numpy": numpy.__version__,
                          "python": platform.python_version()}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def guardar_simulacion(slug, tipo, params, semilla, ejecuciones, usuario="equipo"):
    eng = get_engine()
    nombre = CASOS[slug]["nombre"]
    with eng.begin() as c:
        cid = c.execute(select(caso_estudio.c.id).where(caso_estudio.c.nombre == nombre)).scalar_one()
        eid = c.execute(select(escenario.c.id).where(
            escenario.c.caso_id == cid, escenario.c.tipo == tipo)).scalar_one()
        sid = c.execute(insert(simulacion).values(
            escenario_id=eid, fecha=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            usuario_equipo=usuario, estado="COMPLETADA", semilla=semilla,
            hash_parametros=hash_parametros(slug, tipo, params, semilla))).inserted_primary_key[0]
        for ej in ejecuciones:
            xid = c.execute(insert(ejecucion_metodo).values(
                simulacion_id=sid, metodo=ej["metodo"], tolerancia=ej.get("tolerancia"),
                paso=ej.get("paso"), max_iter=ej.get("max_iter"),
                convergio=bool(ej["convergio"]), tiempo_ms=ej.get("tiempo_ms"))).inserted_primary_key[0]
            filas = [{"ejecucion_id": xid, "numero": it["numero"],
                      "aproximacion_json": json.dumps(it["aproximacion"]), "residual": it.get("residual"),
                      "error_abs": it.get("error_abs"), "error_rel": it.get("error_rel")}
                     for it in ej["iteraciones"][:MAX_ITER_GUARDADAS]]
            if filas:
                c.execute(insert(iteracion_resultado), filas)
            c.execute(insert(resultado_resumen).values(
                ejecucion_id=xid, referencia=json.dumps(ej.get("referencia")),
                valor_json=json.dumps({"x": ej.get("x"), "n_iter": len(ej["iteraciones"]),
                                       "mensaje": ej.get("mensaje")}),
                metrica_error_json=json.dumps(ej.get("metrica_error")),
                interpretacion=json.dumps(ej.get("interpretacion"))))
    return sid


def listar_simulaciones(limite=50):
    eng = get_engine()
    j = simulacion.join(escenario, simulacion.c.escenario_id == escenario.c.id)\
                  .join(caso_estudio, escenario.c.caso_id == caso_estudio.c.id)
    q = select(simulacion.c.id, simulacion.c.fecha, simulacion.c.estado, simulacion.c.hash_parametros,
               escenario.c.tipo, caso_estudio.c.nombre).select_from(j)\
        .order_by(simulacion.c.id.desc()).limit(limite)
    with eng.connect() as c:
        return [dict(r._mapping) for r in c.execute(q)]


def obtener_simulacion(sid):
    eng = get_engine()
    with eng.connect() as c:
        j = simulacion.join(escenario, simulacion.c.escenario_id == escenario.c.id)\
                      .join(caso_estudio, escenario.c.caso_id == caso_estudio.c.id)
        s = c.execute(select(simulacion, escenario.c.tipo, escenario.c.parametros_json,
                             caso_estudio.c.nombre).select_from(j)
                      .where(simulacion.c.id == sid)).first()
        if s is None:
            return None
        s = dict(s._mapping)
        s["params"] = json.loads(s.pop("parametros_json"))
        ejs = []
        for e in c.execute(select(ejecucion_metodo).where(ejecucion_metodo.c.simulacion_id == sid)
                           .order_by(ejecucion_metodo.c.id)):
            e = dict(e._mapping)
            e["iteraciones"] = [dict(i._mapping, aproximacion=json.loads(i.aproximacion_json))
                                for i in c.execute(select(iteracion_resultado)
                                                   .where(iteracion_resultado.c.ejecucion_id == e["id"])
                                                   .order_by(iteracion_resultado.c.numero))]
            r = c.execute(select(resultado_resumen).where(resultado_resumen.c.ejecucion_id == e["id"])).first()
            if r:
                e["referencia"] = json.loads(r.referencia) if r.referencia else None
                e["valor"] = json.loads(r.valor_json) if r.valor_json else None
                e["metrica_error"] = json.loads(r.metrica_error_json) if r.metrica_error_json else None
                e["interpretacion"] = json.loads(r.interpretacion) if r.interpretacion else None
            ejs.append(e)
        s["ejecuciones"] = ejs
        return s
