"""Toque en cerco y puerta del caso del manual de mallas de puesta a tierra.

Resuelve los marcadores [CALCULAR] del manual que el metodo simplificado de
IEEE 80 no cubre: el toque en el cerco y en la puerta, el paso en el exterior y
el contraste de las areas ampliadas con sus separaciones reales.

CONVENIO DE ESCALA. El modelo de potencial resuelve su propia resistencia, que
queda por debajo de la de Sverak (ver docs/VALIDACION.md). El manual adopta
Sverak, asi que TODAS las tensiones de este informe se expresan en la escala del
GPR del manual: el modelo aporta la forma del perfil y se aplica al GPR adoptado
mediante tierra.potencial.PerfilEscalado. Nunca se mezclan las dos escalas.

SUPERFICIE DE LOS APOYOS. La tension de paso tolerable supone los dos pies sobre
la misma superficie. Este informe clasifica cada medicion segun donde cae cada
apoyo y senala por separado los casos que quedan a caballo del borde de la grava,
que la formula de Cs no cubre.

Ejecutar:  python ejemplos/caso_libro_cerco.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tierra import conductor, falla, potencial as pot, tolerables  # noqa: E402
from tierra.malla import Malla  # noqa: E402

# --------------------------------------------------------------------------
# Datos del caso (ficha del manual)
# --------------------------------------------------------------------------
RHO = 150.0                 # resistividad del suelo [ohm*m], modelo uniforme
RHO_S, HS = 3000.0, 0.10    # grava
PESO, TS = 50, 0.70         # persona y duracion de respaldo
I_FALLA_MT, X_R = 5.0, 10.0  # kA y relacion X/R de la falla de MT
D_COND = 0.0105             # diametro del conductor enterrado de 70 mm2 [m]

# Recinto: rectangulo original de 20 x 30 m con origen en su esquina suroeste.
# El cerco esta 0.50 m hacia dentro; la puerta ocupa x de 8 a 12 m en el lado sur.
CERCO = [(0.5, 0.5), (19.5, 0.5), (19.5, 29.5), (0.5, 29.5)]
PUERTA_X = (8.0, 12.0)
PUERTA_Y = 0.5

# Grava del diseno final: cubre hasta 2 m mas alla del borde de G2, o sea 7.5 m
# por fuera del cerco.
GRAVA_HASTA = 7.5   # m medidos desde el cerco hacia fuera

DF = falla.factor_decremento(TS, X_R, 60.0)

# (nombre, lx, ly, nx, ny, x0, y0, Sf, Rg del manual)
# nx = conductores paralelos a x (de longitud lx); ny = paralelos a y.
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
    return {"cs_grava": cs_g, "toque_grava": toque_g, "paso_grava": paso_g,
            "toque_suelo": toque_s, "paso_suelo": paso_s,
            "metal_metal": pot.tolerable_metal_metal(TS, PESO)}


def peor_paso_exterior(esc, grava, cerco, eps=0.02, res=0.25, paso_pies=1.0):
    """Peor tension de paso en el exterior, buscando por el perimetro de la grava.

    El maximo no esta en la linea central sino junto al borde de la grava y en las
    esquinas, donde el gradiente es mayor. Se barre una banda alrededor de ese
    borde, con las esquinas en detalle, y se evalua en 24 direcciones por punto.

    grava, cerco: rectangulos (x0, y0, ancho, alto).
    Devuelve dict con el peor caso de cada clase de superficie.
    """
    gx0, gy0, gw, gh = grava
    gx1, gy1 = gx0 + gw, gy0 + gh
    dirs = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 15)]

    cand = []
    # banda a ambos lados del borde de la grava
    for t in (-eps, eps, -0.3, 0.3, -1.0, 1.0):
        n_x = int(gw / res) + 1
        n_y = int(gh / res) + 1
        for i in range(n_x):
            x = gx0 + res * i
            cand += [(x, gy0 - t), (x, gy1 + t)]
        for j in range(n_y):
            y = gy0 + res * j
            cand += [(gx0 - t, y), (gx1 + t, y)]
    # esquinas con detalle angular
    for (cx, cy) in ((gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)):
        for a in range(0, 360, 5):
            dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
            for r in (eps, 0.1, 0.3, 0.6, 1.0):
                cand.append((cx + dx * r, cy + dy * r))

    pares = []
    for p in cand:
        if dentro(cerco, *p):
            continue
        for (dx, dy) in dirs:
            q = (p[0] + dx * paso_pies, p[1] + dy * paso_pies)
            if dentro(cerco, *q):
                continue
            pares.append((p, q))
    pts = sorted({p for par in pares for p in par})
    V = dict(zip(pts, esc.potenciales(pts, bloque=512)))

    peores = {"grava": (-1.0, None, None), "suelo": (-1.0, None, None),
              "mixto": (-1.0, None, None)}
    for (p, q) in pares:
        e = abs(V[p] - V[q])
        g1, g2 = dentro(grava, *p), dentro(grava, *q)
        clave = "grava" if (g1 and g2) else ("suelo" if not (g1 or g2) else "mixto")
        if e > peores[clave][0]:
            peores[clave] = (e, p, q)
    return peores


def dentro(rect, x, y, eps=1e-9):
    x0, y0, w, h = rect
    return (x0 - eps) <= x <= (x0 + w + eps) and (y0 - eps) <= y <= (y0 + h + eps)


def _hacia_fuera(p, centro, retiro):
    """Desplaza p una distancia `retiro` alejandose del centro, perpendicular
    al lado de cerco mas proximo."""
    dx, dy = p[0] - centro[0], p[1] - centro[1]
    if abs(dx) >= abs(dy):
        return (p[0] + retiro * (1 if dx > 0 else -1), p[1])
    return (p[0], p[1] + retiro * (1 if dy > 0 else -1))


def analizar(nombre, lx, ly, nx, ny, x0, y0, sf, rg_manual, n_perfil=60):
    m = Malla.rectangular(lx, ly, nx, ny, h=0.50, d=D_COND, n_varillas=4, l_varilla=3.0)
    ig = I_FALLA_MT * 1000.0 * sf * DF
    modelo = pot.modelo_de_malla(m, RHO, ig, x0=x0, y0=y0)
    # Una sola escala: la del GPR del manual.
    esc = modelo.en_escala(ig * rg_manual)
    centro = (x0 + lx / 2.0, y0 + ly / 2.0)

    peor_cerco = (-1e9, None)
    peor_1m = (-1e9, None)
    for i in range(4):
        a, b = CERCO[i], CERCO[(i + 1) % 4]
        for k in range(n_perfil + 1):
            f = k / n_perfil
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            e = esc.toque(*p)
            if e > peor_cerco[0]:
                peor_cerco = (e, p)
            q = _hacia_fuera(p, centro, 1.0)
            e1 = esc.toque(*q)
            if e1 > peor_1m[0]:
                peor_1m = (e1, q)

    peor_puerta = (-1e9, None)
    for k in range(n_perfil + 1):
        px = PUERTA_X[0] + (PUERTA_X[1] - PUERTA_X[0]) * k / n_perfil
        for dy in (0.0, -1.0):
            p = (px, PUERTA_Y + dy)
            e = esc.toque(*p)
            if e > peor_puerta[0]:
                peor_puerta = (e, p)

    # Paso: linea x = centro, desde el centro de la malla hasta 30 m al sur del
    # cerco. Se recorre con apoyos separados 1 m y se clasifica la superficie.
    paso_grava = (-1e9, None)
    paso_suelo = (-1e9, None)
    paso_mixto = (-1e9, None)
    EPS = 1e-9   # el borde de la grava se compara con tolerancia
    pasos = int((30.0 + ly / 2.0) / 0.05) + 1
    for i in range(pasos):
        d = -(ly / 2.0) + 0.05 * i   # arranca en el centro de la malla
        p1 = (centro[0], PUERTA_Y - d)
        p2 = (centro[0], PUERTA_Y - d - 1.0)
        e = esc.paso(p1, p2)
        g1 = d <= GRAVA_HASTA + EPS
        g2 = (d + 1.0) <= GRAVA_HASTA + EPS
        if g1 and g2:
            if e > paso_grava[0]:
                paso_grava = (e, d)
        elif not (g1 or g2):
            if e > paso_suelo[0]:
                paso_suelo = (e, d)
        else:
            if e > paso_mixto[0]:
                paso_mixto = (e, d)

    return {"nombre": nombre, "malla": m, "modelo": modelo, "escala": esc, "ig": ig,
            "rg_manual": rg_manual, "rg_sverak": m.rg_sverak(RHO), "rg_modelo": modelo.rg,
            "gpr_manual": esc.gpr, "gpr_modelo": modelo.gpr, "factor": esc.factor,
            "em": m.tension_malla(RHO, ig), "es": m.tension_paso(RHO, ig),
            "toque_cerco": peor_cerco, "toque_1m": peor_1m, "toque_puerta": peor_puerta,
            "paso_grava": paso_grava, "paso_suelo": paso_suelo, "paso_mixto": paso_mixto}


def main():
    lim = limites()
    L = "-" * 104
    print("CASO DEL MANUAL - TOQUE EN CERCO Y PUERTA")
    print("=" * 104)
    print(f"Suelo {RHO:g} ohm*m · grava {RHO_S:g} ohm*m de {HS:g} m hasta {GRAVA_HASTA:g} m "
          f"del cerco · persona de {PESO} kg · ts = {TS:g} s")
    print(f"Falla de MT {I_FALLA_MT:g} kA con X/R = {X_R:g} · Df = {DF:.4f} · "
          f"IG = 5000 · Sf · Df")
    print(f"Limites tolerables [V]: toque sobre grava {lim['toque_grava']:.1f} · "
          f"paso sobre grava {lim['paso_grava']:.1f} · toque sobre suelo {lim['toque_suelo']:.1f} · "
          f"paso sobre suelo {lim['paso_suelo']:.1f} · metal-metal {lim['metal_metal']:.1f}")
    print()
    print("TODAS las tensiones estan en la escala del GPR del manual (Rg de Sverak).")
    print("El modelo aporta la forma del perfil; el factor de escala se indica por geometria.")
    print()

    filas = [analizar(*g) for g in GEOMETRIAS]

    print("1) GEOMETRIAS CON SUS SEPARACIONES REALES  [7.4.1]")
    print(L)
    print(f"{'Geometria':22} {'Lc':>5} {'Dx':>5} {'Dy':>5} {'IG':>7} "
          f"{'Rg man.':>8} {'Rg Sver.':>9} {'Rg mod.':>8} {'GPR man.':>9} {'GPR mod.':>9} "
          f"{'k':>6} {'Em':>6} {'Es':>6}")
    for r in filas:
        m = r["malla"]
        dx, dy = m.lx / (m.ny_cond - 1), m.ly / (m.nx_cond - 1)
        print(f"{r['nombre']:22} {m.lc:5.0f} {dx:5.2f} {dy:5.2f} {r['ig']:7.1f} "
              f"{r['rg_manual']:8.2f} {r['rg_sverak']:9.3f} {r['rg_modelo']:8.3f} "
              f"{r['gpr_manual']:9.1f} {r['gpr_modelo']:9.1f} {r['factor']:6.4f} "
              f"{r['em']:6.0f} {r['es']:6.0f}")
    print()
    print("  'Rg man.' es la del manual; 'Rg Sver.' la que recalcula esta herramienta con la")
    print("  misma formula (coinciden); 'Rg mod.' la del modelo de potencial. k = GPR man./GPR mod.")
    print("  Em es la tension de malla: toque en el INTERIOR. Es es la estimacion de paso del")
    print("  metodo simplificado y NO se limita al interior: el paso puede alcanzar su maximo")
    print("  fuera del perimetro. Se conservan separadas la estimacion simplificada (Em, Es) y")
    print("  la evaluacion por perfiles de las secciones siguientes.")
    print()

    print("2) TOQUE EN CERCO Y PUERTA  [3.2.1, 3.3.1, 5.5, 6.3.1, 6.5.1, 7.5]")
    print(L)
    print(f"{'Geometria':22} {'cerco':>8} {'a 1 m':>8} {'puerta':>8} {'peor':>8} "
          f"{'/579 grava':>11} {'/170 suelo':>11} {'veredicto':>12}")
    for r in filas:
        peor = max(r["toque_cerco"][0], r["toque_1m"][0], r["toque_puerta"][0])
        ok = peor <= lim["toque_grava"]
        print(f"{r['nombre']:22} {r['toque_cerco'][0]:8.1f} {r['toque_1m'][0]:8.1f} "
              f"{r['toque_puerta'][0]:8.1f} {peor:8.1f} {peor/lim['toque_grava']:11.3f} "
              f"{peor/lim['toque_suelo']:11.3f} {'cumple' if ok else 'NO cumple':>12}")
    print()
    print("  'cerco' : peor punto sobre la linea del cerco, persona ahi tocando el cerco.")
    print("  'a 1 m' : persona 1 m por fuera del cerco, tocandolo con el brazo extendido.")
    print("  'puerta': peor punto en la puerta (x de 8 a 12 m, lado sur) y 1 m por fuera.")
    print("  Los cocientes usan 'peor'. La superficie bajo los pies decide el limite: con")
    print("  grava son 579 V; sobre suelo expuesto, 170 V. Solo G2 tiene grava especificada")
    print("  hasta 7.5 m del cerco, asi que para las demas se dan ambos cocientes.")
    print()

    print("3) PASO EN LA LINEA CENTRAL - COTA INFERIOR, NO EL MAXIMO")
    print(L)
    print(f"{'Geometria':22} {'ambos grava':>12} {'/1899':>7} {'ambos suelo':>12} {'/263':>7} "
          f"{'a caballo':>10} {'dist.':>7}")
    for r in filas:
        pg, ps, pm = r["paso_grava"], r["paso_suelo"], r["paso_mixto"]
        print(f"{r['nombre']:22} {pg[0]:12.1f} {pg[0]/lim['paso_grava']:7.3f} "
              f"{ps[0]:12.1f} {ps[0]/lim['paso_suelo']:7.3f} {pm[0]:10.1f} {pm[1]:7.1f}")
    print()
    print("  ATENCION: estas cifras corresponden a UN recorrido, la linea x = centro de la")
    print("  malla hacia el sur, con los apoyos separados 1 m. NO son el maximo exterior:")
    print("  el gradiente es mayor en las esquinas y junto al borde de la grava. Sirven como")
    print("  cota inferior y para comparar geometrias entre si. El maximo real se busca")
    print("  barriendo el exterior (seccion 4 para G2, y ejemplos/caso_libro_paso_exterior.py).")
    print("  'ambos grava': los dos apoyos dentro de los 7.5 m de grava.")
    print("  'ambos suelo': los dos apoyos mas alla del borde de la grava.")
    print("  'a caballo'  : un apoyo sobre grava y el otro sobre suelo expuesto. La formula")
    print("                 de Cs supone los dos pies sobre la misma superficie, asi que este")
    print("                 caso requiere un criterio especifico para apoyos sobre superficies")
    print("                 distintas; queda como comprobacion ABIERTA, no como cumplimiento.")
    print()

    print("4) PERFIL SALIENDO DEL CERCO - G2 CON GRAVA EXTENDIDA  [6.3.1]")
    print(L)
    g2 = filas[-1]
    esc = g2["escala"]
    print(f"  Potencial del cerco = GPR del manual = {esc.gpr:.1f} V  (el cerco esta unido a la malla)")
    print(f"  Corriente inyectada IG = {g2['ig']:.1f} A · Rg del modelo = {g2['rg_modelo']:.4f} ohm "
          f"· GPR del modelo = {g2['gpr_modelo']:.1f} V · factor k = {esc.factor:.4f}")
    print()
    print(f"{'dist. cerco (m)':>16} {'V superficie':>13} {'GPR - V':>9} {'toque':>8} "
          f"{'paso 1 m':>9} {'superficie de los apoyos':>26}")
    for d in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 5.5, 7.0, 7.5, 10.0, 15.0):
        p = (10.0, PUERTA_Y - d)
        v = esc.potencial(*p)
        e_toque = esc.toque(*p)
        e_paso = esc.paso(p, (p[0], p[1] - 1.0))
        g1, g2b = d <= GRAVA_HASTA, (d + 1.0) <= GRAVA_HASTA
        sup = "grava / grava" if (g1 and g2b) else ("suelo / suelo" if not (g1 or g2b)
                                                    else "grava / suelo (a caballo)")
        col_t = f"{e_toque:8.1f}" if d <= 1.0 else "       -"
        print(f"{d:16.1f} {v:13.1f} {esc.gpr - v:9.1f} {col_t} {e_paso:9.1f} {sup:>26}")
    print()
    print("  'V superficie' y 'toque' estan en la misma escala: su suma es el GPR del manual.")
    print("  El toque solo aplica donde la persona alcanza el cerco (hasta ~1 m); mas alla la")
    print("  comprobacion que gobierna es el paso.")
    print()

    print("4b) MAXIMO DE PASO EN EL EXTERIOR DE G2 - BARRIDO DEL BORDE DE LA GRAVA")
    print(L)
    r_g2 = filas[-1]
    grava_rect = (-5.0 - 2.0, -5.0 - 2.0, 30.0 + 4.0, 40.0 + 4.0)   # 2 m mas alla de G2
    cerco_rect = (0.5, 0.5, 19.0, 29.0)
    peores = peor_paso_exterior(r_g2["escala"], grava_rect, cerco_rect)
    for clave, etiqueta, limite in (
            ("grava", "Ambos apoyos sobre grava", lim["paso_grava"]),
            ("suelo", "Ambos apoyos sobre suelo expuesto", lim["paso_suelo"]),
            ("mixto", "Apoyos sobre superficies distintas", None)):
        e, p1, p2 = peores[clave]
        if limite is not None:
            print(f"  {etiqueta:36} {e:8.1f} V / {limite:8.1f} V = {e/limite:.3f}   "
                  f"{'cumple' if e <= limite else 'NO CUMPLE'}")
        else:
            print(f"  {etiqueta:36} {e:8.1f} V   requiere un criterio especifico para")
            print(f"  {'':36}            apoyos sobre superficies distintas:")
            print(f"  {'':36}            COMPROBACION ABIERTA")
        print(f"  {'':36} apoyos en ({p1[0]:.2f}, {p1[1]:.2f}) y ({p2[0]:.2f}, {p2[1]:.2f})")
    print()
    print("  El maximo con ambos apoyos sobre suelo aparece a pocos centimetros del borde de")
    print("  la grava, en las cuatro esquinas por simetria, y SUPERA el limite. La cobertura de")
    print("  grava de 2 m mas alla del borde de la malla no basta para esa comprobacion.")
    print("  Al refinar la discretizacion el valor se estabiliza (288.5, 287.7 y 287.4 V con")
    print("  832, 1664 y 3328 subsegmentos), asi que no es un artefacto numerico.")
    print()
    print("  Extension de grava necesaria (peor paso con ambos apoyos justo fuera de ella):")
    print("    2.0 m -> 289.6 V / 263.4 = 1.099   NO cumple   (cobertura actual)")
    print("    2.5 m -> 252.3 V / 263.4 = 0.958   cumple, con poco margen")
    print("    3.0 m -> 223.9 V / 263.4 = 0.850   cumple")
    print("  Reproducible con ejemplos/caso_libro_paso_exterior.py")
    print()

    print("5) CONEXIONES DE BT: 43 kA, 0.20 s, X/R = 3  [5.2, 5.5, 6.5]")
    print(L)
    df_bt = falla.factor_decremento(0.20, 3.0, 60.0)
    i_bt = 43.0 * df_bt
    print(f"  Df = {df_bt:.4f} · corriente termica = {i_bt:.2f} kA · temperatura inicial 40 C")
    for union, etiqueta in (("conector_mecanico", "conector mecanico (250 C)"),
                            ("soldadura_fuerte", "soldadura fuerte (450 C)"),
                            ("soldadura_exotermica", "soldadura exotermica (fusion)")):
        a = conductor.seccion_minima_mm2(i_bt, 0.20, "cobre_duro", 40.0, union)
        print(f"  {etiqueta:32} seccion minima {a:6.1f} mm2   "
              f"enlace de 120 mm2: {'cumple' if 120 >= a else 'NO cumple'}")
    print()

    print("6) RESUMEN DE G2 PARA LA MEMORIA  [6.5, 6.5.1]")
    print(L)
    r = filas[-1]
    peor_toque = max(r["toque_cerco"][0], r["toque_1m"][0], r["toque_puerta"][0])
    a_bt = conductor.seccion_minima_mm2(i_bt, 0.20, "cobre_duro", 40.0, "conector_mecanico")
    tabla = [
        ("Toque interior (Em, metodo simplificado)", r["em"], lim["toque_grava"], "V"),
        ("Toque junto al cerco y en la puerta", peor_toque, lim["toque_grava"], "V"),
        ("Paso exterior, ambos apoyos sobre grava", peores["grava"][0], lim["paso_grava"], "V"),
        ("Paso exterior, ambos apoyos sobre suelo", peores["suelo"][0], lim["paso_suelo"], "V"),
        ("Enlace de BT (120 mm2 adoptados)", a_bt, 120.0, "mm2"),
    ]
    print(f"{'Comprobacion':44} {'Resultado':>11} {'Limite':>9} {'Cociente':>9} {'Veredicto':>11}")
    for nombre, val, lim_v, u in tabla:
        coc = val / lim_v
        print(f"{nombre:44} {val:9.1f} {u:>2} {lim_v:9.1f} {coc:9.3f} "
              f"{'cumple' if coc <= 1 else 'NO cumple':>11}")
    print()
    print(f"  Las dos filas de paso vienen del barrido de la seccion 4b, no de la linea central.")
    print(f"  ABIERTO - apoyos sobre superficies distintas: {peores['mixto'][0]:.1f} V en el borde")
    print("  de la grava. Requiere un criterio especifico para apoyos sobre superficies")
    print("  distintas; la resistencia de contacto de los pies forma parte de la evaluacion y")
    print("  la grava la modifica, asi que no procede aplicarle ninguno de los dos limites.")
    print("  ABIERTO - el paso exterior sobre suelo expuesto NO cumple con la grava actual de")
    print("  2 m; con 2.5 m cumple con poco margen y con 3.0 m con margen razonable.")
    print("  Metal-metal: el limite de "
          f"{lim['metal_metal']:.1f} V no se aplica al toque de la puerta de arriba, sino a la")
    print("  DIFERENCIA de potencial entre dos partes metalicas que la persona toque a la vez")
    print("  (hoja y marco, hoja y poste). Si la puerta esta unida al cerco y este a la malla,")
    print("  esa diferencia es practicamente nula. Sin esa union hay que calcularla con el")
    print("  detalle de la union, que este modelo no representa.")


if __name__ == "__main__":
    main()
