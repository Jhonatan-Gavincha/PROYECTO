import os, tempfile
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, insert, select

def _setup_old_db(path):
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    from simtele import bd
    bd.reset_engine()
    eng = bd.get_engine()
    md = MetaData()
    caso = Table("caso_estudio", md, Column("id", Integer, primary_key=True), Column("nombre", String(160)), Column("modelo_version", String(40)))
    esc = Table("escenario", md, Column("id", Integer, primary_key=True), Column("caso_id", Integer), Column("tipo", String(40)), Column("parametros_json", Text), Column("fuente_datos", Text))
    md.create_all(eng)
    with eng.begin() as c:
        for nombre in ["Detención de emergencia", "Deterioro y mantenimiento", "Oscilaciones por viento", "Reconstrucción de sensores"]:
            cid = c.execute(insert(caso).values(nombre=nombre, modelo_version="2.0-semana2")).inserted_primary_key[0]
            for t in ["NORMAL","ESTRES","MAL_CONDICIONADO"]:
                c.execute(insert(esc).values(caso_id=cid, tipo=t, parametros_json="{}", fuente_datos="x"))
    return bd


def test_migracion_nombres_viejos_y_guardado(tmp_path):
    dbp = tmp_path / "old.db"
    bd = _setup_old_db(str(dbp))
    bd.init_db()
    from simtele import servicio
    res = servicio.ejecutar("detencion", "NORMAL", semilla=42)
    sid = bd.guardar_simulacion("detencion", "NORMAL", res["params"], res["semilla"], res["ejecuciones"], conclusiones=res.get("conclusiones"), comparacion=res.get("comparacion"), sensibilidad=res.get("sensibilidad"), metadatos=res.get("metadatos"))
    sim = bd.obtener_simulacion(sid)
    assert sim is not None
    assert sim["slug"] == "detencion"
    assert sim["nombre"] == "Detención de emergencia de cabinas"


def test_ui_todos_modulos_escenarios(tmp_path):
    dbp = tmp_path / "ui.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{dbp}"
    from simtele import bd
    bd.reset_engine()
    from web.app import create_app
    app = create_app(); app.config["TESTING"] = True
    c = app.test_client()
    for slug in ["detencion","deterioro","oscilaciones","sensores"]:
        for tipo in ["NORMAL","ESTRES","MAL_CONDICIONADO"]:
            r = c.post(f"/modulo/{slug}/ejecutar", data={"tipo": tipo})
            assert r.status_code == 302, (slug, tipo, r.status_code)
            p = c.get(r.headers["Location"])
            assert p.status_code == 200, (slug, tipo, p.status_code, p.data[:200])
            assert b"Not Found" not in p.data
