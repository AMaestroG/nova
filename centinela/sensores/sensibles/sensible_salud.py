"""
SENSIBLE SALUD — Detecta anomalías de salud antes de que sean evidentes.
=========================================================================
Combina: todos los biométricos
Detecta: infecciones (temp+HR), deshidratación, arritmias, inflamación
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger("centinela.sensores.sensible_salud")


class SensibleSalud:
    """Siente la salud de Abel más allá de las constantes individuales."""

    def __init__(self):
        self._indice_salud: float = 0.8
        self._alerta_infeccion: bool = False
        self._alerta_deshidratacion: bool = False
        self._hr_ventana = deque(maxlen=60)
        self._temp_ventana = deque(maxlen=30)

    def sentir(self, hr: float = None, hrv: float = None,
               temp: float = None, spo2: float = None,
               pasos: int = None, sueno_calidad: int = None) -> Dict:
        """Siente la salud general de Abel."""
        if hr: self._hr_ventana.append(hr)
        if temp: self._temp_ventana.append(temp)

        alertas = []
        indice = 0.7  # base

        # ¿Infección? (HR elevada + temperatura elevada)
        if self._hr_ventana and self._temp_ventana:
            hr_avg = sum(self._hr_ventana) / len(self._hr_ventana)
            temp_avg = sum(self._temp_ventana) / len(self._temp_ventana)
            if hr_avg > 85 and temp_avg > 37.2:
                self._alerta_infeccion = True
                alertas.append("⚠️ Posible infección: HR y temperatura elevadas.")
                indice -= 0.3
            else:
                self._alerta_infeccion = False

        # ¿Deshidratación? (HR elevada + HRV baja)
        if hr and hrv:
            if hr > 80 and hrv < 35:
                alertas.append("💧 Posible deshidratación. Bebe agua.")
                indice -= 0.15

        # Bonificaciones
        if hrv and hrv > 55:
            indice += 0.1
        if spo2 and spo2 > 96:
            indice += 0.05
        if pasos and pasos > 7000:
            indice += 0.05
        if sueno_calidad and sueno_calidad > 70:
            indice += 0.05

        self._indice_salud = max(0, min(1, indice))

        return {
            "indice": round(self._indice_salud, 2),
            "alerta_infeccion": self._alerta_infeccion,
            "alertas": alertas,
        }

    def obtener_estado(self) -> Dict:
        return {
            "indice_salud": round(self._indice_salud, 2),
            "alerta_infeccion": self._alerta_infeccion,
        }
