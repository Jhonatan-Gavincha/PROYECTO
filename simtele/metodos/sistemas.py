"""Métodos de sistemas lineales: Jacobi, Gauss-Seidel, LU, Gradiente Conjugado."""
from __future__ import annotations
import math
import numpy as np
from simtele.numerico import metricas_error, estado_resultado, ESTADOS, norma


def _base(nombre, formula, datos, criterio):
    return {
        "metodo": nombre, "familia": "Sistemas lineales", "formula": formula,
        "datos_entrada": datos, "criterio_parada": criterio,
        "iteraciones": [], "pasos": [], "desarrollo": [],
        "convergio": False, "estado": "no_convergio", "mensaje": "",
    }


def _finalizar(r, x, x_ref, residual_vec, max_iter_alcanzado=False, divergencia=False, no_aplicable=False, entrada_invalida=False, interrumpido=False):
    r["x"] = None if x is None else np.array(x, dtype=float).tolist()
    res_norm = None if residual_vec is None else float(norma(residual_vec))
    r["convergio"] = bool(r.get("convergio")) and not any([divergencia, no_aplicable, entrada_invalida, interrumpido])
    r["estado"] = estado_resultado(r["convergio"], max_iter_alcanzado=max_iter_alcanzado, divergencia=divergencia, no_aplicable=no_aplicable, entrada_invalida=entrada_invalida, interrumpido=interrumpido)
    r["estado_detalle"] = ESTADOS[r["estado"]]
    r["residual"] = residual_vec.tolist() if residual_vec is not None else None
    r["residual_norma"] = res_norm
    ref_norm = None if x_ref is None or x is None else float(norma(np.array(x_ref)-np.array(x)))
    ref_den = None if x_ref is None else float(norma(x_ref))
    rel = None if ref_norm is None or ref_den in (None, 0) else ref_norm / ref_den
    r["metrica_error"] = {
        "error_abs": ref_norm,
        "error_rel": rel,
        "error_pct": None if rel is None else rel * 100,
        "error_rel_nota": None if rel is not None else ("No definido (referencia cero)" if ref_den == 0 else "No disponible"),
        "error_pct_nota": None if rel is not None else ("No definido (referencia cero)" if ref_den == 0 else "No disponible"),
        "residual_norma": res_norm,
    }
    r["referencia"] = {"x_ref": None if x_ref is None else np.array(x_ref, dtype=float).tolist()}
    r["verificacion"] = {"residual_norma_2": res_norm, "residual": r["residual"]}
    if not r.get("mensaje"):
        r["mensaje"] = r["estado_detalle"] + "."
    return r


def numero_condicion(A, ord=2):
    A = np.array(A, dtype=float)
    return float(np.linalg.cond(A, ord))


def _validar_sistema(A, b, x0=None):
    A = np.array(A, dtype=float)
    b = np.array(b, dtype=float).reshape(-1)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("A debe ser cuadrada")
    if b.shape[0] != A.shape[0]:
        raise ValueError("Dimensiones incompatibles entre A y b")
    if not np.all(np.isfinite(A)) or not np.all(np.isfinite(b)):
        raise ValueError("A y b deben ser finitos")
    if x0 is None:
        x0 = np.zeros(A.shape[0], dtype=float)
    else:
        x0 = np.array(x0, dtype=float).reshape(-1)
        if x0.shape[0] != A.shape[0]:
            raise ValueError("x0 incompatible")
    return A, b, x0


def jacobi(A, b, x0=None, tol=1e-10, max_iter=200, x_ref=None):
    datos = {"A": np.array(A).tolist(), "b": np.array(b).tolist(), "x0": [] if x0 is None else np.array(x0).tolist(), "tol": tol, "max_iter": max_iter}
    formula = "x_i^(k+1) = (b_i - sum_{j!=i} a_ij x_j^(k)) / a_ii"
    r = _base("Jacobi", formula, datos, f"||x^(k)-x^(k-1)||_2 < {tol} o ||r||_2 < {tol} o k=max_iter")
    try:
        A, b, x = _validar_sistema(A, b, x0)
    except Exception as e:
        r["mensaje"] = str(e)
        return _finalizar(r, None, x_ref, None, entrada_invalida=True)
    D = np.diag(A)
    if np.any(np.isclose(D, 0.0)):
        r["mensaje"] = "Método no aplicable: hay ceros en la diagonal."
        return _finalizar(r, None, x_ref, b - A @ x, no_aplicable=True)
    r["sustitucion"] = f"A {A.shape[0]}x{A.shape[1]}, diag={np.diag(A).tolist()}, x0={x.tolist()}"
    r["pasos"].append({"paso": "Verificación", "detalle": "Se requiere a_ii != 0. Dominancia diagonal es condición suficiente, no necesaria."})
    for k in range(1, max_iter + 1):
        x_new = x.copy()
        for i in range(A.shape[0]):
            s = sum(A[i, j] * x[j] for j in range(A.shape[1]) if j != i)
            x_new[i] = (b[i] - s) / A[i, i]
        err_iter = float(norma(x_new - x))
        res = b - A @ x_new
        res_norm = float(norma(res))
        it = {"numero": k, "aproximacion": x_new.tolist(), "residual_norma": res_norm, "error_iter": err_iter}
        if x_ref is not None:
            e = float(norma(x_new - np.array(x_ref)))
            it["error_abs"] = e
            den = float(norma(x_ref))
            it["error_rel"] = None if den == 0 else e / den
        r["iteraciones"].append(it)
        if k <= 2:
            r["desarrollo"].append(f"k={k}: x={x_new.tolist()}, ||x_k-x_(k-1)||={err_iter:.3e}, ||r||={res_norm:.3e}")
        if not np.all(np.isfinite(x_new)) or err_iter > 1e12 or res_norm > 1e12:
            r["mensaje"] = "Divergencia detectada."
            return _finalizar(r, x_new, x_ref, res, divergencia=True)
        x = x_new
        if err_iter < tol or res_norm < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k}."
            return _finalizar(r, x, x_ref, res)
    res = b - A @ x
    r["mensaje"] = f"Se alcanzó max_iter={max_iter}."
    return _finalizar(r, x, x_ref, res, max_iter_alcanzado=True)


def gauss_seidel(A, b, x0=None, tol=1e-10, max_iter=200, x_ref=None):
    datos = {"A": np.array(A).tolist(), "b": np.array(b).tolist(), "x0": [] if x0 is None else np.array(x0).tolist(), "tol": tol, "max_iter": max_iter}
    formula = "x_i^(k+1) = (b_i - sum_{j<i} a_ij x_j^(k+1) - sum_{j>i} a_ij x_j^(k)) / a_ii"
    r = _base("Gauss-Seidel", formula, datos, f"||x^(k)-x^(k-1)||_2 < {tol} o ||r||_2 < {tol} o k=max_iter")
    try:
        A, b, x = _validar_sistema(A, b, x0)
    except Exception as e:
        r["mensaje"] = str(e)
        return _finalizar(r, None, x_ref, None, entrada_invalida=True)
    D = np.diag(A)
    if np.any(np.isclose(D, 0.0)):
        r["mensaje"] = "Método no aplicable: hay ceros en la diagonal."
        return _finalizar(r, None, x_ref, b - A @ x, no_aplicable=True)
    r["sustitucion"] = f"A {A.shape[0]}x{A.shape[1]}, x0={x.tolist()}"
    for k in range(1, max_iter + 1):
        x_old = x.copy()
        for i in range(A.shape[0]):
            s1 = sum(A[i, j] * x[j] for j in range(i))
            s2 = sum(A[i, j] * x_old[j] for j in range(i + 1, A.shape[1]))
            x[i] = (b[i] - s1 - s2) / A[i, i]
        err_iter = float(norma(x - x_old))
        res = b - A @ x
        res_norm = float(norma(res))
        it = {"numero": k, "aproximacion": x.tolist(), "residual_norma": res_norm, "error_iter": err_iter}
        if x_ref is not None:
            e = float(norma(x - np.array(x_ref)))
            it["error_abs"] = e
            den = float(norma(x_ref))
            it["error_rel"] = None if den == 0 else e / den
        r["iteraciones"].append(it)
        if k <= 2:
            r["desarrollo"].append(f"k={k}: x={x.tolist()}, ||delta||={err_iter:.3e}, ||r||={res_norm:.3e}")
        if not np.all(np.isfinite(x)) or err_iter > 1e12 or res_norm > 1e12:
            r["mensaje"] = "Divergencia detectada."
            return _finalizar(r, x, x_ref, res, divergencia=True)
        if err_iter < tol or res_norm < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k}."
            return _finalizar(r, x, x_ref, res)
    res = b - A @ x
    r["mensaje"] = f"Se alcanzó max_iter={max_iter}."
    return _finalizar(r, x, x_ref, res, max_iter_alcanzado=True)


def lu_solve(A, b, x_ref=None):
    datos = {"A": np.array(A).tolist(), "b": np.array(b).tolist()}
    formula = "A=LU (Doolittle con pivoteo parcial); Ly=Pb; Ux=y"
    r = _base("Factorización LU", formula, datos, "Factorización directa con pivoteo parcial")
    try:
        A, b, _ = _validar_sistema(A, b)
    except Exception as e:
        r["mensaje"] = str(e)
        return _finalizar(r, None, x_ref, None, entrada_invalida=True)
    n = A.shape[0]
    U = A.copy().astype(float)
    L = np.eye(n)
    P = np.eye(n)
    perm = list(range(n))
    pasos = []
    for k in range(n - 1):
        pivot = max(range(k, n), key=lambda i: abs(U[i, k]))
        if abs(U[pivot, k]) < 1e-14:
            r["mensaje"] = "Matriz singular o casi singular; LU no aplicable."
            return _finalizar(r, None, x_ref, b - A @ np.zeros(n), no_aplicable=True)
        if pivot != k:
            U[[k, pivot], k:] = U[[pivot, k], k:]
            L[[k, pivot], :k] = L[[pivot, k], :k]
            P[[k, pivot], :] = P[[pivot, k], :]
            perm[k], perm[pivot] = perm[pivot], perm[k]
            pasos.append(f"Pivoteo: intercambio filas {k} <-> {pivot}")
        for i in range(k + 1, n):
            L[i, k] = U[i, k] / U[k, k]
            U[i, k:] = U[i, k:] - L[i, k] * U[k, k:]
            U[i, k] = 0.0
    if abs(U[n - 1, n - 1]) < 1e-14:
        r["mensaje"] = "Matriz singular; LU no aplicable."
        return _finalizar(r, None, x_ref, b - A @ np.zeros(n), no_aplicable=True)
    Pb = P @ b
    # forward Ly=Pb
    y = np.zeros(n)
    for i in range(n):
        y[i] = Pb[i] - np.dot(L[i, :i], y[:i])
    # backward Ux=y
    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - np.dot(U[i, i + 1:], x[i + 1:])) / U[i, i]
    res = b - A @ x
    r["pasos"] = [{"paso": "Factorización", "detalle": p} for p in pasos]
    r["pasos"].append({"paso": "Ly=Pb", "detalle": f"y={y.tolist()}"})
    r["pasos"].append({"paso": "Ux=y", "detalle": f"x={x.tolist()}"})
    r["desarrollo"] = pasos[:3] + [f"Sustitución hacia adelante: y={y.tolist()}", f"Sustitución hacia atrás: x={x.tolist()}"]
    r["matrices"] = {"P": P.tolist(), "L": L.tolist(), "U": U.tolist(), "Pb": Pb.tolist(), "y": y.tolist()}
    r["convergio"] = True
    r["mensaje"] = "Factorización directa completada."
    r["iteraciones"] = [{"numero": 1, "aproximacion": x.tolist(), "residual_norma": float(norma(res)), "error_iter": None}]
    return _finalizar(r, x, x_ref, res)


def gradiente_conjugado(A, b, x0=None, tol=1e-10, max_iter=200, x_ref=None):
    datos = {"A": np.array(A).tolist(), "b": np.array(b).tolist(), "x0": [] if x0 is None else np.array(x0).tolist(), "tol": tol, "max_iter": max_iter}
    formula = "r_k=b-Ax_k; alpha_k=r_k^T r_k/(p_k^T A p_k); x_{k+1}=x_k+alpha_k p_k; r_{k+1}=r_k-alpha_k A p_k; beta_k=r_{k+1}^T r_{k+1}/(r_k^T r_k); p_{k+1}=r_{k+1}+beta_k p_k"
    r = _base("Gradiente conjugado", formula, datos, f"||r_k||_2 < {tol} o k=max_iter; requiere A simétrica definida positiva")
    try:
        A, b, x = _validar_sistema(A, b, x0)
    except Exception as e:
        r["mensaje"] = str(e)
        return _finalizar(r, None, x_ref, None, entrada_invalida=True)
    simetrica = np.allclose(A, A.T, atol=1e-10)
    r["pasos"].append({"paso": "Verificación SPD", "detalle": f"Simétrica: {simetrica}"})
    if not simetrica:
        r["mensaje"] = "No aplicable: la matriz no es simétrica; GC estándar requiere SPD."
        return _finalizar(r, None, x_ref, b - A @ x, no_aplicable=True)
    try:
        eig = np.linalg.eigvalsh(A)
        spd = bool(np.all(eig > 0))
        r["pasos"].append({"paso": "Autovalores", "detalle": f"min(lambda)={float(np.min(eig)):.6g}, max(lambda)={float(np.max(eig)):.6g}, SPD={spd}"})
    except Exception:
        spd = False
    if not spd:
        r["mensaje"] = "No aplicable: la matriz no es definida positiva (autovalor <= 0)."
        return _finalizar(r, None, x_ref, b - A @ x, no_aplicable=True)
    rmat = b - A @ x
    p = rmat.copy()
    rsold = float(np.dot(rmat, rmat))
    r["sustitucion"] = f"x0={x.tolist()}, r0=b-Ax0, ||r0||={math.sqrt(rsold):.6g}"
    for k in range(1, max_iter + 1):
        Ap = A @ p
        denom = float(np.dot(p, Ap))
        if abs(denom) < 1e-14:
            r["mensaje"] = "Interrupción numérica: denominador p^T A p casi nulo."
            return _finalizar(r, x, x_ref, rmat, interrumpido=True)
        alpha = rsold / denom
        x = x + alpha * p
        rmat = rmat - alpha * Ap
        rsnew = float(np.dot(rmat, rmat))
        err_iter = abs(alpha) * float(norma(p))
        res_norm = math.sqrt(rsnew)
        it = {"numero": k, "aproximacion": x.tolist(), "residual_norma": res_norm, "error_iter": err_iter, "alpha": float(alpha), "beta": None, "r": rmat.tolist(), "p": p.tolist()}
        if x_ref is not None:
            e = float(norma(x - np.array(x_ref)))
            it["error_abs"] = e
            den = float(norma(x_ref))
            it["error_rel"] = None if den == 0 else e / den
        if k <= 2:
            r["desarrollo"].append(f"k={k}: alpha={alpha:.6g}, ||r||={res_norm:.3e}, x={x.tolist()}")
        if res_norm < tol:
            r["convergio"] = True
            r["mensaje"] = f"Convergió en k={k}."
            r["iteraciones"].append(it)
            return _finalizar(r, x, x_ref, rmat)
        beta = rsnew / rsold if rsold != 0 else 0.0
        it["beta"] = float(beta)
        r["iteraciones"].append(it)
        p = rmat + beta * p
        rsold = rsnew
        if not np.all(np.isfinite(x)) or res_norm > 1e12:
            r["mensaje"] = "Divergencia detectada."
            return _finalizar(r, x, x_ref, rmat, divergencia=True)
    r["mensaje"] = f"Se alcanzó max_iter={max_iter}."
    return _finalizar(r, x, x_ref, rmat, max_iter_alcanzado=True)
