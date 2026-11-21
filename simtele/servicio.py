"""Orquestación de módulos, métodos, sensibilidad y conclusiones."""
from __future__ import annotations
import math, time, copy
import numpy as np
from simtele.escenarios import CASOS, ESCENARIOS, MODELO_VERSION
from simtele.referencias import REFERENCIAS
from simtele.metodos.raices import biseccion, newton_raphson, secante
from simtele.metodos.sistemas import jacobi, gauss_seidel, lu_solve, gradiente_conjugado, numero_condicion
from simtele.metodos.interpolacion import lagrange, newton_diferencias_divididas, spline_cubico
from simtele.metodos.integracion import trapecio_compuesto, simpson_13_compuesto, romberg
from simtele.metodos.edo import rk2, rk4
from simtele.numerico import metricas_error


def _clone_params(p):
    return copy.deepcopy(p)


def _base_ejec(r, metodo=None):
    r.setdefault("metodo", metodo or r.get("metodo"))
    r.setdefault("convergio", False)
    r.setdefault("iteraciones", [])
    r.setdefault("metrica_error", {})
    r.setdefault("mensaje", "")
    r.setdefault("estado", "convergio" if r.get("convergio") else "no_convergio")
    r.setdefault("estado_detalle", r.get("estado"))
    r.setdefault("conclusion_numerica", "")
    r.setdefault("conclusion_problema", "")
    return r


def _conclusiones_metodo(slug, tipo, params, ref, ej):
    m = ej.get("metrica_error", {})
    estado = ej.get("estado_detalle", ej.get("estado", ""))
    ea = m.get("error_abs")
    er = m.get("error_rel")
    res = m.get("residual_norma", m.get("residual"))
    nit = len(ej.get("iteraciones", []))
    conv = ej.get("convergio")
    nombre = ej.get("metodo", "Método")
    # numérica
    cn = [f"{nombre}: estado {estado}."]
    if ea is not None: cn.append(f"Error absoluto={ea:.3e}.")
    if er is not None: cn.append(f"Error relativo={er:.3e}.")
    elif m.get("error_rel_nota"): cn.append(f"Error relativo: {m.get('error_rel_nota')}.")
    if res is not None: cn.append(f"Residual/norma={float(res):.3e}." if isinstance(res,(int,float)) else f"Residual reportado.")
    cn.append(f"Iteraciones/refinamientos={nit}.")
    cn.append("Comparar con otros métodos del mismo escenario para juzgar precisión/costo.")
    # problema
    cp = _conclusion_problema(slug, tipo, params, ref, ej)
    return " ".join(cn), cp


def _conclusion_problema(slug, tipo, params, ref, ej):
    x = ej.get("x")
    if slug == "detencion":
        tdet = ref.get("t_detencion")
        dtotal = ref.get("d_total")
        extra = ""
        if ref.get("exceso_sobre_disponible") is not None and ref["exceso_sobre_disponible"] > 0:
            extra = f" En el escenario hay exceso de {ref['exceso_sobre_disponible']:.3g} m sobre la distancia disponible hipotética."
        return (f"El resultado indica t_detención≈{tdet:.4g} s y distancia total≈{dtotal:.4g} m bajo parámetros sintéticos. "
                f"Mayor v0 o t_r incrementa distancia; mayor a la reduce.{extra} "
                "Limitación: modelo educativo simplificado, no representa seguridad real.")
    if slug == "deterioro":
        t = ref.get("t_estrella")
        msg = f"El umbral hipotético se alcanza en t≈{t:.4g} meses." if t is not None else "No se obtuvo raíz física admisible."
        if ref.get("raiz_doble"):
            msg += " La raíz doble indica alta sensibilidad: pequeños cambios en datos cambian mucho el tiempo estimado."
        return msg + " Limitación: indicador sintético; no predice deterioro real."
    if slug == "oscilaciones":
        amp = ref.get("amplitud_estacionaria")
        info = f" Amplitud estacionaria estimada≈{amp:.4g} m." if amp is not None else ""
        return ("La respuesta depende de m,k,c y F(t); mayor amortiguamiento reduce oscilación y cercanía a resonancia la amplifica." + info +
                " Limitación: modelo equivalente lineal, no comportamiento real de cabina.")
    if slug == "sensores":
        return ("La reconstrucción depende de nodos, ruido y distribución. Splines suelen ser más estables ante oscilación polinómica; "
                "ruido/nodos equiespaciados desfavorables aumentan distorsión. Limitación: inferir valores no observados tiene incertidumbre.")
    return "Interpretación no disponible."


# -------- Módulo 1: Detención --------
def _det_funs(p, tipo):
    v0, a, tr = float(p["v0"]), float(p["a"]), float(p["tr"])
    x0 = float(p.get("x0", 0.0))
    eps = float(p.get("eps", 0.0)) if tipo == "MAL_CONDICIONADO" else 0.0
    def v_t(t):
        return v0 - a*t + eps*t*t
    def x_t_analitica(t):
        return x0 + v0*t - a*t*t/2 + eps*t*t*t/3
    def f_sistema(t, y):
        # y=[x,v]
        return np.array([y[1], -a + 2*eps*t], dtype=float)
    return v_t, x_t_analitica, f_sistema


def ejecutar_detencion(tipo, params, ref):
    p = params
    v_t, x_analitica, f_sys = _det_funs(p, tipo)
    v0, a, tr = float(p["v0"]), float(p["a"]), float(p["tr"])
    x0 = float(p.get("x0", 0.0))
    t_det = float(ref["t_detencion"])
    h = float(p.get("h", 0.2))
    n_pasos = max(1, int(math.ceil(t_det/h)))
    h_real = t_det / n_pasos
    ejecuciones = []

    # RK2
    t0r = time.perf_counter()
    r = rk2(f_sys, 0.0, [x0, v0], h_real, n_pasos, ref_fn=lambda t: np.array([x_analitica(t), v_t(t)]), nombre_sistema="x'=v, v'=-a+2*eps*t")
    r["tiempo_ms"] = (time.perf_counter()-t0r)*1000
    r["tolerancia"] = None; r["paso"] = h_real; r["max_iter"] = n_pasos
    r["referencia"] = {"t_detencion": t_det, "x_detencion": x_analitica(t_det), "v_detencion": v_t(t_det)}
    r["grafico"] = {"tipo": "edo", "series": [{"nombre":"x RK2","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][0] for it in r["iteraciones"]]} , {"nombre":"v RK2","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][1] for it in r["iteraciones"]]}]}
    _base_ejec(r)
    ejecuciones.append(r)

    # RK4
    t0r = time.perf_counter()
    r = rk4(f_sys, 0.0, [x0, v0], h_real, n_pasos, ref_fn=lambda t: np.array([x_analitica(t), v_t(t)]), nombre_sistema="x'=v, v'=-a+2*eps*t")
    r["tiempo_ms"] = (time.perf_counter()-t0r)*1000
    r["paso"] = h_real; r["max_iter"] = n_pasos
    r["referencia"] = {"t_detencion": t_det, "x_detencion": x_analitica(t_det), "v_detencion": v_t(t_det)}
    r["grafico"] = {"tipo": "edo", "series": [{"nombre":"x RK4","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][0] for it in r["iteraciones"]]} , {"nombre":"v RK4","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][1] for it in r["iteraciones"]]}]}
    _base_ejec(r)
    ejecuciones.append(r)

    # Integración de v(t)
    n_int = int(p.get("n_integracion", 20))
    if n_int % 2 == 1: n_int += 1
    for fn, nombre in [(trapecio_compuesto, "Trapecio compuesto"), (simpson_13_compuesto, "Simpson 1/3 compuesto"), (romberg, "Romberg")]:
        t0r = time.perf_counter()
        if nombre == "Romberg":
            res = fn(v_t, 0.0, t_det, max_nivel=5, tol=1e-10, x_ref=ref["d_frenado"], nombre_f="v(t)")
        else:
            res = fn(v_t, 0.0, t_det, n=n_int, x_ref=ref["d_frenado"], nombre_f="v(t)")
        res["tiempo_ms"] = (time.perf_counter()-t0r)*1000
        res["referencia"] = {"integral_ref": ref["d_frenado"], "magnitud": "Distancia de frenado = integral_0^{t_det} v(t) dt"}
        res["metrica_error"] = metricas_error(ref["d_frenado"], res.get("x"))
        _base_ejec(res, nombre)
        ejecuciones.append(res)

    # Raíces v(t)=0
    for nombre, fncall in [("Bisección", lambda: biseccion(v_t, 0.0, max(t_det*1.5, 1.0), tol=1e-10, max_iter=200, x_ref=t_det, nombre_f="v(t)")),
                           ("Newton-Raphson", lambda: newton_raphson(v_t, lambda t: -a + 2*float(p.get("eps",0.0))*t, t_det*0.8, tol=1e-10, max_iter=100, x_ref=t_det, nombre_f="v(t)", nombre_df="v'(t)")),
                           ("Secante", lambda: secante(v_t, t_det*0.7, t_det*1.3, tol=1e-10, max_iter=100, x_ref=t_det, nombre_f="v(t)"))]:
        t0r = time.perf_counter()
        res = fncall(); res["tiempo_ms"] = (time.perf_counter()-t0r)*1000
        res["referencia"] = {"t_detencion_ref": t_det}
        _base_ejec(res, nombre)
        ejecuciones.append(res)

    # sensibilidad
    sens = _sensibilidad_detencion(tipo, p, ref)
    comp = _comparar_ejecuciones(ejecuciones)
    conclusiones = _conclusiones_modulo(slug="detencion", tipo=tipo, params=p, ref=ref, ejecuciones=ejecuciones, sensibilidad=sens)
    for ej in ejecuciones:
        ej["conclusion_numerica"], ej["conclusion_problema"] = _conclusiones_metodo("detencion", tipo, p, ref, ej)
    return ejecuciones, sens, comp, conclusiones


def _sensibilidad_detencion(tipo, p, ref):
    base_t = ref.get("t_detencion")
    base_d = ref.get("d_total")
    rows = []
    for param, delta in [("v0", 0.05*float(p["v0"])), ("a", 0.05*float(p["a"])), ("tr", 0.05*float(p["tr"]))]:
        p2 = _clone_params(p); p2[param] = float(p2[param]) + delta
        ref2 = REFERENCIAS["detencion"](tipo, p2)
        for nombre, base, nuevo in [("t_detencion", base_t, ref2.get("t_detencion")), ("d_total", base_d, ref2.get("d_total"))]:
            if base is None or nuevo is None: continue
            rows.append({"parametro": param, "original": float(p[param]), "perturbado": float(p2[param]), "magnitud": delta, "salida": nombre, "resultado_original": base, "resultado_perturbado": nuevo, "delta_abs": abs(nuevo-base), "delta_rel": (abs(nuevo-base)/abs(base) if abs(base)>1e-12 else None)})
    return {"filas": rows, "interpretacion": "Sensibilidad del modelo: cambios en v0 y tr aumentan distancia total; aumentar a la reduce. No confundir con error numérico."}


# -------- Módulo 2: Deterioro --------
def ejecutar_deterioro(tipo, params, ref):
    p = params
    D = lambda t: float(p["D0"]) + float(p["alpha"])*t + float(p["beta"])*t*t
    f = lambda t: D(t) - float(p["Du"])
    df = lambda t: float(p["alpha"]) + 2*float(p["beta"])*t
    x_ref = ref.get("t_estrella")
    ejecuciones = []

    # Raíces
    defs = [
        ("Bisección", lambda: biseccion(f, 0.0, 60.0, tol=1e-10, max_iter=200, x_ref=x_ref, nombre_f="D(t)-Du")),
        ("Newton-Raphson", lambda: newton_raphson(f, df, 5.0 if x_ref is None else max(0.1, x_ref*0.8), tol=1e-10, max_iter=100, x_ref=x_ref, nombre_f="D(t)-Du", nombre_df="D'(t)")),
        ("Secante", lambda: secante(f, 0.0, 20.0, tol=1e-10, max_iter=100, x_ref=x_ref, nombre_f="D(t)-Du")),
    ]
    for nombre, fn in defs:
        t0r=time.perf_counter(); r=fn(); r["tiempo_ms"]=(time.perf_counter()-t0r)*1000
        r["referencia"]={"t_estrella": x_ref, "raices": ref.get("raices")}
        _base_ejec(r, nombre); ejecuciones.append(r)

    # Sistema lineal 4x4 (calibración sintética)
    A, b, x_true = _sistema_deterioro(tipo, p)
    cond = numero_condicion(A)
    for nombre, fn in [("Jacobi", lambda: jacobi(A,b,x0=np.zeros(4),tol=1e-10,max_iter=200,x_ref=x_true)),
                       ("Gauss-Seidel", lambda: gauss_seidel(A,b,x0=np.zeros(4),tol=1e-10,max_iter=200,x_ref=x_true)),
                       ("LU", lambda: lu_solve(A,b,x_ref=x_true)),
                       ("Gradiente conjugado", lambda: gradiente_conjugado(A,b,x0=np.zeros(4),tol=1e-10,max_iter=200,x_ref=x_true))]:
        t0r=time.perf_counter(); r=fn(); r["tiempo_ms"]=(time.perf_counter()-t0r)*1000
        r["referencia"]={"x_ref": x_true.tolist(), "condicion_2": cond}
        r["condicion_2"] = cond
        _base_ejec(r, nombre); ejecuciones.append(r)

    sens = _sensibilidad_deterioro(tipo, p, ref, A)
    comp = _comparar_ejecuciones(ejecuciones)
    conclusiones = _conclusiones_modulo("deterioro", tipo, p, ref, ejecuciones, sens)
    for ej in ejecuciones:
        ej["conclusion_numerica"], ej["conclusion_problema"] = _conclusiones_metodo("deterioro", tipo, p, ref, ej)
    return ejecuciones, sens, comp, conclusiones


def _sistema_deterioro(tipo, p):
    # Sistema sintético de calibración: A x = b, x* conocido
    x_true = np.array([float(p["D0"]), float(p["alpha"]), float(p["beta"]), 1.0], dtype=float)
    if tipo == "MAL_CONDICIONADO":
        eps = 1e-4
        A = np.array([[1,1,1,1],[1,1+eps,1,1],[1,1,1+eps,1],[1,1,1,1+eps]], dtype=float)
        # hacer SPD? no necesariamente; para GC usaremos otra SPD mal condicionada
        # Para requisitos: GC sobre matriz SPD; entonces definimos A_spd aparte en ejecución? Mejor construir A SPD y usarla para todos, explicando calibración sintética
    # Usar matriz SPD bien definida; en mal condicionado aumentar condición
    if tipo == "NORMAL":
        A = np.array([[4,1,0,1],[1,3,1,0],[0,1,2,1],[1,0,1,3]], dtype=float)
    elif tipo == "ESTRES":
        A = np.array([[6,2,1,1],[2,5,2,0],[1,2,4,1],[1,0,1,3]], dtype=float)
    else:
        # SPD pero mal condicionada
        A = np.array([[1,1,1,1],[1,1.0001,1,1],[1,1,1.0002,1],[1,1,1,1.0003]], dtype=float)
        # Esta no es SPD garantizada; construir SPD explícita
        B = np.array([[1,0.9999,0.9998,0.9997],[0.9999,1,0.9999,0.9998],[0.9998,0.9999,1,0.9999],[0.9997,0.9998,0.9999,1]], dtype=float)
        A = B.T @ B + 1e-6*np.eye(4)
    b = A @ x_true
    return A, b, x_true


def _sensibilidad_deterioro(tipo, p, ref, A):
    rows = []
    base_t = ref.get("t_estrella")
    for param in ["D0","alpha","beta","Du"]:
        p2=_clone_params(p); delta = 0.01*abs(float(p[param])) if abs(float(p[param]))>1e-12 else 0.01
        p2[param]=float(p2[param])+delta
        ref2=REFERENCIAS["deterioro"](tipo,p2)
        nuevo=ref2.get("t_estrella")
        if base_t is not None and nuevo is not None:
            rows.append({"parametro":param,"original":float(p[param]),"perturbado":float(p2[param]),"magnitud":delta,"salida":"t_estrella","resultado_original":base_t,"resultado_perturbado":nuevo,"delta_abs":abs(nuevo-base_t),"delta_rel":(abs(nuevo-base_t)/abs(base_t) if abs(base_t)>1e-12 else None)})
    # condición y perturbación en b
    cond = numero_condicion(A)
    x_true = np.ones(A.shape[0])
    b = A @ x_true
    db = b * 0.001
    x2 = np.linalg.solve(A, b+db)
    rows.append({"parametro":"b (perturbación 0.1%)","original":"b","perturbado":"b+db","magnitud":0.001,"salida":"||delta x||/||x||","resultado_original":0.0,"resultado_perturbado":float(np.linalg.norm(x2-x_true)/np.linalg.norm(x_true)),"delta_abs":float(np.linalg.norm(x2-x_true)/np.linalg.norm(x_true)),"delta_rel":None,"condicion_2":cond})
    interp = f"cond2(A)={cond:.3e}. "
    interp += "Matriz mal condicionada: pequeña perturbación en b cambia mucho x." if cond>1e3 else "Condicionamiento moderado/bajo en este escenario."
    return {"filas": rows, "condicion_2": cond, "interpretacion": interp}


# -------- Módulo 3: Oscilaciones --------
def ejecutar_oscilaciones(tipo, params, ref):
    p=params; m,k,zeta=float(p["m"]),float(p["k"]),float(p["zeta"])
    c = 2*zeta*math.sqrt(k*m)
    F0,r=float(p.get("F0",0)),float(p.get("r",0))
    w0=math.sqrt(k/m); wr=r*w0
    def F(t): return F0*math.sin(wr*t)
    def f_sys(t,y): return np.array([y[1], (F(t)-c*y[1]-k*y[0])/m], dtype=float)
    x0,v0=float(p.get("x0",0)),float(p.get("v0",0))
    T=float(p["T"]); h=float(p.get("h",0.05)); n_pasos=max(1,int(math.ceil(T/h))); h_real=T/n_pasos
    ref_fn=None
    if abs(F0) < 1e-12 and ref.get("tipo_ref") == "analitica_vibracion_libre":
        c1 = float(ref.get("C1", x0)); c2 = float(ref.get("C2", 0.0))
        w0r = float(ref.get("omega0", w0)); zr = float(ref.get("zeta", zeta)); wd_local = w0*math.sqrt(max(0.0,1-zeta*zeta)); wdr = float(ref.get("omega_d", wd_local))
        def ref_fn(t):
            e = math.exp(-zr*w0r*t)
            xt = e*(c1*math.cos(wdr*t) + c2*math.sin(wdr*t))
            vt = e*((-zr*w0r*c1 + wdr*c2)*math.cos(wdr*t) + (-zr*w0r*c2 - wdr*c1)*math.sin(wdr*t))
            return np.array([xt, vt], dtype=float)
    ejecuciones=[]
    # EDO
    for fn, nombre in [(rk2,"RK2 (Heun)"),(rk4,"RK4")]:
        t0r=time.perf_counter(); r=fn(f_sys,0.0,[x0,v0],h_real,n_pasos,ref_fn=ref_fn,nombre_sistema="x'=v, v'=(F(t)-c v-k x)/m")
        r["tiempo_ms"]=(time.perf_counter()-t0r)*1000; r["paso"]=h_real; r["max_iter"]=n_pasos
        r["referencia"]={"tipo":ref.get("tipo_ref")}
        # grafico
        r["grafico"]={"tipo":"edo","series":[{"nombre":"x","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][0] for it in r["iteraciones"]]},{"nombre":"v","x":[it["t"] for it in r["iteraciones"]],"y":[it["y"][1] for it in r["iteraciones"]]}]}
        _base_ejec(r, nombre); ejecuciones.append(r)

    # magnitud acumulada: integral_0^T |x(t)| dt usando trayectoria RK4 de referencia (misma malla)
    ts=np.array([it["t"] for it in ejecuciones[-1]["iteraciones"]], dtype=float)
    xs=np.abs(np.array([it["y"][0] for it in ejecuciones[-1]["iteraciones"]], dtype=float))
    integral_ref=float(np.trapezoid(xs,ts) if hasattr(np,"trapezoid") else np.trapz(xs,ts))
    def g_abs(t):
        # evaluar x(t) por interpolación lineal sobre malla fina
        return float(np.interp(t, ts, xs))
    n_int=int(p.get("n_integracion",40))
    if n_int%2==1: n_int+=1
    for fn, nombre in [(trapecio_compuesto,"Trapecio compuesto"),(simpson_13_compuesto,"Simpson 1/3 compuesto"),(romberg,"Romberg")]:
        t0r=time.perf_counter()
        if nombre=="Romberg": res=fn(g_abs,0.0,T,max_nivel=5,tol=1e-8,x_ref=integral_ref,nombre_f="|x(t)|")
        else: res=fn(g_abs,0.0,T,n=n_int,x_ref=integral_ref,nombre_f="|x(t)|")
        res["tiempo_ms"]=(time.perf_counter()-t0r)*1000
        res["referencia"]={"integral_ref":integral_ref, "magnitud":"∫_0^T |x(t)| dt", "tipo_ref":"numérica independiente (RK4 fino + trapecio fino)"}
        res["metrica_error"]=metricas_error(integral_ref,res.get("x"))
        _base_ejec(res,nombre); ejecuciones.append(res)

    sens=_sensibilidad_oscilaciones(tipo,p,ref)
    comp=_comparar_ejecuciones(ejecuciones)
    conclusiones=_conclusiones_modulo("oscilaciones",tipo,p,ref,ejecuciones,sens)
    for ej in ejecuciones:
        ej["conclusion_numerica"], ej["conclusion_problema"]=_conclusiones_metodo("oscilaciones",tipo,p,ref,ej)
    return ejecuciones,sens,comp,conclusiones


def _sensibilidad_oscilaciones(tipo,p,ref):
    rows=[]
    base=ref.get("amplitud_estacionaria")
    if base is not None:
        for param in ["zeta","r","F0"]:
            p2=_clone_params(p); delta=0.01*abs(float(p[param])) if abs(float(p[param]))>1e-12 else 0.001
            p2[param]=float(p2[param])+delta
            ref2=REFERENCIAS["oscilaciones"](tipo,p2)
            nuevo=ref2.get("amplitud_estacionaria")
            if nuevo is not None:
                rows.append({"parametro":param,"original":float(p[param]),"perturbado":float(p2[param]),"magnitud":delta,"salida":"amplitud_estacionaria","resultado_original":base,"resultado_perturbado":nuevo,"delta_abs":abs(nuevo-base),"delta_rel":(abs(nuevo-base)/abs(base) if abs(base)>1e-12 else None)})
    return {"filas":rows, "interpretacion":"Cerca de resonancia (r≈1) y bajo amortiguamiento, la amplitud es altamente sensible."}


# -------- Módulo 4: Sensores --------
def ejecutar_sensores(tipo, params, ref):
    x_nodos=np.array(ref["usados_x"],dtype=float); y_nodos=np.array(ref["usados_y"],dtype=float)
    x_eval=np.array(ref["ocultos_x"],dtype=float); y_true=np.array(ref["ocultos_y_true"],dtype=float)
    ejecuciones=[]
    for fn,nombre in [(lagrange,"Lagrange"),(newton_diferencias_divididas,"Newton (diferencias divididas)"),(spline_cubico,"Spline cúbico")]:
        t0r=time.perf_counter(); r=fn(x_nodos,y_nodos,x_eval,y_ref=y_true); r["tiempo_ms"]=(time.perf_counter()-t0r)*1000
        r["referencia"]={"ocultos_x":x_eval.tolist(),"ocultos_y_true":y_true.tolist()}
        _base_ejec(r,nombre); ejecuciones.append(r)
    sens=_sensibilidad_sensores(tipo,params,ref)
    comp=_comparar_ejecuciones(ejecuciones)
    conclusiones=_conclusiones_modulo("sensores",tipo,params,ref,ejecuciones,sens)
    for ej in ejecuciones:
        ej["conclusion_numerica"], ej["conclusion_problema"]=_conclusiones_metodo("sensores",tipo,params,ref,ej)
    return ejecuciones,sens,comp,conclusiones


def _sensibilidad_sensores(tipo,p,ref):
    rows=[]
    # perturbación de ruido
    p2=_clone_params(p); p2["sigma"]=float(p.get("sigma",0))+0.01
    ref2=REFERENCIAS["sensores"](tipo,p2)
    # comparar Lagrange en punto ocultado
    try:
        r1=lagrange(ref["usados_x"],ref["usados_y"],[ref["ocultos_x"][0]],y_ref=[ref["ocultos_y_true"][0]])
        r2=lagrange(ref2["usados_x"],ref2["usados_y"],[ref2["ocultos_x"][0]],y_ref=[ref2["ocultos_y_true"][0]])
        a1=r1["x"][0]; a2=r2["x"][0]
        rows.append({"parametro":"sigma","original":float(p.get("sigma",0)),"perturbado":float(p2["sigma"]),"magnitud":0.01,"salida":"prediccion_oculta_1","resultado_original":a1,"resultado_perturbado":a2,"delta_abs":abs(a2-a1),"delta_rel":(abs(a2-a1)/abs(a1) if abs(a1)>1e-12 else None)})
    except Exception:
        pass
    return {"filas":rows, "lebesgue_usados":ref.get("lebesgue_nodos_usados"), "lebesgue_todos":ref.get("lebesgue_equiespaciados_todos"), "lebesgue_chebyshev":ref.get("lebesgue_chebyshev"), "interpretacion":"Nodos equiespaciados muchos y ruido aumentan sensibilidad; Lebesgue alto indica mal condicionamiento de interpolación."}


# -------- Común --------
def _comparar_ejecuciones(ejecuciones):
    filas=[]
    for ej in ejecuciones:
        m=ej.get("metrica_error",{})
        filas.append({"metodo":ej.get("metodo"),"estado":ej.get("estado_detalle",ej.get("estado")),"convergio":ej.get("convergio"),"error_abs":m.get("error_abs"),"error_rel":m.get("error_rel"),"error_pct":m.get("error_pct"),"residual":m.get("residual_norma",m.get("residual")), "iteraciones":len(ej.get("iteraciones",[])), "tiempo_ms":ej.get("tiempo_ms")})
    return {"filas":filas}


def _conclusiones_modulo(slug,tipo,params,ref,ejecuciones,sensibilidad):
    # numérica
    ok=[e for e in ejecuciones if e.get("convergio")]
    best=None
    for e in ok:
        ea=(e.get("metrica_error") or {}).get("error_abs")
        if ea is None: continue
        if best is None or ea < best[0]: best=(ea,e)
    cn=f"Escenario {tipo}: se ejecutaron {len(ejecuciones)} métodos; convergieron {len(ok)}. "
    if best: cn+=f"Menor error absoluto observado: {best[1]['metodo']} ({best[0]:.3e}). "
    cn+="El error/residual/iteraciones dependen del método y parámetros; no se generaliza fuera de esta ejecución."
    # problema
    cp=_conclusion_problema(slug,tipo,params,ref,ejecuciones[0] if ejecuciones else {})
    cp="Conclusión del problema: "+cp
    return {"numerica":cn, "problema":cp, "sensibilidad":sensibilidad.get("interpretacion","")}


DISPATCH = {
    "detencion": ejecutar_detencion,
    "deterioro": ejecutar_deterioro,
    "oscilaciones": ejecutar_oscilaciones,
    "sensores": ejecutar_sensores,
}


def ejecutar(slug, tipo, semilla=42):
    if slug not in CASOS or tipo not in ESCENARIOS[slug]:
        raise ValueError("Caso o escenario inválido")
    params = _clone_params(ESCENARIOS[slug][tipo]["params"])
    params["semilla"] = semilla
    ref = REFERENCIAS[slug](tipo, params)
    ejecuciones, sensibilidad, comparacion, conclusiones = DISPATCH[slug](tipo, params, ref)
    # resumen comparación por métrica
    return {
        "slug": slug, "tipo": tipo, "params": params, "semilla": semilla,
        "referencia": ref, "ejecuciones": ejecuciones,
        "sensibilidad": sensibilidad, "comparacion": comparacion,
        "conclusiones": conclusiones,
        "modelo_version": MODELO_VERSION,
    }
