"""Genera docs/index.html (un solo archivo) incrustando el codigo de src/tierra.

Uso:  python build_web.py
Despues de cambiar cualquier archivo de src/tierra, vuelve a ejecutarlo.
"""

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
sys.path.insert(0, str(RAIZ / "src"))

from tierra.materiales import MATERIALES  # noqa: E402

fuentes = {p.name: p.read_text(encoding="utf-8") for p in sorted((RAIZ / "src" / "tierra").glob("*.py"))
           if p.name != "__main__.py"}
materiales = [[m.clave, m.nombre] for m in MATERIALES.values()]

html = (RAIZ / "web" / "plantilla.html").read_text(encoding="utf-8")
# "</" dentro de <script> podria cerrar la etiqueta; se escapa.
js_fuentes = json.dumps(fuentes, ensure_ascii=False).replace("</", "<\\/")
html = html.replace("/*__FUENTES__*/{}", js_fuentes).replace("/*__MATERIALES__*/[]", json.dumps(materiales, ensure_ascii=False))

salida = RAIZ / "docs" / "index.html"
salida.write_text(html, encoding="utf-8")
print(f"Generado {salida} ({salida.stat().st_size / 1024:.0f} kB)")
