"""
Z-SUBAGENTES — Los 7 ayudantes de Z
=====================================
Cada subagente es una extensión sensorial o cognitiva de Z.
Viven dentro del Z Fold y le dan a Z percepción del mundo.
"""

# Todos exportados desde aquí
from centinela.agente_z.z_subagentes.z_pulso import ZPulso
from centinela.agente_z.z_subagentes.z_ojo import ZOjo
from centinela.agente_z.z_subagentes.z_oido import ZOido
from centinela.agente_z.z_subagentes.z_piel import ZPiel
from centinela.agente_z.z_subagentes.z_mapa import ZMapa
from centinela.agente_z.z_subagentes.z_mente import ZMente
from centinela.agente_z.z_subagentes.z_alma import ZAlma

__all__ = [
    "ZPulso", "ZOjo", "ZOido", "ZPiel",
    "ZMapa", "ZMente", "ZAlma",
]
