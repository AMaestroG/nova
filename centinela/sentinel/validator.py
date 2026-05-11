"""
validator — Validación de Datos Entrantes
Nova Homonexus — SENTINEL

Valida todos los datos que ingresan al sistema:
  - Rangos de sensores Z Fold y Watch 8
  - Detección de inyección SQL/NoSQL
  - Sanitización de JSON
  - Rechazo de timestamps inválidos
"""

import json
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List, Union
from functools import wraps

from flask import request, jsonify

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.validator")


# =============================================================================
# PATRONES DE DETECCIÓN DE INYECCIÓN
# =============================================================================

# Patrones de inyección SQL
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\bSELECT\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bINSERT\b.*\bINTO\b)", re.IGNORECASE),
    re.compile(r"(\bUPDATE\b.*\bSET\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
    re.compile(r"(\bALTER\b.*\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bEXEC\b|\bEXECUTE\b)", re.IGNORECASE),
    re.compile(r"(\bOR\b.*\b1\s*=\s*1\b)", re.IGNORECASE),
    re.compile(r"(\bAND\b.*\b1\s*=\s*1\b)", re.IGNORECASE),
    re.compile(r"'?\s*--\s*$"),
    re.compile(r"'\s*;\s*$"),
    re.compile(r"'\s*OR\s*'1'\s*=\s*'1"),
    re.compile(r"'\s*OR\s*1\s*=\s*1\s*--"),
    re.compile(r"\bpg_sleep\b", re.IGNORECASE),
    re.compile(r"\bWAITFOR\b.*\bDELAY\b", re.IGNORECASE),
    re.compile(r"\bbenchmark\b", re.IGNORECASE),
]

# Patrones de inyección NoSQL (MongoDB)
NOSQL_INJECTION_PATTERNS = [
    re.compile(r"\$where\b"),
    re.compile(r"\$ne\b"),
    re.compile(r"\$gt\b"),
    re.compile(r"\$regex\b"),
    re.compile(r"\$exists\b"),
    re.compile(r"\{\s*\$"),
    re.compile(r"ne\s*:\s*null"),
]

# Patrones de payload malicioso
MALICIOUS_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"__proto__\b"),
    re.compile(r"constructor\b"),
    re.compile(r"prototype\b"),
    re.compile(r"\bprocess\.env\b"),
    re.compile(r"\brequire\s*\("),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bsystem\s*\("),
    re.compile(r"\bspawn\s*\("),
    re.compile(r"\bfs\.\b"),
    re.compile(r"\bchild_process\b"),
]


# =============================================================================
# DATA VALIDATOR
# =============================================================================

class DataValidator:
    """
    Validador de datos entrantes para el sistema Centinela.

    Valida:
      - Rangos de sensores del Z Fold
      - Rangos biométricos del Watch 8
      - Inyección SQL/NoSQL
      - Sanitización JSON
      - Timestamps válidos
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        self._sensor_ranges = self._rules.sensor_ranges
        self._health_ranges = self._rules.health_ranges

        # Timestamp: máximo 1 hora en el futuro o pasado
        self._max_timestamp_delta = timedelta(hours=1)

        logger.info(
            "DataValidator inicializado con %d tipos de sensor",
            len(self._sensor_ranges),
        )

    # ------------------------------------------------------------------
    # VALIDACIÓN DE SENSORES Z FOLD
    # ------------------------------------------------------------------

    def validate_sensor_data(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Valida una lectura de sensor del Z Fold.

        Args:
            data: Datos del sensor.

        Returns:
            (válido, razón, datos_normalizados)
        """
        tipo = data.get("tipo_sensor", "")
        valor = data.get("valor", {})

        if not tipo:
            return False, "tipo_sensor es requerido", None
        if not isinstance(valor, dict):
            return False, "valor debe ser un objeto JSON", None

        # Validar según tipo de sensor
        validators = {
            "acelerometro": self._validate_accelerometer,
            "giroscopio": self._validate_gyroscope,
            "magnetometro": self._validate_magnetometer,
            "barometro": self._validate_barometer,
            "luz_ambiental": self._validate_light,
            "proximidad": self._validate_proximity,
            "gps": self._validate_gps,
            "temperatura": self._validate_temperature,
            "humedad": self._validate_humidity,
        }

        validator = validators.get(tipo)
        if not validator:
            return False, f"Tipo de sensor desconocido: {tipo}", None

        return validator(valor, data)

    def _validate_accelerometer(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida acelerómetro: ±16g en 3 ejes."""
        ranges = self._sensor_ranges.get("acelerometro", {})
        for eje in ("x", "y", "z"):
            v = valor.get(eje)
            if v is None:
                return False, f"acelerometro.{eje} requerido", None
            if not isinstance(v, (int, float)):
                return False, f"acelerometro.{eje} debe ser numérico", None
            if v < ranges.get(f"min_{eje}", -16) or v > ranges.get(
                f"max_{eje}", 16
            ):
                return False, (
                    f"acelerometro.{eje}={v} fuera de rango "
                    f"[{ranges.get(f'min_{eje}', -16)}, "
                    f"{ranges.get(f'max_{eje}', 16)}]"
                ), None
        return True, "ok", data

    def _validate_gyroscope(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida giroscopio: ±2000 dps en 3 ejes."""
        ranges = self._sensor_ranges.get("giroscopio", {})
        for eje in ("x", "y", "z"):
            v = valor.get(eje)
            if v is None:
                return False, f"giroscopio.{eje} requerido", None
            if not isinstance(v, (int, float)):
                return False, f"giroscopio.{eje} debe ser numérico", None
            if v < ranges.get(f"min_{eje}", -2000) or v > ranges.get(
                f"max_{eje}", 2000
            ):
                return False, (
                    f"giroscopio.{eje}={v} fuera de rango "
                    f"[{ranges.get(f'min_{eje}', -2000)}, "
                    f"{ranges.get(f'max_{eje}', 2000)}]"
                ), None
        return True, "ok", data

    def _validate_magnetometer(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida magnetómetro: ±4900 µT en 3 ejes."""
        ranges = self._sensor_ranges.get("magnetometro", {})
        for eje in ("x", "y", "z"):
            v = valor.get(eje)
            if v is None:
                return False, f"magnetometro.{eje} requerido", None
            if not isinstance(v, (int, float)):
                return False, f"magnetometro.{eje} debe ser numérico", None
            if v < ranges.get(f"min_{eje}", -4900) or v > ranges.get(
                f"max_{eje}", 4900
            ):
                return False, (
                    f"magnetometro.{eje}={v} fuera de rango "
                    f"[{ranges.get(f'min_{eje}', -4900)}, "
                    f"{ranges.get(f'max_{eje}', 4900)}]"
                ), None
        return True, "ok", data

    def _validate_barometer(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida barómetro: 300-1100 hPa."""
        ranges = self._sensor_ranges.get("barometro", {})
        v = valor.get("presion") or valor.get("valor") or valor.get("x")
        if v is None:
            return False, "barometro.presion requerido", None
        if not isinstance(v, (int, float)):
            return False, "barometro.presion debe ser numérico", None
        min_v = ranges.get("min_val", 300)
        max_v = ranges.get("max_val", 1100)
        if v < min_v or v > max_v:
            return False, (
                f"barometro.presion={v} fuera de rango [{min_v}, {max_v}]"
            ), None
        return True, "ok", data

    def _validate_light(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida luz ambiental: 0-65535 lux."""
        ranges = self._sensor_ranges.get("luz_ambiental", {})
        v = valor.get("lux") or valor.get("valor") or valor.get("x")
        if v is None:
            return False, "luz_ambiental.lux requerido", None
        if not isinstance(v, (int, float)):
            return False, "luz_ambiental.lux debe ser numérico", None
        min_v = ranges.get("min_val", 0)
        max_v = ranges.get("max_val", 65535)
        if v < min_v or v > max_v:
            return False, (
                f"luz_ambiental={v} fuera de rango [{min_v}, {max_v}]"
            ), None
        return True, "ok", data

    def _validate_proximity(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida proximidad: 0-5 cm."""
        ranges = self._sensor_ranges.get("proximidad", {})
        v = valor.get("distancia") or valor.get("valor")
        if v is None:
            return False, "proximidad.distancia requerido", None
        if not isinstance(v, (int, float)):
            return False, "proximidad.distancia debe ser numérico", None
        min_v = ranges.get("min_val", 0)
        max_v = ranges.get("max_val", 5)
        if v < min_v or v > max_v:
            return False, (
                f"proximidad={v} fuera de rango [{min_v}, {max_v}]"
            ), None
        return True, "ok", data

    def _validate_gps(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida GPS: lat[-90,90], lon[-180,180], alt[-500,9000]."""
        ranges = self._sensor_ranges.get("gps", {})
        lat = valor.get("lat")
        lon = valor.get("lon")
        if lat is None or lon is None:
            return False, "gps.lat y gps.lon requeridos", None
        if not isinstance(lat, (int, float)) or not isinstance(
            lon, (int, float)
        ):
            return False, "lat y lon deben ser numéricos", None
        if lat < ranges.get("lat_min", -90) or lat > ranges.get(
            "lat_max", 90
        ):
            return False, (
                f"lat={lat} fuera de rango "
                f"[{ranges.get('lat_min', -90)}, "
                f"{ranges.get('lat_max', 90)}]"
            ), None
        if lon < ranges.get("lon_min", -180) or lon > ranges.get(
            "lon_max", 180
        ):
            return False, (
                f"lon={lon} fuera de rango "
                f"[{ranges.get('lon_min', -180)}, "
                f"{ranges.get('lon_max', 180)}]"
            ), None
        # Altitud opcional
        alt = valor.get("altitud")
        if alt is not None:
            if not isinstance(alt, (int, float)):
                return False, "altitud debe ser numérico", None
            if alt < ranges.get("alt_min", -500) or alt > ranges.get(
                "alt_max", 9000
            ):
                return False, (
                    f"altitud={alt} fuera de rango "
                    f"[{ranges.get('alt_min', -500)}, "
                    f"{ranges.get('alt_max', 9000)}]"
                ), None
        return True, "ok", data

    def _validate_temperature(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida temperatura ambiente: -40 a 85°C."""
        ranges = self._sensor_ranges.get("temperatura", {})
        v = valor.get("temp") or valor.get("valor")
        if v is None:
            return False, "temperatura.temp requerido", None
        if not isinstance(v, (int, float)):
            return False, "temperatura debe ser numérico", None
        min_v = ranges.get("min_val", -40)
        max_v = ranges.get("max_val", 85)
        if v < min_v or v > max_v:
            return False, (
                f"temperatura={v} fuera de rango [{min_v}, {max_v}]"
            ), None
        return True, "ok", data

    def _validate_humidity(
        self, valor: Dict, data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Valida humedad: 0-100%."""
        ranges = self._sensor_ranges.get("humedad", {})
        v = valor.get("humedad") or valor.get("valor")
        if v is None:
            return False, "humedad.humedad requerido", None
        if not isinstance(v, (int, float)):
            return False, "humedad debe ser numérico", None
        min_v = ranges.get("min_val", 0)
        max_v = ranges.get("max_val", 100)
        if v < min_v or v > max_v:
            return False, (
                f"humedad={v} fuera de rango [{min_v}, {max_v}]"
            ), None
        return True, "ok", data

    # ------------------------------------------------------------------
    # VALIDACIÓN DE DATOS DE SALUD (WATCH 8)
    # ------------------------------------------------------------------

    def validate_health_data(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Valida datos biométricos del Galaxy Watch 8 Classic.

        Args:
            data: Datos de salud.

        Returns:
            (válido, razón, datos_normalizados)
        """
        ranges = self._health_ranges

        # Heart Rate
        hr = data.get("heart_rate")
        if hr is not None:
            if not isinstance(hr, (int, float)):
                return False, "heart_rate debe ser numérico", None
            hr_min = ranges.get("heart_rate_min", 30)
            hr_max = ranges.get("heart_rate_max", 220)
            if hr < hr_min or hr > hr_max:
                return False, (
                    f"heart_rate={hr} fuera de rango [{hr_min}, {hr_max}]"
                ), None

        # Presión arterial sistólica
        bps = data.get("blood_pressure_sys")
        if bps is not None:
            if not isinstance(bps, (int, float)):
                return False, (
                    "blood_pressure_sys debe ser numérico"
                ), None
            bps_min = ranges.get("blood_pressure_sys_min", 70)
            bps_max = ranges.get("blood_pressure_sys_max", 250)
            if bps < bps_min or bps > bps_max:
                return False, (
                    f"blood_pressure_sys={bps} fuera de rango "
                    f"[{bps_min}, {bps_max}]"
                ), None

        # Presión arterial diastólica
        bpd = data.get("blood_pressure_dia")
        if bpd is not None:
            if not isinstance(bpd, (int, float)):
                return False, (
                    "blood_pressure_dia debe ser numérico"
                ), None
            bpd_min = ranges.get("blood_pressure_dia_min", 40)
            bpd_max = ranges.get("blood_pressure_dia_max", 150)
            if bpd < bpd_min or bpd > bpd_max:
                return False, (
                    f"blood_pressure_dia={bpd} fuera de rango "
                    f"[{bpd_min}, {bpd_max}]"
                ), None

        # SpO2
        spo2 = data.get("spo2")
        if spo2 is not None:
            if not isinstance(spo2, (int, float)):
                return False, "spo2 debe ser numérico", None
            spo2_min = ranges.get("spo2_min", 70.0)
            spo2_max = ranges.get("spo2_max", 100.0)
            if spo2 < spo2_min or spo2 > spo2_max:
                return False, (
                    f"spo2={spo2} fuera de rango [{spo2_min}, {spo2_max}]"
                ), None

        # Temperatura piel
        temp = data.get("temperature_skin")
        if temp is not None:
            if not isinstance(temp, (int, float)):
                return False, (
                    "temperature_skin debe ser numérico"
                ), None
            t_min = ranges.get("temperature_skin_min", 35.0)
            t_max = ranges.get("temperature_skin_max", 42.0)
            if temp < t_min or temp > t_max:
                return False, (
                    f"temperature_skin={temp} fuera de rango "
                    f"[{t_min}, {t_max}]"
                ), None

        # Estrés
        stress = data.get("stress_level")
        if stress is not None:
            if not isinstance(stress, (int, float)):
                return False, "stress_level debe ser numérico", None
            s_min = ranges.get("stress_min", 0)
            s_max = ranges.get("stress_max", 100)
            if stress < s_min or stress > s_max:
                return False, (
                    f"stress_level={stress} fuera de rango "
                    f"[{s_min}, {s_max}]"
                ), None

        # HRV
        hrv = data.get("hrv")
        if hrv is not None:
            if not isinstance(hrv, (int, float)):
                return False, "hrv debe ser numérico", None
            hrv_min = ranges.get("hrv_min", 10.0)
            hrv_max = ranges.get("hrv_max", 200.0)
            if hrv < hrv_min or hrv > hrv_max:
                return False, (
                    f"hrv={hrv} fuera de rango [{hrv_min}, {hrv_max}]"
                ), None

        # Batería
        bat = data.get("battery_level")
        if bat is not None:
            if not isinstance(bat, (int, float)):
                return False, "battery_level debe ser numérico", None
            b_min = ranges.get("battery_min", 0)
            b_max = ranges.get("battery_max", 100)
            if bat < b_min or bat > b_max:
                return False, (
                    f"battery_level={bat} fuera de rango "
                    f"[{b_min}, {b_max}]"
                ), None

        # Bioimpedancia BIA
        bia = data.get("bioimpedance")
        if bia and isinstance(bia, dict):
            checks = [
                ("bia_body_fat", "bia_body_fat_min", "bia_body_fat_max"),
                (
                    "bia_muscle_mass",
                    "bia_muscle_mass_min",
                    "bia_muscle_mass_max",
                ),
                ("bia_bone_mass", "bia_bone_mass_min", "bia_bone_mass_max"),
                (
                    "bia_body_water",
                    "bia_body_water_min",
                    "bia_body_water_max",
                ),
                ("bia_bmr", "bia_bmr_min", "bia_bmr_max"),
            ]
            for field, min_key, max_key in checks:
                val = bia.get(field) or data.get(field)
                if val is not None:
                    if not isinstance(val, (int, float)):
                        return False, f"{field} debe ser numérico", None
                    mn = ranges.get(min_key, 0)
                    mx = ranges.get(max_key, 100)
                    if val < mn or val > mx:
                        return False, (
                            f"{field}={val} fuera de rango [{mn}, {mx}]"
                        ), None

        return True, "ok", data

    # ------------------------------------------------------------------
    # VALIDACIÓN DE TIMESTAMPS
    # ------------------------------------------------------------------

    def validate_timestamp(
        self, ts_str: Optional[str]
    ) -> Tuple[bool, str, Optional[datetime]]:
        """
        Valida un timestamp ISO 8601.

        Rechaza:
          - Timestamps futuros (>1h adelante)
          - Timestamps muy antiguos (>1h atrás)
          - Formatos inválidos

        Args:
            ts_str: Timestamp en string ISO 8601.

        Returns:
            (válido, razón, datetime_parsed)
        """
        if not ts_str:
            return True, "sin timestamp (se usará now)", None

        try:
            ts = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return False, (
                f"Formato de timestamp inválido: {ts_str}"
            ), None

        now = datetime.now(timezone.utc)

        # Asegurar timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Verificar límites
        if ts > now + self._max_timestamp_delta:
            return False, (
                f"Timestamp futuro ({ts.isoformat()}) "
                f"excede el máximo permitido de 1 hora"
            ), None

        if ts < now - self._max_timestamp_delta:
            return False, (
                f"Timestamp muy antiguo ({ts.isoformat()}) "
                f"supera el límite de 1 hora"
            ), None

        return True, "ok", ts

    # ------------------------------------------------------------------
    # DETECCIÓN DE INYECCIÓN
    # ------------------------------------------------------------------

    def detect_injection(
        self, data: Any, depth: int = 0
    ) -> Tuple[bool, str]:
        """
        Detecta intentos de inyección SQL/NoSQL en los datos.

        Args:
            data: Datos a escanear (dict, list, str, etc.).
            depth: Profundidad actual de recursión.

        Returns:
            (limpio, razón)
        """
        max_depth = self._rules.threat.get("max_json_depth", 10)
        if depth > max_depth:
            return False, "Profundidad máxima de JSON excedida"

        if isinstance(data, str):
            # Escanear strings
            for pattern in SQL_INJECTION_PATTERNS:
                if pattern.search(data):
                    return False, (
                        f"Posible inyección SQL detectada: {pattern.pattern}"
                    )
            for pattern in NOSQL_INJECTION_PATTERNS:
                if pattern.search(data):
                    return False, (
                        f"Posible inyección NoSQL detectada: "
                        f"{pattern.pattern}"
                    )
            for pattern in MALICIOUS_PATTERNS:
                if pattern.search(data):
                    return False, (
                        f"Payload malicioso detectado: {pattern.pattern}"
                    )

        elif isinstance(data, dict):
            # Escanear claves y valores
            for key, value in data.items():
                if isinstance(key, str):
                    limpio, razon = self.detect_injection(key, depth + 1)
                    if not limpio:
                        return False, razon
                limpio, razon = self.detect_injection(value, depth + 1)
                if not limpio:
                    return False, razon

        elif isinstance(data, list):
            for item in data:
                limpio, razon = self.detect_injection(item, depth + 1)
                if not limpio:
                    return False, razon

        return True, "ok"

    # ------------------------------------------------------------------
    # SANITIZACIÓN DE DATOS
    # ------------------------------------------------------------------

    def sanitize_json(
        self, data: Any
    ) -> Tuple[bool, Any, str]:
        """
        Sanitiza datos JSON entrantes.

        Elimina:
          - Campos con valores None (opcional)
          - Strings con solo espacios
          - Caracteres de control no imprimibles

        Args:
            data: Datos a sanitizar.

        Returns:
            (modificado, datos_sanitizados, razón)
        """
        if isinstance(data, str):
            # Eliminar caracteres de control (excepto \n, \r, \t)
            cleaned = re.sub(
                r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", data
            )
            cleaned = cleaned.strip()
            if cleaned != data:
                return True, cleaned, "caracteres de control eliminados"
            return False, data, "sin cambios"

        if isinstance(data, dict):
            result = {}
            modificado = False
            for key, value in data.items():
                if isinstance(key, str):
                    k_mod, k_clean, _ = self.sanitize_json(key)
                    if k_mod:
                        modificado = True
                else:
                    k_clean = key
                v_mod, v_clean, _ = self.sanitize_json(value)
                if v_mod:
                    modificado = True
                result[k_clean] = v_clean
            return modificado, result, (
                "sanitizado" if modificado else "sin cambios"
            )

        if isinstance(data, list):
            result = []
            modificado = False
            for item in data:
                m, cleaned, _ = self.sanitize_json(item)
                if m:
                    modificado = True
                result.append(cleaned)
            return modificado, result, (
                "sanitizado" if modificado else "sin cambios"
            )

        return False, data, "sin cambios"

    # ------------------------------------------------------------------
    # VALIDACIÓN COMPLETA DE PAYLOAD
    # ------------------------------------------------------------------

    def validate_payload(
        self, data: Dict[str, Any], payload_type: str = "sensor"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validación completa de un payload entrante.

        Incluye:
          - Sanitización
          - Detección de inyección
          - Validación de timestamp
          - Validación de rangos según tipo

        Args:
            data: Payload a validar.
            payload_type: Tipo de payload (sensor, health, ubicacion, etc.).

        Returns:
            (válido, razón, datos_validados)
        """
        # 1. Sanitizar
        _, sanitized, _ = self.sanitize_json(data)

        # 2. Detectar inyección
        limpio, razon = self.detect_injection(sanitized)
        if not limpio:
            logger.warning(
                "Inyección detectada en payload %s: %s",
                payload_type,
                razon,
            )
            return False, razon, None

        # 3. Validar timestamp
        ts = sanitized.get("timestamp")
        ts_valido, ts_razon, ts_dt = self.validate_timestamp(ts)
        if not ts_valido:
            return False, f"Timestamp inválido: {ts_razon}", None

        # 4. Validar según tipo
        if payload_type == "sensor":
            return self.validate_sensor_data(sanitized)
        elif payload_type == "health":
            return self.validate_health_data(sanitized)
        elif payload_type == "ubicacion":
            # La ubicación usa el validador GPS
            valor = {
                "lat": sanitized.get("lat"),
                "lon": sanitized.get("lon"),
                "altitud": sanitized.get("altitud"),
            }
            gps_data = {
                "tipo_sensor": "gps",
                "valor": valor,
            }
            valido, razon, _ = self._validate_gps(valor, gps_data)
            if not valido:
                return False, razon, None
            # Return sanitized top-level data so route handler finds lat/lon
            return True, "ok", sanitized
        elif payload_type == "emocion":
            # Validación de emociones: acepta biométricas crudas O emocion pre-detectada
            emocion = sanitized.get("emocion_detectada")
            confianza = sanitized.get("confianza")
            heart_rate = sanitized.get("heart_rate")
            hrv = sanitized.get("hrv")

            # Si viene con emocion pre-detectada, validar confianza
            if emocion:
                if confianza is not None and (
                    not isinstance(confianza, (int, float))
                    or confianza < 0
                    or confianza > 1
                ):
                    return False, (
                        "confianza debe ser un número entre 0 y 1"
                    ), None
            # Si vienen biométricas crudas, la detección se hace en el endpoint
            elif heart_rate or hrv:
                pass  # OK, se detectará en el endpoint
            else:
                return False, "emocion_detectada o heart_rate requeridos", None
            return True, "ok", sanitized
        else:
            return True, "ok", sanitized

    # ------------------------------------------------------------------
    # MIDDLEWARE FLASK
    # ------------------------------------------------------------------

    def validation_middleware(self, payload_type: str = "sensor"):
        """
        Decorador para validar automáticamente los payloads entrantes.

        Args:
            payload_type: Tipo de payload esperado.
        """
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    data = request.get_json(force=True)
                except Exception as e:
                    return jsonify({
                        "error": f"JSON inválido: {e}",
                        "codigo": "INVALID_JSON",
                    }), 400

                if not data:
                    return jsonify({
                        "error": "Body JSON requerido",
                        "codigo": "EMPTY_BODY",
                    }), 400

                valido, razon, datos_validados = self.validate_payload(
                    data, payload_type
                )
                if not valido:
                    logger.warning(
                        "Payload inválido (%s): %s", payload_type, razon
                    )
                    return jsonify({
                        "error": razon,
                        "codigo": "VALIDATION_ERROR",
                    }), 422

                # Inyectar datos validados en el request
                request.validated_data = datos_validados
                return f(*args, **kwargs)
            return wrapper
        return decorator
