"""Resistividad del suelo: metodo de Wenner y modelo de dos capas (Sunde)."""

import math


def rho_aparente_wenner(a, resistencia, b=0.0):
    """Resistividad aparente [ohm*m] de una medicion Wenner.

    a: separacion entre electrodos [m]; resistencia: R medida [ohm]
    b: profundidad de enterramiento de los electrodos [m]
       b = 0  ->  rho_a = 2 pi a R
       b > 0  ->  formula completa de Wenner
    """
    if a <= 0 or resistencia <= 0:
        raise ValueError("La separacion a y la resistencia medida deben ser positivas.")
    if b <= 0:
        return 2.0 * math.pi * a * resistencia
    den = 1.0 + 2.0 * a / math.sqrt(a * a + 4.0 * b * b) - a / math.sqrt(a * a + b * b)
    return 4.0 * math.pi * a * resistencia / den


def rho_aparente_dos_capas(rho1, rho2, h, a):
    """Resistividad aparente Wenner [ohm*m] sobre un suelo de dos capas.

        rho_a = rho1 [ 1 + 4 sum_{n>=1} K^n ( 1/sqrt(1+(2nh/a)^2) - 1/sqrt(4+(2nh/a)^2) ) ]
        K = (rho2 - rho1)/(rho2 + rho1)
    """
    k = (rho2 - rho1) / (rho2 + rho1)
    if abs(k) < 1e-12:
        return rho1
    suma = 0.0
    n = 1
    while n < 20000:
        x = 2.0 * n * h / a
        termino = (k**n) * (1.0 / math.sqrt(1.0 + x * x) - 1.0 / math.sqrt(4.0 + x * x))
        suma += termino
        if n >= 3 and abs(termino) < 1e-9 * max(1.0, abs(suma)):
            break
        n += 1
    return rho1 * (1.0 + 4.0 * suma)


def rho_promedio(mediciones):
    """Promedio aritmetico de las resistividades aparentes [(a, rho_a), ...]."""
    if not mediciones:
        raise ValueError("No hay mediciones.")
    return sum(r for _, r in mediciones) / len(mediciones)


def ajustar_dos_capas(mediciones, razon_max=50.0):
    """Ajusta (rho1, rho2, h) a mediciones Wenner [(a, rho_a), ...].

    Busqueda en malla logaritmica + refinamiento por busqueda de patron,
    minimizando el error cuadratico de los logaritmos. El ajuste de un suelo
    de dos capas no siempre es unico: revisar el resultado contra la curva
    medida y el criterio del ingeniero.

    Devuelve dict con rho1, rho2, h, error_rms_pct y la comparacion punto a punto.
    """
    if len(mediciones) < 3:
        raise ValueError("Se necesitan al menos 3 mediciones para ajustar dos capas.")
    datos = sorted((float(a), float(r)) for a, r in mediciones)
    amin, amax = datos[0][0], datos[-1][0]
    rmin = min(r for _, r in datos)
    rmax = max(r for _, r in datos)
    logs = [math.log(r) for _, r in datos]

    def error(p):
        r1, r2, h = math.exp(p[0]), math.exp(p[1]), math.exp(p[2])
        razon = r2 / r1
        if razon > razon_max or razon < 1.0 / razon_max:
            return 1e9
        e = 0.0
        for (a, _), lr in zip(datos, logs):
            e += (math.log(rho_aparente_dos_capas(r1, r2, h, a)) - lr) ** 2
        return e

    def geom(lo, hi, n):
        return [math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * i / (n - 1)) for i in range(n)]

    mejor, p_mejor = 1e18, None
    for r1 in geom(rmin * 0.5, rmax * 1.5, 10):
        for r2 in geom(rmin * 0.2, rmax * 5.0, 12):
            for h in geom(amin * 0.3, amax * 2.0, 14):
                p = (math.log(r1), math.log(r2), math.log(h))
                e = error(p)
                if e < mejor:
                    mejor, p_mejor = e, p

    paso = 0.3
    p = list(p_mejor)
    for _ in range(80):
        mejoro = False
        for i in range(3):
            for s in (+paso, -paso):
                q = list(p)
                q[i] += s
                e = error(q)
                if e < mejor:
                    mejor, p, mejoro = e, q, True
        if not mejoro:
            paso *= 0.5
            if paso < 1e-4:
                break

    r1, r2, h = math.exp(p[0]), math.exp(p[1]), math.exp(p[2])
    detalle = []
    for a, r in datos:
        m = rho_aparente_dos_capas(r1, r2, h, a)
        detalle.append({"a": a, "rho_medida": r, "rho_modelo": m})
    rms = math.sqrt(mejor / len(datos)) * 100.0
    return {"rho1": r1, "rho2": r2, "h": h, "error_rms_pct": rms, "detalle": detalle}
