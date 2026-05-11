"""
FUSIÓN SENSORIAL — Combina todos los sensores en una percepción unificada.
============================================================================
El Z Fold + Watch 8 generan docenas de flujos de datos. La fusión sensorial
los combina en una sola "percepción" coherente, como un cerebro integra
visión, oído y tacto en una experiencia unificada.

Capas:
  1. CRUDO: datos directos de cada sensor
  2. LIMPIO: datos filtrados (ruido eliminado)
  3. FUSIONADO: combinación de sensores relacionados
  4. INTERPRETADO: significado de alto nivel

Ejemplo:
  Acelerómetro(z=9.81) + GPS(vel=0) + Proximidad(cerca) → "Teléfono en mesa"
  HR(82) + HRV(55) + Temp(36.6) + Stress(28) → "Abel tranquilo, buena forma"
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("centinela.sensores.fusion")


class NivelFusion(Enum):
    CRUDO = auto()
    LIMPIO = auto()
    FUSIONADO = auto()
    INTERPRETADO = auto()


@dataclass
class PercepcionUnificada:
    """El mundo según todos los sensores, unificado."""
    timestamp: str = ""
    
    # Físico (acelerómetro + giroscopio + gravedad)
    orientacion: str = "desconocida"      # boca_arriba, boca_abajo, vertical, horizontal
    movimiento: str = "quieto"            # quieto, caminando, corriendo, vehiculo, bicicleta
    caida_detectada: bool = False
    
    # Entorno (luz + proximidad + barómetro + micrófono)
    ubicacion_estimada: str = "desconocida"  # bolsillo, mesa, mano, exterior, interior
    luminosidad: str = "media"
    ruido_ambiente: str = "bajo"
    presion_tendencia: str = "estable"
    
    # Abel (Watch 8 + fusión)
    estado_abel: str = "desconocido"       # despierto_activo, tranquilo, estresado, durmiendo
    nivel_estres: float = 0.0              # 0-1 combinado
    nivel_fatiga: float = 0.0
    nivel_energia: float = 0.5
    calidad_sueno_estimada: float = 0.5
    
    # Confianza de la percepción
    confianza: float = 0.5
    sensores_activos: int = 0


class FusionSensorial:
    """
    Combina datos de todos los sensores en una percepción unificada.
    Como un cerebro que integra sentidos.
    """

    def __init__(self):
        # Ventanas de datos para cada sensor
        self._ventanas: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._ultima_percepcion: Optional[PercepcionUnificada] = None
        self._confianza_por_sensor: Dict[str, float] = {}

    def alimentar(self, tipo: str, datos: Dict[str, Any]) -> None:
        """Alimenta un nuevo dato de sensor al fusionador."""
        clave = f"{tipo}:{datetime.now(timezone.utc).timestamp()}"
        self._ventanas[tipo].append({
            "datos": datos,
            "timestamp": datetime.now(timezone.utc),
        })

    def fusionar(self) -> PercepcionUnificada:
        """
        Fusiona todos los sensores en una percepción unificada.
        """
        p = PercepcionUnificada(timestamp=datetime.now(timezone.utc).isoformat())
        sensores_activos = 0

        # ──── FUSIÓN FÍSICA ────
        accel = self._ultimo("acelerometro")
        giro = self._ultimo("giroscopio")
        gps = self._ultimo("gps")

        if accel:
            sensores_activos += 1
            ax = accel.get("x", 0)
            ay = accel.get("y", 0)
            az = accel.get("z", 9.81)
            
            # Orientación del teléfono
            if abs(az) > 8:
                p.orientacion = "boca_arriba" if az > 0 else "boca_abajo"
            elif abs(ax) > 8:
                p.orientacion = "vertical"
            else:
                p.orientacion = "horizontal"

            # Detección de movimiento
            magnitud = math.sqrt(ax**2 + ay**2 + (az - 9.81)**2)
            if magnitud < 0.3:
                p.movimiento = "quieto"
            elif magnitud < 2:
                p.movimiento = "caminando"
            elif magnitud < 8:
                p.movimiento = "corriendo"
            else:
                p.movimiento = "movimiento_brusco"

            # Caída libre
            total = math.sqrt(ax**2 + ay**2 + az**2)
            if total < 2:
                p.caida_detectada = True

        # GPS refina movimiento
        if gps:
            sensores_activos += 1
            vel = gps.get("velocidad", 0)
            if vel > 20:
                p.movimiento = "vehiculo"
            elif vel > 8:
                p.movimiento = "bicicleta"

        # ──── FUSIÓN ENTORNO ────
        luz = self._ultimo("luz_ambiental")
        prox = self._ultimo("proximidad")
        baro = self._ultimo("barometro")
        oido = self._ultimo("microfono")

        if luz:
            sensores_activos += 1
            lux = luz.get("x", luz.get("lux", 500))
            if lux < 5:
                p.luminosidad = "oscuridad"
            elif lux < 100:
                p.luminosidad = "tenue"
            elif lux < 1000:
                p.luminosidad = "interior"
            elif lux < 10000:
                p.luminosidad = "exterior_nublado"
            else:
                p.luminosidad = "sol_directo"

        # Ubicación estimada del teléfono
        if prox and prox.get("x", prox.get("valor", 5)) < 1:
            p.ubicacion_estimada = "bolsillo" if p.luminosidad == "oscuridad" else "contra_oreja"
        elif p.movimiento == "quieto" and p.orientacion == "boca_arriba":
            p.ubicacion_estimada = "mesa"
        elif p.movimiento in ("caminando", "corriendo"):
            p.ubicacion_estimada = "mano"
        elif p.luminosidad in ("exterior_nublado", "sol_directo"):
            p.ubicacion_estimada = "exterior"
        else:
            p.ubicacion_estimada = "interior"

        # ──── FUSIÓN ABEL (Watch 8) ────
        health = self._ultimo("health")
        if health:
            sensores_activos += 1
            hr = health.get("heart_rate")
            hrv = health.get("hrv")
            stress = health.get("stress_level")
            sleep_stage = health.get("sleep_stage")

            # Estado de Abel
            if sleep_stage in ("profundo", "REM", "ligero"):
                p.estado_abel = "durmiendo"
            elif stress and stress > 70:
                p.estado_abel = "estresado"
            elif hr and hr > 100:
                p.estado_abel = "activo_intenso"
            elif hr and hrv and hrv > 50:
                p.estado_abel = "tranquilo"
            else:
                p.estado_abel = "despierto_activo"

            # Nivel de estrés combinado (HR + HRV + stress)
            p.nivel_estres = self._calcular_estres_combinado(hr, hrv, stress)

            # Nivel de fatiga (HRV bajo + HR elevado en reposo)
            p.nivel_fatiga = self._calcular_fatiga(hr, hrv, stress)

            # Nivel de energía
            p.nivel_energia = max(0, 1.0 - p.nivel_fatiga)

            # Calidad de sueño
            if sleep_stage:
                p.calidad_sueno_estimada = 0.9 if sleep_stage == "profundo" else 0.6

        p.sensores_activos = sensores_activos
        p.confianza = min(1.0, sensores_activos / 5)  # 5+ sensores = máxima confianza

        self._ultima_percepcion = p
        return p

    def _calcular_estres_combinado(
        self, hr: Optional[float], hrv: Optional[float], stress: Optional[int]
    ) -> float:
        """Calcula nivel de estrés combinando HR, HRV y stress reportado."""
        puntuacion = 0.0
        factores = 0

        if stress is not None:
            puntuacion += stress / 100
            factores += 1
        if hr and hr > 80:
            puntuacion += (hr - 80) / 70
            factores += 1
        if hrv and hrv < 40:
            puntuacion += (40 - hrv) / 40
            factores += 1

        if factores == 0:
            return 0.0
        return min(1.0, puntuacion / factores)

    def _calcular_fatiga(
        self, hr: Optional[float], hrv: Optional[float], stress: Optional[int]
    ) -> float:
        """Calcula nivel de fatiga combinado."""
        fatiga = 0.0
        factores = 0

        if hrv and hrv < 35:
            fatiga += (35 - hrv) / 35
            factores += 1
        if hr and hr > 75:
            fatiga += (hr - 75) / 75
            factores += 1
        if stress and stress > 50:
            fatiga += (stress - 50) / 50
            factores += 1

        if factores == 0:
            return 0.0
        return min(1.0, fatiga / factores)

    def _ultimo(self, tipo: str) -> Optional[Dict]:
        """Obtiene el último dato de un tipo de sensor."""
        ventana = self._ventanas.get(tipo)
        if ventana:
            return ventana[-1]["datos"]
        return None

    def obtener_estado(self) -> Dict:
        p = self.fusionar()
        return {
            "percepcion": {
                "orientacion": p.orientacion,
                "movimiento": p.movimiento,
                "caida": p.caida_detectada,
                "ubicacion_estimada": p.ubicacion_estimada,
                "luminosidad": p.luminosidad,
                "estado_abel": p.estado_abel,
                "nivel_estres": round(p.nivel_estres, 2),
                "nivel_fatiga": round(p.nivel_fatiga, 2),
                "nivel_energia": round(p.nivel_energia, 2),
            },
            "confianza": round(p.confianza, 2),
            "sensores_activos": p.sensores_activos,
            "timestamp": p.timestamp,
        }
