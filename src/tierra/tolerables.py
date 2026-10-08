"""Tensiones tolerables de paso y contacto (IEEE 80)."""

import math

_K = {50: 0.116, 70: 0.157}


def factor_cs(rho, rho_s=None, hs=0.0):
    """Factor de reduccion de la capa superficial Cs.

        Cs = 1 - 0.09 (1 - rho/rho_s) / (2 hs + 0.09)

    Sin capa superficial (rho_s None, igual a rho o hs = 0) Cs = 1.
    """
    if rho <= 0:
        raise ValueError("La resistividad del suelo debe ser positiva.")
    if rho_s is None or hs <= 0 or rho_s == rho:
        return 1.0
    if rho_s <= 0:
        raise ValueError("La resistividad de la capa superficial debe ser positiva.")
    return 1.0 - 0.09 * (1.0 - rho / rho_s) / (2.0 * hs + 0.09)


def tensiones_tolerables(rho, ts, peso=70, rho_s=None, hs=0.0):
    """Devuelve (Cs, E_paso, E_contacto) en voltios.

        E_paso     = (1000 + 6   Cs rho_s) k / sqrt(ts)
        E_contacto = (1000 + 1.5 Cs rho_s) k / sqrt(ts)

    k = 0.116 (peso 50 kg) o 0.157 (peso 70 kg). Sin capa superficial rho_s = rho.
    """
    if ts <= 0:
        raise ValueError("La duracion de la descarga ts debe ser positiva.")
    if peso not in _K:
        raise ValueError("El peso corporal debe ser 50 o 70 kg.")
    cs = factor_cs(rho, rho_s, hs)
    rs = rho if (rho_s is None or hs <= 0) else rho_s
    k = _K[peso]
    e_paso = (1000.0 + 6.0 * cs * rs) * k / math.sqrt(ts)
    e_contacto = (1000.0 + 1.5 * cs * rs) * k / math.sqrt(ts)
    return cs, e_paso, e_contacto
