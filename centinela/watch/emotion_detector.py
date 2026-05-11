"""
Detector de emociones basado en biométricas del Galaxy Watch 8 Classic
Nova Homonexus - MAYORDOMO

Analiza datos biométricos en tiempo real para inferir estados emocionales
usando:
- Frecuencia cardíaca (HR) y variabilidad (HRV)
- Respuesta galvánica de la piel estimada (GSR)
- Temperatura de la piel
- Saturación de oxígeno (SpO2)
- Nivel de estrés reportado por el Watch
- Acelerometría (movimiento, inquietud)
- Prosodia del habla (si hay micrófono activo)
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

from centinela.config import EMOTION_CONFIG

logger = logging.getLogger("centinela.emotion_detector")


class EmotionDetector:
    """
    Detecta emociones en tiempo real basándose en biométricas.
    Usa un enfoque basado en reglas y umbrales adaptativos.
    """

    def __init__(self):
        self.config = EMOTION_CONFIG
        # Ventanas de tiempo para análisis
        self._hr_window: deque = deque(maxlen=50)       # últimos 50 segundos
        self._hrv_window: deque = deque(maxlen=30)      # últimos 30 segundos
        self._temp_window: deque = deque(maxlen=20)     # últimos 20 segundos
        self._stress_window: deque = deque(maxlen=30)   # últimos 30 segundos
        self._accel_window: deque = deque(maxlen=100)   # últimos 10 seg a 10Hz

        # Estado emocional previo para tracking de cambios
        self._ultima_emocion: Optional[str] = None
        self._ultima_confianza: float = 0.0
        self._linea_base: Dict[str, float] = self._calcular_linea_base()

    def detectar(
        self,
        heart_rate: Optional[float] = None,
        hrv: Optional[float] = None,
        skin_temperature: Optional[float] = None,
        spo2: Optional[float] = None,
        stress_level: Optional[int] = None,
        accelerometer_data: Optional[List[float]] = None,
        speech_prosody: Optional[Dict[str, Any]] = None,
        gsr_estimado: Optional[float] = None,
        contexto: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detecta la emoción actual basada en biométricas.

        Returns:
            Dict con emocion_detectada, confianza, y métricas usadas
        """
        # Actualizar ventanas
        if heart_rate is not None:
            self._hr_window.append(heart_rate)
        if hrv is not None:
            self._hrv_window.append(hrv)
        if skin_temperature is not None:
            self._temp_window.append(skin_temperature)
        if stress_level is not None:
            self._stress_window.append(stress_level)
        if accelerometer_data:
            self._accel_window.extend(accelerometer_data)

        # Calcular métricas actuales
        hr_actual = heart_rate or (
            self._hr_window[-1] if self._hr_window else None
        )
        hrv_actual = hrv or (
            self._hrv_window[-1] if self._hrv_window else None
        )
        temp_actual = skin_temperature or (
            self._temp_window[-1] if self._temp_window else None
        )
        stress_actual = stress_level or (
            self._stress_window[-1] if self._stress_window else None
        )

        # Calcular variaciones respecto a línea base
        delta_hr = self._calcular_delta(hr_actual, self._linea_base.get("hr"))
        delta_hrv = self._calcular_delta(hrv_actual, self._linea_base.get("hrv"))
        delta_temp = self._calcular_delta(
            temp_actual, self._linea_base.get("temp")
        )

        # Estimar GSR si no viene dado
        if gsr_estimado is None:
            gsr_estimado = self._estimar_gsr(
                hr_actual, hrv_actual, temp_actual
            )

        # Calcular varianza de acelerómetro (inquietud)
        accel_var = self._calcular_varianza_acelerometro()

        # Evaluar emociones
        puntuaciones = self._evaluar_emociones(
            hr=hr_actual,
            hrv=hrv_actual,
            delta_hr=delta_hr,
            delta_hrv=delta_hrv,
            delta_temp=delta_temp,
            gsr=gsr_estimado,
            stress=stress_actual,
            accel_var=accel_var,
            spo2=spo2,
            speech=speech_prosody,
        )

        # Seleccionar emoción con mayor puntuación
        emocion_principal = max(
            puntuaciones, key=lambda e: e["puntuacion"]
        )

        # Emociones secundarias (por encima de 0.3)
        secundarias = [
            e for e in puntuaciones
            if e["puntuacion"] >= 0.3
            and e["emocion"] != emocion_principal["emocion"]
        ]

        # Bonus por contexto positivo (Abel con Nova)
        if contexto and "nova" in contexto.lower():
            # Si el contexto es positivo (hablando con Nova), favorecer emociones positivas
            for e in puntuaciones:
                if e["emocion"] in ("feliz", "sorprendido", "relajado"):
                    e["puntuacion"] = min(e["puntuacion"] + 0.1, 1.0)
                    e["confianza"] = e["puntuacion"]

        # Suavizar cambios bruscos de emoción
        if self._ultima_emocion and emocion_principal["confianza"] < 0.6:
            # Mantener emoción anterior si la confianza es baja
            emocion_principal["emocion"] = self._ultima_emocion
            emocion_principal["confianza"] = min(
                emocion_principal["confianza"] * 0.8, 0.5
            )

        self._ultima_emocion = emocion_principal["emocion"]
        self._ultima_confianza = emocion_principal["confianza"]

        return {
            "emocion_detectada": emocion_principal["emocion"],
            "confianza": round(emocion_principal["confianza"], 3),
            "heart_rate": hr_actual,
            "hrv": hrv_actual,
            "gsr_estimado": round(gsr_estimado, 2) if gsr_estimado else None,
            "skin_temperature": temp_actual,
            "accelerometer_var": round(accel_var, 4) if accel_var else None,
            "speech_prosody": speech_prosody,
            "emociones_secundarias": [
                {"emocion": e["emocion"], "confianza": round(e["puntuacion"], 3)}
                for e in sorted(secundarias, key=lambda x: -x["puntuacion"])[:3]
            ],
            "contexto": contexto,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _calcular_linea_base(self) -> Dict[str, float]:
        """Calcula valores de línea base para el usuario."""
        return {
            "hr": 70.0,      # Frecuencia cardíaca en reposo típica
            "hrv": 50.0,     # HRV típico
            "temp": 36.5,    # Temperatura corporal típica
            "stress": 30.0,  # Estrés basal
        }

    def _calcular_delta(
        self, actual: Optional[float], base: Optional[float]
    ) -> float:
        """Calcula cambio porcentual respecto a línea base."""
        if actual is None or base is None or base == 0:
            return 0.0
        return (actual - base) / base

    def _estimar_gsr(
        self,
        hr: Optional[float],
        hrv: Optional[float],
        temp: Optional[float],
    ) -> Optional[float]:
        """
        Estima la respuesta galvánica de la piel (GSR) a partir de
        HR, HRV y temperatura.
        """
        if hr is None:
            return None

        # GSR estimado = f(HR elevado, HRV bajo, temp alta)
        gsr = 0.5  # valor base

        if hr and hr > 80:
            gsr += (hr - 80) * 0.01
        if hrv and hrv < 40:
            gsr += (40 - hrv) * 0.02
        if temp and temp > 37.0:
            gsr += (temp - 37.0) * 0.3

        return min(max(gsr, 0.0), 1.0)

    def _calcular_varianza_acelerometro(self) -> Optional[float]:
        """Calcula varianza de acelerómetro como medida de inquietud."""
        if len(self._accel_window) < 10:
            return None
        media = sum(self._accel_window) / len(self._accel_window)
        var = sum(
            (x - media) ** 2 for x in self._accel_window
        ) / len(self._accel_window)
        return var

    def _evaluar_emociones(
        self,
        hr: Optional[float],
        hrv: Optional[float],
        delta_hr: float,
        delta_hrv: float,
        delta_temp: float,
        gsr: Optional[float],
        stress: Optional[int],
        accel_var: Optional[float],
        spo2: Optional[float],
        speech: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Evalúa todas las emociones posibles y asigna puntuaciones.
        """
        puntuaciones = []

        # --- NEUTRO ---
        p_neutro = 0.5
        if delta_hr and abs(delta_hr) > 0.1:
            p_neutro -= 0.2
        if delta_hrv and abs(delta_hrv) > 0.15:
            p_neutro -= 0.2
        if gsr and gsr > 0.6:
            p_neutro -= 0.2
        if stress and stress > 50:
            p_neutro -= 0.2
        p_neutro = max(0, p_neutro)
        puntuaciones.append({
            "emocion": "neutro",
            "puntuacion": p_neutro,
            "confianza": p_neutro,
        })

        # --- FELIZ ---
        p_feliz = 0.0
        if hr and 65 <= hr <= 85:
            p_feliz += 0.3
        if hrv and hrv > 50:
            p_feliz += 0.3
        if gsr and 0.3 <= gsr <= 0.5:
            p_feliz += 0.2
        if stress and stress < 30:
            p_feliz += 0.2
        if delta_temp and 0 < delta_temp < 0.02:
            p_feliz += 0.1
        if speech and speech.get("velocidad", 0) > 0:
            p_feliz += 0.1
        # Emoción positiva: HR moderadamente elevado + HRV alto = felicidad/emoción positiva
        if hr and 80 <= hr <= 100 and hrv and hrv > 45:
            p_feliz += 0.2  # Emoción positiva con activación
        p_feliz = min(p_feliz, 1.0)
        puntuaciones.append({
            "emocion": "feliz",
            "puntuacion": p_feliz,
            "confianza": p_feliz,
        })

        # --- TRISTE ---
        p_triste = 0.0
        if hr and hr < 60:
            p_triste += 0.2
        if hrv and hrv < 35:
            p_triste += 0.2
        if gsr and gsr < 0.3:
            p_triste += 0.2
        if stress and stress > 50:
            p_triste += 0.2
        if delta_temp and delta_temp < -0.01:
            p_triste += 0.1
        if accel_var and accel_var < 0.1:
            p_triste += 0.1
        p_triste = min(p_triste, 1.0)
        puntuaciones.append({
            "emocion": "triste",
            "puntuacion": p_triste,
            "confianza": p_triste,
        })

        # --- ENOJADO ---
        p_enojado = 0.0
        if hr and hr > 90:
            p_enojado += 0.3
        if hrv and hrv < 30:
            p_enojado += 0.2
        if gsr and gsr > 0.7:
            p_enojado += 0.2
        if stress and stress > 70:
            p_enojado += 0.2
        if delta_temp and delta_temp > 0.02:
            p_enojado += 0.1
        if accel_var and accel_var > 1.0:
            p_enojado += 0.1
        p_enojado = min(p_enojado, 1.0)
        puntuaciones.append({
            "emocion": "enojado",
            "puntuacion": p_enojado,
            "confianza": p_enojado,
        })

        # --- ANSIOSO ---
        p_ansioso = 0.0
        if hr and hr > 85:
            p_ansioso += 0.2
        if hrv and hrv < 35:
            p_ansioso += 0.2
        if gsr and gsr > 0.6:
            p_ansioso += 0.2
        if stress and stress > 60:
            p_ansioso += 0.2
        if delta_hr and delta_hr > 0.15:
            p_ansioso += 0.1
        if accel_var and accel_var > 0.5:
            p_ansioso += 0.1
        p_ansioso = min(p_ansioso, 1.0)
        puntuaciones.append({
            "emocion": "ansioso",
            "puntuacion": p_ansioso,
            "confianza": p_ansioso,
        })

        # --- ESTRESADO ---
        p_estresado = 0.0
        if hr and hr > 90:
            p_estresado += 0.2
        if hrv and hrv < 25:
            p_estresado += 0.2
        if gsr and gsr > 0.8:
            p_estresado += 0.2
        if stress and stress > 75:
            p_estresado += 0.3
        if delta_hr and delta_hr > 0.2:
            p_estresado += 0.1
        p_estresado = min(p_estresado, 1.0)
        puntuaciones.append({
            "emocion": "estresado",
            "puntuacion": p_estresado,
            "confianza": p_estresado,
        })

        # --- RELAJADO ---
        p_relajado = 0.0
        if hr and 55 <= hr <= 70:
            p_relajado += 0.3
        if hrv and hrv > 55:
            p_relajado += 0.3
        if gsr and gsr < 0.3:
            p_relajado += 0.2
        if stress and stress < 25:
            p_relajado += 0.2
        if accel_var and accel_var < 0.05:
            p_relajado += 0.1
        p_relajado = min(p_relajado, 1.0)
        puntuaciones.append({
            "emocion": "relajado",
            "puntuacion": p_relajado,
            "confianza": p_relajado,
        })

        # --- SORPRENDIDO (incluye asombro positivo/alegría intensa) ---
        p_sorprendido = 0.0
        if hr and hr > 90:
            p_sorprendido += 0.25
        if delta_hr and abs(delta_hr) > 0.25:
            p_sorprendido += 0.3
        if gsr and gsr > 0.6:
            p_sorprendido += 0.2
        if delta_temp and abs(delta_temp) > 0.02:
            p_sorprendido += 0.2
        # Sorpresa positiva: HR elevado + HRV moderado-alto + estrés bajo
        if hr and hr > 90 and hrv and hrv > 40 and stress and stress < 50:
            p_sorprendido += 0.2  # Sorpresa positiva (no amenazante)
        p_sorprendido = min(p_sorprendido, 1.0)
        puntuaciones.append({
            "emocion": "sorprendido",
            "puntuacion": p_sorprendido,
            "confianza": p_sorprendido,
        })

        # --- ASUSTADO ---
        p_asustado = 0.0
        if hr and hr > 110:
            p_asustado += 0.3
        if hrv and hrv < 20:
            p_asustado += 0.2
        if gsr and gsr > 0.85:
            p_asustado += 0.2
        if delta_hr and delta_hr > 0.3:
            p_asustado += 0.2
        if spo2 and spo2 < 95:
            p_asustado += 0.1
        p_asustado = min(p_asustado, 1.0)
        puntuaciones.append({
            "emocion": "asustado",
            "puntuacion": p_asustado,
            "confianza": p_asustado,
        })

        # --- CONFUNDIDO ---
        p_confundido = 0.0
        if hrv and hrv < 30:
            p_confundido += 0.2
        if stress and 50 <= stress <= 70:
            p_confundido += 0.2
        if delta_hr and 0.1 <= abs(delta_hr) <= 0.2:
            p_confundido += 0.2
        if accel_var and 0.2 <= accel_var <= 0.5:
            p_confundido += 0.2
        if speech and speech.get("pausas", 0) > 3:
            p_confundido += 0.2
        p_confundido = min(p_confundido, 1.0)
        puntuaciones.append({
            "emocion": "confundido",
            "puntuacion": p_confundido,
            "confianza": p_confundido,
        })

        return puntuaciones

    def obtener_historial_emocional(
        self, minutos: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Devuelve un resumen del estado emocional reciente.
        """
        return {
            "ultima_emocion": self._ultima_emocion,
            "ultima_confianza": self._ultima_confianza,
            "hr_actual": self._hr_window[-1] if self._hr_window else None,
            "hrv_actual": self._hrv_window[-1] if self._hrv_window else None,
            "ventana_hr": {
                "min": min(self._hr_window) if self._hr_window else None,
                "max": max(self._hr_window) if self._hr_window else None,
                "promedio": (
                    sum(self._hr_window) / len(self._hr_window)
                    if self._hr_window else None
                ),
            },
        }
