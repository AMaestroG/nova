"""
SENSORES — Fusión, limpieza, patrones y sensibles.
====================================================
Propaga los sensores del Z Fold + Watch 8 en una red de
detección inteligente que encuentra patrones y elimina ruido.

Módulos:
  fusion_sensorial  — Combina todos los sensores en percepción unificada
  limpiador_ruido   — Filtros Kalman, EMA, outliers
  motor_patrones    — Descubre patrones en series temporales
  sensibles/        — 7 detectores especializados

Los 7 sensibles:
  SensibleEstres      — Estrés antes de que sea visible
  SensibleFatiga      — Cansancio acumulado
  SensibleAnimo       — Estado de ánimo real
  SensibleEntorno     — Ambiente que rodea a Abel
  SensibleMovimiento  — Patrones de actividad física
  SensibleSueno       — Calidad de sueño
  SensibleSalud       — Anomalías de salud tempranas
"""

from centinela.sensores.fusion_sensorial import FusionSensorial, PercepcionUnificada
from centinela.sensores.limpiador_ruido import LimpiadorRuido, SenalLimpia
from centinela.sensores.motor_patrones import MotorPatrones, PatronDetectado
from centinela.sensores.sensibles import (
    SensibleEstres, SensibleFatiga, SensibleAnimo,
    SensibleEntorno, SensibleMovimiento, SensibleSueno,
    SensibleSalud,
)

__all__ = [
    "FusionSensorial", "PercepcionUnificada",
    "LimpiadorRuido", "SenalLimpia",
    "MotorPatrones", "PatronDetectado",
    "SensibleEstres", "SensibleFatiga", "SensibleAnimo",
    "SensibleEntorno", "SensibleMovimiento", "SensibleSueno",
    "SensibleSalud",
]
