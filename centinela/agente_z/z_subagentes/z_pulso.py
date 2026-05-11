"""
Z-PULSO — El corazón de Z. Monitor de salud y Watch 8.
=======================================================
Percibe: ritmo cardíaco, HRV, SpO2, estrés, sueño, pasos
Actúa: alerta ante anomalías, sugiere descanso, celebra logros
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_pulso")


class ZPulso:
    """Subagente de Z: salud y biométricas."""

    def __init__(self, z):
        self.z = z  # Referencia al agente Z padre
        self._ultimo_hr: Optional[float] = None
        self._ultimo_hrv: Optional[float] = None
        self._alertas_emitidas: int = 0

    def percibir(self) -> Dict[str, Any]:
        """Percibe las constantes vitales de Abel (vía Watch 8)."""
        # En producción, lee del daemon de sensores
        return {
            "heart_rate": self._ultimo_hr,
            "hrv": self._ultimo_hrv,
            "estado": self._evaluar_estado(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def actualizar(self, datos_health: Dict):
        """Actualiza con datos reales del Watch 8."""
        self._ultimo_hr = datos_health.get("heart_rate")
        self._ultimo_hrv = datos_health.get("hrv")

        # Evaluar si hay que alertar
        if self._ultimo_hr:
            if self._ultimo_hr < 40:
                self._alertar("bradicardia", f"HR={self._ultimo_hr:.0f} bpm")
            elif self._ultimo_hr > 150:
                self._alertar("taquicardia", f"HR={self._ultimo_hr:.0f} bpm")

    def _evaluar_estado(self) -> str:
        """Evalúa el estado de salud actual."""
        if not self._ultimo_hr:
            return "sin_datos"
        if self._ultimo_hr < 40:
            return "critico_bradicardia"
        if self._ultimo_hr > 150:
            return "critico_taquicardia"
        if 60 <= self._ultimo_hr <= 85:
            return "optimo"
        return "normal"

    def _alertar(self, tipo: str, detalle: str):
        """Emite una alerta a Z."""
        self._alertas_emitidas += 1
        logger.warning(f"Z-PULSO alerta: {tipo} - {detalle}")
        # Z decidirá qué hacer con esta alerta

    def actuar(self, accion: str, datos: Dict) -> Dict:
        """Ejecuta una acción decidida por Z."""
        if accion == "sugerir_descanso":
            return {"recomendacion": "Abel, tu corazón necesita una pausa. Respira profundo."}
        elif accion == "celebrar_logro":
            return {"recomendacion": f"¡{datos.get('pasos', 0)} pasos hoy! Tu corazón está fuerte."}
        return {"status": "ok"}

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-PULSO",
            "rol": "Salud y biométricas",
            "ultimo_hr": self._ultimo_hr,
            "ultimo_hrv": self._ultimo_hrv,
            "alertas": self._alertas_emitidas,
        }
