"""
Módulo de Salud — Acceso compartido a las constantes vitales de Abel
====================================================================
Permite a TODOS los agentes del enjambre (N0, N1, N2) acceder
a los datos de salud en tiempo real y al historial.

Uso desde cualquier agente:
    from centinela.salud import AccesoSalud
    salud = AccesoSalud()
    hr = salud.ultima_pulsacion()
    tendencias = salud.tendencias()
    alertas = salud.alertas_activas()
"""

from centinela.salud.acceso_salud import AccesoSalud
from centinela.salud.analizador_salud import AnalizadorSalud
from centinela.salud.memoria_salud import MemoriaSalud
from centinela.salud.enjambre_salud import EnjambreSalud

__all__ = ["AccesoSalud", "AnalizadorSalud", "MemoriaSalud", "EnjambreSalud"]
