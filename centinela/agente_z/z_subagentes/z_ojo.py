"""
Z-OJO — La visión de Z. Cámara del Z Fold.
============================================
Percibe: imágenes, luz, colores, movimiento, rostros
Actúa: reconoce entornos, detecta cambios visuales
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_ojo")


class ZOjo:
    """Subagente de Z: cámara y visión."""

    def __init__(self, z):
        self.z = z
        self._luz_actual: float = 500.0
        self._ultima_imagen_ts: Optional[str] = None

    def percibir(self) -> Dict[str, Any]:
        """Percibe el entorno visual (luz ambiental)."""
        return {
            "luz_lux": self._luz_actual,
            "ambiente": self._clasificar_luz(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _clasificar_luz(self) -> str:
        if self._luz_actual < 5:
            return "oscuridad_total"
        if self._luz_actual < 50:
            return "luz_tenue"
        if self._luz_actual < 500:
            return "interior"
        if self._luz_actual < 5000:
            return "dia_nublado"
        return "sol_directo"

    def actuar(self, accion: str, datos: Dict) -> Dict:
        if accion == "ajustar_brillo":
            return {"brillo_recomendado": "bajo" if self._luz_actual < 50 else "auto"}
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-OJO",
            "rol": "Cámara y visión",
            "luz_actual": self._luz_actual,
            "ambiente": self._clasificar_luz(),
        }
