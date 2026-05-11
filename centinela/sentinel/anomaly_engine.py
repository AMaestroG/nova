"""
anomaly_engine — Motor de Detección de Anomalías
Nova Homonexus — SENTINEL

Detecta anomalías en:
  - Signos vitales (bradicardia, taquicardia, cambios de presión, SpO2)
  - Caídas (acelerómetro + giroscopio)
  - Patrones de sueño anómalos
  - Inactividad prolongada
  - Cambios bruscos de temperatura corporal
  - Arritmias detectables por HRV
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from collections import deque, defaultdict
from dataclasses import dataclass, field

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.anomaly")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AnomalyEvent:
    """Evento de anomalía detectada."""
    anomaly_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    device_id: str
    description: str
    current_value: Any
    threshold: Any
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "device_id": self.device_id,
            "description": self.description,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "details": self.details,
            "timestamp": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
        }


# =============================================================================
# ANOMALY ENGINE
# =============================================================================

class AnomalyEngine:
    """
    Motor de detección de anomalías biométricas y de sensores.

    Analiza datos en tiempo real para detectar:
      - Problemas cardíacos (bradicardia, taquicardia, arritmia)
      - Cambios bruscos de presión arterial
      - Caídas de SpO2
      - Caídas físicas (acelerómetro + giroscopio)
      - Picos de estrés
      - Inactividad prolongada
      - Anomalías de temperatura
      - Patrones de sueño anómalos
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        ad_cfg = self._rules.anomaly

        # Heart Rate
        self._hr_sudden_change = ad_cfg.get("hr_sudden_change", 30)
        self._bradycardia = ad_cfg.get("bradycardia_threshold", 40)
        self._tachycardia = ad_cfg.get("tachycardia_threshold", 180)

        # Presión arterial
        self._bp_sudden_sys = ad_cfg.get("bp_sudden_change_sys", 20)
        self._bp_sudden_dia = ad_cfg.get("bp_sudden_change_dia", 15)

        # SpO2
        self._spo2_drop = ad_cfg.get("spo2_drop_threshold", 5)
        self._spo2_critical = ad_cfg.get("spo2_critical", 88.0)

        # Estrés
        self._stress_spike = ad_cfg.get("stress_sudden_spike", 25)

        # Temperatura
        self._temp_change = ad_cfg.get("temp_sudden_change", 1.5)

        # Caídas
        self._fall_accel = ad_cfg.get(
            "fall_acceleration_threshold", 6.0
        )
        self._fall_post_window = ad_cfg.get(
            "fall_post_impact_window", 5
        )

        # Inactividad
        self._inactivity_min = ad_cfg.get(
            "inactivity_threshold_minutes", 120
        )
        self._inactivity_critical = ad_cfg.get(
            "inactivity_critical_minutes", 360
        )

        # Sueño
        self._sleep_rem_anomaly = ad_cfg.get(
            "sleep_rem_anomaly_pct", 40
        )
        self._sleep_min = ad_cfg.get("sleep_min_hours", 4)
        self._sleep_max = ad_cfg.get("sleep_max_hours", 14)

        # Arritmia
        self._arrhythmia_hrv = ad_cfg.get(
            "arrhythmia_hrv_sdnn_threshold", 20.0
        )

        # Ventana de análisis
        self._analysis_window = ad_cfg.get("analysis_window", 300)

        # Buffers de datos por dispositivo
        self._hr_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._bp_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50)
        )
        self._spo2_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50)
        )
        self._stress_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50)
        )
        self._temp_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50)
        )
        self._accel_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )
        self._movement_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._sleep_buffer: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=500)
        )

        # Último timestamp de actividad
        self._last_activity: Dict[str, float] = {}

        # Historial de anomalías
        self._anomaly_history: deque = deque(maxlen=10000)

        logger.info(
            "AnomalyEngine inicializado. "
            "Umbrales: HR=%d/%d, SpO2=%.1f, Caída=%.1fg",
            self._bradycardia,
            self._tachycardia,
            self._spo2_critical,
            self._fall_accel,
        )

    # ------------------------------------------------------------------
    # ANÁLISIS DE FRECUENCIA CARDÍACA
    # ------------------------------------------------------------------

    def analyze_heart_rate(
        self, device_id: str, hr: int, timestamp: float
    ) -> Optional[AnomalyEvent]:
        """
        Analiza la frecuencia cardíaca en busca de anomalías.

        Args:
            device_id: ID del dispositivo.
            hr: Frecuencia cardíaca en bpm.
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent si se detecta anomalía, None en caso contrario.
        """
        buffer = self._hr_buffer[device_id]
        buffer.append((timestamp, hr))

        # Bradicardia
        if hr < self._bradycardia:
            return AnomalyEvent(
                anomaly_type="bradycardia",
                severity="CRITICAL",
                device_id=device_id,
                description=(
                    f"Bradicardia detectada: {hr} bpm "
                    f"(umbral: <{self._bradycardia})"
                ),
                current_value=hr,
                threshold=self._bradycardia,
                details={"heart_rate": hr, "direction": "below"},
            )

        # Taquicardia
        if hr > self._tachycardia:
            return AnomalyEvent(
                anomaly_type="tachycardia",
                severity="CRITICAL",
                device_id=device_id,
                description=(
                    f"Taquicardia detectada: {hr} bpm "
                    f"(umbral: >{self._tachycardia})"
                ),
                current_value=hr,
                threshold=self._tachycardia,
                details={"heart_rate": hr, "direction": "above"},
            )

        # Cambio súbito (comparar con últimos valores)
        if len(buffer) >= 3:
            recent = list(buffer)[-3:-1]
            if recent:
                prev_hr = recent[0][1]
                change = abs(hr - prev_hr)
                if change >= self._hr_sudden_change:
                    return AnomalyEvent(
                        anomaly_type="sudden_hr_change",
                        severity="HIGH",
                        device_id=device_id,
                        description=(
                            f"Cambio súbito de HR: {prev_hr} -> {hr} "
                            f"bpm (delta: {change}, umbral: "
                            f"{self._hr_sudden_change})"
                        ),
                        current_value=hr,
                        threshold=self._hr_sudden_change,
                        details={
                            "previous_hr": prev_hr,
                            "current_hr": hr,
                            "change": change,
                        },
                    )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS DE PRESIÓN ARTERIAL
    # ------------------------------------------------------------------

    def analyze_blood_pressure(
        self,
        device_id: str,
        bp_sys: int,
        bp_dia: int,
        timestamp: float,
    ) -> Optional[AnomalyEvent]:
        """
        Analiza la presión arterial en busca de cambios bruscos.

        Args:
            device_id: ID del dispositivo.
            bp_sys: Presión sistólica (mmHg).
            bp_dia: Presión diastólica (mmHg).
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent o None.
        """
        buffer = self._bp_buffer[device_id]
        buffer.append((timestamp, bp_sys, bp_dia))

        if len(buffer) >= 2:
            prev = list(buffer)[-2]
            change_sys = abs(bp_sys - prev[1])
            change_dia = abs(bp_dia - prev[2])

            if change_sys >= self._bp_sudden_sys:
                return AnomalyEvent(
                    anomaly_type="sudden_bp_change",
                    severity="HIGH",
                    device_id=device_id,
                    description=(
                        f"Cambio brusco de presión sistólica: "
                        f"{prev[1]} -> {bp_sys} mmHg "
                        f"(delta: {change_sys})"
                    ),
                    current_value=bp_sys,
                    threshold=self._bp_sudden_sys,
                    details={
                        "previous_sys": prev[1],
                        "current_sys": bp_sys,
                        "change_sys": change_sys,
                        "previous_dia": prev[2],
                        "current_dia": bp_dia,
                    },
                )

            if change_dia >= self._bp_sudden_dia:
                return AnomalyEvent(
                    anomaly_type="sudden_bp_change",
                    severity="HIGH",
                    device_id=device_id,
                    description=(
                        f"Cambio brusco de presión diastólica: "
                        f"{prev[2]} -> {bp_dia} mmHg "
                        f"(delta: {change_dia})"
                    ),
                    current_value=bp_dia,
                    threshold=self._bp_sudden_dia,
                    details={
                        "previous_sys": prev[1],
                        "current_sys": bp_sys,
                        "previous_dia": prev[2],
                        "current_dia": bp_dia,
                        "change_dia": change_dia,
                    },
                )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS DE SpO2
    # ------------------------------------------------------------------

    def analyze_spo2(
        self, device_id: str, spo2: float, timestamp: float
    ) -> Optional[AnomalyEvent]:
        """
        Analiza la saturación de oxígeno.

        Args:
            device_id: ID del dispositivo.
            spo2: Saturación de oxígeno (%).
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent o None.
        """
        buffer = self._spo2_buffer[device_id]
        buffer.append((timestamp, spo2))

        # SpO2 crítico
        if spo2 < self._spo2_critical:
            return AnomalyEvent(
                anomaly_type="critical_spo2",
                severity="CRITICAL",
                device_id=device_id,
                description=(
                    f"SpO2 crítico: {spo2}% "
                    f"(umbral: <{self._spo2_critical}%)"
                ),
                current_value=spo2,
                threshold=self._spo2_critical,
                details={"spo2": spo2},
            )

        # Caída súbita de SpO2
        if len(buffer) >= 3:
            recent = list(buffer)[-3:-1]
            if recent:
                prev_spo2 = recent[0][1]
                drop = prev_spo2 - spo2
                if drop >= self._spo2_drop:
                    return AnomalyEvent(
                        anomaly_type="spo2_drop",
                        severity="HIGH",
                        device_id=device_id,
                        description=(
                            f"Caída de SpO2: {prev_spo2}% -> {spo2}% "
                            f"(delta: {drop:.1f}%, "
                            f"umbral: {self._spo2_drop}%)"
                        ),
                        current_value=spo2,
                        threshold=self._spo2_drop,
                        details={
                            "previous_spo2": prev_spo2,
                            "current_spo2": spo2,
                            "drop": drop,
                        },
                    )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS DE ESTRÉS
    # ------------------------------------------------------------------

    def analyze_stress(
        self, device_id: str, stress: int, timestamp: float
    ) -> Optional[AnomalyEvent]:
        """
        Analiza el nivel de estrés en busca de picos súbitos.

        Args:
            device_id: ID del dispositivo.
            stress: Nivel de estrés (0-100).
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent o None.
        """
        buffer = self._stress_buffer[device_id]
        buffer.append((timestamp, stress))

        if len(buffer) >= 2:
            prev = list(buffer)[-2][1]
            spike = stress - prev
            if spike >= self._stress_spike:
                return AnomalyEvent(
                    anomaly_type="stress_spike",
                    severity="HIGH",
                    device_id=device_id,
                    description=(
                        f"Pico de estrés: {prev} -> {stress} "
                        f"(delta: {spike}, "
                        f"umbral: {self._stress_spike})"
                    ),
                    current_value=stress,
                    threshold=self._stress_spike,
                    details={
                        "previous_stress": prev,
                        "current_stress": stress,
                        "spike": spike,
                    },
                )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS DE TEMPERATURA CORPORAL
    # ------------------------------------------------------------------

    def analyze_temperature(
        self,
        device_id: str,
        temp: float,
        timestamp: float,
    ) -> Optional[AnomalyEvent]:
        """
        Analiza la temperatura corporal en busca de cambios bruscos.

        Args:
            device_id: ID del dispositivo.
            temp: Temperatura en °C.
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent o None.
        """
        buffer = self._temp_buffer[device_id]
        buffer.append((timestamp, temp))

        if len(buffer) >= 2:
            prev = list(buffer)[-2][1]
            change = abs(temp - prev)
            if change >= self._temp_change:
                direction = "aumento" if temp > prev else "disminución"
                return AnomalyEvent(
                    anomaly_type="sudden_temp_change",
                    severity="HIGH",
                    device_id=device_id,
                    description=(
                        f"Cambio brusco de temperatura: "
                        f"{prev}°C -> {temp}°C "
                        f"({direction} de {change:.1f}°C, "
                        f"umbral: {self._temp_change}°C)"
                    ),
                    current_value=temp,
                    threshold=self._temp_change,
                    details={
                        "previous_temp": prev,
                        "current_temp": temp,
                        "change": change,
                        "direction": direction,
                    },
                )

        return None

    # ------------------------------------------------------------------
    # DETECCIÓN DE CAÍDAS
    # ------------------------------------------------------------------

    def detect_fall(
        self,
        device_id: str,
        accel_x: float,
        accel_y: float,
        accel_z: float,
        gyro_x: Optional[float] = None,
        gyro_y: Optional[float] = None,
        gyro_z: Optional[float] = None,
        timestamp: float = 0,
    ) -> Optional[AnomalyEvent]:
        """
        Detecta caídas usando acelerómetro y giroscopio.

        Una caída se caracteriza por:
          1. Alta aceleración combinada (>6g) = impacto
          2. Cambio de orientación (giroscopio)
          3. Post-impacto: inactividad relativa

        Args:
            device_id: ID del dispositivo.
            accel_x, accel_y, accel_z: Aceleración en cada eje (g).
            gyro_x, gyro_y, gyro_z: Velocidad angular (dps, opcional).
            timestamp: Timestamp de la lectura.

        Returns:
            AnomalyEvent si se detecta caída, None en caso contrario.
        """
        buffer = self._accel_buffer[device_id]

        # Calcular aceleración combinada
        accel_magnitude = (
            accel_x ** 2 + accel_y ** 2 + accel_z ** 2
        ) ** 0.5

        buffer.append({
            "time": timestamp or time.time(),
            "accel_mag": accel_magnitude,
            "accel": (accel_x, accel_y, accel_z),
            "gyro": (gyro_x, gyro_y, gyro_z),
        })

        # Detectar impacto
        if accel_magnitude >= self._fall_accel:
            # Verificar cambio de orientación (giroscopio)
            orientation_change = False
            if all(g is not None for g in [gyro_x, gyro_y, gyro_z]):
                gyro_mag = (
                    gyro_x ** 2 + gyro_y ** 2 + gyro_z ** 2
                ) ** 0.5
                orientation_change = gyro_mag > 200  # dps

            # Verificar post-impacto (inactividad después del golpe)
            post_impact_inactive = False
            if len(buffer) >= 5:
                post = list(buffer)[-5:]
                post_mags = [p["accel_mag"] for p in post]
                avg_post = sum(post_mags) / len(post_mags)
                post_impact_inactive = avg_post < 1.5  # g

            # Si hay impacto + cambio de orientación o inactividad
            # Sin giroscopio: asumir caída si la aceleración es muy alta (>8g)
            if orientation_change or post_impact_inactive or accel_magnitude >= 8.0:
                return AnomalyEvent(
                    anomaly_type="fall_detected",
                    severity="CRITICAL",
                    device_id=device_id,
                    description=(
                        f"Caída detectada! "
                        f"Aceleración: {accel_magnitude:.1f}g "
                        f"(umbral: {self._fall_accel}g)"
                    ),
                    current_value=round(accel_magnitude, 2),
                    threshold=self._fall_accel,
                    details={
                        "accel_magnitude": round(accel_magnitude, 2),
                        "accel": {
                            "x": accel_x,
                            "y": accel_y,
                            "z": accel_z,
                        },
                        "orientation_change": orientation_change,
                        "post_impact_inactive": post_impact_inactive,
                    },
                )

        return None

    # ------------------------------------------------------------------
    # DETECCIÓN DE INACTIVIDAD
    # ------------------------------------------------------------------

    def check_inactivity(
        self, device_id: str, current_time: float
    ) -> Optional[AnomalyEvent]:
        """
        Verifica si hay inactividad prolongada.

        Args:
            device_id: ID del dispositivo.
            current_time: Timestamp actual.

        Returns:
            AnomalyEvent si hay inactividad, None en caso contrario.
        """
        last_active = self._last_activity.get(device_id)
        if last_active is None:
            self._last_activity[device_id] = current_time
            return None

        inactive_minutes = (current_time - last_active) / 60

        if inactive_minutes >= self._inactivity_critical:
            return AnomalyEvent(
                anomaly_type="prolonged_inactivity",
                severity="CRITICAL",
                device_id=device_id,
                description=(
                    f"Inactividad crítica: "
                    f"{inactive_minutes:.0f} minutos sin movimiento "
                    f"(umbral crítico: {self._inactivity_critical} min)"
                ),
                current_value=round(inactive_minutes, 0),
                threshold=self._inactivity_critical,
                details={
                    "inactive_minutes": round(inactive_minutes, 0),
                    "last_activity": datetime.fromtimestamp(
                        last_active, tz=timezone.utc
                    ).isoformat(),
                },
            )

        if inactive_minutes >= self._inactivity_min:
            return AnomalyEvent(
                anomaly_type="prolonged_inactivity",
                severity="WARNING",
                device_id=device_id,
                description=(
                    f"Inactividad prolongada: "
                    f"{inactive_minutes:.0f} minutos sin movimiento "
                    f"(umbral: {self._inactivity_min} min)"
                ),
                current_value=round(inactive_minutes, 0),
                threshold=self._inactivity_min,
                details={
                    "inactive_minutes": round(inactive_minutes, 0),
                    "last_activity": datetime.fromtimestamp(
                        last_active, tz=timezone.utc
                    ).isoformat(),
                },
            )

        return None

    def update_activity(self, device_id: str) -> None:
        """Actualiza el timestamp de última actividad."""
        self._last_activity[device_id] = time.time()

    # ------------------------------------------------------------------
    # ANÁLISIS DE ARRITMIA (HRV)
    # ------------------------------------------------------------------

    def analyze_arrhythmia(
        self,
        device_id: str,
        hrv_sdnn: Optional[float],
        hrv_rmssd: Optional[float],
    ) -> Optional[AnomalyEvent]:
        """
        Detecta posibles arritmias basadas en HRV.

        Args:
            device_id: ID del dispositivo.
            hrv_sdnn: Desviación estándar de intervalos NN (ms).
            hrv_rmssd: Raíz cuadrada de diferencias sucesivas (ms).

        Returns:
            AnomalyEvent o None.
        """
        if hrv_sdnn is not None and hrv_sdnn < self._arrhythmia_hrv:
            return AnomalyEvent(
                anomaly_type="possible_arrhythmia",
                severity="HIGH",
                device_id=device_id,
                description=(
                    f"Posible arritmia detectada: "
                    f"HRV-SDNN={hrv_sdnn:.1f}ms "
                    f"(umbral: <{self._arrhythmia_hrv}ms)"
                ),
                current_value=hrv_sdnn,
                threshold=self._arrhythmia_hrv,
                details={
                    "hrv_sdnn": hrv_sdnn,
                    "hrv_rmssd": hrv_rmssd,
                },
            )

        # HRV anormalmente alto (>150ms) puede indicar condiciones como
        # bradicardia sinusal o respuesta vagal excesiva
        if hrv_sdnn is not None and hrv_sdnn > 150.0:
            return AnomalyEvent(
                anomaly_type="high_hrv_anomaly",
                severity="WARNING",
                device_id=device_id,
                description=(
                    f"HRV anormalmente alto: "
                    f"HRV-SDNN={hrv_sdnn:.1f}ms "
                    f"(umbral: >150ms)"
                ),
                current_value=hrv_sdnn,
                threshold=150.0,
                details={
                    "hrv_sdnn": hrv_sdnn,
                    "hrv_rmssd": hrv_rmssd,
                },
            )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS DE SUEÑO
    # ------------------------------------------------------------------

    def analyze_sleep(
        self,
        device_id: str,
        sleep_stage: Optional[str],
        sleep_quality: Optional[int],
    ) -> Optional[AnomalyEvent]:
        """
        Analiza patrones de sueño en busca de anomalías.

        Args:
            device_id: ID del dispositivo.
            sleep_stage: Etapa actual del sueño.
            sleep_quality: Calidad del sueño (0-100).

        Returns:
            AnomalyEvent o None.
        """
        buffer = self._sleep_buffer[device_id]

        if sleep_stage:
            buffer.append({
                "time": time.time(),
                "stage": sleep_stage,
                "quality": sleep_quality,
            })

        # Anomalía en fase REM
        if sleep_stage == "rem":
            rem_count = sum(
                1 for s in buffer if s.get("stage") == "rem"
            )
            total = len(buffer)
            if total > 10:
                rem_pct = (rem_count / total) * 100
                if rem_pct > 60:  # más del 60% REM es anómalo
                    return AnomalyEvent(
                        anomaly_type="sleep_rem_anomaly",
                        severity="WARNING",
                        device_id=device_id,
                        description=(
                            f"Anomalía en sueño REM: "
                            f"{rem_pct:.0f}% del tiempo en REM "
                            f"(esperado: ~20-25%)"
                        ),
                        current_value=round(rem_pct, 0),
                        threshold=self._sleep_rem_anomaly,
                        details={
                            "rem_percentage": round(rem_pct, 1),
                            "rem_count": rem_count,
                            "total_readings": total,
                        },
                    )

        return None

    # ------------------------------------------------------------------
    # ANÁLISIS COMPLETO DE SALUD
    # ------------------------------------------------------------------

    def analyze_health_record(
        self,
        device_id: str,
        health_data: Dict[str, Any],
    ) -> List[AnomalyEvent]:
        """
        Analiza un registro completo de salud en busca de anomalías.

        Args:
            device_id: ID del dispositivo.
            health_data: Datos de salud del Watch 8.

        Returns:
            Lista de anomalías detectadas.
        """
        now = time.time()
        anomalias: List[AnomalyEvent] = []

        # Actualizar actividad
        self.update_activity(device_id)

        # Heart Rate
        hr = health_data.get("heart_rate")
        if hr is not None:
            anomaly = self.analyze_heart_rate(device_id, hr, now)
            if anomaly:
                anomalias.append(anomaly)

        # Presión arterial
        bp_sys = health_data.get("blood_pressure_sys")
        bp_dia = health_data.get("blood_pressure_dia")
        if bp_sys is not None and bp_dia is not None:
            anomaly = self.analyze_blood_pressure(
                device_id, bp_sys, bp_dia, now
            )
            if anomaly:
                anomalias.append(anomaly)

        # SpO2
        spo2 = health_data.get("spo2")
        if spo2 is not None:
            anomaly = self.analyze_spo2(device_id, spo2, now)
            if anomaly:
                anomalias.append(anomaly)

        # Estrés
        stress = health_data.get("stress_level")
        if stress is not None:
            anomaly = self.analyze_stress(device_id, stress, now)
            if anomaly:
                anomalias.append(anomaly)

        # Temperatura
        temp = health_data.get("temperature_skin")
        if temp is not None:
            anomaly = self.analyze_temperature(
                device_id, temp, now
            )
            if anomaly:
                anomalias.append(anomaly)

        # Arritmia (HRV)
        hrv_sdnn = health_data.get("hrv_sdnn")
        hrv_rmssd = health_data.get("hrv_rmssd")
        if hrv_sdnn is not None:
            anomaly = self.analyze_arrhythmia(
                device_id, hrv_sdnn, hrv_rmssd
            )
            if anomaly:
                anomalias.append(anomaly)

        # Sueño
        sleep_stage = health_data.get("sleep_stage")
        sleep_quality = health_data.get("sleep_quality")
        if sleep_stage:
            anomaly = self.analyze_sleep(
                device_id, sleep_stage, sleep_quality
            )
            if anomaly:
                anomalias.append(anomaly)

        # Registrar anomalías
        for a in anomalias:
            self._anomaly_history.append(a)
            logger.log(
                logging.CRITICAL
                if a.severity == "CRITICAL"
                else logging.WARNING,
                "Anomalía [%s/%s]: %s",
                a.severity,
                a.anomaly_type,
                a.description,
            )

        return anomalias

    # ------------------------------------------------------------------
    # ANÁLISIS DE SENSORES (CAÍDAS)
    # ------------------------------------------------------------------

    def analyze_sensor_data(
        self,
        device_id: str,
        sensor_type: str,
        sensor_value: Dict[str, Any],
    ) -> List[AnomalyEvent]:
        """
        Analiza datos de sensores en busca de anomalías (caídas).

        Args:
            device_id: ID del dispositivo.
            sensor_type: Tipo de sensor.
            sensor_value: Valor del sensor.

        Returns:
            Lista de anomalías detectadas.
        """
        anomalias: List[AnomalyEvent] = []

        if sensor_type == "acelerometro":
            ax = sensor_value.get("x", 0)
            ay = sensor_value.get("y", 0)
            az = sensor_value.get("z", 0)

            # Actualizar actividad si hay movimiento
            mag = (ax ** 2 + ay ** 2 + az ** 2) ** 0.5
            if mag > 0.5:  # más de 0.5g = movimiento
                self.update_activity(device_id)

            # Detectar caída
            fall = self.detect_fall(
                device_id, ax, ay, az, timestamp=time.time()
            )
            if fall:
                anomalias.append(fall)

        return anomalias

    # ------------------------------------------------------------------
    # VERIFICACIÓN DE INACTIVIDAD
    # ------------------------------------------------------------------

    def check_all_inactivity(self) -> List[AnomalyEvent]:
        """
        Verifica inactividad para todos los dispositivos conocidos.

        Returns:
            Lista de anomalías de inactividad.
        """
        now = time.time()
        anomalias = []
        for device_id in list(self._last_activity.keys()):
            anomaly = self.check_inactivity(device_id, now)
            if anomaly:
                anomalias.append(anomaly)
        return anomalias

    # ------------------------------------------------------------------
    # ESTADO Y ESTADÍSTICAS
    # ------------------------------------------------------------------

    def get_recent_anomalies(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las anomalías más recientes.

        Args:
            limit: Número máximo de anomalías.

        Returns:
            Lista de eventos de anomalía.
        """
        return [
            a.to_dict()
            for a in list(self._anomaly_history)[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del motor de anomalías.

        Returns:
            Dict con estadísticas.
        """
        stats: Dict[str, Any] = {
            "total_anomalies": len(self._anomaly_history),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "active_devices": len(self._last_activity),
            "buffers": {
                "hr": sum(len(b) for b in self._hr_buffer.values()),
                "bp": sum(len(b) for b in self._bp_buffer.values()),
                "spo2": sum(
                    len(b) for b in self._spo2_buffer.values()
                ),
                "stress": sum(
                    len(b) for b in self._stress_buffer.values()
                ),
                "temp": sum(
                    len(b) for b in self._temp_buffer.values()
                ),
                "accel": sum(
                    len(b) for b in self._accel_buffer.values()
                ),
            },
        }

        for anomaly in self._anomaly_history:
            stats["by_type"][anomaly.anomaly_type] += 1
            stats["by_severity"][anomaly.severity] += 1

        return dict(stats)
