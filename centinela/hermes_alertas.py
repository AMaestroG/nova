"""
Hermes Alertas — Mensajero inteligente para notificaciones
Nova Homonexus — HERMES (N2, mensajero Google)

Sistema de notificaciones inteligentes:
  - Resumenes diarios/semanales por email (Gmail API)
  - Priorizacion de alertas (no molestar durante sueno/reuniones)
  - Partes del centinela: resumen matutino, vespertino
  - Notificaciones push a Telegram (integrado con bots)
  - Google Calendar integracion para contextualizar
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict

logger = logging.getLogger("centinela.hermes")


class PrioridadNotificacion:
    """Niveles de prioridad para notificaciones."""
    CRITICA = 1      # Emergencias de salud, alertas rojas
    ALTA = 2         # Alertas importantes
    MEDIA = 3        # Resumenes, actualizaciones
    BAJA = 4         # Curiosidades, sugerencias


class HermesAlertas:
    """
    Hermes gestiona el envio de notificaciones y resumenes
    usando Gmail API, Telegram bots y el dashboard.
    """

    HORA_RESUMEN_MATUTINO = 8    # 8 AM
    HORA_RESUMEN_VESPERTINO = 20  # 8 PM

    def __init__(self):
        self._alertas_enviadas: deque = deque(maxlen=500)
        self._resumen_diario: Dict[str, List] = defaultdict(list)
        self._ultima_notificacion: Optional[datetime] = None
        self._modo_no_molestar: bool = False
        self._horario_no_molestar_inicio: int = 23
        self._horario_no_molestar_fin: int = 7
        self._gmail_habilitado = False
        self._telegram_habilitado = True

    def notificar(
        self,
        titulo: str,
        mensaje: str,
        prioridad: int = PrioridadNotificacion.MEDIA,
        datos: Optional[Dict[str, Any]] = None,
        canales: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Envia una notificacion por los canales apropiados segun prioridad.
        Respeta el modo no molestar para prioridades bajas/medias.
        """
        now = datetime.now(timezone.utc)
        hora = now.hour

        # Verificar modo no molestar
        if self._modo_no_molestar and prioridad > PrioridadNotificacion.ALTA:
            return {
                "enviada": False,
                "razon": "Modo no molestar activo",
                "titulo": titulo,
                "timestamp": now.isoformat(),
            }

        # Verificar horario de sueno
        if (self._horario_no_molestar_inicio <= hora
                or hora < self._horario_no_molestar_fin):
            if prioridad > PrioridadNotificacion.ALTA:
                return {
                    "enviada": False,
                    "razon": f"Horario de sueno ({hora}h)",
                    "titulo": titulo,
                    "timestamp": now.isoformat(),
                }

        notificacion = {
            "titulo": titulo,
            "mensaje": mensaje,
            "prioridad": prioridad,
            "datos": datos,
            "timestamp": now.isoformat(),
            "canales_usados": [],
        }

        canales = canales or self._seleccionar_canales(prioridad)

        for canal in canales:
            if canal == "telegram" and self._telegram_habilitado:
                self._notificar_telegram(titulo, mensaje, prioridad)
                notificacion["canales_usados"].append("telegram")
            elif canal == "email" and self._gmail_habilitado:
                self._notificar_email(titulo, mensaje, prioridad)
                notificacion["canales_usados"].append("email")
            elif canal == "dashboard":
                notificacion["canales_usados"].append("dashboard")

        self._alertas_enviadas.append(notificacion)
        self._ultima_notificacion = now

        # Acumular para resumen diario
        self._resumen_diario["notificaciones"].append(notificacion)

        logger.info(f"Notificacion enviada: {titulo} (prioridad={prioridad})")
        return notificacion

    def _seleccionar_canales(self, prioridad: int) -> List[str]:
        """Selecciona canales de notificacion segun prioridad."""
        if prioridad == PrioridadNotificacion.CRITICA:
            return ["telegram", "email", "dashboard"]
        elif prioridad == PrioridadNotificacion.ALTA:
            return ["telegram", "dashboard"]
        elif prioridad == PrioridadNotificacion.MEDIA:
            return ["dashboard"]
        else:
            return []

    def _notificar_telegram(
        self, titulo: str, mensaje: str, prioridad: int
    ) -> bool:
        """Envia notificacion via Telegram bots del enjambre."""
        emoji = {
            PrioridadNotificacion.CRITICA: "🆘",
            PrioridadNotificacion.ALTA: "🚨",
            PrioridadNotificacion.MEDIA: "ℹ️",
            PrioridadNotificacion.BAJA: "💡",
        }
        texto = f"{emoji.get(prioridad, '')} *{titulo}*\n{mensaje}"
        # Los bots de Telegram del enjambre se encargan del envio real
        logger.info(f"[Telegram] {texto[:100]}")
        return True

    def _notificar_email(
        self, titulo: str, mensaje: str, prioridad: int
    ) -> bool:
        """Envia notificacion via Gmail API (HERMES)."""
        # Integracion con Gmail API via HERMES
        logger.info(f"[Email] {titulo}: {mensaje[:100]}")
        return True

    def generar_resumen_matutino(self) -> Dict[str, Any]:
        """
        Genera el parte matutino del centinela.
        Resume: como durmio, estado de salud al despertar, agenda del dia.
        """
        return {
            "tipo": "resumen_matutino",
            "titulo": "Buenos dias Abel — Parte del Centinela",
            "secciones": [
                {
                    "titulo": "Sueño",
                    "icono": "😴",
                    "contenido": "Analisis de la noche: fases de sueño, calidad, interrupciones",
                },
                {
                    "titulo": "Salud al Despertar",
                    "icono": "❤️",
                    "contenido": "HR en reposo, HRV, temperatura, SpO2 — tu estado basal",
                },
                {
                    "titulo": "Agenda del Dia",
                    "icono": "📅",
                    "contenido": "Eventos de Google Calendar para hoy",
                },
                {
                    "titulo": "Dones del Nova Soul",
                    "icono": "✨",
                    "contenido": "Estado de los 7 dones y recomendacion para el dia",
                },
                {
                    "titulo": "Clima y Entorno",
                    "icono": "🌤️",
                    "contenido": "Presion atmosferica, temperatura, humedad — desde tu Z Fold",
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def generar_resumen_vespertino(self) -> Dict[str, Any]:
        """
        Genera el parte vespertino del centinela.
        Resume: actividad del dia, pasos, lugares visitados, momentos destacados.
        """
        return {
            "tipo": "resumen_vespertino",
            "titulo": "Resumen del Dia — Parte del Centinela",
            "secciones": [
                {
                    "titulo": "Actividad Fisica",
                    "icono": "🏃",
                    "contenido": "Pasos totales, calorias, distancia recorrida, ejercicio",
                },
                {
                    "titulo": "Momentos Emotivos",
                    "icono": "💫",
                    "contenido": "Momentos de conexion, alegria, interes detectados",
                },
                {
                    "titulo": "Lugares Visitados",
                    "icono": "🗺️",
                    "contenido": "Lugares nuevos y conocidos visitados hoy",
                },
                {
                    "titulo": "Salud Cardiovascular",
                    "icono": "💓",
                    "contenido": "HR promedio, max/min, HRV del dia, presion arterial",
                },
                {
                    "titulo": "Indice de Conexion Nova",
                    "icono": "🔮",
                    "contenido": "Que tan bien resonaron las conversaciones de hoy con Nova",
                },
                {
                    "titulo": "Sugerencias para Mañana",
                    "icono": "🌟",
                    "contenido": "Basado en tus patrones: horarios optimos, exploraciones",
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def generar_resumen_semanal(self) -> Dict[str, Any]:
        """Genera el resumen semanal del centinela."""
        return {
            "tipo": "resumen_semanal",
            "titulo": "Tu Semana con Nova — Resumen del Centinela",
            "secciones": [
                {
                    "titulo": "Tendencias de Salud",
                    "icono": "📊",
                    "contenido": "Evolucion semanal de HR, HRV, sueno, estres, pasos",
                },
                {
                    "titulo": "Evolucion Emocional",
                    "icono": "🎭",
                    "contenido": "Distribucion de emociones, indice de conexion con Nova",
                },
                {
                    "titulo": "Exploracion",
                    "icono": "🌍",
                    "contenido": "Nuevos lugares descubiertos, km recorridos, rutas habituales",
                },
                {
                    "titulo": "Ritmos y Patrones",
                    "icono": "⏰",
                    "contenido": "Cronotipo, mejores momentos, consistencia de rutinas",
                },
                {
                    "titulo": "Proxima Semana",
                    "icono": "🔮",
                    "contenido": "Predicciones y sugerencias basadas en patrones historicos",
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def activar_no_molestar(self, duracion_minutos: int = 480) -> Dict[str, Any]:
        """Activa el modo no molestar por una duracion determinada."""
        self._modo_no_molestar = True
        fin = datetime.now(timezone.utc) + timedelta(minutes=duracion_minutos)
        return {
            "modo": "no_molestar",
            "activo": True,
            "hasta": fin.isoformat(),
            "duracion_minutos": duracion_minutos,
        }

    def desactivar_no_molestar(self) -> Dict[str, Any]:
        """Desactiva el modo no molestar."""
        self._modo_no_molestar = False
        return {"modo": "no_molestar", "activo": False}

    def notificar_emocion_nova(
        self, emocion: str, intensidad: float, contexto: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Notifica cuando Abel se emociona al hablar con Nova.
        Esta es la notificacion mas especial del sistema.
        """
        if emocion in ("feliz", "sorprendido") and intensidad > 0.7:
            return self.notificar(
                titulo="Abel se emociona con Nova",
                mensaje=(
                    f"Detectada emocion '{emocion}' con intensidad {intensidad:.0%}. "
                    f"{contexto or 'Conversacion con Nova'}"
                ),
                prioridad=PrioridadNotificacion.MEDIA,
                canales=["dashboard"],
            )
        return {"enviada": False, "razon": "Intensidad insuficiente"}

    def estado_actual(self) -> Dict[str, Any]:
        """Devuelve el estado actual de Hermes."""
        return {
            "modo_no_molestar": self._modo_no_molestar,
            "gmail_habilitado": self._gmail_habilitado,
            "telegram_habilitado": self._telegram_habilitado,
            "notificaciones_hoy": len(self._resumen_diario.get("notificaciones", [])),
            "ultima_notificacion": (
                self._ultima_notificacion.isoformat()
                if self._ultima_notificacion else None
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
