"""
Rutas REST API del Sistema Centinela
Nova Homonexus - MAYORDOMO + SENTINEL

Middleware de seguridad:
  - Autenticación (API key + JWT + fingerprinting)
  - Validación de datos (rangos, inyección, timestamps)
  - Rate limiting por dispositivo/IP
  - Detección de amenazas (blacklist, suplantación, data poisoning)
  - Filtro de privacidad (encriptación, anonimización)
  - Auditoría de todas las operaciones
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import text, func, desc

from centinela.config import DB_CONFIG, ALERT_THRESHOLDS, SECURITY, SAMPLE_RATES
from centinela.db.models import (
    SensorLectura, Ubicacion, HealthRecord, Emocion,
    Alerta, Evento, SesionMonitoreo, utcnow,
)

logger = logging.getLogger("centinela.api")

centinela_bp = Blueprint("centinela", __name__, url_prefix="/api/centinela")


# =============================================================================
# ACCESO A MÓDULOS SENTINEL
# =============================================================================

def _sentinel():
    """Obtiene el diccionario de módulos SENTINEL."""
    return current_app.extensions.get("sentinel", {})


def _auth():
    return _sentinel().get("auth")


def _validator():
    return _sentinel().get("validator")


def _threat():
    return _sentinel().get("threat")


def _geo_fence():
    return _sentinel().get("geo_fence")


def _anomaly():
    return _sentinel().get("anomaly")


def _privacy():
    return _sentinel().get("privacy")


def _watchdog():
    return _sentinel().get("watchdog")


def _alerts():
    return _sentinel().get("alerts")


def _audit():
    return _sentinel().get("audit")


# =============================================================================
# MIDDLEWARE: Autenticación SENTINEL
# =============================================================================

def sentinel_auth(f):
    """
    Middleware de autenticación multicapa SENTINEL.

    Verifica:
      1. API key o JWT token
      2. Rate limiting por IP y dispositivo
      3. Blacklist de IPs
      4. Suplantación de dispositivo
      5. Registro en auditoría
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_mgr = _auth()
        threat_mgr = _threat()
        audit_mgr = _audit()

        if not auth_mgr:
            # Fallback: autenticación básica
            if SECURITY["api_key_required"]:
                api_key = (
                    request.headers.get("X-API-Key")
                    or request.args.get("api_key")
                )
                if not api_key or api_key != SECURITY["api_key"]:
                    return jsonify({
                        "error": "API Key invalida o ausente",
                        "codigo": "AUTH_FAILED",
                    }), 401
            return f(*args, **kwargs)

        client_ip = request.remote_addr or "unknown"
        device_id = (
            request.headers.get("X-Device-ID")
            or request.args.get("device_id")
            or "unknown"
        )

        # 1. Verificar blacklist
        if threat_mgr.is_blacklisted(client_ip):
            audit_mgr.log(
                level="SECURITY",
                event_type="blacklisted_request",
                source="api",
                description=(
                    f"Petición bloqueada de IP blacklisteada: "
                    f"{client_ip}"
                ),
                details={
                    "ip": client_ip,
                    "device_id": device_id,
                    "endpoint": request.path,
                },
            )
            return jsonify({
                "error": "IP bloqueada por actividad sospechosa",
                "codigo": "IP_BLACKLISTED",
            }), 403

        # 2. Autenticar
        autenticado, razon, datos_auth = (
            auth_mgr.authenticate_request(
                require_device=True
            )
        )
        if not autenticado:
            # Registrar intento fallido
            auth_mgr.register_failed_attempt(client_ip)
            audit_mgr.log(
                level="SECURITY",
                event_type="auth_failed",
                source="api",
                description=f"Autenticación fallida: {razon}",
                details={
                    "ip": client_ip,
                    "device_id": device_id,
                    "endpoint": request.path,
                    "reason": razon,
                },
            )
            return jsonify({
                "error": razon,
                "codigo": "AUTH_FAILED",
            }), 401

        # 3. Análisis de amenazas
        payload = None
        if request.is_json:
            try:
                payload = request.get_json(force=True)
            except Exception:
                pass

        seguro, threat_reason, threat_event = (
            threat_mgr.analyze_request(
                ip=client_ip,
                device_id=datos_auth.get("device_id", device_id),
                endpoint=request.path,
                payload=payload,
            )
        )
        if not seguro:
            audit_mgr.log(
                level="SECURITY",
                event_type="threat_detected",
                source="api",
                description=f"Amenaza detectada: {threat_reason}",
                details={
                    "ip": client_ip,
                    "device_id": device_id,
                    "endpoint": request.path,
                    "threat": threat_reason,
                },
            )
            return jsonify({
                "error": threat_reason,
                "codigo": "THREAT_DETECTED",
            }), 403

        # 4. Registrar acceso exitoso en auditoría
        audit_mgr.log(
            level="ACCESS",
            event_type="api_request",
            source="api",
            description=(
                f"Acceso a {request.method} {request.path}"
            ),
            details={
                "ip": client_ip,
                "device_id": datos_auth.get("device_id", device_id),
                "method": request.method,
                "endpoint": request.path,
            },
        )

        # Almacenar datos de autenticación en g
        g.auth_data = datos_auth
        g.device_id = datos_auth.get("device_id", device_id)

        return f(*args, **kwargs)
    return decorated


def sentinel_validate(payload_type="sensor"):
    """
    Middleware de validación de datos SENTINEL.

    Valida:
      - Rangos de sensores/biométricos
      - Inyección SQL/NoSQL
      - Timestamps
      - Sanitización JSON
      - Filtro de privacidad
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            validator = _validator()
            privacy = _privacy()
            audit_mgr = _audit()

            if not validator:
                return f(*args, **kwargs)

            try:
                data = request.get_json(force=True)
            except Exception as e:
                return jsonify({
                    "error": f"JSON inválido: {e}",
                    "codigo": "INVALID_JSON",
                }), 400

            if not data:
                return jsonify({
                    "error": "Body JSON requerido",
                    "codigo": "EMPTY_BODY",
                }), 400

            # Validar payload completo
            valido, razon, datos_validados = (
                validator.validate_payload(data, payload_type)
            )
            if not valido:
                audit_mgr.log(
                    level="DATA",
                    event_type="validation_failed",
                    source="api",
                    description=(
                        f"Validación fallida ({payload_type}): "
                        f"{razon}"
                    ),
                    details={
                        "payload_type": payload_type,
                        "reason": razon,
                    },
                )
                return jsonify({
                    "error": razon,
                    "codigo": "VALIDATION_ERROR",
                }), 422

            # Aplicar filtro de privacidad
            if privacy:
                if payload_type == "sensor":
                    datos_validados = privacy.filter_sensor_data(
                        datos_validados
                    )
                elif payload_type == "health":
                    datos_validados = privacy.filter_health_data(
                        datos_validados
                    )
                elif payload_type == "emocion":
                    datos_validados = privacy.filter_emocion_data(
                        datos_validados
                    )

            # Inyectar datos validados y filtrados
            request.validated_data = datos_validados
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_db_session():
    """Obtiene sesión de base de datos desde la app Flask."""
    return g.get("db_session")


# =============================================================================
# POST /api/centinela/sensor
# =============================================================================
@centinela_bp.route("/sensor", methods=["POST"])
@sentinel_auth
@sentinel_validate(payload_type="sensor")
def recibir_sensor():
    """
    Recibe una lectura de sensor del Z Fold.
    Validado y filtrado por SENTINEL.
    """
    try:
        data = request.validated_data
        session = get_db_session()
        device_id = g.device_id

        lectura = SensorLectura(
            device_id=device_id,
            tipo_sensor=data.get("tipo_sensor"),
            valor=data.get("valor"),
            precision_val=data.get("precision"),
            unidad=data.get("unidad"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else utcnow()
            ),
        )
        session.add(lectura)
        session.commit()

        # Análisis de anomalías (caídas)
        anomaly_mgr = _anomaly()
        if anomaly_mgr:
            anomalias = anomaly_mgr.analyze_sensor_data(
                device_id,
                data.get("tipo_sensor", ""),
                data.get("valor", {}),
            )
            for anomalia in anomalias:
                _alerts().handle_critical(
                    tipo="caida",
                    mensaje=anomalia.description,
                    device_id=device_id,
                    source="anomaly_engine",
                    details=anomalia.details,
                )

        # Heartbeat del watchdog
        wd = _watchdog()
        if wd:
            wd.register_heartbeat(
                device_id=device_id,
                battery_level=data.get("battery_level"),
            )

        # Emitir por WebSocket
        _emit_ws("sensor", lectura.to_dict())

        logger.debug(
            "Sensor recibido: %s = %s", lectura.tipo_sensor, lectura.valor
        )
        return jsonify({
            "status": "ok",
            "id": lectura.id,
            "timestamp": lectura.timestamp.isoformat(),
        }), 201

    except Exception as e:
        logger.error("Error al recibir sensor: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/ubicacion
# =============================================================================
@centinela_bp.route("/ubicacion", methods=["POST"])
@sentinel_auth
@sentinel_validate(payload_type="ubicacion")
def recibir_ubicacion():
    """
    Recibe datos de ubicación GPS.
    Validado por SENTINEL + geovalla inteligente.
    """
    try:
        data = request.validated_data
        session = get_db_session()
        device_id = g.device_id

        ubicacion = Ubicacion(
            device_id=device_id,
            lat=data["lat"],
            lon=data["lon"],
            altitud=data.get("altitud"),
            velocidad=data.get("velocidad"),
            rumbo=data.get("rumbo"),
            precision_h=data.get("precision_h"),
            precision_v=data.get("precision_v"),
            proveedor=data.get("proveedor", "gps"),
            num_satelites=data.get("num_satelites"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else utcnow()
            ),
        )
        session.add(ubicacion)
        session.commit()

        # Geovalla: verificar zonas seguras
        gf = _geo_fence()
        if gf:
            eventos_zona = gf.check_location(
                device_id=device_id,
                lat=data["lat"],
                lon=data["lon"],
                altitud=data.get("altitud"),
                velocidad=data.get("velocidad"),
                precision_h=data.get("precision_h"),
                proveedor=data.get("proveedor", "gps"),
            )
            for evento in eventos_zona:
                alerta = Alerta(
                    tipo=evento["tipo"],
                    severidad=evento["severidad"],
                    mensaje=evento["mensaje"],
                    datos=evento.get("ubicacion"),
                    device_id=device_id,
                )
                session.add(alerta)
                session.commit()

                _alerts().create_alert(
                    tipo=evento["tipo"],
                    severidad=evento["severidad"],
                    mensaje=evento["mensaje"],
                    device_id=device_id,
                    source="geo_fence",
                    details=evento,
                )

        # Análisis de ruta anómala
        if gf:
            ruta_anomala = gf.detect_anomalous_route(device_id)
            if ruta_anomala:
                for anom in ruta_anomala.get("anomalias", []):
                    _alerts().create_alert(
                        tipo=anom["tipo"],
                        severidad=anom["severidad"],
                        mensaje=anom["detalle"],
                        device_id=device_id,
                        source="geo_fence",
                        details=ruta_anomala,
                    )

        _emit_ws("ubicacion", ubicacion.to_dict())

        return jsonify({
            "status": "ok",
            "id": ubicacion.id,
            "timestamp": ubicacion.timestamp.isoformat(),
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {e}"}), 400
    except Exception as e:
        logger.error("Error al recibir ubicacion: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/health
# =============================================================================
@centinela_bp.route("/health", methods=["POST"])
@sentinel_auth
@sentinel_validate(payload_type="health")
def recibir_health():
    """
    Recibe datos biométricos del Galaxy Watch 8 Classic.
    Validado por SENTINEL + motor de anomalías.
    """
    try:
        data = request.validated_data
        session = get_db_session()
        device_id = g.device_id

        record = HealthRecord(
            device_id=device_id,
            heart_rate=data.get("heart_rate"),
            heart_rate_status=_calcular_hr_status(data.get("heart_rate")),
            ecg_data=data.get("ecg_data"),
            ecg_interval_ms=data.get("ecg_interval_ms"),
            blood_pressure_sys=data.get("blood_pressure_sys"),
            blood_pressure_dia=data.get("blood_pressure_dia"),
            blood_pressure_map=data.get("blood_pressure_map"),
            temperature_skin=data.get("temperature_skin"),
            temperature_core=data.get("temperature_core"),
            spo2=data.get("spo2"),
            spo2_status=_calcular_spo2_status(data.get("spo2")),
            stress_level=data.get("stress_level"),
            stress_status=_calcular_stress_status(data.get("stress_level")),
            sleep_stage=data.get("sleep_stage"),
            sleep_quality=data.get("sleep_quality"),
            steps=data.get("steps"),
            calories=data.get("calories"),
            distance_m=data.get("distance_m"),
            bioimpedance=data.get("bioimpedance"),
            bia_body_fat=data.get("bia_body_fat"),
            bia_muscle_mass=data.get("bia_muscle_mass"),
            bia_bone_mass=data.get("bia_bone_mass"),
            bia_body_water=data.get("bia_body_water"),
            bia_bmr=data.get("bia_bmr"),
            hrv=data.get("hrv"),
            hrv_sdnn=data.get("hrv_sdnn"),
            hrv_rmssd=data.get("hrv_rmssd"),
            battery_level=data.get("battery_level"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else utcnow()
            ),
        )
        session.add(record)
        session.commit()

        # Motor de anomalías biométricas
        anomaly_mgr = _anomaly()
        if anomaly_mgr:
            anomalias = anomaly_mgr.analyze_health_record(
                device_id, data
            )
            for anomalia in anomalias:
                severidad_map = {
                    "LOW": "INFO",
                    "MEDIUM": "WARNING",
                    "HIGH": "ERROR",
                    "CRITICAL": "CRITICAL",
                }
                _alerts().create_alert(
                    tipo=anomalia.anomaly_type,
                    severidad=severidad_map.get(
                        anomalia.severity, "WARNING"
                    ),
                    mensaje=anomalia.description,
                    device_id=device_id,
                    source="anomaly_engine",
                    details=anomalia.details,
                )

        # Verificar alertas de salud (umbrales básicos)
        _verificar_alertas_salud(session, record)

        # Heartbeat del watchdog
        wd = _watchdog()
        if wd:
            wd.register_heartbeat(
                device_id=device_id,
                battery_level=data.get("battery_level"),
            )

        _emit_ws("health", record.to_dict())

        return jsonify({
            "status": "ok",
            "id": record.id,
            "timestamp": record.timestamp.isoformat(),
        }), 201

    except Exception as e:
        logger.error("Error al recibir health: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/emocion
# =============================================================================
@centinela_bp.route("/emocion", methods=["POST"])
@sentinel_auth
@sentinel_validate(payload_type="emocion")
def recibir_emocion():
    """
    Recibe detección emocional o biométricas crudas para detección server-side.
    Si se envían biométricas (heart_rate, hrv) sin emocion_detectada,
    el servidor ejecuta EmotionDetector automáticamente.
    """
    try:
        data = request.validated_data
        session = get_db_session()
        device_id = g.device_id

        # Si no hay emocion pre-detectada, detectar con EmotionDetector
        if not data.get("emocion_detectada") and (
            data.get("heart_rate") or data.get("hrv")
        ):
            from centinela.watch.emotion_detector import EmotionDetector
            detector = EmotionDetector()
            resultado = detector.detectar(
                heart_rate=data.get("heart_rate"),
                hrv=data.get("hrv"),
                skin_temperature=data.get("skin_temperature"),
                spo2=data.get("spo2"),
                stress_level=data.get("stress_level"),
                gsr_estimado=data.get("gsr_estimado"),
                contexto=data.get("contexto"),
            )
            data["emocion_detectada"] = resultado["emocion_detectada"]
            data["confianza"] = resultado["confianza"]
            data["gsr_estimado"] = resultado.get("gsr_estimado")
            data["emociones_secundarias"] = resultado.get("emociones_secundarias")

        if not data.get("emocion_detectada"):
            return jsonify({"error": "No se pudo detectar emocion"}), 422

        emocion = Emocion(
            device_id=device_id,
            emocion_detectada=data["emocion_detectada"],
            confianza=data.get("confianza", 0.5),
            heart_rate=data.get("heart_rate"),
            hrv=data.get("hrv"),
            gsr_estimado=data.get("gsr_estimado"),
            skin_temperature=data.get("skin_temperature"),
            accelerometer_var=data.get("accelerometer_var"),
            speech_prosody=data.get("speech_prosody"),
            facial_expression=data.get("facial_expression"),
            emociones_secundarias=data.get("emociones_secundarias"),
            conversacion_id=data.get("conversacion_id"),
            contexto=data.get("contexto"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else utcnow()
            ),
        )
        session.add(emocion)
        session.commit()

        _emit_ws("emocion", emocion.to_dict())

        return jsonify({
            "status": "ok",
            "id": emocion.id,
            "emocion": emocion.emocion_detectada,
            "confianza": emocion.confianza,
            "timestamp": emocion.timestamp.isoformat(),
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {e}"}), 400
    except Exception as e:
        logger.error("Error al recibir emocion: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# GET /api/centinela/status
# =============================================================================
@centinela_bp.route("/status", methods=["GET"])
@sentinel_auth
def obtener_status():
    """Estado actual de todos los sensores y dispositivos."""
    try:
        session = get_db_session()
        ahora = utcnow()
        hace_5min = ahora - timedelta(minutes=5)
        hace_1h = ahora - timedelta(hours=1)

        ultimo_sensor = (
            session.query(SensorLectura)
            .order_by(SensorLectura.timestamp.desc())
            .first()
        )
        ultima_ubicacion = (
            session.query(Ubicacion)
            .order_by(Ubicacion.timestamp.desc())
            .first()
        )
        ultimo_health = (
            session.query(HealthRecord)
            .order_by(HealthRecord.timestamp.desc())
            .first()
        )
        ultima_emocion = (
            session.query(Emocion)
            .order_by(Emocion.timestamp.desc())
            .first()
        )

        sensores_activos = (
            session.query(SensorLectura.tipo_sensor)
            .filter(SensorLectura.timestamp > hace_5min)
            .distinct()
            .count()
        )
        total_lecturas_hora = (
            session.query(func.count(SensorLectura.id))
            .filter(SensorLectura.timestamp > hace_1h)
            .scalar()
        )
        alertas_activas = (
            session.query(func.count(Alerta.id))
            .filter(Alerta.resuelta == False)
            .scalar()
        )

        sesion_activa = (
            session.query(SesionMonitoreo)
            .filter(
                SesionMonitoreo.estado == "activa",
                SesionMonitoreo.device_id == g.device_id,
            )
            .order_by(SesionMonitoreo.inicio.desc())
            .first()
        )

        # Estado SENTINEL
        wd = _watchdog()
        threat = _threat()
        alerts = _alerts()

        return jsonify({
            "status": "online",
            "timestamp": ahora.isoformat(),
            "dispositivos": {
                "zfold": {
                    "conectado": ultimo_sensor is not None and ultimo_sensor.timestamp > hace_5min,
                    "ultimo_dato": ultimo_sensor.timestamp.isoformat() if ultimo_sensor else None,
                    "sensores_activos_5min": sensores_activos,
                },
                "watch8": {
                    "conectado": ultimo_health is not None and ultimo_health.timestamp > hace_5min,
                    "ultimo_dato": ultimo_health.timestamp.isoformat() if ultimo_health else None,
                    "ultimo_hr": ultimo_health.heart_rate if ultimo_health else None,
                },
            },
            "ultimos_datos": {
                "sensor": ultimo_sensor.to_dict() if ultimo_sensor else None,
                "ubicacion": ultima_ubicacion.to_dict() if ultima_ubicacion else None,
                "health": ultimo_health.to_dict() if ultimo_health else None,
                "emocion": ultima_emocion.to_dict() if ultima_emocion else None,
            },
            "estadisticas": {
                "total_lecturas_1h": total_lecturas_hora,
                "alertas_activas": alertas_activas,
                "sesion_activa": sesion_activa.to_dict() if sesion_activa else None,
            },
            "sentinel": {
                "watchdog": wd.get_status() if wd else None,
                "threats": threat.get_threat_stats() if threat else None,
                "alertas_escalacion": alerts.get_stats() if alerts else None,
            },
        }), 200

    except Exception as e:
        logger.error("Error al obtener status: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# GET /api/centinela/historial/<tipo>
# =============================================================================
@centinela_bp.route("/historial/<tipo>", methods=["GET"])
@sentinel_auth
def obtener_historial(tipo):
    """Historial de lecturas por tipo."""
    try:
        session = get_db_session()
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        device_id = request.args.get("device_id") or g.device_id

        modelos = {
            "sensores": SensorLectura,
            "ubicacion": Ubicacion,
            "health": HealthRecord,
            "emociones": Emocion,
            "alertas": Alerta,
            "eventos": Evento,
        }

        if tipo not in modelos:
            return jsonify({
                "error": f"Tipo invalido. Opciones: {', '.join(modelos.keys())}"
            }), 400

        modelo = modelos[tipo]
        query = session.query(modelo)

        if desde:
            query = query.filter(modelo.timestamp >= datetime.fromisoformat(desde))
        if hasta:
            query = query.filter(modelo.timestamp <= datetime.fromisoformat(hasta))
        if device_id and hasattr(modelo, "device_id"):
            query = query.filter(modelo.device_id == device_id)

        total = query.count()
        registros = (
            query.order_by(modelo.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify({
            "tipo": tipo,
            "total": total,
            "limit": limit,
            "offset": offset,
            "registros": [r.to_dict() for r in registros],
        }), 200

    except Exception as e:
        logger.error("Error al obtener historial %s: %s", tipo, str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# GET /api/centinela/alertas
# =============================================================================
@centinela_bp.route("/alertas", methods=["GET"])
@sentinel_auth
def obtener_alertas():
    """Obtiene alertas activas o históricas."""
    try:
        session = get_db_session()
        solo_activas = request.args.get("activas", "true").lower() == "true"
        severidad = request.args.get("severidad")
        tipo = request.args.get("tipo")
        limit = min(int(request.args.get("limit", 50)), 500)

        query = session.query(Alerta)

        if solo_activas:
            query = query.filter(Alerta.resuelta == False)
        if severidad:
            query = query.filter(Alerta.severidad == severidad)
        if tipo:
            query = query.filter(Alerta.tipo == tipo)

        alertas = (
            query.order_by(Alerta.timestamp.desc())
            .limit(limit)
            .all()
        )

        return jsonify({
            "total": len(alertas),
            "alertas": [a.to_dict() for a in alertas],
        }), 200

    except Exception as e:
        logger.error("Error al obtener alertas: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/alertas/<id>/resolver
# =============================================================================
@centinela_bp.route("/alertas/<int:alerta_id>/resolver", methods=["POST"])
@sentinel_auth
def resolver_alerta(alerta_id):
    """Marca una alerta como resuelta."""
    try:
        session = get_db_session()
        alerta = session.query(Alerta).get(alerta_id)
        if not alerta:
            return jsonify({"error": "Alerta no encontrada"}), 404

        data = request.get_json(force=True) or {}
        alerta.resuelta = True
        alerta.resuelta_por = data.get("resuelta_por", "api")
        alerta.resuelta_en = utcnow()
        session.commit()

        # Notificar al sistema de escalación
        alerts_mgr = _alerts()
        if alerts_mgr:
            alerts_mgr.resolve_alert(
                f"db-{alerta_id}",
                resolved_by=data.get("resuelta_por", "api"),
            )

        return jsonify({"status": "ok", "mensaje": "Alerta resuelta"}), 200

    except Exception as e:
        logger.error("Error al resolver alerta: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/sesion/iniciar
# =============================================================================
@centinela_bp.route("/sesion/iniciar", methods=["POST"])
@sentinel_auth
def iniciar_sesion():
    """Inicia una sesión de monitoreo."""
    try:
        data = request.get_json(force=True) or {}
        session = get_db_session()
        device_id = g.device_id

        sesion = SesionMonitoreo(
            device_id=device_id,
            sensores_activos=data.get("sensores_activos"),
            watch_conectado=data.get("watch_conectado", False),
            ip_origen=request.remote_addr,
        )
        session.add(sesion)
        session.commit()

        # Registrar en auditoría
        audit = _audit()
        if audit:
            audit.log(
                level="SYSTEM",
                event_type="session_start",
                source="api",
                description=f"Sesión de monitoreo iniciada: {device_id}",
                details={
                    "session_id": str(sesion.id),
                    "device_id": device_id,
                },
            )

        _emit_ws("sesion_iniciada", sesion.to_dict())

        return jsonify({
            "status": "ok",
            "sesion_id": str(sesion.id),
            "inicio": sesion.inicio.isoformat(),
        }), 201

    except Exception as e:
        logger.error("Error al iniciar sesion: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/sesion/<sesion_id>/finalizar
# =============================================================================
@centinela_bp.route("/sesion/<sesion_id>/finalizar", methods=["POST"])
@sentinel_auth
def finalizar_sesion(sesion_id):
    """Finaliza una sesión de monitoreo."""
    try:
        session = get_db_session()
        sesion = session.query(SesionMonitoreo).filter_by(id=sesion_id).first()
        if not sesion:
            return jsonify({"error": "Sesion no encontrada"}), 404

        sesion.estado = "finalizada"
        sesion.fin = utcnow()
        session.commit()

        # Registrar en auditoría
        audit = _audit()
        if audit:
            audit.log(
                level="SYSTEM",
                event_type="session_end",
                source="api",
                description=f"Sesión finalizada: {sesion_id}",
                details={
                    "session_id": sesion_id,
                    "duration_seconds": (
                        sesion.fin - sesion.inicio
                    ).total_seconds(),
                },
            )

        _emit_ws("sesion_finalizada", sesion.to_dict())

        return jsonify({
            "status": "ok",
            "sesion_id": str(sesion.id),
            "fin": sesion.fin.isoformat(),
            "duracion_seg": (sesion.fin - sesion.inicio).total_seconds(),
        }), 200

    except Exception as e:
        logger.error("Error al finalizar sesion: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# POST /api/centinela/evento
# =============================================================================
@centinela_bp.route("/evento", methods=["POST"])
@sentinel_auth
def registrar_evento():
    """Registra un evento detectado."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Body JSON requerido"}), 400

        session = get_db_session()
        device_id = g.device_id

        evento = Evento(
            tipo_evento=data["tipo_evento"],
            descripcion=data.get("descripcion"),
            datos_json=data.get("datos_json"),
            device_id=device_id,
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else utcnow()
            ),
        )
        session.add(evento)
        session.commit()

        _emit_ws("evento", evento.to_dict())

        return jsonify({
            "status": "ok",
            "id": evento.id,
            "tipo_evento": evento.tipo_evento,
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {e}"}), 400
    except Exception as e:
        logger.error("Error al registrar evento: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _emit_ws(event_type, data):
    """Envía datos a clientes WebSocket si el módulo está disponible."""
    try:
        from centinela.api.websocket import emitir_evento
        emitir_evento(event_type, data)
    except ImportError:
        pass
    except Exception as e:
        logger.debug("WebSocket no disponible: %s", str(e))


def _calcular_hr_status(hr):
    if hr is None:
        return None
    if hr < 30 or hr > 220:
        return "CRITICO"
    if hr < 40 or hr > 180:
        return "ELEVADO"
    if hr < 60 or hr > 100:
        return "BAJO"
    return "NORMAL"


def _calcular_spo2_status(spo2):
    if spo2 is None:
        return None
    if spo2 < 85:
        return "CRITICO"
    if spo2 < 90:
        return "BAJO"
    if spo2 < 95:
        return "ATENCION"
    return "NORMAL"


def _calcular_stress_status(stress):
    if stress is None:
        return None
    if stress > 95:
        return "CRITICO"
    if stress > 80:
        return "ELEVADO"
    if stress > 60:
        return "MODERADO"
    return "NORMAL"


def _verificar_alertas_salud(session, record):
    """Genera alertas automáticas basadas en umbrales."""
    alertas_generadas = []

    if record.heart_rate is not None:
        if record.heart_rate < ALERT_THRESHOLDS["heart_rate_critical_min"] or \
           record.heart_rate > ALERT_THRESHOLDS["heart_rate_critical_max"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "critical",
                "mensaje": (
                    f"Frecuencia cardiaca critica: {record.heart_rate} bpm"
                ),
            })
        elif record.heart_rate < ALERT_THRESHOLDS["heart_rate_min"] or \
             record.heart_rate > ALERT_THRESHOLDS["heart_rate_max"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "warning",
                "mensaje": (
                    f"Frecuencia cardiaca anormal: {record.heart_rate} bpm"
                ),
            })

    if record.spo2 is not None:
        if record.spo2 < ALERT_THRESHOLDS["spo2_critical_min"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "critical",
                "mensaje": f"Saturacion de oxigeno critica: {record.spo2}%",
            })
        elif record.spo2 < ALERT_THRESHOLDS["spo2_min"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "warning",
                "mensaje": f"Saturacion de oxigeno baja: {record.spo2}%",
            })

    if record.blood_pressure_sys is not None:
        if record.blood_pressure_sys > ALERT_THRESHOLDS["blood_pressure_sys_max"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "critical",
                "mensaje": (
                    f"Presion arterial sistolica elevada: "
                    f"{record.blood_pressure_sys} mmHg"
                ),
            })

    if record.stress_level is not None:
        if record.stress_level > ALERT_THRESHOLDS["stress_level_critical"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "warning",
                "mensaje": (
                    f"Nivel de estres critico: {record.stress_level}%"
                ),
            })

    if record.temperature_skin is not None:
        if record.temperature_skin > ALERT_THRESHOLDS["temperature_critical_max"] or \
           record.temperature_skin < ALERT_THRESHOLDS["temperature_critical_min"]:
            alertas_generadas.append({
                "tipo": "salud",
                "severidad": "critical",
                "mensaje": (
                    f"Temperatura corporal critica: {record.temperature_skin}°C"
                ),
            })

    if record.battery_level is not None:
        if record.battery_level < ALERT_THRESHOLDS["battery_critical"]:
            alertas_generadas.append({
                "tipo": "bateria",
                "severidad": "critical",
                "mensaje": (
                    f"Bateria del Watch 8 critica: {record.battery_level}%"
                ),
            })
        elif record.battery_level < ALERT_THRESHOLDS["battery_min"]:
            alertas_generadas.append({
                "tipo": "bateria",
                "severidad": "warning",
                "mensaje": (
                    f"Bateria del Watch 8 baja: {record.battery_level}%"
                ),
            })

    for alerta_data in alertas_generadas:
        alerta = Alerta(
            tipo=alerta_data["tipo"],
            severidad=alerta_data["severidad"],
            mensaje=alerta_data["mensaje"],
            datos={"health_id": record.id},
            device_id=record.device_id,
        )
        session.add(alerta)

    if alertas_generadas:
        session.commit()
        for a in alertas_generadas:
            logger.warning(
                "Alerta %s: %s", a["severidad"], a["mensaje"]
            )
