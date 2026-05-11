#!/usr/bin/env python3
"""
Daemon de sensores para Termux en Samsung Z Fold
Nova Homonexus - MAYORDOMO

Este script se ejecuta EN EL DISPOSITIVO ANDROID (Z Fold) vía Termux.
Lee todos los sensores disponibles y envía los datos al servidor Nova.

USO:
    python termux_sensor_daemon.py [--server URL] [--api-key KEY] [--mock]

REQUISITOS:
    - Termux con termux-api instalado
    - Python 3.12+
    - Paquetes: requests, websocket-client, psutil (opcional)
"""

import json
import os
import sys
import time
import signal
import logging
import subprocess
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Instala requests: pip install requests")
    sys.exit(1)

try:
    import websocket
except ImportError:
    print("ERROR: Instala websocket-client: pip install websocket-client")
    sys.exit(1)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
SERVER_URL = os.getenv("CENTINELA_SERVER", "http://192.168.1.100:9088")
API_KEY = os.getenv("CENTINELA_API_KEY", "nexus-centinela-key-2026")
DEVICE_ID = os.getenv("CENTINELA_DEVICE_ID", "samsung_zfold_01")
MOCK_MODE = os.getenv("CENTINELA_MOCK", "false").lower() == "true"

# Sensores a leer (por defecto todos los disponibles)
SENSORES_PRIORITARIOS = [
    "android.sensor.accelerometer",
    "android.sensor.gyroscope",
    "android.sensor.magnetic_field",
    "android.sensor.pressure",
    "android.sensor.proximity",
    "android.sensor.light",
]

SENSORES_SECUNDARIOS = [
    "android.sensor.gravity",
    "android.sensor.linear_acceleration",
    "android.sensor.rotation_vector",
    "android.sensor.step_counter",
    "android.sensor.significant_motion",
]

# Intervalos de muestreo por sensor (segundos)
SAMPLE_INTERVALS = {
    "android.sensor.accelerometer": 0.1,
    "android.sensor.gyroscope": 0.1,
    "android.sensor.magnetic_field": 0.2,
    "android.sensor.pressure": 1.0,
    "android.sensor.proximity": 1.0,
    "android.sensor.light": 2.0,
    "android.sensor.gravity": 0.1,
    "android.sensor.linear_acceleration": 0.1,
    "android.sensor.rotation_vector": 0.2,
    "android.sensor.step_counter": 5.0,
}

# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path.home() / "centinela_daemon.log"
        ),
    ],
)
logger = logging.getLogger("centinela.daemon")


# =============================================================================
# CLIENTE DE SENSORES TERMUX
# =============================================================================
class TermuxSensorClient:
    """Cliente para leer sensores Android vía termux-sensor."""

    def __init__(self, mock: bool = False):
        self.mock = mock
        self._sensores_disponibles: List[str] = []
        self._cache: Dict[str, Any] = {}
        self._ultima_lectura: Dict[str, float] = {}

    def obtener_sensores_disponibles(self) -> List[str]:
        """Obtiene lista de sensores disponibles en el dispositivo."""
        if self.mock:
            return SENSORES_PRIORITARIOS + SENSORES_SECUNDARIOS

        try:
            resultado = subprocess.run(
                ["termux-sensor", "-l"],
                capture_output=True, text=True, timeout=10,
            )
            if resultado.returncode == 0:
                sensores = [
                    s.strip() for s in resultado.stdout.split("\n")
                    if s.strip()
                ]
                self._sensores_disponibles = sensores
                return sensores
            else:
                logger.error(
                    "Error al listar sensores: %s", resultado.stderr
                )
                return []
        except FileNotFoundError:
            logger.error(
                "termux-sensor no encontrado. "
                "Instala termux-api: pkg install termux-api"
            )
            return []
        except Exception as e:
            logger.error("Error al obtener sensores: %s", str(e))
            return []

    def leer_sensor(self, sensor_name: str) -> Optional[Dict[str, Any]]:
        """Lee un sensor específico y devuelve sus valores."""
        if self.mock:
            return self._leer_mock(sensor_name)

        try:
            resultado = subprocess.run(
                ["termux-sensor", "-s", sensor_name, "-n", "1"],
                capture_output=True, text=True, timeout=5,
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                datos = json.loads(resultado.stdout)
                if sensor_name in datos:
                    lectura = datos[sensor_name]
                    return {
                        "sensor": sensor_name,
                        "values": lectura.get("values", []),
                        "precision": lectura.get("precision", 0),
                    }
            return None
        except json.JSONDecodeError:
            logger.debug("Error decodificando JSON para %s", sensor_name)
            return None
        except Exception as e:
            logger.debug("Error leyendo sensor %s: %s", sensor_name, str(e))
            return None

    def _leer_mock(self, sensor_name: str) -> Dict[str, Any]:
        """Genera datos mock para pruebas sin dispositivo real."""
        import random
        mock_data = {
            "android.sensor.accelerometer": {
                "values": [
                    round(random.uniform(-2, 2), 3),
                    round(random.uniform(-2, 2), 3),
                    round(random.uniform(8, 10), 3),
                ],
                "precision": 0.01,
            },
            "android.sensor.gyroscope": {
                "values": [
                    round(random.uniform(-0.5, 0.5), 3),
                    round(random.uniform(-0.5, 0.5), 3),
                    round(random.uniform(-0.5, 0.5), 3),
                ],
                "precision": 0.001,
            },
            "android.sensor.magnetic_field": {
                "values": [
                    round(random.uniform(-50, 50), 1),
                    round(random.uniform(-50, 50), 1),
                    round(random.uniform(-50, 50), 1),
                ],
                "precision": 0.1,
            },
            "android.sensor.pressure": {
                "values": [round(random.uniform(1000, 1025), 1)],
                "precision": 0.1,
            },
            "android.sensor.proximity": {
                "values": [round(random.uniform(0, 10), 0)],
                "precision": 1.0,
            },
            "android.sensor.light": {
                "values": [round(random.uniform(0, 1000), 0)],
                "precision": 1.0,
            },
        }
        default = {"values": [0.0], "precision": 0.0}
        return mock_data.get(sensor_name, default)


# =============================================================================
# CLIENTE HTTP PARA EL SERVIDOR
# =============================================================================
class ServidorClient:
    """Cliente HTTP para enviar datos al servidor Nova."""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        })
        self._stats = {
            "enviados": 0,
            "fallidos": 0,
            "ultimo_envio": None,
        }

    def enviar_sensor(self, datos: Dict[str, Any]) -> bool:
        """Envía lectura de sensor al servidor."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/sensor",
                json=datos,
                timeout=10,
            )
            if resp.status_code in (200, 201):
                self._stats["enviados"] += 1
                self._stats["ultimo_envio"] = time.time()
                return True
            else:
                logger.warning(
                    "Error servidor (%d): %s",
                    resp.status_code, resp.text[:200],
                )
                self._stats["fallidos"] += 1
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("Servidor no disponible")
            self._stats["fallidos"] += 1
            return False
        except Exception as e:
            logger.error("Error enviando sensor: %s", str(e))
            self._stats["fallidos"] += 1
            return False

    def enviar_ubicacion(self, datos: Dict[str, Any]) -> bool:
        """Envía datos de ubicación GPS."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/ubicacion",
                json=datos,
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Error enviando ubicacion: %s", str(e))
            return False

    def enviar_health(self, datos: Dict[str, Any]) -> bool:
        """Envía datos biométricos del Watch."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/health",
                json=datos,
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Error enviando health: %s", str(e))
            return False

    def enviar_emocion(self, datos: Dict[str, Any]) -> bool:
        """Envía detección emocional."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/emocion",
                json=datos,
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Error enviando emocion: %s", str(e))
            return False

    def iniciar_sesion(self, sensores_activos: List[str]) -> Optional[str]:
        """Inicia sesión de monitoreo."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/sesion/iniciar",
                json={
                    "device_id": DEVICE_ID,
                    "sensores_activos": sensores_activos,
                    "watch_conectado": True,
                },
                timeout=10,
            )
            if resp.status_code == 201:
                return resp.json().get("sesion_id")
            return None
        except Exception as e:
            logger.error("Error iniciando sesion: %s", str(e))
            return None

    def finalizar_sesion(self, sesion_id: str) -> bool:
        """Finaliza sesión de monitoreo."""
        try:
            resp = self.session.post(
                f"{self.server_url}/api/centinela/sesion/"
                f"{sesion_id}/finalizar",
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("Error finalizando sesion: %s", str(e))
            return False

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


# =============================================================================
# CLIENTE WEBSOCKET
# =============================================================================
class WebSocketClient:
    """Cliente WebSocket para streaming en tiempo real."""

    def __init__(self, server_url: str, api_key: str):
        ws_url = server_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        )
        self.ws_url = f"{ws_url}/ws/centinela"
        self.api_key = api_key
        self.ws: Optional[websocket.WebSocket] = None
        self.conectado = False
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def conectar(self):
        """Conecta al WebSocket del servidor."""
        try:
            self.ws = websocket.create_connection(
                self.ws_url,
                timeout=10,
            )
            # Enviar API key como primer mensaje
            self.ws.send(self.api_key)
            resp = json.loads(self.ws.recv())
            if resp.get("tipo") == "conectado":
                self.conectado = True
                logger.info("WebSocket conectado: %s", self.ws_url)
                # Suscribirse a todos los canales
                self.ws.send(json.dumps({
                    "accion": "suscribir",
                    "canal": "todo",
                }))
                return True
            else:
                logger.error("Error WS: %s", resp)
                return False
        except Exception as e:
            logger.warning("Error conectando WS: %s", str(e))
            return False

    def enviar(self, datos: Dict[str, Any]):
        """Envía datos por WebSocket."""
        if self.ws and self.conectado:
            try:
                self.ws.send(json.dumps(datos))
            except Exception:
                self.conectado = False

    def cerrar(self):
        """Cierra la conexión WebSocket."""
        self._running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.conectado = False


# =============================================================================
# DAEMON PRINCIPAL
# =============================================================================
class CentinelaDaemon:
    """Daemon principal de sensores Centinela."""

    def __init__(self, server_url: str, api_key: str, mock: bool = False):
        self.sensor_client = TermuxSensorClient(mock=mock)
        self.server_client = ServidorClient(server_url, api_key)
        self.ws_client = WebSocketClient(server_url, api_key)
        self._running = False
        self._sesion_id: Optional[str] = None
        self._sensores_activos: List[str] = []
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def iniciar(self):
        """Inicia el daemon de sensores."""
        logger.info("=" * 60)
        logger.info("SISTEMA CENTINELA - Daemon de Sensores")
        logger.info("Dispositivo: %s", DEVICE_ID)
        logger.info("Servidor: %s", SERVER_URL)
        logger.info("=" * 60)

        # Obtener sensores disponibles
        logger.info("Detectando sensores...")
        sensores = self.sensor_client.obtener_sensores_disponibles()

        if not sensores:
            logger.warning(
                "No se detectaron sensores. Usando sensores por defecto."
            )
            sensores = SENSORES_PRIORITARIOS

        self._sensores_activos = sensores
        logger.info(
            "Sensores detectados: %d", len(sensores)
        )
        for s in sensores:
            logger.info("  - %s", s)

        # Iniciar sesión en el servidor
        logger.info("Iniciando sesion de monitoreo...")
        self._sesion_id = self.server_client.iniciar_sesion(sensores)
        if self._sesion_id:
            logger.info("Sesion iniciada: %s", self._sesion_id)
        else:
            logger.warning("No se pudo iniciar sesion en el servidor")

        # Conectar WebSocket
        logger.info("Conectando WebSocket...")
        self.ws_client.conectar()

        # Iniciar hilos de lectura de sensores
        self._running = True
        self._stop_event.clear()

        # Hilo para sensores prioritarios (alta frecuencia)
        for sensor in SENSORES_PRIORITARIOS:
            if sensor in sensores:
                intervalo = SAMPLE_INTERVALS.get(sensor, 1.0)
                t = threading.Thread(
                    target=self._bucle_sensor,
                    args=(sensor, intervalo),
                    daemon=True,
                    name=f"sensor-{sensor.split('.')[-1]}",
                )
                t.start()
                self._threads.append(t)

        # Hilo para sensores secundarios (baja frecuencia)
        for sensor in SENSORES_SECUNDARIOS:
            if sensor in sensores:
                intervalo = SAMPLE_INTERVALS.get(sensor, 5.0)
                t = threading.Thread(
                    target=self._bucle_sensor,
                    args=(sensor, intervalo),
                    daemon=True,
                    name=f"sensor-{sensor.split('.')[-1]}",
                )
                t.start()
                self._threads.append(t)

        # Hilo de reporte de estadísticas
        t_stats = threading.Thread(
            target=self._bucle_stats,
            daemon=True,
            name="stats",
        )
        t_stats.start()
        self._threads.append(t_stats)

        logger.info(
            "Daemon iniciado con %d hilos de sensores",
            len(self._threads),
        )

        # Mantener vivo
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo daemon...")
            self.detener()

    def detener(self):
        """Detiene el daemon de sensores."""
        logger.info("Deteniendo daemon...")
        self._running = False
        self._stop_event.set()

        # Finalizar sesión
        if self._sesion_id:
            self.server_client.finalizar_sesion(self._sesion_id)
            logger.info("Sesion finalizada: %s", self._sesion_id)

        # Cerrar WebSocket
        self.ws_client.cerrar()

        # Esperar hilos
        for t in self._threads:
            t.join(timeout=3)

        logger.info("Daemon detenido")
        logger.info(
            "Estadisticas: %s", self.server_client.get_stats()
        )

    def _bucle_sensor(self, sensor_name: str, intervalo: float):
        """Bucle de lectura para un sensor específico."""
        nombre_corto = sensor_name.split(".")[-1]
        logger.debug(
            "Iniciando hilo para %s (intervalo: %.2fs)",
            nombre_corto, intervalo,
        )

        while self._running and not self._stop_event.is_set():
            try:
                lectura = self.sensor_client.leer_sensor(sensor_name)
                if lectura:
                    # Añadir timestamp y device_id
                    lectura["timestamp"] = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    lectura["device_id"] = DEVICE_ID

                    # Enviar al servidor
                    exito = self.server_client.enviar_sensor(lectura)

                    # También enviar por WebSocket si está conectado
                    if exito and self.ws_client.conectado:
                        self.ws_client.enviar({
                            "accion": "sensor",
                            "datos": lectura,
                        })

            except Exception as e:
                logger.error(
                    "Error en bucle %s: %s", nombre_corto, str(e)
                )

            # Esperar intervalo (con chequeo de stop)
            self._stop_event.wait(intervalo)

    def _bucle_stats(self):
        """Bucle de reporte de estadísticas."""
        while self._running and not self._stop_event.is_set():
            stats = self.server_client.get_stats()
            logger.info(
                "Stats - Enviados: %d | Fallidos: %d | WS: %s",
                stats["enviados"],
                stats["fallidos"],
                "conectado" if self.ws_client.conectado else "desconectado",
            )
            self._stop_event.wait(60)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Daemon de sensores Centinela para Termux"
    )
    parser.add_argument(
        "--server",
        default=SERVER_URL,
        help="URL del servidor Nova (default: %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        default=API_KEY,
        help="API Key para autenticacion",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=MOCK_MODE,
        help="Usar datos simulados (sin dispositivo real)",
    )
    parser.add_argument(
        "--device-id",
        default=DEVICE_ID,
        help="ID del dispositivo (default: %(default)s)",
    )

    args = parser.parse_args()

    global SERVER_URL, API_KEY, DEVICE_ID, MOCK_MODE
    SERVER_URL = args.server
    API_KEY = args.api_key
    DEVICE_ID = args.device_id
    MOCK_MODE = args.mock

    daemon = CentinelaDaemon(
        server_url=SERVER_URL,
        api_key=API_KEY,
        mock=MOCK_MODE,
    )

    # Manejar señales para cierre graceful
    def signal_handler(signum, frame):
        logger.info("Senial %s recibida", signum)
        daemon.detener()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    daemon.iniciar()


if __name__ == "__main__":
    main()
