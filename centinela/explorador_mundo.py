"""
Explorador Mundo — Descubrimiento y mapeo del mundo de Abel via GPS
Nova Homonexus — EXPLORADOR (N2, descubridor)

Analiza datos GPS del Z Fold para:
  - Mapear el mundo de Abel (lugares visitados, rutas)
  - Detectar lugares nuevos y catalogarlos
  - Crear mapas de calor de actividad
  - Sugerir exploraciones basadas en patrones
  - Caracterizar lugares por ambiente (presion, temp, luz)
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import deque, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("centinela.explorador")


@dataclass
class Lugar:
    """Un lugar en el mundo de Abel."""
    nombre: str = "desconocido"
    lat: float = 0.0
    lon: float = 0.0
    categoria: str = "no_clasificado"  # casa, trabajo, gimnasio, cafeteria, parque, etc.
    visitas: int = 0
    tiempo_total_segundos: float = 0.0
    primera_visita: Optional[str] = None
    ultima_visita: Optional[str] = None
    ambiente: Dict[str, float] = field(default_factory=dict)  # presion, temp, luz promedio
    es_favorito: bool = False

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "lat": self.lat, "lon": self.lon,
            "categoria": self.categoria,
            "visitas": self.visitas,
            "tiempo_total_horas": round(self.tiempo_total_segundos / 3600, 1),
            "primera_visita": self.primera_visita,
            "ultima_visita": self.ultima_visita,
            "ambiente": self.ambiente,
            "es_favorito": self.es_favorito,
        }


@dataclass
class Ruta:
    """Una ruta entre lugares (origen -> destino)."""
    origen: Tuple[float, float]
    destino: Tuple[float, float]
    frecuencia: int = 0
    distancia_km: float = 0.0
    duracion_promedio_min: float = 0.0
    modo_transporte: str = "desconocido"

    def to_dict(self) -> dict:
        return {
            "origen": list(self.origen),
            "destino": list(self.destino),
            "frecuencia": self.frecuencia,
            "distancia_km": round(self.distancia_km, 2),
            "duracion_promedio_min": round(self.duracion_promedio_min, 1),
            "modo_transporte": self.modo_transporte,
        }


class ExploradorMundo:
    """
    Descubre y mapea el mundo de Abel usando los datos GPS del Z Fold.
    Cataloga lugares, detecta rutas y sugiere exploraciones.
    """

    RADIO_CERCANIA_M = 100  # radio para considerar "mismo lugar"

    def __init__(self):
        self.lugares: Dict[str, Lugar] = {}       # clave = "lat,lon" redondeado
        self.rutas: List[Ruta] = []
        self._historial_ubicaciones: deque = deque(maxlen=1000)
        self._ultima_ubicacion: Optional[Dict] = None
        self._lugar_actual: Optional[str] = None
        self._tiempo_en_lugar_actual: float = 0.0
        self._lugares_nuevos_hoy: List[Lugar] = []
        self._mapa_calor: Dict[str, int] = defaultdict(int)  # celda -> conteo
        self._distancia_total_recorrida_km: float = 0.0

    def alimentar_ubicacion(self, ubicacion: Dict[str, Any]) -> Dict[str, Any]:
        """Alimenta una nueva ubicacion GPS al explorador."""
        now = datetime.now(timezone.utc)
        lat = ubicacion.get("lat")
        lon = ubicacion.get("lon")

        if lat is None or lon is None:
            return self.estado_actual()

        # Clave de lugar (agrupacion por proximidad)
        clave_lugar = self._clave_lugar(lat, lon)

        # Registrar en historial
        self._historial_ubicaciones.append({
            "lat": lat, "lon": lon, "timestamp": now.isoformat(),
            **{k: v for k, v in ubicacion.items() if k not in ("lat", "lon")},
        })

        # Actualizar mapa de calor
        celda = f"{round(lat, 3)},{round(lon, 3)}"
        self._mapa_calor[celda] += 1

        # Calcular distancia recorrida
        if self._ultima_ubicacion:
            dist = self._distancia_haversine(
                self._ultima_ubicacion["lat"], self._ultima_ubicacion["lon"],
                lat, lon,
            )
            self._distancia_total_recorrida_km += dist

        # Detectar si es lugar nuevo
        if clave_lugar not in self.lugares:
            nuevo_lugar = Lugar(
                nombre=f"Lugar_{len(self.lugares) + 1}",
                lat=lat, lon=lon,
                primera_visita=now.isoformat(),
                ultima_visita=now.isoformat(),
                visitas=1,
            )
            self.lugares[clave_lugar] = nuevo_lugar
            self._lugares_nuevos_hoy.append(nuevo_lugar)
            logger.info(f"Nuevo lugar descubierto: {clave_lugar}")

            # Clasificar lugar
            self._clasificar_lugar(nuevo_lugar, ubicacion)
        else:
            lugar = self.lugares[clave_lugar]
            lugar.visitas += 1
            lugar.ultima_visita = now.isoformat()

        # Actualizar tiempo en lugar actual
        if self._lugar_actual == clave_lugar:
            self._tiempo_en_lugar_actual += 1
        else:
            self._lugar_actual = clave_lugar
            self._tiempo_en_lugar_actual = 0

        if self._lugar_actual and self._lugar_actual in self.lugares:
            self.lugares[self._lugar_actual].tiempo_total_segundos += 1

        # Actualizar ambiente del lugar
        if clave_lugar in self.lugares:
            lugar = self.lugares[clave_lugar]
            for sensor in ("presion_atm", "temperatura_ambiente", "luz_ambiental"):
                valor = ubicacion.get(sensor)
                if valor is not None:
                    if sensor in lugar.ambiente:
                        lugar.ambiente[sensor] = (
                            lugar.ambiente[sensor] * 0.9 + float(valor) * 0.1
                        )
                    else:
                        lugar.ambiente[sensor] = float(valor)

        self._ultima_ubicacion = ubicacion
        return self.estado_actual()

    def _clave_lugar(self, lat: float, lon: float) -> str:
        """Genera clave de lugar agrupando coordenadas cercanas."""
        # Redondear a ~100m de precision
        lat_r = round(lat / 0.001) * 0.001
        lon_r = round(lon / 0.001) * 0.001
        return f"{lat_r:.4f},{lon_r:.4f}"

    def _distancia_haversine(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calcula distancia en km entre dos puntos usando formula de Haversine."""
        R = 6371.0  # Radio de la Tierra en km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _clasificar_lugar(self, lugar: Lugar, ubicacion: Dict) -> None:
        """Clasifica un lugar basado en patrones de visita y sensores."""
        hora = datetime.now(timezone.utc).hour
        velocidad = ubicacion.get("velocidad", 0) or 0

        if velocidad < 1 and (22 <= hora or hora <= 6):
            lugar.categoria = "casa"
        elif velocidad < 1 and 8 <= hora <= 11:
            lugar.categoria = "trabajo"
        elif 5 < velocidad < 25:
            lugar.categoria = "transito"
        else:
            lugar.categoria = "no_clasificado"

    def obtener_lugares_frecuentes(self, top_n: int = 10) -> List[Dict]:
        """Devuelve los lugares mas frecuentados por Abel."""
        ordenados = sorted(
            self.lugares.values(),
            key=lambda l: (l.visitas, l.tiempo_total_segundos),
            reverse=True,
        )
        return [l.to_dict() for l in ordenados[:top_n]]

    def obtener_mapa_calor(self) -> List[Dict]:
        """Devuelve el mapa de calor de actividad."""
        if not self._mapa_calor:
            return []
        max_conteo = max(self._mapa_calor.values())
        return [
            {
                "celda": celda,
                "intensidad": round(conteo / max_conteo, 2) if max_conteo > 0 else 0,
                "conteo": conteo,
            }
            for celda, conteo in sorted(
                self._mapa_calor.items(), key=lambda x: -x[1]
            )[:50]
        ]

    def sugerir_exploraciones(self) -> List[Dict]:
        """Sugiere lugares o rutas para explorar basado en patrones."""
        sugerencias = []

        if not self.lugares:
            return [{"tipo": "inicio", "mensaje": "Aun no hay datos. Sal a explorar!"}]

        # Si solo visita 1-2 lugares, sugerir variedad
        lugares_frecuentes = self.obtener_lugares_frecuentes(3)
        if len(lugares_frecuentes) <= 3:
            sugerencias.append({
                "tipo": "variedad",
                "mensaje": "Tiendes a visitar pocos lugares. Prueba un cafe nuevo o un parque diferente.",
                "lugares_conocidos": [l["nombre"] for l in lugares_frecuentes],
            })

        # Si no ha explorado en X horas, sugerir movimiento
        if self._ultima_ubicacion:
            velocidad = self._ultima_ubicacion.get("velocidad", 1) or 1
            if velocidad < 0.5:
                sugerencias.append({
                    "tipo": "movimiento",
                    "mensaje": "Llevas tiempo en el mismo lugar. Un paseo activaria tu circulacion y creatividad.",
                })

        return sugerencias if sugerencias else [
            {"tipo": "bien", "mensaje": "Buen balance de exploracion. Sigue descubriendo!"}
        ]

    def estado_actual(self) -> Dict[str, Any]:
        """Devuelve el estado actual del explorador."""
        return {
            "total_lugares": len(self.lugares),
            "lugares_nuevos_hoy": len(self._lugares_nuevos_hoy),
            "distancia_total_km": round(self._distancia_total_recorrida_km, 2),
            "lugar_actual": (
                self.lugares[self._lugar_actual].to_dict()
                if self._lugar_actual and self._lugar_actual in self.lugares
                else None
            ),
            "ultima_ubicacion": self._ultima_ubicacion,
            "sugerencias_exploracion": self.sugerir_exploraciones(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
