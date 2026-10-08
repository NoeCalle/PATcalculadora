"""Corriente de falla, factor de decremento y corriente de malla (IEEE 80)."""

import math


def constante_tiempo_dc(x_r, f=60.0):
    """Ta = (X/R) / (2 pi f)  [s]"""
    if x_r < 0 or f <= 0:
        raise ValueError("X/R no puede ser negativo y la frecuencia debe ser positiva.")
    return x_r / (2.0 * math.pi * f)


def factor_decremento(tf, x_r, f=60.0):
    """Factor de decremento Df para una falla de duracion tf [s].

        Df = sqrt( 1 + (Ta/tf) (1 - exp(-2 tf/Ta)) )
    """
    if tf <= 0:
        raise ValueError("La duracion de la falla tf debe ser positiva.")
    ta = constante_tiempo_dc(x_r, f)
    if ta == 0:
        return 1.0
    return math.sqrt(1.0 + (ta / tf) * (1.0 - math.exp(-2.0 * tf / ta)))


def corriente_falla_monofasica(v_ll_kv, z1, z2, z0, rf=0.0):
    """Falla monofasica a tierra. Devuelve (3I0 [kA], X/R de la secuencia total).

    z1, z2, z0: impedancias de secuencia [ohm] (numeros complejos o reales)
    rf: resistencia de falla [ohm]
        3I0 = 3 E / (Z1 + Z2 + Z0 + 3 Rf),  E = V_ll / sqrt(3)
    """
    if v_ll_kv <= 0:
        raise ValueError("La tension de linea debe ser positiva.")
    z = complex(z1) + complex(z2) + complex(z0) + 3.0 * rf
    if abs(z) == 0:
        raise ValueError("La impedancia total no puede ser cero.")
    i_ka = math.sqrt(3.0) * v_ll_kv / abs(z)
    x_r = abs(z.imag) / z.real if z.real > 0 else float("inf")
    return i_ka, x_r


def corriente_malla(i_falla_ka, sf=1.0, df=1.0, cp=1.0):
    """Corriente maxima de malla IG [A].

        IG = Cp * Df * Sf * If

    i_falla_ka: corriente simetrica de falla a tierra 3I0 [kA]
    sf: factor de division de corriente de falla (0..1)
    df: factor de decremento
    cp: factor de proyeccion de crecimiento del sistema (>= 1)
    """
    if i_falla_ka <= 0:
        raise ValueError("La corriente de falla debe ser positiva.")
    if not (0 < sf <= 1):
        raise ValueError("El factor de division Sf debe estar entre 0 y 1.")
    if cp < 1:
        raise ValueError("El factor de crecimiento Cp debe ser >= 1.")
    return cp * df * sf * i_falla_ka * 1000.0
