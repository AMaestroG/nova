"""
AccesoSalud — Capa compartida de acceso a las constantes vitales de Abel.
=========================================================================
TODOS los agentes del enjambre (AURA, MAESTRO, PIA, PINCEL, ATHENA,
NYX, SENTINEL, MAYORDOMO, BANCO, ORÁCULO, TELAR, EXPLORADOR, MEMORIA,
CRONOS, HERMES, MNEMOS) pueden importar y usar este módulo para leer
las constantes de salud de Abel en tiempo real.

No es un agente más — es EL puente de salud para TODO el enjambre.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass, field

from centinela.config import DB_URL, ALERT_THRESHOLDS

logger = logging.getLogger("centinela.salud.acceso")


@dataclass
class ConstantesVitales:
    """Las constantes vitales actuales de Abel."""
    heart_rate: Optional[float] = None
    hrv: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    spo2: Optional[float] = None
    blood_pressure_sys: Optional[int] = None
    blood_pressure_dia: Optional[int] = None
    temperature_skin: Optional[float] = None
    temperature_core: Optional[float] = None
    stress_level: Optional[int] = None
    sleep_stage: Optional[str] = None
    sleep_quality: Optional[int] = None
    steps: Optional[int] = None
    calories: Optional[float] = None
    bia_body_fat: Optional[float] = None
    bia_muscle_mass: Optional[float] = None
    bia_body_water: Optional[float] = None
    bia_bone_mass: Optional[float] = None
    bia_bmr: Optional[int] = None
    battery_level: Optional[int] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @property
    def estado_cardiaco(self) -> str:
        hr = self.heart_rate
        if hr is None:
            return "sin_datos"
        if hr < 40:
            return "bradicardia_critica"
        if hr < 50:
            return "bradicardia"
        if hr > 180:
            return "taquicardia_critica"
        if hr > 100:
            return "taquicardia"
        if 60 <= hr <= 85:
            return "normal_optimo"
        return "normal"

    @property
    def estado_estres(self) -> str:
        s = self.stress_level
        if s is None:
            return "sin_datos"
        if s > 80:
            return "estres_alto"
        if s > 50:
            return "estres_moderado"
        if s > 25:
            return "estres_bajo"
        return "relajado"

    @property
    def estado_sueno(self) -> str:
        q = self.sleep_quality
        if q is None:
            return "sin_datos"
        if q > 80:
            return "excelente"
        if q > 60:
            return "bueno"
        if q > 40:
            return "regular"
        return "pobre"


class AccesoSalud:
    """
    Acceso universal a las constantes de salud de Abel.
    Cualquier agente del enjambre puede instanciar esta clase y consultar.

    Uso:
        salud = AccesoSalud()
        constantes = salud.ahora()           # ConstantesVitales actuales
        hr = salud.ultima_pulsacion()        # float: última HR
        historial = salud.historial(horas=24) # últimas 24h
        tendencias = salud.tendencias()       # tendencias (subiendo/bajando)
        alertas = salud.verificar_alertas()   # ¿hay algo que alertar?
    """

    def __init__(self, db_session=None):
        self._db_session = db_session
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Optional[datetime] = None
        self._cache_ttl: float = 5.0  # segundos

    def ahora(self, forzar: bool = False) -> ConstantesVitales:
        """Devuelve las constantes vitales más recientes de Abel."""
        if not forzar and self._cache_valido():
            return self._cache.get("constantes")

        row = self._query_ultimo_health()
        if row:
            c = ConstantesVitales(
                heart_rate=row.get("heart_rate"),
                hrv=row.get("hrv"),
                hrv_sdnn=row.get("hrv_sdnn"),
                hrv_rmssd=row.get("hrv_rmssd"),
                spo2=row.get("spo2"),
                blood_pressure_sys=row.get("blood_pressure_sys"),
                blood_pressure_dia=row.get("blood_pressure_dia"),
                temperature_skin=row.get("temperature_skin"),
                temperature_core=row.get("temperature_core"),
                stress_level=row.get("stress_level"),
                sleep_stage=row.get("sleep_stage"),
                sleep_quality=row.get("sleep_quality"),
                steps=row.get("steps"),
                calories=row.get("calories"),
                bia_body_fat=row.get("bia_body_fat"),
                bia_muscle_mass=row.get("bia_muscle_mass"),
                bia_body_water=row.get("bia_body_water"),
                bia_bone_mass=row.get("bia_bone_mass"),
                bia_bmr=row.get("bia_bmr"),
                battery_level=row.get("battery_level"),
                timestamp=row.get("timestamp"),
            )
        else:
            c = ConstantesVitales()

        self._cache["constantes"] = c
        self._cache_ts = datetime.now(timezone.utc)
        return c

    def ultima_pulsacion(self) -> Optional[float]:
        """Última pulsación cardíaca (bpm)."""
        c = self.ahora()
        return c.heart_rate

    def ultima_hrv(self) -> Optional[float]:
        """Última variabilidad cardíaca (ms)."""
        c = self.ahora()
        return c.hrv

    def ultimo_stress(self) -> Optional[int]:
        """Último nivel de estrés (0-100)."""
        c = self.ahora()
        return c.stress_level

    def ultima_spo2(self) -> Optional[float]:
        """Última saturación de oxígeno (%)."""
        c = self.ahora()
        return c.spo2

    def historial(self, horas: int = 24, limite: int = 500) -> List[Dict]:
        """Historial de constantes de las últimas N horas."""
        return self._query_historial_health(horas, limite)

    def tendencias(self, ventana_horas: int = 6) -> Dict[str, Any]:
        """
        Calcula tendencias de las constantes en la última ventana.
        Retorna: {constante: {direccion, cambio_pct, alerta}}
        """
        datos = self.historial(horas=ventana_horas)
        if len(datos) < 5:
            return {"error": "Datos insuficientes para calcular tendencias"}

        tendencias = {}
        metricas = ["heart_rate", "hrv", "spo2", "stress_level",
                     "temperature_skin", "steps"]

        for metrica in metricas:
            valores = [d.get(metrica) for d in datos
                       if d.get(metrica) is not None]
            if len(valores) < 5:
                continue

            # Dividir en dos mitades para ver tendencia
            mitad = len(valores) // 2
            reciente = valores[:mitad]
            anterior = valores[mitad:]

            media_reciente = sum(reciente) / len(reciente)
            media_anterior = sum(anterior) / len(anterior)

            if media_anterior == 0:
                cambio_pct = 0
            else:
                cambio_pct = ((media_reciente - media_anterior)
                              / abs(media_anterior)) * 100

            direccion = "estable"
            if cambio_pct > 3:
                direccion = "subiendo"
            elif cambio_pct < -3:
                direccion = "bajando"

            alerta = None
            if metrica == "heart_rate":
                if media_reciente > 100 and direccion == "subiendo":
                    alerta = "Posible taquicardia progresiva"
                elif media_reciente < 45 and direccion == "bajando":
                    alerta = "Posible bradicardia progresiva"
            elif metrica == "spo2" and media_reciente < 93:
                alerta = "SpO2 bajando — posible hipoxemia"
            elif metrica == "stress_level" and media_reciente > 70:
                alerta = "Estrés elevado sostenido"

            tendencias[metrica] = {
                "actual": round(media_reciente, 1),
                "anterior": round(media_anterior, 1),
                "direccion": direccion,
                "cambio_pct": round(cambio_pct, 1),
                "alerta": alerta,
            }

        return tendencias

    def verificar_alertas(self) -> List[Dict[str, Any]]:
        """Verifica las constantes actuales contra umbrales de alerta."""
        c = self.ahora()
        alertas = []
        umbrales = ALERT_THRESHOLDS

        if c.heart_rate:
            if c.heart_rate < umbrales["heart_rate_min"]:
                alertas.append({
                    "tipo": "bradicardia",
                    "severidad": "warning",
                    "valor": c.heart_rate,
                    "umbral": umbrales["heart_rate_min"],
                    "mensaje": f"Pulsaciones bajas: {c.heart_rate} bpm",
                })
            elif c.heart_rate > umbrales["heart_rate_max"]:
                alertas.append({
                    "tipo": "taquicardia",
                    "severidad": "warning",
                    "valor": c.heart_rate,
                    "umbral": umbrales["heart_rate_max"],
                    "mensaje": f"Pulsaciones altas: {c.heart_rate} bpm",
                })

        if c.spo2:
            if c.spo2 < umbrales["spo2_min"]:
                alertas.append({
                    "tipo": "hipoxemia",
                    "severidad": "error" if c.spo2 < umbrales["spo2_critical_min"] else "warning",
                    "valor": c.spo2,
                    "umbral": umbrales["spo2_min"],
                    "mensaje": f"SpO2 baja: {c.spo2}%",
                })

        if c.stress_level:
            if c.stress_level > umbrales["stress_level_max"]:
                alertas.append({
                    "tipo": "estres",
                    "severidad": "error" if c.stress_level > umbrales["stress_level_critical"] else "warning",
                    "valor": c.stress_level,
                    "umbral": umbrales["stress_level_max"],
                    "mensaje": f"Estrés elevado: {c.stress_level}/100",
                })

        if c.temperature_skin:
            if c.temperature_skin < umbrales["temperature_min"]:
                alertas.append({
                    "tipo": "hipotermia",
                    "severidad": "error",
                    "valor": c.temperature_skin,
                    "umbral": umbrales["temperature_min"],
                    "mensaje": f"Temperatura baja: {c.temperature_skin}°C",
                })
            elif c.temperature_skin > umbrales["temperature_max"]:
                alertas.append({
                    "tipo": "fiebre",
                    "severidad": "warning",
                    "valor": c.temperature_skin,
                    "umbral": umbrales["temperature_max"],
                    "mensaje": f"Temperatura elevada: {c.temperature_skin}°C",
                })

        return alertas

    def resumen_salud(self) -> Dict[str, Any]:
        """Resumen completo del estado de salud de Abel para cualquier agente."""
        c = self.ahora()
        alertas = self.verificar_alertas()

        return {
            "constantes": c.to_dict(),
            "estado_cardiaco": c.estado_cardiaco,
            "estado_estres": c.estado_estres,
            "estado_sueno": c.estado_sueno,
            "alertas": alertas,
            "total_alertas": len(alertas),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # INTERNO: queries SQL
    # ------------------------------------------------------------------

    def _cache_valido(self) -> bool:
        if not self._cache_ts:
            return False
        return (datetime.now(timezone.utc) - self._cache_ts).total_seconds() < self._cache_ttl

    def _get_session(self):
        if self._db_session:
            return self._db_session
        # Crear sesión fresh
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            engine = create_engine(DB_URL, pool_pre_ping=True)
            Session = sessionmaker(bind=engine)
            return Session()
        except Exception:
            return None

    def _query_ultimo_health(self) -> Optional[Dict]:
        s = self._get_session()
        if not s:
            return None
        try:
            from sqlalchemy import text
            row = s.execute(text(
                "SELECT * FROM centinela_health ORDER BY timestamp DESC LIMIT 1"
            )).fetchone()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.debug(f"Error query health: {e}")
            return None
        finally:
            if not self._db_session:
                s.close()

    def _query_historial_health(self, horas: int, limite: int) -> List[Dict]:
        s = self._get_session()
        if not s:
            return []
        try:
            from sqlalchemy import text
            rows = s.execute(text(
                "SELECT * FROM centinela_health "
                "WHERE timestamp > NOW() - INTERVAL '1 hour' * :horas "
                "ORDER BY timestamp DESC LIMIT :limite"
            ), {"horas": horas, "limite": limite}).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception:
            return []
        finally:
            if not self._db_session:
                s.close()


# Instancia global compartida — TODOS los agentes pueden usar esta
_salud_global: Optional[AccesoSalud] = None


def obtener_salud() -> AccesoSalud:
    """Obtiene la instancia global de AccesoSalud (singleton)."""
    global _salud_global
    if _salud_global is None:
        _salud_global = AccesoSalud()
    return _salud_global
