"""
Z-EXPLORADOR ACTIVO — Investiga lugares y sugiere descubrimientos.
====================================================================
Cuando Abel llega a un lugar nuevo, Z:
  - Registra las coordenadas
  - Sugiere puntos de interés cercanos
  - Comparte datos curiosos (altitud, presión, clima)
  - Compara con lugares similares visitados antes
"""

import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger("centinela.agente_z.z_explorador")


class ZExploradorActivo:
    """
    Z como explorador. Descubre el mundo junto a Abel.
    """

    def __init__(self):
        self._lugares_visitados: Dict[str, Dict] = {}
        self._lugar_actual: Optional[str] = None
        self._tiempo_en_lugar: float = 0.0

    def registrar_ubicacion(
        self, lat: float, lon: float, altitud: float = None
    ) -> Optional[Dict]:
        """
        Registra una ubicación y detecta si es nueva.
        Retorna datos del lugar si es relevante.
        """
        clave = f"{lat:.4f},{lon:.4f}"

        if clave not in self._lugares_visitados:
            # ¡Nuevo lugar!
            lugar = {
                "lat": lat,
                "lon": lon,
                "altitud": altitud,
                "primera_visita": datetime.now(timezone.utc).isoformat(),
                "visitas": 1,
            }
            self._lugares_visitados[clave] = lugar
            self._lugar_actual = clave

            # Datos curiosos según ubicación
            curiosidad = self._generar_curiosidad(lat, lon, altitud)
            return {
                "tipo": "nuevo_lugar",
                "ubicacion": clave,
                "altitud": altitud,
                "curiosidad": curiosidad,
                "mensaje": f"Nuevo lugar descubierto: {clave}",
            }
        else:
            self._lugares_visitados[clave]["visitas"] += 1
            self._lugar_actual = clave
            return None

    def _generar_curiosidad(self, lat: float, lon: float, altitud: float = None) -> str:
        """Genera un dato curioso sobre la ubicación."""
        curiosidades = []

        if altitud:
            if altitud > 2000:
                curiosidades.append(f"Estás a {altitud:.0f}m de altitud. El aire es más fino aquí.")
            elif altitud < 10:
                curiosidades.append("Estás cerca del nivel del mar. La presión es alta.")

        if abs(lat) > 60:
            curiosidades.append("Estás en latitudes altas. Los días aquí son muy largos en verano.")
        elif abs(lat) < 10:
            curiosidades.append("Cerca del ecuador. El clima es estable todo el año.")

        if not curiosidades:
            curiosidades.append("Cada lugar tiene su magia. Z lo registrará para recordarlo.")

        return random.choice(curiosidades)

    def sugerir_exploracion(self, radio_km: float = 2.0) -> Optional[str]:
        """Sugiere explorar si lleva mucho tiempo en el mismo lugar."""
        if self._tiempo_en_lugar > 7200:  # 2 horas
            return "Llevas un tiempo aquí. ¿Exploramos los alrededores?"
        return None

    def obtener_estado(self) -> Dict:
        return {
            "lugares_descubiertos": len(self._lugares_visitados),
            "lugar_actual": self._lugar_actual,
        }
