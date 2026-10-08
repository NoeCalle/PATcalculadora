"""Constantes de materiales para el dimensionamiento del conductor de la malla.

Fuente de los valores: IEEE Std 80-2013, tabla de constantes de materiales
(alpha_r, K0, Tm, rho_r, TCAP). IMPORTANTE: contrastar cada valor con la
edicion de la norma que se cite en el libro antes de publicar; los valores
estan centralizados aqui para que una correccion se haga en un solo lugar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    clave: str
    nombre: str
    alpha_r: float  # coeficiente termico de resistividad a 20 C [1/C]
    k0: float  # 1/alpha_0 o (1/alpha_r - 20) a 0 C [C]
    tm: float  # temperatura de fusion [C]
    rho_r: float  # resistividad a 20 C [micro-ohm*cm]
    tcap: float  # capacidad termica por unidad de volumen [J/(cm3*C)]


_LISTA = [
    Material("cobre_blando", "Cobre recocido trefilado blando (100 %)", 0.00393, 234.0, 1083.0, 1.72, 3.42),
    Material("cobre_duro", "Cobre trefilado duro comercial (97 %)", 0.00381, 242.0, 1084.0, 1.78, 3.42),
    Material("cobre_acero_40", "Alambre acero recubierto de cobre 40 %", 0.00378, 245.0, 1084.0, 4.40, 3.846),
    Material("cobre_acero_30", "Alambre acero recubierto de cobre 30 %", 0.00378, 245.0, 1084.0, 5.86, 3.846),
    Material("cobre_acero_20", "Varilla acero recubierta de cobre 20 %", 0.00378, 245.0, 1084.0, 8.62, 3.846),
    Material("aluminio_ec", "Aluminio grado EC", 0.00403, 228.0, 657.0, 2.86, 2.556),
    Material("aluminio_5005", "Aluminio aleacion 5005", 0.00353, 263.0, 652.0, 3.22, 2.598),
    Material("aluminio_6201", "Aluminio aleacion 6201", 0.00347, 268.0, 654.0, 3.28, 2.598),
    Material("aluminio_acero_20", "Acero recubierto de aluminio 20.3 %", 0.00360, 258.0, 657.0, 8.48, 3.58),
    Material("acero_1020", "Acero 1020", 0.00160, 605.0, 1510.0, 15.90, 3.28),
    Material("acero_inox_recub_20", "Acero recubierto de acero inoxidable 20.3 %", 0.00160, 605.0, 1400.0, 17.50, 3.28),
    Material("acero_zincado", "Varilla de acero cincada (galvanizada)", 0.00320, 293.0, 419.0, 72.00, 3.931),
    Material("acero_inox_304", "Acero inoxidable 304", 0.00130, 749.0, 1400.0, 72.00, 4.032),
]

MATERIALES = {m.clave: m for m in _LISTA}

# Temperatura maxima admisible segun el tipo de union (C). None = usar Tm del conductor.
TEMP_MAX_UNION = {
    "soldadura_exotermica": None,
    "soldadura_fuerte": 450.0,
    "conector_mecanico": 250.0,
}


def obtener(clave: str) -> Material:
    try:
        return MATERIALES[clave]
    except KeyError:
        raise ValueError(
            f"Material desconocido: '{clave}'. Opciones: {', '.join(MATERIALES)}"
        ) from None
