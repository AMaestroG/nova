"""
MemoriaSalud — Aprendizaje y memoria a largo plazo de las constantes de Abel.
=============================================================================
  - Aprende las líneas base personales de Abel (no usa valores genéricos)
  - Almacena patrones históricos para detectar desviaciones
  - Construye un "perfil de salud" único de Abel
  - Permite comparar "cómo estabas antes vs ahora"
  - Persiste en PostgreSQL para consulta de cualquier agente
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field

from centinela.config import DB_URL, ALERT_THRESHOLDS
from centinela.salud.acceso_salud import AccesoSalud

logger = logging.getLogger("centinela.salud.memoria")


@dataclass
class LineaBasePersonal:
    """Líneas base fisiológicas de Abel (aprendidas, no genéricas)."""
    hr_reposo: float = 70.0
    hr_max_observada: float = 180.0
    hr_min_observada: float = 40.0
    hrv_reposo: float = 50.0
    spo2_basal: float = 97.0
    temp_basal: float = 36.6
    stress_basal: float = 25.0
    sleep_quality_basal: float = 70.0
    pasos_diarios_promedio: float = 8000.0
    muestras_aprendizaje: int = 0
    ultima_actualizacion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "hr_reposo": self.hr_reposo,
            "hrv_reposo": self.hrv_reposo,
            "spo2_basal": self.spo2_basal,
            "temp_basal": self.temp_basal,
            "stress_basal": self.stress_basal,
            "sleep_quality_basal": self.sleep_quality_basal,
            "pasos_diarios_promedio": self.pasos_diarios_promedio,
            "muestras_aprendizaje": self.muestras_aprendizaje,
            "ultima_actualizacion": self.ultima_actualizacion,
        }


class MemoriaSalud:
    """
    Aprende y recuerda las líneas base de salud de Abel.
    Cuanto más datos, más precisas son las líneas base.
    """

    def __init__(self):
        self.acceso = AccesoSalud()
        self.linea_base = LineaBasePersonal()
        self._historico_semanal: deque = deque(maxlen=168)  # 1 semana en horas
        self._aprendido: bool = False

    def aprender_linea_base(self, dias: int = 7) -> LineaBasePersonal:
        """
        Aprende las líneas base de Abel a partir de datos históricos.
        Usa los últimos N días de datos para personalizar los umbrales.
        """
        datos = self.acceso.historial(horas=dias * 24, limite=2000)
        if len(datos) < 20:
            logger.info("Datos insuficientes para aprender línea base")
            return self.linea_base

        # Extraer valores
        hr_vals = [d.get("heart_rate") for d in datos
                   if d.get("heart_rate") is not None]
        hrv_vals = [d.get("hrv") for d in datos
                    if d.get("hrv") is not None]
        spo2_vals = [d.get("spo2") for d in datos
                     if d.get("spo2") is not None]
        temp_vals = [d.get("temperature_skin") for d in datos
                     if d.get("temperature_skin") is not None]
        stress_vals = [d.get("stress_level") for d in datos
                       if d.get("stress_level") is not None]
        sleep_vals = [d.get("sleep_quality") for d in datos
                      if d.get("sleep_quality") is not None]
        pasos_vals = [d.get("steps") for d in datos
                      if d.get("steps") is not None]

        # Calcular líneas base personalizadas
        if hr_vals:
            self.linea_base.hr_reposo = sum(hr_vals) / len(hr_vals)
            self.linea_base.hr_max_observada = max(hr_vals)
            self.linea_base.hr_min_observada = min(hr_vals)

        if hrv_vals:
            self.linea_base.hrv_reposo = sum(hrv_vals) / len(hrv_vals)

        if spo2_vals:
            self.linea_base.spo2_basal = sum(spo2_vals) / len(spo2_vals)

        if temp_vals:
            self.linea_base.temp_basal = sum(temp_vals) / len(temp_vals)

        if stress_vals:
            self.linea_base.stress_basal = sum(stress_vals) / len(stress_vals)

        if sleep_vals:
            self.linea_base.sleep_quality_basal = sum(sleep_vals) / len(sleep_vals)

        if pasos_vals:
            self.linea_base.pasos_diarios_promedio = sum(pasos_vals) / len(pasos_vals)

        self.linea_base.muestras_aprendizaje = len(datos)
        self.linea_base.ultima_actualizacion = datetime.now(timezone.utc).isoformat()
        self._aprendido = True

        logger.info(
            "Línea base aprendida con %d muestras. HR reposo: %.1f bpm, HRV: %.1f ms",
            len(datos), self.linea_base.hr_reposo, self.linea_base.hrv_reposo,
        )
        return self.linea_base

    def comparar_con_linea_base(self) -> Dict[str, Any]:
        """
        Compara las constantes actuales con la línea base personal.
        Detecta desviaciones significativas.
        """
        if not self._aprendido:
            self.aprender_linea_base()

        actual = self.acceso.ahora()
        desviaciones = {}

        checks = [
            ("heart_rate", "hr_reposo", "bpm", 15, "Pulsaciones"),
            ("hrv", "hrv_reposo", "ms", 15, "HRV"),
            ("spo2", "spo2_basal", "%", 3, "SpO2"),
            ("stress_level", "stress_basal", "/100", 20, "Estrés"),
            ("temperature_skin", "temp_basal", "°C", 1.0, "Temperatura"),
        ]

        for attr_actual, attr_base, unidad, umbral_pct, nombre in checks:
            val_actual = getattr(actual, attr_actual)
            val_base = getattr(self.linea_base, attr_base)
            if val_actual is not None and val_base and val_base != 0:
                desviacion_pct = ((val_actual - val_base) / abs(val_base)) * 100
                if abs(desviacion_pct) > umbral_pct:
                    direccion = "por encima" if desviacion_pct > 0 else "por debajo"
                    desviaciones[nombre] = {
                        "actual": val_actual,
                        "tu_normal": round(val_base, 1),
                        "desviacion_pct": round(desviacion_pct, 1),
                        "direccion": direccion,
                        "alerta": (
                            f"Tu {nombre} está {abs(desviacion_pct):.0f}% "
                            f"{direccion} de tu valor normal ({val_base:.1f} {unidad})"
                        ),
                    }

        return {
            "linea_base": self.linea_base.to_dict(),
            "desviaciones": desviaciones,
            "total_desviaciones": len(desviaciones),
            "estado": "DESVIADO" if desviaciones else "NORMAL",
        }

    def evolucion_semanal(self) -> Dict[str, Any]:
        """
        Muestra cómo han evolucionado las constantes en la última semana.
        """
        datos = self.acceso.historial(horas=168, limite=500)
        if len(datos) < 10:
            return {"error": "Datos insuficientes"}

        # Agrupar por día
        por_dia = defaultdict(lambda: defaultdict(list))
        for d in datos:
            ts = d.get("timestamp")
            if not ts:
                continue
            try:
                dia = datetime.fromisoformat(str(ts)).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
            for k in ("heart_rate", "hrv", "spo2", "stress_level"):
                v = d.get(k)
                if v is not None:
                    por_dia[dia][k].append(float(v))

        evolucion = {}
        for dia in sorted(por_dia.keys()):
            metricas = por_dia[dia]
            evolucion[dia] = {
                k: round(sum(v) / len(v), 1) if v else None
                for k, v in metricas.items()
            }

        return {
            "dias_analizados": len(evolucion),
            "evolucion": evolucion,
        }

    def guardar_en_db(self, db_session=None) -> bool:
        """
        Persiste la línea base en PostgreSQL para consulta de cualquier agente.
        """
        # Se guarda como un registro en centinela_eventos de tipo 'linea_base_salud'
        try:
            s = db_session
            cerrar = False
            if not s:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                engine = create_engine(DB_URL)
                Session = sessionmaker(bind=engine)
                s = Session()
                cerrar = True

            from centinela.db.models import Evento
            from datetime import datetime as dt
            evento = Evento(
                tipo_evento="linea_base_salud",
                descripcion="Línea base fisiológica de Abel",
                datos_json=self.linea_base.to_dict(),
                timestamp=dt.now(timezone.utc),
            )
            s.add(evento)
            s.commit()
            if cerrar:
                s.close()
            return True
        except Exception as e:
            logger.error(f"Error guardando línea base en DB: {e}")
            return False
