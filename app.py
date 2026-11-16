import os
import psycopg2
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  try:
    # Intenta conectarse a Neon PostgreSQL usando la variable de entorno
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    cur.close()
    conn.close()
    return f"¡Conexión exitosa a Neon PostgreSQL! Versión: {db_version[0]}"
  except Exception as e:
    return (
        "La app funciona, pero hubo un error al conectar a la base de"
        f" datos: {e}"
    )


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)