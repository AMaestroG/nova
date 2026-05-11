"""
SENTINEL — Capa de Seguridad, Vigilancia y Monitoreo
Nova Homonexus — Sistema Centinela

Módulos:
  auth              Autenticación avanzada (JWT, API keys, fingerprinting)
  validator         Validación de datos entrantes (rangos, inyección, sanitización)
  threat_detector   Detección de amenazas (patrones, blacklist, data poisoning)
  geo_fence         Geovalla inteligente y zonas seguras
  anomaly_engine    Motor de detección de anomalías biométricas y de sensores
  privacy_filter    Filtro de privacidad (encriptación, anonimización, retención)
  watchdog          Perro guardián (heartbeat, reconexión, estado del Z Fold)
  alert_escalation  Escalación de alertas (niveles, notificaciones, protocolos)
  audit_log         Registro de auditoría inmutable (hash encadenado)
  rules             Reglas de seguridad configurables (cargadas desde YAML)
"""

from centinela.sentinel.auth import AuthManager
from centinela.sentinel.validator import DataValidator
from centinela.sentinel.threat_detector import ThreatDetector
from centinela.sentinel.geo_fence import GeoFence
from centinela.sentinel.anomaly_engine import AnomalyEngine
from centinela.sentinel.privacy_filter import PrivacyFilter
from centinela.sentinel.watchdog import Watchdog
from centinela.sentinel.alert_escalation import AlertEscalation
from centinela.sentinel.audit_log import AuditLog
from centinela.sentinel.rules import SecurityRules

__all__ = [
    "AuthManager",
    "DataValidator",
    "ThreatDetector",
    "GeoFence",
    "AnomalyEngine",
    "PrivacyFilter",
    "Watchdog",
    "AlertEscalation",
    "AuditLog",
    "SecurityRules",
]

VERSION = "1.0.0"
CODENAME = "SENTINEL-N1"
