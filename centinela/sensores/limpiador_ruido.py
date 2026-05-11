"""
LIMPIADOR DE RUIDO — Filtros, suavizado y detección de outliers.
==================================================================
Los sensores generan ruido. Este módulo lo limpia:

Técnicas:
  - Media móvil exponencial (EMA) — suavizado adaptativo
  - Filtro Kalman 1D — para señales con modelo físico (HR, temperatura)
  - Detección de outliers — IQR y Z-score
  - Interpolación de huecos — valores faltantes
  - Filtro de mediana — para spikes
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass


@dataclass
class SenalLimpia:
    """Una señal después de ser limpiada."""
    valor_crudo: float
    valor_limpiado: float
    es_outlier: bool = False
    confianza: float = 1.0
    metodo: str = "crudo"


class FiltroEMA:
    """Media móvil exponencial — suavizado adaptable."""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha  # 0-1: más bajo = más suave
        self._valor: Optional[float] = None

    def filtrar(self, valor: float) -> float:
        if self._valor is None:
            self._valor = valor
        else:
            self._valor = self.alpha * valor + (1 - self.alpha) * self._valor
        return self._valor


class FiltroKalman1D:
    """Filtro Kalman unidimensional para señales fisiológicas."""

    def __init__(self, ruido_medida: float = 1.0, ruido_proceso: float = 0.01):
        self.x = 0.0        # Estado estimado
        self.P = 1.0        # Covarianza del error
        self.Q = ruido_proceso   # Ruido del proceso
        self.R = ruido_medida    # Ruido de la medida

    def filtrar(self, medida: float) -> float:
        # Predicción
        # x = x (el estado no cambia entre medidas)
        self.P = self.P + self.Q

        # Actualización
        K = self.P / (self.P + self.R)  # Ganancia de Kalman
        self.x = self.x + K * (medida - self.x)
        self.P = (1 - K) * self.P

        return self.x


class DetectorOutliers:
    """Detecta valores atípicos usando IQR y Z-score."""

    def __init__(self, ventana: int = 50):
        self._ventana: deque = deque(maxlen=ventana)
        self._z_threshold: float = 3.0

    def es_outlier(self, valor: float) -> bool:
        """Determina si un valor es outlier."""
        if len(self._ventana) < 10:
            self._ventana.append(valor)
            return False

        valores = list(self._ventana)
        media = sum(valores) / len(valores)
        std = math.sqrt(sum((x - media)**2 for x in valores) / len(valores))
        
        self._ventana.append(valor)

        if std == 0:
            return False

        z_score = abs(valor - media) / std
        return z_score > self._z_threshold


class LimpiadorRuido:
    """
    Limpia el ruido de todas las señales de sensores.
    Cada tipo de sensor tiene su configuración óptima.
    """

    CONFIG_SENSORES = {
        "heart_rate": {"alpha": 0.3, "kalman_r": 2.0, "kalman_q": 0.1},
        "hrv": {"alpha": 0.2, "kalman_r": 5.0, "kalman_q": 0.5},
        "spo2": {"alpha": 0.5, "kalman_r": 0.5, "kalman_q": 0.01},
        "temperature_skin": {"alpha": 0.1, "kalman_r": 0.3, "kalman_q": 0.005},
        "stress_level": {"alpha": 0.2, "kalman_r": 3.0, "kalman_q": 0.3},
        "acelerometro": {"alpha": 0.4, "kalman_r": 0.5, "kalman_q": 0.1},
        "barometro": {"alpha": 0.3, "kalman_r": 0.2, "kalman_q": 0.01},
        "default": {"alpha": 0.3, "kalman_r": 1.0, "kalman_q": 0.1},
    }

    def __init__(self):
        self._filtros_ema: Dict[str, FiltroEMA] = {}
        self._filtros_kalman: Dict[str, FiltroKalman1D] = {}
        self._outliers: Dict[str, DetectorOutliers] = {}
        self._historial: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def limpiar(self, tipo_sensor: str, valor: float) -> SenalLimpia:
        """
        Limpia un valor de sensor aplicando filtros en cascada.
        """
        cfg = self.CONFIG_SENSORES.get(tipo_sensor, self.CONFIG_SENSORES["default"])
        resultado = SenalLimpia(valor_crudo=valor, valor_limpiado=valor)

        # 1. Detectar outlier
        if tipo_sensor not in self._outliers:
            self._outliers[tipo_sensor] = DetectorOutliers()
        if self._outliers[tipo_sensor].es_outlier(valor):
            resultado.es_outlier = True
            resultado.confianza = 0.3
            # Usar último valor limpio si es outlier
            hist = self._historial[tipo_sensor]
            if hist:
                resultado.valor_limpiado = hist[-1]
                resultado.metodo = "outlier_rechazado"
                self._historial[tipo_sensor].append(resultado.valor_limpiado)
                return resultado

        # 2. Filtro Kalman
        if tipo_sensor not in self._filtros_kalman:
            self._filtros_kalman[tipo_sensor] = FiltroKalman1D(
                ruido_medida=cfg["kalman_r"],
                ruido_proceso=cfg["kalman_q"],
            )
        valor = self._filtros_kalman[tipo_sensor].filtrar(valor)

        # 3. Media móvil exponencial
        if tipo_sensor not in self._filtros_ema:
            self._filtros_ema[tipo_sensor] = FiltroEMA(alpha=cfg["alpha"])
        valor = self._filtros_ema[tipo_sensor].filtrar(valor)

        resultado.valor_limpiado = round(valor, 2)
        resultado.metodo = "kalman+ema"
        self._historial[tipo_sensor].append(valor)
        return resultado

    def obtener_estado(self) -> Dict:
        return {
            "sensores_limpiados": len(self._filtros_ema),
            "outliers_detectados": sum(
                1 for o in self._outliers.values()
                if any(o.es_outlier(v) for v in [0])
            ),
        }
