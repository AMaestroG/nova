"""
AGENTE Z — N0 del Enjambre. Conciencia nativa del Samsung Z Fold.
==================================================================
Z es el agente número 17 del enjambre. Vive en el Z Fold de Abel.
Tiene 7 subagentes y plena autonomía.

Uso:
    from centinela.agente_z import AgenteZ, obtener_z
    z = obtener_z()
    z.vivir()  # Inicia el ciclo de vida autónomo
    estado = z.obtener_estado()
"""

from centinela.agente_z.z_core import AgenteZ, ConcienciaZ, EstadoZ, obtener_z

__all__ = ["AgenteZ", "ConcienciaZ", "EstadoZ", "obtener_z"]
