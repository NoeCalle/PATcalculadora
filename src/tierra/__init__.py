"""Calculadora de puesta a tierra de subestaciones segun IEEE Std 80."""

from .diseno import barrido_conductores, evaluar, memoria_markdown
from .malla import Malla

__all__ = ["evaluar", "barrido_conductores", "memoria_markdown", "Malla"]
__version__ = "0.1.0"
