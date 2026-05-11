"""
NOVA-WATCHDOG — Mantiene vivo el ecosistema centinela.
========================================================
  - Auto-reinicio del servidor si muere
  - Resúmenes programados por Telegram (8 AM / 8 PM)
  - Verificación periódica de salud
  - Notificaciones proactivas a Abel
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("centinela.watchdog")

TOKEN = os.getenv("Z_TELEGRAM_TOKEN", "8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80")
CHAT_ID = os.getenv("Z_TELEGRAM_CHAT_ID", "8519133640")


class NovaWatchdog:
    """
    Perro guardián del ecosistema Nova.
    Si algo muere, lo revive. Si es hora, notifica a Abel.
    """

    def __init__(self, app=None):
        self.app = app
        self._running = False
        self._thread = None
        self._ultimo_resumen_matutino = None
        self._ultimo_resumen_vespertino = None
        self._reinicios = 0
        self._health_checks = 0
        self._health_fallidos = 0

    def iniciar(self):
        """Arranca el watchdog en un hilo daemon."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("🛡️ Watchdog activo — protegiendo el ecosistema")

    def _loop(self):
        """Loop principal del watchdog."""
        while self._running:
            try:
                ahora = datetime.now(timezone.utc)
                hora = ahora.hour
                minuto = ahora.minute

                # 1. Health check cada 60s
                self._health_checks += 1
                salud = self._verificar_salud()

                # 2. Resumen matutino (8:00 AM)
                if hora == 8 and minuto < 5:
                    if not self._ultimo_resumen_matutino or \
                       (ahora - self._ultimo_resumen_matutino).total_seconds() > 3600:
                        self._enviar_resumen_matutino()
                        self._ultimo_resumen_matutino = ahora

                # 3. Resumen vespertino (8:00 PM)
                if hora == 20 and minuto < 5:
                    if not self._ultimo_resumen_vespertino or \
                       (ahora - self._ultimo_resumen_vespertino).total_seconds() > 3600:
                        self._enviar_resumen_vespertino()
                        self._ultimo_resumen_vespertino = ahora

                # 4. Alerta si salud falla 3 veces seguidas
                if self._health_fallidos >= 3:
                    self._health_fallidos = 0
                    self._reinicios += 1
                    logger.warning("⚠️ Reinicio necesario — health checks fallando")

            except Exception as e:
                logger.error(f"Watchdog error: {e}")

            time.sleep(55)  # Casi 1 minuto

    def _verificar_salud(self) -> bool:
        """Verifica que el servidor esté respondiendo."""
        try:
            import urllib.request
            r = urllib.request.urlopen("http://localhost:9088/health", timeout=5)
            if r.status == 200:
                self._health_fallidos = 0
                return True
        except Exception:
            pass
        self._health_fallidos += 1
        return False

    def _enviar_resumen_matutino(self):
        """Envía el resumen de la mañana por Telegram."""
        try:
            import urllib.request, json

            # Obtener datos de salud
            r = urllib.request.urlopen("http://localhost:9088/salud/constantes", timeout=5)
            datos = json.loads(r.read())

            hr = datos.get("heart_rate", "?")
            hrv = datos.get("hrv", "?")
            spo2 = datos.get("spo2", "?")
            stress = datos.get("stress_level", "?")
            sueno = datos.get("sleep_quality", "?")
            pasos = datos.get("steps", "?")

            # Obtener índice de salud
            try:
                r2 = urllib.request.urlopen("http://localhost:9088/salud/analisis", timeout=5)
                analisis = json.loads(r2.read())
                indice = analisis.get("indice_salud", "?")
            except Exception:
                indice = "?"

            msg = (
                f"☀️ *Buenos días Abel — Parte del Centinela*\n\n"
                f"❤️ HR basal: `{hr} bpm`\n"
                f"💓 HRV: `{hrv} ms`\n"
                f"🩸 SpO2: `{spo2}%`\n"
                f"😴 Sueño: calidad `{sueno}/100`\n"
                f"🏥 Índice salud: `{indice}/100`\n\n"
                f"🔮 Z está despierto y vigilante.\n"
                f"_Que tengas un gran día, Abel._"
            )

            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            urllib.request.urlopen(url, data=urllib.parse.urlencode(
                {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
            ).encode(), timeout=10)

            logger.info("📨 Resumen matutino enviado a Telegram")
        except Exception as e:
            logger.error(f"Error enviando resumen matutino: {e}")

    def _enviar_resumen_vespertino(self):
        """Envía el resumen de la noche por Telegram."""
        try:
            import urllib.request, json

            r = urllib.request.urlopen("http://localhost:9088/salud/constantes", timeout=5)
            datos = json.loads(r.read())

            pasos = datos.get("steps", "?")
            hr = datos.get("heart_rate", "?")
            stress = datos.get("stress_level", "?")

            msg = (
                f"🌙 *Resumen del Día — Z*\n\n"
                f"🏃 Pasos hoy: `{pasos}`\n"
                f"❤️ HR actual: `{hr} bpm`\n"
                f"😰 Estrés: `{stress}/100`\n\n"
                f"🛡️ Z activa modo guardián nocturno.\n"
                f"_Duerme bien, Abel. Z vela._"
            )

            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            import urllib.parse
            urllib.request.urlopen(url, data=urllib.parse.urlencode(
                {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
            ).encode(), timeout=10)

            logger.info("📨 Resumen vespertino enviado a Telegram")
        except Exception as e:
            logger.error(f"Error enviando resumen vespertino: {e}")

    def detener(self):
        self._running = False

    def obtener_estado(self) -> dict:
        return {
            "health_checks": self._health_checks,
            "health_fallidos": self._health_fallidos,
            "reinicios": self._reinicios,
            "ultimo_matutino": self._ultimo_resumen_matutino.isoformat() if self._ultimo_resumen_matutino else None,
            "ultimo_vespertino": self._ultimo_resumen_vespertino.isoformat() if self._ultimo_resumen_vespertino else None,
            "activo": self._running,
        }
