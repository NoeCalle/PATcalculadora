"""Interfaz JSON-in / JSON-out. La usa la pagina web (Pyodide) y sirve para scripts."""

import json

from . import diseno, suelo


def _responder(fn):
    try:
        return json.dumps(fn(), ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except (KeyError, TypeError) as e:
        return json.dumps({"error": f"Dato faltante o con formato invalido: {e}"}, ensure_ascii=False)


def calcular(json_entrada):
    """Evalua un diseno. Devuelve JSON con resultados + memoria en Markdown."""

    def _f():
        datos = json.loads(json_entrada)
        r = diseno.evaluar(datos)
        r["memoria_md"] = diseno.memoria_markdown(r)
        return r

    return _responder(_f)


def barrido(json_entrada, n_max=30):
    def _f():
        datos = json.loads(json_entrada)
        filas, primero = diseno.barrido_conductores(datos, n_max)
        return {"filas": filas, "primer_n_que_cumple": primero}

    return _responder(_f)


def ajustar_suelo(json_entrada):
    """Entrada: {"b": 0, "wenner": [{"a":..,"R":..}, ...]}"""

    def _f():
        d = json.loads(json_entrada)
        b = float(d.get("b", 0) or 0)
        med = [(float(x["a"]), suelo.rho_aparente_wenner(float(x["a"]), float(x["R"]), b)) for x in d["wenner"]]
        res = suelo.ajustar_dos_capas(med)
        res["promedio"] = suelo.rho_promedio(med)
        return res

    return _responder(_f)


def ejemplo():
    return json.dumps(diseno.ESQUEMA_EJEMPLO, ensure_ascii=False, indent=2)
