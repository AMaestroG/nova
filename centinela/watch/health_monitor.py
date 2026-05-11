"""
Procesador de datos biométricos del Galaxy Watch 8 Classic
Nova Homonexus - MAYORDOMO

Recibe y procesa datos de salud desde el Watch 8 vía:
1. Health Connect API (recomendado)
2. Samsung Health API
3. Datos enviados desde Termux (vía bridge)
"""

import json
import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

from centinela.config import ALERT_THRESHOLDS, DEVICE_WATCH8_ID

logger = logging.getLogger("centinela.health_monitor")

# =============================================================================
# CONSTANTES
# =============================================================================
HR_ZONES = {
    "zona_1_reposo": (40, 60),
    "zona_2_quema_grasa": (60, 70),
    "zona_3_cardio": (70, 80),
    "zona_4_alto_rendimiento": (80, 90),
    "zona_5_maximo": (90, 100),
}

BP_CLASSIFICATION = {
    "normal": {"sys_max": 120, "dia_max": 80},
    "elevada": {"sys_max": 129, "dia_max": 80},
    "hipertension_grado_1": {"sys_max": 139, "dia_max": 89},
    "hipertension_grado_2": {"sys_max": 180, "dia_max": 120},
    "crisis_hipertensiva": {"sys_max": 999, "dia_max": 999},
}

SLEEP_STAGES = {
    "despierto": "DESPIERTO",
    "light": "LIGERO",
    "deep": "PROFUNDO",
    "rem": "REM",
}


class HealthDataProcessor:
    """
    Procesa y analiza datos biométricos del Galaxy Watch 8 Classic.
    Mantiene ventanas de tiempo para cálculos de tendencias.
    """

    def __init__(self, window_minutes: int = 30):
        self.window_minutes = window_minutes
        # Buffers circulares para análisis de tendencias
        self._hr_buffer: deque = deque(maxlen=1800)  # 30 min a 1 Hz
        self._hrv_buffer: deque = deque(maxlen=180)
        self._spo2_buffer: deque = deque(maxlen=360)
        self._stress_buffer: deque = deque(maxlen=180)
        self._temp_buffer: deque = deque(maxlen=60)
        self._bp_buffer: deque = deque(maxlen=30)

    def procesar_health_data(
        self, datos: Dict[str, Any],
        device_id: str = DEVICE_WATCH8_ID,
    ) -> Dict[str, Any]:
        """
        Procesa datos crudos del Watch 8 y los prepara para la API.

        Args:
            datos: Datos biométricos del Watch 8
                   Ej: {"heart_rate": 72, "spo2": 98.5, ...}

        Returns:
            Dict listo para POST a /api/centinela/health
        """
        # Actualizar buffers
        self._actualizar_buffers(datos)

        # Calcular métricas derivadas
        hrv = self._calcular_hrv(datos)
        bp_map = self._calcular_presion_media(datos)

        # Clasificar estados
        hr_status = self._clasificar_hr(datos.get("heart_rate"))
        spo2_status = self._clasificar_spo2(datos.get("spo2"))
        stress_status = self._clasificar_stress(datos.get("stress_level"))

        return {
            "device_id": device_id,
            "heart_rate": datos.get("heart_rate"),
            "heart_rate_status": hr_status,
            "ecg_data": datos.get("ecg_data"),
            "ecg_interval_ms": datos.get("ecg_interval_ms"),
            "blood_pressure_sys": datos.get("blood_pressure_sys"),
            "blood_pressure_dia": datos.get("blood_pressure_dia"),
            "blood_pressure_map": bp_map,
            "temperature_skin": datos.get("temperature_skin"),
            "temperature_core": datos.get("temperature_core"),
            "spo2": datos.get("spo2"),
            "spo2_status": spo2_status,
            "stress_level": datos.get("stress_level"),
            "stress_status": stress_status,
            "sleep_stage": datos.get("sleep_stage"),
            "sleep_quality": datos.get("sleep_quality"),
            "steps": datos.get("steps"),
            "calories": datos.get("calories"),
            "distance_m": datos.get("distance_m"),
            "bioimpedance": datos.get("bioimpedance"),
            "bia_body_fat": datos.get("bia_body_fat"),
            "bia_muscle_mass": datos.get("bia_muscle_mass"),
            "bia_bone_mass": datos.get("bia_bone_mass"),
            "bia_body_water": datos.get("bia_body_water"),
            "bia_bmr": datos.get("bia_bmr"),
            "hrv": hrv,
            "hrv_sdnn": self._calcular_sdnn(),
            "hrv_rmssd": self._calcular_rmssd(),
            "battery_level": datos.get("battery_level"),
            "timestamp": (
                datos.get("timestamp")
                or datetime.now(timezone.utc).isoformat()
            ),
        }

    def _actualizar_buffers(self, datos: Dict[str, Any]):
        """Actualiza los buffers con nuevos datos."""
        if datos.get("heart_rate") is not None:
            self._hr_buffer.append({
                "value": datos["heart_rate"],
                "timestamp": datetime.now(timezone.utc),
            })
        if datos.get("hrv") is not None:
            self._hrv_buffer.append({
                "value": datos["hrv"],
                "timestamp": datetime.now(timezone.utc),
            })
        if datos.get("spo2") is not None:
            self._spo2_buffer.append({
                "value": datos["spo2"],
                "timestamp": datetime.now(timezone.utc),
            })
        if datos.get("stress_level") is not None:
            self._stress_buffer.append({
                "value": datos["stress_level"],
                "timestamp": datetime.now(timezone.utc),
            })
        if datos.get("temperature_skin") is not None:
            self._temp_buffer.append({
                "value": datos["temperature_skin"],
                "timestamp": datetime.now(timezone.utc),
            })
        if datos.get("blood_pressure_sys") is not None:
            self._bp_buffer.append({
                "sys": datos["blood_pressure_sys"],
                "dia": datos.get("blood_pressure_dia"),
                "timestamp": datetime.now(timezone.utc),
            })

    def _calcular_hrv(self, datos: Dict[str, Any]) -> Optional[float]:
        """Calcula o extrae HRV de los datos disponibles."""
        if datos.get("hrv") is not None:
            return datos["hrv"]

        # Estimar HRV desde HR si no hay dato directo
        hr = datos.get("heart_rate")
        if hr and hr > 0:
            rr_interval = 60000.0 / hr  # ms entre latidos
            # Estimación simple: HRV ~ 5-10% del RR interval
            return round(rr_interval * 0.07, 2)

        return None

    def _calcular_presion_media(
        self, datos: Dict[str, Any]
    ) -> Optional[int]:
        """Calcula la presión arterial media (MAP)."""
        sys = datos.get("blood_pressure_sys")
        dia = datos.get("blood_pressure_dia")
        if sys and dia:
            return round(dia + (sys - dia) / 3)
        return None

    def _clasificar_hr(self, hr: Optional[int]) -> Optional[str]:
        """Clasifica el estado de la frecuencia cardíaca."""
        if hr is None:
            return None
        if hr < ALERT_THRESHOLDS["heart_rate_critical_min"] or \
           hr > ALERT_THRESHOLDS["heart_rate_critical_max"]:
            return "CRITICO"
        if hr < ALERT_THRESHOLDS["heart_rate_min"] or \
           hr > ALERT_THRESHOLDS["heart_rate_max"]:
            return "ELEVADO"
        return "NORMAL"

    def _clasificar_spo2(self, spo2: Optional[float]) -> Optional[str]:
        """Clasifica el estado de saturación de oxígeno."""
        if spo2 is None:
            return None
        if spo2 < ALERT_THRESHOLDS["spo2_critical_min"]:
            return "CRITICO"
        if spo2 < ALERT_THRESHOLDS["spo2_min"]:
            return "BAJO"
        return "NORMAL"

    def _clasificar_stress(
        self, stress: Optional[int]
    ) -> Optional[str]:
        """Clasifica el nivel de estrés."""
        if stress is None:
            return None
        if stress > ALERT_THRESHOLDS["stress_level_critical"]:
            return "CRITICO"
        if stress > ALERT_THRESHOLDS["stress_level_max"]:
            return "ELEVADO"
        return "NORMAL"

    def _calcular_sdnn(self) -> Optional[float]:
        """Calcula SDNN (desviación estándar de intervalos NN)."""
        if len(self._hrv_buffer) < 2:
            return None
        valores = [h["value"] for h in self._hrv_buffer]
        return round(statistics.stdev(valores), 2) if len(valores) > 1 else None

    def _calcular_rmssd(self) -> Optional[float]:
        """Calcula RMSSD (root mean square of successive differences)."""
        if len(self._hrv_buffer) < 2:
            return None
        valores = [h["value"] for h in self._hrv_buffer]
        diferencias = [
            abs(valores[i] - valores[i - 1])
            for i in range(1, len(valores))
        ]
        if not diferencias:
            return None
        mean_sq = sum(d ** 2 for d in diferencias) / len(diferencias)
        return round(mean_sq ** 0.5, 2)

    def obtener_tendencias(self) -> Dict[str, Any]:
        """Obtiene tendencias de salud de la ventana actual."""
        tendencias = {}

        if self._hr_buffer:
            hrs = [h["value"] for h in self._hr_buffer]
            tendencias["heart_rate"] = {
                "actual": hrs[-1],
                "promedio": round(statistics.mean(hrs), 1),
                "min": min(hrs),
                "max": max(hrs),
                "tendencia": self._calcular_tendencia(hrs),
            }

        if self._spo2_buffer:
            spo2s = [s["value"] for s in self._spo2_buffer]
            tendencias["spo2"] = {
                "actual": spo2s[-1],
                "promedio": round(statistics.mean(spo2s), 1),
                "min": min(spo2s),
                "max": max(spo2s),
            }

        if self._stress_buffer:
            stresses = [s["value"] for s in self._stress_buffer]
            tendencias["stress"] = {
                "actual": stresses[-1],
                "promedio": round(statistics.mean(stresses), 1),
                "tendencia": self._calcular_tendencia(stresses),
            }

        return tendencias

    def _calcular_tendencia(self, valores: List[float]) -> str:
        """Calcula la tendencia de una serie de valores."""
        if len(valores) < 10:
            return "estable"

        # Comparar últimos 5 con los 5 anteriores
        recientes = valores[-5:]
        anteriores = valores[-10:-5]

        if not anteriores:
            return "estable"

        media_reciente = statistics.mean(recientes)
        media_anterior = statistics.mean(anteriores)
        cambio = media_reciente - media_anterior
        pct = (cambio / media_anterior) * 100 if media_anterior else 0

        if pct > 10:
            return "subiendo"
        if pct < -10:
            return "bajando"
        if pct > 5:
            return "ligero_aumento"
        if pct < -5:
            return "ligera_disminucion"
        return "estable"

    def detectar_anomalias(
        self, datos: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detecta anomalías en los datos biométricos."""
        anomalias = []

        # Heart rate fuera de rango
        hr = datos.get("heart_rate")
        if hr:
            if hr < 40:
                anomalias.append({
                    "tipo": "bradicardia",
                    "severidad": "alta" if hr < 35 else "media",
                    "valor": hr,
                    "mensaje": f"Frecuencia cardiaca baja: {hr} bpm",
                })
            elif hr > 180:
                anomalias.append({
                    "tipo": "taquicardia",
                    "severidad": "alta" if hr > 200 else "media",
                    "valor": hr,
                    "mensaje": f"Frecuencia cardiaca alta: {hr} bpm",
                })

        # SpO2 bajo
        spo2 = datos.get("spo2")
        if spo2 and spo2 < 90:
            anomalias.append({
                "tipo": "hipoxia",
                "severidad": "alta" if spo2 < 85 else "media",
                "valor": spo2,
                "mensaje": f"Saturacion de oxigeno baja: {spo2}%",
            })

        # Presión arterial alta
        sys = datos.get("blood_pressure_sys")
        if sys and sys > 160:
            anomalias.append({
                "tipo": "hipertension",
                "severidad": "alta" if sys > 180 else "media",
                "valor": sys,
                "mensaje": f"Presion arterial elevada: {sys} mmHg",
            })

        # Estrés alto sostenido
        stress = datos.get("stress_level")
        if stress and stress > 85:
            anomalias.append({
                "tipo": "estres_alto",
                "severidad": "media",
                "valor": stress,
                "mensaje": f"Nivel de estres elevado: {stress}%",
            })

        return anomalias


# =============================================================================
# INTERFAZ HEALTH CONNECT (para usar desde Termux)
# =============================================================================
class HealthConnectBridge:
    """
    Puente para leer datos de Samsung Health / Health Connect
    desde Termux en el Z Fold.
    """

    @staticmethod
    def leer_health_connect(
        tipo_dato: str,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Lee datos de Health Connect usando termux-api.

        Args:
            tipo_dato: heart_rate, blood_pressure, spo2, steps, sleep, etc.
            desde: Inicio del período
            hasta: Fin del período
        """
        import subprocess

        cmd = ["termux-health-connect", "--read", tipo_dato]
        if desde:
            cmd.extend(["--from", desde.isoformat()])
        if hasta:
            cmd.extend(["--to", hasta.isoformat()])

        try:
            resultado = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                return json.loads(resultado.stdout)
            return None
        except FileNotFoundError:
            logger.warning(
                "termux-health-connect no disponible. "
                "Usa Samsung Health directamente."
            )
            return None
        except Exception as e:
            logger.error("Error leyendo Health Connect: %s", str(e))
            return None

    @staticmethod
    def leer_watch_directo() -> Optional[Dict[str, Any]]:
        """
        Intenta leer datos directamente del Watch 8 vía Bluetooth.
        Requiere la app 'Watch Data Bridge' en el Z Fold.
        """
        import subprocess

        try:
            resultado = subprocess.run(
                ["termux-watch-data", "--read-all"],
                capture_output=True, text=True, timeout=10,
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                return json.loads(resultado.stdout)
            return None
        except FileNotFoundError:
            logger.debug(
                "termux-watch-data no disponible. "
                "Usando datos enviados desde el Watch."
            )
            return None
        except Exception as e:
            logger.error("Error leyendo Watch directo: %s", str(e))
            return None
