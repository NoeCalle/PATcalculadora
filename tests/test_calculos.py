"""Verificacion de las ecuaciones.

Los valores esperados se obtuvieron de dos fuentes independientes del codigo:
  * valores publicados de la tabla del factor de decremento (IEEE 80, 60 Hz, X/R = 10)
  * calculos manuales paso a paso (mostrados en los comentarios)
"""

import math

import pytest

from tierra import conductor, falla, suelo, tolerables
from tierra.malla import Malla


# ---------------- factor de decremento ----------------
@pytest.mark.parametrize("tf, esperado", [(0.05, 1.232), (0.10, 1.125), (0.20, 1.064),
                                          (0.50, 1.026), (1.00, 1.013)])
def test_factor_decremento_tabla(tf, esperado):
    assert falla.factor_decremento(tf, 10, 60) == pytest.approx(esperado, abs=0.001)


def test_factor_decremento_sin_componente_dc():
    assert falla.factor_decremento(0.5, 0) == 1.0


def test_corriente_malla():
    # 3.18 kA * Df 1.0 * Sf 0.6 * Cp 1.1 = 2098.8 A
    assert falla.corriente_malla(3.18, 0.6, 1.0, 1.1) == pytest.approx(2098.8)


def test_falla_monofasica():
    # Z total = 1+j3 + 1+j3 + 2+j6 = 4+j12 -> |Z| = 12.649; 3I0 = sqrt(3)*23 /12.649 = 3.149 kA
    i, xr = falla.corriente_falla_monofasica(23.0, 1 + 3j, 1 + 3j, 2 + 6j)
    assert i == pytest.approx(3.1495, abs=1e-3)
    assert xr == pytest.approx(3.0)


# ---------------- tensiones tolerables ----------------
def test_cs():
    # 1 - 0.09 (1 - 400/2500) / (2*0.102 + 0.09) = 1 - 0.0756/0.294 = 0.74286
    assert tolerables.factor_cs(400, 2500, 0.102) == pytest.approx(0.74286, abs=1e-5)


def test_tensiones_tolerables_70kg():
    cs, paso, contacto = tolerables.tensiones_tolerables(400, 0.5, 70, 2500, 0.102)
    # contacto = (1000 + 1.5*0.74286*2500)*0.157/sqrt(0.5) = 3785.7*0.22204 = 840.5
    assert contacto == pytest.approx(840.5, abs=0.2)
    # paso = (1000 + 6*0.74286*2500)*0.157/sqrt(0.5) = 12143*0.22204 = 2696.1
    assert paso == pytest.approx(2696.1, abs=0.5)


def test_tensiones_tolerables_50kg_menores_que_70kg():
    _, p50, c50 = tolerables.tensiones_tolerables(400, 0.5, 50)
    _, p70, c70 = tolerables.tensiones_tolerables(400, 0.5, 70)
    assert p50 < p70 and c50 < c70


def test_sin_capa_superficial_usa_rho_del_suelo():
    cs, paso, contacto = tolerables.tensiones_tolerables(100, 1.0, 70)
    assert cs == 1.0
    assert contacto == pytest.approx((1000 + 1.5 * 100) * 0.157)


# ---------------- conductor ----------------
def test_seccion_cobre_blando_fusion():
    # Cobre blando, Tm=1083, Ta=40, 1 kA, 1 s -> 3.548 mm2 (= 7.00 kcmil/kA, valor clasico)
    a = conductor.seccion_minima_mm2(1.0, 1.0, "cobre_blando", 40, "soldadura_exotermica")
    assert a == pytest.approx(3.548, abs=0.01)
    assert a * 1.9735 == pytest.approx(7.00, abs=0.02)


def test_seccion_escala_con_corriente_y_tiempo():
    a1 = conductor.seccion_minima_mm2(1.0, 1.0, "cobre_duro")
    assert conductor.seccion_minima_mm2(2.0, 1.0, "cobre_duro") == pytest.approx(2 * a1)
    assert conductor.seccion_minima_mm2(1.0, 4.0, "cobre_duro") == pytest.approx(2 * a1)


def test_union_mecanica_exige_mas_seccion():
    base = conductor.seccion_minima_mm2(5.0, 0.5, "cobre_duro", 40, "soldadura_exotermica")
    mec = conductor.seccion_minima_mm2(5.0, 0.5, "cobre_duro", 40, "conector_mecanico")
    assert mec > base


# ---------------- suelo ----------------
def test_wenner_simple():
    assert suelo.rho_aparente_wenner(2.0, 10.0) == pytest.approx(2 * math.pi * 2 * 10)


def test_wenner_con_profundidad_tiende_al_simple():
    assert suelo.rho_aparente_wenner(3.0, 10.0, b=0.001) == pytest.approx(
        suelo.rho_aparente_wenner(3.0, 10.0), rel=1e-3)


def test_dos_capas_limites():
    # a << h -> rho1 ; a >> h -> rho2 ; K = 0 -> rho1
    assert suelo.rho_aparente_dos_capas(100, 400, 10, 0.1) == pytest.approx(100, rel=1e-3)
    assert suelo.rho_aparente_dos_capas(100, 400, 1, 500) == pytest.approx(400, rel=0.02)
    assert suelo.rho_aparente_dos_capas(200, 200, 3, 5) == 200


def test_ajuste_dos_capas_recupera_parametros():
    rho1, rho2, h = 120.0, 600.0, 3.0
    datos = [(a, suelo.rho_aparente_dos_capas(rho1, rho2, h, a)) for a in (0.5, 1, 2, 4, 8, 16, 32)]
    r = suelo.ajustar_dos_capas(datos)
    assert r["error_rms_pct"] < 1.0
    assert r["rho1"] == pytest.approx(rho1, rel=0.1)
    assert r["rho2"] == pytest.approx(rho2, rel=0.15)
    assert r["h"] == pytest.approx(h, rel=0.15)


# ---------------- malla 70 x 70 m, 11 x 11 conductores, h = 0.5 m, d = 10 mm, rho = 400 ----------------
@pytest.fixture
def malla70():
    return Malla.rectangular(70, 70, 11, 11, 0.5, 0.010)


def test_geometria(malla70):
    assert malla70.lc == 1540
    assert malla70.d_sep == pytest.approx(7.0)
    assert malla70.n == pytest.approx(11.0)  # na = 2*1540/280 = 11; nb = nc = nd = 1
    assert malla70.ki == pytest.approx(2.272)  # 0.644 + 0.148*11


def test_rg_sverak(malla70):
    # 400 [1/1540 + 1/sqrt(98000) (1 + 1/(1 + 0.5 sqrt(20/4900)))] = 2.7757
    assert malla70.rg_sverak(400) == pytest.approx(2.7757, abs=1e-3)


def test_km_ks(malla70):
    # Km: ln(612.5 + 114.286 - 12.5) = 6.5714 ; Kii = 1/(22)^(2/11) = 0.5701 ; Kh = sqrt(1.5)
    #     (6.5714 + 0.5701/1.2247 * ln(8/(pi*21)))/(2 pi) = 0.8896
    assert malla70.km == pytest.approx(0.8896, abs=1e-3)
    # Ks = 1/pi [1/1 + 1/7.5 + (1/7)(1 - 0.5^9)] = 0.40614
    assert malla70.ks == pytest.approx(0.40614, abs=1e-4)


def test_schwarz_cercano_a_sverak_sin_varillas(malla70):
    sv, sw = malla70.rg_sverak(400), malla70.rg_schwarz(400)
    assert abs(sw - sv) / sv < 0.10


def test_varillas_reducen_resistencia():
    sin = Malla.rectangular(70, 70, 11, 11, 0.5, 0.010)
    con = Malla.rectangular(70, 70, 11, 11, 0.5, 0.010, n_varillas=20, l_varilla=7.5)
    assert con.rg_sverak(400) < sin.rg_sverak(400)
    assert con.rg_schwarz(400) < sin.rg_schwarz(400)


def test_varillas_perimetrales_aumentan_lm():
    con = Malla.rectangular(70, 70, 11, 11, 0.5, 0.010, n_varillas=20, l_varilla=7.5)
    # LM = 1540 + (1.55 + 1.22*7.5/99.0) * 150
    assert con.lm == pytest.approx(1540 + (1.55 + 1.22 * 7.5 / math.hypot(70, 70)) * 150)
    assert con.ls == pytest.approx(0.75 * 1540 + 0.85 * 150)


def test_mas_conductores_reduce_tension_de_malla():
    # Em baja siempre al densificar. Es NO es monotona: con IEEE 80, Ks e Ki crecen mas
    # rapido que Ls al reducirse D, por lo que Es tiene un minimo (aqui cerca de n = 12).
    prev_em = float("inf")
    for n in (6, 9, 12, 16):
        m = Malla.rectangular(70, 70, n, n, 0.5, 0.010)
        em = m.tension_malla(400, 3000)
        assert em < prev_em
        prev_em = em
    es = [Malla.rectangular(70, 70, n, n, 0.5, 0.010).tension_paso(400, 3000) for n in (6, 12, 16)]
    assert es[1] < es[0] and es[1] < es[2]


def test_advertencias_h_fuera_de_rango():
    m = Malla.rectangular(15, 15, 11, 11, 3.0, 0.010)  # D = 1.5 m, h = 3 m
    assert any("profundidad" in a for a in m.advertencias())
    assert any("espaciamiento" in a for a in m.advertencias())


def test_malla_invalida():
    with pytest.raises(ValueError):
        Malla.rectangular(70, 70, 1, 11, 0.5, 0.01)
    with pytest.raises(ValueError):
        Malla.rectangular(70, -1, 5, 5, 0.5, 0.01)
