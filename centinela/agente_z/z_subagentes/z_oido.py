"""
Z-OIDO — El oído de Z. Micrófono del Z Fold.
==============================================
Percibe: nivel de ruido, patrones de sonido, voz de Abel
Actúa: detecta entornos ruidosos, reconoce llamadas
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_oido")


class ZOido:
    """Subagente de Z: micrófono y sonido."""

    def __init__(self, z):
        self.z = z
        self._nivel_ruido_db: float = 40.0
        self._voz_detectada: bool = False

    def percibir(self) -> Dict[str, Any]:
        """Percibe el entorno sonoro."""
        return {
            "ruido_db": self._nivel_ruido_db,
            "entorno": self._clasificar_sonido(),
            "voz_detectada": self._voz_detectada,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _clasificar_sonido(self) -> str:
        if self._nivel_ruido_db < 30:
            return "silencio"
        if self._nivel_ruido_db < 50:
            return "conversacion"
        if self._nivel_ruido_db < 70:
            return "ambiente_activo"
        return "ruidoso"

    def actuar(self, accion: str, datos: Dict) -> Dict:
        if accion == "modo_silencio":
            return {"recomendacion": "Entorno ruidoso detectado. ¿Modo vibración?"}
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-OIDO",
            "rol": "Micrófono y sonido",
            "ruido_db": self._nivel_ruido_db,
            "entorno": self._clasificar_sonido(),
        }
