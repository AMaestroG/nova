"""
Z-MAPA — La orientación de Z. GPS y ubicación.
================================================
Percibe: latitud, longitud, altitud, velocidad, dirección
Actúa: detecta lugares, geovalla, sugiere rutas
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("centinela.agente_z.z_mapa")


class ZMapa:
    """Subagente de Z: GPS y ubicación."""

    def __init__(self, z):
        self.z = z
        self._lat: Optional[float] = None
        self._lon: Optional[float] = None
        self._altitud: Optional[float] = None
        self._velocidad: float = 0.0
        self._en_casa: bool = False
        self._en_movimiento: bool = False

    def percibir(self) -> Dict[str, Any]:
        """Percibe la ubicación actual."""
        return {
            "lat": self._lat,
            "lon": self._lon,
            "altitud": self._altitud,
            "velocidad": self._velocidad,
            "en_casa": self._en_casa,
            "en_movimiento": self._velocidad > 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def actualizar_ubicacion(self, lat: float, lon: float, **kwargs):
        """Actualiza con datos GPS reales."""
        self._lat = lat
        self._lon = lon
        self._altitud = kwargs.get("altitud")
        self._velocidad = kwargs.get("velocidad", 0.0)
        self._en_movimiento = self._velocidad > 1.0

    def actuar(self, accion: str, datos: Dict) -> Dict:
        if accion == "sugerir_ruta":
            return {"recomendacion": "Hay un parque a 500m que no has visitado."}
        elif accion == "geovalla":
            return {"alerta": "Has salido de tu zona habitual."}
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-MAPA",
            "rol": "GPS y ubicación",
            "ubicacion": f"{self._lat},{self._lon}" if self._lat else "desconocida",
            "en_movimiento": self._en_movimiento,
        }
