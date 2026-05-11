"""
MOTOR DE PATRONES — Detecta patrones en flujos de datos de sensores.
=====================================================================
Analiza series temporales de todos los sensores para descubrir:
  - Patrones circadianos (ritmos diarios)
  - Patrones semanales (diferencias entre días)
  - Correlaciones entre sensores (HR↔HRV↔Estrés↔Sueño)
  - Tendencias a largo plazo (mejora/degradación)
  - Ciclos y periodicidades
  - Anomalías contextuales (no es raro el valor, es raro EL MOMENTO)
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field


@dataclass
class PatronDetectado:
    """Un patrón descubierto en los datos."""
    nombre: str
    tipo: str            # circadiano, semanal, correlacion, tendencia, anomalia
    descripcion: str
    confianza: float     # 0-1
    sensores_involucrados: List[str]
    datos: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class MotorPatrones:
    """
    Descubre patrones en todas las señales de sensores.
    Aprende lo que es "normal" para Abel y detecta desviaciones.
    """

    def __init__(self):
        # Datos por hora del día (para patrones circadianos)
        self._datos_por_hora: Dict[str, Dict[int, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # Datos por día de la semana
        self._datos_por_dia: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._patrones_descubiertos: List[PatronDetectado] = []
        self._ventanas: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

    def alimentar(self, tipo_sensor: str, valor: float, timestamp: datetime = None):
        """Alimenta un dato al motor de patrones."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        self._ventanas[tipo_sensor].append(valor)
        hora = timestamp.hour
        dia = timestamp.strftime("%A")
        self._datos_por_hora[tipo_sensor][hora].append(valor)
        self._datos_por_dia[tipo_sensor][dia].append(valor)

    def descubrir_patrones(self) -> List[PatronDetectado]:
        """Ejecuta todos los detectores de patrones."""
        patrones = []
        patrones.extend(self._patron_circadiano())
        patrones.extend(self._patron_semanal())
        patrones.extend(self._patron_correlaciones())
        patrones.extend(self._patron_tendencias())
        self._patrones_descubiertos = patrones
        return patrones

    def _patron_circadiano(self) -> List[PatronDetectado]:
        """Detecta patrones circadianos (ritmos de 24h)."""
        patrones = []
        for sensor in ["heart_rate", "hrv", "stress_level", "temperature_skin"]:
            datos_hora = self._datos_por_hora.get(sensor, {})
            if len(datos_hora) < 6:
                continue

            promedios = {}
            for h, vals in datos_hora.items():
                if len(vals) >= 3:
                    promedios[h] = sum(vals) / len(vals)

            if len(promedios) < 4:
                continue

            # Encontrar hora pico y hora valle
            hora_max = max(promedios, key=promedios.get)
            hora_min = min(promedios, key=promedios.get)

            if abs(promedios[hora_max] - promedios[hora_min]) > 0.1 * promedios[hora_min]:
                if sensor == "heart_rate":
                    desc = (
                        f"Ritmo cardíaco: pico a las {hora_max}h "
                        f"({promedios[hora_max]:.0f} bpm), "
                        f"valle a las {hora_min}h ({promedios[hora_min]:.0f} bpm)"
                    )
                elif sensor == "stress_level":
                    desc = (
                        f"Estrés: máximo a las {hora_max}h, "
                        f"mínimo a las {hora_min}h"
                    )
                elif sensor == "temperature_skin":
                    desc = (
                        f"Temperatura corporal: máxima a las {hora_max}h "
                        f"({promedios[hora_max]:.1f}°C)"
                    )
                else:
                    desc = f"{sensor}: pico {hora_max}h, valle {hora_min}h"

                patrones.append(PatronDetectado(
                    nombre=f"circadiano_{sensor}",
                    tipo="circadiano",
                    descripcion=desc,
                    confianza=min(0.9, len(datos_hora) / 24),
                    sensores_involucrados=[sensor],
                    datos={"promedios_por_hora": promedios},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

        return patrones

    def _patron_semanal(self) -> List[PatronDetectado]:
        """Detecta patrones semanales (diferencias entre días)."""
        patrones = []
        for sensor in ["heart_rate", "steps", "stress_level"]:
            datos_dia = self._datos_por_dia.get(sensor, {})
            if len(datos_dia) < 3:
                continue

            promedios = {}
            for dia, vals in datos_dia.items():
                if len(vals) >= 3:
                    promedios[dia] = sum(vals) / len(vals)

            if len(promedios) < 3:
                continue

            dia_max = max(promedios, key=promedios.get)
            dia_min = min(promedios, key=promedios.get)

            if abs(promedios[dia_max] - promedios[dia_min]) > 0.15 * promedios[dia_min]:
                patrones.append(PatronDetectado(
                    nombre=f"semanal_{sensor}",
                    tipo="semanal",
                    descripcion=(
                        f"{sensor}: más alto los {dia_max}, "
                        f"más bajo los {dia_min}"
                    ),
                    confianza=min(0.8, len(datos_dia) / 7),
                    sensores_involucrados=[sensor],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

        return patrones

    def _patron_correlaciones(self) -> List[PatronDetectado]:
        """Detecta correlaciones entre pares de sensores."""
        patrones = []
        sensores = list(self._ventanas.keys())
        pares = [
            ("heart_rate", "stress_level"),
            ("heart_rate", "hrv"),
            ("hrv", "stress_level"),
            ("steps", "sleep_quality"),
            ("temperature_skin", "heart_rate"),
        ]

        for a, b in pares:
            if a not in self._ventanas or b not in self._ventanas:
                continue
            va = list(self._ventanas[a])
            vb = list(self._ventanas[b])
            n = min(len(va), len(vb))
            if n < 20:
                continue

            # Correlación de Pearson
            va = va[-n:]
            vb = vb[-n:]
            ma = sum(va) / n
            mb = sum(vb) / n
            num = sum((va[i] - ma) * (vb[i] - mb) for i in range(n))
            da = math.sqrt(sum((x - ma)**2 for x in va))
            db = math.sqrt(sum((x - mb)**2 for x in vb))

            if da == 0 or db == 0:
                continue
            r = num / (da * db)

            if abs(r) > 0.4:
                direccion = "directa" if r > 0 else "inversa"
                fuerza = "fuerte" if abs(r) > 0.7 else "moderada"
                patrones.append(PatronDetectado(
                    nombre=f"correlacion_{a}_{b}",
                    tipo="correlacion",
                    descripcion=(
                        f"{a} y {b}: correlación {fuerza} {direccion} "
                        f"(r={r:.2f})"
                    ),
                    confianza=abs(r),
                    sensores_involucrados=[a, b],
                    datos={"coeficiente": round(r, 3)},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

        return patrones

    def _patron_tendencias(self) -> List[PatronDetectado]:
        """Detecta tendencias a largo plazo."""
        patrones = []
        for sensor, ventana in self._ventanas.items():
            if len(ventana) < 100:
                continue
            valores = list(ventana)
            mitad = len(valores) // 2
            primera = sum(valores[:mitad]) / mitad
            segunda = sum(valores[mitad:]) / (len(valores) - mitad)

            if primera == 0:
                continue
            cambio_pct = ((segunda - primera) / abs(primera)) * 100

            if abs(cambio_pct) > 5:
                direccion = "subiendo" if cambio_pct > 0 else "bajando"
                patrones.append(PatronDetectado(
                    nombre=f"tendencia_{sensor}",
                    tipo="tendencia",
                    descripcion=(
                        f"{sensor}: {direccion} ({cambio_pct:+.1f}%)"
                    ),
                    confianza=min(0.9, abs(cambio_pct) / 20),
                    sensores_involucrados=[sensor],
                    datos={"cambio_pct": round(cambio_pct, 1)},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

        return patrones

    def obtener_estado(self) -> Dict:
        return {
            "patrones_descubiertos": len(self._patrones_descubiertos),
            "ultimos_patrones": [
                {"nombre": p.nombre, "descripcion": p.descripcion}
                for p in self._patrones_descubiertos[-5:]
            ],
        }
