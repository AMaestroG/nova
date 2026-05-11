"""
Puente de comunicación con Termux para el Sistema Centinela
Nova Homonexus - MAYORDOMO

Este módulo se ejecuta en el servidor y proporciona la interfaz
para recibir y procesar datos enviados desde Termux en el Z Fold.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from centinela.config import DEVICE_ZFOLD_ID

logger = logging.getLogger("centinela.sensor_bridge")

# Mapeo de nombres de sensores Android a nombres normalizados
SENSOR_MAP = {
    "android.sensor.accelerometer": "acelerometro",
    "android.sensor.gyroscope": "giroscopio",
    "android.sensor.magnetic_field": "magnetometro",
    "android.sensor.pressure": "barometro",
    "android.sensor.proximity": "proximidad",
    "android.sensor.light": "luz_ambiental",
    "android.sensor.fingerprint": "huella",
    "android.sensor.gps": "gps",
    "android.sensor.nfc": "nfc",
    "android.sensor.uwb": "uwb",
    "android.sensor.heart_rate": "ritmo_cardiaco",
    "android.sensor.step_counter": "contador_pasos",
    "android.sensor.gravity": "gravedad",
    "android.sensor.linear_acceleration": "aceleracion_lineal",
    "android.sensor.rotation_vector": "vector_rotacion",
    "android.sensor.humidity": "humedad",
    "android.sensor.ambient_temperature": "temperatura_ambiente",
    "android.sensor.game_rotation_vector": "vector_rotacion_juego",
    "android.sensor.geomagnetic_rotation_vector": "vector_rotacion_geomagnetico",
    "android.sensor.significant_motion": "movimiento_significativo",
    "android.sensor.step_detector": "detector_pasos",
    "android.sensor.tilt_detector": "detector_inclinacion",
    "android.sensor.wake_gesture": "gesto_despertar",
    "android.sensor.glance_gesture": "gesto_mirada",
    "android.sensor.pick_up_gesture": "gesto_levantar",
}

# Unidades por tipo de sensor
SENSOR_UNITS = {
    "acelerometro": "m/s²",
    "giroscopio": "rad/s",
    "magnetometro": "µT",
    "barometro": "hPa",
    "proximidad": "cm",
    "luz_ambiental": "lux",
    "gravedad": "m/s²",
    "aceleracion_lineal": "m/s²",
    "humedad": "%",
    "temperatura_ambiente": "°C",
    "ritmo_cardiaco": "bpm",
}


def normalizar_sensor(nombre_android: str) -> str:
    """Convierte nombre de sensor Android a nombre normalizado."""
    return SENSOR_MAP.get(nombre_android, nombre_android.lower().replace(" ", "_"))


def obtener_unidad(tipo_sensor: str) -> Optional[str]:
    """Obtiene la unidad de medida para un tipo de sensor."""
    return SENSOR_UNITS.get(tipo_sensor)


def procesar_lectura_sensor(
    datos: Dict[str, Any],
    device_id: str = DEVICE_ZFOLD_ID,
) -> Dict[str, Any]:
    """
    Procesa una lectura cruda de sensor desde Termux y la prepara
    para enviar al servidor.

    Args:
        datos: Diccionario con datos del sensor desde Termux
               Ej: {"sensor": "android.sensor.accelerometer",
                    "values": [0.1, -0.2, 9.8],
                    "precision": 0.01}

    Returns:
        Diccionario listo para POST a /api/centinela/sensor
    """
    tipo_original = datos.get("sensor", datos.get("tipo_sensor", "desconocido"))
    tipo_normalizado = normalizar_sensor(tipo_original)
    valores = datos.get("values", datos.get("valor", {}))

    # Convertir lista de valores a dict con nombres de ejes
    if isinstance(valores, list):
        if len(valores) == 1:
            valor_dict = {"valor": valores[0]}
        elif len(valores) == 2:
            valor_dict = {"x": valores[0], "y": valores[1]}
        elif len(valores) >= 3:
            valor_dict = {
                "x": valores[0],
                "y": valores[1],
                "z": valores[2],
            }
            if len(valores) > 3:
                valor_dict["w"] = valores[3]
        else:
            valor_dict = {"valor": valores}
    elif isinstance(valores, dict):
        valor_dict = valores
    else:
        valor_dict = {"valor": valores}

    return {
        "device_id": device_id,
        "tipo_sensor": tipo_normalizado,
        "valor": valor_dict,
        "precision": datos.get("precision", datos.get("precision_val")),
        "unidad": obtener_unidad(tipo_normalizado),
        "timestamp": (
            datos.get("timestamp")
            or datetime.now(timezone.utc).isoformat()
        ),
    }


def procesar_lote_sensores(
    lecturas: list,
    device_id: str = DEVICE_ZFOLD_ID,
) -> list:
    """Procesa un lote de lecturas de sensores."""
    return [
        procesar_lectura_sensor(lectura, device_id)
        for lectura in lecturas
    ]


def detectar_eventos(sensor_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Detecta eventos significativos basados en lecturas de sensores.

    Returns:
        Dict con tipo_evento y descripcion, o None si no hay evento.
    """
    tipo = sensor_data.get("tipo_sensor")
    valor = sensor_data.get("valor", {})

    if tipo == "acelerometro":
        # Detectar caída libre
        magnitud = (
            valor.get("x", 0) ** 2
            + valor.get("y", 0) ** 2
            + valor.get("z", 0) ** 2
        ) ** 0.5
        if magnitud < 0.5:
            return {
                "tipo_evento": "caida_libre",
                "descripcion": "Posible caida detectada",
                "datos_json": {"magnitud": magnitud, "valores": valor},
            }
        # Detectar movimiento brusco
        if magnitud > 25:
            return {
                "tipo_evento": "movimiento_brusco",
                "descripcion": "Movimiento repentino de alta aceleracion",
                "datos_json": {"magnitud": magnitud, "valores": valor},
            }

    elif tipo == "proximidad":
        cerca = valor.get("valor", valor.get("x", 100))
        if cerca is not None and cerca < 1.0:
            return {
                "tipo_evento": "proximidad_inmediata",
                "descripcion": "Objeto muy cerca del dispositivo",
                "datos_json": {"distancia_cm": cerca},
            }

    elif tipo == "luz_ambiental":
        lux = valor.get("valor", valor.get("x", 0))
        if lux < 5:
            return {
                "tipo_evento": "oscuridad",
                "descripcion": "Entorno con poca luz detectado",
                "datos_json": {"lux": lux},
            }

    elif tipo == "barometro":
        presion = valor.get("valor", valor.get("x", 1013))
        if presion and abs(presion - 1013) > 30:
            return {
                "tipo_evento": "cambio_presion",
                "descripcion": "Cambio significativo de presion atmosferica",
                "datos_json": {"presion_hPa": presion},
            }

    return None
