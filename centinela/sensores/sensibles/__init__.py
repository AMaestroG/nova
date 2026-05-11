"""
SENSIBLES — Detectores especializados que sienten lo que los datos esconden.
=============================================================================
7 sensibles que monitorean aspectos específicos de la vida de Abel.
Son como "sentidos artificiales" que van más allá de los sensores crudos.

Cada sensible:
  - Recibe datos de múltiples sensores
  - Aplica su propio modelo de detección
  - Genera alertas TEMPRANAS (antes de que el problema sea visible)
  - Aprende líneas base personales
"""

from centinela.sensores.sensibles.sensible_estres import SensibleEstres
from centinela.sensores.sensibles.sensible_fatiga import SensibleFatiga
from centinela.sensores.sensibles.sensible_animo import SensibleAnimo
from centinela.sensores.sensibles.sensible_entorno import SensibleEntorno
from centinela.sensores.sensibles.sensible_movimiento import SensibleMovimiento
from centinela.sensores.sensibles.sensible_sueno import SensibleSueno
from centinela.sensores.sensibles.sensible_salud import SensibleSalud

__all__ = [
    "SensibleEstres", "SensibleFatiga", "SensibleAnimo",
    "SensibleEntorno", "SensibleMovimiento", "SensibleSueno",
    "SensibleSalud",
]
