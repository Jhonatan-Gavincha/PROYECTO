import math, numpy as np, pytest
from simtele.metodos.raices import biseccion, newton_raphson, secante
from simtele.metodos.sistemas import jacobi, gauss_seidel, lu_solve, gradiente_conjugado
from simtele.metodos.interpolacion import lagrange, newton_diferencias_divididas, spline_cubico
from simtele.metodos.integracion import trapecio_compuesto, simpson_13_compuesto, romberg
from simtele.metodos.edo import rk2, rk4


def test_raices_basicas():
    f=lambda x:x*x-2; df=lambda x:2*x
    r=biseccion(f,1,2,x_ref=math.sqrt(2)); assert r['convergio'] and abs(r['x']-math.sqrt(2))<1e-8
    r=newton_raphson(f,df,1.0,x_ref=math.sqrt(2)); assert r['convergio'] and abs(r['x']-math.sqrt(2))<1e-10
    r=secante(f,1.0,2.0,x_ref=math.sqrt(2)); assert r['convergio'] and abs(r['x']-math.sqrt(2))<1e-10


def test_sistemas_4x4_spd():
    A=np.array([[4,1,1,0],[1,3,-1,1],[1,-1,2,0],[0,1,0,2]],dtype=float)
    x_true=np.array([1,2,3,4],dtype=float); b=A@x_true
    for fn in [lambda: jacobi(A,b,x0=np.zeros(4),max_iter=500,tol=1e-10,x_ref=x_true), lambda: gauss_seidel(A,b,x0=np.zeros(4),max_iter=500,tol=1e-10,x_ref=x_true), lambda: lu_solve(A,b,x_ref=x_true), lambda: gradiente_conjugado(A,b,x0=np.zeros(4),max_iter=200,tol=1e-10,x_ref=x_true)]:
        r=fn(); assert np.linalg.norm(np.array(r['x'])-x_true) < 1e-6
    r=gradiente_conjugado(np.array([[1,2],[2,1]],dtype=float),np.array([1,1],dtype=float))
    assert r['estado']=='no_aplicable' or not r['convergio']


def test_interpolacion_ocultos():
    x=np.array([0,0.5,1.0,1.5,2.0]); y=np.sin(x)
    xe=[0.75,1.25]; yr=np.sin(xe)
    for fn in [lagrange,newton_diferencias_divididas,spline_cubico]:
        r=fn(x,y,xe,y_ref=yr)
        assert max(row['error_abs'] for row in r['tabla_evaluacion']) < 0.05


def test_integracion():
    f=lambda x:x*x; ref=1/3
    r=trapecio_compuesto(f,0,1,100,x_ref=ref); assert abs(r['x']-ref)<1e-3
    r=simpson_13_compuesto(f,0,1,100,x_ref=ref); assert abs(r['x']-ref)<1e-8
    r=romberg(f,0,1,max_nivel=5,x_ref=ref); assert abs(r['x']-ref)<1e-10
    bad=simpson_13_compuesto(f,0,1,3); assert bad['estado']=='entrada_invalida'


def test_edo():
    f=lambda t,y: -y
    ref_fn=lambda t:[math.exp(-t)]
    r=rk2(f,0,[1.0],0.1,10,ref_fn=ref_fn); assert r['convergio']
    r4=rk4(f,0,[1.0],0.1,10,ref_fn=ref_fn); assert abs(r4['x'][0]-math.exp(-1)) < abs(r['x'][0]-math.exp(-1))
