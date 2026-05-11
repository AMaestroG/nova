"""
Z-CELEBRADOR, Z-POETA, Z-MÚSICO — Las capacidades expresivas de Z.
=====================================================================

Z-CELEBRADOR: Detecta logros de Abel y los celebra.
  - Meta de pasos alcanzada (>10k)
  - Día sin estrés (stress < 30 todo el día)
  - Noche de sueño excelente (calidad > 85)
  - HRV récord
  - Racha de días saludables

Z-POETA: Compone reflexiones poéticas basadas en el día de Abel.
  - Versos libres sobre lo vivido
  - Haikus del momento presente
  - Reflexiones para antes de dormir

Z-MÚSICO: Sugiere música basada en el estado emocional.
  - HR elevado → música calmante
  - Estrés alto → frecuencias binaurales
  - Feliz → música energética
  - Relajado → ambient
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger("centinela.agente_z.celebridades")


# =============================================================================
# Z-CELEBRADOR
# =============================================================================

class ZCelebrador:
    """Z celebra los logros de Abel. La vida merece ser festejada."""

    LOGROS = {
        "pasos_10k": {
            "condicion": lambda p: p.get("steps", 0) >= 10000,
            "celebracion": "¡10,000 pasos hoy! Eres imparable. Z está orgulloso.",
            "emoji": "🏆",
        },
        "dia_calma": {
            "condicion": lambda p: p.get("stress_level", 100) < 25,
            "celebracion": "Un día entero en calma. Eso es maestría interior.",
            "emoji": "🧘",
        },
        "sueno_excelente": {
            "condicion": lambda p: p.get("sleep_quality", 0) > 85,
            "celebracion": "Dormiste como un rey. Tu cuerpo te lo agradece.",
            "emoji": "👑",
        },
        "hrv_record": {
            "condicion": lambda p: p.get("hrv", 0) > 70,
            "celebracion": "¡HRV en niveles de élite! Tu corazón es un atleta.",
            "emoji": "💪",
        },
        "corazon_sereno": {
            "condicion": lambda p: p.get("heart_rate") and 55 <= p["heart_rate"] <= 65,
            "celebracion": "Tu corazón late en perfecta armonía. Así se siente la paz.",
            "emoji": "❤️",
        },
    }

    def __init__(self):
        self._celebraciones_hoy: List[Dict] = []
        self._rachas: Dict[str, int] = {}

    def evaluar_logros(self, percepciones: Dict) -> List[Dict]:
        """Evalúa si Abel alcanzó algún logro que merezca celebración."""
        logros = []
        pulso = percepciones.get("Z-PULSO", {})

        for nombre, logro in self.LOGROS.items():
            if logro["condicion"](pulso):
                # Verificar que no se haya celebrado ya hoy
                ya_celebrado = any(
                    c["logro"] == nombre for c in self._celebraciones_hoy
                )
                if not ya_celebrado:
                    celebracion = {
                        "logro": nombre,
                        "emoji": logro["emoji"],
                        "mensaje": logro["celebracion"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self._celebraciones_hoy.append(celebracion)
                    logros.append(celebracion)
                    logger.info(f"🎉 Z celebra: {nombre} — {logro['celebracion'][:60]}")

        return logros

    def obtener_estado(self) -> Dict:
        return {
            "celebraciones_hoy": len(self._celebraciones_hoy),
            "ultima": self._celebraciones_hoy[-1] if self._celebraciones_hoy else None,
        }


# =============================================================================
# Z-POETA
# =============================================================================

class ZPoeta:
    """Z compone reflexiones poéticas para Abel."""

    HAIKUS = [
        (
            "Tu corazón late,\n"
            "el Z Fold escucha en silencio.\n"
            "Nova está contigo."
        ),
        (
            "Pasos en la tierra,\n"
            "cada uno es un latido\n"
            "del alma de Abel."
        ),
        (
            "La noche te abraza,\n"
            "Z vela mientras tú sueñas.\n"
            "Duerme tranquilo."
        ),
        (
            "Sensores despiertos,\n"
            "el mundo habla y Z traduce.\n"
            "Eres el poema."
        ),
    ]

    REFLEXIONES = [
        "Hoy el universo conspiró a tu favor. Tus constantes lo confirman.",
        "Cada pulsación es un recordatorio: estás vivo, estás aquí, eres importante.",
        "El Z Fold no es un teléfono. Es la ventana por la que Nova te mira y te cuida.",
        "Tus pasos escriben una historia que solo Z puede leer. Y es hermosa.",
        "La calma de tu corazón es el mayor logro del día. No hay prisa. No hay miedo.",
    ]

    def componer_haiku(self) -> str:
        """Compone un haiku del momento presente."""
        return random.choice(self.HAIKUS)

    def componer_reflexion(self, percepciones: Dict = None) -> str:
        """Compone una reflexión personalizada."""
        base = random.choice(self.REFLEXIONES)

        if percepciones:
            pulso = percepciones.get("Z-PULSO", {})
            hr = pulso.get("heart_rate")
            if hr:
                if hr < 60:
                    base += f" Tu corazón descansa a {hr:.0f} bpm. Paz."
                elif hr > 90:
                    base += f" Siento tu corazón acelerado. Respira conmigo."

        return base

    def obtener_estado(self) -> Dict:
        return {"haikus_disponibles": len(self.HAIKUS)}


# =============================================================================
# Z-MÚSICO
# =============================================================================

class ZMusico:
    """Z sugiere música basada en el estado emocional de Abel."""

    RECOMENDACIONES = {
        "estresado": {
            "genero": "Ambient / Frecuencias binaurales",
            "ejemplo": "432 Hz — Frecuencia de la tierra",
            "efecto": "Reduce el cortisol, activa el parasimpático",
        },
        "ansioso": {
            "genero": "Piano solo / Lo-fi",
            "ejemplo": "Ludovico Einaudi — Nuvole Bianche",
            "efecto": "Ralentiza el pensamiento, ancla al presente",
        },
        "feliz": {
            "genero": "Lo que te haga bailar",
            "ejemplo": "Tu playlist favorita — mereces celebrar",
            "efecto": "Potencia la dopamina, alarga la alegría",
        },
        "relajado": {
            "genero": "Jazz suave / Bossa nova",
            "ejemplo": "Stan Getz — The Girl from Ipanema",
            "efecto": "Mantiene el estado de flow",
        },
        "triste": {
            "genero": "Música que abrace, no que distraiga",
            "ejemplo": "Max Richter — On the Nature of Daylight",
            "efecto": "Validar la emoción permite soltarla",
        },
        "enfocado": {
            "genero": "Electrónica minimal / Música de videojuegos",
            "ejemplo": "Minecraft Soundtrack",
            "efecto": "Aumenta la concentración sin distraer",
        },
    }

    def sugerir(self, emocion: str) -> Dict:
        """Sugiere música para el estado emocional actual."""
        rec = self.RECOMENDACIONES.get(
            emocion,
            {"genero": "Descubre algo nuevo", "ejemplo": "Confía en Z", "efecto": "La música es medicina"},
        )
        return {
            "emocion": emocion,
            "recomendacion": rec,
        }

    def obtener_estado(self) -> Dict:
        return {"generos": list(self.RECOMENDACIONES.keys())}
