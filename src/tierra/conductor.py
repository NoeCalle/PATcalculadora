"""Seccion minima del conductor de la malla (ecuacion de Onderdonk segun IEEE 80)."""

import math

from .materiales import TEMP_MAX_UNION, obtener


def seccion_minima_mm2(i_ka, tc, material="cobre_duro", ta=40.0, union="soldadura_exotermica"):
    """Seccion minima [mm2] para que el conductor soporte la corriente i_ka [kA]
    durante tc [s] sin superar la temperatura maxima admisible.

        A = I / sqrt( (TCAP*1e-4)/(tc*alpha_r*rho_r) * ln((K0+Tm)/(K0+Ta)) )

    i_ka : corriente eficaz simetrica que circula por el conductor [kA]
    tc   : duracion de la corriente [s]
    ta   : temperatura ambiente [C]
    union: tipo de union que limita la temperatura (ver TEMP_MAX_UNION)
    """
    if i_ka <= 0 or tc <= 0:
        raise ValueError("La corriente y el tiempo del conductor deben ser positivos.")
    mat = obtener(material)
    if union not in TEMP_MAX_UNION:
        raise ValueError(f"Tipo de union desconocido: '{union}'. Opciones: {', '.join(TEMP_MAX_UNION)}")
    tm = TEMP_MAX_UNION[union] or mat.tm
    tm = min(tm, mat.tm)
    if tm <= ta:
        raise ValueError("La temperatura maxima admisible debe ser mayor que la ambiente.")
    factor = (mat.tcap * 1e-4) / (tc * mat.alpha_r * mat.rho_r) * math.log((mat.k0 + tm) / (mat.k0 + ta))
    return i_ka / math.sqrt(factor)


def diametro_desde_seccion_mm(a_mm2):
    return math.sqrt(4.0 * a_mm2 / math.pi)


def seccion_desde_diametro_mm2(d_mm):
    return math.pi * d_mm**2 / 4.0
