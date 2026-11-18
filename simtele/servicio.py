"""Orquestación: ejecuta los métodos implementados de un caso/escenario y arma la interpretación.

Para agregar un método nuevo: escribe una función  f(tipo, params, ref) -> dict  y regístrala en IMPLEMENTADOS.
El dict debe traer: metodo, convergio, iteraciones[], x, mensaje, (tolerancia, paso, max_iter, tiempo_ms opcionales).
"""
import time
from simtele.escenarios import CASOS, ESCENARIOS
from simtele.referencias import REFERENCIAS
from simtele.raices import biseccion


def interpretar(ej, ref, params):
    """Las cuatro categorías de criterio son banderas INDEPENDIENTES (no excluyentes)."""
    n = len(ej["iteraciones"])
    banderas = {
        "riesgo_fisico": bool(ref.get("exceso_sobre_disponible", 0) and ref["exceso_sobre_disponible"] > 0),
        "alta_exigencia": n > 100,
        "mal_condicionamiento": bool(ref.get("raiz_doble")),
        "falta_convergencia": not ej["convergio"],
    }
    txt = []
    if banderas["falta_convergencia"]:
        txt.append("El algoritmo NO convergió: " + ej.get("mensaje", ""))
    if banderas["mal_condicionamiento"]:
        txt.append("La raíz es doble: el problema es hipersensible a pequeñas perturbaciones en los datos "
                   "(mal condicionamiento intrínseco), independiente del método elegido.")
    if banderas["alta_exigencia"]:
        txt.append(f"Costo alto: {n} iteraciones.")
    if banderas["riesgo_fisico"]:
        txt.append("Riesgo físico modelado: se excede la distancia disponible (no es un error numérico).")
    if not any(banderas.values()):
        txt.append("Sin alertas: el método convergió y el problema está bien planteado.")
    txt.append("Datos sintéticos: no permite inferir nada sobre componentes reales.")
    return {"banderas": banderas, "texto": " ".join(txt)}


def _m2_biseccion(tipo, p, ref):
    f = lambda t: p["D0"] + p["alpha"] * t + p["beta"] * t * t - p["Du"]
    t0 = time.perf_counter()
    r = biseccion(f, 0.0, 60.0, tol=1e-10, max_iter=200, x_ref=ref["t_estrella"])
    r.update(metodo="Bisección", tolerancia=1e-10, max_iter=200,
             tiempo_ms=(time.perf_counter() - t0) * 1000,
             referencia={"t_estrella": ref["t_estrella"], "intervalo": [0.0, 60.0]})
    if r["iteraciones"]:
        u = r["iteraciones"][-1]
        r["metrica_error"] = {"error_abs": u["error_abs"], "error_rel": u["error_rel"], "residual": u["residual"]}
    return r


IMPLEMENTADOS = {("deterioro", "Bisección"): _m2_biseccion}


def ejecutar(slug, tipo, semilla=42):
    params = ESCENARIOS[slug][tipo]["params"]
    ref = REFERENCIAS[slug](tipo, params)
    ejecuciones, pendientes = [], []
    for metodo in CASOS[slug]["metodos"]:
        impl = IMPLEMENTADOS.get((slug, metodo))
        if impl is None:
            pendientes.append(metodo)
            continue
        ej = impl(tipo, params, ref)
        ej["interpretacion"] = interpretar(ej, ref, params)
        ejecuciones.append(ej)
    return {"slug": slug, "tipo": tipo, "params": params, "semilla": semilla,
            "referencia": ref, "ejecuciones": ejecuciones, "pendientes": pendientes}
