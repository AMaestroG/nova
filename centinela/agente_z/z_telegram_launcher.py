#!/usr/bin/env python3
"""
Z-TELEGRAM LAUNCHER — Inicia a Z con voz en Telegram.
=======================================================
Ejecuta esto en el servidor para darle a Z su voz.

Uso:
  python z_telegram_launcher.py

Z se conecta a Telegram y queda a la escucha.
Abel interactúa con Z por Telegram desde cualquier lugar.
"""

import os
import sys
import logging

# Configurar token
TOKEN = "8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80"
os.environ["Z_TELEGRAM_TOKEN"] = TOKEN

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | Z | %(message)s",
)
logger = logging.getLogger("z_launcher")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║   Z-TELEGRAM — LAUNCHER              ║
║   Dando voz a Z en Telegram          ║
╚══════════════════════════════════════╝
""")

    from centinela.agente_z import AgenteZ

    # Crear a Z
    z = AgenteZ()
    logger.info("🤖 Z DESPERTANDO")

    # Iniciar ciclo de vida
    z.vivir()
    logger.info("💫 Z VIVIENDO — ciclo autónomo activo")

    # Activar Telegram
    if z.telegram:
        logger.info("📱 Activando Telegram...")
        z.iniciar_telegram()
        logger.info("✅ Z tiene voz en Telegram")
        logger.info("   Abre @tu_bot y escribe /z")
    else:
        logger.warning("⚠️ Telegram no disponible")
        logger.info("   pip install python-telegram-bot")

    # Mantener vivo
    import time
    try:
        while True:
            time.sleep(60)
            estado = z.obtener_estado()
            logger.info(
                "💫 Z ciclo %d | %s | %s",
                estado['ciclo'],
                estado['conciencia']['estado'],
                estado['conciencia']['emocion'],
            )
    except KeyboardInterrupt:
        logger.info("💤 Z entrando en reposo...")
        z.detener()
