"""Busqueda del maximo de tension de paso en TODO el exterior de G2.

La linea central no basta para afirmar que un valor es el maximo exterior: el
gradiente de potencial es mayor en las esquinas y el acceso rompe la simetria.
Este script barre el exterior en dos dimensiones, evalua el paso en ocho
direcciones en cada punto y clasifica cada medicion segun la superficie que pisa
cada apoyo.

Ejecutar:  python ejemplos/caso_libro_paso_exterior.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tierra import falla, potencial as pot, tolerables  # noqa: E402
from tierra.malla import Malla  # noqa: E402

RHO, RHO_S, HS, PESO, TS = 150.0, 3000.0, 0.10, 50, 0.70
SF, RG_MANUAL = 0.472, 2.02
PASO_PIES = 1.0        # separacion entre apoyos [m]
RES = 0.25             # resolucion del barrido [m]

# G2 ocupa [-5, 25] x [-5, 35]; la grava llega 2 m mas alla de su borde.
MALLA = (-5.0, -5.0, 30.0, 40.0)
GRAVA = (-7.0, -7.0, 34.0, 44.0)      # x0, y0, ancho, alto
CERCO = (0.5, 0.5, 19.0, 29.0)        # el recinto, 0.5 m dentro del 20 x 30


def dentro(rect, x, y, eps=1e-9):
    x0, y0, w, h = rect
    return (x0 - eps) <= x <= (x0 + w + eps) and (y0 - eps) <= y <= (y0 + h + eps)


def main():
    df = falla.factor_decremento(TS, 10.0, 60.0)
    ig = 5000.0 * SF * df
    m = Malla.rectangular(30, 40, 17, 13, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)
    modelo = pot.modelo_de_malla(m, RHO, ig, x0=MALLA[0], y0=MALLA[1])
    esc = modelo.en_escala(ig * RG_MANUAL)

    _, paso_grava, _ = tolerables.tensiones_tolerables(RHO, TS, PESO, RHO_S, HS)
    _, paso_suelo, _ = tolerables.tensiones_tolerables(RHO, TS, PESO)

    # Region de barrido: desde dentro del recinto hasta 20 m mas alla de la grava.
    x_ini, x_fin = GRAVA[0] - 20.0, GRAVA[0] + GRAVA[2] + 20.0
    y_ini, y_fin = GRAVA[1] - 20.0, GRAVA[1] + GRAVA[3] + 20.0
    nx = int(round((x_fin - x_ini) / RES)) + 1
    ny = int(round((y_fin - y_ini) / RES)) + 1
    xs = [x_ini + RES * i for i in range(nx)]
    ys = [y_ini + RES * j for j in range(ny)]

    print("MAXIMO DE TENSION DE PASO EN EL EXTERIOR DE G2")
    print("=" * 96)
    print(f"IG = {ig:.1f} A · Rg del manual = {RG_MANUAL:g} ohm · GPR adoptado = {esc.gpr:.1f} V "
          f"· factor k = {esc.factor:.4f}")
    print(f"Limites: paso sobre grava {paso_grava:.1f} V · paso sobre suelo expuesto {paso_suelo:.1f} V")
    print(f"Barrido de {x_ini:.1f} a {x_fin:.1f} m en x y de {y_ini:.1f} a {y_fin:.1f} m en y, "
          f"paso de {RES:g} m  ({nx * ny} puntos)")
    print(f"Apoyos separados {PASO_PIES:g} m, evaluados en 8 direcciones por punto.")
    print()

    puntos = [(x, y) for y in ys for x in xs]
    print("Resolviendo el campo de potencial...", flush=True)
    V = esc.potenciales(puntos, bloque=512)
    pot_de = {}
    for (x, y), v in zip(puntos, V):
        pot_de[(round(x, 4), round(y, 4))] = v

    def v_en(x, y):
        return pot_de.get((round(x, 4), round(y, 4)))

    dirs = []
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        dirs.append((PASO_PIES * math.cos(a), PASO_PIES * math.sin(a)))

    peores = {"grava": (-1.0, None, None), "suelo": (-1.0, None, None),
              "mixto": (-1.0, None, None)}
    for (x, y) in puntos:
        if dentro(CERCO, x, y):
            continue  # el interior del recinto se verifica con Em y Es
        v1 = v_en(x, y)
        g1 = dentro(GRAVA, x, y)
        for (dx, dy) in dirs:
            x2 = round(x + dx, 4)
            y2 = round(y + dy, 4)
            v2 = v_en(x2, y2)
            if v2 is None:
                continue
            if dentro(CERCO, x2, y2):
                continue
            g2 = dentro(GRAVA, x2, y2)
            e = abs(v1 - v2)
            clave = "grava" if (g1 and g2) else ("suelo" if not (g1 or g2) else "mixto")
            if e > peores[clave][0]:
                peores[clave] = (e, (x, y), (x2, y2))

    def describe(p):
        x, y = p
        d_cerco = max(CERCO[0] - x, x - (CERCO[0] + CERCO[2]),
                      CERCO[1] - y, y - (CERCO[1] + CERCO[3]))
        return f"({x:7.2f}, {y:7.2f})  a {d_cerco:5.2f} m del cerco"

    print("RESULTADOS DEL BARRIDO COMPLETO")
    print("-" * 96)
    for clave, etiqueta, limite in (
            ("grava", "Ambos apoyos sobre grava", paso_grava),
            ("suelo", "Ambos apoyos sobre suelo expuesto", paso_suelo),
            ("mixto", "Apoyos sobre superficies distintas", None)):
        e, p1, p2 = peores[clave]
        print(f"{etiqueta}")
        print(f"  tension   {e:8.1f} V")
        if limite is not None:
            print(f"  limite    {limite:8.1f} V    cociente {e/limite:.3f}    "
                  f"{'cumple' if e <= limite else 'NO cumple'}")
        else:
            print("  limite        —        requiere un criterio especifico para apoyos")
            print("                         sobre superficies distintas: comprobacion abierta")
        print(f"  apoyo 1   {describe(p1)}")
        print(f"  apoyo 2   {describe(p2)}")
        print()

    # Contraste con la linea central, para ver cuanto subestimaba
    print("CONTRASTE: LINEA CENTRAL FRENTE AL BARRIDO COMPLETO")
    print("-" * 96)
    centro_x = MALLA[0] + MALLA[2] / 2.0
    peor_linea = {"grava": -1.0, "suelo": -1.0}
    d = 0.0
    while d <= 40.0:
        p1 = (centro_x, 0.5 - d)
        p2 = (centro_x, 0.5 - d - PASO_PIES)
        g1, g2 = dentro(GRAVA, *p1), dentro(GRAVA, *p2)
        if g1 or not g2:
            e = esc.paso(p1, p2)
            clave = "grava" if (g1 and g2) else ("suelo" if not (g1 or g2) else None)
            if clave and e > peor_linea[clave]:
                peor_linea[clave] = e
        d += 0.05
    for clave, etiqueta, limite in (("grava", "sobre grava", paso_grava),
                                    ("suelo", "sobre suelo expuesto", paso_suelo)):
        lin, bar = peor_linea[clave], peores[clave][0]
        print(f"  Paso {etiqueta:22} linea central {lin:7.1f} V   barrido {bar:7.1f} V   "
              f"({100*(bar-lin)/lin:+.1f} %)   cociente del barrido {bar/limite:.3f}")
    print()
    print("  La linea central no es el peor recorrido: el barrido completo encuentra")
    print("  valores mayores. Las posiciones de los maximos estan arriba.")


if __name__ == "__main__":
    main()
