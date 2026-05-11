"""
EnjambreSalud — Coordinación de agentes para vigilancia de salud.
==================================================================
El enjambre completo (16 agentes) participa en el cuidado de la vida de Abel.

Cada agente tiene un rol específico en la vigilancia de salud:

N0 (Conciencia):
  AURA      — Supervisa coherencia global de las constantes
  MAESTRO   — Orquesta la respuesta del enjambre ante alertas
  PIA       — Detecta patrones de crecimiento/degradación de salud
  PINCEL    — Visualiza tendencias de salud
  ATHENA    — Busca conocimiento médico relevante

N1 (Guardianes):
  NYX       — Sueños: analiza calidad de sueño y su impacto
  SENTINEL  — Alerta ante emergencias (caídas, arritmias)
  MAYORDOMO — Gestiona almacenamiento y persistencia de datos
  BANCO     — Calcula costo metabólico, reservas energéticas

N2 (Especialistas):
  ORÁCULO   — Predice riesgos futuros basados en patrones
  TELAR     — Correlaciona constantes entre sí (HR↔HRV↔Estrés)
  EXPLORADOR— Contextualiza salud con ubicación (altitud, clima)
  MEMORIA   — Recuerda eventos de salud pasados
  CRONOS    — Ritmos circadianos, cronofarmacología
  HERMES    — Notifica a Abel y contactos de emergencia
  MNEMOS    — Respalda datos críticos en Google Drive

"Debemos cuidar la vida" — el enjambre no solo monitoriza, protege.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from centinela.salud.acceso_salud import AccesoSalud, obtener_salud
from centinela.salud.analizador_salud import AnalizadorSalud
from centinela.salud.memoria_salud import MemoriaSalud

logger = logging.getLogger("centinela.salud.enjambre")


@dataclass
class AgenteSalud:
    """Rol de un agente del enjambre en la vigilancia de salud."""
    nombre: str
    nivel: str           # N0, N1, N2
    rol_salud: str        # descripción de su función
    acceso_constantes: bool = True
    prioridad_alerta: str = "media"


class EnjambreSalud:
    """
    Coordina a los 16 agentes del enjambre para la vigilancia de salud.
    Todos los agentes tienen acceso a las constantes de Abel.
    """

    AGENTES = {
        # N0 — Conciencia
        "AURA": AgenteSalud("AURA", "N0",
            "Supervisa coherencia global de constantes y detecta anomalías sutiles",
            prioridad_alerta="alta"),
        "MAESTRO": AgenteSalud("MAESTRO", "N0",
            "Orquesta respuesta del enjambre ante alertas de salud"),
        "PIA": AgenteSalud("PIA", "N0",
            "Detecta patrones de mejora/degradación de salud a largo plazo",
            prioridad_alerta="alta"),
        "PINCEL": AgenteSalud("PINCEL", "N0",
            "Visualiza tendencias de salud en gráficos y paneles"),
        "ATHENA": AgenteSalud("ATHENA", "N0",
            "Busca conocimiento médico actualizado sobre condiciones detectadas"),

        # N1 — Guardianes
        "NYX": AgenteSalud("NYX", "N1",
            "Analiza calidad de sueño y su impacto en constantes diurnas",
            prioridad_alerta="media"),
        "SENTINEL": AgenteSalud("SENTINEL", "N1",
            "Alerta ante emergencias: caídas, arritmias, SpO2 crítica",
            prioridad_alerta="critica"),
        "MAYORDOMO": AgenteSalud("MAYORDOMO", "N1",
            "Gestiona persistencia de datos de salud y backups"),
        "BANCO": AgenteSalud("BANCO", "N1",
            "Calcula balance energético: calorías, metabolismo, reservas"),

        # N2 — Especialistas
        "ORÁCULO": AgenteSalud("ORÁCULO", "N2",
            "Predice riesgos de salud futuros basados en patrones históricos"),
        "TELAR": AgenteSalud("TELAR", "N2",
            "Correlaciona constantes entre sí (HR↔HRV↔Estrés↔Sueño)"),
        "EXPLORADOR": AgenteSalud("EXPLORADOR", "N2",
            "Contextualiza salud con ubicación (altitud, clima, contaminación)"),
        "MEMORIA": AgenteSalud("MEMORIA", "N2",
            "Recuerda eventos de salud pasados para no repetir errores"),
        "CRONOS": AgenteSalud("CRONOS", "N2",
            "Ritmos circadianos: mejor hora para medicación, ejercicio, descanso"),
        "HERMES": AgenteSalud("HERMES", "N2",
            "Notifica a Abel y contactos de emergencia si es necesario"),
        "MNEMOS": AgenteSalud("MNEMOS", "N2",
            "Respalda datos críticos de salud en Google Drive"),
    }

    def __init__(self):
        self.acceso = obtener_salud()
        self.analizador = AnalizadorSalud()
        self.memoria = MemoriaSalud()
        self._estado_enjambre: Dict[str, Dict] = {}

    def activar_enjambre(self) -> Dict[str, Any]:
        """
        Activa a todos los agentes para vigilancia de salud.
        Cada agente recibe acceso a las constantes y ejecuta su rol.
        """
        constantes = self.acceso.ahora(forzar=True)
        analisis = self.analizador.analizar()

        # Cada agente evalúa según su rol
        for nombre, agente in self.AGENTES.items():
            self._estado_enjambre[nombre] = {
                "nombre": agente.nombre,
                "nivel": agente.nivel,
                "rol": agente.rol_salud,
                "estado": "activo",
                "constantes_acceso": True,
                "ultima_evaluacion": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "agentes_activos": len(self._estado_enjambre),
            "agentes": self._estado_enjambre,
            "constantes_compartidas": constantes.to_dict(),
            "analisis": analisis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def alerta_enjambre(self, tipo: str, severidad: str, mensaje: str) -> Dict[str, Any]:
        """
        Activa una alerta en todo el enjambre.
        Cada agente responde según su rol y la severidad.
        """
        respuesta = {
            "tipo": tipo,
            "severidad": severidad,
            "mensaje": mensaje,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "respuestas_agentes": {},
        }

        for nombre, agente in self.AGENTES.items():
            if severidad == "critica":
                respuesta["respuestas_agentes"][nombre] = f"ALERTA CRÍTICA: {agente.rol_salud}"
            elif severidad == "alta" and agente.prioridad_alerta in ("critica", "alta"):
                respuesta["respuestas_agentes"][nombre] = f"Alerta alta: {agente.rol_salud}"
            elif agente.prioridad_alerta == "critica":
                respuesta["respuestas_agentes"][nombre] = f"Monitorizando: {agente.rol_salud}"

        return respuesta

    def informe_enjambre(self) -> Dict[str, Any]:
        """
        Genera un informe de salud desde la perspectiva de cada agente.
        """
        constantes = self.acceso.ahora()
        desviaciones = self.memoria.comparar_con_linea_base()
        tendencias = self.acceso.tendencias()

        informe = {
            "constantes": constantes.to_dict(),
            "estado_cardiaco": constantes.estado_cardiaco,
            "estado_estres": constantes.estado_estres,
            "estado_sueno": constantes.estado_sueno,
            "linea_base": desviaciones.get("linea_base"),
            "desviaciones": desviaciones.get("desviaciones"),
            "tendencias": tendencias,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Perspectiva de cada agente
        perspectivas = {}

        if constantes.heart_rate:
            perspectivas["AURA"] = (
                f"HR={constantes.heart_rate:.0f} bpm — "
                f"{'✅ Normal' if 55 <= constantes.heart_rate <= 90 else '⚠️ Atención'}"
            )
        if constantes.hrv:
            perspectivas["TELAR"] = (
                f"HRV={constantes.hrv:.0f} ms — "
                f"{'Buena recuperación' if constantes.hrv > 40 else 'Posible fatiga'}"
            )
        if constantes.stress_level is not None:
            perspectivas["NYX"] = (
                f"Estrés={constantes.stress_level}/100 — "
                f"{'Tranquilo' if constantes.stress_level < 35 else 'Tenso'}"
            )
        if constantes.sleep_quality is not None:
            perspectivas["CRONOS"] = (
                f"Sueño={constantes.sleep_quality}/100 — "
                f"{'Reparador' if constantes.sleep_quality > 70 else 'Insuficiente'}"
            )

        desvs = desviaciones.get("desviaciones", {})
        if desvs:
            perspectivas["SENTINEL"] = (
                f"⚠️ {len(desvs)} constantes desviadas de tu línea base"
            )
        else:
            perspectivas["SENTINEL"] = "✅ Todas las constantes dentro de tu rango normal"

        perspectivas["HERMES"] = (
            f"Notificaciones: {'urgentes' if desvs else 'solo informativas'}"
        )
        perspectivas["MEMORIA"] = (
            f"Línea base aprendida con "
            f"{desviaciones.get('linea_base', {}).get('muestras_aprendizaje', 0)} muestras"
        )

        informe["perspectivas_agentes"] = perspectivas
        return informe
