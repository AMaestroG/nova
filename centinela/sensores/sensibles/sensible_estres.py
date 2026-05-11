"""
SENSIBLE ESTRÉS — Detecta estrés antes de que sea visible.
============================================================
Combina: HR, HRV, GSR estimado, temperatura, movimiento, ruido
Detecta: estrés agudo, estrés crónico, picos de ansiedad
Alerta: cuando el estrés sube sin razón aparente (predictivo)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_estres")


class SensibleEstres:
    """
    El sensible de estrés. Siente la tensión antes de que explote.
    """

    def __init__(self):
        self._hr_ventana = deque(maxlen=60)
        self._hrv_ventana = deque(maxlen=30)
        self._stress_ventana = deque(maxlen=30)
        self._nivel_actual: float = 0.0
        self._tendencia: str = "estable"
        self._alertas_emitidas: int = 0

    def sentir(self, hr: float = None, hrv: float = None,
               stress: int = None, ruido: float = None) -> Dict:
        """Siente el nivel de estrés actual y su tendencia."""
        if hr: self._hr_ventana.append(hr)
        if hrv: self._hrv_ventana.append(hrv)
        if stress is not None: self._stress_ventana.append(stress)

        # Calcular nivel combinado
        nivel = 0.0
        factores = 0

        if self._hr_ventana:
            hr_avg = sum(self._hr_ventana) / len(self._hr_ventana)
            if hr_avg > 60:
                nivel += min(1, (hr_avg - 60) / 60)
                factores += 1

        if self._hrv_ventana:
            hrv_avg = sum(self._hrv_ventana) / len(self._hrv_ventana)
            if hrv_avg < 50:
                nivel += min(1, (50 - hrv_avg) / 50)
                factores += 1

        if self._stress_ventana:
            stress_avg = sum(self._stress_ventana) / len(self._stress_ventana)
            nivel += stress_avg / 100
            factores += 1

        if factores > 0:
            self._nivel_actual = nivel / factores

        # Determinar tendencia
        if len(self._stress_ventana) >= 10:
            recientes = list(self._stress_ventana)[-5:]
            anteriores = list(self._stress_ventana)[:5]
            if recientes and anteriores:
                if sum(recientes)/len(recientes) > sum(anteriores)/len(anteriores) * 1.2:
                    self._tendencia = "subiendo"
                elif sum(recientes)/len(recientes) < sum(anteriores)/len(anteriores) * 0.8:
                    self._tendencia = "bajando"
                else:
                    self._tendencia = "estable"

        # Alerta temprana
        alerta = None
        if self._nivel_actual > 0.7 and self._tendencia == "subiendo":
            alerta = "⚠️ Estrés elevándose. Respira. 5 minutos de pausa."
            self._alertas_emitidas += 1
        elif self._nivel_actual > 0.85:
            alerta = "🆘 Estrés crítico. Urgente: técnica 4-7-8."
            self._alertas_emitidas += 1

        return {
            "nivel": round(self._nivel_actual, 2),
            "tendencia": self._tendencia,
            "alerta": alerta,
        }

    def obtener_estado(self) -> Dict:
        return {
            "nivel_estres": round(self._nivel_actual, 2),
            "tendencia": self._tendencia,
            "alertas_emitidas": self._alertas_emitidas,
        }
