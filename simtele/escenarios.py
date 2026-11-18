"""Definición de los 4 casos y sus 3 escenarios (parámetros sintéticos, Sec. 9 del informe)."""

TIPOS = ["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
ETIQUETA = {"NORMAL": "NORMAL", "ESTRES": "ESTRÉS", "MAL_CONDICIONADO": "MAL CONDICIONADO"}
MODELO_VERSION = "2.0-semana2"

CASOS = {
    "detencion": {
        "n": 1, "nombre": "Detención de emergencia",
        "pregunta": "¿Cómo varían tiempo y distancia de detención con velocidad, reacción y frenado?",
        "modelo": "x' = v, v' = -a(v,t).  t_det = t_r + v0/a;  d = v0·t_r + v0²/(2a)",
        "metodos": ["RK2", "RK4", "Trapecio", "Simpson 1/3", "Romberg", "Bisección", "Newton", "Secante"],
    },
    "deterioro": {
        "n": 2, "nombre": "Deterioro y mantenimiento",
        "pregunta": "¿Cuándo un indicador hipotético de deterioro alcanza el umbral de inspección?",
        "modelo": "D(t) = D0 + αt + βt²;  resolver D(t) − Du = 0",
        "metodos": ["Bisección", "Newton", "Secante", "Jacobi", "Gauss-Seidel", "LU", "Gradiente conjugado"],
    },
    "oscilaciones": {
        "n": 3, "nombre": "Oscilaciones por viento",
        "pregunta": "¿Cómo cambia la oscilación con fuerza externa, amortiguamiento y parámetros?",
        "modelo": "x' = v, v' = (F(t) − c·v − k·x)/m",
        "metodos": ["RK2", "RK4", "Trapecio", "Simpson 1/3", "Romberg"],
    },
    "sensores": {
        "n": 4, "nombre": "Reconstrucción de sensores",
        "pregunta": "¿Cómo reconstruir registros faltantes y medir la distorsión por ruido?",
        "modelo": "y(t) = sin t en [0, 2π] con ruido gaussiano; se ocultan nodos interiores",
        "metodos": ["Lagrange", "Newton (dif. divididas)", "Spline cúbico"],
    },
}

ESCENARIOS = {
    "detencion": {
        "NORMAL": {"descripcion": "v0=5 m/s, a=0,8 m/s², t_r=1 s",
                   "params": {"v0": 5.0, "a": 0.8, "tr": 1.0}},
        "ESTRES": {"descripcion": "v0=6 m/s, a=0,5 m/s², t_r=2 s; distancia disponible supuesta 40 m",
                   "params": {"v0": 6.0, "a": 0.5, "tr": 2.0, "d_disp": 40.0}},
        "MAL_CONDICIONADO": {"descripcion": "v(t)=v0(1−t/T)², v0=5, T=6,25 s (raíz doble en t=T)",
                             "params": {"v0": 5.0, "T": 6.25, "eps": 1e-6}},
    },
    "deterioro": {
        "NORMAL": {"descripcion": "D0=0,10; α=0,020; β=0,0015; Du=0,60",
                   "params": {"D0": 0.10, "alpha": 0.020, "beta": 0.0015, "Du": 0.60}},
        "ESTRES": {"descripcion": "Deterioro más rápido: α=0,030; β=0,0025",
                   "params": {"D0": 0.10, "alpha": 0.030, "beta": 0.0025, "Du": 0.60}},
        "MAL_CONDICIONADO": {"descripcion": "Saturación: β=−0,002 y Du igual al máximo de D (raíz doble)",
                             "params": {"D0": 0.10, "alpha": 0.04, "beta": -0.002, "Du": 0.30}},
    },
    "oscilaciones": {
        "NORMAL": {"descripcion": "m=1000 kg, k=40000 N/m, ζ=0,05, F=0, x(0)=0,10 m, T=20 s",
                   "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.05, "F0": 0.0, "r": 0.0,
                              "x0": 0.10, "v0": 0.0, "T": 20.0}},
        "ESTRES": {"descripcion": "ζ=0,02, F(t)=2000·sin(Ωt), Ω=0,9·ω0, T=60 s, pasos h grandes",
                   "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.02, "F0": 2000.0, "r": 0.9,
                              "x0": 0.0, "v0": 0.0, "T": 60.0}},
        "MAL_CONDICIONADO": {"descripcion": "ζ=0,01, Ω=0,99·ω0 (cerca de resonancia). F0=2000 N es supuesto",
                             "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.01, "F0": 2000.0, "r": 0.99,
                                        "x0": 0.0, "v0": 0.0, "T": 60.0}},
    },
    "sensores": {
        "NORMAL": {"descripcion": "9 nodos equiespaciados, sin ruido; se ocultan 3 nodos interiores",
                   "params": {"n": 9, "sigma": 0.0, "ocultos": [2, 4, 6], "semilla": 42}},
        "ESTRES": {"descripcion": "5 nodos (h=π/2) y ruido σ=0,05 (semilla 42)",
                   "params": {"n": 5, "sigma": 0.05, "ocultos": [1, 3], "semilla": 42}},
        "MAL_CONDICIONADO": {"descripcion": "21 nodos equiespaciados, ruido σ=1e-3",
                             "params": {"n": 21, "sigma": 1e-3, "ocultos": [5, 10, 15], "semilla": 42}},
    },
}
