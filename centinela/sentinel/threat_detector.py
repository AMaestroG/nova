"""
threat_detector — Detección de Amenazas
Nova Homonexus — SENTINEL

Monitorea y detecta:
  - Patrones de acceso anómalos
  - Intentos de suplantación de dispositivo
  - Análisis de frecuencia de peticiones
  - Blacklist dinámica de IPs sospechosas
  - Escaneo de payloads maliciosos
  - Data poisoning (datos falsos de sensores)
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, Set, List
from collections import defaultdict, deque
from dataclasses import dataclass, field

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.threat")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ThreatEvent:
    """Evento de amenaza detectada."""
    threat_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    source_ip: str
    device_id: str
    description: str
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_type": self.threat_type,
            "severity": self.severity,
            "source_ip": self.source_ip,
            "device_id": self.device_id,
            "description": self.description,
            "details": self.details,
            "timestamp": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
        }


@dataclass
class DeviceAccessProfile:
    """Perfil de acceso normal de un dispositivo."""
    device_id: str
    usual_ips: Set[str] = field(default_factory=set)
    usual_endpoints: Set[str] = field(default_factory=set)
    usual_sensor_types: Set[str] = field(default_factory=set)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    total_requests: int = 0
    avg_payload_size: float = 0.0
    payload_sizes: List[int] = field(default_factory=list)


# =============================================================================
# THREAT DETECTOR
# =============================================================================

class ThreatDetector:
    """
    Detector de amenazas del sistema Centinela.

    Monitorea patrones de acceso, suplantación, data poisoning
    y mantiene una blacklist dinámica de IPs sospechosas.
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        threat_cfg = self._rules.threat

        # Blacklist
        self._blacklist: Dict[str, float] = {}  # ip -> blocked_until
        self._blacklist_duration = threat_cfg.get(
            "blacklist_duration", 60
        ) * 60
        self._blacklist_max = threat_cfg.get("blacklist_max_ips", 1000)

        # Perfiles de dispositivo
        self._device_profiles: Dict[str, DeviceAccessProfile] = {}

        # Data poisoning
        self._sensor_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._poisoning_std_dev = threat_cfg.get(
            "data_poisoning_std_dev", 5.0
        )
        self._poisoning_window = threat_cfg.get(
            "data_poisoning_window", 3600
        )

        # Suplantación
        self._spoofing_window = threat_cfg.get(
            "spoofing_check_window", 60
        )
        self._max_devices_per_ip = threat_cfg.get(
            "max_devices_per_ip", 3
        )
        self._ip_device_map: Dict[str, Set[str]] = defaultdict(set)

        # Frecuencia de ataque
        self._rate_attack_threshold = threat_cfg.get(
            "rate_attack_threshold", 100
        )
        self._rate_attack_window = threat_cfg.get(
            "rate_attack_window", 10
        )
        self._request_timestamps: Dict[str, List[float]] = defaultdict(
            list
        )

        # Payload máximo
        self._max_payload_bytes = threat_cfg.get(
            "max_payload_bytes", 10485760
        )

        # Historial de amenazas
        self._threat_history: deque = deque(maxlen=10000)

        logger.info(
            "ThreatDetector inicializado. "
            "Blacklist: %d IPs, max %d",
            len(self._blacklist),
            self._blacklist_max,
        )

    # ------------------------------------------------------------------
    # BLACKLIST
    # ------------------------------------------------------------------

    def is_blacklisted(self, ip: str) -> bool:
        """
        Verifica si una IP está en la blacklist.

        Args:
            ip: Dirección IP.

        Returns:
            True si está bloqueada.
        """
        if ip in self._blacklist:
            if time.time() < self._blacklist[ip]:
                return True
            else:
                # Expiró, remover
                del self._blacklist[ip]
        return False

    def add_to_blacklist(
        self, ip: str, reason: str = ""
    ) -> None:
        """
        Añade una IP a la blacklist.

        Args:
            ip: Dirección IP.
            reason: Razón del bloqueo.
        """
        if len(self._blacklist) >= self._blacklist_max:
            # Eliminar la más antigua
            oldest = min(
                self._blacklist.items(), key=lambda x: x[1]
            )
            del self._blacklist[oldest[0]]

        self._blacklist[ip] = time.time() + self._blacklist_duration
        logger.warning(
            "IP añadida a blacklist: %s (%s) por %ds",
            ip,
            reason,
            self._blacklist_duration,
        )

        self._record_threat(
            ThreatEvent(
                threat_type="blacklist",
                severity="HIGH",
                source_ip=ip,
                device_id="unknown",
                description=f"IP bloqueada: {reason}",
                details={"reason": reason, "duration": self._blacklist_duration},
            )
        )

    def remove_from_blacklist(self, ip: str) -> bool:
        """
        Remueve una IP de la blacklist.

        Args:
            ip: Dirección IP.

        Returns:
            True si fue removida.
        """
        if ip in self._blacklist:
            del self._blacklist[ip]
            logger.info("IP removida de blacklist: %s", ip)
            return True
        return False

    def get_blacklist(self) -> Dict[str, float]:
        """Obtiene la blacklist actual."""
        now = time.time()
        return {
            ip: exp for ip, exp in self._blacklist.items()
            if exp > now
        }

    # ------------------------------------------------------------------
    # DETECCIÓN DE SUPLANTACIÓN
    # ------------------------------------------------------------------

    def check_spoofing(
        self, ip: str, device_id: str
    ) -> Tuple[bool, str]:
        """
        Verifica si hay intento de suplantación de dispositivo.

        Un mismo device_id desde IPs muy diferentes en poco tiempo,
        o muchos device_ids desde una misma IP.

        Args:
            ip: Dirección IP.
            device_id: ID del dispositivo.

        Returns:
            (sospechoso, razón)
        """
        now = time.time()

        # Registrar asociación IP-device
        self._ip_device_map[ip].add(device_id)

        # Limpiar entradas antiguas
        cutoff = now - self._spoofing_window
        for ip_key in list(self._ip_device_map.keys()):
            if ip_key not in self._ip_device_map:
                continue
            # No podemos limpiar por tiempo fácilmente aquí,
            # pero limitamos el tamaño
            if len(self._ip_device_map) > 10000:
                self._ip_device_map.clear()

        # Verificar: muchos dispositivos desde misma IP
        devices_from_ip = self._ip_device_map.get(ip, set())
        if len(devices_from_ip) > self._max_devices_per_ip:
            return False, (
                f"Múltiples dispositivos ({len(devices_from_ip)}) "
                f"desde misma IP {ip}"
            )

        # Verificar: mismo dispositivo desde IPs diferentes
        # (esto se maneja mejor con el perfil de dispositivo)
        profile = self._device_profiles.get(device_id)
        if profile and profile.usual_ips:
            if ip not in profile.usual_ips:
                # IP nueva para este dispositivo
                profile.usual_ips.add(ip)
                if len(profile.usual_ips) > 5:
                    return False, (
                        f"Dispositivo {device_id} visto desde "
                        f"demasiadas IPs diferentes"
                    )

        return True, "ok"

    # ------------------------------------------------------------------
    # ANÁLISIS DE FRECUENCIA
    # ------------------------------------------------------------------

    def check_rate_attack(self, ip: str) -> Tuple[bool, int]:
        """
        Detecta ataques de fuerza bruta por frecuencia.

        Args:
            ip: Dirección IP.

        Returns:
            (ataque_detectado, peticiones_en_ventana)
        """
        now = time.time()
        cutoff = now - self._rate_attack_window

        # Limpiar antiguas
        timestamps = self._request_timestamps[ip]
        self._request_timestamps[ip] = [
            t for t in timestamps if t > cutoff
        ]

        count = len(self._request_timestamps[ip])
        self._request_timestamps[ip].append(now)

        if count > self._rate_attack_threshold:
            return True, count

        return False, count

    # ------------------------------------------------------------------
    # DATA POISONING
    # ------------------------------------------------------------------

    def check_data_poisoning(
        self,
        device_id: str,
        sensor_type: str,
        value: Any,
    ) -> Tuple[bool, str]:
        """
        Detecta data poisoning: valores de sensores que se desvían
        significativamente del promedio histórico.

        Args:
            device_id: ID del dispositivo.
            sensor_type: Tipo de sensor.
            value: Valor numérico a verificar.

        Returns:
            (sospechoso, razón)
        """
        if not isinstance(value, (int, float)):
            return False, "valor no numérico, sin verificación"

        key = f"{device_id}:{sensor_type}"
        history = self._sensor_history[key]

        if len(history) < 10:
            # No hay suficiente historial aún
            history.append(value)
            return False, "historial insuficiente"

        # Calcular promedio y desviación estándar
        values = list(history)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        # Verificar si el nuevo valor es anómalo
        if std_dev > 0:
            z_score = abs(value - mean) / std_dev
            if z_score > self._poisoning_std_dev:
                history.append(value)
                return True, (
                    f"Valor {value} se desvía {z_score:.1f} desviaciones "
                    f"estándar del promedio {mean:.2f} "
                    f"(límite: {self._poisoning_std_dev})"
                )

        history.append(value)
        return False, "ok"

    # ------------------------------------------------------------------
    # ESCANEO DE PAYLOADS
    # ------------------------------------------------------------------

    def scan_payload(
        self, payload: Dict[str, Any], ip: str
    ) -> Tuple[bool, str]:
        """
        Escanea un payload en busca de contenido malicioso.

        Args:
            payload: Datos a escanear.
            ip: IP de origen.

        Returns:
            (seguro, razón)
        """
        # Verificar tamaño
        try:
            payload_bytes = len(json.dumps(payload).encode("utf-8"))
        except (TypeError, ValueError):
            return False, "No se pudo serializar el payload"

        if payload_bytes > self._max_payload_bytes:
            return False, (
                f"Payload demasiado grande: "
                f"{payload_bytes} bytes (máx: {self._max_payload_bytes})"
            )

        # Verificar profundidad de anidamiento
        depth = self._check_depth(payload)
        max_depth = self._rules.threat.get("max_json_depth", 10)
        if depth > max_depth:
            return False, (
                f"Anidamiento excesivo: {depth} niveles "
                f"(máx: {max_depth})"
            )

        return True, "ok"

    def _check_depth(self, obj: Any, depth: int = 0) -> int:
        """Calcula la profundidad máxima de anidamiento."""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(
                self._check_depth(v, depth + 1) for v in obj.values()
            )
        if isinstance(obj, list):
            if not obj:
                return depth
            return max(
                self._check_depth(item, depth + 1) for item in obj
            )
        return depth

    # ------------------------------------------------------------------
    # PERFIL DE DISPOSITIVO
    # ------------------------------------------------------------------

    def update_device_profile(
        self,
        device_id: str,
        ip: str,
        endpoint: str,
        sensor_type: Optional[str] = None,
        payload_size: int = 0,
    ) -> None:
        """
        Actualiza el perfil de acceso de un dispositivo.

        Args:
            device_id: ID del dispositivo.
            ip: Dirección IP.
            endpoint: Endpoint al que accede.
            sensor_type: Tipo de sensor (opcional).
            payload_size: Tamaño del payload en bytes.
        """
        if device_id not in self._device_profiles:
            self._device_profiles[device_id] = DeviceAccessProfile(
                device_id=device_id
            )

        profile = self._device_profiles[device_id]
        profile.usual_ips.add(ip)
        profile.usual_endpoints.add(endpoint)
        if sensor_type:
            profile.usual_sensor_types.add(sensor_type)
        profile.last_seen = time.time()
        profile.total_requests += 1
        profile.payload_sizes.append(payload_size)

        # Actualizar promedio
        n = len(profile.payload_sizes)
        if n > 0:
            profile.avg_payload_size = (
                sum(profile.payload_sizes) / n
            )

    def get_device_profile(
        self, device_id: str
    ) -> Optional[DeviceAccessProfile]:
        """
        Obtiene el perfil de acceso de un dispositivo.

        Args:
            device_id: ID del dispositivo.

        Returns:
            Perfil o None si no existe.
        """
        return self._device_profiles.get(device_id)

    # ------------------------------------------------------------------
    # ANÁLISIS COMPLETO
    # ------------------------------------------------------------------

    def analyze_request(
        self,
        ip: str,
        device_id: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        sensor_type: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[ThreatEvent]]:
        """
        Análisis completo de seguridad de una petición.

        Args:
            ip: Dirección IP.
            device_id: ID del dispositivo.
            endpoint: Endpoint solicitado.
            payload: Payload de la petición (opcional).
            sensor_type: Tipo de sensor (opcional).

        Returns:
            (seguro, razón, evento_de_amenaza)
        """
        # 1. Verificar blacklist
        if self.is_blacklisted(ip):
            return False, "IP en blacklist", ThreatEvent(
                threat_type="blacklisted_ip",
                severity="HIGH",
                source_ip=ip,
                device_id=device_id,
                description="Petición de IP blacklisteada",
                details={"endpoint": endpoint},
            )

        # 2. Verificar ataque de frecuencia
        ataque, count = self.check_rate_attack(ip)
        if ataque:
            self.add_to_blacklist(
                ip, f"Ataque de frecuencia: {count} req/{self._rate_attack_window}s"
            )
            return False, "Ataque de frecuencia detectado", ThreatEvent(
                threat_type="rate_attack",
                severity="CRITICAL",
                source_ip=ip,
                device_id=device_id,
                description=(
                    f"Ataque de frecuencia: {count} peticiones "
                    f"en {self._rate_attack_window}s"
                ),
                details={
                    "request_count": count,
                    "window": self._rate_attack_window,
                    "endpoint": endpoint,
                },
            )

        # 3. Verificar suplantación
        no_spoof, spoof_reason = self.check_spoofing(ip, device_id)
        if not no_spoof:
            return False, spoof_reason, ThreatEvent(
                threat_type="spoofing",
                severity="HIGH",
                source_ip=ip,
                device_id=device_id,
                description=f"Posible suplantación: {spoof_reason}",
                details={"endpoint": endpoint},
            )

        # 4. Escanear payload
        if payload:
            seguro, razon = self.scan_payload(payload, ip)
            if not seguro:
                return False, razon, ThreatEvent(
                    threat_type="malicious_payload",
                    severity="HIGH",
                    source_ip=ip,
                    device_id=device_id,
                    description=f"Payload malicioso: {razon}",
                    details={
                        "endpoint": endpoint,
                        "reason": razon,
                    },
                )

        # 5. Verificar data poisoning
        if sensor_type and payload:
            valor = payload.get("valor", {})
            if isinstance(valor, dict):
                for key, val in valor.items():
                    if isinstance(val, (int, float)):
                        poisoned, reason = self.check_data_poisoning(
                            device_id, f"{sensor_type}.{key}", val
                        )
                        if poisoned:
                            return False, reason, ThreatEvent(
                                threat_type="data_poisoning",
                                severity="MEDIUM",
                                source_ip=ip,
                                device_id=device_id,
                                description=(
                                    f"Posible data poisoning: {reason}"
                                ),
                                details={
                                    "sensor_type": sensor_type,
                                    "field": key,
                                    "value": val,
                                },
                            )

        # Actualizar perfil
        payload_size = 0
        if payload:
            try:
                payload_size = len(
                    json.dumps(payload).encode("utf-8")
                )
            except (TypeError, ValueError):
                pass

        self.update_device_profile(
            device_id, ip, endpoint, sensor_type, payload_size
        )

        return True, "ok", None

    # ------------------------------------------------------------------
    # REGISTRO DE AMENAZAS
    # ------------------------------------------------------------------

    def _record_threat(self, event: ThreatEvent) -> None:
        """Registra un evento de amenaza en el historial."""
        self._threat_history.append(event)
        logger.log(
            logging.CRITICAL
            if event.severity == "CRITICAL"
            else logging.WARNING,
            "Amenaza [%s/%s]: %s desde %s",
            event.severity,
            event.threat_type,
            event.description,
            event.source_ip,
        )

    def get_recent_threats(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las amenazas más recientes.

        Args:
            limit: Número máximo de amenazas.

        Returns:
            Lista de eventos de amenaza.
        """
        return [
            t.to_dict()
            for t in list(self._threat_history)[-limit:]
        ]

    def get_threat_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de amenazas.

        Returns:
            Dict con estadísticas.
        """
        stats: Dict[str, Any] = {
            "total_threats": len(self._threat_history),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "blacklist_size": len(self.get_blacklist()),
            "active_profiles": len(self._device_profiles),
        }

        for threat in self._threat_history:
            stats["by_type"][threat.threat_type] += 1
            stats["by_severity"][threat.severity] += 1

        return dict(stats)
