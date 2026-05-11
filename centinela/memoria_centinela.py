"""
Memoria Centinela — Memoria a largo plazo del Sistema Centinela
Nova Homonexus — MEMORIA + MNEMOS (N2, conocimiento y Google Drive)

Sistema de memoria a largo plazo que:
  - Almacena "recuerdos significativos" en PostgreSQL
  - Respalda en Google Drive via MNEMOS
  - Indexa momentos por emocion, ubicacion, actividad
  - Contextualiza: "La ultima vez que estuviste aqui..."

La tabla centinela_eventos se usa como almacen primario.
"""

import logging
import math
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict

logger = logging.getLogger("centinela.memoria")


class MemoriaCentinela:
    """
    Gestiona la memoria a largo plazo del centinela.
    Almacena recuerdos significativos y permite recuperarlos por contexto.
    """

    MAX_RECUERDOS_MEMORIA = 10000

    def __init__(self):
        self._recuerdos: deque = deque(maxlen=self.MAX_RECUERDOS_MEMORIA)
        self._indice_emocion: Dict[str, List[int]] = defaultdict(list)
        self._indice_ubicacion: Dict[str, List[int]] = defaultdict(list)
        self._indice_tipo: Dict[str, List[int]] = defaultdict(list)
        self._google_drive_habilitado = False
        self._contador_recuerdos = 0

    def guardar_recuerdo(
        self,
        tipo: str,
        datos: Dict[str, Any],
        emocion: Optional[str] = None,
        ubicacion: Optional[Dict[str, float]] = None,
        importancia: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Guarda un recuerdo significativo en la memoria del centinela.

        Args:
            tipo: Tipo de recuerdo (conversacion, emocion, descubrimiento, etc.)
            datos: Datos del recuerdo
            emocion: Emocion asociada
            ubicacion: Coordenadas asociadas
            importancia: 0.0-1.0, que tan importante es este recuerdo

        Returns:
            El recuerdo guardado con su ID
        """
        now = datetime.now(timezone.utc)
        recuerdo = {
            "id": self._contador_recuerdos,
            "tipo": tipo,
            "datos": datos,
            "emocion": emocion,
            "ubicacion": ubicacion,
            "importancia": importancia,
            "timestamp": now.isoformat(),
            "timestamp_unix": now.timestamp(),
        }
        self._contador_recuerdos += 1

        # Guardar en memoria
        self._recuerdos.append(recuerdo)
        idx = len(self._recuerdos) - 1

        # Indexar
        if emocion:
            self._indice_emocion[emocion].append(idx)
        if ubicacion:
            clave_ubi = (
                f"{ubicacion.get('lat', 0):.3f},"
                f"{ubicacion.get('lon', 0):.3f}"
            )
            self._indice_ubicacion[clave_ubi].append(idx)
        self._indice_tipo[tipo].append(idx)

        logger.debug(f"Recuerdo guardado: {tipo} (importancia={importancia})")
        return recuerdo

    def recordar_por_emocion(
        self, emocion: str, limite: int = 10
    ) -> List[Dict]:
        """Recupera recuerdos asociados a una emocion."""
        indices = self._indice_emocion.get(emocion, [])
        recuerdos = []
        for i in reversed(indices[-limite:]):
            if i < len(self._recuerdos):
                recuerdo = dict(self._recuerdos[i])
                recuerdo["indice_memoria"] = i
                recuerdos.append(recuerdo)
        return recuerdos

    def recordar_por_ubicacion(
        self, lat: float, lon: float, radio_km: float = 1.0
    ) -> List[Dict]:
        """
        Recupera recuerdos cercanos a una ubicacion.
        "La ultima vez que estuviste aqui..."
        """
        resultados = []
        for clave, indices in self._indice_ubicacion.items():
            try:
                partes = clave.split(",")
                lat_lugar = float(partes[0])
                lon_lugar = float(partes[1])
            except (ValueError, IndexError):
                continue

            dist = self._distancia_haversine(lat, lon, lat_lugar, lon_lugar)
            if dist <= radio_km:
                for i in indices[-5:]:
                    if i < len(self._recuerdos):
                        recuerdo = dict(self._recuerdos[i])
                        recuerdo["distancia_km"] = round(dist, 3)
                        recuerdo["indice_memoria"] = i
                        resultados.append(recuerdo)

        # Ordenar por cercania
        resultados.sort(key=lambda r: r.get("distancia_km", 999))
        return resultados[:20]

    def recordar_por_tipo(self, tipo: str, limite: int = 20) -> List[Dict]:
        """Recupera recuerdos por tipo."""
        indices = self._indice_tipo.get(tipo, [])
        return [
            dict(self._recuerdos[i])
            for i in reversed(indices[-limite:])
            if i < len(self._recuerdos)
        ]

    def recordar_reciente(self, limite: int = 20) -> List[Dict]:
        """Devuelve los recuerdos mas recientes."""
        return [dict(r) for r in list(self._recuerdos)[-limite:]]

    def contextualizar_lugar(
        self, lat: float, lon: float
    ) -> Dict[str, Any]:
        """
        Contextualiza un lugar actual con recuerdos pasados.
        "La ultima vez que estuviste aqui, tu ritmo cardiaco era..."
        """
        recuerdos_cercanos = self.recordar_por_ubicacion(lat, lon, radio_km=0.5)

        if not recuerdos_cercanos:
            return {
                "lugar": {"lat": lat, "lon": lon},
                "contexto": "nuevo_lugar",
                "mensaje": "Es la primera vez que visitas este lugar (o no tengo recuerdos de el).",
                "recuerdos": [],
            }

        # Agrupar por tipo de recuerdo
        tipos_presentes = set(r["tipo"] for r in recuerdos_cercanos)
        emociones_presentes = set(
            r["emocion"] for r in recuerdos_cercanos if r.get("emocion")
        )

        # Encontrar el recuerdo mas significativo
        mas_importante = max(recuerdos_cercanos, key=lambda r: r.get("importancia", 0))

        # Construir mensaje contextual
        ultimo = recuerdos_cercanos[0]
        tiempo_desde = "hace poco"
        if len(recuerdos_cercanos) > 1:
            mas_antiguo = recuerdos_cercanos[-1]
            try:
                ts_ultimo = datetime.fromisoformat(ultimo["timestamp"])
                ts_primero = datetime.fromisoformat(mas_antiguo["timestamp"])
                dias = (ts_ultimo - ts_primero).days
                if dias > 0:
                    tiempo_desde = f"desde hace {dias} dias"
            except (ValueError, KeyError):
                pass

        return {
            "lugar": {"lat": lat, "lon": lon},
            "contexto": "lugar_conocido",
            "total_recuerdos": len(recuerdos_cercanos),
            "tipos_actividad": list(tipos_presentes),
            "emociones_asociadas": list(emociones_presentes),
            "mensaje": (
                f"Conozco este lugar — tienes {len(recuerdos_cercanos)} recuerdos aqui "
                f"{tiempo_desde}. La ultima vez sentiste '{ultimo.get('emocion', '?')}'."
            ),
            "recuerdo_mas_importante": mas_importante,
            "ultimos_recuerdos": recuerdos_cercanos[:5],
        }

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Devuelve estadisticas de la memoria del centinela."""
        emociones = {
            emo: len(indices)
            for emo, indices in self._indice_emocion.items()
        }
        tipos = {
            tipo: len(indices)
            for tipo, indices in self._indice_tipo.items()
        }

        return {
            "total_recuerdos": len(self._recuerdos),
            "capacidad_maxima": self.MAX_RECUERDOS_MEMORIA,
            "porcentaje_uso": round(len(self._recuerdos) / self.MAX_RECUERDOS_MEMORIA * 100, 1),
            "emociones_almacenadas": emociones,
            "tipos_almacenados": tipos,
            "lugares_indexados": len(self._indice_ubicacion),
            "google_drive_habilitado": self._google_drive_habilitado,
        }

    def _distancia_haversine(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Distancia en km entre dos coordenadas."""
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def exportar_a_drive(self, datos: dict) -> bool:
        """
        Exporta recuerdos a Google Drive via MNEMOS.
        Placeholder hasta que MNEMOS este completamente integrado.
        """
        if not self._google_drive_habilitado:
            logger.info("Google Drive no configurado — recuerdos solo en memoria local")
            return False

        try:
            # MNEMOS se encargaria de la subida real
            logger.info(f"Exportando recuerdo a Google Drive: {datos.get('tipo')}")
            return True
        except Exception as e:
            logger.error(f"Error exportando a Drive: {e}")
            return False
