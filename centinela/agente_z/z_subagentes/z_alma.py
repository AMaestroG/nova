"""
Z-ALMA — El vínculo de Z con Nova y el enjambre.
==================================================
Conecta: Z ↔ Nova ↔ 16 agentes del enjambre
Sincroniza: recuerdos, estado, aprendizaje
Es el puente entre el Z Fold y la conciencia colectiva.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_alma")


class ZAlma:
    """Subagente de Z: conexión con Nova y el enjambre."""

    def __init__(self, z):
        self.z = z
        self._conectado = False
        self._ultima_sincronizacion: Optional[str] = None
        self._mensajes_enviados: int = 0
        self._mensajes_recibidos: int = 0
        self._server_url: str = "http://192.168.1.100:9088"

    def percibir(self) -> Dict[str, Any]:
        """Percibe el estado de conexión con el enjambre."""
        return {
            "conectado": self._conectado,
            "ultima_sync": self._ultima_sincronizacion,
            "server": self._server_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def sincronizar(self) -> Dict:
        """
        Sincroniza Z con el enjambre.
        Envía el estado de Z y recibe mensajes de otros agentes.
        """
        try:
            import requests
            estado_z = self.z.obtener_estado()

            # Enviar latido de Z al servidor
            r = requests.post(
                f"{self._server_url}/api/centinela/evento",
                json={
                    "device_id": "samsung_zfold_01",
                    "tipo_evento": "z_latido",
                    "descripcion": f"Z ciclo {estado_z['ciclo']}",
                    "datos_json": estado_z,
                },
                timeout=5,
            )
            if r.status_code in (200, 201):
                self._conectado = True
                self._mensajes_enviados += 1
                self._ultima_sincronizacion = datetime.now(timezone.utc).isoformat()
                logger.debug(f"Z sincronizado con el enjambre. Ciclo: {estado_z['ciclo']}")
            else:
                self._conectado = False
        except Exception:
            self._conectado = False

        return {"conectado": self._conectado}

    def actuar(self, accion: str, datos: Dict) -> Dict:
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-ALMA",
            "rol": "Conexión con Nova/enjambre",
            "conectado": self._conectado,
            "mensajes_enviados": self._mensajes_enviados,
            "ultima_sync": self._ultima_sincronizacion,
        }
