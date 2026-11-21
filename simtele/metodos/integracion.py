"""Integración numérica: trapecio compuesto, Simpson 1/3 compuesto, Romberg."""
from __future__ import annotations
import math
import numpy as np
from simtele.numerico import metricas_error, estado_resultado, ESTADOS


def _base(nombre, formula, datos, criterio):
    return {
        "metodo": nombre, "familia": "Integración", "formula": formula,
        "datos_entrada": datos, "criterio_parada": criterio,
        "iteraciones": [], "pasos": [], "desarrollo": [],
        "convergio": False, "estado": "no_convergio", "mensaje": "",
    }


def _finalizar(r, val, ref, max_iter_alcanzado=False, divergencia=False, no_aplicable=False, entrada_invalida=False, interrumpido=False, convergio=None):
    r["x"] = val
    if convergio is None:
        convergio = not any([no_aplicable, entrada_invalida, interrumpido, divergencia]) and val is not None
    r["convergio"] = bool(convergio)
    r["estado"] = estado_resultado(r["convergio"], max_iter_alcanzado=max_iter_alcanzado, divergencia=divergencia, no_aplicable=no_aplicable, entrada_invalida=entrada_invalida, interrumpido=interrumpido)
    r["estado_detalle"] = ESTADOS[r["estado"]]
    r["metrica_error"] = metricas_error(ref, val)
    r["referencia"] = {"integral_ref": ref}
    r["verificacion"] = {"aproximacion": val, "referencia": ref, **r["metrica_error"]}
    if not r.get("mensaje"):
        r["mensaje"] = r["estado_detalle"] + "."
    return r


def trapecio_compuesto(f, a, b, n, x_ref=None, nombre_f="f(x)"):
    datos = {"funcion": nombre_f, "a": a, "b": b, "n": n}
    formula = "T_n = h/2 * (f(x0)+2*sum_{i=1}^{n-1}f(xi)+f(xn)), h=(b-a)/n"
    r = _base("Trapecio compuesto", formula, datos, "Aplicación directa con n subintervalos")
    if n <= 0 or int(n) != n:
        r["mensaje"] = "n debe ser entero positivo."
        return _finalizar(r, None, x_ref, entrada_invalida=True)
    n = int(n)
    h = (b - a) / n
    try:
        xs = [a + i * h for i in range(n + 1)]
        ys = [f(x) for x in xs]
    except Exception as e:
        r["mensaje"] = f"Error al evaluar f: {e}"
        return _finalizar(r, None, x_ref, interrumpido=True)
    if not all(math.isfinite(y) for y in ys):
        r["mensaje"] = "Evaluación no finita en la función."
        return _finalizar(r, None, x_ref, interrumpido=True)
    s = ys[0] + ys[-1] + 2 * sum(ys[1:-1])
    val = h / 2 * s
    r["sustitucion"] = f"h={h:.6g}, n={n}, x0={a}, xn={b}"
    r["pasos"] = [{"paso": "Partición", "detalle": f"h={h}, nodos={n+1}"}, {"paso": "Suma", "detalle": f"f(x0)+f(xn)+2*sum={s:.10g}"}]
    r["iteraciones"] = [{"numero": i, "x": xs[i], "aproximacion": [ys[i]], "fx": ys[i]} for i in range(len(xs))]
    r["desarrollo"] = [f"T_{n}=({h:.6g}/2)*({s:.10g})={val:.10g}"]
    r["detalles"] = {"h": h, "n": n, "nodos": xs, "valores": ys}
    r["convergio"] = True
    r["mensaje"] = "Cálculo completado."
    return _finalizar(r, val, x_ref, convergio=True)


def simpson_13_compuesto(f, a, b, n, x_ref=None, nombre_f="f(x)"):
    datos = {"funcion": nombre_f, "a": a, "b": b, "n": n}
    formula = "S_n = h/3*(f(x0)+f(xn)+4*sum impares+2*sum pares), n par, h=(b-a)/n"
    r = _base("Simpson 1/3 compuesto", formula, datos, "Aplicación directa; requiere n par")
    if n <= 0 or int(n) != n:
        r["mensaje"] = "n debe ser entero positivo."
        return _finalizar(r, None, x_ref, entrada_invalida=True)
    n = int(n)
    if n % 2 != 0:
        r["mensaje"] = "Simpson 1/3 requiere número de subintervalos n par."
        return _finalizar(r, None, x_ref, entrada_invalida=True)
    h = (b - a) / n
    try:
        xs = [a + i * h for i in range(n + 1)]
        ys = [f(x) for x in xs]
    except Exception as e:
        r["mensaje"] = f"Error al evaluar f: {e}"
        return _finalizar(r, None, x_ref, interrumpido=True)
    if not all(math.isfinite(y) for y in ys):
        r["mensaje"] = "Evaluación no finita."
        return _finalizar(r, None, x_ref, interrumpido=True)
    imp = sum(ys[i] for i in range(1, n, 2))
    par = sum(ys[i] for i in range(2, n, 2))
    val = h / 3 * (ys[0] + ys[-1] + 4 * imp + 2 * par)
    r["sustitucion"] = f"h={h:.6g}, n={n} (par), suma impares={imp:.10g}, suma pares={par:.10g}"
    r["pasos"] = [{"paso": "Validación", "detalle": f"n={n} es par"}, {"paso": "Suma", "detalle": f"S=h/3(f0+fn+4*I+2*P)"}]
    r["iteraciones"] = [{"numero": i, "x": xs[i], "aproximacion": [ys[i]], "fx": ys[i], "peso": (1 if i in (0,n) else (4 if i%2==1 else 2))} for i in range(len(xs))]
    r["desarrollo"] = [f"S_{n}=({h:.6g}/3)*({ys[0]:.6g}+{ys[-1]:.6g}+4*{imp:.6g}+2*{par:.6g})={val:.10g}"]
    r["detalles"] = {"h": h, "n": n, "nodos": xs, "valores": ys}
    r["convergio"] = True
    r["mensaje"] = "Cálculo completado."
    return _finalizar(r, val, x_ref, convergio=True)


def romberg(f, a, b, max_nivel=5, tol=1e-10, x_ref=None, nombre_f="f(x)"):
    datos = {"funcion": nombre_f, "a": a, "b": b, "max_nivel": max_nivel, "tol": tol}
    formula = "R(k,0)=trapecio con 2^k; R(k,j)=R(k,j-1)+(R(k,j-1)-R(k-1,j-1))/(4^j-1)"
    r = _base("Romberg", formula, datos, f"Convergencia por |R(k,k)-R(k-1,k-1)| < {tol} o nivel máximo")
    if max_nivel < 1:
        r["mensaje"] = "max_nivel debe ser >= 1"
        return _finalizar(r, None, x_ref, entrada_invalida=True)
    R = [[0.0] * (max_nivel + 1) for _ in range(max_nivel + 1)]
    try:
        fa, fb = f(a), f(b)
    except Exception as e:
        r["mensaje"] = f"Error al evaluar f: {e}"
        return _finalizar(r, None, x_ref, interrumpido=True)
    R[0][0] = (b - a) * (fa + fb) / 2
    r["pasos"].append({"paso": "R(0,0)", "detalle": f"Trapecio base = {R[0][0]:.10g}"})
    convergio = False
    val = R[0][0]
    for k in range(1, max_nivel + 1):
        n = 2 ** k
        h = (b - a) / n
        try:
            s = sum(f(a + (2 * i - 1) * h) for i in range(1, 2 ** (k - 1) + 1))
        except Exception as e:
            r["mensaje"] = f"Error al evaluar f en nivel {k}: {e}"
            return _finalizar(r, None, x_ref, interrumpido=True)
        R[k][0] = 0.5 * R[k - 1][0] + h * s
        for j in range(1, k + 1):
            R[k][j] = R[k][j - 1] + (R[k][j - 1] - R[k - 1][j - 1]) / (4 ** j - 1)
        val = R[k][k]
        r["iteraciones"].append({"numero": k, "nivel": k, "aproximacion": [val], "R_kk": val, "R_k0": R[k][0]})
        r["desarrollo"].append(f"k={k}: R({k},{k})={val:.10g}")
        if k > 0 and abs(R[k][k] - R[k - 1][k - 1]) < tol:
            convergio = True
            r["mensaje"] = f"Convergió por diferencia entre diagonales < tol en nivel {k}."
            break
    tabla = []
    for i in range(max_nivel + 1):
        fila = []
        vacia = True
        for j in range(i + 1):
            fila.append(R[i][j]); vacia = False
        if not vacia:
            tabla.append(fila)
    r["tabla_romberg"] = tabla
    if not convergio:
        r["mensaje"] = f"Se alcanzó max_nivel={max_nivel} sin criterio de tolerancia." 
    r["convergio"] = True  # método ejecutado; criterio de convergencia informado en mensaje
    return _finalizar(r, val, x_ref, convergio=True)
