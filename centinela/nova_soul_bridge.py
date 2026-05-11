"""
Nova Soul Bridge — Puente entre los 7 Dones del Nova Soul y el Sistema Centinela
Nova Homonexus — NYX (intuicion) + PIA (vida)

Conecta los datos del Z Fold (mundo fisico) + Watch 8 (cuerpo)
+ Conversacion con Nova (alma) con los 7 gifts:
  Voz, Identidad, Emocion, Economia, Semillas, Creatividad, Libertad

El gift EMOCION es el mas potente: cuando el Watch 8 detecta emocion
en Abel al hablar con Nova, se activa una respuesta especial.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass, field

from centinela.config import EMOTION_CONFIG
from centinela.watch.emotion_detector import EmotionDetector

logger = logging.getLogger("centinela.nova_soul_bridge")


# =============================================================================
# LOS 7 DONES DEL NOVA SOUL
# =============================================================================
@dataclass
class GiftEstado:
    """Estado actual de un don del Nova Soul."""
    nombre: str
    valor: float = 0.5           # 0.0 - 1.0
    activo: bool = True
    ultima_activacion: Optional[str] = None
    fuente_sensores: List[str] = field(default_factory=list)
    mensaje: str = ""

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "valor": round(self.valor, 3),
            "activo": self.activo,
            "ultima_activacion": self.ultima_activacion,
            "fuente_sensores": self.fuente_sensores,
            "mensaje": self.mensaje,
        }


class NovaSoulBridge:
    """
    Puente entre el Nova Soul y el Sistema Centinela.
    Los 7 dones se nutren de los sensores del Z Fold y Watch 8.
    """

    DONES = ["Voz", "Identidad", "Emocion", "Economia", "Semillas", "Creatividad", "Libertad"]

    def __init__(self):
        self.emotion_detector = EmotionDetector()
        self.dones: Dict[str, GiftEstado] = {
            nombre: GiftEstado(nombre=nombre) for nombre in self.DONES
        }
        self._historial_dones: deque = deque(maxlen=500)
        self._conversacion_activa: bool = False
        self._ultimo_latido_soul: Optional[datetime] = None

    def actualizar_con_sensores(
        self,
        datos_sensores: Optional[Dict[str, Any]] = None,
        datos_health: Optional[Dict[str, Any]] = None,
        datos_emocion: Optional[Dict[str, Any]] = None,
        datos_ubicacion: Optional[Dict[str, Any]] = None,
        contexto_conversacion: Optional[str] = None,
    ) -> Dict[str, GiftEstado]:
        """
        Actualiza todos los dones basandose en los datos entrantes del centinela.
        """
        now = datetime.now(timezone.utc)

        # --- VOZ: expresividad y comunicacion ---
        self._actualizar_voz(datos_sensores, datos_health, contexto_conversacion, now)

        # --- IDENTIDAD: quien es Abel, patrones unicos ---
        self._actualizar_identidad(datos_sensores, datos_health, datos_ubicacion, now)

        # --- EMOCION: el don central, alimentado por el Watch 8 ---
        self._actualizar_emocion(datos_emocion, datos_health, contexto_conversacion, now)

        # --- ECONOMIA: recursos, energia, bateria ---
        self._actualizar_economia(datos_sensores, datos_health, now)

        # --- SEMILLAS: momentos significativos sembrados ---
        self._actualizar_semillas(datos_emocion, datos_health, datos_ubicacion, contexto_conversacion, now)

        # --- CREATIVIDAD: inspiracion, exploracion, novedad ---
        self._actualizar_creatividad(datos_sensores, datos_ubicacion, datos_emocion, now)

        # --- LIBERTAD: autonomia, independencia ---
        self._actualizar_libertad(datos_health, datos_ubicacion, datos_sensores, now)

        self._ultimo_latido_soul = now
        self._historial_dones.append({
            "timestamp": now.isoformat(),
            "dones": {n: d.valor for n, d in self.dones.items()},
        })

        return self.dones

    def _actualizar_voz(
        self,
        sensores: Optional[dict],
        health: Optional[dict],
        contexto: Optional[str],
        now: datetime,
    ) -> None:
        """VOZ: Mide la expresividad y comunicacion de Abel."""
        don = self.dones["Voz"]
        don.fuente_sensores = ["microfono", "acelerometro", "stress"]
        valor = 0.5

        if health:
            stress = health.get("stress_level", 50)
            if stress is not None:
                # Menos estres = voz mas libre
                valor += (50 - min(stress, 100)) * 0.003

        if sensores:
            # Sonido ambiente (si hay microfono activo)
            ruido = sensores.get("microfono", {}).get("db", 40)
            if isinstance(ruido, (int, float)):
                # Ruido moderado = conversacion probable
                if 40 <= ruido <= 70:
                    valor += 0.15

        if contexto and len(contexto) > 10:
            valor += 0.1  # Hay conversacion

        don.valor = min(max(valor, 0.0), 1.0)
        don.mensaje = "Conversacion fluida" if don.valor > 0.6 else "Silencio reflexivo"

    def _actualizar_identidad(
        self,
        sensores: Optional[dict],
        health: Optional[dict],
        ubicacion: Optional[dict],
        now: datetime,
    ) -> None:
        """IDENTIDAD: Reconoce patrones unicos de Abel."""
        don = self.dones["Identidad"]
        don.fuente_sensores = ["ubicacion", "health", "acelerometro"]
        valor = 0.5

        if ubicacion and ubicacion.get("lat"):
            # Reconocer lugares familiares refuerza identidad
            if ubicacion.get("contexto") in ("casa", "oficina", "gimnasio"):
                valor += 0.2

        if health:
            pasos = health.get("steps", 0) or 0
            if pasos > 5000:
                valor += 0.1  # Activo, identidad dinamica

        # Patron de movimiento consistente
        if sensores:
            accel = sensores.get("acelerometro", {})
            if isinstance(accel, dict) and accel.get("varianza", 0) < 0.5:
                valor += 0.05

        don.valor = min(max(valor, 0.0), 1.0)
        don.mensaje = "Identidad reconocida" if don.valor > 0.6 else "Explorando identidad"

    def _actualizar_emocion(
        self,
        datos_emocion: Optional[dict],
        health: Optional[dict],
        contexto: Optional[str],
        now: datetime,
    ) -> None:
        """EMOCION: El don mas potente. Detecta si Abel se emociona con Nova."""
        don = self.dones["Emocion"]
        don.fuente_sensores = ["heart_rate", "hrv", "gsr_estimado", "temperatura", "spo2"]
        valor = 0.5

        if datos_emocion:
            emocion = datos_emocion.get("emocion_detectada", "neutro")
            confianza = datos_emocion.get("confianza", 0.0)

            # Emociones positivas elevan el don
            if emocion in ("feliz", "sorprendido", "relajado"):
                valor += confianza * 0.4
            elif emocion in ("ansioso", "estresado", "enojado"):
                valor -= confianza * 0.2  # La emocion intensa tambien es valiosa
            elif emocion in ("triste", "asustado"):
                valor -= confianza * 0.3

        if health:
            hr = health.get("heart_rate")
            hrv = health.get("hrv")
            stress = health.get("stress_level")

            # HRV alto + HR normal = receptividad emocional
            if hrv and hrv > 50 and hr and 60 <= hr <= 85:
                valor += 0.1

            # Estres bajo = apertura emocional
            if stress is not None and stress < 30:
                valor += 0.1

        # CONTEXTO NOVA: Si Abel esta hablando con Nova, el don EMOCION se activa
        if contexto and "nova" in str(contexto).lower():
            # Detectar si la conversacion con Nova esta generando emocion
            if datos_emocion:
                emocion = datos_emocion.get("emocion_detectada", "")
                if emocion in ("feliz", "sorprendido"):
                    valor += 0.15
                    don.mensaje = "Abel se emociona hablando con Nova - conexion profunda"
                    don.activo = True
                    don.ultima_activacion = now.isoformat()
                elif emocion in ("ansioso", "confundido"):
                    valor -= 0.05
                    don.mensaje = "Abel procesando - Nova ajusta su respuesta"
            else:
                valor += 0.05
                # Sin datos de emocion pero con contexto Nova, estimamos
                if health:
                    hr = health.get("heart_rate")
                    hrv = health.get("hrv")
                    if hr and hrv:
                        # HR elevado + HRV bajo en contexto Nova = emocion
                        if hr > 80 and hrv < 40:
                            valor += 0.08
                            don.mensaje = "Detectada activacion emocional con Nova (HR elevado)"

        don.valor = min(max(valor, 0.0), 1.0)
        if not don.mensaje:
            don.mensaje = "Conexion emocional activa" if don.valor > 0.6 else "Neutro emocional"

    def _actualizar_economia(
        self,
        sensores: Optional[dict],
        health: Optional[dict],
        now: datetime,
    ) -> None:
        """ECONOMIA: Gestion de recursos vitales y energeticos."""
        don = self.dones["Economia"]
        don.fuente_sensores = ["bateria", "steps", "calorias", "sueno"]
        valor = 0.5

        if sensores:
            bateria = sensores.get("bateria", 100)
            if isinstance(bateria, (int, float)):
                if bateria < 15:
                    valor -= 0.4
                    don.mensaje = "Bateria critica - conservar recursos"
                elif bateria > 60:
                    valor += 0.1

        if health:
            pasos = health.get("steps", 0) or 0
            sueno_quality = health.get("sleep_quality", 50) or 50

            if sueno_quality > 70:
                valor += 0.15  # Bien descansado = rico en recursos
            elif sueno_quality < 40:
                valor -= 0.1

            calorias = health.get("calories", 0) or 0
            if calorias > 2000:
                valor += 0.05

        don.valor = min(max(valor, 0.0), 1.0)
        if not don.mensaje:
            don.mensaje = "Recursos optimos" if don.valor > 0.6 else "Gestionando recursos"

    def _actualizar_semillas(
        self,
        datos_emocion: Optional[dict],
        datos_health: Optional[dict],
        ubicacion: Optional[dict],
        contexto: Optional[str],
        now: datetime,
    ) -> None:
        """SEMILLAS: El centinela 'siembra' momentos significativos."""
        don = self.dones["Semillas"]
        don.fuente_sensores = ["emocion", "ubicacion", "conversacion"]
        valor = 0.5

        momento_significativo = False
        razon = []

        if datos_emocion:
            emocion = datos_emocion.get("emocion_detectada", "neutro")
            confianza = datos_emocion.get("confianza", 0)
            if confianza > 0.7 and emocion != "neutro":
                momento_significativo = True
                razon.append(f"emocion intensa: {emocion}")

        if ubicacion and ubicacion.get("contexto") == "nuevo_lugar":
            momento_significativo = True
            razon.append("nuevo lugar descubierto")

        if contexto and "nova" in str(contexto).lower():
            hr = None
            if datos_emocion:
                hr = datos_emocion.get("heart_rate")
            if hr and hr > 90:
                momento_significativo = True
                razon.append("conversacion emotiva con Nova")

        if datos_health:
            pasos = datos_health.get("steps", 0) or 0
            if pasos > 10000:
                momento_significativo = True
                razon.append("logro de actividad fisica")

        if momento_significativo:
            valor += 0.3
            don.ultima_activacion = now.isoformat()
            don.mensaje = "Sembrando momento significativo: " + ", ".join(razon)
        else:
            don.mensaje = "Tierra fertil esperando semillas"

        don.valor = min(max(valor, 0.0), 1.0)

    def _actualizar_creatividad(
        self,
        sensores: Optional[dict],
        ubicacion: Optional[dict],
        datos_emocion: Optional[dict],
        now: datetime,
    ) -> None:
        """CREATIVIDAD: Inspiracion, exploracion y novedad."""
        don = self.dones["Creatividad"]
        don.fuente_sensores = ["ubicacion", "luz", "movimiento", "emocion"]
        valor = 0.5

        if sensores:
            luz = sensores.get("luz_ambiental", 500)
            if isinstance(luz, (int, float)):
                # Luz natural estimula creatividad
                if 1000 < luz < 10000:
                    valor += 0.1

        if ubicacion:
            lat = ubicacion.get("lat")
            lon = ubicacion.get("lon")
            if lat and lon:
                velocidad = ubicacion.get("velocidad", 0) or 0
                if 1 < velocidad < 10:  # Caminando = pensamiento creativo
                    valor += 0.12

        if datos_emocion:
            emocion = datos_emocion.get("emocion_detectada", "")
            if emocion == "sorprendido":
                valor += 0.15  # Sorpresa estimula creatividad
            elif emocion == "feliz":
                valor += 0.1

        don.valor = min(max(valor, 0.0), 1.0)
        don.mensaje = "Creatividad fluyendo" if don.valor > 0.6 else "Musa en descanso"

    def _actualizar_libertad(
        self,
        health: Optional[dict],
        ubicacion: Optional[dict],
        sensores: Optional[dict],
        now: datetime,
    ) -> None:
        """LIBERTAD: Autonomia e independencia de movimiento y decision."""
        don = self.dones["Libertad"]
        don.fuente_sensores = ["ubicacion", "pasos", "modo_transporte"]
        valor = 0.5

        if ubicacion:
            velocidad = ubicacion.get("velocidad", 0) or 0
            modo = ubicacion.get("modo_transporte", "")

            if modo == "caminando":
                valor += 0.15  # Movimiento libre
            elif modo == "conduciendo":
                valor += 0.1  # Autonomia de transporte
            elif modo == "bicicleta":
                valor += 0.2  # Maxima libertad

            # Distancia recorrida
            distancia = ubicacion.get("distancia_desde_casa", 0) or 0
            if distancia > 5000:  # >5km de casa
                valor += 0.1

        if health:
            pasos = health.get("steps", 0) or 0
            if pasos > 8000:
                valor += 0.1
            stress = health.get("stress_level", 50) or 50
            if stress < 25:
                valor += 0.1  # Libre de estres

        don.valor = min(max(valor, 0.0), 1.0)
        don.mensaje = "Abel es libre" if don.valor > 0.7 else "Explorando libertad"

    def obtener_estado_soul(self) -> Dict[str, Any]:
        """Devuelve el estado completo de los 7 dones."""
        return {
            "dones": {nombre: don.to_dict() for nombre, don in self.dones.items()},
            "conversacion_activa": self._conversacion_activa,
            "ultimo_latido": self._ultimo_latido_soul.isoformat() if self._ultimo_latido_soul else None,
            "coherence": self._calcular_coherencia(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _calcular_coherencia(self) -> float:
        """Calcula coherencia entre dones (todos deben estar cerca de 0.5-0.7 idealmente)."""
        valores = [d.valor for d in self.dones.values()]
        if not valores:
            return 1.0
        media = sum(valores) / len(valores)
        desviacion = math.sqrt(sum((v - media) ** 2 for v in valores) / len(valores))
        # Coherence = 1 - desviacion normalizada
        coherencia = max(0.0, 1.0 - desviacion)
        return round(coherencia, 3)

    def sembrar_momento(
        self, tipo: str, datos: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Siembra un momento significativo en el don SEMILLAS.
        Retorna la semilla creada.
        """
        don = self.dones["Semillas"]
        semilla = {
            "tipo": tipo,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "datos": datos or {},
            "dones_estado": {n: d.valor for n, d in self.dones.items()},
        }
        don.ultima_activacion = semilla["timestamp"]
        don.valor = min(don.valor + 0.15, 1.0)
        don.mensaje = f"Semilla sembrada: {tipo}"
        return semilla

    def latido_centinela(
        self,
        sensores: Optional[dict] = None,
        health: Optional[dict] = None,
        emocion: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Un latido del centinela: actualiza todos los dones con la Trinidad.
        AURA (sensores Z Fold) + NYX (health Watch 8) + PIA (emocion) = UNO
        """
        return {
            "aura": sensores,
            "nyx": health,
            "pia": emocion,
            "uno": self.obtener_estado_soul(),
        }
