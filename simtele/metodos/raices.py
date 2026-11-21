"""Métodos de raíces con evidencia completa."""
from __future__ import annotations
import math
from simtele.numerico import metricas_error, estado_resultado, ESTADOS


def _base(nombre, formula, datos, criterio):
    return {
        "metodo": nombre, "familia": "Raíces", "formula": formula,
        "datos_entrada": datos, "criterio_parada": criterio,
        "iteraciones": [], "pasos": [], "desarrollo": [],
        "convergio": False, "estado": "no_convergio", "mensaje": "",
    }


def _finalizar(r, x, ref, residual, max_iter_alcanzado=False, divergencia=False, no_aplicable=False, entrada_invalida=False, interrumpido=False):
    r["x"] = x
    r["convergio"] = bool(r.get("convergio")) and not any([divergencia, no_aplicable, entrada_invalida, interrumpido])
    r["estado"] = estado_resultado(r["convergio"], max_iter_alcanzado=max_iter_alcanzado, divergencia=divergencia, no_aplicable=no_aplicable, entrada_invalida=entrada_invalida, interrumpido=interrumpido)
    r["estado_detalle"] = ESTADOS[r["estado"]]
    r["residual"] = residual
    r["metrica_error"] = metricas_error(ref, x, residual=residual)
    r["referencia"] = {"x_ref": ref}
    r["verificacion"] = {
        "referencia": ref,
        "aproximacion": x,
        "residual": residual,
        "error_abs": r["metrica_error"]["error_abs"],
        "error_rel": r["metrica_error"]["error_rel"],
        "error_rel_nota": r["metrica_error"]["error_rel_nota"],
    }
    if not r.get("mensaje"):
        r["mensaje"] = r["estado_detalle"] + "."
    return r


def biseccion(f, a, b, tol=1e-10, max_iter=200, x_ref=None, nombre_f="f(t)"):
    datos = {"funcion": nombre_f, "a": a, "b": b, "tol": tol, "max_iter": max_iter}
    formula = "c_k=(a_k+b_k)/2; elegir subintervalo con cambio de signo"
    criterio = f"|f(c_k)| < {tol} o (b_k-a_k)/2 < {tol} o k=max_iter"
    r = _base("Bisección", formula, datos, criterio)
    try:
        fa, fb = f(a), f(b)
    except Exception as e:
        r["mensaje"] = f"Error al evaluar la función: {e}"
        return _finalizar(r, None, x_ref, None, interrumpido=True)
    if not all(map(math.isfinite, [a, b, fa, fb])):
        r["mensaje"] = "Entrada inválida: a, b o f(a), f(b) no finitos."
        return _finalizar(r, None, x_ref, None, entrada_invalida=True)
    r["sustitucion"] = f"a_0={a}, b_0={b}, f(a_0)={fa:.6g}, f(b_0)={fb:.6g}, tol={tol}"
    r["pasos"].append({"paso": "Evaluación inicial", "detalle": r["sustitucion"]})
    if fa == 0:
        r["convergio"] = True
        r["iteraciones"].append({"numero": 0, "a": a, "b": b, "aproximacion": [a], "f_aprox": fa, "residual": 0.0, "error_abs": abs(a-x_ref) if x_ref is not None else None, "error_rel": (abs(a-x_ref)/abs(x_ref) if x_ref not in (None,0) else None), "intervalo": [a,b]})
        r["mensaje"] = "La raíz está en el extremo a."
        return _finalizar(r, a, x_ref, 0.0)
    if fb == 0:
        r["convergio"] = True
        r["iteraciones"].append({"numero": 0, "a": a, "b": b, "aproximacion": [b], "f_aprox": fb, "residual": 0.0, "error_abs": abs(b-x_ref) if x_ref is not None else None, "error_rel": (abs(b-x_ref)/abs(x_ref) if x_ref not in (None,0) else None), "intervalo": [a,b]})
        r["mensaje"] = "La raíz está en el extremo b."
        return _finalizar(r, b, x_ref, 0.0)
    if fa * fb > 0:
        r["mensaje"] = f"No hay cambio de signo en [{a}, {b}]: f(a)={fa:.6g}, f(b)={fb:.6g}. Bisección no aplicable."
        return _finalizar(r, None, x_ref, None, no_aplicable=True)
    c = a
    for k in range(1, max_iter + 1):
        c = (a + b) / 2
        try:
            fc = f(c)
        except Exception as e:
            r["mensaje"] = f"Error numérico al evaluar f(c) en iteración {k}: {e}"
            return _finalizar(r, c, x_ref, None, interrumpido=True)
        ea = abs(c - x_ref) if x_ref is not None else None
        er = (ea / abs(x_ref) if x_ref not in (None, 0) and ea is not None else None)
        it = {"numero": k, "a": a, "b": b, "aproximacion": [c], "f_aprox": fc, "residual": abs(fc), "error_abs": ea, "error_rel": er, "intervalo": [a, b], "ancho_intervalo": b-a}
        r["iteraciones"].append(it)
        if k <= 3:
            r["desarrollo"].append(f"k={k}: c=( {a:.6g}+{b:.6g})/2={c:.6g}, f(c)={fc:.6g}, intervalo=[{a:.6g},{b:.6g}]")
        if abs(fc) < tol or (b - a) / 2 < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k} por {'|f(c)|<tol' if abs(fc)<tol else 'ancho de intervalo/2<tol'}."
            return _finalizar(r, c, x_ref, abs(fc))
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    r["mensaje"] = f"Se alcanzó max_iter={max_iter} sin satisfacer tolerancia."
    return _finalizar(r, c, x_ref, abs(f(c)), max_iter_alcanzado=True)


def newton_raphson(f, df, x0, tol=1e-10, max_iter=100, x_ref=None, nombre_f="f(t)", nombre_df="f'(t)"):
    datos = {"funcion": nombre_f, "derivada": nombre_df, "x0": x0, "tol": tol, "max_iter": max_iter}
    formula = "x_{k+1}=x_k-f(x_k)/f'(x_k)"
    criterio = f"|f(x_k)| < {tol} o |x_k-x_{{k-1}}| < {tol} o derivada nula/pequeña o k=max_iter"
    r = _base("Newton-Raphson", formula, datos, criterio)
    r["sustitucion"] = f"x_0={x0}, tol={tol}, max_iter={max_iter}"
    x = x0
    prev = None
    for k in range(1, max_iter + 1):
        try:
            fx = f(x); dfx = df(x)
        except Exception as e:
            r["mensaje"] = f"Error numérico en iteración {k}: {e}"
            return _finalizar(r, x, x_ref, None, interrumpido=True)
        if not math.isfinite(fx) or not math.isfinite(dfx):
            r["mensaje"] = f"Valor no finito en iteración {k}."
            return _finalizar(r, x, x_ref, None, interrumpido=True)
        if abs(dfx) < 1e-14:
            r["mensaje"] = f"Derivada nula o muy pequeña en k={k} (f'={dfx:.3g}); Newton no aplicable."
            it = {"numero": k, "aproximacion": [x], "f_aprox": fx, "df_aprox": dfx, "residual": abs(fx), "error_abs": abs(x-x_ref) if x_ref is not None else None, "error_rel": (abs(x-x_ref)/abs(x_ref) if x_ref not in (None,0) else None), "error_iter": abs(x-prev) if prev is not None else None}
            r["iteraciones"].append(it)
            return _finalizar(r, x, x_ref, abs(fx), no_aplicable=True)
        x1 = x - fx / dfx
        ea = abs(x1 - x_ref) if x_ref is not None else None
        er = (ea / abs(x_ref) if x_ref not in (None, 0) and ea is not None else None)
        e_iter = abs(x1 - x)
        it = {"numero": k, "aproximacion": [x1], "x_prev": x, "f_aprox": fx, "df_aprox": dfx, "residual": abs(f(x1)) if math.isfinite(x1) else None, "error_abs": ea, "error_rel": er, "error_iter": e_iter}
        r["iteraciones"].append(it)
        if k <= 3:
            r["desarrollo"].append(f"k={k}: x_{k}=x_{k-1}-f(x_{k-1})/f'(x_{k-1})={x:.6g}-({fx:.6g})/({dfx:.6g})={x1:.6g}")
        if not math.isfinite(x1):
            r["mensaje"] = "Divergencia: aproximación no finita."
            return _finalizar(r, x, x_ref, abs(fx), divergencia=True)
        if abs(f(x1)) < tol or e_iter < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k}."
            return _finalizar(r, x1, x_ref, abs(f(x1)))
        if abs(x1) > 1e12:
            r["mensaje"] = "Divergencia: la aproximación creció excesivamente."
            return _finalizar(r, x1, x_ref, abs(f(x1)) if math.isfinite(f(x1)) else None, divergencia=True)
        prev, x = x, x1
    r["mensaje"] = f"Se alcanzó max_iter={max_iter} sin converger."
    try:
        res = abs(f(x))
    except Exception:
        res = None
    return _finalizar(r, x, x_ref, res, max_iter_alcanzado=True)


def secante(f, x0, x1, tol=1e-10, max_iter=100, x_ref=None, nombre_f="f(t)"):
    datos = {"funcion": nombre_f, "x0": x0, "x1": x1, "tol": tol, "max_iter": max_iter}
    formula = "x_{k+1}=x_k-f(x_k)*(x_k-x_{k-1})/(f(x_k)-f(x_{k-1}))"
    criterio = f"|f(x_k)| < {tol} o |x_k-x_{{k-1}}| < {tol} o denominador nulo/pequeño o k=max_iter"
    r = _base("Secante", formula, datos, criterio)
    r["sustitucion"] = f"x_0={x0}, x_1={x1}, tol={tol}"
    try:
        f0, f1 = f(x0), f(x1)
    except Exception as e:
        r["mensaje"] = f"Error al evaluar semillas: {e}"
        return _finalizar(r, None, x_ref, None, interrumpido=True)
    prev, cur = x0, x1
    fprev, fcur = f0, f1
    for k in range(1, max_iter + 1):
        denom = fcur - fprev
        if abs(denom) < 1e-14:
            r["mensaje"] = f"Denominador nulo o muy pequeño en k={k}; secante no aplicable."
            r["iteraciones"].append({"numero": k, "aproximacion": [cur], "x_prev": prev, "f_aprox": fcur, "residual": abs(fcur), "error_abs": abs(cur-x_ref) if x_ref is not None else None, "error_rel": (abs(cur-x_ref)/abs(x_ref) if x_ref not in (None,0) else None), "error_iter": abs(cur-prev)})
            return _finalizar(r, cur, x_ref, abs(fcur), no_aplicable=True)
        x2 = cur - fcur * (cur - prev) / denom
        try:
            f2 = f(x2)
        except Exception as e:
            r["mensaje"] = f"Error numérico en k={k}: {e}"
            return _finalizar(r, x2, x_ref, None, interrumpido=True)
        ea = abs(x2 - x_ref) if x_ref is not None else None
        er = (ea / abs(x_ref) if x_ref not in (None, 0) and ea is not None else None)
        e_iter = abs(x2 - cur)
        it = {"numero": k, "aproximacion": [x2], "x_prev": cur, "x_prev2": prev, "f_aprox": fcur, "f_prev": fprev, "residual": abs(f2), "error_abs": ea, "error_rel": er, "error_iter": e_iter}
        r["iteraciones"].append(it)
        if k <= 3:
            r["desarrollo"].append(f"k={k}: x_{k+1}={cur:.6g}-({fcur:.6g})*({cur:.6g}-{prev:.6g})/({fcur:.6g}-{fprev:.6g})={x2:.6g}")
        if not math.isfinite(x2) or abs(x2) > 1e12:
            r["mensaje"] = "Divergencia: aproximación no finita o excesiva."
            return _finalizar(r, x2, x_ref, abs(f2) if math.isfinite(f2) else None, divergencia=True)
        if abs(f2) < tol or e_iter < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k}."
            return _finalizar(r, x2, x_ref, abs(f2))
        prev, cur, fprev, fcur = cur, x2, fcur, f2
    r["mensaje"] = f"Se alcanzó max_iter={max_iter} sin converger."
    try:
        res = abs(f(cur))
    except Exception:
        res = None
    return _finalizar(r, cur, x_ref, res, max_iter_alcanzado=True)
