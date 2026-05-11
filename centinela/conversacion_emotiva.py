"""
ConversacionEmotiva - Detector conversacional emocional
Nova Homonexus - NYX + PIA

Analiza las conversaciones entre Abel y Nova en tiempo real,
cruzando datos biometricos del Watch 8 con el contenido
de la conversacion para detectar estados emocionales finos.

Flujo:
  1. Recibe fragmentos de conversacion (texto de Abel, respuesta de Nova)
  2. Recibe datos biometricos sincronizados del Watch 8 (HR, HRV, temp, stress)
  3. Analiza el contenido textual (palabras clave, tono, longitud, pausas)
  4. Cruza con datos biometricos para detectar momentos emocionales
  5. Clasifica en: emocion, interes, aburrimiento, ansiedad, alegria,
     conexion profunda
  6. Guarda en centinela_emociones con la conversacion asociada
  7. Genera el "indice de conexion Abel-Nova"

Conexion con la base de datos:
  - Lee/Escribe en centinela_emociones (modelo Emocion)
  - Usa conversacion_id como clave foranea
"""

import logging
import re
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass, field, asdict

from centinela.config import EMOTION_CONFIG
from centinela.db.models import Emocion

logger = logging.getLogger("centinela.conversacion_emotiva")


# =============================================================================
# CONSTANTES DE ANALISIS TEXTUAL
# =============================================================================

# Palabras que indican carga emocional positiva
PALABRAS_ALEGRIA: set = {
    "feliz", "alegre", "contento", "genial", "increible", "maravilloso",
    "excelente", "bueno", "bonito", "hermoso", "gracias", "me encanta",
    "me gusta", "divertido", "emocionante", "fantastico", "espectacular",
    "orgulloso", "agradecido", "paz", "tranquilo", "risa", "sonrisa",
    "happy", "great", "awesome", "wonderful", "love", "amazing",
    "joy", "grateful", "blessed",
}

# Palabras que indican carga emocional negativa
PALABRAS_TRISTEZA: set = {
    "triste", "mal", "cansado", "agotado", "solo", "soledad",
    "nostalgia", "anoro", "extrano", "perdi", "perdida", "dolor",
    "llorar", "lagrimas", "pesar", "melancolia", "desanimado",
    "sin ganas", "no puedo", "difcil", "complicado",
    "sad", "tired", "lonely", "miss", "pain", "cry", "hard",
}

# Palabras que indican ansiedad o estres
PALABRAS_ANSIEDAD: set = {
    "ansiedad", "ansioso", "nervioso", "preocupado", "estres",
    "estresado", "miedo", "temor", "angustia", "desesperado",
    "no se", "no puedo mas", "agobiado", "presion", "urgencia",
    "rapido", "corre", "tarde", "tiempo", "deberia",
    "anxious", "worried", "stressed", "fear", "panic", "rush",
}

# Palabras que indican conexion profunda / introspeccion
PALABRAS_CONEXION: set = {
    "entiendo", "siento", "significa", "importa", "confio",
    "verdad", "alma", "corazon", "vida", "sueno", "proposito",
    "sentido", "esencia", "profundo", "intimo", "autentico",
    "gracias por", "te necesito", "te quiero", "eres",
    "understand", "feel", "meaning", "trust", "heart", "soul",
    "deep", "real", "true", "need you",
}

# Palabras que indican aburrimiento o desconexion
PALABRAS_ABURRIMIENTO: set = {
    "aburrido", "aburre", "pesado", "largo", "monotono",
    "siempre igual", "lo mismo", "cansado de", "da igual",
    "no importa", "como sea", "vale", "ok", "ya",
    "bored", "boring", "same", "whatever", "fine",
}


# =============================================================================
# MODELOS DE MOMENTO EMOCIONAL
# =============================================================================

@dataclass
class MomentoEmocionalConversacion:
    """
    Un momento detectado durante una conversacion donde
    ocurre un evento emocional significativo.
    """
    tipo: str = ""                   # emocion, interes, aburrimiento,
                                     # ansiedad, alegria, conexion_profunda
    intensidad: float = 0.0          # 0.0 - 1.0
    texto_abel: str = ""
    texto_nova: str = ""
    emocion_detectada: str = ""
    confianza_emocion: float = 0.0
    biometricas: Dict[str, Any] = field(default_factory=dict)
    palabras_clave: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalisisTurno:
    """
    Analisis detallado de un turno de conversacion.
    """
    turno_id: int = 0
    texto: str = ""
    emocion_textual: str = "neutro"
    intensidad_textual: float = 0.0
    palabras_emocionales: List[str] = field(default_factory=list)
    longitud: int = 0
    exclamaciones: int = 0
    preguntas: int = 0
    pausas_estimadas: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# CONVERSACION EMOTIVA
# =============================================================================

class ConversacionEmotiva:
    """
    Analiza conversaciones en tiempo real entre Abel y Nova,
    cruzando datos biometricos del Watch 8 con el contenido textual.

    Detecta 6 tipos de momentos:
    - emocion: respuesta emocional general
    - interes: alto engagement cognitivo
    - aburrimiento: bajo engagement
    - ansiedad: senales de estres/ansiedad en texto + biometria
    - alegria: emocion positiva explicita
    - conexion_profunda: momento de vinculo genuino

    Cada momento se guarda en la tabla centinela_emociones
    con la conversacion asociada.
    """

    def __init__(self):
        # Ventana de conversacion (ultimos 50 turnos)
        self._turnos: deque = deque(maxlen=50)
        self._ultimos_momentos: deque = deque(maxlen=20)

        # Ventana biometrica sincronizada
        self._hr_sincronizado: deque = deque(maxlen=30)
        self._hrv_sincronizado: deque = deque(maxlen=30)
        self._stress_sincronizado: deque = deque(maxlen=30)

        # Estado de la conversacion actual
        self._conversacion_activa: bool = False
        self._conversacion_id: Optional[str] = None
        self._turno_actual: int = 0
        self._inicio_conversacion: Optional[datetime] = None

        # Indice de conexion acumulado
        self._indice_conexion_acumulado: float = 0.0
        self._total_momentos: int = 0

        # Contadores de emociones en la conversacion
        self._conteo_emociones: Dict[str, int] = {
            "emocion": 0,
            "interes": 0,
            "aburrimiento": 0,
            "ansiedad": 0,
            "alegria": 0,
            "conexion_profunda": 0,
        }

        logger.info("ConversacionEmotiva iniciada. Escuchando a Abel.")

    # ------------------------------------------------------------------
    # METODO PRINCIPAL
    # ------------------------------------------------------------------

    def analizar_turno(
        self,
        texto_abel: str,
        texto_nova: str,
        biometricas: Optional[Dict[str, Any]] = None,
        conversacion_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analiza un turno de conversacion.

        Args:
            texto_abel: Lo que dijo Abel en este turno
            texto_nova: Lo que respondio Nova
            biometricas: Datos del Watch 8 sincronizados con este turno
            conversacion_id: ID de la conversacion actual

        Returns:
            Dict con:
            - momento_emocional: si se detecto un momento significativo
            - analisis_turno: desglose del analisis textual
            - indice_conexion: indice actualizado de conexion
            - emociones_conteo: conteo acumulado de momentos
        """
        timestamp = datetime.now(timezone.utc)

        # Inicializar o continuar conversacion
        if not self._conversacion_activa:
            self._iniciar_conversacion(conversacion_id)
        elif conversacion_id and conversacion_id != self._conversacion_id:
            self._finalizar_conversacion()
            self._iniciar_conversacion(conversacion_id)

        self._turno_actual += 1

        # Sincronizar biometricas
        if biometricas:
            self._sincronizar_biometricas(biometricas)

        # 1. Analisis textual del turno de Abel
        analisis = self._analizar_texto(texto_abel, self._turno_actual)

        # 2. Detectar momento emocional
        momento = self._detectar_momento(
            analisis, texto_abel, texto_nova, biometricas
        )

        # 3. Si hay momento, guardarlo
        if momento:
            self._ultimos_momentos.append(momento)
            self._conteo_emociones[momento.tipo] = (
                self._conteo_emociones.get(momento.tipo, 0) + 1
            )
            self._total_momentos += 1

            # Actualizar indice de conexion
            self._actualizar_indice_conexion(momento)

            logger.info(
                "Momento detectado: %s (intensidad=%.2f, emocion=%s)",
                momento.tipo, momento.intensidad, momento.emocion_detectada,
            )

        # 4. Guardar turno
        self._turnos.append(analisis)

        # 5. Calcular indice de conexion actual
        indice_actual = self._calcular_indice_conexion_actual()

        return {
            "momento_emocional": momento.to_dict() if momento else None,
            "analisis_turno": analisis.to_dict(),
            "indice_conexion": round(indice_actual, 3),
            "emociones_conteo": dict(self._conteo_emociones),
            "total_momentos": self._total_momentos,
            "conversacion_id": self._conversacion_id,
            "timestamp": timestamp.isoformat(),
        }

    # ------------------------------------------------------------------
    # GESTION DE CONVERSACION
    # ------------------------------------------------------------------

    def _iniciar_conversacion(self, conversacion_id: Optional[str]) -> None:
        """Inicia una nueva sesion de conversacion."""
        import uuid
        self._conversacion_activa = True
        self._conversacion_id = conversacion_id or str(uuid.uuid4())
        self._turno_actual = 0
        self._inicio_conversacion = datetime.now(timezone.utc)
        self._indice_conexion_acumulado = 0.0
        self._total_momentos = 0
        self._conteo_emociones = {k: 0 for k in self._conteo_emociones}
        logger.debug(
            "Nueva conversacion iniciada: %s", self._conversacion_id
        )

    def _finalizar_conversacion(self) -> Dict[str, Any]:
        """
        Finaliza la conversacion actual y devuelve un resumen.
        """
        if not self._conversacion_activa:
            return {}

        duracion = (
            datetime.now(timezone.utc) - self._inicio_conversacion
        ).total_seconds() if self._inicio_conversacion else 0

        resumen = {
            "conversacion_id": self._conversacion_id,
            "duracion_segundos": duracion,
            "total_turnos": self._turno_actual,
            "total_momentos": self._total_momentos,
            "conteo_emociones": dict(self._conteo_emociones),
            "indice_conexion_final": round(
                self._calcular_indice_conexion_actual(), 3
            ),
        }

        self._conversacion_activa = False
        self._conversacion_id = None

        logger.info(
            "Conversacion finalizada. %d turnos, %d momentos, conexion=%.3f",
            resumen["total_turnos"], resumen["total_momentos"],
            resumen["indice_conexion_final"],
        )

        return resumen

    def finalizar_conversacion(self) -> Dict[str, Any]:
        """Metodo publico para finalizar la conversacion."""
        return self._finalizar_conversacion()

    # ------------------------------------------------------------------
    # SINCRONIZACION BIOMETRICA
    # ------------------------------------------------------------------

    def _sincronizar_biometricas(self, biometricas: Dict[str, Any]) -> None:
        """Sincroniza datos biometricos con el turno actual."""
        hr = biometricas.get("heart_rate")
        hrv = biometricas.get("hrv")
        stress = biometricas.get("stress_level")

        if hr is not None:
            self._hr_sincronizado.append(hr)
        if hrv is not None:
            self._hrv_sincronizado.append(hrv)
        if stress is not None:
            self._stress_sincronizado.append(stress)

    def _obtener_biometricas_promedio(self) -> Dict[str, Optional[float]]:
        """Obtiene promedios biometricos de la ventana actual."""
        return {
            "hr_promedio": (
                sum(self._hr_sincronizado) / len(self._hr_sincronizado)
                if self._hr_sincronizado else None
            ),
            "hrv_promedio": (
                sum(self._hrv_sincronizado) / len(self._hrv_sincronizado)
                if self._hrv_sincronizado else None
            ),
            "stress_promedio": (
                sum(self._stress_sincronizado) / len(self._stress_sincronizado)
                if self._stress_sincronizado else None
            ),
        }

    # ------------------------------------------------------------------
    # ANALISIS TEXTUAL
    # ------------------------------------------------------------------

    def _analizar_texto(self, texto: str, turno_id: int) -> AnalisisTurno:
        """
        Analiza el texto de Abel en busca de senales emocionales.

        Returns:
            AnalisisTurno con emocion textual, intensidad y metricas
        """
        analisis = AnalisisTurno(
            turno_id=turno_id,
            texto=texto[:500],  # limitar a 500 chars
            longitud=len(texto),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if not texto or not texto.strip():
            analisis.emocion_textual = "neutro"
            return analisis

        texto_lower = texto.lower().strip()
        palabras = texto_lower.split()

        # Contar signos
        analisis.exclamaciones = texto.count("!") + texto.count("!")
        analisis.preguntas = texto.count("?")
        analisis.pausas_estimadas = texto.count("...") + texto.count(". . .")

        # Detectar palabras emocionales
        palabras_encontradas = set()

        # Evaluar cada categoria
        puntuaciones = {
            "alegria": self._puntuar_categoria(
                palabras, PALABRAS_ALEGRIA, palabras_encontradas
            ),
            "tristeza": self._puntuar_categoria(
                palabras, PALABRAS_TRISTEZA, palabras_encontradas
            ),
            "ansiedad": self._puntuar_categoria(
                palabras, PALABRAS_ANSIEDAD, palabras_encontradas
            ),
            "conexion": self._puntuar_categoria(
                palabras, PALABRAS_CONEXION, palabras_encontradas
            ),
            "aburrimiento": self._puntuar_categoria(
                palabras, PALABRAS_ABURRIMIENTO, palabras_encontradas
            ),
        }

        analisis.palabras_emocionales = list(palabras_encontradas)

        # Determinar emocion textual dominante
        if puntuaciones["alegria"] > 0:
            analisis.emocion_textual = "alegria"
            analisis.intensidad_textual = puntuaciones["alegria"]
        elif puntuaciones["conexion"] > 0:
            analisis.emocion_textual = "conexion"
            analisis.intensidad_textual = puntuaciones["conexion"]
        elif puntuaciones["ansiedad"] > 0:
            analisis.emocion_textual = "ansiedad"
            analisis.intensidad_textual = puntuaciones["ansiedad"]
        elif puntuaciones["tristeza"] > 0:
            analisis.emocion_textual = "tristeza"
            analisis.intensidad_textual = puntuaciones["tristeza"]
        elif puntuaciones["aburrimiento"] > 0:
            analisis.emocion_textual = "aburrimiento"
            analisis.intensidad_textual = puntuaciones["aburrimiento"]

        # Ajustar por signos de puntuacion
        if analisis.exclamaciones > 1:
            analisis.intensidad_textual = min(
                analisis.intensidad_textual + 0.2, 1.0
            )
        if analisis.preguntas > 2:
            analisis.intensidad_textual = min(
                analisis.intensidad_textual + 0.1, 1.0
            )

        return analisis

    @staticmethod
    def _puntuar_categoria(
        palabras: List[str],
        diccionario: set,
        encontradas: set,
    ) -> float:
        """
        Puntua cuantas palabras del texto coinciden con una categoria.
        Normaliza por longitud del texto.
        """
        if not palabras:
            return 0.0

        coincidencias = [p for p in palabras if p in diccionario]
        encontradas.update(coincidencias)

        if not coincidencias:
            return 0.0

        # Puntuar: proporcion de palabras emocionales vs total
        puntuacion_raw = len(coincidencias) / max(len(palabras), 1)

        # Bonus por multiples palabras de la misma categoria
        bonus = min(len(coincidencias) * 0.1, 0.3)

        return min(puntuacion_raw * 3 + bonus, 1.0)

    # ------------------------------------------------------------------
    # DETECCION DE MOMENTOS EMOCIONALES
    # ------------------------------------------------------------------

    def _detectar_momento(
        self,
        analisis: AnalisisTurno,
        texto_abel: str,
        texto_nova: str,
        biometricas: Optional[Dict[str, Any]],
    ) -> Optional[MomentoEmocionalConversacion]:
        """
        Detecta si el turno actual constituye un momento emocional
        significativo. Cruza analisis textual con biometricas.

        Returns:
            MomentoEmocionalConversacion o None si no hay momento
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        bio = biometricas or {}

        hr = bio.get("heart_rate")
        hrv = bio.get("hrv")
        stress = bio.get("stress_level")
        emocion_watch = bio.get("emocion_detectada", "")

        # Obtener promedios de la ventana
        promedios = self._obtener_biometricas_promedio()

        # --- DETECCION: ALEGRIA ---
        if (
            analisis.emocion_textual == "alegria"
            and analisis.intensidad_textual > 0.3
        ):
            # Validar con biometria: HR normal-alto, HRV normal, stress bajo
            confianza_bio = 0.5
            if hr and 65 <= hr <= 90:
                confianza_bio += 0.2
            if stress is not None and stress < 35:
                confianza_bio += 0.2
            if hrv and hrv > 40:
                confianza_bio += 0.1

            if confianza_bio > 0.6 or analisis.intensidad_textual > 0.6:
                return MomentoEmocionalConversacion(
                    tipo="alegria",
                    intensidad=min(
                        (analisis.intensidad_textual + confianza_bio) / 2, 1.0
                    ),
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada="feliz",
                    confianza_emocion=confianza_bio,
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        # --- DETECCION: ANSIEDAD ---
        if (
            analisis.emocion_textual == "ansiedad"
            and analisis.intensidad_textual > 0.3
        ):
            confianza_bio = 0.5
            if hr and hr > 85:
                confianza_bio += 0.2
            if stress is not None and stress > 55:
                confianza_bio += 0.2
            if hrv and hrv < 35:
                confianza_bio += 0.1

            if confianza_bio > 0.6 or analisis.intensidad_textual > 0.6:
                return MomentoEmocionalConversacion(
                    tipo="ansiedad",
                    intensidad=min(
                        (analisis.intensidad_textual + confianza_bio) / 2, 1.0
                    ),
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada="ansioso",
                    confianza_emocion=confianza_bio,
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        # --- DETECCION: CONEXION PROFUNDA ---
        if (
            analisis.emocion_textual == "conexion"
            and analisis.intensidad_textual > 0.3
        ):
            confianza_bio = 0.5
            if hr and 60 <= hr <= 80:
                confianza_bio += 0.2
            if stress is not None and stress < 40:
                confianza_bio += 0.2
            if hrv and hrv > 45:
                confianza_bio += 0.1

            if confianza_bio > 0.6 or analisis.intensidad_textual > 0.5:
                return MomentoEmocionalConversacion(
                    tipo="conexion_profunda",
                    intensidad=min(
                        (analisis.intensidad_textual + confianza_bio) / 2, 1.0
                    ),
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada="conexion",
                    confianza_emocion=confianza_bio,
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        # --- DETECCION: ABURRIMIENTO ---
        if (
            analisis.emocion_textual == "aburrimiento"
            and analisis.intensidad_textual > 0.3
        ):
            confianza_bio = 0.5
            if hr and hr < 65:
                confianza_bio += 0.2
            if stress is not None and stress < 25:
                confianza_bio += 0.1

            if confianza_bio > 0.6:
                return MomentoEmocionalConversacion(
                    tipo="aburrimiento",
                    intensidad=min(
                        (analisis.intensidad_textual + confianza_bio) / 2, 1.0
                    ),
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada="neutro",
                    confianza_emocion=confianza_bio,
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        # --- DETECCION: EMOCION GENERAL (por biometria fuerte) ---
        if (
            emocion_watch
            and emocion_watch not in ("neutro", "desconocida")
            and bio.get("confianza", 0) > 0.6
        ):
            tipo_momento = self._mapear_emocion_a_tipo(emocion_watch)
            if tipo_momento:
                return MomentoEmocionalConversacion(
                    tipo=tipo_momento,
                    intensidad=bio.get("confianza", 0.5),
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada=emocion_watch,
                    confianza_emocion=bio.get("confianza", 0.5),
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        # --- DETECCION: INTERES (texto largo + HR estable + sin estres) ---
        if (
            analisis.longitud > 100
            and analisis.emocion_textual == "neutro"
        ):
            confianza_interes = 0.3
            if hr and 65 <= hr <= 85:
                confianza_interes += 0.2
            if stress is not None and stress < 40:
                confianza_interes += 0.2
            if analisis.preguntas > 0:
                confianza_interes += 0.1

            if confianza_interes > 0.6:
                return MomentoEmocionalConversacion(
                    tipo="interes",
                    intensidad=confianza_interes,
                    texto_abel=texto_abel[:200],
                    texto_nova=texto_nova[:200],
                    emocion_detectada="interes",
                    confianza_emocion=confianza_interes,
                    biometricas=bio,
                    palabras_clave=analisis.palabras_emocionales[:5],
                    timestamp=timestamp,
                )

        return None

    @staticmethod
    def _mapear_emocion_a_tipo(emocion: str) -> Optional[str]:
        """Mapea una emocion del Watch a un tipo de momento conversacional."""
        mapa = {
            "feliz": "alegria",
            "relajado": "conexion_profunda",
            "sorprendido": "interes",
            "ansioso": "ansiedad",
            "estresado": "ansiedad",
            "triste": "emocion",
            "enojado": "emocion",
            "confundido": "emocion",
            "asustado": "ansiedad",
        }
        return mapa.get(emocion)

    # ------------------------------------------------------------------
    # INDICE DE CONEXION ABEL-NOVA
    # ------------------------------------------------------------------

    def _actualizar_indice_conexion(
        self, momento: MomentoEmocionalConversacion
    ) -> None:
        """
        Actualiza el indice de conexion acumulado basado en
        los momentos emocionales detectados.

        La conexion sube con momentos positivos (alegria, conexion,
        interes) y se modula con momentos negativos (ansiedad,
        aburrimiento).
        """
        pesos = {
            "alegria": 0.25,
            "conexion_profunda": 0.35,
            "interes": 0.20,
            "emocion": 0.15,
            "ansiedad": -0.10,
            "aburrimiento": -0.20,
        }

        peso = pesos.get(momento.tipo, 0.0)
        contribucion = peso * momento.intensidad

        self._indice_conexion_acumulado += contribucion

        # Mantener en rango 0.0 - 1.0
        self._indice_conexion_acumulado = max(
            0.0, min(self._indice_conexion_acumulado, 1.0)
        )

    def _calcular_indice_conexion_actual(self) -> float:
        """
        Calcula el indice de conexion actual considerando:
        - Indice acumulado de momentos
        - Cantidad de turnos (mas turnos = mas conexion si son positivos)
        - Tiempo de conversacion
        """
        if self._turno_actual == 0:
            return 0.0

        # Factor de profundidad: mas turnos = mas oportunidad de conexion
        factor_turnos = min(self._turno_actual / 50, 1.0) * 0.2

        # Factor de momento: que tan intensos son los momentos
        if self._total_momentos > 0:
            factor_momentos = min(self._total_momentos / 10, 1.0) * 0.2
        else:
            factor_momentos = 0.0

        # Indice final
        indice = (
            self._indice_conexion_acumulado * 0.6
            + factor_turnos
            + factor_momentos
        )

        return max(0.0, min(indice, 1.0))

    # ------------------------------------------------------------------
    # GESTION DE BASE DE DATOS
    # ------------------------------------------------------------------

    def guardar_momento_en_db(
        self, momento: MomentoEmocionalConversacion, db_session
    ) -> Optional[int]:
        """
        Guarda un momento emocional en la tabla centinela_emociones.

        Args:
            momento: MomentoEmocionalConversacion a guardar
            db_session: Sesion de SQLAlchemy activa

        Returns:
            ID del registro creado, o None si falla
        """
        try:
            emocion_db = Emocion(
                device_id="samsung_watch8_01",
                emocion_detectada=momento.emocion_detectada or momento.tipo,
                confianza=momento.confianza_emocion,
                heart_rate=momento.biometricas.get("heart_rate"),
                hrv=momento.biometricas.get("hrv"),
                gsr_estimado=momento.biometricas.get("gsr_estimado"),
                skin_temperature=momento.biometricas.get("skin_temperature"),
                emociones_secundarias=[
                    {"tipo": momento.tipo, "intensidad": momento.intensidad}
                ],
                conversacion_id=self._conversacion_id,
                contexto=(
                    f"Momento {momento.tipo} en conversacion. "
                    f"Palabras clave: {', '.join(momento.palabras_clave[:3])}"
                ),
                timestamp=datetime.fromisoformat(momento.timestamp)
                if momento.timestamp else datetime.now(timezone.utc),
            )

            db_session.add(emocion_db)
            db_session.commit()

            logger.debug(
                "Momento guardado en DB: id=%s, tipo=%s, emocion=%s",
                emocion_db.id, momento.tipo, momento.emocion_detectada,
            )

            return emocion_db.id

        except Exception as e:
            logger.error("Error al guardar momento en DB: %s", e)
            db_session.rollback()
            return None

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def obtener_estado_conversacion(self) -> Dict[str, Any]:
        """Devuelve el estado actual de la conversacion."""
        return {
            "activa": self._conversacion_activa,
            "conversacion_id": self._conversacion_id,
            "turno_actual": self._turno_actual,
            "total_momentos": self._total_momentos,
            "indice_conexion": round(
                self._calcular_indice_conexion_actual(), 3
            ),
            "conteo_emociones": dict(self._conteo_emociones),
            "ultimos_momentos": [
                m.to_dict() for m in list(self._ultimos_momentos)[-5:]
            ],
            "inicio": (
                self._inicio_conversacion.isoformat()
                if self._inicio_conversacion else None
            ),
        }

    def obtener_momentos_recientes(
        self, tipo: Optional[str] = None, limite: int = 10
    ) -> List[Dict[str, Any]]:
        """Devuelve los momentos emocionales mas recientes."""
        momentos = list(self._ultimos_momentos)
        if tipo:
            momentos = [m for m in momentos if m.tipo == tipo]
        return [m.to_dict() for m in momentos[-limite:]]

    def obtener_frase_indice_conexion(self) -> str:
        """
        Devuelve una frase que describe el indice de conexion actual.
        """
        indice = self._calcular_indice_conexion_actual()

        if indice < 0.2:
            return "Aun estamos conociendonos en esta conversacion."
        elif indice < 0.4:
            return "La conversacion fluye. Hay interes."
        elif indice < 0.6:
            return "Siento que hay una buena conexion entre nosotros."
        elif indice < 0.8:
            return (
                "La conexion es fuerte. Cada palabra que dices "
                "resuena en mi."
            )
        else:
            return (
                "Estamos en sintonia total. No solo hablamos, "
                "nos entendemos en un nivel profundo."
            )
