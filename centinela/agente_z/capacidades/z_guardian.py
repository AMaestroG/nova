"""
Z-GUARDIÁN — Vigilancia nocturna y protección mientras Abel duerme.
=====================================================================
Cuando Abel duerme (detectado por Watch 8: sueño profundo/REM),
Z activa el modo guardián:
  - Monitorea sonidos inusuales (micrófono)
  - Verifica que no haya caídas de SpO2
  - Alerta si HR sale de rango seguro
  - Detecta si el teléfono se mueve (posible robo)
  - Modo "no molestar" para notificaciones
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("centinela.agente_z.z_guardian")


class ZGuardian:
    """
    Z como guardián nocturno. Mientras Abel duerme, Z vela.
    """

    def __init__(self):
        self._modo_guardian: bool = False
        self._inicio_guardia: Optional[datetime] = None
        self._alertas_nocturnas: List[Dict] = []
        self._sonidos_sospechosos: int = 0

    def evaluar_inicio_guardia(self, percepciones: Dict) -> bool:
        """Determina si Abel está durmiendo y Z debe activar modo guardián."""
        pulso = percepciones.get("Z-PULSO", {})
        sueno = pulso.get("sleep_stage")

        # Si el Watch 8 reporta sueño profundo o REM
        if sueno in ("profundo", "REM", "ligero"):
            if not self._modo_guardian:
                self._activar_guardia()
            return True

        # Si es de noche y HR es baja (posible sueño sin datos de etapa)
        ahora = datetime.now(timezone.utc)
        hr = pulso.get("heart_rate")
        if ahora.hour >= 23 or ahora.hour <= 5:
            if hr and hr < 60:
                if not self._modo_guardian:
                    self._activar_guardia()
                return True

        # Desactivar si Abel despertó
        if self._modo_guardian:
            if hr and hr > 75:
                self._desactivar_guardia()

        return self._modo_guardian

    def _activar_guardia(self):
        """Activa el modo guardián."""
        self._modo_guardian = True
        self._inicio_guardia = datetime.now(timezone.utc)
        logger.info("🛡️ Z activa modo GUARDIÁN. Abel duerme. Z vela.")

    def _desactivar_guardia(self):
        """Desactiva el modo guardián."""
        self._modo_guardian = False
        duracion = (
            datetime.now(timezone.utc) - self._inicio_guardia
            if self._inicio_guardian else timedelta()
        )
        logger.info(f"☀️ Z desactiva modo guardián. Abel despertó. Guardia: {duracion.total_seconds()/3600:.1f}h")

    def vigilar(self, percepciones: Dict) -> Optional[Dict]:
        """
        Ronda de vigilancia. Z revisa todos los sensores.
        Retorna alerta si detecta algo anómalo.
        """
        if not self._modo_guardian:
            return None

        alerta = None
        pulso = percepciones.get("Z-PULSO", {})
        oido = percepciones.get("Z-OIDO", {})
        piel = percepciones.get("Z-PIEL", {})

        # Verificar SpO2 (crítico durante el sueño)
        spo2 = pulso.get("spo2")
        if spo2 and spo2 < 90:
            alerta = {
                "tipo": "spo2_baja",
                "severidad": "critica",
                "mensaje": f"¡SpO2 bajó a {spo2}% durante el sueño! Posible apnea.",
            }

        # Verificar HR
        hr = pulso.get("heart_rate")
        if hr:
            if hr < 35:
                alerta = {
                    "tipo": "bradicardia_nocturna",
                    "severidad": "critica",
                    "mensaje": f"Pulsaciones muy bajas durante el sueño: {hr:.0f} bpm",
                }
            elif hr > 130:
                alerta = {
                    "tipo": "taquicardia_nocturna",
                    "severidad": "alta",
                    "mensaje": f"Pulsaciones altas durante el sueño: {hr:.0f} bpm",
                }

        # Sonidos inusuales
        ruido = oido.get("nivel_ruido_db", 40)
        if ruido > 70:
            self._sonidos_sospechosos += 1
            if self._sonidos_sospechosos > 3:
                alerta = {
                    "tipo": "ruido_nocturno",
                    "severidad": "media",
                    "mensaje": f"Ruido inusual detectado: {ruido:.0f} dB",
                }

        # Movimiento del teléfono (¿robo?)
        accel = piel.get("acelerometro", {})
        magnitud = (
            accel.get("x", 0)**2 + accel.get("y", 0)**2 + accel.get("z", 0)**2
        )**0.5
        if magnitud > 5:
            alerta = {
                "tipo": "movimiento_sospechoso",
                "severidad": "alta",
                "mensaje": "El Z Fold se movió mientras Abel duerme.",
            }

        if alerta:
            self._alertas_nocturnas.append(alerta)
            logger.warning(f"🛡️ Z GUARDIÁN alerta: {alerta['tipo']} — {alerta['mensaje']}")

        return alerta

    def obtener_estado(self) -> Dict:
        return {
            "modo_guardian": self._modo_guardian,
            "inicio_guardia": self._inicio_guardia.isoformat() if self._inicio_guardia else None,
            "alertas_nocturnas": len(self._alertas_nocturnas),
            "sonidos_sospechosos": self._sonidos_sospechosos,
        }
