"""Métodos de raíces. Cada método devuelve un dict estándar para poder persistirlo."""


def _err(x, x_ref, tau=1e-12):
    if x_ref is None:
        return None, None
    e = abs(x - x_ref)
    return e, (e / abs(x_ref) if abs(x_ref) > tau else None)   # error_rel NULL si ||ref|| ~ 0


def biseccion(f, a, b, tol=1e-10, max_iter=200, x_ref=None):
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return {"convergio": False, "iteraciones": [], "x": None,
                "mensaje": f"No hay cambio de signo en [{a}, {b}]: f(a)={fa:.3g}, f(b)={fb:.3g}. "
                           "La bisección no es aplicable."}
    its = []
    c = a
    for k in range(1, max_iter + 1):
        c = (a + b) / 2
        fc = f(c)
        ea, er = _err(c, x_ref)
        its.append({"numero": k, "aproximacion": [c], "residual": abs(fc), "error_abs": ea, "error_rel": er})
        if abs(fc) < tol or (b - a) / 2 < tol:
            return {"convergio": True, "iteraciones": its, "x": c, "mensaje": "Convergió."}
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return {"convergio": False, "iteraciones": its, "x": c, "mensaje": "Se alcanzó max_iter sin converger."}
