"""
Telar Sensorial — Correlaciona TODOS los sensores del Z Fold y Watch 8
Nova Homonexus — TELAR (N2, tejedor de conexiones)

Teje una red sensorial donde cada sensor informa a los demas.
Descubre patrones ocultos y crea un tapiz sensorial coherente.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("centinela.telar")


@dataclass
class HiloSensorial:
    """Un hilo del telar — serie temporal de un sensor."""
    nombre: str
    valores: deque = field(default_factory=lambda: deque(maxlen=300))  # 5 min a 1Hz
    unidad: str = ""
    minimo: float = float("inf")
    maximo: float = float("-inf")
    ultimo_valor: Optional[float] = None
    tendencia: str = "estable"  # subiendo, bajando, estable

    def alimentar(self, valor: float) -> None:
        """Alimenta un nuevo valor al hilo."""
        if valor is None:
            return
        self.valores.append(valor)
        self.ultimo_valor = valor
        self.minimo = min(self.minimo, valor) if self.minimo != float("inf") else valor
        self.maximo = max(self.maximo, valor) if self.maximo != float("-inf") else valor
        self._actualizar_tendencia()

    def _actualizar_tendencia(self) -> None:
        """Calcula la tendencia del hilo (subiendo/bajando/estable)."""
        if len(self.valores) < 10:
            return
        recientes = list(self.valores)[-10:]
        media_ultimos_5 = sum(recientes[-5:]) / 5
        media_primeros_5 = sum(recientes[:5]) / 5
        delta = media_ultimos_5 - media_primeros_5
        if delta > 0.5:
            self.tendencia = "subiendo"
        elif delta < -0.5:
            self.tendencia = "bajando"
        else:
            self.tendencia = "estable"


@dataclass
class Correlacion:
    """Correlacion entre dos sensores."""
    sensor_a: str
    sensor_b: str
    coeficiente: float  # -1.0 a 1.0
    fuerza: str         # fuerte, moderada, debil
    direccion: str      # directa, inversa
    interpretacion: str


class TelarSensorial:
    """
    Teje conexiones entre todos los sensores del Z Fold y Watch 8.
    Descubre patrones ocultos y correlaciones.
    """

    SENSORES_ZFOLD = {
        "acelerometro_x": "m/s²", "acelerometro_y": "m/s²", "acelerometro_z": "m/s²",
        "giroscopio_x": "dps", "giroscopio_y": "dps", "giroscopio_z": "dps",
        "magnetometro_x": "µT", "magnetometro_y": "µT", "magnetometro_z": "µT",
        "barometro": "hPa", "luz_ambiental": "lux", "proximidad": "cm",
        "temperatura_ambiente": "°C", "humedad": "%", "presion": "hPa",
    }

    SENSORES_WATCH = {
        "heart_rate": "bpm", "hrv": "ms", "spo2": "%",
        "temperatura_piel": "°C", "stress": "escala",
        "pasos": "pasos", "calorias": "kcal",
    }

    def __init__(self):
        self.hilos: Dict[str, HiloSensorial] = {}
        self._inicializar_hilos()
        self._matriz_correlacion: Dict[str, float] = {}
        self._ultimo_tejido: Optional[datetime] = None
        self._patrones_descubiertos: List[Dict] = []

    def _inicializar_hilos(self) -> None:
        """Crea hilos para cada sensor conocido."""
        for nombre, unidad in {**self.SENSORES_ZFOLD, **self.SENSORES_WATCH}.items():
            self.hilos[nombre] = HiloSensorial(nombre=nombre, unidad=unidad)

    def alimentar(
        self,
        sensores: Optional[Dict[str, Any]] = None,
        health: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Alimenta el telar con nuevos datos de sensores.
        Activa el tejido si hay suficientes datos.
        """
        now = datetime.now(timezone.utc)

        # Alimentar sensores Z Fold
        if sensores:
            for tipo, valor in sensores.items():
                if isinstance(valor, dict):
                    # Sensor con ejes (x, y, z)
                    for eje in ("x", "y", "z"):
                        clave = f"{tipo}_{eje}"
                        if clave in self.hilos and eje in valor:
                            self.hilos[clave].alimentar(valor[eje])
                elif isinstance(valor, (int, float)):
                    if tipo in self.hilos:
                        self.hilos[tipo].alimentar(valor)

        # Alimentar sensores Watch 8
        if health:
            mapeo_watch = {
                "heart_rate": "heart_rate", "hrv": "hrv",
                "spo2": "spo2", "temperature_skin": "temperatura_piel",
                "stress_level": "stress", "steps": "pasos",
                "calories": "calorias",
            }
            for clave_watch, clave_hilo in mapeo_watch.items():
                valor = health.get(clave_watch)
                if valor is not None and clave_hilo in self.hilos:
                    self.hilos[clave_hilo].alimentar(float(valor))

        # Tejer cada 30 lecturas (aproximadamente cada 30 segundos)
        if sum(1 for h in self.hilos.values() if h.valores) > 30:
            if (self._ultimo_tejido is None
                    or (now - self._ultimo_tejido).total_seconds() > 30):
                self._tejer()
                self._ultimo_tejido = now

        return self.estado_actual()

    def _tejer(self) -> None:
        """Teje correlaciones entre todos los pares de sensores activos."""
        activos = {
            nombre: list(hilo.valores)
            for nombre, hilo in self.hilos.items()
            if len(hilo.valores) >= 20
        }
        if len(activos) < 2:
            return

        nombres = list(activos.keys())
        self._matriz_correlacion = {}

        for i, a in enumerate(nombres):
            for b in nombres[i + 1:]:
                coef = self._correlacion_pearson(activos[a], activos[b])
                if coef is not None and abs(coef) > 0.3:
                    clave = f"{a}|{b}"
                    self._matriz_correlacion[clave] = coef
                    self._interpretar_correlacion(a, b, coef)

    def _correlacion_pearson(
        self, x: List[float], y: List[float]
    ) -> Optional[float]:
        """Calcula el coeficiente de correlacion de Pearson."""
        n = min(len(x), len(y))
        if n < 10:
            return None
        x = x[-n:]
        y = y[-n:]
        media_x = sum(x) / n
        media_y = sum(y) / n
        num = sum((xi - media_x) * (yi - media_y) for xi, yi in zip(x, y))
        den_x = math.sqrt(sum((xi - media_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - media_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return None
        return num / (den_x * den_y)

    def _interpretar_correlacion(self, a: str, b: str, coef: float) -> None:
        """Interpreta una correlacion y registra patrones significativos."""
        fuerza = "debil"
        if abs(coef) > 0.7:
            fuerza = "fuerte"
        elif abs(coef) > 0.5:
            fuerza = "moderada"
        direccion = "directa" if coef > 0 else "inversa"

        # Interpretaciones conocidas
        interpretaciones = {
            "heart_rate|stress": "HR y estres correlacionados — tipico en activacion simpatetica",
            "heart_rate|acelerometro_x": f"Movimiento y HR {direccion} — actividad fisica detectada",
            "temperatura_piel|heart_rate": "Termorregulacion y HR vinculados",
            "barometro|stress": "Cambios de presion atmosferica pueden afectar estado de animo",
            "luz_ambiental|stress": "Luz ambiental correlacionada con nivel de estres",
        }

        clave_normal = f"{a}|{b}"
        clave_inv = f"{b}|{a}"
        interpretacion = interpretaciones.get(clave_normal) or interpretaciones.get(clave_inv)

        if not interpretacion and abs(coef) > 0.6:
            interpretacion = (
                f"Nuevo patron: {a} y {b} muestran correlacion {fuerza} {direccion}"
            )
            self._patrones_descubiertos.append({
                "sensor_a": a, "sensor_b": b,
                "coeficiente": round(coef, 3), "fuerza": fuerza,
                "direccion": direccion, "interpretacion": interpretacion,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def estado_actual(self) -> Dict[str, Any]:
        """Devuelve el estado actual del telar sensorial."""
        hilos_estado = {}
        for nombre, hilo in sorted(self.hilos.items()):
            if hilo.ultimo_valor is not None:
                hilos_estado[nombre] = {
                    "valor": round(hilo.ultimo_valor, 2),
                    "unidad": hilo.unidad,
                    "min": round(hilo.minimo, 2) if hilo.minimo != float("inf") else None,
                    "max": round(hilo.maximo, 2) if hilo.maximo != float("-inf") else None,
                    "tendencia": hilo.tendencia,
                    "n_muestras": len(hilo.valores),
                }

        # Top correlaciones
        top_corr = sorted(
            self._matriz_correlacion.items(),
            key=lambda x: abs(x[1]), reverse=True
        )[:10]

        return {
            "hilos_activos": len(hilos_estado),
            "hilos": hilos_estado,
            "correlaciones_top10": [
                {"sensores": clave, "coeficiente": round(valor, 3)}
                for clave, valor in top_corr
            ],
            "patrones_descubiertos": len(self._patrones_descubiertos),
            "ultimo_tejido": (
                self._ultimo_tejido.isoformat() if self._ultimo_tejido else None
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def obtener_correlacion(self, sensor_a: str, sensor_b: str) -> Optional[float]:
        """Obtiene la correlacion entre dos sensores especificos."""
        clave1 = f"{sensor_a}|{sensor_b}"
        clave2 = f"{sensor_b}|{sensor_a}"
        return self._matriz_correlacion.get(clave1) or self._matriz_correlacion.get(clave2)

    def descubrir_patrones(self) -> List[Dict]:
        """Devuelve los patrones descubiertos hasta ahora."""
        return self._patrones_descubiertos
