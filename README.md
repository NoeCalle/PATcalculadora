# Calculadora de puesta a tierra de subestaciones (IEEE Std 80)

Herramienta de apoyo del libro sobre mallas de puesta a tierra. Sirve para dos cosas:

1. **Verificar los cálculos del libro**: cada ecuación está implementada en un módulo pequeño y probado con valores manuales y con tablas publicadas.
2. **Que el lector diseñe su propia malla** con una interfaz visual, sin instalar nada.

## Opción A — Usar la calculadora (sin instalar nada)

1. Abre `docs/index.html` con doble clic (se abre en tu navegador). La primera vez necesita internet para cargar el motor de cálculo.
2. Cambia los datos de la columna izquierda y pulsa **Calcular**.
3. Lee el veredicto (CUMPLE / NO CUMPLE), las tres verificaciones y la memoria de cálculo paso a paso.
4. Botones útiles: **Probar más conductores** (barrido), **Descargar memoria (.md)**, **Imprimir / guardar PDF**, **Guardar datos** y **Abrir datos** para retomar un diseño.

Si publicas el repositorio en GitHub, activa **Settings → Pages → Branch: main, carpeta /docs** y la calculadora quedará disponible en una dirección web para tus lectores.

## Opción B — Usar el motor en Python (para verificar el libro)

Requiere Python 3.9 o superior. No tiene dependencias externas. Una sola vez, desde la carpeta del repositorio:

```
pip install -e .
```

Luego:

```
python -m tierra ejemplos/ejemplo_cumple.json
```

Imprime la memoria de cálculo. Los archivos de `ejemplos/` muestran el formato de entrada (suelo uniforme, suelo con mediciones Wenner, diseño que cumple y que no cumple).

Uso desde Python:

```python
from tierra import evaluar
resultado = evaluar(datos)          # datos: diccionario como en ejemplos/*.json
resultado["e_malla"], resultado["e_contacto_tol"], resultado["cumple"]
```

## Pruebas

```
pip install -e ".[dev]"
python -m pytest
```

## Qué calcula

| Módulo | Contenido |
|---|---|
| `suelo.py` | Resistividad aparente Wenner, modelo de dos capas (Sunde) y ajuste a mediciones |
| `falla.py` | Constante de tiempo DC, factor de decremento Df, corriente de malla IG, falla monofásica |
| `conductor.py` | Sección mínima del conductor (Onderdonk) según material y tipo de unión |
| `materiales.py` | Constantes de 13 materiales (cobre, aluminio, aceros recubiertos, etc.) |
| `tolerables.py` | Factor Cs y tensiones tolerables de paso y contacto (50 y 70 kg) |
| `malla.py` | Rg (Sverak y Schwarz), n, Ki, Kii, Kh, Km, Ks, LM, Ls, Em, Es y avisos de validez |
| `diseno.py` | Flujo completo, verificaciones, barrido de conductores y memoria de cálculo |

## Alcance y límites (léelo antes de citar resultados)

- **El factor de división de corriente Sf es un dato de entrada.** No se calcula a partir de las líneas y cables de guarda (IEEE 80, capítulo 15); usar 1.0 es conservador.
- Mallas **rectangulares**. El espaciamiento D es el promedio de ambas direcciones. Las formas en L o irregulares no están implementadas aún (la clase `Malla` ya admite los parámetros generales).
- Suelo: el diseño usa una resistividad equivalente (valor dado o promedio de las mediciones). El modelo de dos capas es **informativo**; su ajuste no siempre es único.
- Las ecuaciones de Km y Ks solo son válidas con 0.25 ≤ h ≤ 2.5 m, D > 2.5 m y d < 0.25 D. La calculadora avisa cuando se salen del rango.
- Los coeficientes k1 y k2 de Schwarz se interpolan entre las profundidades publicadas; úsalo como comprobación cruzada de Sverak.
- Las constantes de `materiales.py` y las ecuaciones deben contrastarse con la edición de IEEE 80 que cites en el libro (la referencia es IEEE Std 80-2013). Cualquier corrección se hace en un solo archivo.
- La tensión de paso **no** disminuye siempre al densificar la malla: tiene un mínimo. Es un comportamiento de las ecuaciones de la norma, no un error.

## Estructura

```
src/tierra/     motor de cálculo (Python puro)
tests/          pruebas
ejemplos/       datos de entrada de ejemplo
web/            plantilla de la interfaz
docs/index.html calculadora web de un solo archivo (generada)
build_web.py    regenera docs/index.html si cambias el código
```

Si modificas algo en `src/tierra/`, ejecuta `python build_web.py` para actualizar la página web.
