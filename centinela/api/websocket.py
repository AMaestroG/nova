"""
WebSocket para streaming en tiempo real del Sistema Centinela
Nova Homonexus - MAYORDOMO
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Set, Dict, Any

from flask import current_app
from flask_sock import Sock

from centinela.config import WEBSOCKET_CONFIG, SECURITY

logger = logging.getLogger("centinela.websocket")

# Almacén de conexiones WebSocket activas
# { "sensor": set(ws), "health": set(ws), ... }
ws_clients: Dict[str, set] = {}
ws_clients_all: set = set()


def init_websocket(app, sock: Sock):
    """Inicializa los endpoints WebSocket en la aplicación Flask."""

    @sock.route("/ws/centinela")
    def centinela_ws(ws):
        """Canal WebSocket principal para streaming en tiempo real."""
        client_id = id(ws)
        logger.info("Cliente WebSocket conectado: %s", client_id)

        # Autenticación
        api_key = ws.receive(timeout=5)
        if SECURITY["api_key_required"] and api_key != SECURITY["api_key"]:
            ws.send(json.dumps({
                "error": "Autenticacion fallida",
                "codigo": "AUTH_FAILED",
            }))
            ws.close()
            return

        # Registrar cliente
        ws_clients_all.add(ws)
        subs = set()

        try:
            # Enviar confirmación
            ws.send(json.dumps({
                "tipo": "conectado",
                "mensaje": "Conectado al Sistema Centinela",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "canales_disponibles": [
                    "sensor", "ubicacion", "health", "emocion",
                    "alerta", "evento", "sesion", "todo",
                ],
            }))

            # Bucle principal de mensajes
            while True:
                mensaje = ws.receive(timeout=WEBSOCKET_CONFIG["ping_interval"])

                if mensaje is None:
                    continue

                try:
                    data = json.loads(mensaje)
                except json.JSONDecodeError:
                    ws.send(json.dumps({
                        "tipo": "error",
                        "mensaje": "Formato JSON invalido",
                    }))
                    continue

                accion = data.get("accion")

                if accion == "suscribir":
                    canal = data.get("canal", "todo")
                    if canal == "todo":
                        subs = {"sensor", "ubicacion", "health", "emocion",
                                "alerta", "evento", "sesion"}
                    else:
                        subs.add(canal)
                    ws.send(json.dumps({
                        "tipo": "suscripcion",
                        "canales": list(subs),
                        "mensaje": f"Suscrito a {len(subs)} canales",
                    }))

                elif accion == "unsuscribir":
                    canal = data.get("canal")
                    if canal in subs:
                        subs.discard(canal)
                    ws.send(json.dumps({
                        "tipo": "suscripcion",
                        "canales": list(subs),
                    }))

                elif accion == "ping":
                    ws.send(json.dumps({
                        "tipo": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }))

                elif accion == "listar_canales":
                    ws.send(json.dumps({
                        "tipo": "canales",
                        "canales": list(subs) if subs else ["ninguno"],
                    }))

                else:
                    ws.send(json.dumps({
                        "tipo": "error",
                        "mensaje": f"Accion desconocida: {accion}",
                    }))

        except Exception as e:
            logger.debug("Cliente WebSocket %s desconectado: %s", client_id, str(e))
        finally:
            ws_clients_all.discard(ws)
            logger.info("Cliente WebSocket desconectado: %s", client_id)


def emitir_evento(tipo: str, datos: Dict[str, Any]):
    """
    Emite un evento a todos los clientes WebSocket suscritos.
    Esta función puede ser llamada desde cualquier parte del sistema.
    """
    if not ws_clients_all:
        return

    mensaje = json.dumps({
        "tipo": tipo,
        "datos": datos,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Enviar a todos los clientes conectados
    desconectados = set()
    for ws in ws_clients_all:
        try:
            ws.send(mensaje)
        except Exception:
            desconectados.add(ws)

    # Limpiar clientes desconectados
    ws_clients_all.difference_update(desconectados)
