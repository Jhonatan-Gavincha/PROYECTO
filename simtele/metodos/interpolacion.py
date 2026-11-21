"""Interpolación: Lagrange, Newton diferencias divididas, Spline cúbico natural."""
from __future__ import annotations
import math
import numpy as np
from simtele.numerico import metricas_error, ESTADOS


def _base(nombre, formula, datos, criterio):
    return {
        "metodo": nombre, "familia": "Interpolación", "formula": formula,
        "datos_entrada": datos, "criterio_parada": criterio,
        "iteraciones": [], "pasos": [], "desarrollo": [],
        "convergio": True, "estado": "convergio", "estado_detalle": ESTADOS["convergio"],
        "mensaje": "Evaluación completada.",
    }


def _validar_nodos(x, y):
    x = np.array(x, dtype=float).reshape(-1)
    y = np.array(y, dtype=float).reshape(-1)
    if x.size != y.size:
        raise ValueError("x e y deben tener el mismo tamaño")
    if x.size < 2:
        raise ValueError("Se requieren al menos 2 nodos")
    if len(set(x.tolist())) != x.size:
        raise ValueError("Nodos duplicados: el método no los admite")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Nodos/valores deben ser finitos")
    return x, y


def lagrange(x, y, x_eval, y_ref=None):
    x, y = _validar_nodos(x, y)
    xe = np.array(x_eval, dtype=float).reshape(-1)
    datos = {"nodos_x": x.tolist(), "nodos_y": y.tolist(), "x_eval": xe.tolist()}
    formula = "P(x)=sum_{i=0}^{n} y_i * L_i(x), L_i(x)=prod_{j!=i}(x-x_j)/(x_i-x_j)"
    r = _base("Lagrange", formula, datos, "Construcción/evaluación directa del polinomio")
    r["sustitucion"] = f"n={len(x)} nodos; evaluación en {xe.tolist()}"
    for i in range(len(x)):
        denom = np.prod([x[i]-x[j] for j in range(len(x)) if j != i])
        r["pasos"].append({"paso": f"L_{i}", "detalle": f"denominador L_{i}={denom:.6g}, y_{i}={y[i]:.6g}"})
    def eval_point(xp):
        total = 0.0
        for i in range(len(x)):
            li = 1.0
            for j in range(len(x)):
                if j != i:
                    li *= (xp - x[j]) / (x[i] - x[j])
            total += y[i] * li
        return float(total)
    preds = [eval_point(float(xp)) for xp in xe]
    r["x"] = preds
    rows = []
    for k, xp in enumerate(xe.tolist()):
        ref = None if y_ref is None else float(np.array(y_ref).reshape(-1)[k])
        ap = preds[k]
        rows.append({"numero": k+1, "x": xp, "valor_verdadero": ref, "aproximacion": [ap], "error_abs": None if ref is None else abs(ref-ap), "error_rel": (abs(ref-ap)/abs(ref) if ref not in (None,0) else None), "error_rel_nota": ("No definido (referencia cero)" if ref==0 else None)})
    r["iteraciones"] = rows
    r["tabla_evaluacion"] = rows
    r["metrica_error"] = _metricas_eval(rows)
    r["verificacion"] = {"puntos_ocultos": rows}
    r["desarrollo"] = [f"P({xp})={preds[i]:.10g}" for i, xp in enumerate(xe.tolist()[:3])]
    return r


def newton_diferencias_divididas(x, y, x_eval, y_ref=None):
    x, y = _validar_nodos(x, y)
    xe = np.array(x_eval, dtype=float).reshape(-1)
    n = len(x)
    coef = np.zeros((n, n), dtype=float)
    coef[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            coef[i, j] = (coef[i + 1, j - 1] - coef[i, j - 1]) / (x[i + j] - x[i])
    datos = {"nodos_x": x.tolist(), "nodos_y": y.tolist(), "x_eval": xe.tolist()}
    formula = "P(x)=f[x0]+f[x0,x1](x-x0)+...+f[x0,..,xn]prod(x-xi)"
    r = _base("Newton (diferencias divididas)", formula, datos, "Construcción directa por tabla de diferencias divididas")
    r["coeficientes"] = coef[0, :].tolist()
    r["tabla_diferencias"] = coef.tolist()
    r["pasos"].append({"paso": "Tabla", "detalle": f"Coeficientes b_k=f[x0..xk]={r['coeficientes']}"})
    def eval_point(xp):
        val = coef[0, n - 1]
        for k in range(n - 2, -1, -1):
            val = val * (xp - x[k]) + coef[0, k]
        return float(val)
    preds = [eval_point(float(xp)) for xp in xe]
    r["x"] = preds
    rows = []
    for k, xp in enumerate(xe.tolist()):
        ref = None if y_ref is None else float(np.array(y_ref).reshape(-1)[k])
        ap = preds[k]
        rows.append({"numero": k+1, "x": xp, "valor_verdadero": ref, "aproximacion": [ap], "error_abs": None if ref is None else abs(ref-ap), "error_rel": (abs(ref-ap)/abs(ref) if ref not in (None,0) else None), "error_rel_nota": ("No definido (referencia cero)" if ref==0 else None)})
    r["iteraciones"] = rows
    r["tabla_evaluacion"] = rows
    r["metrica_error"] = _metricas_eval(rows)
    r["desarrollo"] = [f"b_{i}={r['coeficientes'][i]:.8g}" for i in range(min(4, n))]
    return r


def spline_cubico(x, y, x_eval, y_ref=None, tipo="natural"):
    x, y = _validar_nodos(x, y)
    order = np.argsort(x)
    x, y = x[order], y[order]
    xe = np.array(x_eval, dtype=float).reshape(-1)
    n = len(x)
    if n < 3:
        raise ValueError("Spline cúbico requiere al menos 3 nodos")
    h = np.diff(x)
    if np.any(h <= 0):
        raise ValueError("Nodos deben estar ordenados y ser distintos")
    # Natural cubic spline: M0=Mn-1=0, tridiagonal for M1..Mn-2
    A = np.zeros((n, n))
    rhs = np.zeros(n)
    A[0, 0] = 1.0
    A[-1, -1] = 1.0
    for i in range(1, n - 1):
        A[i, i - 1] = h[i - 1]
        A[i, i] = 2 * (h[i - 1] + h[i])
        A[i, i + 1] = h[i]
        rhs[i] = 6 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    M = np.linalg.solve(A, rhs)
    coefs = []
    for i in range(n - 1):
        ai = y[i]
        bi = (y[i + 1] - y[i]) / h[i] - h[i] * (2 * M[i] + M[i + 1]) / 6
        ci = M[i] / 2
        di = (M[i + 1] - M[i]) / (6 * h[i])
        coefs.append({"tramo": i+1, "intervalo": [float(x[i]), float(x[i+1])], "a": float(ai), "b": float(bi), "c": float(ci), "d": float(di)})
    datos = {"nodos_x": x.tolist(), "nodos_y": y.tolist(), "x_eval": xe.tolist(), "tipo": tipo}
    formula = "S_i(x)=a_i+b_i(x-x_i)+c_i(x-x_i)^2+d_i(x-x_i)^3; spline natural: M_0=M_{n-1}=0"
    r = _base("Spline cúbico natural", formula, datos, "Resolver sistema tridiagonal para segundas derivadas y evaluar por tramos")
    r["sustitucion"] = f"n={n} nodos, tipo={tipo}, condiciones frontera S''(x0)=S''(xn)=0"
    r["pasos"].append({"paso": "Sistema", "detalle": "Sistema tridiagonal para M_i=S''(x_i) resuelto por numpy.linalg.solve"})
    r["matrices"] = {"A": A.tolist(), "rhs": rhs.tolist(), "M": M.tolist()}
    r["coeficientes_tramos"] = coefs
    def eval_point(xp):
        # clamp/extrap not used; find interval
        if xp <= x[0]:
            i = 0
        elif xp >= x[-1]:
            i = n - 2
        else:
            i = int(np.searchsorted(x, xp) - 1)
            i = min(max(i, 0), n - 2)
        dx = xp - x[i]
        c = coefs[i]
        return float(c["a"] + c["b"]*dx + c["c"]*dx*dx + c["d"]*dx*dx*dx)
    preds = [eval_point(float(xp)) for xp in xe]
    r["x"] = preds
    rows = []
    for k, xp in enumerate(xe.tolist()):
        ref = None if y_ref is None else float(np.array(y_ref).reshape(-1)[k])
        ap = preds[k]
        rows.append({"numero": k+1, "x": xp, "valor_verdadero": ref, "aproximacion": [ap], "error_abs": None if ref is None else abs(ref-ap), "error_rel": (abs(ref-ap)/abs(ref) if ref not in (None,0) else None), "error_rel_nota": ("No definido (referencia cero)" if ref==0 else None)})
    r["iteraciones"] = rows
    r["tabla_evaluacion"] = rows
    r["metrica_error"] = _metricas_eval(rows)
    r["desarrollo"] = [f"Tramo {c['tramo']}: [{c['intervalo'][0]:.4g},{c['intervalo'][1]:.4g}] a={c['a']:.4g},b={c['b']:.4g},c={c['c']:.4g},d={c['d']:.4g}" for c in coefs[:3]]
    # continuidad check at internal nodes
    cont = []
    for i in range(1, n-1):
        left = coefs[i-1]; right = coefs[i]
        dx = x[i]-x[i-1]
        s_left = left["a"] + left["b"]*dx + left["c"]*dx*dx + left["d"]*dx*dx*dx
        s_right = right["a"]
        ds_left = left["b"] + 2*left["c"]*dx + 3*left["d"]*dx*dx
        ds_right = right["b"]
        d2s_left = 2*left["c"] + 6*left["d"]*dx
        d2s_right = 2*right["c"]
        cont.append({"nodo": float(x[i]), "S": abs(s_left-s_right), "S1": abs(ds_left-ds_right), "S2": abs(d2s_left-d2s_right)})
    r["verificacion"] = {"continuidad": cont, "puntos_ocultos": rows}
    return r


def _metricas_eval(rows):
    abs_errs = [r["error_abs"] for r in rows if r.get("error_abs") is not None]
    rel_errs = [r["error_rel"] for r in rows if r.get("error_rel") is not None]
    abs_max = max(abs_errs) if abs_errs else None
    rel_max = max(rel_errs) if rel_errs else None
    return {
        "error_abs": abs_max,
        "error_abs_max": abs_max,
        "error_abs_prom": sum(abs_errs)/len(abs_errs) if abs_errs else None,
        "error_rel": rel_max,
        "error_rel_max": rel_max,
        "error_pct": (rel_max * 100.0 if rel_max is not None else None),
        "error_rel_nota": None if rel_errs else ("No definido (referencia cero)" if any(r.get("error_rel_nota") for r in rows) else "No disponible"),
    }
