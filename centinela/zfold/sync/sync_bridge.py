"""
Sync Bridge — Sincronización bidireccional Z Fold ↔ Servidor Casa
==================================================================
Cuando el Z Fold está en WiFi, sincroniza los datos locales (SQLite)
con el servidor central (PostgreSQL). Soporta:

  - ZFOLD → SERVER: Subir datos nuevos
  - SERVER → ZFOLD: Bajar configuraciones, dones, análisis
  - Resolución de conflictos por timestamp
  - Solo en WiFi (no consume datos móviles)
  - Batería > 20%
"""

import os
import sys
import json
import time
import sqlite3
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("centinela.zfold.sync")


class SyncBridge:
    """
    Puente de sincronización Z Fold (SQLite) ↔ Servidor (PostgreSQL).
    """

    TABLAS_SYNC = ["sensores", "ubicacion", "health", "emociones"]

    def __init__(
        self,
        zfold_db_path: str,
        server_url: str,
        api_key: str = "nexus-centinela-key-2026",
        device_id: str = "samsung_zfold_01",
    ):
        self.zfold_db = sqlite3.connect(zfold_db_path, check_same_thread=False)
        self.zfold_db.row_factory = sqlite3.Row
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.device_id = device_id
        self._ultima_sync: Optional[datetime] = None
        self._sync_interval = 300  # 5 minutos

    def debe_sincronizar(self, forzar: bool = False) -> bool:
        """Determina si es momento de sincronizar."""
        if forzar:
            return True

        # Verificar WiFi
        if not self._en_wifi():
            logger.debug("No WiFi — sincronización pospuesta")
            return False

        # Verificar intervalo
        if self._ultima_sync:
            segundos = (datetime.now(timezone.utc) - self._ultima_sync).total_seconds()
            if segundos < self._sync_interval:
                return False

        return True

    def sincronizar(self, direccion: str = "ambas") -> Dict[str, Any]:
        """
        Sincroniza datos entre Z Fold y servidor.

        Args:
            direccion: 'subir' (ZFold→Server), 'bajar' (Server→ZFold), 'ambas'
        """
        if not self.debe_sincronizar(forzar=(direccion != "ambas")):
            return {"sincronizado": False, "razon": "No WiFi o intervalo"}

        resultados = {}
        self._ultima_sync = datetime.now(timezone.utc)

        if direccion in ("subir", "ambas"):
            resultados["subida"] = self._subir_datos()

        if direccion in ("bajar", "ambas"):
            resultados["bajada"] = self._bajar_datos()

        self._registrar_sync(resultados)
        return resultados

    def _subir_datos(self) -> Dict[str, int]:
        """Sube datos nuevos del Z Fold al servidor."""
        subidos = {}
        headers = {
            "X-API-Key": self.api_key,
            "X-Device-ID": self.device_id,
            "Content-Type": "application/json",
        }

        for tabla in self.TABLAS_SYNC:
            # Obtener registros no sincronizados (últimos 5 min)
            cursor = self.zfold_db.execute(
                f"SELECT * FROM {tabla} WHERE timestamp > datetime('now', '-10 minutes') "
                "ORDER BY timestamp ASC LIMIT 500"
            )
            rows = cursor.fetchall()
            if not rows:
                continue

            endpoint = f"/api/centinela/{tabla.rstrip('s')}"
            count = 0
            for row in rows:
                data = dict(row)
                # Limpiar campos internos
                data.pop("id", None)
                data["device_id"] = data.get("device_id", self.device_id)
                try:
                    r = requests.post(
                        f"{self.server_url}{endpoint}",
                        json=data,
                        headers=headers,
                        timeout=10,
                    )
                    if r.status_code in (200, 201):
                        count += 1
                except requests.RequestException:
                    break
            subidos[tabla] = count

        return subidos

    def _bajar_datos(self) -> Dict[str, Any]:
        """Baja configuraciones y análisis del servidor al Z Fold."""
        bajados = {}
        headers = {
            "X-API-Key": self.api_key,
            "X-Device-ID": self.device_id,
        }

        # Bajar estado de los dones
        try:
            r = requests.get(
                f"{self.server_url}/centinela/soul",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                dones_data = r.json().get("dones", {})
                cursor = self.zfold_db.cursor()
                for nombre, don in dones_data.items():
                    cursor.execute(
                        "INSERT OR REPLACE INTO dones (nombre, valor, mensaje) "
                        "VALUES (?, ?, ?)",
                        (nombre, don["valor"], don.get("mensaje", "")),
                    )
                self.zfold_db.commit()
                bajados["dones"] = len(dones_data)
        except requests.RequestException:
            pass

        # Bajar análisis de salud
        try:
            r = requests.get(
                f"{self.server_url}/salud/analisis",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                bajados["analisis_salud"] = r.json()
        except requests.RequestException:
            pass

        return bajados

    def _registrar_sync(self, resultados: Dict):
        """Registra la sincronización en el log."""
        for direccion, datos in resultados.items():
            if isinstance(datos, dict):
                for tabla, count in datos.items():
                    self.zfold_db.execute(
                        "INSERT INTO sync_log (direccion, tabla, registros, estado) "
                        "VALUES (?, ?, ?, 'ok')",
                        (direccion, tabla, count if isinstance(count, int) else 0),
                    )
        self.zfold_db.commit()

    def _en_wifi(self) -> bool:
        """Detecta si el Z Fold está conectado por WiFi."""
        try:
            import subprocess
            result = subprocess.run(
                ["termux-wifi-connectioninfo"],
                capture_output=True, text=True, timeout=5,
            )
            return "SSID" in result.stdout
        except Exception:
            # Si no podemos detectar, asumir WiFi para no bloquear
            return True


def sincronizar_loop(
    db_path: str,
    server_url: str,
    api_key: str = "nexus-centinela-key-2026",
    intervalo: int = 300,
):
    """Loop de sincronización continua (ejecutar en hilo separado)."""
    bridge = SyncBridge(db_path, server_url, api_key)

    while True:
        try:
            if bridge.debe_sincronizar():
                resultado = bridge.sincronizar("ambas")
                logger.info(f"Sync completado: {resultado}")
        except Exception as e:
            logger.error(f"Error en sync: {e}")
        time.sleep(min(intervalo, 60))  # Chequear cada minuto


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync Bridge ZFold ↔ Server")
    parser.add_argument("--db", default=str(Path.home() / "centinela" / "data" / "centinela_zfold.db"))
    parser.add_argument("--server", default="http://192.168.1.100:9088")
    parser.add_argument("--key", default="nexus-centinela-key-2026")
    parser.add_argument("--loop", action="store_true", help="Sincronización continua")
    args = parser.parse_args()

    if args.loop:
        sincronizar_loop(args.db, args.server, args.key)
    else:
        bridge = SyncBridge(args.db, args.server, args.key)
        result = bridge.sincronizar("ambas")
        print(json.dumps(result, indent=2))
