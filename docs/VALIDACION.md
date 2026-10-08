# Validación de la calculadora

Este documento registra contra qué fuentes externas se comparó el motor de cálculo, qué coincide y qué sigue sin validar. Las comprobaciones están automatizadas en `tests/test_validacion_externa.py`, de modo que cualquier cambio futuro del código que rompa una de ellas se detecta al correr las pruebas.

Distinción importante:

- `tests/test_calculos.py` y `tests/test_diseno.py` comprueban el código contra cálculos manuales propios. Detectan errores de programación, pero **no** errores de transcripción de una ecuación de la norma.
- `tests/test_validacion_externa.py` compara contra números que **otra persona** publicó. Es la única prueba capaz de detectar una ecuación mal transcrita.

## Caso A — Malla rectangular con varillas (validación completa)

Subestación de parque eólico de 110 kV. Fuente: [Wind farm BoP, *Substation Earthing Design per IEEE 80 — Step by Step*](https://www.windfarmbop.com/substation-earthing-design-per-ieee-80-step-by-step/).

Es el caso externo más completo encontrado: publica todos los valores intermedios, no solo el resultado final.

**Datos:** ρ = 75 Ω·m · ρs = 4000 Ω·m · hs = 0,2 m · ts = 0,5 s · 70 kg · malla 43,75 × 65,25 m · Lc = 1156 m · D = 5,45 m · h = 0,8 m · d = 0,0124 m · 30 varillas de 3 m en el perímetro · IG = 10 676 A.

| Magnitud | Publicado | Calculador | Diferencia |
|---|---:|---:|---:|
| Lc | 1156 m | 1156,0 m | 0 % |
| Área | 2855 m² | 2854,7 m² | 0,01 % |
| D | 5,45 m | 5,453 m | 0,06 % |
| n | ~10,7 | 10,711 | — |
| Ki | ~2,23 | 2,229 | 0,04 % |
| Km | ~0,64 | 0,640 | 0 % |
| Ks | ~0,308 | 0,3081 | 0,03 % |
| LM | ~1300 m | 1299,7 m | 0,02 % |
| Ls | 943,5 m | 943,5 m | 0 % |
| Rg | 0,668 Ω | 0,6683 Ω | 0,04 % |
| GPR | ~7134 V | 7134,3 V | 0 % |
| Cs | 0,82 | 0,8198 | 0,02 % |
| E paso tolerable | 4590 V | 4590,4 V | 0,01 % |
| E contacto tolerable | 1314 V | 1314,1 V | 0,01 % |
| **Em (tensión de malla)** | **~880 V** | **878,9 V** | **0,13 %** |
| **Es (tensión de paso)** | **~583 V** | **582,8 V** | **0,03 %** |

Las 16 magnitudes coinciden dentro del redondeo de la fuente. Esto valida, de forma independiente, la cadena completa: geometría, n, Ki, Km, Ks, LM, Ls, Rg de Sverak, Cs, tensiones tolerables y las dos tensiones calculadas.

Los conductores se modelaron como 13 de 43,75 m más 9 de 65,25 m, que reproduce Lc = 1156 m exacto y D = 5,45 m.

## Caso B — Malla cuadrada 70 × 70 m del Anexo B de IEEE 80 (validación parcial)

Fuente secundaria: *CYMGRD IEEE Validation Cases*, que tabula lado a lado los resultados de IEEE 80 y los del software CYMGRD para los ejemplos 1 a 4 de la norma.

**Datos:** ρ = 400 Ω·m · ρs = 2500 Ω·m · hs = 0,102 m · ts = 0,5 s · 70 kg · 70 × 70 m con 100 retículas (11 × 11 conductores, D = 7 m) · h = 0,5 m · d = 0,01 m · IG = 1908 A (Sf = 0,6 sobre 3180 A).

| Magnitud | IEEE 80 | CYMGRD | Calculador |
|---|---:|---:|---:|
| Rg (sin varillas) | 2,78 Ω | 2,675 Ω | 2,7757 Ω |
| GPR | 5304 V | 5105,6 V | 5296,0 V |
| E paso tolerable | 2686,00 V | 2696,10 V | 2696,10 V |
| E contacto tolerable | 838,20 V | 840,55 V | 840,55 V |
| Rg (con varillas de 7,5 m) | 2,75 Ω | 2,50 Ω | 2,7526 Ω (20 varillas) |

Las dos diferencias aparentes tienen explicación comprobada:

- **Tensiones tolerables.** El calculador coincide al céntimo con CYMGRD. Los valores de IEEE 80 se reproducen exactamente (2686,58 V y 838,17 V) al arrastrar Cs redondeado a 0,74 en lugar del valor exacto 0,74286. Es redondeo de la norma, no diferencia de fórmula.
- **GPR.** 5304 V = 1908 A × 2,78 Ω, es decir, la norma usa su propio Rg ya redondeado. Con Rg sin redondear sale 5296 V.
- **Rg de CYMGRD.** Es menor porque ese software resuelve el problema numéricamente en lugar de aplicar la fórmula cerrada de Sverak. La diferencia (≈4 %) es del método, no un error.

El número de varillas del ejemplo 2 no está publicado. La cifra de 2,75 Ω acota el número a unas 20-25 varillas; con 38 o 40 el calculador daría 2,73-2,74 Ω.

## Qué sigue sin validar externamente

1. **El factor Kii** (`1/(2n)^(2/n)`), que solo actúa en mallas **sin** varillas. El único caso externo completo (A) lleva varillas perimetrales, donde Kii = 1 por definición. Para el caso B el motor da Kii = 0,5701, Km = 0,8896, Em = 1001,6 V y Es = 609,7 V, pero no se encontró fuente publicada con esos intermedios. Están registrados en una prueba para que cualquier cambio futuro sea deliberado, no como validación.
2. **Las constantes de materiales** de `materiales.py` (αr, K0, Tm, ρr, TCAP de 13 materiales) y la sección mínima del conductor. Solo se comprobó la coherencia interna y el valor clásico de 7,00 kcmil/kA para cobre blando a 1 s.
3. **El factor de decremento Df**, comparado con una tabla publicada de la norma pero no con un ejemplo resuelto completo.
4. **Las ecuaciones de Schwarz** para Rg. Se usan solo como comprobación cruzada de Sverak; sus coeficientes k1 y k2 se interpolan entre las profundidades publicadas.
5. **El modelo de suelo de dos capas**, validado únicamente contra sus propios límites analíticos (a ≪ h → ρ1, a ≫ h → ρ2) y recuperando parámetros de curvas sintéticas.

## Cómo cerrar los puntos pendientes

Lo más valioso sería reproducir los ejemplos 1 y 2 del Anexo B de IEEE Std 80-2013 con sus valores intermedios (n, Kii, Km, Ks, LM, Ls, Em, Es). Con la norma a la vista, basta añadirlos a `tests/test_validacion_externa.py` siguiendo el formato del caso A.

## Alcance de esta validación

La coincidencia del caso A es evidencia fuerte de que las ecuaciones principales están bien transcritas, pero una sola fuente secundaria no equivale a la certificación de un software comercial. Para diseños reales, los resultados deben revisarse contra otro software o cálculo manual independiente.
