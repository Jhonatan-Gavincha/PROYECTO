"""Utilidades numéricas comunes: errores, estados, serialización segura y validaciones."""
from __future__ import annotations
import math
import json
import numpy as np

ESTADOS = {
    "convergio": "Convergió",
    "max_iter": "Se alcanzó el máximo de iteraciones",
    "no_convergio": "No convergió",
    "divergio": "Divergió",
    "entrada_invalida": "Entrada inválida",
    "no_aplicable": "Método no aplicable a las condiciones proporcionadas",
    "interrumpido": "Cálculo interrumpido por una condición numérica",
}


def es_numero_finito(x):
    try:
        v = float(x)
    except Exception:
        return False
    return math.isfinite(v)


def to_float(x, nombre="valor"):
    if not es_numero_finito(x):
        raise ValueError(f"{nombre} debe ser numérico y finito")
    return float(x)


def to_int(x, nombre="valor"):
    if isinstance(x, bool) or not es_numero_finito(x):
        raise ValueError(f"{nombre} debe ser entero")
    v = int(float(x))
    if abs(v - float(x)) > 1e-9:
        raise ValueError(f"{nombre} debe ser entero")
    return v


def safe_json(obj):
    return json.loads(json.dumps(obj, default=_default))


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def error_abs(ref, aprox):
    if ref is None or aprox is None:
        return None
    try:
        r = float(ref); a = float(aprox)
    except Exception:
        return None
    if not (math.isfinite(r) and math.isfinite(a)):
        return None
    return abs(r - a)


def error_rel(ref, aprox, tau=1e-12):
    ea = error_abs(ref, aprox)
    if ea is None:
        return None
    r = float(ref)
    if abs(r) <= tau:
        return None
    return ea / abs(r)


def error_pct(ref, aprox, tau=1e-12):
    er = error_rel(ref, aprox, tau=tau)
    return None if er is None else er * 100.0


def metricas_error(ref, aprox, residual=None, extra=None):
    er = error_rel(ref, aprox)
    ep = error_pct(ref, aprox)
    m = {
        "error_abs": error_abs(ref, aprox),
        "error_rel": er,
        "error_pct": ep,
        "error_rel_nota": None if er is not None else ("No definido (referencia cero)" if ref is not None and abs(float(ref)) <= 1e-12 else "No disponible"),
        "error_pct_nota": None if ep is not None else ("No definido (referencia cero)" if ref is not None and abs(float(ref)) <= 1e-12 else "No disponible"),
        "residual": residual,
    }
    if extra:
        m.update(extra)
    return m


def norma(v, ord=2):
    a = np.array(v, dtype=float)
    return float(np.linalg.norm(a, ord=ord))


def fmt_num(x, digits=10):
    if x is None:
        return "—"
    try:
        v = float(x)
    except Exception:
        return str(x)
    if not math.isfinite(v):
        return "No definido"
    if abs(v) >= 1e4 or (0 < abs(v) < 1e-4):
        return f"{v:.{digits}g}"
    return f"{v:.10g}"


def estado_resultado(convergio, max_iter_alcanzado=False, divergencia=False, no_aplicable=False, entrada_invalida=False, interrumpido=False):
    if entrada_invalida:
        return "entrada_invalida"
    if no_aplicable:
        return "no_aplicable"
    if interrumpido:
        return "interrumpido"
    if divergencia:
        return "divergio"
    if convergio:
        return "convergio"
    if max_iter_alcanzado:
        return "max_iter"
    return "no_convergio"
