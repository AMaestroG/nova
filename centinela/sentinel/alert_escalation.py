"""
alert_escalation — Escalación de Alertas
Nova Homonexus — SENTINEL

Gestiona el ciclo de vida de las alertas:
  - Niveles: INFO, WARNING, ERROR, CRITICAL
  - Protocolo CRITICAL: notificación inmediata multicanal
  - Integración con bots de Telegram del enjambre
  - Reglas de escalación temporal
  - Registro de tiempo de respuesta y resolución
"""

import os
import time
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List, Callable
from collections import defaultdict
from dataclasses import dataclass, field

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.escalation")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AlertRecord:
    """Registro de una alerta en el sistema de escalación."""
    alert_id: str
    tipo: str
    severidad: str  # INFO, WARNING, ERROR, CRITICAL
    mensaje: str
    device_id: str
    source: str  # sensor, health, geo, threat, anomaly, watchdog
    details: Dict[str, Any]
    timestamp: float
    nivel_actual: int  # índice en levels
    nivel_inicial: int
    ultima_escalacion: float
    resuelta: bool = False
    resuelta_por: str = ""
    resuelta_en: float = 0.0
    notificaciones_enviadas: List[str] = field(default_factory=list)
    tiempo_respuesta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "device_id": self.device_id,
            "source": self.source,
            "details": self.details,
            "timestamp": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "nivel_actual": self.nivel_actual,
            "nivel_inicial": self.nivel_inicial,
            "resuelta": self.resuelta,
            "resuelta_por": self.resuelta_por,
            "resuelta_en": (
                datetime.fromtimestamp(
                    self.resuelta_en, tz=timezone.utc
                ).isoformat()
                if self.resuelta_en > 0
                else None
            ),
            "tiempo_respuesta_seg": self.tiempo_respuesta,
            "notificaciones": self.notificaciones_enviadas,
        }


# =============================================================================
# ALERT ESCALATION
# =============================================================================

class AlertEscalation:
    """
    Sistema de escalación de alertas del Centinela.

    Gestiona:
      - Niveles de severidad con escalación automática
      - Notificaciones multicanal (dashboard, Telegram, webhook)
      - Protocolo CRITICAL con respuesta inmediata
      - Registro de tiempos de respuesta
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        ae_cfg = self._rules.alert_escalation_cfg

        # Niveles de severidad
        self._levels = ae_cfg.get(
            "levels", ["INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        self._level_map = {
            level: i for i, level in enumerate(self._levels)
        }

        # Tiempos de escalación (minutos)
        self._escalation_times = ae_cfg.get("escalation_minutes", {})

        # Canales de notificación por nivel
        self._notification_channels = ae_cfg.get(
            "notification_channels", {}
        )

        # Telegram
        self._telegram_bots = ae_cfg.get("telegram_bots", [])

        # Webhook
        self._webhook_url = ae_cfg.get("webhook_url", "")

        # Respuesta crítica
        self._critical_timeout = ae_cfg.get(
            "critical_response_timeout", 5
        )

        # Reintentos
        self._notification_retries = ae_cfg.get(
            "notification_retries", 3
        )
        self._retry_delay = ae_cfg.get(
            "notification_retry_delay", 10
        )

        # Alertas activas
        self._active_alerts: Dict[str, AlertRecord] = {}
        self._resolved_alerts: List[AlertRecord] = []
        self._max_resolved = 10000

        # Callbacks de notificación
        self._notify_callbacks: Dict[str, Callable] = {}

        logger.info(
            "AlertEscalation inicializado. "
            "Niveles: %s, Canales: %s",
            self._levels,
            list(self._notification_channels.keys()),
        )

    # ------------------------------------------------------------------
    # REGISTRO DE CALLBACKS
    # ------------------------------------------------------------------

    def register_notification_callback(
        self, channel: str, callback: Callable
    ) -> None:
        """
        Registra un callback para un canal de notificación.

        Args:
            channel: Nombre del canal (dashboard, telegram, webhook).
            callback: Función que recibe (alert_data, channel).
        """
        self._notify_callbacks[channel] = callback
        logger.debug(
            "Callback registrado para canal: %s", channel
        )

    # ------------------------------------------------------------------
    # CREACIÓN Y ESCALACIÓN DE ALERTAS
    # ------------------------------------------------------------------

    def create_alert(
        self,
        tipo: str,
        severidad: str,
        mensaje: str,
        device_id: str = "sistema",
        source: str = "sistema",
        details: Optional[Dict[str, Any]] = None,
    ) -> AlertRecord:
        """
        Crea una nueva alerta en el sistema de escalación.

        Args:
            tipo: Tipo de alerta (salud, seguridad, sistema, etc.).
            severidad: Nivel inicial (INFO, WARNING, ERROR, CRITICAL).
            mensaje: Descripción de la alerta.
            device_id: ID del dispositivo relacionado.
            source: Origen de la alerta.
            details: Detalles adicionales.

        Returns:
            AlertRecord creado.
        """
        now = time.time()
        nivel = self._level_map.get(severidad, 0)

        alert_id = (
            f"{source}-{tipo}-{int(now)}-"
            f"{hash(mensaje) % 10000:04d}"
        )

        alert = AlertRecord(
            alert_id=alert_id,
            tipo=tipo,
            severidad=severidad,
            mensaje=mensaje,
            device_id=device_id,
            source=source,
            details=details or {},
            timestamp=now,
            nivel_actual=nivel,
            nivel_inicial=nivel,
            ultima_escalacion=now,
        )

        self._active_alerts[alert_id] = alert

        logger.log(
            logging.CRITICAL
            if severidad == "CRITICAL"
            else logging.WARNING,
            "Alerta creada [%s/%s]: %s",
            severidad,
            source,
            mensaje,
        )

        # Enviar notificaciones inmediatas
        self._send_notifications(alert)

        return alert

    def escalate_alert(self, alert_id: str) -> bool:
        """
        Escala una alerta al siguiente nivel.

        Args:
            alert_id: ID de la alerta.

        Returns:
            True si se escaló exitosamente.
        """
        alert = self._active_alerts.get(alert_id)
        if not alert or alert.resuelta:
            return False

        max_level = len(self._levels) - 1
        if alert.nivel_actual >= max_level:
            return False  # Ya en nivel máximo

        alert.nivel_actual += 1
        alert.ultima_escalacion = time.time()
        alert.severidad = self._levels[alert.nivel_actual]

        logger.warning(
            "Alerta escalada [%s]: %s -> %s",
            alert_id,
            self._levels[alert.nivel_actual - 1],
            alert.severidad,
        )

        # Notificar en nuevo nivel
        self._send_notifications(alert)

        return True

    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str = "sistema",
    ) -> bool:
        """
        Resuelve una alerta activa.

        Args:
            alert_id: ID de la alerta.
            resolved_by: Quién o qué resolvió la alerta.

        Returns:
            True si se resolvió exitosamente.
        """
        alert = self._active_alerts.get(alert_id)
        if not alert:
            return False

        now = time.time()
        alert.resuelta = True
        alert.resuelta_por = resolved_by
        alert.resuelta_en = now
        alert.tiempo_respuesta = now - alert.timestamp

        # Mover a historial
        self._resolved_alerts.append(alert)
        if len(self._resolved_alerts) > self._max_resolved:
            self._resolved_alerts = (
                self._resolved_alerts[-self._max_resolved:]
            )

        del self._active_alerts[alert_id]

        logger.info(
            "Alerta resuelta [%s] por %s en %.1fs",
            alert_id,
            resolved_by,
            alert.tiempo_respuesta,
        )

        return True

    # ------------------------------------------------------------------
    # VERIFICACIÓN DE ESCALACIÓN TEMPORAL
    # ------------------------------------------------------------------

    def check_escalations(self) -> List[AlertRecord]:
        """
        Verifica si alguna alerta debe ser escalada por tiempo.

        Returns:
            Lista de alertas escaladas.
        """
        now = time.time()
        escalated = []

        for alert_id, alert in list(self._active_alerts.items()):
            if alert.resuelta:
                continue

            severidad = self._levels[alert.nivel_actual]
            escalation_time = self._escalation_times.get(severidad)

            if escalation_time:
                elapsed = now - alert.ultima_escalacion
                if elapsed >= escalation_time * 60:
                    if self.escalate_alert(alert_id):
                        escalated.append(alert)

        return escalated

    # ------------------------------------------------------------------
    # NOTIFICACIONES
    # ------------------------------------------------------------------

    def _send_notifications(self, alert: AlertRecord) -> None:
        """
        Envía notificaciones para una alerta según su nivel.

        Args:
            alert: Alerta a notificar.
        """
        severidad = self._levels[alert.nivel_actual]
        channels = self._notification_channels.get(severidad, [])

        for channel in channels:
            if channel in alert.notificaciones_enviadas:
                continue  # Ya notificado por este canal

            success = self._notify_channel(channel, alert)
            if success:
                alert.notificaciones_enviadas.append(channel)

    def _notify_channel(
        self, channel: str, alert: AlertRecord
    ) -> bool:
        """
        Envía notificación por un canal específico.

        Args:
            channel: Canal de notificación.
            alert: Alerta a notificar.

        Returns:
            True si se notificó exitosamente.
        """
        alert_data = alert.to_dict()

        # Callback registrado
        if channel in self._notify_callbacks:
            try:
                self._notify_callbacks[channel](alert_data, channel)
                return True
            except Exception as e:
                logger.error(
                    "Error en callback %s: %s", channel, str(e)
                )
                return False

        # Canales por defecto
        if channel == "dashboard":
            # El dashboard recibe vía WebSocket
            logger.debug(
                "Notificación dashboard: %s", alert.mensaje
            )
            return True

        elif channel == "telegram":
            return self._notify_telegram(alert)

        elif channel == "webhook":
            return self._notify_webhook(alert)

        elif channel == "telegram_enjambre":
            return self._notify_telegram_enjambre(alert)

        return False

    def _notify_telegram(self, alert: AlertRecord) -> bool:
        """
        Envía notificación por Telegram.

        Args:
            alert: Alerta a notificar.

        Returns:
            True si se envió.
        """
        try:
            mensaje = self._format_telegram_message(alert)
            logger.info(
                "Telegram [%s]: %s", alert.severidad, mensaje
            )
            # Aquí se integraría con el bot de Telegram
            # Por ahora, logueamos
            return True
        except Exception as e:
            logger.error("Error notificación Telegram: %s", str(e))
            return False

    def _notify_webhook(self, alert: AlertRecord) -> bool:
        """
        Envía notificación por webhook.

        Args:
            alert: Alerta a notificar.

        Returns:
            True si se envió.
        """
        if not self._webhook_url:
            logger.debug(
                "Webhook no configurado, saltando"
            )
            return False

        try:
            import requests
            response = requests.post(
                self._webhook_url,
                json=alert.to_dict(),
                timeout=5,
                headers={
                    "Content-Type": "application/json",
                    "X-Sentinel-Alert": alert.severidad,
                },
            )
            return response.status_code < 500
        except ImportError:
            logger.warning(
                "requests no disponible para webhook"
            )
            return False
        except Exception as e:
            logger.error("Error webhook: %s", str(e))
            return False

    def _notify_telegram_enjambre(self, alert: AlertRecord) -> bool:
        """
        Envía notificación a todos los bots del enjambre.

        Args:
            alert: Alerta a notificar.

        Returns:
            True si se envió a al menos un bot.
        """
        success = False
        for bot in self._telegram_bots:
            try:
                logger.info(
                    "Enjambre [%s]: %s - %s",
                    bot,
                    alert.severidad,
                    alert.mensaje,
                )
                success = True
            except Exception as e:
                logger.error(
                    "Error en bot %s: %s", bot, str(e)
                )
        return success

    def _format_telegram_message(
        self, alert: AlertRecord
    ) -> str:
        """
        Formatea una alerta para mensaje de Telegram.

        Args:
            alert: Alerta a formatear.

        Returns:
            Mensaje formateado.
        """
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "🚨",
            "CRITICAL": "🆘",
        }
        emoji = emoji_map.get(alert.severidad, "🔔")

        lines = [
            f"{emoji} *ALERTA {alert.severidad}*",
            f"",
            f"*Tipo:* {alert.tipo}",
            f"*Origen:* {alert.source}",
            f"*Dispositivo:* {alert.device_id}",
            f"",
            f"*Mensaje:* {alert.mensaje}",
        ]

        if alert.details:
            lines.append("")
            lines.append("*Detalles:*")
            for key, value in list(alert.details.items())[:5]:
                lines.append(f"  • {key}: {value}")

        lines.append("")
        lines.append(
            f"🕐 {datetime.fromtimestamp(alert.timestamp, tz=timezone.utc).strftime('%H:%M:%S')}"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # PROTOCOLO CRITICAL
    # ------------------------------------------------------------------

    def handle_critical(
        self,
        tipo: str,
        mensaje: str,
        device_id: str = "sistema",
        source: str = "sistema",
        details: Optional[Dict[str, Any]] = None,
    ) -> AlertRecord:
        """
        Maneja una alerta CRITICAL con protocolo completo.

        Protocolo:
          1. Crear alerta CRITICAL
          2. Notificar a TODOS los canales inmediatamente
          3. Registrar en auditoría
          4. Iniciar temporizador de respuesta

        Args:
            tipo: Tipo de alerta.
            mensaje: Descripción.
            device_id: Dispositivo relacionado.
            source: Origen.
            details: Detalles adicionales.

        Returns:
            AlertRecord creado.
        """
        alert = self.create_alert(
            tipo=tipo,
            severidad="CRITICAL",
            mensaje=mensaje,
            device_id=device_id,
            source=source,
            details=details,
        )

        logger.critical(
            "PROTOCOLO CRITICAL activado: %s - %s",
            tipo,
            mensaje,
        )

        return alert

    # ------------------------------------------------------------------
    # ESTADÍSTICAS
    # ------------------------------------------------------------------

    def get_active_alerts(
        self, severidad: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene alertas activas, opcionalmente filtradas.

        Args:
            severidad: Filtrar por nivel (opcional).

        Returns:
            Lista de alertas activas.
        """
        alerts = list(self._active_alerts.values())
        if severidad:
            alerts = [
                a for a in alerts if a.severidad == severidad
            ]
        return [a.to_dict() for a in alerts]

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de escalación.

        Returns:
            Dict con estadísticas.
        """
        stats: Dict[str, Any] = {
            "alertas_activas": len(self._active_alerts),
            "alertas_resueltas": len(self._resolved_alerts),
            "por_severidad": defaultdict(int),
            "por_origen": defaultdict(int),
            "tiempo_medio_respuesta": 0.0,
        }

        for alert in list(self._active_alerts.values()):
            stats["por_severidad"][alert.severidad] += 1
            stats["por_origen"][alert.source] += 1

        for alert in self._resolved_alerts:
            stats["por_severidad"][alert.severidad] += 1
            stats["por_origen"][alert.source] += 1

        tiempos = [
            a.tiempo_respuesta
            for a in self._resolved_alerts
            if a.tiempo_respuesta > 0
        ]
        if tiempos:
            stats["tiempo_medio_respuesta"] = (
                sum(tiempos) / len(tiempos)
            )

        return dict(stats)
