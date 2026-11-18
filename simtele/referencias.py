"""Referencias analíticas (soluciones exactas) de cada caso. Sirven como 'x exacto' para medir errores."""
import math
import numpy as np


def ref_detencion(tipo, p):
    if tipo == "MAL_CONDICIONADO":
        v0, T, eps = p["v0"], p["T"], p["eps"]
        return {"raiz_doble": True, "t_raiz": T, "distancia_frenado": v0 * T / 3,
                "desplazamiento_raiz_por_eps": T * math.sqrt(eps / v0)}
    v0, a, tr = p["v0"], p["a"], p["tr"]
    d_reac, d_fren = v0 * tr, v0 ** 2 / (2 * a)
    ref = {"raiz_doble": False, "t_frenado": v0 / a, "t_total": tr + v0 / a,
           "d_reaccion": d_reac, "d_frenado": d_fren, "d_total": d_reac + d_fren}
    if "d_disp" in p:
        ref["exceso_sobre_disponible"] = ref["d_total"] - p["d_disp"]
    return ref


def raices_deterioro(p):
    """Raíces de beta t² + alpha t + (D0 − Du) = 0."""
    a, b, c = p["beta"], p["alpha"], p["D0"] - p["Du"]
    disc = b * b - 4 * a * c
    if abs(disc) < 1e-12:
        return [-b / (2 * a)]
    if disc < 0:
        return []
    s = math.sqrt(disc)
    return sorted([(-b - s) / (2 * a), (-b + s) / (2 * a)])


def ref_deterioro(tipo, p):
    r = raices_deterioro(p)
    pos = [x for x in r if x > 0]
    return {"raiz_doble": len(r) == 1, "raices": r, "t_estrella": min(pos) if pos else None}


def ref_oscilaciones(tipo, p):
    w0 = math.sqrt(p["k"] / p["m"]); z = p["zeta"]
    wd = w0 * math.sqrt(1 - z * z)
    ref = {"raiz_doble": False, "omega0": w0, "omega_d": wd, "c": 2 * z * math.sqrt(p["k"] * p["m"])}
    if p["F0"] == 0:
        ref["C2"] = z * w0 * p["x0"] / wd
    else:
        r = p["r"]; D = (1 - r * r) ** 2 + (2 * z * r) ** 2
        ref["factor_amplificacion"] = 1 / math.sqrt(D)
        ref["amplitud_estacionaria"] = p["F0"] / p["k"] / math.sqrt(D)
        dD = -4 * r * r * (1 - r * r) + 8 * z * z * r * r   # r·dD/dr
        ref["sensibilidad_a_r"] = abs(-0.5 * dD / D)
    return ref


def _lebesgue(nodos):
    xs = np.linspace(nodos.min(), nodos.max(), 20001); L = np.zeros_like(xs)
    for i in range(len(nodos)):
        li = np.ones_like(xs)
        for j in range(len(nodos)):
            if j != i:
                li *= (xs - nodos[j]) / (nodos[i] - nodos[j])
        L += np.abs(li)
    return float(L.max())


def ref_sensores(tipo, p):
    n = p["n"]; t = np.linspace(0, 2 * np.pi, n)
    ref = {"raiz_doble": False, "nodos_ocultos": [float(t[i]) for i in p["ocultos"]],
           "valores_exactos_ocultos": [float(np.sin(t[i])) for i in p["ocultos"]]}
    usados = np.delete(t, p["ocultos"])
    ref["lebesgue_nodos_usados"] = _lebesgue(usados)
    if tipo == "MAL_CONDICIONADO":
        k = np.arange(n)
        cheb = np.cos((2 * k + 1) * np.pi / (2 * n))
        ref["lebesgue_equiespaciados_todos"] = _lebesgue(t)
        ref["lebesgue_chebyshev"] = _lebesgue(cheb)
        ref["cota_amplificacion_ruido"] = ref["lebesgue_equiespaciados_todos"] * p["sigma"]
    return ref


REFERENCIAS = {"detencion": ref_detencion, "deterioro": ref_deterioro,
               "oscilaciones": ref_oscilaciones, "sensores": ref_sensores}
