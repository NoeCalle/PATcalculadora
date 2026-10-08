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
| `potencial.py` | Perfil de potencial superficial, toque en cerco y puerta, paso en cualquier punto |
| `diseno.py` | Flujo completo, verificaciones, barrido de conductores y memoria de cálculo |

## Toque en el cerco y en la puerta

El método simplificado de IEEE 80 describe el **interior** de la malla: Em y Es no sirven para el cerco, la puerta ni el suelo exterior, porque esas posiciones necesitan el potencial de la superficie donde la persona apoya los pies.

`potencial.py` lo calcula. Divide la malla en segmentos, resuelve el reparto de corriente de fuga que los mantiene equipotenciales y con esa solución evalúa el potencial de cualquier punto:

```python
from tierra import potencial as pot
from tierra.malla import Malla

m = Malla.rectangular(30, 40, 17, 13, h=0.50, d=0.0105, n_varillas=4, l_varilla=3.0)
mod = pot.modelo_de_malla(m, rho=150, ig=2405, x0=-5, y0=-5)

mod.rg                              # resistencia que entrega el modelo
mod.toque(0.5, 0.5)                 # toque en un punto del cerco
mod.paso((10, -8), (10, -9))        # paso entre dos apoyos
mod.toque_maximo((0.5, 0.5), (19.5, 0.5))   # peor punto de un lado del cerco
mod.perfil((10, 0.5), (10, -15))    # perfil para graficar
```

`ejemplos/caso_libro_cerco.py` es un caso completo resuelto: ocho geometrías, toque en cerco y puerta, perfil hacia el exterior y comprobación térmica de las conexiones.

A diferencia de Sverak, este modelo resuelve el problema numéricamente, así que su Rg se parece a la de un programa comercial. Coincide con CYMGRD dentro del 2 % en los tres ejemplos del Anexo B de IEEE 80.

## Validación

El motor se comparó con un ejemplo resuelto publicado por terceros (subestación de parque eólico de 110 kV, malla rectangular de 43,75 × 65,25 m con 30 varillas). Las **16 magnitudes** coinciden dentro del redondeo de la fuente, incluidas las dos críticas: tensión de malla (878,9 V frente a ~880 V publicados) y tensión de paso (582,8 V frente a ~583 V).

También se comprobó contra los valores tabulados del ejemplo de 70 × 70 m del Anexo B de IEEE 80: Rg = 2,7757 Ω frente a 2,78 Ω de la norma, y las tensiones tolerables coinciden al céntimo con CYMGRD.

Todo está automatizado en `tests/test_validacion_externa.py`. **Lee [docs/VALIDACION.md](docs/VALIDACION.md) antes de citar resultados en un documento**: detalla las fuentes, las diferencias y, sobre todo, lo que todavía **no** está validado (el factor Kii de mallas sin varillas, las constantes de materiales y las ecuaciones de Schwarz).

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

## Licencia

MIT — ver [LICENSE](LICENSE). Puedes usarla, modificarla y redistribuirla, incluso en trabajos comerciales, citando la autoría. Se entrega sin garantía: la responsabilidad de verificar los resultados de un diseño real es de quien los usa.
