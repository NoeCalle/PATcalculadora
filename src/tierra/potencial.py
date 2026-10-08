"""Perfil de potencial superficial de una malla enterrada.

Para que IEEE 80 compare la tension de toque hay que conocer el potencial de la
superficie donde la persona apoya los pies. Em y Es del metodo simplificado solo
describen el INTERIOR de la malla: no sirven para el cerco, la puerta ni el suelo
exterior. Este modulo calcula el potencial en cualquier punto de la superficie y,
con el, las tensiones de toque y de paso en posiciones accesibles concretas.

MODELO (leer antes de usar los resultados)

Suelo uniforme de resistividad rho en un semiespacio. La malla se divide en
segmentos rectos; cada uno fuga al terreno una corriente desconocida I_j con
densidad uniforme a lo largo del propio segmento. Se impone la condicion fisica
que el metodo de densidad uniforme omite: TODOS los segmentos estan al mismo
potencial V, porque el cobre los une.

    suma_j  Z_ij I_j = V        para cada segmento i
    suma_j  I_j      = IG

Z_ij es el potencial que aparece en el centro del segmento i por unidad de
corriente fugada por el segmento j, calculado con el metodo de imagenes respecto
de la superficie del terreno:

    Z_ij = (rho / 4 pi L_j) * [ int_j ds/r + int_j ds/r' ]

con r la distancia al segmento real y r' la distancia a su imagen. Para un
segmento recto la integral tiene forma cerrada con asinh. El sistema es lineal y
se resuelve de una vez; de su solucion salen a la vez la resistencia de la malla
(Rg = V / IG) y el potencial de cualquier punto de la superficie.

Este planteamiento es el metodo analitico clasico de analisis de mallas. Que
entregue una Rg proxima a la de Sverak es su comprobacion de coherencia: ver
docs/VALIDACION.md.

LIMITES. Suelo uniforme: no modela dos capas. No incluye el acoplamiento
inductivo ni la impedancia longitudinal del conductor, por lo que corresponde a
un modelo resistivo de baja frecuencia. No sustituye al metodo simplificado de
IEEE 80 para el interior: lo complementa en las posiciones que el metodo no
cubre. Las comprobaciones del interior se siguen haciendo con Em y Es.
"""

import math
from dataclasses import dataclass

try:  # numpy acelera el sistema lineal; el modulo funciona sin el
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

RADIO_POR_DEFECTO = 0.00525  # m (conductor de 10.5 mm de diametro)


@dataclass(frozen=True)
class Segmento:
    """Segmento recto enterrado. z negativo = bajo la superficie."""

    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float

    @property
    def longitud(self):
        return math.sqrt((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2
                         + (self.z2 - self.z1) ** 2)

    @property
    def centro(self):
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0, (self.z1 + self.z2) / 2.0)

    def subdividir(self, n):
        out = []
        for k in range(n):
            f0, f1 = k / n, (k + 1) / n
            out.append(Segmento(
                self.x1 + (self.x2 - self.x1) * f0, self.y1 + (self.y2 - self.y1) * f0,
                self.z1 + (self.z2 - self.z1) * f0,
                self.x1 + (self.x2 - self.x1) * f1, self.y1 + (self.y2 - self.y1) * f1,
                self.z1 + (self.z2 - self.z1) * f1))
        return out


def _integral(seg, px, py, pz, a_min):
    """int_0^L ds / r desde el punto (px, py, pz) hasta el segmento."""
    L = seg.longitud
    if L <= 0:
        return 0.0
    ux, uy, uz = (seg.x2 - seg.x1) / L, (seg.y2 - seg.y1) / L, (seg.z2 - seg.z1) / L
    wx, wy, wz = px - seg.x1, py - seg.y1, pz - seg.z1
    t0 = wx * ux + wy * uy + wz * uz
    d2 = (wx * wx + wy * wy + wz * wz) - t0 * t0
    d = math.sqrt(max(d2, a_min * a_min))
    return math.asinh((L - t0) / d) + math.asinh(t0 / d)


def _coef(seg, rho, px, py, pz, a_min):
    """Potencial en (px, py, pz) por unidad de corriente fugada por el segmento."""
    L = seg.longitud
    img = Segmento(seg.x1, seg.y1, -seg.z1, seg.x2, seg.y2, -seg.z2)
    return rho * (_integral(seg, px, py, pz, a_min) + _integral(img, px, py, pz, a_min)) \
        / (4.0 * math.pi * L)


def _coefs_vectorizado(A, B, L, Lp, invL, punto, rho, a_min):
    """Potencial en `punto` por unidad de corriente de cada segmento, con numpy.

    A, B: extremos (N, 3); L: longitudes (N,); Lp: extremos imagen (A', B').
    Devuelve un vector (N,) de coeficientes.
    """
    px, py, pz = punto
    total = None
    for (Ai, Bi) in ((A, B), (Lp[0], Lp[1])):
        u = (Bi - Ai) * invL[:, None]
        w = _np.empty_like(Ai)
        w[:, 0] = px - Ai[:, 0]
        w[:, 1] = py - Ai[:, 1]
        w[:, 2] = pz - Ai[:, 2]
        t0 = (w * u).sum(axis=1)
        d2 = (w * w).sum(axis=1) - t0 * t0
        d = _np.sqrt(_np.maximum(d2, a_min * a_min))
        val = _np.arcsinh((L - t0) / d) + _np.arcsinh(t0 / d)
        total = val if total is None else total + val
    return rho * total * invL / (4.0 * math.pi)


def _resolver(A, b):
    """Eliminacion gaussiana con pivoteo parcial (sin dependencias)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-14:
            raise ValueError("El sistema de potenciales es singular; revisa la geometria.")
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] / piv
            if f:
                row_r, row_c = M[r], M[c]
                for k in range(c, n + 1):
                    row_r[k] -= f * row_c[k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


class ModeloPotencial:
    """Resuelve el reparto de corriente de fuga y evalua potenciales.

    segmentos: lista de Segmento de la malla (conductores y varillas)
    rho: resistividad del suelo [ohm*m]
    ig: corriente total que la malla descarga al terreno [A]
    radio_conductor: radio del conductor [m]
    n_sub: subdivisiones por segmento. Si se omite, se eligen para llegar a unos
           160 subsegmentos, que equilibra precision y tiempo de calculo.
    """

    def __init__(self, segmentos, rho, ig, radio_conductor=RADIO_POR_DEFECTO,
                 n_sub=None, largo_subsegmento=None, max_subsegmentos=1800):
        """largo_subsegmento: longitud objetivo de cada subsegmento [m]. La
        precision del perfil exige subsegmentos cortos frente al espaciamiento de
        la malla; por omision se toma la mitad del espaciamiento (ver
        `modelo_de_malla`). max_subsegmentos acota el tamano del sistema lineal."""
        if not segmentos:
            raise ValueError("La malla no tiene segmentos.")
        if rho <= 0:
            raise ValueError("La resistividad debe ser positiva.")
        if ig <= 0:
            raise ValueError("La corriente de malla debe ser positiva.")
        l_total = sum(s.longitud for s in segmentos)
        if n_sub is None:
            if largo_subsegmento is None:
                largo_subsegmento = l_total / max(len(segmentos), 1) / 8.0
            n_sub = max(1, math.ceil(min(s.longitud for s in segmentos) / largo_subsegmento))
            while len(segmentos) * n_sub > max_subsegmentos and n_sub > 1:
                n_sub -= 1
        self.rho, self.ig, self.a = rho, ig, radio_conductor
        self.n_sub = n_sub
        self.subsegmentos = [s for seg in segmentos for s in seg.subdividir(n_sub)]
        self.largo_subsegmento_medio = l_total / len(self.subsegmentos)
        self._preparar_arreglos()
        self._resolver_reparto()

    def _preparar_arreglos(self):
        segs = self.subsegmentos
        if _np is None:
            self._arr = None
            return
        A = _np.array([[s.x1, s.y1, s.z1] for s in segs], dtype=float)
        B = _np.array([[s.x2, s.y2, s.z2] for s in segs], dtype=float)
        L = _np.array([s.longitud for s in segs], dtype=float)
        Ai = A.copy(); Ai[:, 2] *= -1.0
        Bi = B.copy(); Bi[:, 2] *= -1.0
        self._arr = (A, B, L, (Ai, Bi), 1.0 / L)

    def _coefs(self, punto):
        """Coeficientes de potencial de todos los subsegmentos en un punto."""
        if self._arr is not None:
            A, B, L, Lp, invL = self._arr
            return _coefs_vectorizado(A, B, L, Lp, invL, punto, self.rho, self.a)
        return [_coef(s, self.rho, punto[0], punto[1], punto[2], self.a)
                for s in self.subsegmentos]

    def _resolver_reparto(self):
        n = len(self.subsegmentos)
        centros = [s.centro for s in self.subsegmentos]
        if _np is not None:
            Z = _np.empty((n, n), dtype=float)
            for i, c in enumerate(centros):
                Z[i, :] = self._coefs(c)
            M = _np.empty((n + 1, n + 1), dtype=float)
            M[:n, :n] = Z
            M[:n, n] = -1.0
            M[n, :n] = 1.0
            M[n, n] = 0.0
            b = _np.zeros(n + 1, dtype=float)
            b[n] = self.ig
            sol = _np.linalg.solve(M, b)
            self.corrientes = sol[:n]
            self.gpr = float(sol[n])
        else:  # pragma: no cover
            Z = [self._coefs(c) for c in centros]
            A = [list(Z[i]) + [-1.0] for i in range(n)]
            A.append([1.0] * n + [0.0])
            sol = _resolver(A, [0.0] * n + [self.ig])
            self.corrientes = sol[:n]
            self.gpr = sol[n]

    # ---- resultados ---------------------------------------------------
    @property
    def rg(self):
        """Resistencia de la malla que entrega este modelo [ohm]."""
        return self.gpr / self.ig

    def potencial(self, px, py, pz=0.0):
        """Potencial [V] en un punto, respecto de tierra remota."""
        c = self._coefs((px, py, pz))
        if self._arr is not None:
            return float(_np.dot(c, self.corrientes))
        return sum(ci * ii for ci, ii in zip(c, self.corrientes))

    def toque(self, px, py):
        """Tension de toque [V]: persona de pie en (px, py) que toca metal unido
        a la malla.  E_toque = GPR - V_superficie."""
        return self.gpr - self.potencial(px, py, 0.0)

    def paso(self, p1, p2):
        """Tension de paso [V] entre dos apoyos (normalmente separados 1 m)."""
        return abs(self.potencial(p1[0], p1[1], 0.0) - self.potencial(p2[0], p2[1], 0.0))

    def perfil(self, punto_a, punto_b, n=60):
        """Perfil de potencial y de toque entre dos puntos de la superficie."""
        (xa, ya), (xb, yb) = punto_a, punto_b
        largo = math.hypot(xb - xa, yb - ya)
        out = []
        for i in range(n + 1):
            f = i / n
            px, py = xa + (xb - xa) * f, ya + (yb - ya) * f
            v = self.potencial(px, py, 0.0)
            out.append({"s": largo * f, "x": px, "y": py, "v": v, "toque": self.gpr - v})
        return out

    def toque_maximo(self, punto_a, punto_b, n=120):
        """Maximo de la tension de toque en una linea. Devuelve (E, x, y)."""
        peor = (-float("inf"), None, None)
        for p in self.perfil(punto_a, punto_b, n):
            if p["toque"] > peor[0]:
                peor = (p["toque"], p["x"], p["y"])
        return peor

    def paso_maximo(self, punto_a, punto_b, n=120, separacion=1.0):
        """Maxima tension de paso a lo largo de una linea, con apoyos separados
        `separacion` metros en la direccion de la linea. Devuelve (E, x, y)."""
        (xa, ya), (xb, yb) = punto_a, punto_b
        largo = math.hypot(xb - xa, yb - ya)
        if largo <= separacion:
            raise ValueError("La linea debe ser mas larga que la separacion de los pies.")
        ux, uy = (xb - xa) / largo, (yb - ya) / largo
        peor = (-float("inf"), None, None)
        for i in range(n + 1):
            s = (largo - separacion) * i / n
            x1, y1 = xa + ux * s, ya + uy * s
            x2, y2 = x1 + ux * separacion, y1 + uy * separacion
            e = self.paso((x1, y1), (x2, y2))
            if e > peor[0]:
                peor = (e, x1, y1)
        return peor


def posiciones_perimetro(x0, y0, lx, ly, n):
    """n posiciones repartidas de forma uniforme a lo largo del perimetro.

    Con n <= 4 devuelve las esquinas. Se usa para colocar las varillas cuando el
    proyecto solo indica su cantidad.
    """
    if n <= 0:
        return []
    esquinas = [(x0, y0), (x0 + lx, y0), (x0 + lx, y0 + ly), (x0, y0 + ly)]
    if n <= 4:
        return esquinas[:n]
    per = 2.0 * (lx + ly)
    lados = [((x0, y0), (x0 + lx, y0), lx), ((x0 + lx, y0), (x0 + lx, y0 + ly), ly),
             ((x0 + lx, y0 + ly), (x0, y0 + ly), lx), ((x0, y0 + ly), (x0, y0), ly)]
    out = []
    for k in range(n):
        s = per * k / n
        for (a, b, largo) in lados:
            if s <= largo or largo == 0:
                f = s / largo if largo else 0.0
                out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
            s -= largo
    return out


def segmentos_malla_rectangular(malla, x0=0.0, y0=0.0, varillas_xy=None):
    """Segmentos de una malla rectangular construida con Malla.rectangular().

    La malla ocupa [x0, x0+lx] x [y0, y0+ly].
    varillas_xy: posiciones (x, y) de las varillas; por omision, las esquinas.
    """
    lx, ly, h = malla.lx, malla.ly, malla.h
    nx, ny = malla.nx_cond, malla.ny_cond
    if nx < 2 or ny < 2:
        raise ValueError("Construye la malla con Malla.rectangular() para obtener sus segmentos.")
    # Los conductores se parten en los cruces: asi todos los subsegmentos miden
    # como el espaciamiento y el refinado converge de forma monotona.
    xs = [x0 + lx * j / (ny - 1) for j in range(ny)]
    ys = [y0 + ly * i / (nx - 1) for i in range(nx)]
    segs = []
    for y in ys:  # conductores paralelos a x
        for j in range(ny - 1):
            segs.append(Segmento(xs[j], y, -h, xs[j + 1], y, -h))
    for x in xs:  # conductores paralelos a y
        for i in range(nx - 1):
            segs.append(Segmento(x, ys[i], -h, x, ys[i + 1], -h))
    if malla.n_varillas > 0:
        if varillas_xy is None:
            varillas_xy = posiciones_perimetro(x0, y0, lx, ly, malla.n_varillas)
        for (vx, vy) in list(varillas_xy)[: malla.n_varillas]:
            segs.append(Segmento(vx, vy, -h, vx, vy, -h - malla.l_varilla))
    return segs


def modelo_de_malla(malla, rho, ig, x0=0.0, y0=0.0, varillas_xy=None, n_sub=None,
                    largo_subsegmento=None, max_subsegmentos=1800):
    """Atajo: construye el modelo de potencial de una malla rectangular.

    Por omision los subsegmentos miden un cuarto del espaciamiento entre
    conductores, que es la escala a la que varia el potencial superficial. Con ese
    refinado la tension de toque en el cerco queda a ~1 % de su valor convergido
    (ver el estudio de convergencia en docs/VALIDACION.md).
    """
    segs = segmentos_malla_rectangular(malla, x0, y0, varillas_xy)
    if n_sub is None and largo_subsegmento is None:
        largo_subsegmento = malla.d_sep / 4.0
    return ModeloPotencial(segs, rho, ig, radio_conductor=malla.d / 2.0, n_sub=n_sub,
                           largo_subsegmento=largo_subsegmento,
                           max_subsegmentos=max_subsegmentos)


def tolerable_metal_metal(ts, peso=70):
    """Tension tolerable de toque metal-metal [V].

    Persona que toca dos partes metalicas a la vez, o que esta de pie sobre metal
    puesto a tierra: no hay resistencia del terreno en serie con los pies, por lo
    que el limite es mucho mas bajo que el del toque convencional.

        E_mm = 1000 k / sqrt(ts)
    """
    k = {50: 0.116, 70: 0.157}
    if peso not in k:
        raise ValueError("El peso corporal debe ser 50 o 70 kg.")
    if ts <= 0:
        raise ValueError("La duracion ts debe ser positiva.")
    return 1000.0 * k[peso] / math.sqrt(ts)
