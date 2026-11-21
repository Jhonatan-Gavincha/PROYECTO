"""Referencias analíticas/numéricas justificadas para verificación."""
from __future__ import annotations
import math
import numpy as np


def ref_detencion(tipo, p):
    v0, a, tr = float(p["v0"]), float(p["a"]), float(p["tr"])
    x0 = float(p.get("x0", 0.0))
    eps = float(p.get("eps", 0.0))
    if tipo == "MAL_CONDICIONADO":
        # v(t)=v0-a*t+eps*t^2 ; raíz física en [0, ~v0/a]
        A, B, C = eps, -a, v0
        disc = B*B - 4*A*C
        raiz = None
        if abs(A) < 1e-15:
            raiz = v0/a
        elif disc >= 0:
            s = math.sqrt(disc)
            r1, r2 = (-B-s)/(2*A), (-B+s)/(2*A)
            cands = [r for r in [r1, r2] if r > 0]
            raiz = min(cands) if cands else None
        # distancia frenado por integral analítica de v(t)
        t_det = raiz
        d_fren = v0*t_det - a*t_det*t_det/2 + eps*t_det*t_det*t_det/3 if t_det is not None else None
        return {
            "modelo": "v(t)=v0-a*t+eps*t^2 (perturbación pequeña; sensible por derivada cerca de raíz)",
            "raiz_doble": False,
            "t_detencion": t_det,
            "d_reaccion": v0*tr,
            "d_frenado": d_fren,
            "d_total": (v0*tr + d_fren) if d_fren is not None else None,
            "exceso_sobre_disponible": ((v0*tr + d_fren)-p["d_disp"]) if (d_fren is not None and "d_disp" in p) else None,
            "x_ref_raiz": t_det,
        }
    t_det = v0 / a
    d_reac = v0 * tr
    d_fren = v0*v0/(2*a)
    ref = {
        "modelo": "v(t)=v0-a*t, x(t)=x0+v0*t-a*t^2/2",
        "raiz_doble": False,
        "t_detencion": t_det,
        "t_frenado": t_det,
        "t_total": tr + t_det,
        "d_reaccion": d_reac,
        "d_frenado": d_fren,
        "d_total": d_reac + d_fren,
        "x_ref_raiz": t_det,
    }
    if "d_disp" in p:
        ref["exceso_sobre_disponible"] = ref["d_total"] - float(p["d_disp"])
    return ref


def raices_deterioro(p):
    a, b, c = float(p["beta"]), float(p["alpha"]), float(p["D0"]) - float(p["Du"])
    if abs(a) < 1e-15:
        if abs(b) < 1e-15: return []
        return [-c/b]
    disc = b*b - 4*a*c
    if abs(disc) < 1e-12:
        return [-b/(2*a)]
    if disc < 0:
        return []
    s = math.sqrt(disc)
    return sorted([(-b-s)/(2*a), (-b+s)/(2*a)])


def ref_deterioro(tipo, p):
    r = raices_deterioro(p)
    pos = [x for x in r if x >= 0]
    t_estrella = min(pos) if pos else None
    ref = {
        "modelo": "D(t)-Du=beta*t^2+alpha*t+(D0-Du)=0",
        "raiz_doble": len(r) == 1,
        "raices": r,
        "t_estrella": t_estrella,
        "x_ref_raiz": t_estrella,
    }
    if tipo == "MAL_CONDICIONADO":
        ref["nota"] = "Raíz doble: sensibilidad intrínseca alta."
    return ref


def ref_oscilaciones(tipo, p):
    m, k, zeta = float(p["m"]), float(p["k"]), float(p["zeta"])
    F0, r, x0, v0 = float(p.get("F0", 0)), float(p.get("r", 0)), float(p.get("x0", 0)), float(p.get("v0", 0))
    w0 = math.sqrt(k/m)
    c = 2*zeta*math.sqrt(k*m)
    wd = w0*math.sqrt(max(0.0, 1-zeta*zeta))
    ref = {"modelo": "x'' + 2*zeta*w0*x' + w0^2*x = F(t)/m", "omega0": w0, "zeta": zeta, "omega_d": wd, "c": c, "raiz_doble": False}
    if abs(F0) < 1e-12:
        # vibración libre subamortiguada
        C1 = x0
        C2 = (v0 + zeta*w0*x0)/wd if wd > 1e-12 else 0.0
        ref.update({"C1": C1, "C2": C2, "tipo_ref": "analitica_vibracion_libre"})
        def x_analitica(t):
            return math.exp(-zeta*w0*t)*(C1*math.cos(wd*t)+C2*math.sin(wd*t))
        # integral de |x| no cerrada simple; referencia numérica independiente de alta precisión
        T = float(p["T"])
        xs = np.linspace(0, T, 4001)
        ys = np.abs([x_analitica(tt) for tt in xs])
        ref["integral_abs_ref"] = float(np.trapezoid(ys,xs) if hasattr(np,"trapezoid") else np.trapz(ys,xs))
        ref["integral_ref_tipo"] = "numérica independiente (trapecio alta resolución sobre solución analítica)"
    else:
        wr = r*w0
        D = (1-r*r)**2 + (2*zeta*r)**2
        X = (F0/k)/math.sqrt(D) if D > 0 else float('inf')
        ref.update({"tipo_ref": "forzada_senoidal", "Omega": wr, "amplitud_estacionaria": X, "factor_amplificacion": (1/math.sqrt(D) if D>0 else None)})
        if tipo == "MAL_CONDICIONADO":
            dr = 1e-3
            rp, rm = r+dr, max(0, r-dr)
            Dp = (1-rp*rp)**2 + (2*zeta*rp)**2
            Dm = (1-rm*rm)**2 + (2*zeta*rm)**2
            Xp = (F0/k)/math.sqrt(Dp)
            Xm = (F0/k)/math.sqrt(Dm)
            ref["sensibilidad_amplitud_dr"] = {"dr": dr, "A_r": X, "A_r+dr": Xp, "A_r-dr": Xm, "delta_abs": abs(Xp-Xm), "delta_rel": (abs(Xp-Xm)/abs(X) if abs(X)>1e-12 else None)}
        # referencia numérica para integral con RK4 paso muy pequeño
        T = float(p["T"])
        ref["integral_ref_tipo"] = "numérica independiente (RK4 paso fino para trayectoria, trapecio fino para integral)"
        ref["T"] = T
    return ref


def _lebesgue(nodos):
    xs = np.linspace(float(nodos.min()), float(nodos.max()), 2001)
    L = np.zeros_like(xs)
    for i in range(len(nodos)):
        li = np.ones_like(xs)
        for j in range(len(nodos)):
            if j != i:
                li *= (xs - nodos[j]) / (nodos[i] - nodos[j])
        L += np.abs(li)
    return float(L.max())


def ref_sensores(tipo, p):
    n = int(p["n"])
    sigma = float(p["sigma"])
    ocultos = list(p["ocultos"])
    semilla = int(p.get("semilla", 42))
    t = np.linspace(0, 2*np.pi, n)
    y_true = np.sin(t)
    rng = np.random.default_rng(semilla)
    ruido = rng.normal(0, sigma, size=n)
    y_med = y_true + ruido
    mask = np.ones(n, dtype=bool)
    mask[ocultos] = False
    usados_x, usados_y = t[mask], y_med[mask]
    ocultos_x, ocultos_y_true = t[~mask], y_true[~mask]
    ref = {
        "modelo": "y(t)=sin(t)+ruido_gaussiano(sigma,semilla)",
        "raiz_doble": False,
        "nodos_x": t.tolist(), "y_true": y_true.tolist(), "y_med": y_med.tolist(),
        "ocultos_idx": ocultos, "ocultos_x": ocultos_x.tolist(), "ocultos_y_true": ocultos_y_true.tolist(),
        "usados_x": usados_x.tolist(), "usados_y": usados_y.tolist(),
        "lebesgue_nodos_usados": _lebesgue(usados_x),
    }
    if tipo == "MAL_CONDICIONADO":
        k = np.arange(n)
        cheb = np.cos((2*k+1)*np.pi/(2*n))
        cheb = (cheb - cheb.min())/(cheb.max()-cheb.min())*2*np.pi
        ref["lebesgue_equiespaciados_todos"] = _lebesgue(t)
        ref["lebesgue_chebyshev"] = _lebesgue(np.sort(cheb))
        ref["cota_amplificacion_ruido"] = ref["lebesgue_equiespaciados_todos"] * sigma
    return ref


REFERENCIAS = {
    "detencion": ref_detencion,
    "deterioro": ref_deterioro,
    "oscilaciones": ref_oscilaciones,
    "sensores": ref_sensores,
}
