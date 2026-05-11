"""
watchdog — Perro Guardián
Nova Homonexus — SENTINEL

Monitorea la salud del sistema:
  - Heartbeat bidireccional servidor ↔ Z Fold (cada 5s)
  - Detección de desconexión (>15s sin heartbeat)
  - Reconexión automática con backoff exponencial
  - Estado del dispositivo (batería, señal, almacenamiento, CPU)
  - Watchdog interno del servidor (auto-reinicio si falla)
"""

import os
import time
import json
import logging
import signal
import subprocess
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, Callable, List
from collections import defaultdict
from dataclasses import dataclass, field

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.watchdog")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DeviceHeartbeat:
    """Heartbeat de un dispositivo."""
    device_id: str
    last_seen: float
    battery_level: Optional[int]
    signal_strength: Optional[int]  # RSSI dBm
    storage_used_pct: Optional[float]
    cpu_temp: Optional[float]
    cpu_usage_pct: Optional[float]
    memory_used_mb: Optional[float]
    is_connected: bool = True
    missed_beats: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "last_seen": datetime.fromtimestamp(
                self.last_seen, tz=timezone.utc
            ).isoformat(),
            "battery_level": self.battery_level,
            "signal_strength": self.signal_strength,
            "storage_used_pct": self.storage_used_pct,
            "cpu_temp": self.cpu_temp,
            "cpu_usage_pct": self.cpu_usage_pct,
            "memory_used_mb": self.memory_used_mb,
            "is_connected": self.is_connected,
            "missed_beats": self.missed_beats,
        }


@dataclass
class ServerHealth:
    """Salud del servidor Centinela."""
    pid: int
    start_time: float
    cpu_usage_pct: float
    memory_used_mb: float
    memory_total_mb: float
    disk_used_pct: float
    uptime_seconds: float
    active_connections: int
    last_check: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "start_time": datetime.fromtimestamp(
                self.start_time, tz=timezone.utc
            ).isoformat(),
            "cpu_usage_pct": self.cpu_usage_pct,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "disk_used_pct": self.disk_used_pct,
            "uptime_seconds": self.uptime_seconds,
            "active_connections": self.active_connections,
            "last_check": datetime.fromtimestamp(
                self.last_check, tz=timezone.utc
            ).isoformat(),
        }


# =============================================================================
# WATCHDOG
# =============================================================================

class Watchdog:
    """
    Perro guardián del sistema Centinela.

    Monitorea:
      - Heartbeat bidireccional con dispositivos
      - Reconexión automática con backoff exponencial
      - Estado de salud del Z Fold y Watch 8
      - Salud del propio servidor
      - Auto-recuperación en caso de fallo
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        wd_cfg = self._rules.watchdog_cfg

        # Heartbeat
        self._heartbeat_interval = wd_cfg.get(
            "heartbeat_interval", 5
        )
        self._heartbeat_timeout = wd_cfg.get(
            "heartbeat_timeout", 15
        )

        # Reconexión
        self._reconnect_base = wd_cfg.get(
            "reconnect_base_delay", 1
        )
        self._reconnect_max = wd_cfg.get(
            "reconnect_max_delay", 60
        )
        self._reconnect_retries = wd_cfg.get(
            "reconnect_max_retries", 10
        )

        # Watchdog interno
        self._self_check_interval = wd_cfg.get(
            "self_check_interval", 30
        )
        self._memory_warning = wd_cfg.get(
            "memory_warning_mb", 500
        )
        self._cpu_warning = wd_cfg.get("cpu_warning_pct", 80)
        self._disk_warning = wd_cfg.get("disk_warning_pct", 85)
        self._cpu_temp_max = wd_cfg.get("cpu_temp_max", 85.0)

        # Batería
        self._battery_critical = wd_cfg.get(
            "battery_critical_pct", 5
        )
        self._battery_warning = wd_cfg.get(
            "battery_warning_pct", 15
        )

        # Señal
        self._signal_good = wd_cfg.get("signal_min_good", -80)
        self._signal_critical = wd_cfg.get("signal_critical", -100)

        # Estado de dispositivos
        self._devices: Dict[str, DeviceHeartbeat] = {}

        # Estado del servidor
        self._server_start = time.time()
        self._server_health: Optional[ServerHealth] = None

        # Callbacks
        self._on_disconnect: Optional[Callable] = None
        self._on_reconnect: Optional[Callable] = None
        self._on_health_warning: Optional[Callable] = None

        # Control de hilos
        self._running = False
        self._watchdog_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        logger.info(
            "Watchdog inicializado. "
            "Heartbeat: %ds, Timeout: %ds, "
            "Reconexión base: %ds",
            self._heartbeat_interval,
            self._heartbeat_timeout,
            self._reconnect_base,
        )

    # ------------------------------------------------------------------
    # CALLBACKS
    # ------------------------------------------------------------------

    def set_on_disconnect(
        self, callback: Callable[[str, DeviceHeartbeat], None]
    ) -> None:
        """Establece callback para cuando un dispositivo se desconecta."""
        self._on_disconnect = callback

    def set_on_reconnect(
        self, callback: Callable[[str, DeviceHeartbeat], None]
    ) -> None:
        """Establece callback para cuando un dispositivo se reconecta."""
        self._on_reconnect = callback

    def set_on_health_warning(
        self,
        callback: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        """
        Establece callback para advertencias de salud del servidor.
        """
        self._on_health_warning = callback

    # ------------------------------------------------------------------
    # HEARTBEAT
    # ------------------------------------------------------------------

    def register_heartbeat(
        self,
        device_id: str,
        battery_level: Optional[int] = None,
        signal_strength: Optional[int] = None,
        storage_used_pct: Optional[float] = None,
        cpu_temp: Optional[float] = None,
        cpu_usage_pct: Optional[float] = None,
        memory_used_mb: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Registra un heartbeat de un dispositivo.

        Args:
            device_id: ID del dispositivo.
            battery_level: Nivel de batería (0-100).
            signal_strength: RSSI en dBm.
            storage_used_pct: Almacenamiento usado (%).
            cpu_temp: Temperatura de CPU (°C).
            cpu_usage_pct: Uso de CPU (%).
            memory_used_mb: Memoria usada (MB).

        Returns:
            Dict con estado actual y acciones recomendadas.
        """
        now = time.time()
        was_disconnected = False

        with self._lock:
            prev = self._devices.get(device_id)
            if prev and not prev.is_connected:
                was_disconnected = True

            heartbeat = DeviceHeartbeat(
                device_id=device_id,
                last_seen=now,
                battery_level=battery_level,
                signal_strength=signal_strength,
                storage_used_pct=storage_used_pct,
                cpu_temp=cpu_temp,
                cpu_usage_pct=cpu_usage_pct,
                memory_used_mb=memory_used_mb,
                is_connected=True,
                missed_beats=0,
            )
            self._devices[device_id] = heartbeat

        # Disparar callback de reconexión
        if was_disconnected and self._on_reconnect:
            self._on_reconnect(device_id, heartbeat)

        # Verificar estado del dispositivo
        warnings = self._check_device_health(device_id, heartbeat)

        logger.debug(
            "Heartbeat recibido: %s (bat=%s%%, señal=%s dBm)",
            device_id,
            battery_level,
            signal_strength,
        )

        return {
            "status": "ok",
            "device_id": device_id,
            "last_seen": heartbeat.last_seen,
            "warnings": warnings,
        }

    def _check_device_health(
        self, device_id: str, hb: DeviceHeartbeat
    ) -> List[Dict[str, Any]]:
        """
        Verifica la salud del dispositivo y genera advertencias.

        Args:
            device_id: ID del dispositivo.
            hb: Heartbeat del dispositivo.

        Returns:
            Lista de advertencias.
        """
        warnings = []

        # Batería
        if hb.battery_level is not None:
            if hb.battery_level <= self._battery_critical:
                warnings.append({
                    "tipo": "bateria_critica",
                    "severidad": "CRITICAL",
                    "mensaje": (
                        f"Batería crítica: {hb.battery_level}%"
                    ),
                    "valor": hb.battery_level,
                    "umbral": self._battery_critical,
                })
            elif hb.battery_level <= self._battery_warning:
                warnings.append({
                    "tipo": "bateria_baja",
                    "severidad": "WARNING",
                    "mensaje": (
                        f"Batería baja: {hb.battery_level}%"
                    ),
                    "valor": hb.battery_level,
                    "umbral": self._battery_warning,
                })

        # Señal
        if hb.signal_strength is not None:
            if hb.signal_strength <= self._signal_critical:
                warnings.append({
                    "tipo": "senal_critica",
                    "severidad": "WARNING",
                    "mensaje": (
                        f"Señal crítica: {hb.signal_strength} dBm"
                    ),
                    "valor": hb.signal_strength,
                    "umbral": self._signal_critical,
                })

        # Temperatura CPU
        if hb.cpu_temp is not None:
            if hb.cpu_temp >= self._cpu_temp_max:
                warnings.append({
                    "tipo": "cpu_caliente",
                    "severidad": "WARNING",
                    "mensaje": (
                        f"CPU sobrecalentada: {hb.cpu_temp}°C"
                    ),
                    "valor": hb.cpu_temp,
                    "umbral": self._cpu_temp_max,
                })

        # Almacenamiento
        if hb.storage_used_pct is not None:
            if hb.storage_used_pct >= self._disk_warning:
                warnings.append({
                    "tipo": "almacenamiento_lleno",
                    "severidad": "WARNING",
                    "mensaje": (
                        f"Almacenamiento al {hb.storage_used_pct}%"
                    ),
                    "valor": hb.storage_used_pct,
                    "umbral": self._disk_warning,
                })

        return warnings

    # ------------------------------------------------------------------
    # DETECCIÓN DE DESCONEXIÓN
    # ------------------------------------------------------------------

    def check_disconnections(self) -> List[Dict[str, Any]]:
        """
        Verifica qué dispositivos están desconectados.

        Returns:
            Lista de eventos de desconexión.
        """
        now = time.time()
        events = []

        with self._lock:
            for device_id, hb in self._devices.items():
                elapsed = now - hb.last_seen

                if elapsed > self._heartbeat_timeout and hb.is_connected:
                    hb.is_connected = False
                    hb.missed_beats += 1

                    events.append({
                        "tipo": "desconexion",
                        "severidad": "ERROR",
                        "device_id": device_id,
                        "mensaje": (
                            f"Dispositivo {device_id} desconectado. "
                            f"Último heartbeat hace "
                            f"{elapsed:.0f}s"
                        ),
                        "tiempo_desconectado": elapsed,
                        "heartbeat_perdidos": hb.missed_beats,
                    })

                    logger.warning(
                        "DESCONEXIÓN: %s (%ds sin heartbeat)",
                        device_id,
                        elapsed,
                    )

                    if self._on_disconnect:
                        self._on_disconnect(device_id, hb)

                elif elapsed <= self._heartbeat_timeout and not hb.is_connected:
                    # Reconectado
                    hb.is_connected = True
                    events.append({
                        "tipo": "reconexion",
                        "severidad": "INFO",
                        "device_id": device_id,
                        "mensaje": (
                            f"Dispositivo {device_id} reconectado "
                            f"tras {hb.missed_beats} heartbeats perdidos"
                        ),
                    })

                    logger.info(
                        "RECONEXIÓN: %s", device_id
                    )

        return events

    # ------------------------------------------------------------------
    # BACKOFF EXPONENCIAL
    # ------------------------------------------------------------------

    def get_reconnect_delay(self, retry_count: int) -> float:
        """
        Calcula el delay de reconexión con backoff exponencial.

        Args:
            retry_count: Número de reintento actual.

        Returns:
            Delay en segundos.
        """
        delay = self._reconnect_base * (2 ** retry_count)
        return min(delay, self._reconnect_max)

    def should_attempt_reconnect(self, retry_count: int) -> bool:
        """
        Verifica si se debe intentar reconectar.

        Args:
            retry_count: Número de reintento actual.

        Returns:
            True si se debe intentar reconectar.
        """
        return retry_count < self._reconnect_retries

    # ------------------------------------------------------------------
    # WATCHDOG INTERNO DEL SERVIDOR
    # ------------------------------------------------------------------

    def check_server_health(self) -> ServerHealth:
        """
        Verifica la salud del servidor Centinela.

        Returns:
            ServerHealth con estado actual.
        """
        pid = os.getpid()
        now = time.time()

        # CPU
        cpu_usage = self._get_cpu_usage()

        # Memoria
        mem_used, mem_total = self._get_memory_usage()

        # Disco
        disk_used = self._get_disk_usage()

        # Conexiones activas
        active_connections = len(self._devices)

        health = ServerHealth(
            pid=pid,
            start_time=self._server_start,
            cpu_usage_pct=cpu_usage,
            memory_used_mb=mem_used,
            memory_total_mb=mem_total,
            disk_used_pct=disk_used,
            uptime_seconds=now - self._server_start,
            active_connections=active_connections,
            last_check=now,
        )

        self._server_health = health

        # Verificar umbrales
        warnings = []
        if cpu_usage > self._cpu_warning:
            warnings.append(
                f"CPU alta: {cpu_usage:.1f}% "
                f"(umbral: {self._cpu_warning}%)"
            )
        if mem_used > self._memory_warning:
            warnings.append(
                f"Memoria alta: {mem_used:.0f}MB "
                f"(umbral: {self._memory_warning}MB)"
            )
        if disk_used > self._disk_warning:
            warnings.append(
                f"Disco alto: {disk_used:.1f}% "
                f"(umbral: {self._disk_warning}%)"
            )

        if warnings and self._on_health_warning:
            self._on_health_warning(
                "servidor",
                {
                    "warnings": warnings,
                    "health": health.to_dict(),
                },
            )

        return health

    def _get_cpu_usage(self) -> float:
        """Obtiene el uso de CPU del proceso actual."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            # Fallback: leer de /proc/stat
            try:
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                    parts = line.split()
                    if len(parts) >= 5:
                        user = int(parts[1])
                        nice = int(parts[2])
                        system = int(parts[3])
                        idle = int(parts[4])
                        total = user + nice + system + idle
                        if total > 0:
                            return (
                                (user + nice + system) / total * 100
                            )
            except (IOError, IndexError, ValueError):
                pass
            return 0.0

    def _get_memory_usage(self) -> Tuple[float, float]:
        """Obtiene el uso de memoria en MB."""
        try:
            import psutil
            proc = psutil.Process()
            mem_info = proc.memory_info()
            used_mb = mem_info.rss / (1024 * 1024)
            total_mb = psutil.virtual_memory().total / (1024 * 1024)
            return used_mb, total_mb
        except ImportError:
            # Fallback: leer de /proc/self/status
            try:
                with open("/proc/self/status", "r") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                used_kb = int(parts[1])
                                return used_kb / 1024, 0
            except (IOError, IndexError, ValueError):
                pass
            return 0.0, 0.0

    def _get_disk_usage(self) -> float:
        """Obtiene el uso de disco del directorio de trabajo."""
        try:
            stat = os.statvfs("/home/opc/nova")
            used = (
                (stat.f_blocks - stat.f_bfree) * stat.f_frsize
            )
            total = stat.f_blocks * stat.f_frsize
            if total > 0:
                return (used / total) * 100
        except (AttributeError, OSError):
            pass
        return 0.0

    # ------------------------------------------------------------------
    # HILO DE MONITOREO
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia el hilo de monitoreo del watchdog."""
        if self._running:
            return

        self._running = True
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="sentinel-watchdog",
        )
        self._watchdog_thread.start()
        logger.info("Watchdog iniciado en hilo de monitoreo")

    def stop(self) -> None:
        """Detiene el hilo de monitoreo."""
        self._running = False
        logger.info("Watchdog detenido")

    def _watchdog_loop(self) -> None:
        """Bucle principal del watchdog."""
        last_heartbeat_check = 0.0
        last_self_check = 0.0

        while self._running:
            now = time.time()

            # Verificar heartbeats cada intervalo
            if now - last_heartbeat_check >= self._heartbeat_interval:
                events = self.check_disconnections()
                for event in events:
                    if event["severidad"] in ("ERROR", "CRITICAL"):
                        logger.warning(
                            "Watchdog: %s - %s",
                            event["tipo"],
                            event["mensaje"],
                        )
                last_heartbeat_check = now

            # Auto-verificación del servidor
            if now - last_self_check >= self._self_check_interval:
                self.check_server_health()
                last_self_check = now

            time.sleep(1)

    # ------------------------------------------------------------------
    # ESTADO
    # ------------------------------------------------------------------

    def get_device_status(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de un dispositivo.

        Args:
            device_id: ID del dispositivo.

        Returns:
            Dict con estado o None.
        """
        hb = self._devices.get(device_id)
        if hb:
            return hb.to_dict()
        return None

    def get_all_devices(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los dispositivos."""
        return {
            did: hb.to_dict()
            for did, hb in self._devices.items()
        }

    def get_server_health(self) -> Optional[Dict[str, Any]]:
        """Obtiene la salud del servidor."""
        if self._server_health:
            return self._server_health.to_dict()
        return None

    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado completo del watchdog."""
        return {
            "running": self._running,
            "heartbeat_interval": self._heartbeat_interval,
            "heartbeat_timeout": self._heartbeat_timeout,
            "devices": self.get_all_devices(),
            "server_health": self.get_server_health(),
            "uptime_seconds": time.time() - self._server_start,
            "config": {
                "reconnect_base_delay": self._reconnect_base,
                "reconnect_max_delay": self._reconnect_max,
                "reconnect_max_retries": self._reconnect_retries,
                "battery_critical": self._battery_critical,
                "battery_warning": self._battery_warning,
                "signal_good": self._signal_good,
                "signal_critical": self._signal_critical,
                "cpu_warning": self._cpu_warning,
                "memory_warning_mb": self._memory_warning,
                "disk_warning": self._disk_warning,
            },
        }
