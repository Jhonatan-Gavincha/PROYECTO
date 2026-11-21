"""Definición de casos, escenarios y fichas de modelo (datos sintéticos)."""

TIPOS = ["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
ETIQUETA = {"NORMAL": "NORMAL", "ESTRES": "ESTRÉS", "MAL_CONDICIONADO": "MAL CONDICIONADO"}
MODELO_VERSION = "3.0-completo"

CASOS = {
    "detencion": {
        "slug": "detencion", "nombre": "Detención de emergencia de cabinas",
        "pregunta": "¿Cómo varían el tiempo y la distancia de detención frente a cambios de velocidad inicial, tiempo de reacción y frenado?",
        "modelo_latex": r"v(t)=v_0-a t,\quad x(t)=x_0+v_0 t-\frac{a t^2}{2},\quad t_{det}=\frac{v_0}{a},\quad d_{fren}=\frac{v_0^2}{2a}",
        "descripcion": "Caso hipotético y educativo inspirado en el transporte por cable urbano de La Paz–El Alto. No representa mecanismos reales de seguridad de Mi Teleférico ni de ningún operador.",
        "contexto": {
            "situacion": "Simulación educativa inspirada en Mi Teleférico (La Paz–El Alto) para estimar la detención segura de una cabina.",
            "problematica": "Calcular con precisión el tiempo y la distancia de frenado ante cambios de velocidad, reacción y desaceleración.",
            "aporte_sistemas": ["Sistemas: define requisitos, parámetros, trazabilidad y criterios de validación.", "Software: implementa la simulación, la interfaz y el registro de resultados para apoyo a decisión."],
            "decision": "Verificar si el margen de detención es seguro en escenarios normales, de estrés y sensibles.",
        },
        "variables": [
            {"simbolo": "v0", "desc": "Velocidad inicial", "unidad": "m/s"},
            {"simbolo": "a", "desc": "Desaceleración constante positiva", "unidad": "m/s²"},
            {"simbolo": "t_r", "desc": "Tiempo de reacción", "unidad": "s"},
            {"simbolo": "t", "desc": "Tiempo", "unidad": "s"},
            {"simbolo": "v(t)", "desc": "Velocidad", "unidad": "m/s"},
            {"simbolo": "x(t)", "desc": "Posición/distancia", "unidad": "m"},
        ],
        "hipotesis": ["Desaceleración constante en el caso base.", "Movimiento rectilíneo 1D.", "Datos sintéticos hipotéticos."],
        "metodos": ["RK2 (Heun)", "RK4", "Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg", "Bisección", "Newton-Raphson", "Secante"],
    },
    "deterioro": {
        "slug": "deterioro", "nombre": "Deterioro mecánico y mantenimiento",
        "pregunta": "¿Cuándo alcanzaría un indicador hipotético de deterioro un umbral de inspección?",
        "modelo_latex": r"D(t)=D_0+\alpha t+\beta t^2,\qquad D(t)-D_u=0,\qquad A\mathbf{x}=\mathbf{b}\; (4\times4)",
        "descripcion": "Indicador sintético de deterioro inspirado en la gestión de mantenimiento de infraestructura de transporte por cable. No predice deterioro real de equipo.",
        "contexto": {
            "situacion": "Modelo educativo para planificar inspección de componentes en un sistema de transporte por cable.",
            "problematica": "Estimar cuándo un indicador sintético de desgaste alcanzará el umbral de mantenimiento.",
            "aporte_sistemas": ["Sistemas: analiza riesgos, umbrales y condiciones del proceso de mantenimiento.", "Software: desarrolla el cálculo numérico, alertas y visualización del estado del indicador."],
            "decision": "Anticipar el tiempo de inspección con base en resultados numéricos confiables.",
        },
        "variables": [
            {"simbolo": "D0", "desc": "Deterioro inicial", "unidad": "adimensional"},
            {"simbolo": "α", "desc": "Tasa lineal", "unidad": "1/mes"},
            {"simbolo": "β", "desc": "Tasa cuadrática", "unidad": "1/mes²"},
            {"simbolo": "Du", "desc": "Umbral de inspección", "unidad": "adimensional"},
            {"simbolo": "t", "desc": "Tiempo", "unidad": "meses"},
        ],
        "hipotesis": ["Modelo polinómico de segundo orden.", "Umbral fijo conocido.", "Sistema 4x4 sintético para calibración."],
        "metodos": ["Bisección", "Newton-Raphson", "Secante", "Jacobi", "Gauss-Seidel", "LU", "Gradiente conjugado"],
    },
    "oscilaciones": {
        "slug": "oscilaciones", "nombre": "Oscilaciones por viento",
        "pregunta": "¿Cómo se modifica la oscilación ante cambios de fuerza externa, amortiguamiento y parámetros del modelo?",
        "modelo_latex": r"x'=v,\qquad v'=\frac{F(t)-c v-k x}{m},\qquad F(t)=F_0\sin(\Omega t),\qquad \Omega=r\omega_0",
        "descripcion": "Modelo equivalente masa-resorte-amortiguador, educativo y sintético, inspirado en condiciones de viento en corredores urbanos de altura.",
        "contexto": {
            "situacion": "Simulación educativa de oscilaciones por viento en cabinas, considerando condiciones de altura.",
            "problematica": "Evaluar cómo cambian desplazamiento y respuesta dinámica ante viento, amortiguamiento y resonancia.",
            "aporte_sistemas": ["Sistemas: modela escenarios operativos, límites y criterios de seguridad.", "Software: implementa EDO/integración, gráficas y monitoreo de resultados."],
            "decision": "Identificar condiciones con mayor oscilación y validar la estabilidad del modelo.",
        },
        "variables": [
            {"simbolo": "m", "desc": "Masa equivalente", "unidad": "kg"},
            {"simbolo": "k", "desc": "Rigidez equivalente", "unidad": "N/m"},
            {"simbolo": "c", "desc": "Amortiguamiento", "unidad": "N·s/m"},
            {"simbolo": "F0", "desc": "Amplitud de fuerza externa", "unidad": "N"},
            {"simbolo": "x(t)", "desc": "Desplazamiento", "unidad": "m"},
            {"simbolo": "v(t)", "desc": "Velocidad", "unidad": "m/s"},
        ],
        "hipotesis": ["Sistema lineal equivalente.", "Parámetros constantes por escenario.", "Vibración libre tiene referencia analítica subamortiguada."],
        "metodos": ["RK2 (Heun)", "RK4", "Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg"],
    },
    "sensores": {
        "slug": "sensores", "nombre": "Reconstrucción de señales de sensores",
        "pregunta": "¿Cómo reconstruir registros faltantes y medir la distorsión que producen datos con ruido?",
        "modelo_latex": r"y(t)=\sin(t),\qquad t\in[0,2\pi]",
        "descripcion": "Datos sintéticos con ruido controlado, inspirados en telemetría de sensores de operación. No corresponde a señales reales.",
        "contexto": {
            "situacion": "Reconstrucción educativa de señales de telemetría con datos faltantes o ruido.",
            "problematica": "Recuperar valores no observados sin distorsionar la señal usada por el sistema.",
            "aporte_sistemas": ["Sistemas: define calidad de datos, tolerancia a fallos y reglas de uso.", "Software: implementa interpolación, métricas de error y comparación de métodos."],
            "decision": "Elegir el método de reconstrucción más confiable para el monitoreo.",
        },
        "variables": [
            {"simbolo": "t", "desc": "Coordenada/tiempo sintético", "unidad": "rad"},
            {"simbolo": "y(t)", "desc": "Señal", "unidad": "adimensional"},
            {"simbolo": "sigma", "desc": "Desv. estándar ruido gaussiano", "unidad": "adimensional"},
            {"simbolo": "n", "desc": "Cantidad de nodos", "unidad": "nodos"},
        ],
        "hipotesis": ["Señal base conocida para evaluación.", "Puntos ocultos no se usan para ajustar.", "Ruido gaussiano con semilla fija."],
        "metodos": ["Lagrange", "Newton (diferencias divididas)", "Spline cúbico"],
    },
}

ESCENARIOS = {
    "detencion": {
        "NORMAL": {"descripcion": "v0=20 m/s, a=2.5 m/s², t_r=1.0 s, x0=0", "params": {"v0": 20.0, "a": 2.5, "tr": 1.0, "x0": 0.0, "h": 0.2, "n_integracion": 20}},
        "ESTRES": {"descripcion": "v0=30 m/s, a=2.0 m/s², t_r=1.5 s, distancia disponible 350 m", "params": {"v0": 30.0, "a": 2.0, "tr": 1.5, "x0": 0.0, "d_disp": 350.0, "h": 0.5, "n_integracion": 20}},
        "MAL_CONDICIONADO": {"descripcion": "f(t)=v0-a*t+eps*t^2 con eps pequeño; raíz casi sensible (derivada pequeña relativa)", "params": {"v0": 20.0, "a": 2.5, "tr": 1.0, "x0": 0.0, "eps": 1e-4, "h": 0.2, "n_integracion": 20}},
    },
    "deterioro": {
        "NORMAL": {"descripcion": "D0=0.10, α=0.020, β=0.0015, Du=0.60", "params": {"D0": 0.10, "alpha": 0.020, "beta": 0.0015, "Du": 0.60}},
        "ESTRES": {"descripcion": "D0=0.10, α=0.030, β=0.0025, Du=0.60", "params": {"D0": 0.10, "alpha": 0.030, "beta": 0.0025, "Du": 0.60}},
        "MAL_CONDICIONADO": {"descripcion": "β=-0.002, Du igual al máximo (raíz doble en t=10)", "params": {"D0": 0.10, "alpha": 0.04, "beta": -0.002, "Du": 0.30}},
    },
    "oscilaciones": {
        "NORMAL": {"descripcion": "m=1000, k=40000, ζ=0.05, F0=0, x0=0.10, v0=0, T=20 s", "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.05, "F0": 0.0, "r": 0.0, "x0": 0.10, "v0": 0.0, "T": 20.0, "h": 0.05, "n_integracion": 40}},
        "ESTRES": {"descripcion": "ζ=0.02, F0=2000, r=0.9, T=60 s", "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.02, "F0": 2000.0, "r": 0.9, "x0": 0.0, "v0": 0.0, "T": 60.0, "h": 0.1, "n_integracion": 60}},
        "MAL_CONDICIONADO": {"descripcion": "ζ=0.01, F0=2000, r=0.99 (cerca de resonancia)", "params": {"m": 1000.0, "k": 40000.0, "zeta": 0.01, "F0": 2000.0, "r": 0.99, "x0": 0.0, "v0": 0.0, "T": 60.0, "h": 0.05, "n_integracion": 60}},
    },
    "sensores": {
        "NORMAL": {"descripcion": "9 nodos equiespaciados, sin ruido; oculta 3", "params": {"n": 9, "sigma": 0.0, "ocultos": [2, 4, 6], "semilla": 42}},
        "ESTRES": {"descripcion": "5 nodos y ruido σ=0.05 (semilla 42)", "params": {"n": 5, "sigma": 0.05, "ocultos": [1, 3], "semilla": 42}},
        "MAL_CONDICIONADO": {"descripcion": "21 nodos equiespaciados, ruido σ=0.001", "params": {"n": 21, "sigma": 0.001, "ocultos": [5, 10, 15], "semilla": 42}},
    },
}
