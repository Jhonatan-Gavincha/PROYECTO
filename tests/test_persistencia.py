import os
from simtele import bd, servicio

def test_persistencia_reinicio(tmp_path, monkeypatch):
    db = tmp_path/'p.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    bd.reset_engine(); bd.init_db()
    res = servicio.ejecutar('detencion','NORMAL', semilla=42)
    sid = bd.guardar_simulacion('detencion','NORMAL',res['params'],res['semilla'],res['ejecuciones'],conclusiones=res.get('conclusiones'),comparacion=res.get('comparacion'),sensibilidad=res.get('sensibilidad'))
    # simular reinicio
    bd.reset_engine(); bd.init_db()
    sim = bd.obtener_simulacion(sid)
    assert sim is not None
    assert sim['nombre'].startswith('Detención')
    assert len(sim['ejecuciones']) == len(res['ejecuciones'])
    assert sim['conclusiones']['numerica']
    # repetir
    old = servicio.ESCENARIOS['detencion']['NORMAL']['params']
    servicio.ESCENARIOS['detencion']['NORMAL']['params'] = sim['params']
    try:
        res2 = servicio.ejecutar('detencion','NORMAL', semilla=sim['semilla'])
    finally:
        servicio.ESCENARIOS['detencion']['NORMAL']['params'] = old
    assert len(res2['ejecuciones']) == len(sim['ejecuciones'])
