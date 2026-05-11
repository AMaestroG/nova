"""
geo_fence — Geovalla Inteligente
Nova Homonexus — SENTINEL

Define zonas seguras y monitorea movimientos:
  - Zonas seguras configurables (casa, oficina, etc.)
  - Alertas al salir/entrar de zonas
  - Historial de movimientos con detección de rutas anómalas
  - Cálculo de velocidad y detección de modo transporte
  - Integración con alertas de seguridad
"""

import math
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass, field
from collections import deque, defaultdict

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.geofence")


# =============================================================================
# CONSTANTES
# =============================================================================

# Radio de la Tierra en metros
EARTH_RADIUS_M = 6371000.0


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SafeZone:
    """Zona segura definida por coordenadas y radio."""
    name: str
    lat: float
    lon: float
    radius: float  # metros
    zone_type: str  # home, work, gym, etc.
    enabled: bool = True

    def contains(self, lat: float, lon: float) -> bool:
        """
        Verifica si un punto está dentro de la zona.

        Args:
            lat: Latitud del punto.
            lon: Longitud del punto.

        Returns:
            True si está dentro del radio.
        """
        distance = haversine_distance(
            self.lat, self.lon, lat, lon
        )
        return distance <= self.radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "radius": self.radius,
            "type": self.zone_type,
            "enabled": self.enabled,
        }


@dataclass
class MovementPoint:
    """Punto de movimiento con timestamp."""
    lat: float
    lon: float
    altitud: Optional[float]
    velocidad: Optional[float]
    precision_h: Optional[float]
    timestamp: float
    proveedor: str = "gps"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitud": self.altitud,
            "velocidad": self.velocidad,
            "precision": self.precision_h,
            "timestamp": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "proveedor": self.proveedor,
        }


# =============================================================================
# FUNCIONES DE CÁLCULO GEOGRÁFICO
# =============================================================================

def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calcula la distancia entre dos puntos GPS usando la fórmula de Haversine.

    Args:
        lat1, lon1: Coordenadas del punto 1 (grados).
        lat2, lon2: Coordenadas del punto 2 (grados).

    Returns:
        Distancia en metros.
    """
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def calculate_speed(
    p1: MovementPoint, p2: MovementPoint
) -> float:
    """
    Calcula la velocidad entre dos puntos de movimiento.

    Args:
        p1, p2: Puntos de movimiento consecutivos.

    Returns:
        Velocidad en km/h.
    """
    distance = haversine_distance(
        p1.lat, p1.lon, p2.lat, p2.lon
    )
    time_diff = abs(p2.timestamp - p1.timestamp)
    if time_diff <= 0:
        return 0.0
    speed_ms = distance / time_diff
    return speed_ms * 3.6  # convertir m/s a km/h


def detect_transport_mode(speed_kmh: float) -> str:
    """
    Detecta el modo de transporte basado en la velocidad.

    Args:
        speed_kmh: Velocidad en km/h.

    Returns:
        Modo de transporte: "stationary", "walking", "running",
        "cycling", "driving", "flying"
    """
    if speed_kmh < 0.5:
        return "stationary"
    elif speed_kmh < 6:
        return "walking"
    elif speed_kmh < 12:
        return "running"
    elif speed_kmh < 25:
        return "cycling"
    elif speed_kmh < 180:
        return "driving"
    else:
        return "flying"


# =============================================================================
# GEO FENCE
# =============================================================================

class GeoFence:
    """
    Geovalla inteligente para el sistema Centinela.

    Monitorea la ubicación del Z Fold y genera alertas
    basadas en zonas seguras, movimientos anómalos y velocidad.
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        gf_cfg = self._rules.geo_fence

        self._enabled = gf_cfg.get("enabled", True)
        self._default_radius = gf_cfg.get("default_radius", 200)
        self._max_walking_speed = gf_cfg.get(
            "max_walking_speed", 8.0
        )
        self._max_driving_speed = gf_cfg.get(
            "max_driving_speed", 180.0
        )
        self._min_stay_time = gf_cfg.get("min_stay_time", 120)
        self._alert_on_exit = gf_cfg.get("alert_on_exit", True)
        self._alert_on_entry = gf_cfg.get("alert_on_entry", True)

        # Zonas seguras
        self._safe_zones: Dict[str, SafeZone] = {}
        self._load_safe_zones()

        # Historial de movimientos (últimos 1000 puntos)
        self._movement_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

        # Estado de zonas (dentro/fuera)
        self._zone_status: Dict[str, Dict[str, bool]] = defaultdict(
            lambda: {}
        )

        # Última alerta por zona (para evitar spam)
        self._last_alert: Dict[str, float] = {}

        logger.info(
            "GeoFence inicializado con %d zonas seguras",
            len(self._safe_zones),
        )

    def _load_safe_zones(self) -> None:
        """Carga las zonas seguras desde la configuración."""
        zones = self._rules.geo_fence.get("safe_zones", {})
        for zone_id, zone_data in zones.items():
            self._safe_zones[zone_id] = SafeZone(
                name=zone_data.get("name", zone_id),
                lat=zone_data.get("lat", 0.0),
                lon=zone_data.get("lon", 0.0),
                radius=zone_data.get(
                    "radius", self._default_radius
                ),
                zone_type=zone_data.get("type", "unknown"),
                enabled=zone_data.get("enabled", True),
            )

    # ------------------------------------------------------------------
    # GESTIÓN DE ZONAS
    # ------------------------------------------------------------------

    def add_zone(
        self,
        zone_id: str,
        name: str,
        lat: float,
        lon: float,
        radius: Optional[float] = None,
        zone_type: str = "custom",
    ) -> SafeZone:
        """
        Añade una nueva zona segura.

        Args:
            zone_id: ID único de la zona.
            name: Nombre descriptivo.
            lat: Latitud del centro.
            lon: Longitud del centro.
            radius: Radio en metros (por defecto el configurado).
            zone_type: Tipo de zona (home, work, gym, custom).

        Returns:
            La zona creada.
        """
        zone = SafeZone(
            name=name,
            lat=lat,
            lon=lon,
            radius=radius or self._default_radius,
            zone_type=zone_type,
        )
        self._safe_zones[zone_id] = zone
        logger.info(
            "Zona segura añadida: %s (%s) en [%.4f, %.4f] r=%.0fm",
            zone_id,
            name,
            lat,
            lon,
            zone.radius,
        )
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        """
        Elimina una zona segura.

        Args:
            zone_id: ID de la zona.

        Returns:
            True si fue eliminada.
        """
        if zone_id in self._safe_zones:
            del self._safe_zones[zone_id]
            logger.info("Zona segura eliminada: %s", zone_id)
            return True
        return False

    def get_zones(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene todas las zonas seguras."""
        return {
            zid: zone.to_dict()
            for zid, zone in self._safe_zones.items()
        }

    def get_zone(self, zone_id: str) -> Optional[SafeZone]:
        """Obtiene una zona por su ID."""
        return self._safe_zones.get(zone_id)

    # ------------------------------------------------------------------
    # VERIFICACIÓN DE UBICACIÓN
    # ------------------------------------------------------------------

    def check_location(
        self,
        device_id: str,
        lat: float,
        lon: float,
        altitud: Optional[float] = None,
        velocidad: Optional[float] = None,
        precision_h: Optional[float] = None,
        proveedor: str = "gps",
    ) -> List[Dict[str, Any]]:
        """
        Verifica una ubicación contra todas las zonas seguras.

        Args:
            device_id: ID del dispositivo.
            lat: Latitud.
            lon: Longitud.
            altitud: Altitud (opcional).
            velocidad: Velocidad (opcional).
            precision_h: Precisión horizontal (opcional).
            proveedor: Proveedor de GPS.

        Returns:
            Lista de eventos generados (alertas de zona).
        """
        if not self._enabled:
            return []

        now = time.time()
        eventos = []

        # Registrar punto de movimiento
        point = MovementPoint(
            lat=lat,
            lon=lon,
            altitud=altitud,
            velocidad=velocidad,
            precision_h=precision_h,
            timestamp=now,
            proveedor=proveedor,
        )
        self._movement_history[device_id].append(point)

        # Verificar cada zona
        for zone_id, zone in self._safe_zones.items():
            if not zone.enabled:
                continue

            was_inside = self._zone_status[device_id].get(
                zone_id, False
            )
            is_inside = zone.contains(lat, lon)

            self._zone_status[device_id][zone_id] = is_inside

            # Detectar salida
            if was_inside and not is_inside:
                if self._alert_on_exit:
                    eventos.append({
                        "tipo": "geo_salida",
                        "severidad": "WARNING",
                        "mensaje": (
                            f"Salida de zona segura '{zone.name}'"
                        ),
                        "zona": zone_id,
                        "ubicacion": {
                            "lat": lat,
                            "lon": lon,
                        },
                        "timestamp": now,
                    })
                    logger.info(
                        "Salida de zona %s: %s [%.4f, %.4f]",
                        device_id,
                        zone.name,
                        lat,
                        lon,
                    )

            # Detectar entrada
            elif not was_inside and is_inside:
                if self._alert_on_entry:
                    eventos.append({
                        "tipo": "geo_entrada",
                        "severidad": "INFO",
                        "mensaje": (
                            f"Entrada a zona segura '{zone.name}'"
                        ),
                        "zona": zone_id,
                        "ubicacion": {
                            "lat": lat,
                            "lon": lon,
                        },
                        "timestamp": now,
                    })
                    logger.info(
                        "Entrada a zona %s: %s [%.4f, %.4f]",
                        device_id,
                        zone.name,
                        lat,
                        lon,
                    )

        return eventos

    # ------------------------------------------------------------------
    # ANÁLISIS DE MOVIMIENTO
    # ------------------------------------------------------------------

    def analyze_movement(
        self, device_id: str
    ) -> Dict[str, Any]:
        """
        Analiza el movimiento reciente de un dispositivo.

        Args:
            device_id: ID del dispositivo.

        Returns:
            Dict con análisis de movimiento.
        """
        history = list(self._movement_history.get(device_id, []))
        if len(history) < 2:
            return {
                "status": "insufficient_data",
                "points": len(history),
            }

        # Últimos dos puntos
        p1 = history[-2]
        p2 = history[-1]

        # Calcular velocidad
        speed = calculate_speed(p1, p2)
        if p2.velocidad is not None:
            speed = max(speed, p2.velocidad)

        # Detectar modo de transporte
        transport_mode = detect_transport_mode(speed)

        # Calcular distancia total reciente (últimos 10 puntos)
        recent = history[-10:]
        total_distance = 0.0
        for i in range(1, len(recent)):
            total_distance += haversine_distance(
                recent[i - 1].lat,
                recent[i - 1].lon,
                recent[i].lat,
                recent[i].lon,
            )

        # Detectar inactividad
        time_span = p2.timestamp - history[0].timestamp
        inactivity = time_span > 300  # 5 minutos sin movimiento significativo

        # Detectar velocidad anómala
        speed_anomaly = False
        speed_reason = ""
        if speed > self._max_driving_speed:
            speed_anomaly = True
            speed_reason = (
                f"Velocidad {speed:.1f} km/h excede el máximo "
                f"de conducción ({self._max_driving_speed} km/h)"
            )
        elif speed > self._max_walking_speed and transport_mode == "walking":
            speed_anomaly = True
            speed_reason = (
                f"Velocidad {speed:.1f} km/h muy alta para "
                f"caminar (máx: {self._max_walking_speed} km/h)"
            )

        return {
            "status": "ok",
            "points_analyzed": len(history),
            "ultima_ubicacion": p2.to_dict(),
            "velocidad_kmh": round(speed, 2),
            "modo_transporte": transport_mode,
            "distancia_reciente_m": round(total_distance, 1),
            "inactividad": inactivity,
            "anomalia_velocidad": speed_anomaly,
            "razon_anomalia": speed_reason,
            "zonas_actuales": [
                zid
                for zid, inside in self._zone_status.get(
                    device_id, {}
                ).items()
                if inside
            ],
        }

    # ------------------------------------------------------------------
    # DETECCIÓN DE RUTAS ANÓMALAS
    # ------------------------------------------------------------------

    def detect_anomalous_route(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta rutas anómalas basadas en el historial de movimiento.

        Args:
            device_id: ID del dispositivo.

        Returns:
            Dict con la anomalía detectada o None.
        """
        history = list(self._movement_history.get(device_id, []))
        if len(history) < 5:
            return None

        analysis = self.analyze_movement(device_id)

        anomalias = []

        # 1. Velocidad anómala
        if analysis.get("anomalia_velocidad"):
            anomalias.append({
                "tipo": "velocidad_anomala",
                "severidad": "WARNING",
                "detalle": analysis["razon_anomalia"],
            })

        # 2. Fuera de todas las zonas seguras por mucho tiempo
        in_any_zone = any(
            self._zone_status.get(device_id, {}).values()
        )
        if not in_any_zone and len(history) > 20:
            time_outside = (
                history[-1].timestamp - history[0].timestamp
            )
            if time_outside > 3600:  # más de 1 hora fuera
                anomalias.append({
                    "tipo": "fuera_de_zona_prolongado",
                    "severidad": "WARNING",
                    "detalle": (
                        f"Dispositivo fuera de zonas seguras "
                        f"por {time_outside / 60:.0f} minutos"
                    ),
                })

        # 3. Precisión GPS anómala (muy baja)
        last_points = history[-3:]
        bad_gps = sum(
            1
            for p in last_points
            if p.precision_h is not None and p.precision_h > 50
        )
        if bad_gps >= 2:
            anomalias.append({
                "tipo": "gps_impreciso",
                "severidad": "INFO",
                "detalle": (
                    "Precisión GPS baja en lecturas recientes"
                ),
            })

        if not anomalias:
            return None

        return {
            "device_id": device_id,
            "timestamp": time.time(),
            "anomalias": anomalias,
            "ubicacion_actual": history[-1].to_dict(),
        }

    # ------------------------------------------------------------------
    # ESTADO
    # ------------------------------------------------------------------

    def get_status(self, device_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado completo de geovalla para un dispositivo.

        Args:
            device_id: ID del dispositivo.

        Returns:
            Dict con estado de geovalla.
        """
        history = list(self._movement_history.get(device_id, []))
        analysis = self.analyze_movement(device_id)

        return {
            "enabled": self._enabled,
            "zonas_totales": len(self._safe_zones),
            "zonas_activas": sum(
                1 for z in self._safe_zones.values() if z.enabled
            ),
            "zonas": self.get_zones(),
            "estado_zonas": self._zone_status.get(device_id, {}),
            "analisis_movimiento": analysis,
            "puntos_historial": len(history),
            "ruta_anomala": self.detect_anomalous_route(device_id),
        }
