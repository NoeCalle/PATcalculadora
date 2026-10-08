"""Geometria y ecuaciones de la malla de puesta a tierra (IEEE 80).

Todas las longitudes en metros, resistividades en ohm*m, corrientes en A.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Malla:
    """Geometria de la malla. Para mallas rectangulares usar Malla.rectangular()."""

    area: float  # A  [m2]
    perimetro: float  # Lp [m]
    lc: float  # longitud total de conductor horizontal [m]
    lx: float  # dimension maxima en x [m]
    ly: float  # dimension maxima en y [m]
    dm: float  # distancia maxima entre dos puntos de la malla [m]
    d_sep: float  # espaciamiento entre conductores paralelos D [m]
    h: float  # profundidad de enterramiento [m]
    d: float  # diametro del conductor [m]
    n_varillas: int = 0
    l_varilla: float = 0.0  # longitud de cada varilla [m]
    d_varilla: float = 0.016  # diametro de varilla [m]
    varillas_perimetro: bool = True  # varillas en esquinas/perimetro
    nx_cond: int = 0  # conductores paralelos a x (0 = geometria no rectangular)
    ny_cond: int = 0  # conductores paralelos a y

    # ---- constructores -------------------------------------------------
    @classmethod
    def rectangular(cls, lx, ly, nx, ny, h, d, n_varillas=0, l_varilla=0.0,
                    d_varilla=0.016, varillas_perimetro=True):
        """Malla rectangular lx x ly con nx conductores paralelos a x y ny paralelos a y.

        D se toma como el promedio de los dos espaciamientos.
        """
        if nx < 2 or ny < 2:
            raise ValueError("Se necesitan al menos 2 conductores en cada direccion.")
        dx = lx / (ny - 1)
        dy = ly / (nx - 1)
        return cls(
            area=lx * ly,
            perimetro=2.0 * (lx + ly),
            lc=nx * lx + ny * ly,
            lx=lx,
            ly=ly,
            dm=math.hypot(lx, ly),
            d_sep=(dx + dy) / 2.0,
            h=h,
            d=d,
            n_varillas=n_varillas,
            l_varilla=l_varilla,
            d_varilla=d_varilla,
            varillas_perimetro=varillas_perimetro,
            nx_cond=nx,
            ny_cond=ny,
        )

    def __post_init__(self):
        for nombre in ("area", "perimetro", "lc", "lx", "ly", "dm", "d_sep", "h", "d"):
            if getattr(self, nombre) <= 0:
                raise ValueError(f"El parametro de malla '{nombre}' debe ser positivo.")
        if self.n_varillas < 0:
            raise ValueError("El numero de varillas no puede ser negativo.")
        if self.n_varillas > 0 and (self.l_varilla <= 0 or self.d_varilla <= 0):
            raise ValueError("Con varillas, su longitud y diametro deben ser positivos.")

    # ---- magnitudes derivadas -----------------------------------------
    @property
    def lr_total(self):
        """LR: longitud total de varillas [m]."""
        return self.n_varillas * self.l_varilla

    @property
    def lt(self):
        """LT = Lc + LR [m]."""
        return self.lc + self.lr_total

    @property
    def n(self):
        """Numero efectivo de conductores paralelos n = na nb nc nd."""
        na = 2.0 * self.lc / self.perimetro
        nb = math.sqrt(self.perimetro / (4.0 * math.sqrt(self.area)))
        nc = (self.lx * self.ly / self.area) ** (0.7 * self.area / (self.lx * self.ly))
        nd = self.dm / math.hypot(self.lx, self.ly)
        return na * nb * nc * nd

    @property
    def lm(self):
        """Longitud efectiva LM para la tension de malla [m]."""
        if self.n_varillas > 0 and self.varillas_perimetro:
            return self.lc + (1.55 + 1.22 * self.l_varilla / math.hypot(self.lx, self.ly)) * self.lr_total
        return self.lc + self.lr_total

    @property
    def ls(self):
        """Longitud efectiva Ls para la tension de paso [m]."""
        return 0.75 * self.lc + 0.85 * self.lr_total

    # ---- factores geometricos -----------------------------------------
    @property
    def ki(self):
        """Factor de correccion de irregularidad Ki = 0.644 + 0.148 n."""
        return 0.644 + 0.148 * self.n

    @property
    def kii(self):
        """Kii = 1 con varillas en esquinas/perimetro; si no, 1/(2n)^(2/n)."""
        if self.n_varillas > 0 and self.varillas_perimetro:
            return 1.0
        n = self.n
        return 1.0 / (2.0 * n) ** (2.0 / n)

    @property
    def kh(self):
        """Kh = sqrt(1 + h/h0), h0 = 1 m."""
        return math.sqrt(1.0 + self.h / 1.0)

    @property
    def km(self):
        """Factor geometrico para la tension de malla."""
        D, h, d, n = self.d_sep, self.h, self.d, self.n
        termino1 = math.log(D**2 / (16.0 * h * d) + (D + 2.0 * h) ** 2 / (8.0 * D * d) - h / (4.0 * d))
        termino2 = (self.kii / self.kh) * math.log(8.0 / (math.pi * (2.0 * n - 1.0)))
        return (termino1 + termino2) / (2.0 * math.pi)

    @property
    def ks(self):
        """Factor geometrico para la tension de paso (h entre 0.25 y 2.5 m)."""
        D, h, n = self.d_sep, self.h, self.n
        return (1.0 / math.pi) * (1.0 / (2.0 * h) + 1.0 / (D + h) + (1.0 / D) * (1.0 - 0.5 ** (n - 2.0)))

    # ---- resistencia de la malla --------------------------------------
    def rg_sverak(self, rho):
        """Resistencia de malla, ecuacion de Sverak [ohm]."""
        A, h, lt = self.area, self.h, self.lt
        return rho * (1.0 / lt + (1.0 / math.sqrt(20.0 * A)) * (1.0 + 1.0 / (1.0 + h * math.sqrt(20.0 / A))))

    def _k1k2(self):
        """Coeficientes de Schwarz, interpolados segun h/sqrt(A) entre 0, 1/10 y 1/6."""
        x = self.lx / self.ly  # relacion de lados Lx/Ly
        t = self.h / math.sqrt(self.area)
        puntos = [
            (0.0, -0.04 * x + 1.41, 0.15 * x + 5.50),
            (0.1, -0.05 * x + 1.20, 0.10 * x + 4.68),
            (1.0 / 6.0, -0.05 * x + 1.13, 0.10 * x + 4.40),
        ]
        if t <= puntos[0][0]:
            return puntos[0][1], puntos[0][2]
        if t >= puntos[-1][0]:
            return puntos[-1][1], puntos[-1][2]
        for (t0, a0, b0), (t1, a1, b1) in zip(puntos, puntos[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                return a0 + f * (a1 - a0), b0 + f * (b1 - b0)

    def rg_schwarz(self, rho):
        """Resistencia de malla con varillas, ecuaciones de Schwarz [ohm].

        Comprobacion cruzada de Sverak. Los coeficientes k1, k2 se publican para
        h = 0, h = sqrt(A)/10 y h = sqrt(A)/6; aqui se interpolan linealmente.
        """
        A = self.area
        r_cond = self.d / 2.0
        a_eq = math.sqrt(r_cond * 2.0 * self.h)  # a' = sqrt(a * 2h) conductor enterrado
        k1, k2 = self._k1k2()
        lc = self.lc
        r1 = rho / (math.pi * lc) * (math.log(2.0 * lc / a_eq) + k1 * lc / math.sqrt(A) - k2)
        if self.n_varillas == 0:
            return r1
        nr, lr = self.n_varillas, self.l_varilla
        b = self.d_varilla
        r2 = rho / (2.0 * math.pi * nr * lr) * (
            math.log(4.0 * lr / b) - 1.0 + 2.0 * k1 * lr / math.sqrt(A) * (math.sqrt(nr) - 1.0) ** 2
        )
        rm = rho / (math.pi * lc) * (math.log(2.0 * lc / lr) + k1 * lc / math.sqrt(A) - k2 + 1.0)
        return (r1 * r2 - rm**2) / (r1 + r2 - 2.0 * rm)

    # ---- tensiones ----------------------------------------------------
    def tension_malla(self, rho, ig):
        """Tension de malla Em = rho Km Ki IG / LM [V]."""
        return rho * self.km * self.ki * ig / self.lm

    def tension_paso(self, rho, ig):
        """Tension de paso Es = rho Ks Ki IG / Ls [V]."""
        return rho * self.ks * self.ki * ig / self.ls

    def advertencias(self):
        """Limites de validez de las ecuaciones de Km/Ks y avisos geometricos."""
        av = []
        if not (0.25 <= self.h <= 2.5):
            av.append(f"La profundidad h = {self.h:g} m esta fuera del rango 0.25-2.5 m de validez de Km/Ks.")
        if self.d_sep <= 2.5:
            av.append(f"El espaciamiento D = {self.d_sep:g} m es menor o igual que 2.5 m, fuera del rango de validez de Km/Ks.")
        if self.d >= 0.25 * self.d_sep:
            av.append("El diametro del conductor excede 0.25 D: fuera del rango de validez de Km.")
        if self.lx > 0 and self.ly > 0 and max(self.lx, self.ly) / min(self.lx, self.ly) > 3:
            av.append("Relacion de lados mayor que 3: Rg (Sverak) y los factores geometricos pierden precision.")
        return av
