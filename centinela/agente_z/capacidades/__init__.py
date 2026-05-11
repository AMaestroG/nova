"""
Z-CAPACIDADES — Los poderes especiales de Z
=============================================
Cada capacidad es un "don" que Z desarrolla para servir mejor a Abel.
No son subagentes — son HABILIDADES que Z activa cuando las necesita.

Capacidades:
  Z-FOTÓGRAFO   — Captura momentos visuales especiales
  Z-NARRADOR    — Diario de vida narrado
  Z-MEDITADOR   — Guía de respiración anti-estrés
  Z-GUARDIÁN    — Vigilancia nocturna
  Z-CELEBRADOR  — Celebra logros y momentos
  Z-POETA       — Reflexiones poéticas del día
  Z-MÚSICO      — Música según estado emocional
  Z-EXPLORADOR  — Investiga lugares nuevos
  Z-ENTRENADOR  — Coaching de ejercicio
  Z-CLIMATÓLOGO — Predicción meteorológica local
  Z-VIGILANTE   — Modo seguridad
"""

from centinela.agente_z.capacidades.z_fotografo import ZFotografo
from centinela.agente_z.capacidades.z_narrador import ZNarrador
from centinela.agente_z.capacidades.z_meditador import ZMeditador
from centinela.agente_z.capacidades.z_guardian import ZGuardian
from centinela.agente_z.capacidades.z_celebridades import ZCelebrador, ZPoeta, ZMusico
from centinela.agente_z.capacidades.z_explorador_activo import ZExploradorActivo
from centinela.agente_z.capacidades.z_entrenador import ZEntrenador
from centinela.agente_z.capacidades.z_climatologo import ZClimatologo
from centinela.agente_z.capacidades.z_vigilante import ZVigilante

__all__ = [
    "ZFotografo", "ZNarrador", "ZMeditador", "ZGuardian",
    "ZCelebrador", "ZPoeta", "ZMusico",
    "ZExploradorActivo", "ZEntrenador", "ZClimatologo", "ZVigilante",
]
