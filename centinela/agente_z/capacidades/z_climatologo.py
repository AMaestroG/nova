"""
Z-CLIMATÓLOGO — Predicción meteorológica local con barómetro.
===============================================================
Z usa el barómetro del Z Fold para predecir cambios de clima:
  - Presión subiendo rápido → buen tiempo
  - Presión bajando rápido → tormenta inminente
  - Presión estable → clima sin cambios
  - Altitud + presión → ajuste de predicción

Más preciso que apps genéricas porque usa datos LOCALES.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger("centinela.agente_z.z_climatologo")


class ZClimatologo:
    """
    Z como climatólogo local. Predice el tiempo con el barómetro del Z Fold.
    """

    # Umbrales de cambio de presión (hPa por hora)
    UMBRAL_SUBIDA_RAPIDA = 2.0     # Subida > 2 hPa/h = mejorando
    UMBRAL_BAJADA_RAPIDA = -2.0    # Bajada > 2 hPa/h = tormenta
    UMBRAL_BAJADA_TORMENTA = -5.0  # Bajada > 5 hPa/h = tormenta severa

    def __init__(self):
        self._historial_presion: deque = deque(maxlen=60)  # 60 min
        self._ultima_prediccion: Optional[str] = None

    def alimentar_barometro(self, presion_hpa: float):
        """Registra una lectura del barómetro."""
        ahora = datetime.now(timezone.utc)
        self._historial_presion.append({
            "presion": presion_hpa,
            "timestamp": ahora,
        })

    def predecir(self) -> Optional[Dict]:
        """
        Predice el clima basado en la tendencia del barómetro.
        """
        if len(self._historial_presion) < 10:
            return None

        # Calcular tendencia (últimos 30 min vs anteriores 30 min)
        historial = list(self._historial_presion)
        mitad = len(historial) // 2
        recientes = historial[-mitad:]
        anteriores = historial[:mitad]

        presion_ahora = recientes[-1]["presion"]
        presion_antes = anteriores[0]["presion"]

        # Calcular tiempo transcurrido en horas
        dt = (recientes[-1]["timestamp"] - anteriores[0]["timestamp"]).total_seconds() / 3600
        if dt == 0:
            return None

        cambio_por_hora = (presion_ahora - presion_antes) / dt

        # Interpretar
        if cambio_por_hora > self.UMBRAL_SUBIDA_RAPIDA:
            prediccion = "Mejorando — cielo despejándose, buen tiempo en camino"
            icono = "☀️"
            confianza = 0.8
        elif cambio_por_hora > 1.0:
            prediccion = "Estable tendiendo a mejor — nubes dispersándose"
            icono = "🌤️"
            confianza = 0.7
        elif cambio_por_hora < self.UMBRAL_BAJADA_TORMENTA:
            prediccion = "⚠️ Tormenta severa inminente — busca refugio"
            icono = "⛈️"
            confianza = 0.9
        elif cambio_por_hora < self.UMBRAL_BAJADA_RAPIDA:
            prediccion = "Lluvia probable — presión bajando rápido"
            icono = "🌧️"
            confianza = 0.8
        elif cambio_por_hora < -0.5:
            prediccion = "Nubosidad en aumento — posible lluvia ligera"
            icono = "☁️"
            confianza = 0.6
        else:
            prediccion = "Estable — sin cambios significativos esperados"
            icono = "🌤️"
            confianza = 0.7

        return {
            "presion_actual": round(presion_ahora, 2),
            "tendencia_hpa_h": round(cambio_por_hora, 2),
            "prediccion": prediccion,
            "icono": icono,
            "confianza": confianza,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def obtener_estado(self) -> Dict:
        return {
            "presion_actual": self._historial_presion[-1]["presion"] if self._historial_presion else None,
            "muestras": len(self._historial_presion),
            "prediccion": self.predecir(),
        }
