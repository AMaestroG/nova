"""
Z-MEDITADOR — Guía de respiración y calma cuando Abel está estresado.
======================================================================
Z detecta estrés elevado (Watch 8) y ofrece ejercicios de respiración
guiada. No espera a que Abel se lo pida — Z es proactivo.

Técnicas:
  - 4-7-8: inhala 4s, retiene 7s, exhala 8s (ansiedad)
  - Box breathing: 4-4-4-4 (estrés general)
  - Coherencia cardíaca: 5-5 (HRV bajo)
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

logger = logging.getLogger("centinela.agente_z.z_meditador")


class ZMeditador:
    """
    Z como guía de meditación. Detecta estrés y ayuda a Abel a respirar.
    """

    TECNICAS = {
        "estres_alto": {
            "nombre": "Respiración 4-7-8",
            "fases": [
                {"accion": "inhala", "segundos": 4, "icono": "🫁"},
                {"accion": "retén", "segundos": 7, "icono": "⏸️"},
                {"accion": "exhala", "segundos": 8, "icono": "😤"},
            ],
            "repeticiones": 4,
            "descripcion": "Reduce la ansiedad activando el sistema parasimpático.",
        },
        "estres_moderado": {
            "nombre": "Coherencia Cardíaca",
            "fases": [
                {"accion": "inhala", "segundos": 5, "icono": "🫁"},
                {"accion": "exhala", "segundos": 5, "icono": "😤"},
            ],
            "repeticiones": 6,
            "descripcion": "Sincroniza tu corazón con tu respiración.",
        },
        "estres_bajo": {
            "nombre": "Respiración Consciente",
            "fases": [
                {"accion": "inhala profundo", "segundos": 3, "icono": "🫁"},
                {"accion": "exhala lento", "segundos": 6, "icono": "😤"},
            ],
            "repeticiones": 3,
            "descripcion": "Un momento de presencia. Solo respirar.",
        },
    }

    def __init__(self):
        self._ultima_sesion: Optional[datetime] = None
        self._sesiones_hoy: int = 0
        self._cooldown_minutos: int = 60

    def evaluar_necesidad(
        self, percepciones: Dict
    ) -> Optional[Dict]:
        """
        Evalúa si Abel necesita una sesión de respiración.
        Z es proactivo: no espera a que Abel se lo pida.
        """
        ahora = datetime.now(timezone.utc)

        # Cooldown: no molestar cada 5 minutos
        if self._ultima_sesion:
            if (ahora - self._ultima_sesion).total_seconds() < self._cooldown_minutos * 60:
                return None

        pulso = percepciones.get("Z-PULSO", {})
        stress = pulso.get("stress_level")
        hr = pulso.get("heart_rate")

        if stress is None and hr is None:
            return None

        # Determinar nivel y técnica
        if stress and stress > 75:
            tecnica = self.TECNICAS["estres_alto"]
            razon = f"Estrés elevado detectado: {stress}/100"
        elif stress and stress > 50:
            tecnica = self.TECNICAS["estres_moderado"]
            razon = f"Estrés moderado: {stress}/100. Un respiro te vendrá bien."
        elif hr and hr > 90:
            tecnica = self.TECNICAS["estres_moderado"]
            razon = f"Tu corazón está acelerado: {hr:.0f} bpm."
        elif hr and hr > 75:
            tecnica = self.TECNICAS["estres_bajo"]
            razon = f"Un momento de respiración consciente."
        else:
            return None

        self._ultima_sesion = ahora
        self._sesiones_hoy += 1

        return {
            "tecnica": tecnica["nombre"],
            "fases": tecnica["fases"],
            "repeticiones": tecnica["repeticiones"],
            "descripcion": tecnica["descripcion"],
            "razon": razon,
            "duracion_total_segundos": sum(f["segundos"] for f in tecnica["fases"]) * tecnica["repeticiones"],
        }

    def obtener_estado(self) -> Dict:
        return {
            "sesiones_hoy": self._sesiones_hoy,
            "ultima_sesion": self._ultima_sesion.isoformat() if self._ultima_sesion else None,
        }
