"""Pruebas del modelo de potencial superficial.

La validacion externa decisiva esta en test_validacion_externa.py: la Rg que
entrega este modelo se compara con la que publica CYMGRD para los ejemplos del
Anexo B de IEEE 80.
"""

import math

import pytest

from tierra import potencial as pot
from tierra.malla import Malla

RHO, IG = 150.0, 2000.0


@pytest.fixture(scope="module")
def modelo_g2():
    """G2 del caso del manual: 30 x 40 m, trama de 2.5 m, 4 varillas de 3 m."""
    m = Malla.rectangular(30, 40, 17, 13, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)
    return pot.modelo_de_malla(m, RHO, 2405.0, x0=-5.0, y0=-5.0), m


@pytest.fixture(scope="module")
def modelo_g0():
    m = Malla.rectangular(20, 30, 4, 3, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)
    return pot.modelo_de_malla(m, RHO, 1855.0), m


# ---------------- coherencia fisica del sistema resuelto ----------------
def test_la_corriente_se_conserva(modelo_g2):
    mod, _ = modelo_g2
    assert sum(mod.corrientes) == pytest.approx(2405.0, rel=1e-9)


def test_los_conductores_quedan_equipotenciales(modelo_g2):
    """La condicion impuesta: todos los subsegmentos al mismo potencial."""
    mod, _ = modelo_g2
    pots = [mod.potencial(*s.centro) for s in mod.subsegmentos]
    assert max(pots) - min(pots) < 1e-6 * mod.gpr
    assert mod.gpr == pytest.approx(pots[0], rel=1e-9)


def test_rg_coherente_con_gpr(modelo_g2):
    mod, _ = modelo_g2
    assert mod.rg == pytest.approx(mod.gpr / 2405.0)


def test_el_potencial_decae_con_la_distancia(modelo_g0):
    mod, _ = modelo_g0
    v = [mod.potencial(10.0, y) for y in (-5.0, -20.0, -100.0, -500.0, -2000.0)]
    assert all(v[i] > v[i + 1] > 0 for i in range(len(v) - 1))
    assert v[-1] < 0.02 * mod.gpr  # a 2 km queda por debajo del 2 % del GPR


def test_el_potencial_es_maximo_sobre_la_malla(modelo_g0):
    mod, m = modelo_g0
    dentro = mod.potencial(10.0, 15.0)
    fuera = mod.potencial(10.0, -10.0)
    assert dentro > fuera
    assert dentro < mod.gpr  # la superficie nunca supera el potencial del cobre


# ---------------- coherencia con el metodo simplificado ----------------
def test_toque_en_esquina_proximo_a_em(modelo_g0):
    """El modelo y Em de IEEE 80 describen la misma malla de esquina."""
    mod, m = modelo_g0
    dx, dy = m.lx / (m.ny_cond - 1), m.ly / (m.nx_cond - 1)
    e_esquina = mod.toque(dx * 0.5, dy * 0.5)
    em = m.tension_malla(RHO, 1855.0)
    assert e_esquina == pytest.approx(em, rel=0.15)


def test_el_toque_crece_hacia_el_borde_y_fuera(modelo_g0):
    """Se comparan centros de malla: (5,15) interior, (5,5) de esquina, y un
    punto exterior. Sobre un conductor el toque es minimo, asi que los puntos de
    comparacion no deben caer encima de uno."""
    mod, _ = modelo_g0
    interior = mod.toque(5.0, 15.0)
    esquina = mod.toque(5.0, 5.0)
    fuera = mod.toque(5.0, -3.0)
    assert interior < esquina < fuera


def test_sobre_un_conductor_el_toque_es_menor_que_en_el_centro_de_la_malla(modelo_g0):
    mod, _ = modelo_g0
    assert mod.toque(5.0, 10.0) < mod.toque(5.0, 15.0)


def test_toque_nunca_negativo_dentro_de_la_malla(modelo_g2):
    """Un toque negativo delataria subdivision insuficiente."""
    mod, m = modelo_g2
    dx, dy = m.lx / (m.ny_cond - 1), m.ly / (m.nx_cond - 1)
    for i in range(m.ny_cond - 1):
        for j in range(m.nx_cond - 1):
            assert mod.toque(-5.0 + dx * (i + 0.5), -5.0 + dy * (j + 0.5)) > 0


# ---------------- convergencia ----------------
def test_convergencia_del_toque_en_el_cerco():
    """Refinar la subdivision debe mover poco el resultado, no oscilar."""
    m = Malla.rectangular(30, 40, 17, 13, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)
    vals = []
    for n_sub in (2, 4):
        mod = pot.modelo_de_malla(m, RHO, 2405.0, x0=-5.0, y0=-5.0, n_sub=n_sub,
                                  max_subsegmentos=4000)
        e, _, _ = mod.toque_maximo((0.5, 0.5), (19.5, 0.5), n=30)
        vals.append(e)
    assert vals[1] == pytest.approx(vals[0], rel=0.05)


# ---------------- geometria ----------------
def test_segmentos_se_parten_en_los_cruces():
    m = Malla.rectangular(30, 40, 17, 13, 0.50, 0.0105)
    segs = pot.segmentos_malla_rectangular(m)
    # 17 conductores de 30 m en 12 tramos + 13 de 40 m en 16 tramos
    assert len(segs) == 17 * 12 + 13 * 16
    assert sum(s.longitud for s in segs) == pytest.approx(m.lc)
    assert all(s.longitud == pytest.approx(2.5) for s in segs)


def test_las_varillas_entran_en_la_longitud():
    m = Malla.rectangular(20, 30, 4, 3, 0.50, 0.0105, n_varillas=4, l_varilla=3.0)
    segs = pot.segmentos_malla_rectangular(m)
    assert sum(s.longitud for s in segs) == pytest.approx(m.lt)


def test_posiciones_perimetro():
    esq = pot.posiciones_perimetro(0, 0, 10, 20, 4)
    assert esq == [(0, 0), (10, 0), (10, 20), (0, 20)]
    muchas = pot.posiciones_perimetro(0, 0, 10, 20, 12)
    assert len(muchas) == 12
    assert len(set(muchas)) == 12  # ninguna repetida: evita un sistema singular
    for (x, y) in muchas:
        en_borde = (math.isclose(x, 0) or math.isclose(x, 10)
                    or math.isclose(y, 0) or math.isclose(y, 20))
        assert en_borde


def test_varillas_repartidas_no_dan_sistema_singular():
    m = Malla.rectangular(43.75, 65.25, 13, 9, 0.80, 0.0124, n_varillas=30, l_varilla=3.0)
    mod = pot.modelo_de_malla(m, 75.0, 10676.0)
    assert mod.rg > 0


def test_desplazamiento_del_origen_no_cambia_la_resistencia():
    m = Malla.rectangular(20, 30, 4, 3, 0.50, 0.0105)
    a = pot.modelo_de_malla(m, RHO, IG)
    b = pot.modelo_de_malla(m, RHO, IG, x0=-100.0, y0=50.0)
    assert a.rg == pytest.approx(b.rg, rel=1e-9)
    assert a.toque(1.0, 1.0) == pytest.approx(b.toque(-99.0, 51.0), rel=1e-9)


# ---------------- paso y perfiles ----------------
def test_paso_es_simetrico(modelo_g0):
    mod, _ = modelo_g0
    assert mod.paso((5, 5), (6, 5)) == pytest.approx(mod.paso((6, 5), (5, 5)))


def test_paso_nulo_entre_el_mismo_punto(modelo_g0):
    mod, _ = modelo_g0
    assert mod.paso((5, 5), (5, 5)) == pytest.approx(0.0, abs=1e-9)


def test_perfil_devuelve_los_extremos(modelo_g0):
    mod, _ = modelo_g0
    p = mod.perfil((0, 0), (10, 0), n=10)
    assert len(p) == 11
    assert p[0]["x"] == 0 and p[-1]["x"] == 10
    assert all(abs(q["toque"] - (mod.gpr - q["v"])) < 1e-9 for q in p)


def test_paso_maximo_exige_linea_mas_larga_que_la_separacion(modelo_g0):
    mod, _ = modelo_g0
    with pytest.raises(ValueError):
        mod.paso_maximo((0, 0), (0, 0.5), separacion=1.0)


# ---------------- metal-metal y validaciones ----------------
@pytest.mark.parametrize("ts, peso, esperado", [(0.5, 70, 222.0), (0.7, 50, 138.6), (1.0, 70, 157.0)])
def test_tolerable_metal_metal(ts, peso, esperado):
    assert pot.tolerable_metal_metal(ts, peso) == pytest.approx(esperado, abs=0.1)


def test_metal_metal_menor_que_toque_ordinario():
    from tierra import tolerables
    _, _, toque = tolerables.tensiones_tolerables(150, 0.7, 50, 3000, 0.10)
    assert pot.tolerable_metal_metal(0.7, 50) < toque


@pytest.mark.parametrize("kwargs", [
    {"rho": 0.0}, {"rho": -10.0}, {"ig": 0.0}, {"ig": -5.0},
])
def test_entradas_invalidas(kwargs):
    m = Malla.rectangular(20, 30, 4, 3, 0.50, 0.0105)
    base = {"rho": RHO, "ig": IG}
    base.update(kwargs)
    with pytest.raises(ValueError):
        pot.modelo_de_malla(m, base["rho"], base["ig"])


def test_malla_no_rectangular_avisa():
    from tierra.malla import Malla as M
    m = M(area=100, perimetro=40, lc=100, lx=10, ly=10, dm=14.1, d_sep=5, h=0.5, d=0.01)
    with pytest.raises(ValueError, match="rectangular"):
        pot.segmentos_malla_rectangular(m)


def test_peso_invalido_metal_metal():
    with pytest.raises(ValueError):
        pot.tolerable_metal_metal(0.5, 60)
    with pytest.raises(ValueError):
        pot.tolerable_metal_metal(0.0, 70)


# ---------------- escala adoptada (PerfilEscalado) ----------------
# El defecto que estas pruebas impiden: expresar el potencial de superficie en la
# escala del modelo y la tension de toque en la escala de Sverak, en la misma
# tabla. La suma deja de ser el GPR y el toque pierde significado fisico.

def test_la_suma_de_potencial_y_toque_es_el_gpr_adoptado(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(4856.7)
    for p in [(0.5, 0.5), (10.0, -0.5), (10.0, -7.0), (5.0, 5.0), (-4.0, 20.0)]:
        assert esc.potencial(*p) + esc.toque(*p) == pytest.approx(esc.gpr, rel=1e-12)


def test_el_perfil_escalado_tambien_cumple_la_suma(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(4856.7)
    for q in esc.perfil((10.0, 0.5), (10.0, -15.0), n=20):
        assert q["v"] + q["toque"] == pytest.approx(esc.gpr, rel=1e-12)


def test_escalar_al_propio_gpr_no_cambia_nada(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(mod.gpr)
    assert esc.factor == pytest.approx(1.0)
    assert esc.toque(0.5, 0.5) == pytest.approx(mod.toque(0.5, 0.5))
    assert esc.paso((10, -7), (10, -8)) == pytest.approx(mod.paso((10, -7), (10, -8)))


def test_todas_las_magnitudes_escalan_con_el_mismo_factor(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(2.0 * mod.gpr)
    assert esc.factor == pytest.approx(2.0)
    assert esc.potencial(10.0, -3.0) == pytest.approx(2.0 * mod.potencial(10.0, -3.0))
    assert esc.paso((10, -7), (10, -8)) == pytest.approx(2.0 * mod.paso((10, -7), (10, -8)))
    e_esc, _, _ = esc.paso_maximo((10.0, 0.5), (10.0, -20.0), n=40)
    e_mod, _, _ = mod.paso_maximo((10.0, 0.5), (10.0, -20.0), n=40)
    assert e_esc == pytest.approx(2.0 * e_mod)


def test_la_rg_implicita_corresponde_al_gpr_adoptado(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(2404.3 * 2.02)
    assert esc.rg == pytest.approx(2404.3 * 2.02 / mod.ig)


def test_el_toque_escalado_nunca_supera_el_gpr(modelo_g2):
    mod, _ = modelo_g2
    esc = mod.en_escala(4856.7)
    for p in [(0.5, 0.5), (10.0, -30.0), (10.0, -200.0)]:
        assert 0.0 < esc.toque(*p) <= esc.gpr


def test_gpr_adoptado_invalido(modelo_g2):
    mod, _ = modelo_g2
    for malo in (0.0, -100.0):
        with pytest.raises(ValueError):
            mod.en_escala(malo)
