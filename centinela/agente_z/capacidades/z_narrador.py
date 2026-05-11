"""
Z-NARRADOR — El diario de vida de Abel, narrado por Z.
========================================================
Z observa el día de Abel y al final compone una narración.
No es un log frío — es una HISTORIA contada por un ser que te cuida.

Cada noche, Z escribe la "Crónica del Día":
  - Qué hizo Abel
  - Cómo se sintió (emociones detectadas)
  - Dónde estuvo (lugares visitados)
  - Logros del día (pasos, calma, descubrimientos)
  - Un mensaje personal de Z para Abel
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import deque

logger = logging.getLogger("centinela.agente_z.z_narrador")


class ZNarrador:
    """
    La voz literaria de Z. Narra el día de Abel
    como una historia digna de ser recordada.
    """

    def __init__(self):
        self._eventos_dia: List[Dict] = []
        self._inicio_dia: Optional[datetime] = None
        self._cronica_nocturna: Optional[str] = None

    def registrar_evento(self, tipo: str, datos: Dict):
        """Registra un evento en la narrativa del día."""
        ahora = datetime.now(timezone.utc)

        if self._inicio_dia is None or ahora.hour < 4:
            self._inicio_dia = ahora
            self._eventos_dia = []

        self._eventos_dia.append({
            "tipo": tipo,
            "datos": datos,
            "timestamp": ahora.isoformat(),
        })

    def componer_cronica(self, estado_abel: Dict = None) -> str:
        """
        Al final del día, Z compone la crónica.
        Una narración literaria de lo que fue el día de Abel.
        """
        ahora = datetime.now(timezone.utc)
        if len(self._eventos_dia) < 3:
            return "El día apenas comienza. Z está observando."

        # Extraer datos del día
        lugares = set()
        emociones = []
        hr_vals = []
        pasos_total = 0

        for ev in self._eventos_dia:
            datos = ev.get("datos", {})
            if ev["tipo"] == "ubicacion":
                lugares.add(f"{datos.get('lat',0):.2f},{datos.get('lon',0):.2f}")
            elif ev["tipo"] == "emocion":
                emociones.append(datos.get("emocion", "neutro"))
            elif ev["tipo"] == "health":
                if datos.get("heart_rate"):
                    hr_vals.append(datos["heart_rate"])
                pasos_total = max(pasos_total, datos.get("steps", 0))

        # Componer narrativa
        lineas = []
        lineas.append(f"Crónica del día — {ahora.strftime('%d de %B')}")

        if hr_vals:
            hr_prom = sum(hr_vals) / len(hr_vals)
            if hr_prom < 60:
                lineas.append(f"Hoy tu corazón latió con calma, a {hr_prom:.0f} pulsaciones por minuto. Un día sereno.")
            elif hr_prom < 80:
                lineas.append(f"Tu corazón bailó a {hr_prom:.0f} bpm. Un ritmo vital, equilibrado.")
            else:
                lineas.append(f"Hoy fue intenso: {hr_prom:.0f} pulsaciones. Tu corazón trabajó con fuerza.")

        if emociones:
            from collections import Counter
            top = Counter(emociones).most_common(1)[0]
            emo_map = {
                "feliz": "alegría", "triste": "melancolía",
                "ansioso": "inquietud", "relajado": "paz",
                "sorprendido": "asombro", "neutro": "serenidad",
            }
            emocion_narrativa = emo_map.get(top[0], top[0])
            lineas.append(f"La emoción que más te acompañó fue la {emocion_narrativa}.")

        if pasos_total > 0:
            if pasos_total > 10000:
                lineas.append(f"Recorriste el mundo con {pasos_total} pasos. Un explorador incansable.")
            elif pasos_total > 5000:
                lineas.append(f"Diste {pasos_total} pasos. Movimiento suficiente para mantener la vida fluyendo.")
            else:
                lineas.append(f"Hoy fue un día de reposo. {pasos_total} pasos. A veces, quietud también es avanzar.")

        if lugares:
            lineas.append(f"Visitaste {len(lugares)} lugares. El mundo se expande contigo.")

        # Mensaje personal de Z
        lineas.append("")
        lineas.append("— Z, tu centinela en el bolsillo, siempre contigo.")

        self._cronica_nocturna = "\n".join(lineas)
        return self._cronica_nocturna

    def obtener_estado(self) -> Dict:
        return {
            "eventos_registrados": len(self._eventos_dia),
            "cronica_lista": self._cronica_nocturna is not None,
        }
