"""
auth — Autenticación Avanzada
Nova Homonexus — SENTINEL

Sistema de autenticación multicapa:
  - API keys con rotación automática cada 24h
  - JWT tokens para sesiones de monitoreo
  - Fingerprinting de dispositivo Z Fold
  - Rate limiting por dispositivo y endpoint
  - Bloqueo automático tras intentos fallidos
"""

import os
import json
import time
import hmac
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from collections import defaultdict
from dataclasses import dataclass, field

import jwt as pyjwt
from flask import request, jsonify, g

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.auth")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DeviceFingerprint:
    """Fingerprint de hardware del dispositivo Z Fold."""
    device_id: str
    hardware_id: str
    android_id: str
    board: str
    brand: str
    model: str
    build_fingerprint: str
    serial_number: str  # anonimizado
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "hardware_id": self.hardware_id[-8:],  # solo últimos 8 chars
            "model": self.model,
            "timestamp": self.timestamp,
        }

    def verify(self, expected_prefix: str) -> Tuple[bool, str]:
        """
        Verifica que el fingerprint coincida con lo esperado.

        Args:
            expected_prefix: Prefijo esperado del hardware_id.

        Returns:
            (válido, razón)
        """
        if not self.hardware_id.startswith(expected_prefix):
            return False, (
                f"hardware_id no coincide con prefijo esperado: "
                f"{expected_prefix}"
            )
        if not self.device_id:
            return False, "device_id vacío"
        if time.time() - self.timestamp > 60:
            return False, "fingerprint expirado (>60s)"
        return True, "ok"


@dataclass
class RateLimitState:
    """Estado de rate limiting para un dispositivo o IP."""
    counts: List[float] = field(default_factory=list)
    blocked_until: float = 0.0
    failed_attempts: List[float] = field(default_factory=list)


# =============================================================================
# AUTH MANAGER
# =============================================================================

class AuthManager:
    """
    Gestor de autenticación avanzada del sistema Centinela.

    Características:
      - API keys rotativas cada 24h
      - JWT para sesiones de monitoreo
      - Fingerprinting de dispositivo
      - Rate limiting por dispositivo/IP
      - Bloqueo automático
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        auth_cfg = self._rules.auth

        # API keys
        self._api_key_current: str = ""
        self._api_key_previous: str = ""
        self._api_key_rotated_at: float = 0.0
        self._rotation_interval = auth_cfg.get(
            "api_key_rotation_hours", 24
        ) * 3600

        # JWT
        self._jwt_secret: str = os.getenv(
            "SENTINEL_JWT_SECRET",
            hashlib.sha256(
                str(uuid.uuid4()).encode()
            ).hexdigest()
        )
        self._jwt_algorithm = auth_cfg.get("jwt_algorithm", "HS256")
        self._jwt_expiration = auth_cfg.get("jwt_expiration_minutes", 60)
        self._jwt_refresh_days = auth_cfg.get(
            "jwt_refresh_expiration_days", 7
        )

        # Rate limiting
        self._rate_limit_per_minute = auth_cfg.get(
            "rate_limit_per_minute", 600
        )
        self._rate_limit_window = auth_cfg.get("rate_limit_window", 60)
        self._rate_states: Dict[str, RateLimitState] = defaultdict(
            RateLimitState
        )

        # Bloqueo
        self._max_failed = auth_cfg.get("max_failed_attempts", 5)
        self._failed_window = auth_cfg.get("failed_attempts_window", 60)
        self._lockout_duration = auth_cfg.get("lockout_duration", 300)

        # Dispositivos autorizados
        self._authorized_devices = set(
            auth_cfg.get("authorized_devices", [])
        )
        self._expected_fingerprint_prefix = auth_cfg.get(
            "expected_fingerprint_prefix", "ZFOLD-NHX-"
        )

        # Inicializar primera API key
        self._rotate_api_key()

        logger.info(
            "AuthManager inicializado. "
            "Rate limit: %d/min, Max intentos: %d",
            self._rate_limit_per_minute,
            self._max_failed,
        )

    # ------------------------------------------------------------------
    # API KEYS
    # ------------------------------------------------------------------

    def _rotate_api_key(self) -> None:
        """Genera una nueva API key y mueve la actual a 'anterior'."""
        self._api_key_previous = self._api_key_current
        self._api_key_current = (
            f"NHX-{secrets.token_hex(24).upper()}"
        )
        self._api_key_rotated_at = time.time()
        logger.info(
            "API key rotada. Nueva: %s...",
            self._api_key_current[:12],
        )

    def get_current_api_key(self) -> str:
        """
        Obtiene la API key actual.

        Returns:
            API key vigente.
        """
        self._check_rotation()
        return self._api_key_current

    def get_previous_api_key(self) -> str:
        """
        Obtiene la API key anterior (válida por ventana de solapamiento).

        Returns:
            API key anterior.
        """
        return self._api_key_previous

    def _check_rotation(self) -> None:
        """Verifica si es necesario rotar la API key."""
        elapsed = time.time() - self._api_key_rotated_at
        if elapsed >= self._rotation_interval:
            self._rotate_api_key()

    def validate_api_key(self, key: Optional[str]) -> Tuple[bool, str]:
        """
        Valida una API key contra la actual o la anterior.

        Args:
            key: API key a validar.

        Returns:
            (válida, razón)
        """
        if not key:
            return False, "API key no proporcionada"

        self._check_rotation()

        if hmac.compare_digest(key, self._api_key_current):
            return True, "ok"
        if self._api_key_previous and hmac.compare_digest(
            key, self._api_key_previous
        ):
            return True, "ok (key anterior)"
        return False, "API key inválida"

    # ------------------------------------------------------------------
    # JWT TOKENS
    # ------------------------------------------------------------------

    def create_jwt(
        self,
        device_id: str,
        session_id: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Crea un JWT para una sesión de monitoreo.

        Args:
            device_id: Identificador del dispositivo.
            session_id: ID de sesión (opcional).
            extra_claims: Claims adicionales.

        Returns:
            Token JWT codificado.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "nova-homonexus-centinela",
            "sub": device_id,
            "iat": now,
            "exp": now + timedelta(minutes=self._jwt_expiration),
            "jti": str(uuid.uuid4()),
            "device_id": device_id,
            "session_id": session_id or str(uuid.uuid4()),
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        token = pyjwt.encode(
            payload, self._jwt_secret, algorithm=self._jwt_algorithm
        )
        logger.debug(
            "JWT creado para %s, expira en %d min",
            device_id,
            self._jwt_expiration,
        )
        return token

    def create_refresh_token(self, device_id: str) -> str:
        """
        Crea un refresh token de larga duración.

        Args:
            device_id: Identificador del dispositivo.

        Returns:
            Refresh token JWT.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "nova-homonexus-centinela",
            "sub": device_id,
            "iat": now,
            "exp": now + timedelta(days=self._jwt_refresh_days),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return pyjwt.encode(
            payload, self._jwt_secret, algorithm=self._jwt_algorithm
        )

    def validate_jwt(
        self, token: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Valida un JWT y devuelve su payload.

        Args:
            token: Token JWT a validar.

        Returns:
            (válido, payload, razón)
        """
        try:
            payload = pyjwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
                issuer="nova-homonexus-centinela",
            )
            return True, payload, "ok"
        except pyjwt.ExpiredSignatureError:
            return False, {}, "Token expirado"
        except pyjwt.InvalidIssuerError:
            return False, {}, "Issuer inválido"
        except pyjwt.InvalidTokenError as e:
            return False, {}, f"Token inválido: {e}"

    def refresh_jwt(self, refresh_token: str) -> Tuple[bool, str, str]:
        """
        Refresca un JWT usando un refresh token.

        Args:
            refresh_token: Refresh token JWT.

        Returns:
            (éxito, nuevo_access_token, razón)
        """
        valido, payload, razon = self.validate_jwt(refresh_token)
        if not valido:
            return False, "", razon
        if payload.get("type") != "refresh":
            return False, "", "No es un refresh token"

        device_id = payload.get("sub", "")
        new_token = self.create_jwt(device_id)
        return True, new_token, "ok"

    # ------------------------------------------------------------------
    # FINGERPRINTING
    # ------------------------------------------------------------------

    def verify_fingerprint(
        self, fingerprint_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Verifica el fingerprint de hardware del Z Fold.

        Args:
            fingerprint_data: Datos de fingerprint del dispositivo.

        Returns:
            (válido, razón)
        """
        try:
            fp = DeviceFingerprint(
                device_id=fingerprint_data.get("device_id", ""),
                hardware_id=fingerprint_data.get("hardware_id", ""),
                android_id=fingerprint_data.get("android_id", ""),
                board=fingerprint_data.get("board", ""),
                brand=fingerprint_data.get("brand", ""),
                model=fingerprint_data.get("model", ""),
                build_fingerprint=fingerprint_data.get(
                    "build_fingerprint", ""
                ),
                serial_number=fingerprint_data.get("serial_number", ""),
                timestamp=fingerprint_data.get("timestamp", 0),
            )
            return fp.verify(self._expected_fingerprint_prefix)
        except (KeyError, TypeError, ValueError) as e:
            return False, f"Fingerprint malformado: {e}"

    def is_authorized_device(self, device_id: str) -> bool:
        """
        Verifica si un device_id está autorizado.

        Args:
            device_id: Identificador del dispositivo.

        Returns:
            True si está autorizado.
        """
        return device_id in self._authorized_devices

    # ------------------------------------------------------------------
    # RATE LIMITING
    # ------------------------------------------------------------------

    def check_rate_limit(
        self, key: str, endpoint: str = "default"
    ) -> Tuple[bool, int, int]:
        """
        Verifica rate limiting para una clave (IP o device_id).

        Args:
            key: Clave para rate limiting (IP o device_id).
            endpoint: Endpoint al que se accede.

        Returns:
            (permitido, intentos_actuales, límite)
        """
        now = time.time()
        state = self._rate_states[key]

        # Verificar si está bloqueado
        if state.blocked_until > now:
            remaining = int(state.blocked_until - now)
            logger.warning(
                "Rate limit: %s bloqueado por %ds", key, remaining
            )
            return False, 0, 0

        # Limpiar entradas antiguas
        cutoff = now - self._rate_limit_window
        state.counts = [t for t in state.counts if t > cutoff]

        # Determinar límite según endpoint
        limite = self._rate_limit_per_minute
        if endpoint in ("sensor", "health"):
            limite = self._rate_limit_per_minute
        elif endpoint in ("auth", "admin"):
            limite = self._rules.auth.get(
                "rate_limit_critical_per_minute", 60
            )

        # Verificar límite
        if len(state.counts) >= limite:
            logger.warning(
                "Rate limit excedido para %s: %d/%d",
                key,
                len(state.counts),
                limite,
            )
            return False, len(state.counts), limite

        state.counts.append(now)
        return True, len(state.counts) + 1, limite

    # ------------------------------------------------------------------
    # BLOQUEO POR INTENTOS FALLIDOS
    # ------------------------------------------------------------------

    def register_failed_attempt(self, key: str) -> Tuple[bool, int]:
        """
        Registra un intento fallido de autenticación.

        Args:
            key: Clave (IP o device_id).

        Returns:
            (bloqueado, número_de_intentos)
        """
        now = time.time()
        state = self._rate_states[key]

        # Limpiar intentos antiguos
        cutoff = now - self._failed_window
        state.failed_attempts = [
            t for t in state.failed_attempts if t > cutoff
        ]
        state.failed_attempts.append(now)

        attempt_count = len(state.failed_attempts)

        if attempt_count >= self._max_failed:
            state.blocked_until = now + self._lockout_duration
            logger.warning(
                "BLOQUEO: %s bloqueado por %ds tras %d intentos fallidos",
                key,
                self._lockout_duration,
                attempt_count,
            )
            return True, attempt_count

        return False, attempt_count

    def reset_failed_attempts(self, key: str) -> None:
        """Resetea los intentos fallidos para una clave."""
        state = self._rate_states[key]
        state.failed_attempts = []
        state.blocked_until = 0.0
        logger.debug("Intentos fallidos reseteados para %s", key)

    # ------------------------------------------------------------------
    # MIDDLEWARE FLASK
    # ------------------------------------------------------------------

    def authenticate_request(
        self,
        require_device: bool = True,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Middleware de autenticación para Flask.
        Verifica API key o JWT, rate limiting y dispositivo.

        Args:
            require_device: Si True, requiere device_id válido.

        Returns:
            (autenticado, razón, datos_extra)
        """
        client_ip = request.remote_addr or "unknown"
        device_id = (
            request.headers.get("X-Device-ID")
            or request.args.get("device_id")
            or "unknown"
        )

        # 1. Rate limiting por IP
        permitido, count, limite = self.check_rate_limit(client_ip)
        if not permitido:
            return False, (
                f"Rate limit excedido. Límite: {limite}/min. "
                f"Intente en {self._lockout_duration}s"
            ), None

        # 2. Verificar API key (header o query param)
        api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization", "").replace(
                "Bearer ", ""
            )
            or request.args.get("api_key")
        )

        if api_key:
            valida, razon = self.validate_api_key(api_key)
            if not valida:
                bloqueado, intentos = self.register_failed_attempt(
                    client_ip
                )
                return False, (
                    f"API key inválida. "
                    f"Intento {intentos}/{self._max_failed}"
                ), None
            # Resetear intentos si la key es válida
            self.reset_failed_attempts(client_ip)
        else:
            # Intentar con JWT
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("JWT "):
                token = auth_header[4:]
                valido, payload, razon = self.validate_jwt(token)
                if not valido:
                    return False, f"JWT inválido: {razon}", None
                device_id = payload.get("device_id", device_id)
            else:
                return False, (
                    "Autenticación requerida. "
                    "Use X-API-Key o Authorization: JWT <token>"
                ), None

        # 3. Verificar dispositivo autorizado
        if require_device and not self.is_authorized_device(device_id):
            return False, (
                f"Dispositivo no autorizado: {device_id}"
            ), None

        return True, "ok", {
            "device_id": device_id,
            "client_ip": client_ip,
        }

    def get_auth_data(self) -> Dict[str, Any]:
        """
        Obtiene información del estado de autenticación.

        Returns:
            Dict con estado de auth.
        """
        self._check_rotation()
        return {
            "api_key_rotated_at": datetime.fromtimestamp(
                self._api_key_rotated_at, tz=timezone.utc
            ).isoformat(),
            "api_key_next_rotation": datetime.fromtimestamp(
                self._api_key_rotated_at + self._rotation_interval,
                tz=timezone.utc,
            ).isoformat(),
            "jwt_expiration_minutes": self._jwt_expiration,
            "rate_limit_per_minute": self._rate_limit_per_minute,
            "authorized_devices": list(self._authorized_devices),
            "active_rate_states": len(self._rate_states),
        }
