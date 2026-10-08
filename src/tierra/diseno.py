"""Orquestador: evalua un diseno completo de malla segun el flujo de IEEE 80.

Entrada: diccionario (ver ejemplos/*.json). Salida: diccionario con resultados,
verificaciones, advertencias y los pasos de la memoria de calculo.
"""

import copy
import math

from . import conductor as cond
from . import falla, suelo, tolerables
from .malla import Malla

ESQUEMA_EJEMPLO = {
    "proyecto": "Ejemplo didactico: malla 70 x 70 m con 20 varillas",
    "suelo": {"rho": 400.0},
    "capa_superficial": {"rho_s": 2500.0, "hs": 0.102},
    "falla": {"i_falla_ka": 3.18, "sf": 0.6, "x_r": 10.0, "frecuencia": 60.0, "tf": 0.5, "cp": 1.0},
    "descarga": {"ts": 0.5, "peso": 70},
    "conductor": {"material": "cobre_duro", "ta": 40.0, "union": "soldadura_exotermica", "diametro_mm": 10.0},
    "malla": {
        "lx": 70.0, "ly": 70.0, "nx": 11, "ny": 11, "h": 0.5,
        "varillas": {"cantidad": 20, "largo": 7.5, "diametro_mm": 16.0, "en_perimetro": True},
    },
    "metodo_rg": "sverak",
}


def _paso(simbolo, nombre, valor, unidad, formula=""):
    return {"simbolo": simbolo, "nombre": nombre, "valor": valor, "unidad": unidad, "formula": formula}


def _num(d, clave, defecto=None, minimo=None, nombre=None):
    v = d.get(clave, defecto)
    if v is None:
        raise ValueError(f"Falta el dato '{nombre or clave}'.")
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"El dato '{nombre or clave}' debe ser un numero.") from None
    if not math.isfinite(v):
        raise ValueError(f"El dato '{nombre or clave}' no es un numero finito.")
    if minimo is not None and v <= minimo:
        raise ValueError(f"El dato '{nombre or clave}' debe ser mayor que {minimo:g}.")
    return v


def _construir_malla(m, d_mm):
    v = m.get("varillas") or {}
    cantidad = int(_num(v, "cantidad", 0, nombre="varillas.cantidad") if v else 0)
    return Malla.rectangular(
        lx=_num(m, "lx", minimo=0, nombre="malla.lx"),
        ly=_num(m, "ly", minimo=0, nombre="malla.ly"),
        nx=int(_num(m, "nx", minimo=1, nombre="malla.nx")),
        ny=int(_num(m, "ny", minimo=1, nombre="malla.ny")),
        h=_num(m, "h", minimo=0, nombre="malla.h"),
        d=d_mm / 1000.0,
        n_varillas=cantidad,
        l_varilla=_num(v, "largo", 0.0, nombre="varillas.largo") if cantidad else 0.0,
        d_varilla=_num(v, "diametro_mm", 16.0, nombre="varillas.diametro_mm") / 1000.0,
        varillas_perimetro=bool(v.get("en_perimetro", True)),
    )


def evaluar(datos):
    """Evalua el diseno. Lanza ValueError con mensaje en espanol si hay datos invalidos."""
    datos = copy.deepcopy(datos)
    pasos, advertencias, extra = [], [], {}

    # ---- suelo --------------------------------------------------------
    s = datos.get("suelo") or {}
    if "wenner" in s and s["wenner"]:
        b = float(s.get("b", 0.0) or 0.0)
        med = []
        for fila in s["wenner"]:
            a, r = _num(fila, "a", minimo=0, nombre="wenner.a"), _num(fila, "R", minimo=0, nombre="wenner.R")
            med.append((a, suelo.rho_aparente_wenner(a, r, b)))
        rho = float(s["rho"]) if s.get("rho") else suelo.rho_promedio(med)
        extra["mediciones_rho_a"] = [{"a": a, "rho_a": r} for a, r in med]
        if len(med) >= 3:
            try:
                extra["modelo_dos_capas"] = suelo.ajustar_dos_capas(med)
            except ValueError:
                pass
        origen = "promedio de las resistividades aparentes Wenner" if not s.get("rho") else "valor ingresado por el usuario"
        pasos.append(_paso("rho", f"Resistividad de diseno ({origen})", rho, "ohm*m", "rho = promedio(rho_a)"))
    else:
        rho = _num(s, "rho", minimo=0, nombre="suelo.rho")
        pasos.append(_paso("rho", "Resistividad del suelo", rho, "ohm*m", "dato"))

    cs_ = datos.get("capa_superficial") or {}
    rho_s = float(cs_["rho_s"]) if cs_.get("rho_s") else None
    hs = float(cs_.get("hs", 0.0) or 0.0)

    # ---- falla --------------------------------------------------------
    f = datos.get("falla") or {}
    tf = _num(f, "tf", minimo=0, nombre="falla.tf")
    x_r = _num(f, "x_r", 0.0, nombre="falla.x_r")
    frec = _num(f, "frecuencia", 60.0, minimo=0, nombre="falla.frecuencia")
    sf = _num(f, "sf", 1.0, minimo=0, nombre="falla.sf")
    cp = _num(f, "cp", 1.0, minimo=0, nombre="falla.cp")
    i_falla = _num(f, "i_falla_ka", minimo=0, nombre="falla.i_falla_ka")
    ta = falla.constante_tiempo_dc(x_r, frec)
    df = falla.factor_decremento(tf, x_r, frec)
    ig = falla.corriente_malla(i_falla, sf, df, cp)
    pasos += [
        _paso("Ta", "Constante de tiempo DC", ta, "s", "Ta = (X/R)/(2 pi f)"),
        _paso("Df", "Factor de decremento", df, "-", "Df = sqrt(1 + Ta/tf (1 - exp(-2 tf/Ta)))"),
        _paso("IG", "Corriente maxima de malla", ig, "A", "IG = Cp * Df * Sf * If"),
    ]

    # ---- descarga y tensiones tolerables ------------------------------
    de = datos.get("descarga") or {}
    ts = _num(de, "ts", tf, minimo=0, nombre="descarga.ts")
    peso = int(_num(de, "peso", 70, nombre="descarga.peso"))
    cs, e_paso_t, e_cont_t = tolerables.tensiones_tolerables(rho, ts, peso, rho_s, hs)
    pasos += [
        _paso("Cs", "Factor de capa superficial", cs, "-", "Cs = 1 - 0.09 (1 - rho/rho_s)/(2 hs + 0.09)"),
        _paso("E_paso,tol", f"Tension de paso tolerable ({peso} kg)", e_paso_t, "V", "(1000 + 6 Cs rho_s) k / sqrt(ts)"),
        _paso("E_cont,tol", f"Tension de contacto tolerable ({peso} kg)", e_cont_t, "V", "(1000 + 1.5 Cs rho_s) k / sqrt(ts)"),
    ]

    # ---- conductor ----------------------------------------------------
    c = datos.get("conductor") or {}
    material = c.get("material", "cobre_duro")
    ta_amb = _num(c, "ta", 40.0, nombre="conductor.ta")
    tc = _num(c, "tc", tf, minimo=0, nombre="conductor.tc")
    union = c.get("union", "soldadura_exotermica")
    d_mm = _num(c, "diametro_mm", minimo=0, nombre="conductor.diametro_mm")
    # Criterio conservador: el conductor se dimensiona con la corriente de falla
    # completa 3I0 (sin factor de division Sf), porque un conductor puede quedar
    # en serie con toda la corriente de falla.
    a_min = cond.seccion_minima_mm2(i_falla, tc, material, ta_amb, union)
    d_min = cond.diametro_desde_seccion_mm(a_min)
    a_real = cond.seccion_desde_diametro_mm2(d_mm)
    pasos += [
        _paso("A_min", "Seccion minima del conductor", a_min, "mm2",
              "A = I / sqrt((TCAP 1e-4)/(tc alpha_r rho_r) ln((K0+Tm)/(K0+Ta)))"),
        _paso("d_min", "Diametro minimo equivalente", d_min, "mm", "d = sqrt(4 A / pi)"),
    ]

    # ---- malla --------------------------------------------------------
    malla = _construir_malla(datos.get("malla") or {}, d_mm)
    advertencias += malla.advertencias()
    metodo = datos.get("metodo_rg", "sverak")
    rg_sv = malla.rg_sverak(rho)
    rg_sw = malla.rg_schwarz(rho)
    rg = rg_sw if metodo == "schwarz" else rg_sv
    em = malla.tension_malla(rho, ig)
    es = malla.tension_paso(rho, ig)
    gpr = ig * rg
    pasos += [
        _paso("A", "Area de la malla", malla.area, "m2", "A = Lx Ly"),
        _paso("Lc", "Longitud de conductor horizontal", malla.lc, "m", "Lc = nx Lx + ny Ly"),
        _paso("LR", "Longitud total de varillas", malla.lr_total, "m", "LR = N_var * L_var"),
        _paso("LT", "Longitud total enterrada", malla.lt, "m", "LT = Lc + LR"),
        _paso("D", "Espaciamiento entre conductores", malla.d_sep, "m", "promedio de los espaciamientos"),
        _paso("Rg (Sverak)", "Resistencia de malla", rg_sv, "ohm", "rho [1/LT + 1/sqrt(20A) (1 + 1/(1+h sqrt(20/A)))]"),
        _paso("Rg (Schwarz)", "Resistencia de malla (verificacion)", rg_sw, "ohm", "(R1 R2 - Rm^2)/(R1 + R2 - 2 Rm)"),
        _paso("GPR", "Elevacion de potencial de tierra", gpr, "V", "GPR = IG Rg"),
        _paso("n", "Numero efectivo de conductores", malla.n, "-", "n = na nb nc nd"),
        _paso("Ki", "Factor de irregularidad", malla.ki, "-", "Ki = 0.644 + 0.148 n"),
        _paso("Kii", "Factor de correccion por electrodos", malla.kii, "-", "1 con varillas perimetrales; si no 1/(2n)^(2/n)"),
        _paso("Kh", "Factor de profundidad", malla.kh, "-", "Kh = sqrt(1 + h/h0)"),
        _paso("Km", "Factor geometrico de malla", malla.km, "-", "ver IEEE 80"),
        _paso("Ks", "Factor geometrico de paso", malla.ks, "-", "ver IEEE 80"),
        _paso("LM", "Longitud efectiva para tension de malla", malla.lm, "m", "Lc + [1.55 + 1.22 Lr/sqrt(Lx^2+Ly^2)] LR"),
        _paso("Ls", "Longitud efectiva para tension de paso", malla.ls, "m", "Ls = 0.75 Lc + 0.85 LR"),
        _paso("Em", "Tension de malla", em, "V", "Em = rho Km Ki IG / LM"),
        _paso("Es", "Tension de paso", es, "V", "Es = rho Ks Ki IG / Ls"),
    ]

    # ---- verificaciones -----------------------------------------------
    verif = [
        {"nombre": "Seccion del conductor", "valor": a_real, "limite": a_min, "unidad": "mm2",
         "cumple": a_real >= a_min, "criterio": "A_real >= A_min"},
        {"nombre": "Tension de malla", "valor": em, "limite": e_cont_t, "unidad": "V",
         "cumple": em <= e_cont_t, "criterio": "Em <= E_contacto,tol"},
        {"nombre": "Tension de paso", "valor": es, "limite": e_paso_t, "unidad": "V",
         "cumple": es <= e_paso_t, "criterio": "Es <= E_paso,tol"},
    ]
    gpr_ok = gpr <= e_cont_t
    info_gpr = ("GPR <= E_contacto,tol: la malla cumple sin mas analisis (criterio de diseno inicial)."
                if gpr_ok else "GPR > E_contacto,tol: se requiere verificar Em y Es (ya evaluados arriba).")

    return {
        "proyecto": datos.get("proyecto", ""),
        "metodo_rg": metodo,
        "rho": rho, "cs": cs, "df": df, "ig_a": ig, "gpr_v": gpr, "rg_ohm": rg,
        "rg_sverak": rg_sv, "rg_schwarz": rg_sw,
        "e_malla": em, "e_paso": es, "e_contacto_tol": e_cont_t, "e_paso_tol": e_paso_t,
        "a_min_mm2": a_min, "d_min_mm": d_min,
        "n": malla.n, "km": malla.km, "ks": malla.ks, "ki": malla.ki,
        "verificaciones": verif,
        "cumple": all(v["cumple"] for v in verif),
        "nota_gpr": info_gpr,
        "advertencias": advertencias,
        "pasos": pasos,
        "extra": extra,
    }


def barrido_conductores(datos, n_max=40):
    """Evalua el diseno variando nx = ny entre 3 y n_max. Devuelve lista de filas
    {n_conductores, em, es, rg, cumple, valida} y el primer n que cumple con
    geometria valida (o None)."""
    filas, primero = [], None
    for n in range(3, int(n_max) + 1):
        d = copy.deepcopy(datos)
        d["malla"]["nx"] = n
        d["malla"]["ny"] = n
        try:
            r = evaluar(d)
        except ValueError:
            continue
        # Km/Ks solo son validos con D > 2.5 m: esas filas se muestran pero no se proponen.
        valida = not any("espaciamiento" in a for a in r["advertencias"])
        ok = r["cumple"]
        filas.append({"n_conductores": n, "em": r["e_malla"], "es": r["e_paso"], "rg": r["rg_ohm"],
                      "cumple": ok, "valida": valida})
        if ok and valida and primero is None:
            primero = n
    return filas, primero


def memoria_markdown(r):
    """Memoria de calculo en Markdown a partir del resultado de evaluar()."""
    L = []
    L.append(f"# Memoria de calculo de malla de puesta a tierra")
    if r.get("proyecto"):
        L.append(f"\n**Proyecto:** {r['proyecto']}")
    L.append("\nMetodologia: IEEE Std 80. Calculado con la calculadora de puesta a tierra (repositorio del libro).\n")
    L.append("## Pasos de calculo\n")
    L.append("| Simbolo | Descripcion | Valor | Unidad | Expresion |")
    L.append("|---|---|---:|---|---|")
    for p in r["pasos"]:
        v = p["valor"]
        txt = f"{v:,.4f}" if abs(v) < 1000 else f"{v:,.1f}"
        L.append(f"| {p['simbolo']} | {p['nombre']} | {txt} | {p['unidad']} | {p['formula']} |")
    L.append("\n## Verificaciones\n")
    L.append("| Verificacion | Valor | Limite | Criterio | Resultado |")
    L.append("|---|---:|---:|---|---|")
    for v in r["verificaciones"]:
        L.append(f"| {v['nombre']} | {v['valor']:,.2f} {v['unidad']} | {v['limite']:,.2f} {v['unidad']} | {v['criterio']} | {'CUMPLE' if v['cumple'] else 'NO CUMPLE'} |")
    L.append(f"\n{r['nota_gpr']}")
    L.append(f"\n**Conclusion: {'EL DISENO CUMPLE' if r['cumple'] else 'EL DISENO NO CUMPLE'}**")
    if r["advertencias"]:
        L.append("\n## Advertencias\n")
        for a in r["advertencias"]:
            L.append(f"- {a}")
    return "\n".join(L) + "\n"
