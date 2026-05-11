"""
Z-ENTRENADOR — Coaching de ejercicio y recuperación.
======================================================
Z analiza la actividad física de Abel y sugiere:
  - Cuándo entrenar (HRV alto = buen momento)
  - Cuándo descansar (HRV bajo = necesita recuperación)
  - Tipo de ejercicio según energía y historial
  - Hidratación y nutrición post-ejercicio
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("centinela.agente_z.z_entrenador")


class ZEntrenador:
    """
    Z como entrenador personal. Optimiza el rendimiento físico de Abel.
    """

    def __init__(self):
        self._sesiones_hoy: int = 0
        self._hrv_baseline: Optional[float] = None
        self._consejos_dados: List[str] = []

    def evaluar_estado_fisico(self, percepciones: Dict) -> Dict:
        """
        Evalúa el estado físico actual y recomienda acción.
        """
        pulso = percepciones.get("Z-PULSO", {})
        hr = pulso.get("heart_rate")
        hrv = pulso.get("hrv")
        pasos = pulso.get("steps", 0)
        stress = pulso.get("stress_level")

        # Actualizar baseline de HRV
        if hrv and not self._hrv_baseline:
            self._hrv_baseline = hrv

        recomendacion = self._determinar_recomendacion(hr, hrv, pasos, stress)
        return recomendacion

    def _determinar_recomendacion(
        self, hr: Optional[float], hrv: Optional[float],
        pasos: int, stress: Optional[int],
    ) -> Dict:
        """Determina la recomendación de entrenamiento."""
        if hrv and self._hrv_baseline:
            if hrv > self._hrv_baseline * 1.1:
                return {
                    "estado": "listo",
                    "recomendacion": "Tu HRV está alta. Momento ideal para entrenar fuerte.",
                    "tipo_ejercicio": "Alta intensidad: running, HIIT, pesas",
                    "emoji": "🔥",
                }
            elif hrv < self._hrv_baseline * 0.85:
                return {
                    "estado": "recuperacion",
                    "recomendacion": "Tu cuerpo pide descanso. HRV baja = día de recuperación activa.",
                    "tipo_ejercicio": "Yoga suave, caminata, estiramientos",
                    "emoji": "🧘",
                }

        if pasos > 12000:
            return {
                "estado": "activo",
                "recomendacion": "Ya te moviste mucho hoy. Hidratación y estiramientos.",
                "tipo_ejercicio": "Descanso merecido",
                "emoji": "💧",
            }

        if stress and stress > 60:
            return {
                "estado": "estresado",
                "recomendacion": "Ejercicio suave para bajar el cortisol. Nada intenso.",
                "tipo_ejercicio": "Caminata al aire libre, natación suave",
                "emoji": "🌿",
            }

        return {
            "estado": "normal",
            "recomendacion": "Buen momento para mover el cuerpo. 30 min de actividad moderada.",
            "tipo_ejercicio": "Caminata rápida, bicicleta, natación",
            "emoji": "🚶",
        }

    def obtener_estado(self) -> Dict:
        return {
            "hrv_baseline": self._hrv_baseline,
            "consejos_dados": len(self._consejos_dados),
        }
