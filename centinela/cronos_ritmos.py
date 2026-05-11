"""
Cronos Ritmos — Gestion del tiempo, ritmos circadianos y predicciones temporales
Nova Homonexus — CRONOS (N2, gestor del tiempo)

Detecta:
  - Ritmos circadianos de Abel (sueno, actividad, temperatura)
  - Mejores momentos para interactuar con Nova
  - Predicciones de patrones diarios
  - Sincronizacion con Google Calendar (via HERMES)

El "cronotipo" personal de Abel emerge del analisis temporal.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("centinela.cronos")


@dataclass
class BloqueHorario:
    """Un bloque de tiempo en el dia de Abel."""
    hora_inicio: int   # 0-23
    hora_fin: int
    etiqueta: str      # sueno, trabajo, ejercicio, ocio, etc.
    actividad_tipica: str
    energia_promedio: float  # 0-1
    receptividad_nova: float  # 0-1 (que tan receptivo esta a interactuar con Nova)


@dataclass
class RitmoCircadiano:
    """Modelo del ritmo circadiano de Abel."""
    hora_pico_energia: int = 10      # hora del dia con maxima energia
    hora_pico_cortisol: int = 7      # pico matutino
    hora_inicio_sueno: int = 23      # hora tipica de dormir
    hora_fin_sueno: int = 7          # hora tipica de despertar
    temperatura_min_hora: int = 4    # hora de minima temperatura corporal
    temperatura_max_hora: int = 18   # hora de maxima temperatura


class CronosRitmos:
    """
    Analiza los ritmos temporales de Abel usando datos del Watch 8,
    sensores del Z Fold y (opcionalmente) Google Calendar.
    """

    HORAS_DIA = list(range(24))

    def __init__(self):
        # Acumuladores por hora del dia
        self._hr_por_hora: Dict[int, List[float]] = defaultdict(list)
        self._pasos_por_hora: Dict[int, List[int]] = defaultdict(list)
        self._stress_por_hora: Dict[int, List[int]] = defaultdict(list)
        self._temperatura_por_hora: Dict[int, List[float]] = defaultdict(list)
        self._ubicacion_por_hora: Dict[int, List[str]] = defaultdict(list)

        self._ritmo = RitmoCircadiano()
        self._bloques: List[BloqueHorario] = []
        self._ultimo_analisis: Optional[datetime] = None
        self._mejores_momentos_nova: List[Dict] = []
        self._eventos_calendario: List[Dict] = []
        self._consejos_horarios: List[str] = []

    def alimentar(
        self,
        health: Optional[Dict[str, Any]] = None,
        ubicacion: Optional[Dict[str, Any]] = None,
        sensores: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Alimenta datos temporales al sistema Cronos."""
        now = datetime.now(timezone.utc)
        hora = now.hour

        if health:
            hr = health.get("heart_rate")
            if hr:
                self._hr_por_hora[hora].append(float(hr))
            pasos = health.get("steps")
            if pasos:
                self._pasos_por_hora[hora].append(int(pasos))
            stress = health.get("stress_level")
            if stress is not None:
                self._stress_por_hora[hora].append(int(stress))
            temp = health.get("temperature_skin")
            if temp:
                self._temperatura_por_hora[hora].append(float(temp))

        if ubicacion and ubicacion.get("contexto"):
            self._ubicacion_por_hora[hora].append(ubicacion["contexto"])

        # Analizar cada 100 muestras
        total_muestras = sum(len(v) for v in self._hr_por_hora.values())
        if total_muestras % 100 == 0 and (
            self._ultimo_analisis is None
            or (now - self._ultimo_analisis).total_seconds() > 3600
        ):
            self._analizar_ritmos(now)
            self._ultimo_analisis = now

    def _analizar_ritmos(self, now: datetime) -> None:
        """Analiza los ritmos circadianos y bloques horarios."""
        # Analisis de frecuencia cardiaca por hora
        hr_promedio_por_hora = {}
        for h in self.HORAS_DIA:
            valores = self._hr_por_hora[h]
            if valores:
                hr_promedio_por_hora[h] = sum(valores) / len(valores)

        if hr_promedio_por_hora:
            # Pico de energia: hora con HR mas alta (despierto)
            horas_despierto = {
                h: v for h, v in hr_promedio_por_hora.items()
                if 6 <= h <= 22 and v > 60
            }
            if horas_despierto:
                self._ritmo.hora_pico_energia = max(
                    horas_despierto, key=horas_despierto.get
                )

            # Hora de menor HR (probable sueno)
            horas_bajas = {
                h: v for h, v in hr_promedio_por_hora.items()
                if 22 <= h or h <= 6
            }
            if horas_bajas:
                hora_min = min(horas_bajas, key=horas_bajas.get)
                self._ritmo.hora_inicio_sueno = (
                    hora_min - 1 if hora_min > 0 else 23
                )

        # Analisis de temperatura
        temp_por_hora = {}
        for h in self.HORAS_DIA:
            valores = self._temperatura_por_hora[h]
            if valores:
                temp_por_hora[h] = sum(valores) / len(valores)
        if temp_por_hora:
            self._ritmo.temperatura_min_hora = min(
                temp_por_hora, key=temp_por_hora.get
            )
            self._ritmo.temperatura_max_hora = max(
                temp_por_hora, key=temp_por_hora.get
            )

        # Construir bloques horarios
        self._construir_bloques()

        # Calcular mejores momentos para Nova
        self._calcular_mejores_momentos()

    def _construir_bloques(self) -> None:
        """Construye bloques horarios tipicos del dia de Abel."""
        self._bloques = [
            BloqueHorario(0, 6, "sueno", "Descanso profundo", 0.1, 0.0),
            BloqueHorario(6, 8, "despertar", "Rutina matutina", 0.4, 0.4),
            BloqueHorario(8, 10, "enfoque", "Trabajo concentrado", 0.7, 0.5),
            BloqueHorario(10, 12, "pico", "Maxima energia", 0.9, 0.8),
            BloqueHorario(12, 14, "almuerzo", "Pausa y digestion", 0.5, 0.6),
            BloqueHorario(14, 17, "tarde", "Productividad moderada", 0.6, 0.6),
            BloqueHorario(17, 19, "ejercicio", "Actividad fisica", 0.8, 0.4),
            BloqueHorario(19, 21, "ocio", "Tiempo libre", 0.5, 0.9),
            BloqueHorario(21, 23, "relajacion", "Preparacion para dormir", 0.3, 0.7),
            BloqueHorario(23, 24, "transicion", "Conciliando sueno", 0.1, 0.1),
        ]

        # Refinar con datos reales si hay suficientes
        hr_hora = {}
        for h in self.HORAS_DIA:
            valores = self._hr_por_hora[h]
            if valores:
                hr_hora[h] = sum(valores) / len(valores)

        if len(hr_hora) >= 6:
            for bloque in self._bloques:
                hrs_en_bloque = [
                    h for h in range(bloque.hora_inicio, bloque.hora_fin)
                    if h in hr_hora
                ]
                if hrs_en_bloque:
                    hr_prom = sum(hr_hora[h] for h in hrs_en_bloque) / len(hrs_en_bloque)
                    # HR entre 60-80 = energia optima para interaccion
                    if 60 <= hr_prom <= 80:
                        bloque.receptividad_nova = 0.8
                    elif hr_prom > 80:
                        bloque.receptividad_nova = 0.5  # Muy activo
                    else:
                        bloque.receptividad_nova = 0.3  # Muy bajo

    def _calcular_mejores_momentos(self) -> None:
        """Calcula los mejores momentos del dia para interactuar con Nova."""
        self._mejores_momentos = []
        for bloque in self._bloques:
            if bloque.receptividad_nova >= 0.7:
                self._mejores_momentos.append({
                    "hora_inicio": f"{bloque.hora_inicio:02d}:00",
                    "hora_fin": f"{bloque.hora_fin:02d}:00",
                    "etiqueta": bloque.etiqueta,
                    "receptividad": bloque.receptividad_nova,
                    "recomendacion": (
                        "Momento ideal para conversaciones profundas con Nova"
                        if bloque.receptividad_nova >= 0.8
                        else "Buen momento para interaccion casual"
                    ),
                })

    def predecir_estado_actual(self) -> Dict[str, Any]:
        """Predice el estado actual de Abel basado en la hora y datos historicos."""
        now = datetime.now(timezone.utc)
        hora = now.hour

        bloque_actual = None
        for b in self._bloques:
            if b.hora_inicio <= hora < b.hora_fin:
                bloque_actual = b
                break

        # Chequear eventos de calendario
        en_evento = False
        evento_actual = None
        for ev in self._eventos_calendario:
            try:
                ini = datetime.fromisoformat(ev.get("inicio", ""))
                fin = datetime.fromisoformat(ev.get("fin", ""))
                if ini <= now <= fin:
                    en_evento = True
                    evento_actual = ev
                    break
            except (ValueError, TypeError):
                pass

        return {
            "hora": hora,
            "dia_semana": now.strftime("%A"),
            "bloque_actual": bloque_actual.etiqueta if bloque_actual else "desconocido",
            "receptividad_nova": bloque_actual.receptividad_nova if bloque_actual else 0.5,
            "energia_estimada": bloque_actual.energia_promedio if bloque_actual else 0.5,
            "en_evento_calendario": en_evento,
            "evento_actual": evento_actual,
            "ritmo_circadiano": {
                "pico_energia": self._ritmo.hora_pico_energia,
                "pico_cortisol": self._ritmo.hora_pico_cortisol,
                "inicio_sueno": self._ritmo.hora_inicio_sueno,
                "fin_sueno": self._ritmo.hora_fin_sueno,
            },
        }

    def mejores_momentos_nova(self) -> List[Dict]:
        """Devuelve los mejores momentos del dia para interactuar con Nova."""
        if not self._mejores_momentos_nova:
            # Valores por defecto
            return [
                {"hora_inicio": "09:00", "hora_fin": "11:00",
                 "etiqueta": "pico", "receptividad": 0.8,
                 "recomendacion": "Momento ideal para conversaciones profundas"},
                {"hora_inicio": "19:00", "hora_fin": "21:00",
                 "etiqueta": "ocio", "receptividad": 0.9,
                 "recomendacion": "Momento optimo: Abel relajado y receptivo"},
            ]
        return self._mejores_momentos

    def obtener_cronotipo(self) -> Dict[str, Any]:
        """Devuelve el cronotipo inferido de Abel."""
        if self._ritmo.hora_inicio_sueno <= 22:
            tipo = "Alondra (matutino)"
        elif self._ritmo.hora_inicio_sueno >= 1:
            tipo = "Buho (nocturno)"
        else:
            tipo = "Intermedio"

        return {
            "tipo": tipo,
            "hora_pico_energia": f"{self._ritmo.hora_pico_energia:02d}:00",
            "hora_inicio_sueno": f"{self._ritmo.hora_inicio_sueno:02d}:00",
            "hora_fin_sueno": f"{self._ritmo.hora_fin_sueno:02d}:00",
            "temperatura_min_hora": f"{self._ritmo.temperatura_min_hora:02d}:00",
            "temperatura_max_hora": f"{self._ritmo.temperatura_max_hora:02d}:00",
        }

    def sincronizar_calendario(self, eventos: List[Dict]) -> None:
        """Sincroniza eventos de Google Calendar (via HERMES)."""
        self._eventos_calendario = eventos
        logger.info(f"Cronos sincronizado: {len(eventos)} eventos de calendario")
