"""
SecurityRules — Cargador de reglas de seguridad desde YAML
Nova Homonexus — SENTINEL

Proporciona acceso centralizado a todas las reglas, umbrales y
configuraciones de seguridad del sistema Centinela.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("sentinel.rules")

_RULES_CACHE: Optional[Dict[str, Any]] = None
_RULES_PATH = Path(__file__).parent / "rules.yaml"


def load_rules(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Carga las reglas de seguridad desde el archivo YAML.

    Args:
        path: Ruta al archivo YAML. Por defecto rules.yaml junto a este módulo.

    Returns:
        Diccionario con todas las reglas de seguridad.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        yaml.YAMLError: Si el YAML es inválido.
    """
    global _RULES_CACHE
    target = path or _RULES_PATH

    if not target.exists():
        logger.error("Archivo de reglas no encontrado: %s", target)
        raise FileNotFoundError(f"Reglas de seguridad no encontradas: {target}")

    with open(target, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)

    _RULES_CACHE = rules
    logger.info(
        "Reglas de seguridad cargadas: %d secciones",
        len(rules) if rules else 0,
    )
    return rules


def get_rules(refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene las reglas de seguridad (con caché).

    Args:
        refresh: Si True, recarga desde disco ignorando la caché.

    Returns:
        Diccionario completo de reglas.
    """
    global _RULES_CACHE
    if _RULES_CACHE is None or refresh:
        return load_rules()
    return _RULES_CACHE


def get_section(section: str, refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene una sección específica de las reglas.

    Args:
        section: Nombre de la sección (ej. "auth", "sensor_ranges").
        refresh: Si True, recarga desde disco.

    Returns:
        Diccionario con la sección solicitada, o dict vacío si no existe.
    """
    rules = get_rules(refresh=refresh)
    return rules.get(section, {})


def get_threshold(threshold_path: str, default: Any = None) -> Any:
    """
    Obtiene un umbral específico usando notación de puntos.

    Args:
        threshold_path: Ruta al valor, ej. "sensor_ranges.acelerometro.max_x".
        default: Valor por defecto si no se encuentra.

    Returns:
        Valor del umbral o default.
    """
    rules = get_rules()
    parts = threshold_path.split(".")
    current = rules
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return default
        else:
            return default
    return current


class SecurityRules:
    """
    Interfaz de alto nivel para acceder a las reglas de seguridad.

    Uso:
        rules = SecurityRules()
        max_hr = rules.get("sensor_ranges.health.heart_rate_max")
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _RULES_PATH
        self._rules: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Carga (o recarga) las reglas desde el archivo YAML."""
        self._rules = load_rules(self._path)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor usando notación de puntos.

        Args:
            key: Clave en notación de puntos, ej. "auth.jwt_secret".
            default: Valor por defecto.

        Returns:
            Valor encontrado o default.
        """
        return get_threshold(key, default)

    @property
    def auth(self) -> Dict[str, Any]:
        """Configuración de autenticación."""
        return self._rules.get("auth", {})

    @property
    def sensor_ranges(self) -> Dict[str, Any]:
        """Rangos válidos de sensores."""
        return self._rules.get("sensor_ranges", {})

    @property
    def health_ranges(self) -> Dict[str, Any]:
        """Rangos válidos de salud/biométricos."""
        return self._rules.get("sensor_ranges", {}).get("health", {})

    @property
    def geo_fence(self) -> Dict[str, Any]:
        """Configuración de geovallas."""
        return self._rules.get("geo_fence", {})

    @property
    def anomaly(self) -> Dict[str, Any]:
        """Configuración del motor de anomalías."""
        return self._rules.get("anomaly_detection", {})

    @property
    def privacy(self) -> Dict[str, Any]:
        """Configuración de privacidad."""
        return self._rules.get("privacy", {})

    @property
    def watchdog_cfg(self) -> Dict[str, Any]:
        """Configuración del watchdog."""
        return self._rules.get("watchdog", {})

    @property
    def alert_escalation_cfg(self) -> Dict[str, Any]:
        """Configuración de escalación de alertas."""
        return self._rules.get("alert_escalation", {})

    @property
    def audit(self) -> Dict[str, Any]:
        """Configuración de auditoría."""
        return self._rules.get("audit", {})

    @property
    def threat(self) -> Dict[str, Any]:
        """Configuración de detección de amenazas."""
        return self._rules.get("threat_detection", {})
