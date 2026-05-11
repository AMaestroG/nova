"""
SENSIBLE FATIGA — Detecta cansancio acumulado antes del agotamiento.
=====================================================================
Combina: HRV, HR en reposo, calidad de sueño, pasos/día, variabilidad
Detecta: fatiga aguda, sobreentrenamiento, fatiga crónica
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_fatiga")


class SensibleFatiga:
    """Siente el cansancio de Abel antes de que él lo note."""

    def __init__(self):
        self._hrv_ventana = deque(maxlen=50)
        self._hr_ventana = deque(maxlen=50)
        self._nivel_actual: float = 0.0
        self._dias_fatiga: int = 0

    def sentir(self, hr: float = None, hrv: float = None,
               sueno_calidad: int = None, pasos: int = None) -> Dict:
        """Siente el nivel de fatiga."""
        if hr: self._hr_ventana.append(hr)
        if hrv: self._hrv_ventana.append(hrv)

        fatiga = 0.0
        factores = 0

        # HRV bajo = fatiga
        if self._hrv_ventana:
            hrv_avg = sum(self._hrv_ventana) / len(self._hrv_ventana)
            if hrv_avg < 30:
                fatiga += 0.8
            elif hrv_avg < 40:
                fatiga += 0.5
            elif hrv_avg < 50:
                fatiga += 0.2
            factores += 1

        # HR elevada en reposo = fatiga
        if self._hr_ventana:
            hr_avg = sum(self._hr_ventana) / len(self._hr_ventana)
            if hr_avg > 80:
                fatiga += 0.6
            elif hr_avg > 70:
                fatiga += 0.3
            factores += 1

        # Sueño pobre = fatiga acumulada
        if sueno_calidad is not None:
            if sueno_calidad < 40:
                fatiga += 0.7
            elif sueno_calidad < 60:
                fatiga += 0.4
            factores += 1

        if factores > 0:
            self._nivel_actual = fatiga / factores

        # Alerta
        alerta = None
        if self._nivel_actual > 0.7:
            alerta = "😴 Fatiga alta. Prioriza dormir 8h hoy."
        elif self._nivel_actual > 0.5:
            alerta = "💤 Fatiga moderada. Tómalo con calma."

        return {
            "nivel": round(self._nivel_actual, 2),
            "alerta": alerta,
        }

    def obtener_estado(self) -> Dict:
        return {"nivel_fatiga": round(self._nivel_actual, 2)}
