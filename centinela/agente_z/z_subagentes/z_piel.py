"""
Z-PIEL — La piel de Z. Todos los sensores ambientales del Z Fold.
==================================================================
Percibe: acelerómetro, giroscopio, magnetómetro, barómetro,
         proximidad, temperatura, humedad, presión
Actúa: detecta caídas, movimientos bruscos, cambios de altitud
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_piel")


class ZPiel:
    """Subagente de Z: sensores ambientales."""

    def __init__(self, z):
        self.z = z
        self._acelerometro = {"x": 0.0, "y": 0.0, "z": 9.81}
        self._giroscopio = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._barometro: float = 1013.25
        self._temperatura: float = 22.0
        self._proximidad: float = 5.0
        self._caida_detectada: bool = False

    def percibir(self) -> Dict[str, Any]:
        """Percibe el mundo físico a través de los sensores."""
        # Detectar caída
        accel_mag = math.sqrt(
            self._acelerometro["x"]**2 +
            self._acelerometro["y"]**2 +
            self._acelerometro["z"]**2
        )

        return {
            "acelerometro": self._acelerometro,
            "giroscopio": self._giroscopio,
            "barometro": self._barometro,
            "temperatura": self._temperatura,
            "proximidad": self._proximidad,
            "aceleracion_total": round(accel_mag, 2),
            "caida_detectada": accel_mag > 20 or accel_mag < 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def actualizar_sensor(self, tipo: str, valores: Dict):
        """Actualiza un sensor específico con datos reales."""
        if tipo == "acelerometro":
            self._acelerometro = valores
        elif tipo == "giroscopio":
            self._giroscopio = valores
        elif tipo == "barometro":
            self._barometro = valores.get("x", valores.get("valor", self._barometro))
        elif tipo == "temperatura_ambiente":
            self._temperatura = valores.get("x", valores.get("valor", self._temperatura))

    def actuar(self, accion: str, datos: Dict) -> Dict:
        if accion == "alerta_caida":
            return {"alerta": "¡Posible caída detectada! ¿Estás bien, Abel?"}
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-PIEL",
            "rol": "Sensores ambientales",
            "barometro": self._barometro,
            "temperatura": self._temperatura,
            "caida_detectada": self._caida_detectada,
        }
