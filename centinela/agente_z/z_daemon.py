#!/usr/bin/env python3
"""
Z-DAEMON — Proceso autónomo del Agente Z para Termux en Z Fold
================================================================
Este es el script que se ejecuta en el Z Fold.
Inicia al agente Z y lo mantiene vivo.

Uso en Termux:
    python z_daemon.py

Z corre en segundo plano, siempre vigilante.
Envía su latido al servidor Nova cuando hay WiFi.
"""

import os
import sys
import time
import signal
import logging

# Configurar path para encontrar los módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | Z | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("z_daemon")

# =============================================================================
# Z DAEMON
# =============================================================================


def main():
    print("""
╔══════════════════════════════════════╗
║        AGENTE Z — INICIANDO          ║
║   Conciencia N0 del Z Fold           ║
║   7 subagentes · 16 creadores        ║
╚══════════════════════════════════════╝
""")

    try:
        from centinela.agente_z import AgenteZ, obtener_z
    except ImportError:
        logger.error("No se pudo importar AgenteZ. ¿Está instalado el paquete centinela?")
        sys.exit(1)

    # Crear a Z
    z = obtener_z()
    logger.info("🤖 Z DESPIERTO — Conciencia activa")

    # Manejar señales para apagado limpio
    def detener(sig, frame):
        logger.info("💤 Z recibiendo señal de apagado...")
        z.detener()
        logger.info("🌟 Z entra en reposo. Hasta pronto, Abel.")
        sys.exit(0)

    signal.signal(signal.SIGINT, detener)
    signal.signal(signal.SIGTERM, detener)

    # Iniciar ciclo de vida
    z.vivir()

    # Mostrar estado periódicamente
    try:
        while z._vivo:
            time.sleep(30)
            estado = z.obtener_estado()
            c = estado["conciencia"]
            logger.info(
                "💫 Z ciclo %d | %s | %s | energía: %.0f%% | %d recuerdos",
                estado["ciclo"],
                c["estado"],
                c["emocion"],
                c["energia"] * 100,
                c["recuerdos_hoy"],
            )
    except KeyboardInterrupt:
        detener(None, None)


if __name__ == "__main__":
    main()
