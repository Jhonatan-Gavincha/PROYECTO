"""Aplicación Flask de SIMTELE-RISK."""
from __future__ import annotations
import os, sys, math
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simtele import bd, servicio                                  # noqa: E402
from simtele.escenarios import CASOS, ESCENARIOS, TIPOS, ETIQUETA  # noqa: E402


def _is_finite_number(v):
    try:
        f = float(v)
        return math.isfinite(f)
    except Exception:
        return False


def _parse_params(slug, tipo, form):
    base = dict(ESCENARIOS[slug][tipo]["params"])
    params = {}
    for k, v in base.items():
        if isinstance(v, bool):
            params[k] = form.get(k, str(v)) in ("1","true","True","on")
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            raw = form.get(k, str(v))
            if not _is_finite_number(raw):
                raise ValueError(f"Parámetro {k} debe ser numérico finito")
            val = float(raw)
            if isinstance(v, int) and abs(val-round(val)) < 1e-9:
                val = int(round(val))
            params[k] = val
        elif isinstance(v, list):
            raw = form.get(k, ",".join(str(x) for x in v))
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            try:
                params[k] = [int(float(p)) for p in parts]
            except Exception:
                raise ValueError(f"Parámetro {k} debe ser lista de enteros separados por coma")
        else:
            params[k] = form.get(k, v)
    # validaciones comunes
    if "h" in params and float(params["h"]) <= 0: raise ValueError("h debe ser > 0")
    if "n_integracion" in params and int(params["n_integracion"]) <= 0: raise ValueError("n_integracion debe ser > 0")
    if "n_integracion" in params and int(params["n_integracion"]) % 2 != 0: params["n_integracion"] = int(params["n_integracion"]) + 1
    if "tol" in params and float(params["tol"]) <= 0: raise ValueError("tol debe ser > 0")
    if "max_iter" in params and int(params["max_iter"]) <= 0: raise ValueError("max_iter debe ser > 0")
    if "n" in params and int(params["n"]) < 3: raise ValueError("n debe ser >= 3")
    if "sigma" in params and float(params["sigma"]) < 0: raise ValueError("sigma debe ser >= 0")
    if "ocultos" in params:
        n = int(params.get("n", len(params["ocultos"])+3))
        oc = params["ocultos"]
        if any(i < 0 or i >= n for i in oc): raise ValueError("Índices ocultos fuera de rango")
        if len(set(oc)) != len(oc): raise ValueError("Índices ocultos duplicados")
        if len(oc) >= n-1: raise ValueError("Debe quedar al menos 2 nodos visibles")
    # fisicas simples
    if "a" in params and float(params["a"]) <= 0: raise ValueError("a debe ser > 0")
    if "m" in params and float(params["m"]) <= 0: raise ValueError("m debe ser > 0")
    if "k" in params and float(params["k"]) <= 0: raise ValueError("k debe ser > 0")
    return params


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solo-local")
    try:
        bd.init_db()
    except Exception as e:
        app.logger.exception("init_db failed: %s", e)

    PARAM_LATEX = {
        "v0":"v_0","a":"a","tr":"t_r","x0":"x_0","h":"h","n_integracion":"n","d_disp":"d_{disp}","eps":r"\varepsilon",
        "D0":"D_0","alpha":r"\alpha","beta":r"\beta","Du":"D_u",
        "m":"m","k":"k","zeta":r"\zeta","F0":"F_0","r":"r","T":"T",
        "n":"n","sigma":r"\sigma","ocultos":"ocultos","semilla":"semilla"
    }

    @app.context_processor
    def globales():
        return {"CASOS": CASOS, "ETIQUETA": ETIQUETA, "TIPOS": TIPOS, "PARAM_LATEX": PARAM_LATEX}

    @app.route("/")
    def inicio():
        return render_template("index.html")

    @app.route("/modulo/<slug>")
    def modulo(slug):
        if slug not in CASOS:
            abort(404)
        return render_template("modulo.html", slug=slug, caso=CASOS[slug],
                               escenarios=ESCENARIOS[slug], tipos=TIPOS)

    @app.post("/modulo/<slug>/ejecutar")
    def ejecutar(slug):
        tipo = request.form.get("tipo", "")
        if slug not in CASOS or tipo not in TIPOS:
            abort(400)
        try:
            params = _parse_params(slug, tipo, request.form)
        except Exception as e:
            return render_template("modulo.html", slug=slug, caso=CASOS[slug], escenarios=ESCENARIOS[slug], tipos=TIPOS, error=str(e)), 400
        semilla = params.get("semilla", 42)
        try:
            semilla = int(semilla)
        except Exception:
            semilla = 42
        old = ESCENARIOS[slug][tipo]["params"]
        ESCENARIOS[slug][tipo]["params"] = params
        try:
            res = servicio.ejecutar(slug, tipo, semilla=semilla)
            sid = bd.guardar_simulacion(slug, tipo, res["params"], res["semilla"], res["ejecuciones"],
                                        conclusiones=res.get("conclusiones"), comparacion=res.get("comparacion"),
                                        sensibilidad=res.get("sensibilidad"), metadatos={"modelo_version": res.get("modelo_version")})
        except Exception as e:
            app.logger.exception("Error ejecutando %s/%s", slug, tipo)
            return render_template("modulo.html", slug=slug, caso=CASOS[slug], escenarios=ESCENARIOS[slug], tipos=TIPOS,
                                   error=f"No se pudo ejecutar/guardar la simulación: {e}"), 500
        finally:
            ESCENARIOS[slug][tipo]["params"] = old
        return redirect(url_for("resultado", sid=sid))

    @app.route("/resultado/<int:sid>")
    def resultado(sid):
        try:
            sim = bd.obtener_simulacion(sid)
        except Exception as e:
            app.logger.exception("Error obteniendo simulación %s", sid)
            return render_template("error.html", mensaje=f"No se pudo recuperar la simulación {sid}.", detalle=str(e)), 500
        if sim is None:
            abort(404)
        slug = sim.get("slug") or next((k for k, v in CASOS.items() if v["nombre"] == sim.get("nombre")), None)
        if slug is None or slug not in CASOS:
            abort(404)
        return render_template("resultado.html", sim=sim, slug=slug, caso=CASOS[slug], igual=request.args.get("igual"), de=request.args.get("de"))

    @app.post("/resultado/<int:sid>/relanzar")
    def relanzar(sid):
        try:
            sim = bd.obtener_simulacion(sid)
        except Exception as e:
            app.logger.exception("Error obteniendo simulación %s para relanzar", sid)
            return render_template("error.html", mensaje=f"No se pudo recuperar la simulación {sid}.", detalle=str(e)), 500
        if sim is None:
            abort(404)
        slug = sim.get("slug") or next((k for k, v in CASOS.items() if v["nombre"] == sim.get("nombre")), None)
        if slug is None or slug not in CASOS:
            abort(404)
        old = ESCENARIOS[slug][sim["tipo"]]["params"]
        ESCENARIOS[slug][sim["tipo"]]["params"] = sim["params"]
        try:
            res = servicio.ejecutar(slug, sim["tipo"], semilla=sim.get("semilla", 42))
            nuevo = bd.guardar_simulacion(slug, sim["tipo"], res["params"], res["semilla"], res["ejecuciones"],
                                          conclusiones=res.get("conclusiones"), comparacion=res.get("comparacion"),
                                          sensibilidad=res.get("sensibilidad"), metadatos={"modelo_version": res.get("modelo_version"), "relanzado_de": sid})
            copia = bd.obtener_simulacion(nuevo)
        except Exception as e:
            app.logger.exception("Error relanzando simulación %s", sid)
            return render_template("error.html", mensaje=f"No se pudo relanzar la simulación {sid}.", detalle=str(e)), 500
        finally:
            ESCENARIOS[slug][sim["tipo"]]["params"] = old
        igual = 1
        try:
            for a, b in zip(sim.get("ejecuciones", []), copia.get("ejecuciones", [])):
                ax, bx = (a.get("valor") or {}).get("x"), (b.get("valor") or {}).get("x")
                if str(ax) != str(bx) or bool(a.get("convergio")) != bool(b.get("convergio")):
                    igual = 0; break
        except Exception:
            igual = 0
        return redirect(url_for("resultado", sid=nuevo, igual=igual, de=sid))

    @app.route("/historial")
    def historial():
        caso = request.args.get("caso") or None
        tipo = request.args.get("tipo") or None
        q = request.args.get("q") or None
        sims = bd.listar_simulaciones(caso=caso, tipo=tipo, q=q)
        return render_template("historial.html", sims=sims, caso=caso, tipo=tipo, q=q or "")

    @app.post("/historial/<int:sid>/eliminar")
    def eliminar_simulacion(sid):
        caso = request.form.get("caso", "")
        tipo = request.form.get("tipo", "")
        q = request.form.get("q", "")
        try:
            bd.eliminar_simulacion(sid)
        except Exception:
            app.logger.exception("Error eliminando simulación %s", sid)
        return redirect(url_for("historial", caso=caso or None, tipo=tipo or None, q=q or None))

    @app.route("/comparar")
    def comparar():
        raw = request.args.getlist("ids")
        parts = []
        for r in raw:
            parts.extend(r.split(","))
        if not parts:
            parts = request.args.get("ids", "").split(",")
        id_list = []
        for part in parts:
            part = part.strip()
            if part.isdigit():
                v = int(part)
                if v not in id_list:
                    id_list.append(v)
        sims = [bd.obtener_simulacion(i) for i in id_list[:4]]
        sims = [s for s in sims if s]
        return render_template("comparar.html", sims=sims, ids=",".join(str(s["id"]) for s in sims))

    @app.route("/api/resultado/<int:sid>")
    def api_resultado(sid):
        sim = bd.obtener_simulacion(sid)
        if sim is None:
            abort(404)
        return jsonify(sim)

    @app.route("/salud")
    def salud():
        try:
            bd.listar_simulaciones(1)
            return jsonify(estado="ok")
        except Exception as e:
            return jsonify(estado="error", detalle=str(e)), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
