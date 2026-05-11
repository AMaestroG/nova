"""
SENSIBLE MOVIMIENTO — Detecta patrones de movimiento y actividad.
==================================================================
Combina: acelerómetro, giroscopio, GPS, pasos
Detecta: quieto, caminando, corriendo, bicicleta, vehículo, temblando
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_movimiento")


class SensibleMovimiento:
    """Siente cómo se mueve Abel."""

    def __init__(self):
        self._actividad_actual: str = "quieto"
        self._intensidad: float = 0.0
        self._acumulado_pasos: int = 0
        self._ultimo_movimiento: Optional[str] = None

    def sentir(self, accel: Dict = None, gps_vel: float = None,
               pasos: int = None) -> Dict:
        """Siente el movimiento actual."""
        if accel:
            magnitud = math.sqrt(
                accel.get("x", 0)**2 + accel.get("y", 0)**2 +
                (accel.get("z", 9.81) - 9.81)**2
            )
            self._intensidad = magnitud

            if magnitud < 0.3:
                self._actividad_actual = "quieto"
            elif magnitud < 2:
                self._actividad_actual = "caminando"
            elif magnitud < 6:
                self._actividad_actual = "corriendo"
            else:
                self._actividad_actual = "movimiento_intenso"

        if gps_vel:
            if gps_vel > 25:
                self._actividad_actual = "vehiculo"
            elif gps_vel > 10:
                self._actividad_actual = "bicicleta"

        if pasos:
            self._acumulado_pasos = pasos

        return {
            "actividad": self._actividad_actual,
            "intensidad": round(self._intensidad, 2),
            "pasos": self._acumulado_pasos,
        }

    def obtener_estado(self) -> Dict:
        return {
            "actividad": self._actividad_actual,
            "intensidad": self._intensidad,
        }
