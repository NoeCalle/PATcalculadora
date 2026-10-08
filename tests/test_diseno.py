import copy
import json

import pytest

from tierra import api, diseno


@pytest.fixture
def base():
    return copy.deepcopy(diseno.ESQUEMA_EJEMPLO)


def test_ejemplo_por_defecto_cumple(base):
    assert diseno.evaluar(base)["cumple"] is True


def test_flujo_completo_valores_clave(base):
    base["falla"]["sf"] = 1.0
    base["malla"]["varillas"]["cantidad"] = 0
    r = diseno.evaluar(base)
    assert r["df"] == pytest.approx(1.0262, abs=1e-3)
    assert r["ig_a"] == pytest.approx(3263.3, abs=0.5)
    assert r["rg_sverak"] == pytest.approx(2.7757, abs=1e-3)
    assert r["e_contacto_tol"] == pytest.approx(840.5, abs=0.2)
    assert r["a_min_mm2"] == pytest.approx(8.05, abs=0.02)
    assert r["gpr_v"] == pytest.approx(r["ig_a"] * r["rg_ohm"])


def test_cumple_cuando_la_corriente_es_baja(base):
    base["falla"]["i_falla_ka"] = 0.5
    r = diseno.evaluar(base)
    assert r["cumple"] is True
    assert "EL DISENO CUMPLE" in diseno.memoria_markdown(r)


def test_no_cumple_con_corriente_alta(base):
    base["falla"]["i_falla_ka"] = 20.0
    assert diseno.evaluar(base)["cumple"] is False


def test_conductor_subdimensionado(base):
    base["conductor"]["diametro_mm"] = 2.0
    r = diseno.evaluar(base)
    v = next(x for x in r["verificaciones"] if x["nombre"] == "Seccion del conductor")
    assert v["cumple"] is False and r["cumple"] is False


def test_suelo_desde_wenner(base):
    base["suelo"] = {"b": 0, "wenner": [{"a": a, "R": 400 / (6.2832 * a)} for a in (1, 2, 4, 8, 16)]}
    r = diseno.evaluar(base)
    assert r["rho"] == pytest.approx(400, rel=1e-3)
    assert "modelo_dos_capas" in r["extra"]


def test_barrido_encuentra_diseno_o_none(base):
    base["falla"]["i_falla_ka"] = 1.5
    filas, primero = diseno.barrido_conductores(base, 25)
    assert len(filas) > 10
    assert primero is None or any(f["cumple"] and f["n_conductores"] == primero for f in filas)
    ems = [f["em"] for f in filas]
    assert ems == sorted(ems, reverse=True)


@pytest.mark.parametrize("campo, valor", [
    (("falla", "tf"), 0), (("falla", "sf"), 1.5), (("malla", "h"), -1),
    (("descarga", "peso"), 60), (("conductor", "material"), "oro"),
])
def test_validaciones(base, campo, valor):
    base[campo[0]][campo[1]] = valor
    with pytest.raises(ValueError):
        diseno.evaluar(base)


def test_api_json_ok_y_error(base):
    ok = json.loads(api.calcular(json.dumps(base)))
    assert "memoria_md" in ok and "error" not in ok
    base["falla"].pop("tf")
    err = json.loads(api.calcular(json.dumps(base)))
    assert "error" in err and "tf" in err["error"]


def test_api_ejemplo_roundtrip():
    r = json.loads(api.calcular(api.ejemplo()))
    assert r["rho"] == 400.0


def test_api_ajustar_suelo():
    from tierra.suelo import rho_aparente_dos_capas
    import math
    datos = []
    for a in (0.5, 1, 2, 4, 8, 16):
        rho_a = rho_aparente_dos_capas(100, 400, 2.5, a)
        datos.append({"a": a, "R": rho_a / (2 * math.pi * a)})
    r = json.loads(api.ajustar_suelo(json.dumps({"wenner": datos})))
    assert r["error_rms_pct"] < 2.0
