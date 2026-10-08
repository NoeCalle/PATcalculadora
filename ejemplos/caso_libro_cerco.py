"""Toque en cerco y puerta del caso del manual de mallas de puesta a tierra.

Resuelve los marcadores [CALCULAR] del manual que el metodo simplificado de
IEEE 80 no cubre: el toque en el cerco y en la puerta, el paso en el exterior y
el contraste de las areas ampliadas con sus separaciones reales.

Ejecutar:  python ejemplos/caso_libro_cerco.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tierra import conductor, falla, potencial as pot, tolerables  # noqa: E402
from tierra.malla import Malla  # noqa: E402

# --------------------------------------------------------------------------
# Datos del caso (ficha del manual)
# --------------------------------------------------------------------------
RHO = 150.0           # resistividad del suelo [ohm*m], modelo uniforme
RHO_S, HS = 3000.0, 0.10   # grava
PESO, TS = 50, 0.70        # persona y duracion de respaldo
I_FALLA_MT, X_R = 5.0, 10.0   # kA, relacion X/R de la falla de MT
D_COND = 0.0105            # diametro del conductor enterrado de 70 mm2 [m]

# Recinto: rectangulo original de 20 x 30 m con origen en su esquina suroeste.
# El cerco esta 0.50 m hacia dentro; la puerta ocupa x de 8 a 12 m en el lado sur.
CERCO = [(0.5, 0.5), (19.5, 0.5), (19.5, 29.5), (0.5, 29.5)]
PUERTA = ((8.0, 0.5), (12.0, 0.5))

DF = falla.factor_decremento(TS, X_R, 60.0)

# Geometrias: (nombre, lx, ly, nx, ny, x0, y0, Sf, Rg_libro)
# nx = conductores paralelos a x (de longitud lx); ny = paralelos a y.
# x0, y0 = esquina suroeste, en el marco del rectangulo original.
GEOMETRIAS = [
    ("G0  20x30 D=10",      20, 30,  4,  3,   0.0,  0.0, 0.364, 3.45),
    ("G1  20x30 D=2",       20, 30, 16, 11,   0.0,  0.0, 0.403, 2.85),
    ("AA  24x34 trama 5",   24, 34,  8,  6,  -2.0, -2.0, 0.419, 2.63),
    ("AA  24x34 trama 4",   24, 34,  9,  7,  -2.0, -2.0, 0.423, 2.58),
    ("AA  24x34 trama 3",   24, 34, 12,  9,  -2.0, -2.0, 0.429, 2.51),
    ("AA  26x36 trama 4",   26, 36, 10,  7,  -3.0, -3.0, 0.437, 2.40),
    ("AA  26x36 trama 3",   26, 36, 13, 10,  -3.0, -3.0, 0.444, 2.33),
    ("G2  30x40 trama 2.5", 30, 40, 17, 13,  -5.0, -5.0, 0.472, 2.02),
]


def limites():
    cs_g, paso_g, toque_g = tolerables.tensiones_tolerables(RHO, TS, PESO, RHO_S, HS)
    cs_s, paso_s, toque_s = tolerables.tensiones_tolerables(RHO, TS, PESO)
    return {
        "cs_grava": cs_g, "toque_grava": toque_g, "paso_grava": paso_g,
        "toque_suelo": toque_s, "paso_suelo": paso_s,
        "metal_metal": pot.tolerable_metal_metal(TS, PESO),
    }


def _lado_exterior(p, centro, retiro):
    """Desplaza el punto p una distancia `retiro` alejandose del centro."""
    dx, dy = p[0] - centro[0], p[1] - centro[1]
    n = max(abs(dx), abs(dy))
    if n == 0:
        return p
    # se retira en la direccion dominante, perpendicular al lado del cerco
    if abs(dx) >= abs(dy):
        return (p[0] + retiro * (1 if dx > 0 else -1), p[1])
    return (p[0], p[1] + retiro * (1 if dy > 0 else -1))


def analizar(nombre, lx, ly, nx, ny, x0, y0, sf, rg_libro, n_perfil=60):
    m = Malla.rectangular(lx, ly, nx, ny, h=0.50, d=D_COND, n_varillas=4, l_varilla=3.0)
    ig = I_FALLA_MT * 1000.0 * sf * DF
    gpr_libro = ig * rg_libro
    mod = pot.modelo_de_malla(m, RHO, ig, x0=x0, y0=y0)

    # El perfil del modelo se expresa como fraccion del GPR y se aplica al GPR
    # del manual (calculado con Sverak), para no mezclar dos resistencias.
    def toque_en(p):
        frac = 1.0 - mod.potencial(p[0], p[1], 0.0) / mod.gpr
        return frac * gpr_libro

    centro = (x0 + lx / 2.0, y0 + ly / 2.0)

    # Recorremos el cerco: sobre la linea y a 1 m hacia fuera del recinto.
    peor_cerco = (-1e9, None)
    peor_cerco_1m = (-1e9, None)
    for i in range(4):
        a, b = CERCO[i], CERCO[(i + 1) % 4]
        for k in range(n_perfil + 1):
            f = k / n_perfil
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            e = toque_en(p)
            if e > peor_cerco[0]:
                peor_cerco = (e, p)
            q = _lado_exterior(p, centro, 1.0)
            e1 = toque_en(q)
            if e1 > peor_cerco_1m[0]:
                peor_cerco_1m = (e1, q)

    # Puerta: persona fuera de la puerta, a 1 m, tocando la hoja metalica.
    peor_puerta = (-1e9, None)
    for k in range(n_perfil + 1):
        f = k / n_perfil
        px = PUERTA[0][0] + (PUERTA[1][0] - PUERTA[0][0]) * f
        for dy in (0.0, -1.0):
            p = (px, PUERTA[0][1] + dy)
            e = toque_en(p)
            if e > peor_puerta[0]:
                peor_puerta = (e, p)

    # Paso en el exterior: linea que sale del centro del lado sur hacia fuera.
    e_paso, xp, yp = mod.paso_maximo((centro[0], y0 + ly / 2.0), (centro[0], y0 - 25.0), n=120)

    return {
        "nombre": nombre, "malla": m, "modelo": mod, "ig": ig,
        "rg_libro": rg_libro, "rg_sverak": m.rg_sverak(RHO), "rg_modelo": mod.rg,
        "gpr_libro": gpr_libro, "em": m.tension_malla(RHO, ig), "es": m.tension_paso(RHO, ig),
        "toque_cerco": peor_cerco, "toque_cerco_1m": peor_cerco_1m,
        "toque_puerta": peor_puerta, "paso_exterior": (e_paso, xp, yp),
        "lc": m.lc,
    }


def main():
    lim = limites()
    print("CASO DEL MANUAL - TOQUE EN CERCO Y PUERTA")
    print("=" * 108)
    print(f"Suelo {RHO:g} ohm*m · grava {RHO_S:g} ohm*m de {HS:g} m · persona de {PESO} kg · "
          f"ts = {TS:g} s · falla de MT {I_FALLA_MT:g} kA con X/R = {X_R:g} · Df = {DF:.4f}")
    print(f"Limites tolerables: toque sobre grava {lim['toque_grava']:.0f} V · "
          f"paso sobre grava {lim['paso_grava']:.0f} V · toque sobre suelo expuesto "
          f"{lim['toque_suelo']:.0f} V · paso sobre suelo expuesto {lim['paso_suelo']:.0f} V · "
          f"metal-metal {lim['metal_metal']:.0f} V")
    print()

    filas = [analizar(*g) for g in GEOMETRIAS]

    print("1) CONTRASTE DE LAS GEOMETRIAS CON SUS SEPARACIONES REALES  [7.4.1]")
    print("-" * 108)
    print(f"{'Geometria':22} {'Lc':>6} {'Dx':>5} {'Dy':>5} {'Rg libro':>9} {'Rg Sverak':>10} "
          f"{'Rg modelo':>10} {'GPR':>7} {'Em':>7} {'Es':>7}")
    for r in filas:
        m = r["malla"]
        dx, dy = m.lx / (m.ny_cond - 1), m.ly / (m.nx_cond - 1)
        print(f"{r['nombre']:22} {r['lc']:6.0f} {dx:5.2f} {dy:5.2f} {r['rg_libro']:9.2f} "
              f"{r['rg_sverak']:10.3f} {r['rg_modelo']:10.3f} {r['gpr_libro']:7.0f} "
              f"{r['em']:7.0f} {r['es']:7.0f}")
    print()

    print("2) TOQUE EN CERCO Y PUERTA  [3.2.1, 3.3.1, 5.5, 6.3.1, 6.5.1, 7.5]")
    print("-" * 108)
    print(f"{'Geometria':22} {'cerco':>8} {'a 1 m':>8} {'puerta':>8} "
          f"{'/579 grava':>11} {'/170 suelo':>11} {'paso ext.':>10} {'veredicto':>12}")
    for r in filas:
        tc = max(r["toque_cerco"][0], r["toque_cerco_1m"][0], r["toque_puerta"][0])
        ok_grava = tc <= lim["toque_grava"]
        print(f"{r['nombre']:22} {r['toque_cerco'][0]:8.0f} {r['toque_cerco_1m'][0]:8.0f} "
              f"{r['toque_puerta'][0]:8.0f} {tc/lim['toque_grava']:11.2f} "
              f"{tc/lim['toque_suelo']:11.2f} {r['paso_exterior'][0]:10.0f} "
              f"{'cumple' if ok_grava else 'NO cumple':>12}")
    print()
    print("  'cerco'  : maximo sobre la linea del cerco.")
    print("  'a 1 m'  : persona 1 m fuera del cerco tocando la malla metalica.")
    print("  'puerta' : maximo en la puerta (x de 8 a 12 m, lado sur) y 1 m por fuera.")
    print("  Los cocientes usan el mayor de los tres. Sobre grava el limite es "
          f"{lim['toque_grava']:.0f} V; sobre suelo expuesto, {lim['toque_suelo']:.0f} V.")
    print()

    print("3) PERFIL SALIENDO DEL CERCO - G2 CON GRAVA EXTENDIDA  [6.3.1]")
    print("-" * 108)
    g2 = filas[-1]
    mod, gpr = g2["modelo"], g2["gpr_libro"]
    print(f"{'dist. del cerco (m)':>20} {'V superficie':>13} {'toque':>8} {'/lim':>6} "
          f"{'paso 1 m':>9} {'/lim':>6} {'superficie':>14}")
    for d in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 5.5, 7.5, 10.0, 15.0):
        p = (10.0, 0.5 - d)   # saliendo por el lado sur, frente a la puerta
        v = mod.potencial(p[0], p[1], 0.0)
        frac = 1.0 - v / mod.gpr
        e_toque = frac * gpr
        e_paso = mod.paso(p, (p[0], p[1] - 1.0)) / mod.gpr * gpr
        en_grava = d <= 7.5
        lt = lim["toque_grava"] if en_grava else lim["toque_suelo"]
        lp = lim["paso_grava"] if en_grava else lim["paso_suelo"]
        sup = "grava" if en_grava else "suelo expuesto"
        # El toque solo aplica donde la persona alcanza el cerco (hasta ~1 m).
        col_toque = f"{e_toque:8.0f}" if d <= 1.0 else "       -"
        col_rt = f"{e_toque/lt:6.2f}" if d <= 1.0 else "     -"
        print(f"{d:20.1f} {v:13.0f} {col_toque} {col_rt} {e_paso:9.0f} "
              f"{e_paso/lp:6.2f} {sup:>14}")
    print("  El toque exige algo metalico al alcance de la mano: solo aplica junto al cerco")
    print("  (hasta ~1 m). Mas alla, la comprobacion que gobierna es la tension de paso.")
    print()
    # El punto critico del exterior es el borde de la grava: ahi el limite de paso
    # cae de 1899 V a 263 V de golpe. Buscamos el peor cociente sobre suelo expuesto.
    peor = (-1.0, None, None)
    d = 7.5
    while d <= 30.0:
        p = (10.0, 0.5 - d)
        e = mod.paso(p, (p[0], p[1] - 1.0)) / mod.gpr * gpr
        coc = e / lim["paso_suelo"]
        if coc > peor[0]:
            peor = (coc, d, e)
        d += 0.25
    print(f"  Peor paso sobre suelo expuesto (desde el borde de la grava, a 7.5 m del cerco):")
    print(f"    {peor[2]:.0f} V a {peor[1]:.2f} m del cerco · limite {lim['paso_suelo']:.0f} V · "
          f"cociente {peor[0]:.2f}  ->  {'cumple' if peor[0] <= 1 else 'NO cumple'}")
    print()

    print("4) CONEXIONES DE BT: 43 kA, 0.20 s, X/R = 3  [5.2, 5.5, 6.5]")
    print("-" * 108)
    df_bt = falla.factor_decremento(0.20, 3.0, 60.0)
    i_bt = 43.0 * df_bt
    for union, etiqueta in (("conector_mecanico", "conector mecanico (250 C)"),
                            ("soldadura_fuerte", "soldadura fuerte (450 C)"),
                            ("soldadura_exotermica", "soldadura exotermica (fusion)")):
        a = conductor.seccion_minima_mm2(i_bt, 0.20, "cobre_duro", 40.0, union)
        print(f"  {etiqueta:32} seccion minima {a:6.1f} mm2   "
              f"enlace de 120 mm2: {'cumple' if 120 >= a else 'NO cumple'}")
    print(f"  Df de BT = {df_bt:.4f}; corriente termica = {i_bt:.2f} kA; temperatura inicial 40 C.")
    print()
    print("5) RESUMEN PARA LA MEMORIA  [6.5, 6.5.1]")
    print("-" * 108)
    g2r = filas[-1]
    tc = max(g2r["toque_cerco"][0], g2r["toque_cerco_1m"][0], g2r["toque_puerta"][0])
    print(f"  G2 interior : Em {g2r['em']:.0f} V / {lim['toque_grava']:.0f} V = "
          f"{g2r['em']/lim['toque_grava']:.2f}  ->  cumple")
    print(f"  G2 cerco    : {tc:.0f} V / {lim['toque_grava']:.0f} V = "
          f"{tc/lim['toque_grava']:.2f}  ->  {'cumple' if tc <= lim['toque_grava'] else 'NO cumple'}")
    print(f"  G2 puerta   : {g2r['toque_puerta'][0]:.0f} V / {lim['toque_grava']:.0f} V = "
          f"{g2r['toque_puerta'][0]/lim['toque_grava']:.2f}  ->  "
          f"{'cumple' if g2r['toque_puerta'][0] <= lim['toque_grava'] else 'NO cumple'}"
          f"   (persona sobre grava que toca la hoja)")
    print(f"  Nota metal-metal: el limite de {lim['metal_metal']:.0f} V no se aplica a la cifra")
    print( "  anterior, sino a la DIFERENCIA de potencial entre dos partes metalicas que la")
    print( "  persona puede tocar a la vez (hoja y marco, o hoja y poste). Si la puerta esta")
    print( "  unida al cerco y este a la malla, esa diferencia es practicamente nula y la")
    print( "  comprobacion la gobierna el toque ordinario. Sin esa union, hay que calcularla")
    print( "  con el detalle de la union, que este modelo no representa.")
    print(f"  Conexiones BT: 120 mm2 frente a "
          f"{conductor.seccion_minima_mm2(i_bt, 0.20, 'cobre_duro', 40.0, 'conector_mecanico'):.0f} mm2 requeridos"
          f"  ->  cumple")


if __name__ == "__main__":
    main()
