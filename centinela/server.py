#!/usr/bin/env python3
"""
NOVA CENTINELA — Servidor de Producción
=========================================
Usa Waitress (WSGI production-grade) en lugar del dev server de Flask.
No se cae. No se queja. Simplemente sirve.

Ejecutar:
  python server.py
  o
  systemctl start nova-centinela
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("Z_TELEGRAM_TOKEN", "8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80")
os.environ.setdefault("Z_TELEGRAM_CHAT_ID", "8519133640")

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("centinela.server")

from centinela.app import create_app
from waitress import serve

app = create_app()

logger.warning("🚀 Nova Centinela — Production Server (Waitress)")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║   NOVA CENTINELA — PRODUCTION        ║
║   Waitress WSGI :9088                 ║
║   No muere. No se queja.              ║
╚══════════════════════════════════════╝
""")
    serve(app, host="0.0.0.0", port=9088, threads=4, 
          connection_limit=100, channel_timeout=120)
