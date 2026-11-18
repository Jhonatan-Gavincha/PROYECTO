"""Aplicación Flask de SIMTELE-RISK.
Local:    flask --app web.app run --debug
Render:   gunicorn web.app:app
"""
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify

load_dotenv()

from simtele import bd, servicio                                  # noqa: E402
from simtele.escenarios import CASOS, ESCENARIOS, TIPOS, ETIQUETA  # noqa: E402


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solo-local")
    bd.init_db()

    @app.context_processor
    def globales():
        return {"CASOS": CASOS, "ETIQUETA": ETIQUETA}

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
        res = servicio.ejecutar(slug, tipo)
        sid = bd.guardar_simulacion(slug, tipo, res["params"], res["semilla"], res["ejecuciones"])
        return redirect(url_for("resultado", sid=sid))

    @app.route("/resultado/<int:sid>")
    def resultado(sid):
        sim = bd.obtener_simulacion(sid)
        if sim is None:
            abort(404)
        slug = next(k for k, v in CASOS.items() if v["nombre"] == sim["nombre"])
        pendientes = [m for m in CASOS[slug]["metodos"]
                      if (slug, m) not in servicio.IMPLEMENTADOS]
        return render_template("resultado.html", sim=sim, slug=slug, pendientes=pendientes,
                               igual=request.args.get("igual"), de=request.args.get("de"))

    @app.post("/resultado/<int:sid>/relanzar")
    def relanzar(sid):
        """Relanza con los mismos parámetros y semilla; compara con la corrida original."""
        sim = bd.obtener_simulacion(sid)
        if sim is None:
            abort(404)
        slug = next(k for k, v in CASOS.items() if v["nombre"] == sim["nombre"])
        res = servicio.ejecutar(slug, sim["tipo"], semilla=sim["semilla"])
        nuevo = bd.guardar_simulacion(slug, sim["tipo"], res["params"], res["semilla"], res["ejecuciones"])
        copia = bd.obtener_simulacion(nuevo)
        igual = int(all(a["valor"]["x"] == b["valor"]["x"] and a["convergio"] == b["convergio"]
                        for a, b in zip(sim["ejecuciones"], copia["ejecuciones"])))
        return redirect(url_for("resultado", sid=nuevo, igual=igual, de=sid))

    @app.route("/historial")
    def historial():
        return render_template("historial.html", sims=bd.listar_simulaciones())

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
        except Exception as e:                       # noqa: BLE001
            return jsonify(estado="error", detalle=str(e)), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
