"""EDO: RK2 (Heun) y RK4 para sistemas x'=f(t,x)."""
from __future__ import annotations
import math
import numpy as np
from simtele.numerico import metricas_error, estado_resultado, ESTADOS


def _base(nombre, formula, datos, criterio, variante=None):
    return {
        "metodo": nombre, "familia": "EDO", "formula": formula, "variante": variante,
        "datos_entrada": datos, "criterio_parada": criterio,
        "iteraciones": [], "pasos": [], "desarrollo": [],
        "convergio": False, "estado": "no_convergio", "mensaje": "",
    }


def _finalizar(r, y_final, t_final, ref_final=None, max_iter_alcanzado=False, divergencia=False, entrada_invalida=False, interrumpido=False):
    r["x"] = None if y_final is None else np.array(y_final, dtype=float).tolist()
    r["t_final"] = t_final
    r["convergio"] = not any([divergencia, entrada_invalida, interrumpido]) and y_final is not None
    r["estado"] = estado_resultado(r["convergio"], max_iter_alcanzado=max_iter_alcanzado, divergencia=divergencia, entrada_invalida=entrada_invalida, interrumpido=interrumpido)
    r["estado_detalle"] = ESTADOS[r["estado"]]
    # metricas against scalar ref if provided
    ref_scalar = ref_final
    aprox_scalar = None if y_final is None else float(np.array(y_final).reshape(-1)[0])
    r["metrica_error"] = metricas_error(ref_scalar, aprox_scalar)
    r["referencia"] = {"y_ref_final": ref_final}
    r["verificacion"] = {"y_final": r["x"], "y_ref_final": ref_final}
    if not r.get("mensaje"):
        r["mensaje"] = r["estado_detalle"] + "."
    return r


def rk2(f, t0, y0, h, n_pasos, ref_fn=None, nombre_sistema="x'=f(t,x)"):
    """RK2 Heun (Euler mejorado)."""
    datos = {"sistema": nombre_sistema, "t0": t0, "y0": list(np.array(y0).reshape(-1)), "h": h, "n_pasos": n_pasos}
    formula = "k1=f(t_n,y_n); k2=f(t_n+h,y_n+h*k1); y_{n+1}=y_n+h/2*(k1+k2)"
    r = _base("RK2 (Heun)", formula, datos, "Avance fijo por n_pasos", variante="Heun/Euler mejorado")
    if h <= 0 or n_pasos <= 0:
        r["mensaje"] = "h y n_pasos deben ser positivos."
        return _finalizar(r, None, t0, entrada_invalida=True)
    t = float(t0)
    y = np.array(y0, dtype=float).reshape(-1)
    r["sustitucion"] = f"t0={t}, y0={y.tolist()}, h={h}, n={n_pasos}"
    r["iteraciones"].append({"numero": 0, "t": t, "aproximacion": y.tolist(), "y": y.tolist(), "error_abs": _err_ref(ref_fn, t, y)})
    for k in range(1, n_pasos + 1):
        try:
            k1 = np.array(f(t, y), dtype=float).reshape(-1)
            y_pred = y + h * k1
            k2 = np.array(f(t + h, y_pred), dtype=float).reshape(-1)
            y_new = y + h * (k1 + k2) / 2
        except Exception as e:
            r["mensaje"] = f"Error numérico en paso {k}: {e}"
            return _finalizar(r, y, t, interrumpido=True)
        t_new = t + h
        if not np.all(np.isfinite(y_new)):
            r["mensaje"] = f"Divergencia/no finito en paso {k}."
            return _finalizar(r, y, t, divergencia=True)
        it = {"numero": k, "t": t_new, "aproximacion": y_new.tolist(), "y": y_new.tolist(), "k1": k1.tolist(), "k2": k2.tolist(), "error_abs": _err_ref(ref_fn, t_new, y_new)}
        r["iteraciones"].append(it)
        if k <= 2:
            r["desarrollo"].append(f"k={k}: k1={k1.tolist()}, k2={k2.tolist()}, y_{k}={y_new.tolist()}")
        t, y = t_new, y_new
    ref_final = None if ref_fn is None else float(np.array(ref_fn(t)).reshape(-1)[0])
    r["mensaje"] = f"Integración completada en {n_pasos} pasos con h={h}."
    r["convergio"] = True
    return _finalizar(r, y, t, ref_final=ref_final)


def rk4(f, t0, y0, h, n_pasos, ref_fn=None, nombre_sistema="x'=f(t,x)"):
    datos = {"sistema": nombre_sistema, "t0": t0, "y0": list(np.array(y0).reshape(-1)), "h": h, "n_pasos": n_pasos}
    formula = "k1=f(t_n,y_n); k2=f(t_n+h/2,y_n+h*k1/2); k3=f(t_n+h/2,y_n+h*k2/2); k4=f(t_n+h,y_n+h*k3); y_{n+1}=y_n+h/6*(k1+2k2+2k3+k4)"
    r = _base("RK4", formula, datos, "Avance fijo por n_pasos")
    if h <= 0 or n_pasos <= 0:
        r["mensaje"] = "h y n_pasos deben ser positivos."
        return _finalizar(r, None, t0, entrada_invalida=True)
    t = float(t0)
    y = np.array(y0, dtype=float).reshape(-1)
    r["sustitucion"] = f"t0={t}, y0={y.tolist()}, h={h}, n={n_pasos}"
    r["iteraciones"].append({"numero": 0, "t": t, "aproximacion": y.tolist(), "y": y.tolist(), "error_abs": _err_ref(ref_fn, t, y)})
    for k in range(1, n_pasos + 1):
        try:
            k1 = np.array(f(t, y), dtype=float).reshape(-1)
            k2 = np.array(f(t + h/2, y + h*k1/2), dtype=float).reshape(-1)
            k3 = np.array(f(t + h/2, y + h*k2/2), dtype=float).reshape(-1)
            k4 = np.array(f(t + h, y + h*k3), dtype=float).reshape(-1)
            y_new = y + h * (k1 + 2*k2 + 2*k3 + k4) / 6
        except Exception as e:
            r["mensaje"] = f"Error numérico en paso {k}: {e}"
            return _finalizar(r, y, t, interrumpido=True)
        t_new = t + h
        if not np.all(np.isfinite(y_new)):
            r["mensaje"] = f"Divergencia/no finito en paso {k}."
            return _finalizar(r, y, t, divergencia=True)
        it = {"numero": k, "t": t_new, "aproximacion": y_new.tolist(), "y": y_new.tolist(), "k1": k1.tolist(), "k2": k2.tolist(), "k3": k3.tolist(), "k4": k4.tolist(), "error_abs": _err_ref(ref_fn, t_new, y_new)}
        r["iteraciones"].append(it)
        if k <= 2:
            r["desarrollo"].append(f"k={k}: k1={k1.tolist()}, k2={k2.tolist()}, k3={k3.tolist()}, k4={k4.tolist()}, y_{k}={y_new.tolist()}")
        t, y = t_new, y_new
    ref_final = None if ref_fn is None else float(np.array(ref_fn(t)).reshape(-1)[0])
    r["mensaje"] = f"Integración completada en {n_pasos} pasos con h={h}."
    r["convergio"] = True
    return _finalizar(r, y, t, ref_final=ref_final)


def _err_ref(ref_fn, t, y):
    if ref_fn is None:
        return None
    try:
        ref = np.array(ref_fn(t), dtype=float).reshape(-1)
        yy = np.array(y, dtype=float).reshape(-1)
        return float(np.linalg.norm(ref - yy))
    except Exception:
        return None
