"""
privacy_filter — Filtro de Privacidad
Nova Homonexus — SENTINEL

Gestiona la privacidad de los datos:
  - Encriptación AES-256-GCM de datos sensibles
  - Anonimización de ubicación en modo privado
  - Política de retención de datos (7, 30, 90, 365 días)
  - Purga automática de datos expirados
  - Modo privado (ubicación aproximada, no exacta)
"""

import os
import json
import time
import base64
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List, Set
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.privacy")


# =============================================================================
# CONSTANTES
# =============================================================================

# Nonce size for AES-256-GCM
AES_GCM_NONCE_SIZE = 12

# Tag size for AES-256-GCM
AES_GCM_TAG_SIZE = 16

# Key size for AES-256
AES_KEY_SIZE = 32


# =============================================================================
# PRIVACY FILTER
# =============================================================================

class PrivacyFilter:
    """
    Filtro de privacidad del sistema Centinela.

    Características:
      - Encriptación AES-256-GCM de datos sensibles
      - Anonimización de ubicación (modo privado)
      - Política de retención configurable por tipo de dato
      - Purga automática de datos expirados
      - Modo privado (solo zona aproximada)
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        priv_cfg = self._rules.privacy

        # Clave de encriptación
        self._encryption_key: Optional[bytes] = None
        self._load_encryption_key()

        # Algoritmo
        self._algorithm = priv_cfg.get(
            "encryption_algorithm", "AES-256-GCM"
        )

        # Política de retención (días)
        self._retention_days = priv_cfg.get("retention_days", {})

        # Campos sensibles
        self._sensitive_fields: Set[str] = set(
            priv_cfg.get("sensitive_fields", [])
        )

        # Modo privado
        self._private_mode = False
        self._private_radius = priv_cfg.get(
            "private_mode_location_radius", 500
        )

        # Intervalo de purga
        self._purge_interval = priv_cfg.get(
            "purge_interval_hours", 6
        )
        self._last_purge: float = 0.0

        logger.info(
            "PrivacyFilter inicializado. "
            "Encriptación: %s, Campos sensibles: %d, "
            "Retención: %s",
            self._algorithm,
            len(self._sensitive_fields),
            self._retention_days,
        )

    # ------------------------------------------------------------------
    # GESTIÓN DE CLAVES
    # ------------------------------------------------------------------

    def _load_encryption_key(self) -> None:
        """Carga la clave maestra de encriptación."""
        key_env = self._rules.privacy.get(
            "master_key_env", "SENTINEL_ENCRYPTION_KEY"
        )
        key_str = os.getenv(key_env)

        if key_str:
            # Derivar clave de 32 bytes usando HKDF
            salt = b"nova-homonexus-centinela-salt-2026"
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=AES_KEY_SIZE,
                salt=salt,
                info=b"sentinel-encryption-key",
            )
            self._encryption_key = hkdf.derive(
                key_str.encode("utf-8")
            )
            logger.debug(
                "Clave de encriptación cargada desde env: %s",
                key_env,
            )
        else:
            # Clave por defecto (solo para desarrollo!)
            logger.warning(
                "Variable de entorno %s no encontrada. "
                "Usando clave por defecto (SOLO DESARROLLO)",
                key_env,
            )
            self._encryption_key = hashlib.sha256(
                b"sentinel-dev-key-2026"
            ).digest()

    def rotate_encryption_key(self, new_key: str) -> None:
        """
        Rota la clave de encriptación.

        Args:
            new_key: Nueva clave maestra.
        """
        salt = b"nova-homonexus-centinela-salt-2026"
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE,
            salt=salt,
            info=b"sentinel-encryption-key",
        )
        self._encryption_key = hkdf.derive(
            new_key.encode("utf-8")
        )
        logger.info("Clave de encriptación rotada")

    # ------------------------------------------------------------------
    # ENCRIPTACIÓN / DESENCRIPTACIÓN
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Encripta un texto usando AES-256-GCM.

        Args:
            plaintext: Texto a encriptar.

        Returns:
            Texto encriptado en base64 (nonce + ciphertext + tag).
        """
        if not self._encryption_key:
            raise RuntimeError(
                "Clave de encriptación no inicializada"
            )

        aesgcm = AESGCM(self._encryption_key)
        nonce = os.urandom(AES_GCM_NONCE_SIZE)
        ciphertext = aesgcm.encrypt(
            nonce, plaintext.encode("utf-8"), None
        )

        # Codificar como base64: nonce + ciphertext
        result = base64.b64encode(nonce + ciphertext).decode("utf-8")
        return result

    def decrypt(self, encrypted_data: str) -> str:
        """
        Desencripta datos encriptados con AES-256-GCM.

        Args:
            encrypted_data: Datos encriptados en base64.

        Returns:
            Texto desencriptado.
        """
        if not self._encryption_key:
            raise RuntimeError(
                "Clave de encriptación no inicializada"
            )

        try:
            raw = base64.b64decode(encrypted_data)
            nonce = raw[:AES_GCM_NONCE_SIZE]
            ciphertext = raw[AES_GCM_NONCE_SIZE:]

            aesgcm = AESGCM(self._encryption_key)
            plaintext = aesgcm.decrypt(
                nonce, ciphertext, None
            )
            return plaintext.decode("utf-8")
        except Exception as e:
            logger.error("Error al desencriptar: %s", str(e))
            raise

    def encrypt_dict(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Encripta los campos sensibles de un diccionario.

        Args:
            data: Diccionario con datos.

        Returns:
            Diccionario con campos sensibles encriptados.
        """
        result = {}
        for key, value in data.items():
            field_path = key
            if field_path in self._sensitive_fields:
                if isinstance(value, str):
                    result[key] = self.encrypt(value)
                elif isinstance(value, (int, float)):
                    result[key] = self.encrypt(str(value))
                elif isinstance(value, dict):
                    result[key] = self.encrypt(
                        json.dumps(value)
                    )
                elif isinstance(value, list):
                    result[key] = self.encrypt(
                        json.dumps(value)
                    )
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            else:
                result[key] = value
        return result

    def decrypt_dict(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Desencripta los campos sensibles de un diccionario.

        Args:
            data: Diccionario con datos encriptados.

        Returns:
            Diccionario con campos desencriptados.
        """
        result = {}
        for key, value in data.items():
            field_path = key
            if field_path in self._sensitive_fields:
                if isinstance(value, str):
                    try:
                        result[key] = self.decrypt(value)
                    except Exception:
                        result[key] = value
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value)
            else:
                result[key] = value
        return result

    # ------------------------------------------------------------------
    # ANONIMIZACIÓN DE UBICACIÓN
    # ------------------------------------------------------------------

    def anonymize_location(
        self, lat: float, lon: float
    ) -> Tuple[float, float]:
        """
        Anonimiza coordenadas GPS redondeándolas a una cuadrícula.

        En modo privado, la ubicación se aproxima a un radio
        de self._private_radius metros.

        Args:
            lat: Latitud original.
            lon: Longitud original.

        Returns:
            (lat_anonimizada, lon_anonimizada)
        """
        if not self._private_mode:
            return lat, lon

        # Redondear a ~500m de precisión
        # 1 grado de latitud ~= 111km
        # 1 grado de longitud ~= 111km * cos(lat)
        lat_precision = self._private_radius / 111000.0
        lon_precision = self._private_radius / (
            111000.0 * abs(
                __import__("math").cos(
                    __import__("math").radians(lat)
                )
            ) or 1
        )

        anon_lat = round(lat / lat_precision) * lat_precision
        anon_lon = round(lon / lon_precision) * lon_precision

        logger.debug(
            "Ubicación anonimizada: [%.6f, %.6f] -> [%.6f, %.6f]",
            lat,
            lon,
            anon_lat,
            anon_lon,
        )
        return anon_lat, anon_lon

    def set_private_mode(self, enabled: bool) -> None:
        """
        Activa o desactiva el modo privado.

        Args:
            enabled: True para activar modo privado.
        """
        self._private_mode = enabled
        logger.info(
            "Modo privado %s",
            "activado" if enabled else "desactivado",
        )

    def is_private_mode(self) -> bool:
        """Verifica si el modo privado está activo."""
        return self._private_mode

    # ------------------------------------------------------------------
    # POLÍTICA DE RETENCIÓN
    # ------------------------------------------------------------------

    def get_retention_days(self, data_type: str) -> int:
        """
        Obtiene los días de retención para un tipo de dato.

        Args:
            data_type: Tipo de dato (sensor_raw, ubicacion, health, etc.).

        Returns:
            Días de retención.
        """
        return self._retention_days.get(data_type, 30)

    def get_retention_cutoff(
        self, data_type: str
    ) -> datetime:
        """
        Obtiene la fecha límite de retención para un tipo de dato.

        Args:
            data_type: Tipo de dato.

        Returns:
            Fecha límite (datetime UTC).
        """
        days = self.get_retention_days(data_type)
        return datetime.now(timezone.utc) - timedelta(days=days)

    def should_purge(self) -> bool:
        """
        Verifica si es momento de purgar datos expirados.

        Returns:
            True si debe ejecutarse la purga.
        """
        elapsed = time.time() - self._last_purge
        return elapsed >= self._purge_interval * 3600

    def mark_purged(self) -> None:
        """Marca que se ha ejecutado la purga."""
        self._last_purge = time.time()

    # ------------------------------------------------------------------
    # FILTRADO DE DATOS
    # ------------------------------------------------------------------

    def filter_sensor_data(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filtra datos de sensor aplicando políticas de privacidad.

        Args:
            data: Datos del sensor.

        Returns:
            Datos filtrados.
        """
        result = dict(data)

        # Anonimizar ubicación si es GPS
        if data.get("tipo_sensor") == "gps":
            valor = result.get("valor", {})
            if "lat" in valor and "lon" in valor:
                anon_lat, anon_lon = self.anonymize_location(
                    valor["lat"], valor["lon"]
                )
                valor["lat"] = anon_lat
                valor["lon"] = anon_lon

        return result

    def filter_health_data(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filtra datos de salud aplicando políticas de privacidad.

        Encripta datos sensibles como ECG y bioimpedancia.

        Args:
            data: Datos de salud.

        Returns:
            Datos filtrados.
        """
        result = dict(data)

        # Encriptar ECG si está presente
        if "ecg_data" in result and result["ecg_data"] is not None:
            result["ecg_data"] = self.encrypt(
                json.dumps(result["ecg_data"])
            )

        # Encriptar bioimpedancia si está presente
        if (
            "bioimpedance" in result
            and result["bioimpedance"] is not None
        ):
            result["bioimpedance"] = self.encrypt(
                json.dumps(result["bioimpedance"])
            )

        return result

    def filter_emocion_data(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filtra datos emocionales aplicando políticas de privacidad.

        Args:
            data: Datos emocionales.

        Returns:
            Datos filtrados.
        """
        result = dict(data)

        # Anonimizar expresión facial
        if "facial_expression" in result:
            result["facial_expression"] = self.encrypt(
                json.dumps(result["facial_expression"])
            )

        return result

    # ------------------------------------------------------------------
    # PURGA DE DATOS
    # ------------------------------------------------------------------

    def get_purge_queries(self) -> Dict[str, str]:
        """
        Genera consultas SQL para purgar datos expirados.

        Returns:
            Dict con {tabla: consulta_sql}.
        """
        queries = {}
        retention_map = {
            "centinela_sensores": "sensor_raw",
            "centinela_ubicacion": "ubicacion",
            "centinela_health": "health",
            "centinela_emociones": "emocion",
            "centinela_alertas": "alerta",
            "centinela_eventos": "evento",
        }

        for table, data_type in retention_map.items():
            cutoff = self.get_retention_cutoff(data_type)
            queries[table] = (
                f"DELETE FROM {table} "
                f"WHERE timestamp < '{cutoff.isoformat()}'"
            )

        return queries

    # ------------------------------------------------------------------
    # ESTADO
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado del filtro de privacidad.

        Returns:
            Dict con estado.
        """
        return {
            "encryption_enabled": self._encryption_key is not None,
            "encryption_algorithm": self._algorithm,
            "private_mode": self._private_mode,
            "private_radius_m": self._private_radius,
            "sensitive_fields_count": len(self._sensitive_fields),
            "retention_policy": dict(self._retention_days),
            "last_purge": (
                datetime.fromtimestamp(
                    self._last_purge, tz=timezone.utc
                ).isoformat()
                if self._last_purge > 0
                else None
            ),
            "purge_interval_hours": self._purge_interval,
        }
