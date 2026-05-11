"""
SENSIBLE SUEÑO — Detecta calidad y patrones de sueño.
=======================================================
Combina: etapa de sueño, HR nocturna, HRV nocturna, movimiento, SpO2
Detecta: sueño profundo, REM, ligero, desvelo, apnea
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_sueno")


class SensibleSueno:
    """Siente cómo duerme Abel."""

    def __init__(self):
        self._calidad_actual: float = 0.5
        self._etapa_actual: str = "despierto"
        self._horas_dormidas: float = 0.0
        self._despertares: int = 0
        self._spo2_min: Optional[float] = None

    def sentir(self, etapa: str = None, hr: float = None,
               spo2: float = None, calidad: int = None) -> Dict:
        """Siente la calidad del sueño."""
        if etapa:
            self._etapa_actual = etapa

        if calidad is not None:
            self._calidad_actual = calidad / 100

        if spo2:
            if self._spo2_min is None or spo2 < self._spo2_min:
                self._spo2_min = spo2

        alerta = None
        if self._spo2_min and self._spo2_min < 90:
            alerta = "⚠️ SpO2 bajó durante el sueño. Posible apnea."
        if self._calidad_actual < 0.4:
            alerta = "😴 Sueño de baja calidad. Prioriza descanso."

        return {
            "etapa": self._etapa_actual,
            "calidad": round(self._calidad_actual, 2),
            "spo2_min": self._spo2_min,
            "alerta": alerta,
        }

    def obtener_estado(self) -> Dict:
        return {
            "etapa": self._etapa_actual,
            "calidad": self._calidad_actual,
        }
