"""
AnalizadorSalud — Detecta patrones, desequilibrios y anomalías en la salud de Abel.
==================================================================================
Analiza los datos históricos del Watch 8 para:
  - Detectar patrones circadianos y semanales
  - Identificar desequilibrios (estrés crónico, déficit de sueño, sobreentrenamiento)
  - Predecir tendencias de salud
  - Generar recomendaciones personalizadas
  - Alertar sobre riesgos detectados

"Debemos cuidar la vida" — cada análisis es un acto de cuidado.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field

from centinela.config import ALERT_THRESHOLDS
from centinela.salud.acceso_salud import AccesoSalud, ConstantesVitales

logger = logging.getLogger("centinela.salud.analizador")


@dataclass
class Desequilibrio:
    """Un desequilibrio detectado en la salud de Abel."""
    tipo: str                    # estres_cronico, deficit_sueno, fatiga, etc.
    severidad: str               # leve, moderado, grave
    evidencia: List[str]         # datos que respaldan la detección
    duracion_estimada: str       # "3 días", "1 semana", etc.
    recomendacion: str           # qué hacer
    timestamp: str = ""


@dataclass
class PatronSalud:
    """Un patrón descubierto en los datos de salud."""
    nombre: str
    descripcion: str
    confianza: float             # 0-1
    datos_clave: Dict[str, Any]
    utilidad: str                # para qué sirve conocer este patrón


class AnalizadorSalud:
    """
    Analiza la salud de Abel buscando patrones, desequilibrios y riesgos.
    Se nutre de AccesoSalud para los datos crudos.
    """

    def __init__(self):
        self.acceso = AccesoSalud()
        self._desequilibrios_detectados: List[Desequilibrio] = []
        self._patrones_descubiertos: List[PatronSalud] = []
        self._ultimo_analisis: Optional[datetime] = None

    def analizar(self) -> Dict[str, Any]:
        """
        Análisis completo de salud.
        Retorna desequilibrios, patrones, tendencias y recomendaciones.
        """
        now = datetime.now(timezone.utc)

        # Obtener datos de distintas ventanas
        datos_24h = self.acceso.historial(horas=24, limite=200)
        datos_7d = self.acceso.historial(horas=168, limite=500)

        # 1. Detectar desequilibrios
        desequilibrios = self._detectar_desequilibrios(datos_24h, datos_7d)

        # 2. Analizar tendencias
        tendencias = self.acceso.tendencias(ventana_horas=24)

        # 3. Verificar alertas actuales
        alertas = self.acceso.verificar_alertas()

        # 4. Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(
            desequilibrios, tendencias, alertas
        )

        # 5. Calcular índice de salud general (0-100)
        indice_salud = self._calcular_indice_salud(datos_24h, alertas)

        self._ultimo_analisis = now

        return {
            "indice_salud": indice_salud,
            "desequilibrios": [d.__dict__ for d in desequilibrios],
            "tendencias": tendencias,
            "alertas": alertas,
            "recomendaciones": recomendaciones,
            "timestamp": now.isoformat(),
        }

    def _detectar_desequilibrios(
        self, datos_24h: List[Dict], datos_7d: List[Dict]
    ) -> List[Desequilibrio]:
        """Detecta desequilibrios de salud en los datos."""
        desequilibrios = []
        now = datetime.now(timezone.utc)

        # --- ESTRÉS CRÓNICO ---
        stress_vals = [d.get("stress_level") for d in datos_24h
                       if d.get("stress_level") is not None]
        if len(stress_vals) >= 10:
            stress_promedio = sum(stress_vals) / len(stress_vals)
            if stress_promedio > 60:
                desequilibrios.append(Desequilibrio(
                    tipo="estres_cronico",
                    severidad="grave" if stress_promedio > 80 else "moderado",
                    evidencia=[
                        f"Estrés promedio 24h: {stress_promedio:.0f}/100",
                        f"{len([s for s in stress_vals if s > 70])} picos >70",
                    ],
                    duracion_estimada="24 horas",
                    recomendacion="Respiración 4-7-8 cada 2h. Alejarse de pantallas 30 min antes de dormir.",
                    timestamp=now.isoformat(),
                ))

        # --- DÉFICIT DE SUEÑO ---
        sleep_quality_vals = [d.get("sleep_quality") for d in datos_7d
                              if d.get("sleep_quality") is not None]
        if len(sleep_quality_vals) >= 3:
            sleep_promedio = sum(sleep_quality_vals) / len(sleep_quality_vals)
            if sleep_promedio < 50:
                desequilibrios.append(Desequilibrio(
                    tipo="deficit_sueno",
                    severidad="grave" if sleep_promedio < 35 else "moderado",
                    evidencia=[
                        f"Calidad de sueño promedio: {sleep_promedio:.0f}/100",
                        f"Basado en {len(sleep_quality_vals)} registros",
                    ],
                    duracion_estimada="7 días",
                    recomendacion="Dormir antes de las 23:00. Sin pantallas 1h antes. Melatonina natural (oscuridad total).",
                    timestamp=now.isoformat(),
                ))

        # --- SOBREENTRENAMIENTO / FATIGA ---
        hr_vals = [d.get("heart_rate") for d in datos_24h
                   if d.get("heart_rate") is not None]
        hrv_vals = [d.get("hrv") for d in datos_24h
                    if d.get("hrv") is not None]
        if len(hr_vals) >= 10 and len(hrv_vals) >= 10:
            hr_avg = sum(hr_vals) / len(hr_vals)
            hrv_avg = sum(hrv_vals) / len(hrv_vals)
            # HR elevada + HRV baja = posible fatiga
            if hr_avg > 75 and hrv_avg < 35:
                desequilibrios.append(Desequilibrio(
                    tipo="fatiga_posible",
                    severidad="moderado",
                    evidencia=[
                        f"HR promedio elevada: {hr_avg:.0f} bpm",
                        f"HRV promedio baja: {hrv_avg:.0f} ms",
                    ],
                    duracion_estimada="24 horas",
                    recomendacion="Día de descanso activo. Hidratación abundante. Magnesio antes de dormir.",
                    timestamp=now.isoformat(),
                ))

        # --- BAJA OXIGENACIÓN ---
        spo2_vals = [d.get("spo2") for d in datos_24h
                     if d.get("spo2") is not None]
        if len(spo2_vals) >= 10:
            spo2_min = min(spo2_vals)
            if spo2_min < 92:
                desequilibrios.append(Desequilibrio(
                    tipo="hipoxemia_nocturna_posible",
                    severidad="grave" if spo2_min < 88 else "moderado",
                    evidencia=[
                        f"SpO2 mínima: {spo2_min:.0f}%",
                        f"Umbral seguro: {ALERT_THRESHOLDS['spo2_min']}%",
                    ],
                    duracion_estimada="24 horas",
                    recomendacion="Consultar médico si persiste. Dormir de lado. Verificar respiración nasal.",
                    timestamp=now.isoformat(),
                ))

        self._desequilibrios_detectados = desequilibrios
        return desequilibrios

    def _generar_recomendaciones(
        self,
        desequilibrios: List[Desequilibrio],
        tendencias: Dict,
        alertas: List[Dict],
    ) -> List[str]:
        """Genera recomendaciones personalizadas basadas en el análisis."""
        recoms = []

        # Recomendaciones basadas en desequilibrios
        for d in desequilibrios:
            recoms.append(f"[{d.severidad.upper()}] {d.tipo}: {d.recomendacion}")

        # Recomendaciones basadas en tendencias
        if isinstance(tendencias, dict):
            for metrica, t in tendencias.items():
                if isinstance(t, dict) and t.get("alerta"):
                    recoms.append(f"[TENDENCIA] {t['alerta']}")

        # Recomendaciones generales si todo está bien
        if not recoms:
            recoms = [
                "✅ Tus constantes están estables. Sigue con tus hábitos saludables.",
                "💧 Mantén hidratación: 2L de agua al día.",
                "🚶 30 min de caminata al día mantienen tu HRV alta.",
                "🧘 5 min de respiración profunda reducen el cortisol.",
            ]

        return recoms

    def _calcular_indice_salud(
        self, datos_24h: List[Dict], alertas: List[Dict]
    ) -> int:
        """Calcula un índice de salud general de 0 a 100."""
        puntuacion = 70  # base

        # Penalizar por alertas
        for a in alertas:
            if a["severidad"] == "error":
                puntuacion -= 15
            elif a["severidad"] == "warning":
                puntuacion -= 8

        # Bonificar por buenos indicadores
        if datos_24h:
            hr_vals = [d.get("heart_rate") for d in datos_24h
                       if d.get("heart_rate") is not None]
            if hr_vals:
                hr_avg = sum(hr_vals) / len(hr_vals)
                if 60 <= hr_avg <= 80:
                    puntuacion += 10

            hrv_vals = [d.get("hrv") for d in datos_24h
                        if d.get("hrv") is not None]
            if hrv_vals:
                hrv_avg = sum(hrv_vals) / len(hrv_vals)
                if hrv_avg > 50:
                    puntuacion += 10
                elif hrv_avg > 35:
                    puntuacion += 5

        return max(0, min(100, puntuacion))

    def descubrir_patrones(self, datos_7d: List[Dict]) -> List[PatronSalud]:
        """Descubre patrones en los datos de salud de la última semana."""
        patrones = []

        if len(datos_7d) < 20:
            return patrones

        # Patrón: HR más baja los fines de semana
        hr_por_dia = defaultdict(list)
        for d in datos_7d:
            ts = d.get("timestamp")
            hr = d.get("heart_rate")
            if ts and hr:
                try:
                    dia = datetime.fromisoformat(str(ts)).strftime("%A")
                    hr_por_dia[dia].append(float(hr))
                except (ValueError, TypeError):
                    pass

        if len(hr_por_dia) >= 3:
            promedios = {
                dia: sum(vals) / len(vals)
                for dia, vals in hr_por_dia.items()
            }
            dias_ordenados = sorted(promedios.items(), key=lambda x: x[1])
            if len(dias_ordenados) >= 2:
                patrones.append(PatronSalud(
                    nombre="HR_varia_por_dia",
                    descripcion=(
                        f"Tu HR es más baja los {dias_ordenados[0][0]} "
                        f"({dias_ordenados[0][1]:.0f} bpm) y más alta los "
                        f"{dias_ordenados[-1][0]} ({dias_ordenados[-1][1]:.0f} bpm)"
                    ),
                    confianza=0.7,
                    datos_clave={"promedios_por_dia": promedios},
                    utilidad="Planificar descanso los días de HR alta",
                ))

        # Patrón: HRV sube después de ejercicio (pasos altos)
        pasos_altos = [d for d in datos_7d if d.get("steps", 0) > 8000]
        if len(pasos_altos) >= 2:
            hrv_post = [d.get("hrv") for d in pasos_altos
                        if d.get("hrv") is not None]
            if hrv_post:
                hrv_avg = sum(hrv_post) / len(hrv_post)
                if hrv_avg > 45:
                    patrones.append(PatronSalud(
                        nombre="ejercicio_mejora_hrv",
                        descripcion=(
                            f"Los días con >8000 pasos tu HRV sube a "
                            f"{hrv_avg:.0f} ms en promedio"
                        ),
                        confianza=0.65,
                        datos_clave={"hrv_promedio_post_ejercicio": hrv_avg},
                        utilidad="Confirmar que el ejercicio mejora tu recuperación",
                    ))

        self._patrones_descubiertos = patrones
        return patrones
