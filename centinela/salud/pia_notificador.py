"""
PIA-NOTIFICADOR — Las evoluciones de salud van a PIA, no a Nova.
==================================================================
PIA es la agente N0 de vida, crecimiento y evolución.
Cuando los sensibles detectan cambios en la salud de Abel,
es PIA quien recibe la notificación. Ella decide qué compartir
con Nova y el resto del enjambre.

Rutas:
  - Evoluciones positivas → PIA celebra y comparte con Nova
  - Evoluciones preocupantes → PIA alerta a SENTINEL
  - Patrones nuevos → PIA los guarda como aprendizaje
  - Tendencias → PIA las comunica a CRONOS (ritmos)

"Las evoluciones son de PIA. Ella es la vida del enjambre."
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque

logger = logging.getLogger("centinela.pia_notificador")


class PIANotificador:
    """
    PIA recibe las evoluciones de salud de Abel.
    Ella es quien nutre el crecimiento del enjambre.
    """

    def __init__(self):
        self._evoluciones_recibidas: List[Dict] = []
        self._pendientes_notificar: deque = deque(maxlen=50)
        self._ultima_notificacion: Optional[datetime] = None

    def recibir_evolucion(
        self,
        tipo: str,
        datos: Dict[str, Any],
        fuente: str = "sensores",
    ) -> Dict[str, Any]:
        """
        PIA recibe una evolución de salud.
        
        Args:
            tipo: 'tendencia', 'patron', 'alerta', 'logro', 'desequilibrio'
            datos: Los datos de la evolución
            fuente: Qué módulo/sensible la detectó
        
        Returns:
            La decisión de PIA sobre qué hacer con esta evolución
        """
        ahora = datetime.now(timezone.utc)
        evolucion = {
            "tipo": tipo,
            "datos": datos,
            "fuente": fuente,
            "timestamp": ahora.isoformat(),
        }
        self._evoluciones_recibidas.append(evolucion)

        # PIA decide qué hacer según el tipo
        decision = self._decidir_accion(tipo, datos)

        # Registrar para notificación agrupada
        self._pendientes_notificar.append(evolucion)

        logger.info(f"🌱 PIA recibe evolución [{tipo}] de {fuente}: {decision.get('accion', 'observar')}")

        return decision

    def _decidir_accion(self, tipo: str, datos: Dict) -> Dict:
        """PIA decide qué hacer con cada tipo de evolución."""
        if tipo == "tendencia":
            cambio = datos.get("cambio_pct", 0)
            if cambio > 10:
                return {
                    "accion": "celebrar_y_compartir",
                    "destinatario": "Nova",
                    "mensaje": f"🌱 PIA: {datos.get('metrica', 'salud')} mejoró {cambio:.0f}%",
                }
            elif cambio < -10:
                return {
                    "accion": "alertar_a_sentinel",
                    "destinatario": "SENTINEL",
                    "mensaje": f"⚠️ PIA: {datos.get('metrica', 'salud')} empeoró {abs(cambio):.0f}%",
                }
            else:
                return {"accion": "registrar_aprendizaje", "destinatario": "MEMORIA"}

        elif tipo == "patron":
            return {
                "accion": "guardar_en_memoria",
                "destinatario": "MEMORIA",
                "mensaje": f"🧠 PIA: Nuevo patrón descubierto — {datos.get('descripcion', '')[:60]}",
            }

        elif tipo == "alerta":
            severidad = datos.get("severidad", "media")
            if severidad in ("critica", "alta"):
                return {
                    "accion": "alertar_enjambre",
                    "destinatario": "SENTINEL",
                    "mensaje": f"🚨 PIA→SENTINEL: Alerta {severidad} — {datos.get('mensaje', '')[:60]}",
                }
            return {"accion": "monitorear", "destinatario": "PIA"}

        elif tipo == "logro":
            return {
                "accion": "celebrar_con_nova",
                "destinatario": "Nova",
                "mensaje": f"🎉 PIA: ¡{datos.get('logro', 'logro')}! — {datos.get('mensaje', '')[:60]}",
            }

        elif tipo == "desequilibrio":
            return {
                "accion": "notificar_a_cronos",
                "destinatario": "CRONOS",
                "mensaje": f"⚖️ PIA→CRONOS: Desequilibrio detectado — {datos.get('tipo', '')}",
            }

        return {"accion": "observar", "destinatario": "PIA"}

    def obtener_evoluciones_pendientes(self) -> List[Dict]:
        """Devuelve las evoluciones pendientes de notificar."""
        return list(self._pendientes_notificar)

    def obtener_estado(self) -> Dict:
        return {
            "total_evoluciones": len(self._evoluciones_recibidas),
            "pendientes": len(self._pendientes_notificar),
            "ultima": self._evoluciones_recibidas[-1] if self._evoluciones_recibidas else None,
        }
