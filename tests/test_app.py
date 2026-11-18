import math, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from simtele import bd
from simtele.escenarios import ESCENARIOS
from simtele.referencias import ref_deterioro, ref_detencion, ref_oscilaciones, ref_sensores
from simtele.raices import biseccion


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    bd.reset_engine()
    from web.app import create_app
    app = create_app(); app.config["TESTING"] = True
    yield app.test_client()
    bd.reset_engine()


def test_referencias_informe():
    assert ref_deterioro("NORMAL", ESCENARIOS["deterioro"]["NORMAL"]["params"])["t_estrella"] == pytest.approx(12.7698, abs=1e-4)
    assert ref_deterioro("ESTRES", ESCENARIOS["deterioro"]["ESTRES"]["params"])["t_estrella"] == pytest.approx(9.3623, abs=1e-4)
    r = ref_deterioro("MAL_CONDICIONADO", ESCENARIOS["deterioro"]["MAL_CONDICIONADO"]["params"])
    assert r["raiz_doble"] and r["t_estrella"] == pytest.approx(10.0)
    d = ref_detencion("ESTRES", ESCENARIOS["detencion"]["ESTRES"]["params"])
    assert d["d_total"] == pytest.approx(48) and d["exceso_sobre_disponible"] == pytest.approx(8)
    assert d["t_total"] == pytest.approx(14)            # t_total = t_r + v0/a (corrige 12 s de la Sem. 1)
    o = ref_oscilaciones("MAL_CONDICIONADO", ESCENARIOS["oscilaciones"]["MAL_CONDICIONADO"]["params"])
    assert o["factor_amplificacion"] == pytest.approx(35.6, abs=0.1) and o["sensibilidad_a_r"] == pytest.approx(49.0, abs=0.1)
    s = ref_sensores("MAL_CONDICIONADO", ESCENARIOS["sensores"]["MAL_CONDICIONADO"]["params"])
    assert s["lebesgue_chebyshev"] == pytest.approx(2.48, abs=0.02)


def test_biseccion_raiz_doble_falla():
    r = biseccion(lambda t: -0.002 * (t - 10) ** 2, 0, 60)
    assert r["convergio"] is False


def test_flujo_completo_guardar_recuperar_relanzar(cliente):
    for ruta in ["/", "/modulo/detencion", "/modulo/deterioro", "/modulo/oscilaciones", "/modulo/sensores", "/historial", "/salud"]:
        assert cliente.get(ruta).status_code == 200, ruta
    r = cliente.post("/modulo/deterioro/ejecutar", data={"tipo": "NORMAL"})
    assert r.status_code == 302
    pag = cliente.get(r.headers["Location"])
    assert pag.status_code == 200 and b"12.769" in pag.data
    api = cliente.get("/api/resultado/1").get_json()
    assert api["ejecuciones"][0]["convergio"] is True
    rr = cliente.post("/resultado/1/relanzar")
    assert "igual=1" in rr.headers["Location"]
    assert b"ID\xc3\x89NTICO" in cliente.get(rr.headers["Location"]).data
    m = cliente.post("/modulo/deterioro/ejecutar", data={"tipo": "MAL_CONDICIONADO"})
    assert b"no convergi" in cliente.get(m.headers["Location"]).data
    assert cliente.post("/modulo/deterioro/ejecutar", data={"tipo": "XX"}).status_code == 400
    assert cliente.get("/modulo/nada").status_code == 404
