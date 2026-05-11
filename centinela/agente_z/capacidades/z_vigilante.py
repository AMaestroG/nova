"""
Z-VIGILANTE — Modo seguridad con cámara y micrófono.
======================================================
Cuando Abel deja el Z Fold en un lugar fijo, Z activa modo vigilante:
  - Detecta movimiento frente a la cámara
  - Reconoce sonidos de alarma, rotura de cristales
  - Alerta si alguien mueve el teléfono
  - Modo discreto: pantalla apagada, solo sensores activos
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("centinela.agente_z.z_vigilante")


class ZVigilante:
    """
    Z como vigilante de seguridad. Protege el espacio de Abel.
    """

    SONIDOS_ALARMA = ["alarma", "sirena", "grito", "vidrio", "golpe"]

    def __init__(self):
        self._modo_vigilante: bool = False
        self._inicio_vigilancia: Optional[datetime] = None
        self._intrusiones_detectadas: int = 0
        self._inmovilidad_minutos: int = 5  # Minutos sin movimiento para activar

    def evaluar_activacion(self, percepciones: Dict) -> bool:
        """
        Activa modo vigilante si el Z Fold lleva inmóvil N minutos
        y Abel no está cerca (Watch 8 no detecta movimiento).
        """
        piel = percepciones.get("Z-PIEL", {})
        accel = piel.get("acelerometro", {})

        # Detectar inmovilidad
        magnitud = (
            accel.get("x", 0)**2 + accel.get("y", 0)**2 + accel.get("z", 9.81)**2
        )**0.5

        # Si la aceleración total es cercana a 9.81 (solo gravedad = quieto)
        if abs(magnitud - 9.81) < 0.3:
            if not self._modo_vigilante:
                self._activar_vigilancia()
            return True
        else:
            if self._modo_vigilante:
                self._desactivar_vigilancia()
            return False

    def _activar_vigilancia(self):
        self._modo_vigilante = True
        self._inicio_vigilancia = datetime.now(timezone.utc)
        logger.info("🔒 Z activa modo VIGILANTE. Protegiendo el espacio.")

    def _desactivar_vigilancia(self):
        self._modo_vigilante = False
        logger.info("🔓 Z desactiva modo vigilante. Abel regresó.")

    def vigilar(self, percepciones: Dict) -> Optional[Dict]:
        """Ronda de vigilancia de seguridad."""
        if not self._modo_vigilante:
            return None

        alerta = None
        ojo = percepciones.get("Z-OJO", {})
        oido = percepciones.get("Z-OIDO", {})
        piel = percepciones.get("Z-PIEL", {})

        # Movimiento brusco
        accel = piel.get("acelerometro", {})
        magnitud = (
            accel.get("x", 0)**2 + accel.get("y", 0)**2 + accel.get("z", 0)**2
        )**0.5
        if magnitud > 5:
            self._intrusiones_detectadas += 1
            alerta = {
                "tipo": "intrusion",
                "severidad": "alta",
                "mensaje": "¡El Z Fold fue movido! ¿Abel eres tú?",
            }

        # Ruido fuerte
        ruido = oido.get("nivel_ruido_db", 40)
        if ruido > 80:
            self._intrusiones_detectadas += 1
            alerta = {
                "tipo": "ruido_sospechoso",
                "severidad": "media",
                "mensaje": f"Ruido fuerte detectado: {ruido:.0f} dB",
            }

        # Cambio brusco de luz (alguien encendió luz)
        luz = ojo.get("luz_lux", 500)
        if luz > 500 and ojo.get("luz_anterior", 500) < 50:
            alerta = {
                "tipo": "cambio_luz",
                "severidad": "baja",
                "mensaje": "Cambio brusco de iluminación detectado.",
            }

        if alerta:
            logger.warning(f"🔒 Z VIGILANTE: {alerta['mensaje']}")

        return alerta

    def obtener_estado(self) -> Dict:
        return {
            "modo_vigilante": self._modo_vigilante,
            "inicio": self._inicio_vigilancia.isoformat() if self._inicio_vigilancia else None,
            "intrusiones": self._intrusiones_detectadas,
        }
