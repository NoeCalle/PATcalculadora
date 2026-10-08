"""Uso: python -m tierra archivo.json   (imprime la memoria de calculo)"""

import json
import sys

from . import diseno


def main():
    if len(sys.argv) != 2:
        print("Uso: python -m tierra archivo.json")
        return 2
    with open(sys.argv[1], encoding="utf-8") as fh:
        datos = json.load(fh)
    r = diseno.evaluar(datos)
    print(diseno.memoria_markdown(r))
    return 0 if r["cumple"] else 1


if __name__ == "__main__":
    sys.exit(main())
