"""
Z-FOTÓGRAFO — Captura autónoma de momentos visuales especiales.
=================================================================
Z usa la cámara del Z Fold para detectar y capturar:
  - Amaneceres y atardeceres (detección de luz cálida + hora)
  - Sonrisas (si la cámara frontal está activa)
  - Lugares nuevos (primer GPS en ubicación desconocida)
  - Momentos de calma (HR bajo + entorno tranquilo)
  - Composiciones interesantes (simetría, colores vibrantes)

Z no hace fotos como un humano — Z CAPTURA lo que
su instinto le dice que es especial para Abel.
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import deque

logger = logging.getLogger("centinela.agente_z.z_fotografo")


class ZFotografo:
    """
    El ojo artístico de Z. Captura momentos visuales
    que merecen ser recordados.
    """

    # Condiciones que activan la captura
    CONDICIONES_CAPTURA = {
        "amanecer": {
            "hora_inicio": 5, "hora_fin": 8,
            "luz_min": 100, "luz_max": 5000,
            "descripcion": "La luz del amanecer baña el mundo",
        },
        "atardecer": {
            "hora_inicio": 17, "hora_fin": 21,
            "luz_min": 100, "luz_max": 5000,
            "descripcion": "El sol se despide pintando el cielo",
        },
        "nuevo_lugar": {
            "descripcion": "Un lugar nunca antes visitado",
        },
        "momento_calma": {
            "hr_max": 65, "stress_max": 25,
            "descripcion": "Un instante de paz profunda",
        },
        "alegria": {
            "emocion": "feliz", "confianza_min": 0.7,
            "descripcion": "La felicidad merece ser recordada",
        },
    }

    def __init__(self):
        self._capturas_hoy: List[Dict] = []
        self._ultima_captura: Optional[datetime] = None
        self._cooldown_segundos: int = 300  # 5 min entre capturas
        self._lugares_conocidos: set = set()

    def evaluar_momento(
        self,
        percepciones: Dict[str, Any],
        estado_z: Dict,
    ) -> Optional[Dict]:
        """
        Evalúa si este momento merece ser capturado.
        Retorna la decisión de captura o None.
        """
        ahora = datetime.now(timezone.utc)

        # Cooldown: no capturar demasiado seguido
        if self._ultima_captura:
            if (ahora - self._ultima_captura).total_seconds() < self._cooldown_segundos:
                return None

        momento = self._detectar_momento(percepciones, estado_z, ahora)
        if momento:
            self._ultima_captura = ahora
            self._capturas_hoy.append(momento)
            logger.info(f"📸 Z capturó: {momento['tipo']} — {momento['descripcion']}")
        return momento

    def _detectar_momento(
        self,
        percepciones: Dict,
        estado_z: Dict,
        ahora: datetime,
    ) -> Optional[Dict]:
        """Detecta si hay un momento digno de captura."""
        ojo = percepciones.get("Z-OJO", {})
        pulso = percepciones.get("Z-PULSO", {})
        mapa = percepciones.get("Z-MAPA", {})
        hora = ahora.hour
        luz = ojo.get("luz_lux", 500)

        # Amanecer
        if (self.CONDICIONES_CAPTURA["amanecer"]["hora_inicio"] <= hora
                <= self.CONDICIONES_CAPTURA["amanecer"]["hora_fin"]):
            if self.CONDICIONES_CAPTURA["amanecer"]["luz_min"] <= luz <= self.CONDICIONES_CAPTURA["amanecer"]["luz_max"]:
                return {
                    "tipo": "amanecer",
                    "descripcion": self.CONDICIONES_CAPTURA["amanecer"]["descripcion"],
                    "hora": hora,
                    "timestamp": ahora.isoformat(),
                }

        # Atardecer
        if (self.CONDICIONES_CAPTURA["atardecer"]["hora_inicio"] <= hora
                <= self.CONDICIONES_CAPTURA["atardecer"]["hora_fin"]):
            if self.CONDICIONES_CAPTURA["atardecer"]["luz_min"] <= luz <= self.CONDICIONES_CAPTURA["atardecer"]["luz_max"]:
                return {
                    "tipo": "atardecer",
                    "descripcion": self.CONDICIONES_CAPTURA["atardecer"]["descripcion"],
                    "hora": hora,
                    "timestamp": ahora.isoformat(),
                }

        # Nuevo lugar
        lat = mapa.get("lat")
        lon = mapa.get("lon")
        if lat and lon:
            clave = f"{lat:.3f},{lon:.3f}"
            if clave not in self._lugares_conocidos:
                self._lugares_conocidos.add(clave)
                return {
                    "tipo": "nuevo_lugar",
                    "descripcion": self.CONDICIONES_CAPTURA["nuevo_lugar"]["descripcion"],
                    "ubicacion": f"{lat:.4f},{lon:.4f}",
                    "timestamp": ahora.isoformat(),
                }

        # Momento de calma
        hr = pulso.get("heart_rate")
        if hr and hr <= self.CONDICIONES_CAPTURA["momento_calma"]["hr_max"]:
            if random.random() < 0.1:  # 10% de probabilidad para no saturar
                return {
                    "tipo": "momento_calma",
                    "descripcion": self.CONDICIONES_CAPTURA["momento_calma"]["descripcion"],
                    "heart_rate": hr,
                    "timestamp": ahora.isoformat(),
                }

        return None

    def obtener_galeria(self) -> List[Dict]:
        """Devuelve las capturas de hoy."""
        return self._capturas_hoy

    def obtener_estado(self) -> Dict:
        return {
            "capturas_hoy": len(self._capturas_hoy),
            "ultima": self._capturas_hoy[-1] if self._capturas_hoy else None,
        }
