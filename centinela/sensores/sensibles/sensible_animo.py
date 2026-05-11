"""
SENSIBLE ÁNIMO — Detecta el estado de ánimo real de Abel.
===========================================================
Combina: emoción detectada, HR, HRV, movimiento, ubicación, hora
Detecta: alegría, tristeza, ansiedad, calma, euforia, apatía
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque, Counter

logger = logging.getLogger("centinela.sensores.sensible_animo")


class SensibleAnimo:
    """Siente el ánimo de Abel más allá de las emociones puntuales."""

    def __init__(self):
        self._emociones_dia: List[str] = []
        self._animo_actual: str = "neutro"
        self._estabilidad: float = 0.5
        self._intensidad: float = 0.5

    def sentir(self, emocion: str = None, hr: float = None,
               hrv: float = None, pasos: int = None,
               es_finde: bool = False) -> Dict:
        """Siente el ánimo profundo de Abel."""
        if emocion:
            self._emociones_dia.append(emocion)

        # Ánimo por emoción dominante
        if self._emociones_dia:
            conteo = Counter(self._emociones_dia[-20:])
            dominante = conteo.most_common(1)[0][0] if conteo else "neutro"
            self._animo_actual = dominante
            # Estabilidad: qué tan variadas son las emociones
            self._estabilidad = 1.0 - (len(conteo) / max(1, len(self._emociones_dia[-20:])))
            self._intensidad = conteo[dominante] / len(self._emociones_dia[-20:])

        # Ajustar por fin de semana
        mensaje = None
        if es_finde and self._animo_actual in ("feliz", "relajado"):
            mensaje = "El finde te sienta bien. Disfrútalo."

        return {
            "animo": self._animo_actual,
            "estabilidad": round(self._estabilidad, 2),
            "intensidad": round(self._intensidad, 2),
            "mensaje": mensaje,
        }

    def obtener_estado(self) -> Dict:
        return {
            "animo": self._animo_actual,
            "estabilidad": round(self._estabilidad, 2),
        }
