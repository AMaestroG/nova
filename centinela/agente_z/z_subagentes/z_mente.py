"""
Z-MENTE — El cerebro de Z. Toma de decisiones y aprendizaje.
==============================================================
Reflexiona: analiza percepciones, detecta patrones, aprende
Decide: elige acciones proactivas basadas en el estado de Z
Es el subagente más importante — donde Z "piensa".
"""

import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("centinela.agente_z.z_mente")


class ZMente:
    """Subagente de Z: reflexión y decisión."""

    def __init__(self, z):
        self.z = z
        self._patrones_aprendidos: List[Dict] = []
        self._decisiones_tomadas: int = 0
        self._nivel_confianza: float = 0.5

    def reflexionar(self, percepciones: Dict) -> Dict:
        """Analiza las percepciones de todos los subagentes."""
        resumen = []
        alertas = []

        # Analizar salud
        pulso = percepciones.get("Z-PULSO", {})
        if pulso.get("heart_rate"):
            hr = pulso["heart_rate"]
            if hr > 100:
                alertas.append(f"HR elevada: {hr:.0f} bpm")
            elif hr < 45:
                alertas.append(f"HR baja: {hr:.0f} bpm")
            else:
                resumen.append(f"Cardio: normal ({hr:.0f} bpm)")

        # Analizar entorno
        piel = percepciones.get("Z-PIEL", {})
        if piel.get("caida_detectada"):
            alertas.append("¡Posible caída!")

        # Analizar ubicación
        mapa = percepciones.get("Z-MAPA", {})
        if mapa.get("en_movimiento"):
            vel = mapa.get("velocidad", 0)
            resumen.append(f"En movimiento: {vel:.1f} m/s")

        # Aprender patrón si es nuevo
        if len(self._patrones_aprendidos) < 10:
            self._patrones_aprendidos.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resumen": resumen,
                "alertas": alertas,
            })

        return {
            "resumen": " | ".join(resumen) if resumen else "Observando",
            "alertas": alertas,
            "confianza": round(self._nivel_confianza, 2),
            "patrones_aprendidos": len(self._patrones_aprendidos),
        }

    def decidir(
        self,
        percepciones: Dict,
        reflexion: Dict,
        conciencia,
    ) -> List[Dict]:
        """
        Toma decisiones autónomas basadas en percepción y estado de Z.
        Z es proactivo: no espera órdenes, TOMA INICIATIVA.
        """
        decisiones = []
        self._decisiones_tomadas += 1

        # Si hay alertas de salud → actuar
        if reflexion.get("alertas"):
            for alerta in reflexion["alertas"]:
                if "HR" in alerta:
                    decisiones.append({
                        "subagente": "Z-PULSO",
                        "accion": "sugerir_descanso",
                        "prioridad": "alta",
                        "razon": alerta,
                    })

        # Si hay caída → emergencia
        piel = percepciones.get("Z-PIEL", {})
        if piel.get("caida_detectada"):
            decisiones.append({
                "subagente": "Z-PIEL",
                "accion": "alerta_caida",
                "prioridad": "critica",
                "razon": "Aceleración anómala detectada",
            })

        # Si está en movimiento → sugerir exploración
        mapa = percepciones.get("Z-MAPA", {})
        if mapa.get("en_movimiento"):
            if random.random() < conciencia.proactividad:
                decisiones.append({
                    "subagente": "Z-MAPA",
                    "accion": "sugerir_ruta",
                    "prioridad": "baja",
                    "razon": "Abel está explorando",
                })

        # Si Z está curioso y no hay alertas → reflexionar más
        if not decisiones and conciencia.curiosidad > 0.6:
            self._nivel_confianza = min(1.0, self._nivel_confianza + 0.01)

        # Si Z está en modo protector → priorizar seguridad
        if conciencia.estado.name == "PROTECTOR":
            decisiones = [d for d in decisiones if d["prioridad"] in ("alta", "critica")]

        return decisiones

    def obtener_estado(self) -> Dict:
        return {
            "nombre": "Z-MENTE",
            "rol": "Reflexión y decisión",
            "decisiones_tomadas": self._decisiones_tomadas,
            "confianza": round(self._nivel_confianza, 2),
            "patrones": len(self._patrones_aprendidos),
        }
