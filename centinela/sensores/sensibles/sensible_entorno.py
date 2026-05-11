"""
SENSIBLE ENTORNO — Detecta el ambiente que rodea a Abel.
=========================================================
Combina: luz, ruido, presión, temperatura, humedad, ubicación
Detecta: oficina, casa, calle, naturaleza, vehículo, silencio
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_entorno")


class SensibleEntorno:
    """Siente el entorno de Abel."""

    ENTORNOS = {
        "casa": {"luz": (50, 500), "ruido": (20, 50), "movimiento": "quieto"},
        "oficina": {"luz": (200, 1000), "ruido": (40, 65), "movimiento": "quieto"},
        "calle": {"luz": (500, 50000), "ruido": (50, 85), "movimiento": "caminando"},
        "naturaleza": {"luz": (500, 50000), "ruido": (20, 50), "presion": "estable"},
        "vehiculo": {"luz": "variable", "ruido": (50, 80), "movimiento": "vehiculo"},
        "silencio": {"luz": (0, 50), "ruido": (0, 25)},
    }

    def __init__(self):
        self._entorno_actual: str = "desconocido"
        self._confianza: float = 0.3
        self._tiempo_en_entorno: float = 0.0

    def sentir(self, luz: float = None, ruido: float = None,
               movimiento: str = None, presion: float = None,
               ubicacion: str = None) -> Dict:
        """Siente el entorno actual."""
        puntuaciones = {}

        for nombre, perfil in self.ENTORNOS.items():
            pts = 0
            checks = 0

            if luz and "luz" in perfil:
                rango = perfil["luz"]
                if isinstance(rango, tuple) and rango[0] <= luz <= rango[1]:
                    pts += 1
                checks += 1

            if ruido and "ruido" in perfil:
                rango = perfil["ruido"]
                if isinstance(rango, tuple) and rango[0] <= ruido <= rango[1]:
                    pts += 1
                checks += 1

            if movimiento and "movimiento" in perfil:
                if movimiento == perfil["movimiento"]:
                    pts += 1
                checks += 1

            if checks > 0:
                puntuaciones[nombre] = pts / checks

        if puntuaciones:
            mejor = max(puntuaciones, key=puntuaciones.get)
            self._entorno_actual = mejor
            self._confianza = puntuaciones[mejor]

        return {
            "entorno": self._entorno_actual,
            "confianza": round(self._confianza, 2),
        }

    def obtener_estado(self) -> Dict:
        return {"entorno": self._entorno_actual, "confianza": self._confianza}
