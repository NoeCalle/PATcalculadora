"""Validacion contra ejemplos resueltos PUBLICADOS por terceros.

A diferencia de test_calculos.py (que comprueba el codigo contra calculos manuales
propios), este archivo compara el motor contra numeros que otra persona publico.
Es la unica prueba que puede detectar un error de transcripcion de una ecuacion.

Fuentes y su trazabilidad estan en docs/VALIDACION.md.
"""

import pytest

from tierra import tolerables
from tierra.malla import Malla

# =====================================================================
# CASO A - Subestacion de parque eolico 110 kV, malla rectangular CON varillas
# Fuente: Wind farm BoP, "Substation Earthing Design per IEEE 80 - Step by Step"
#   https://www.windfarmbop.com/substation-earthing-design-per-ieee-80-step-by-step/
# Es el caso mas completo encontrado: publica n, Ki, Km, Ks, LM, Ls, Rg, Em y Es.
# Datos: rho = 75, rho_s = 4000, hs = 0.2, ts = 0.5 s, 70 kg,
#        malla 43.75 x 65.25 m, Lc = 1156 m, D = 5.45 m, h = 0.8 m, d = 0.0124 m,
#        30 varillas de 3 m en el perimetro, IG = 10676 A.
# nx = 13 conductores de 43.75 m y ny = 9 de 65.25 m reproducen Lc = 1156 m exacto.
# =====================================================================

RHO_A, IG_A = 75.0, 10676.0


@pytest.fixture
def malla_a():
    return Malla.rectangular(43.75, 65.25, 13, 9, h=0.8, d=0.0124,
                             n_varillas=30, l_varilla=3.0)


def test_a_geometria(malla_a):
    assert malla_a.lc == pytest.approx(1156.0)
    assert malla_a.area == pytest.approx(2855.0, abs=1.0)
    assert malla_a.d_sep == pytest.approx(5.45, abs=0.01)


def test_a_factores_geometricos(malla_a):
    assert malla_a.n == pytest.approx(10.7, abs=0.05)
    assert malla_a.ki == pytest.approx(2.23, abs=0.01)
    assert malla_a.km == pytest.approx(0.64, abs=0.005)
    assert malla_a.ks == pytest.approx(0.308, abs=0.001)


def test_a_longitudes_efectivas(malla_a):
    assert malla_a.lm == pytest.approx(1300.0, abs=1.0)
    assert malla_a.ls == pytest.approx(943.5, abs=0.1)


def test_a_resistencia_y_gpr(malla_a):
    assert malla_a.rg_sverak(RHO_A) == pytest.approx(0.668, abs=0.001)
    assert IG_A * malla_a.rg_sverak(RHO_A) == pytest.approx(7134.0, abs=5.0)


def test_a_tensiones(malla_a):
    assert malla_a.tension_malla(RHO_A, IG_A) == pytest.approx(880.0, abs=2.0)
    assert malla_a.tension_paso(RHO_A, IG_A) == pytest.approx(583.0, abs=1.0)


def test_a_tolerables():
    cs, e_paso, e_contacto = tolerables.tensiones_tolerables(RHO_A, 0.5, 70, 4000.0, 0.2)
    assert cs == pytest.approx(0.82, abs=0.001)
    assert e_paso == pytest.approx(4590.0, abs=1.0)
    assert e_contacto == pytest.approx(1314.0, abs=1.0)


def test_a_sin_advertencias(malla_a):
    assert malla_a.advertencias() == []


# =====================================================================
# CASO B - Ejemplo del Anexo B de IEEE Std 80: malla cuadrada 70 x 70 m
# Fuente secundaria: "CYMGRD IEEE Validation Cases", que tabula los resultados
#   de IEEE 80 y los de CYMGRD para los ejemplos 1 a 4 de la norma.
# Datos: rho = 400, rho_s = 2500, hs = 0.102, ts = 0.5 s, 70 kg,
#        70 x 70 m con 100 retículas (11 x 11 conductores, D = 7 m),
#        h = 0.5 m, d = 0.01 m, IG = 1908 A (Sf = 0.6 sobre 3180 A).
# Valores publicados: Rg = 2.78 ohm (IEEE), GPR = 5304 V,
#        E_contacto,tol = 838.20 V (IEEE) / 840.55 V (CYMGRD),
#        E_paso,tol = 2686.00 V (IEEE) / 2696.10 V (CYMGRD).
# =====================================================================

RHO_B, IG_B = 400.0, 1908.0


@pytest.fixture
def malla_b():
    return Malla.rectangular(70.0, 70.0, 11, 11, h=0.5, d=0.010)


def test_b_resistencia(malla_b):
    # IEEE 80 publica 2.78 ohm (2 decimales).
    assert malla_b.rg_sverak(RHO_B) == pytest.approx(2.78, abs=0.005)


def test_b_gpr(malla_b):
    # 5304 V proviene de 1908 A x 2.78 ohm (Rg ya redondeado por la norma).
    assert IG_B * 2.78 == pytest.approx(5304.0, abs=1.0)
    assert IG_B * malla_b.rg_sverak(RHO_B) == pytest.approx(5304.0, rel=0.002)


def test_b_tolerables_coinciden_con_cymgrd():
    """Con Cs sin redondear se reproducen los valores de CYMGRD al centesimo."""
    cs, e_paso, e_contacto = tolerables.tensiones_tolerables(RHO_B, 0.5, 70, 2500.0, 0.102)
    assert cs == pytest.approx(0.74286, abs=1e-5)
    assert e_paso == pytest.approx(2696.10, abs=0.01)
    assert e_contacto == pytest.approx(840.55, abs=0.01)


def test_b_tolerables_con_cs_redondeado_dan_los_de_ieee():
    """IEEE 80 arrastra Cs redondeado a 0.74; eso explica 2686.00 V y 838.20 V.

    Se comprueba inyectando Cs = 0.74 como rho_s equivalente, para confirmar que
    la discrepancia es de redondeo y no de formula.
    """
    k = 0.157
    e_paso = (1000.0 + 6.0 * 0.74 * 2500.0) * k / 0.5**0.5
    e_contacto = (1000.0 + 1.5 * 0.74 * 2500.0) * k / 0.5**0.5
    assert e_paso == pytest.approx(2686.00, abs=0.6)
    assert e_contacto == pytest.approx(838.20, abs=0.1)


# =====================================================================
# CASO C - Mismo ejemplo con varillas de 7.5 m en el perimetro (ejemplo 2)
# Rg publicado por IEEE 80: 2.75 ohm. El documento no indica el numero de
# varillas. El motor da 2.7526 ohm con 20 varillas y 2.7485 con 24, que redondean
# a 2.75; con 38 o 40 varillas daria 2.73-2.74, asi que la cifra publicada acota
# el numero de varillas a unas 20-25. Validacion parcial: confirma el orden de
# magnitud y la tendencia, no fija el numero de varillas del ejemplo.
# =====================================================================


@pytest.mark.parametrize("n_varillas", [20, 24])
def test_c_resistencia_con_varillas(n_varillas):
    m = Malla.rectangular(70.0, 70.0, 11, 11, h=0.5, d=0.010,
                          n_varillas=n_varillas, l_varilla=7.5, d_varilla=0.010)
    assert m.rg_sverak(RHO_B) == pytest.approx(2.75, abs=0.015)
    # Las varillas deben reducir Rg respecto al caso sin varillas.
    assert m.rg_sverak(RHO_B) < Malla.rectangular(70.0, 70.0, 11, 11, 0.5, 0.010).rg_sverak(RHO_B)


# =====================================================================
# PENDIENTE DE VALIDAR (ver docs/VALIDACION.md)
# Kii = 1/(2n)^(2/n), que solo actua en mallas SIN varillas, no se ha podido
# comparar con ninguna fuente publicada: el unico ejemplo externo completo
# (caso A) lleva varillas perimetrales, donde Kii = 1 por definicion.
# Este test deja constancia del valor que produce el motor para el caso B, para
# que cualquier cambio futuro sea deliberado; NO es una validacion externa.
# =====================================================================


def test_b_valores_no_validados_quedan_registrados(malla_b):
    assert malla_b.kii == pytest.approx(0.5701, abs=1e-4)
    assert malla_b.km == pytest.approx(0.8896, abs=1e-4)
    assert malla_b.tension_malla(RHO_B, IG_B) == pytest.approx(1001.6, abs=0.5)
    assert malla_b.tension_paso(RHO_B, IG_B) == pytest.approx(609.7, abs=0.5)


# =====================================================================
# CASO D - El modelo de potencial frente a CYMGRD
# El documento "CYMGRD IEEE Validation Cases" tabula, para los ejemplos 1 a 3
# del Anexo B de IEEE 80, la Rg de la norma (formula cerrada de Sverak) y la que
# obtiene CYMGRD resolviendo el problema numericamente. El modelo de potencial de
# tierra.potencial hace lo segundo, asi que debe acercarse a CYMGRD y no a Sverak.
# Es la validacion externa del modulo nuevo: el unico contraste disponible contra
# un programa comercial de mallas.
# =====================================================================

from tierra import potencial as pot  # noqa: E402


@pytest.mark.parametrize("nombre, malla, rg_cymgrd", [
    ("Ej.1 70x70 sin varillas",
     Malla.rectangular(70, 70, 11, 11, 0.50, 0.010), 2.675),
    ("Ej.2 70x70 + 20 varillas de 7.5 m",
     Malla.rectangular(70, 70, 11, 11, 0.50, 0.010, n_varillas=20, l_varilla=7.5,
                       d_varilla=0.010), 2.500),
    ("Ej.3 63x84 + 38 varillas de 10 m",
     Malla.rectangular(63, 84, 15, 12, 0.50, 0.010, n_varillas=38, l_varilla=10.0,
                       d_varilla=0.010), 2.278),
])
def test_d_rg_del_modelo_coincide_con_cymgrd(nombre, malla, rg_cymgrd):
    mod = pot.modelo_de_malla(malla, 400.0, 1908.0)
    assert mod.rg == pytest.approx(rg_cymgrd, rel=0.03)


def test_d_el_modelo_queda_por_debajo_de_sverak():
    """Patron que CYMGRD tambien muestra: la formula cerrada es conservadora."""
    for malla in (Malla.rectangular(70, 70, 11, 11, 0.50, 0.010),
                  Malla.rectangular(30, 40, 17, 13, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)):
        mod = pot.modelo_de_malla(malla, 400.0, 1908.0)
        assert mod.rg < malla.rg_sverak(400.0)


def test_d_caso_a_tambien_con_el_modelo_de_potencial(malla_a):
    """El caso A publicado da Rg = 0.668 por Sverak; el modelo debe quedar algo
    por debajo, en el mismo margen que muestran los ejemplos de la norma."""
    mod = pot.modelo_de_malla(malla_a, RHO_A, IG_A)
    assert 0.85 * 0.668 < mod.rg < 0.668
