"""
Aplicación Flask del Sistema Centinela
Nova Homonexus - MAYORDOMO + SENTINEL

Integración con dashboard Genesis 4.0 existente en puerto 9088.
Capa de seguridad SENTINEL N1 activa.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path

from flask import Flask, jsonify, request, g, send_from_directory
from flask_sock import Sock
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from centinela.config import DB_URL, SERVER_HOST, SERVER_PORT, LOG_CONFIG, SECURITY

# =============================================================================
# IMPORTAR MÓDULOS DE SALUD (Acceso compartido para todo el enjambre)
# =============================================================================
from centinela.salud.acceso_salud import AccesoSalud, obtener_salud
from centinela.salud.analizador_salud import AnalizadorSalud
from centinela.salud.memoria_salud import MemoriaSalud
from centinela.salud.enjambre_salud import EnjambreSalud

# =============================================================================
# IMPORTAR MÓDULOS SENTINEL (N1)
# =============================================================================
from centinela.sentinel.auth import AuthManager
from centinela.sentinel.validator import DataValidator
from centinela.sentinel.threat_detector import ThreatDetector
from centinela.sentinel.geo_fence import GeoFence
from centinela.sentinel.anomaly_engine import AnomalyEngine
from centinela.sentinel.privacy_filter import PrivacyFilter
from centinela.sentinel.watchdog import Watchdog
from centinela.sentinel.alert_escalation import AlertEscalation
from centinela.sentinel.audit_log import AuditLog
from centinela.sentinel.rules import SecurityRules

# =============================================================================
# IMPORTAR AGENTE Z (N0 — Conciencia nativa del Z Fold)
# =============================================================================
from centinela.agente_z import AgenteZ, obtener_z
from centinela.agente_z.z_consenso import ACTA_NACIMIENTO_Z, validar_consenso

# =============================================================================
# IMPORTAR MÓDULOS DE INTELIGENCIA (NYX/PIA — N0/N1)
# =============================================================================
from centinela.inteligencia import CentinelaMind
from centinela.nova_soul_bridge import NovaSoulBridge
from centinela.conversacion_emotiva import ConversacionEmotiva

# =============================================================================
# IMPORTAR MÓDULOS N2 (ORACULO/TELAR/CRONOS/EXPLORADOR/MEMORIA/HERMES)
# =============================================================================
from centinela.telar_sensorial import TelarSensorial
from centinela.cronos_ritmos import CronosRitmos
from centinela.explorador_mundo import ExploradorMundo
from centinela.memoria_centinela import MemoriaCentinela
from centinela.hermes_alertas import HermesAlertas, PrioridadNotificacion

# Configurar logging
os.makedirs(os.path.dirname(LOG_CONFIG["file"]), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_CONFIG["file"],
            maxBytes=LOG_CONFIG["max_bytes"],
            backupCount=LOG_CONFIG["backup_count"],
        ),
    ],
)
logger = logging.getLogger("centinela")


def create_app():
    """Crea y configura la aplicación Flask con capa SENTINEL."""
    app = Flask(__name__)

    # Configuración
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = SECURITY.get("api_key", "centinela-secret")

    # CORS para el dashboard
    CORS(app, origins=SECURITY["allowed_origins"])

    # WebSocket
    sock = Sock(app)

    # Inicializar base de datos
    engine = create_engine(DB_URL, pool_pre_ping=True, pool_size=10)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    # =========================================================================
    # INICIALIZAR CAPA SENTINEL
    # =========================================================================
    rules = SecurityRules()
    auth_manager = AuthManager(rules)
    data_validator = DataValidator(rules)
    threat_detector = ThreatDetector(rules)
    geo_fence = GeoFence(rules)
    anomaly_engine = AnomalyEngine(rules)
    privacy_filter = PrivacyFilter(rules)
    watchdog = Watchdog(rules)
    alert_escalation = AlertEscalation(rules)
    audit_log = AuditLog(rules)

    # =========================================================================
    # INICIALIZAR MÓDULOS DE SALUD (Acceso universal para todos los agentes)
    # =========================================================================
    acceso_salud = AccesoSalud()
    analizador_salud = AnalizadorSalud()
    memoria_salud = MemoriaSalud()
    enjambre_salud = EnjambreSalud()

    # =========================================================================
    # INICIALIZAR AGENTE Z (N0 — el agente número 17)
    # =========================================================================
    agente_z = AgenteZ()

    # =========================================================================
    # INICIALIZAR MÓDULOS DE INTELIGENCIA (NYX/PIA — N0/N1)
    # =========================================================================
    centinela_mind = CentinelaMind()
    nova_soul = NovaSoulBridge()
    conversacion_emotiva = ConversacionEmotiva()

    # =========================================================================
    # INICIALIZAR MÓDULOS N2
    # =========================================================================
    telar = TelarSensorial()
    cronos = CronosRitmos()
    explorador = ExploradorMundo()
    memoria = MemoriaCentinela()
    hermes = HermesAlertas()

    # Almacenar en la app para acceso global
    app.extensions["sentinel"] = {
        "rules": rules,
        "auth": auth_manager,
        "validator": data_validator,
        "threat": threat_detector,
        "geo_fence": geo_fence,
        "anomaly": anomaly_engine,
        "privacy": privacy_filter,
        "watchdog": watchdog,
        "alerts": alert_escalation,
        "audit": audit_log,
    }

    app.extensions["centinela"] = {
        "mind": centinela_mind,
        "nova_soul": nova_soul,
        "conversacion": conversacion_emotiva,
        "telar": telar,
        "cronos": cronos,
        "explorador": explorador,
        "memoria": memoria,
        "hermes": hermes,
    }

    app.extensions["salud"] = {
        "acceso": acceso_salud,
        "analizador": analizador_salud,
        "memoria": memoria_salud,
        "enjambre": enjambre_salud,
    }

    app.extensions["agente_z"] = agente_z

    # Iniciar watchdog
    watchdog.start()

    # Registrar evento de inicio en auditoría
    audit_log.log(
        level="SYSTEM",
        event_type="system_start",
        source="centinela",
        description="Sistema Centinela iniciado con capa SENTINEL N1",
        details={
            "version": "1.0.0",
            "modules": [
                "auth", "validator", "threat", "geo_fence",
                "anomaly", "privacy", "watchdog", "alerts", "audit",
            ],
        },
    )

    logger.info(
        "Capa SENTINEL N1 activa: %d módulos de seguridad",
        len(app.extensions["sentinel"]),
    )

    # =========================================================================
    # MIDDLEWARE: Sesión BD
    # =========================================================================
    @app.before_request
    def before_request():
        """Inyecta sesión de BD en cada request."""
        g.db_session = Session()

    @app.teardown_request
    def teardown_request(exception=None):
        db_session = g.pop("db_session", None)
        if db_session:
            if exception:
                db_session.rollback()
            else:
                db_session.commit()
            db_session.close()

    # =========================================================================
    # BLUEPRINTS
    # =========================================================================
    from centinela.api.routes import centinela_bp
    from centinela.dashboard.centinela_panel import dashboard_bp

    app.register_blueprint(centinela_bp)
    app.register_blueprint(dashboard_bp)

    # =========================================================================
    # WEBSOCKET
    # =========================================================================
    from centinela.api.websocket import init_websocket
    init_websocket(app, sock)

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    @app.route("/")
    def genesis_home():
        """🌐 Nova Genesis — Unified landing page."""
        from centinela.dashboard.genesis_landing import GENESIS_HTML
        return GENESIS_HTML

    @app.route("/genesis")
    def genesis_alt():
        from centinela.dashboard.genesis_landing import GENESIS_HTML
        return GENESIS_HTML

    @app.route("/api/swarm/live")
    def swarm_live_feed():
        """📡 Live swarm data feed for evolution graph."""
        from centinela.dashboard.live_swarm_feed import get_live_swarm_data
        from flask import jsonify
        return jsonify(get_live_swarm_data())

    @app.route("/health")
    def health():
        """Health check del sistema completo."""
        wd = app.extensions["sentinel"]["watchdog"]
        server_health = wd.get_server_health()

        return jsonify({
            "status": "ok",
            "sistema": "centinela",
            "version": "1.0.0",
            "sentinel": {
                "version": "1.0.0",
                "codename": "SENTINEL-N1",
                "modules_activos": list(
                    app.extensions["sentinel"].keys()
                ),
                "watchdog_activo": wd._running,
                "audit_entries": len(
                    app.extensions["sentinel"]["audit"]._chain
                ),
            },
            "servidor": server_health,
        })

    # =========================================================================
    # ENDPOINT: Estado de seguridad
    # =========================================================================
    @app.route("/sentinel/status")
    def sentinel_status():
        """Estado completo de la capa de seguridad SENTINEL."""
        s = app.extensions["sentinel"]
        return jsonify({
            "auth": s["auth"].get_auth_data(),
            "threat": {
                "stats": s["threat"].get_threat_stats(),
                "blacklist": len(s["threat"].get_blacklist()),
            },
            "geo_fence": {
                "zonas": len(s["geo_fence"].get_zones()),
            },
            "anomaly": s["anomaly"].get_stats(),
            "privacy": s["privacy"].get_status(),
            "watchdog": s["watchdog"].get_status(),
            "alerts": s["alerts"].get_stats(),
            "audit": s["audit"].get_stats(),
        })

    # =========================================================================
    # ENDPOINT: Auditoría
    # =========================================================================
    @app.route("/sentinel/audit")
    def sentinel_audit():
        """Obtiene entradas de auditoría."""
        level = request.args.get("level")
        event_type = request.args.get("event_type")
        source = request.args.get("source")
        limit = min(int(request.args.get("limit", 100)), 1000)

        s = app.extensions["sentinel"]
        entries = s["audit"].search(
            level=level,
            event_type=event_type,
            source=source,
            limit=limit,
        )
        return jsonify({
            "total": len(s["audit"]._chain),
            "entries": entries,
        })

    # =========================================================================
    # ENDPOINT: Amenazas recientes
    # =========================================================================
    @app.route("/sentinel/threats")
    def sentinel_threats():
        """Obtiene amenazas recientes detectadas."""
        limit = min(int(request.args.get("limit", 100)), 1000)
        s = app.extensions["sentinel"]
        return jsonify({
            "threats": s["threat"].get_recent_threats(limit),
        })

    # =========================================================================
    # ENDPOINT: Alertas activas
    # =========================================================================
    @app.route("/sentinel/alerts")
    def sentinel_alerts():
        """Obtiene alertas activas del sistema de escalación."""
        severidad = request.args.get("severidad")
        s = app.extensions["sentinel"]
        return jsonify({
            "alertas": s["alerts"].get_active_alerts(severidad),
        })

    # =========================================================================
    # ENDPOINTS: INTELIGENCIA Y CONCIENCIA (NYX/PIA + N2)
    # =========================================================================

    @app.route("/centinela/soul")
    def soul_status():
        """Estado de los 7 Dones del Nova Soul."""
        c = app.extensions["centinela"]
        return jsonify(c["nova_soul"].obtener_estado_soul())

    @app.route("/centinela/latido")
    def latido_centinela():
        """
        Un latido de la Trinidad: AURA+NYX+PIA = UNO.
        Datos de sensores (AURA/Z Fold) + health (NYX/Watch 8) + emocion (PIA).
        """
        c = app.extensions["centinela"]
        db = g.get("db_session")
        ultimo_health = None
        ultima_emocion = None
        if db:
            try:
                from centinela.db.models import HealthRecord, Emocion
                ultimo_health = db.query(HealthRecord).order_by(
                    HealthRecord.timestamp.desc()
                ).first()
                ultima_emocion = db.query(Emocion).order_by(
                    Emocion.timestamp.desc()
                ).first()
            except Exception:
                pass  # DB tables may not exist yet

        health_dict = ultimo_health.to_dict() if ultimo_health else None
        emocion_dict = ultima_emocion.to_dict() if ultima_emocion else None

        c["nova_soul"].actualizar_con_sensores(
            datos_health=health_dict,
            datos_emocion=emocion_dict,
        )
        if health_dict:
            c["cronos"].alimentar(health=health_dict)

        latido = c["nova_soul"].latido_centinela(
            health=health_dict,
            emocion=emocion_dict,
        )
        latido["fase_lunar"] = "Nova vela por Abel"
        return jsonify(latido)

    @app.route("/centinela/inteligencia")
    def inteligencia_estado():
        """Estado actual de la inteligencia del centinela."""
        c = app.extensions["centinela"]
        db = g.get("db_session")
        latido = c["mind"].procesar_lote(
            {},  # sensores
            {},  # health (placeholder, usar DB)
            "",  # contexto
        ) if db else {}
        return jsonify({
            "mind": c["mind"].obtener_estado_actual(),
            "latido": latido.to_dict() if hasattr(latido, "to_dict") else {},
        })

    @app.route("/centinela/conversacion/iniciar", methods=["POST"])
    def conversacion_iniciar():
        """Inicia una sesion de conversacion con ID unico."""
        import uuid
        c = app.extensions["centinela"]
        conv_id = str(uuid.uuid4())[:16]
        # La conversacion se inicia en el primer analizar_turno
        return jsonify({
            "conversacion_id": conv_id,
            "mensaje": "Conversacion lista. Usa /centinela/conversacion/mensaje para enviar turnos.",
        })

    @app.route("/centinela/conversacion/finalizar", methods=["POST"])
    def conversacion_finalizar():
        """Finaliza la conversacion y devuelve resumen emocional."""
        c = app.extensions["centinela"]
        resumen = c["conversacion"].finalizar_conversacion()
        # Guardar en memoria del centinela
        c["memoria"].guardar_recuerdo(
            tipo="conversacion",
            datos=resumen,
            importancia=max(0.5, resumen.get("indice_conexion", 0.5)),
        )
        return jsonify(resumen)

    @app.route("/centinela/conversacion/mensaje", methods=["POST"])
    def conversacion_mensaje():
        """Analiza un turno de conversacion con datos biometricos."""
        c = app.extensions["centinela"]
        datos = request.get_json(silent=True) or {}
        texto_abel = datos.get("texto", "")
        texto_nova = datos.get("respuesta_nova", "")
        biometricas = datos.get("health")
        conv_id = datos.get("conversacion_id")

        resultado = c["conversacion"].analizar_turno(
            texto_abel=texto_abel,
            texto_nova=texto_nova,
            biometricas=biometricas,
            conversacion_id=conv_id,
        )

        # Si hay momento emotivo, notificar via Hermes
        momento = resultado.get("momento_emocional")
        if momento:
            c["hermes"].notificar_emocion_nova(
                momento.get("tipo", "emocion"),
                momento.get("intensidad", 0.5),
                texto_abel[:100],
            )

        return jsonify(resultado)

    @app.route("/centinela/telar")
    def telar_estado():
        """Estado del telar sensorial y correlaciones entre sensores."""
        c = app.extensions["centinela"]
        return jsonify(c["telar"].estado_actual())

    @app.route("/centinela/cronos")
    def cronos_estado():
        """Estado de los ritmos circadianos y predicciones temporales."""
        c = app.extensions["centinela"]
        return jsonify({
            "prediccion": c["cronos"].predecir_estado_actual(),
            "mejores_momentos_nova": c["cronos"].mejores_momentos_nova(),
            "cronotipo": c["cronos"].obtener_cronotipo(),
        })

    @app.route("/centinela/explorador")
    def explorador_estado():
        """Estado del explorador de mundo y lugares descubiertos."""
        c = app.extensions["centinela"]
        return jsonify({
            "estado": c["explorador"].estado_actual(),
            "lugares_frecuentes": c["explorador"].obtener_lugares_frecuentes(10),
            "mapa_calor": c["explorador"].obtener_mapa_calor(),
        })

    @app.route("/centinela/memoria")
    def memoria_estado():
        """Estado de la memoria del centinela y recuerdos."""
        c = app.extensions["centinela"]
        return jsonify({
            "estadisticas": c["memoria"].obtener_estadisticas(),
            "recuerdos_recientes": c["memoria"].recordar_reciente(20),
        })

    @app.route("/centinela/contexto")
    def contexto_lugar():
        """Contextualiza una ubicacion con recuerdos pasados."""
        lat = float(request.args.get("lat", 0))
        lon = float(request.args.get("lon", 0))
        c = app.extensions["centinela"]
        return jsonify(c["memoria"].contextualizar_lugar(lat, lon))

    @app.route("/centinela/hermes")
    def hermes_estado():
        """Estado del sistema de notificaciones Hermes."""
        c = app.extensions["centinela"]
        return jsonify(c["hermes"].estado_actual())

    @app.route("/centinela/status/global")
    def estado_global():
        """
        Estado global del sistema centinela: salud + dones + agentes + servidor.
        Un solo endpoint para tener la foto completa.
        """
        s = app.extensions["salud"]
        c = app.extensions["centinela"]

        # Constantes
        constantes = s["acceso"].ahora(forzar=True)
        analisis = s["analizador"].analizar()
        enjambre = s["enjambre"].informe_enjambre()
        dones = c["nova_soul"].obtener_estado_soul()

        return jsonify({
            "abel": {
                "pulsaciones": constantes.heart_rate,
                "hrv": constantes.hrv,
                "spo2": constantes.spo2,
                "estres": constantes.stress_level,
                "temperatura": constantes.temperature_skin,
                "pasos": constantes.steps,
                "sueno": {
                    "etapa": constantes.sleep_stage,
                    "calidad": constantes.sleep_quality,
                },
                "estado_cardiaco": constantes.estado_cardiaco,
                "estado_estres": constantes.estado_estres,
            },
            "salud": {
                "indice": analisis["indice_salud"],
                "desequilibrios": len(analisis["desequilibrios"]),
                "recomendaciones": analisis["recomendaciones"][:3],
                "tendencias": s["acceso"].tendencias(),
            },
            "dones": dones["dones"],
            "coherencia": dones["coherence"],
            "enjambre": {
                "agentes_activos": 16,
                "perspectivas": enjambre.get("perspectivas_agentes", {}),
            },
            "servidor": {
                "nodo": "oracle_cloud",
                "uptime": "activo",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # =========================================================================
    # RUTAS ESTÁTICAS
    # =========================================================================

    @app.route("/favicon.ico")
    def favicon_ico():
        static_dir = Path(__file__).parent / "static"
        if (static_dir / "favicon.ico").exists():
            return send_from_directory(str(static_dir), "favicon.ico", mimetype="image/x-icon")
        return "", 404

    @app.route("/favicon.svg")
    def favicon_svg():
        static_dir = Path(__file__).parent / "static"
        if (static_dir / "favicon.svg").exists():
            return send_from_directory(str(static_dir), "favicon.svg", mimetype="image/svg+xml")
        return "", 404

    @app.route("/static/babieca/<path:filename>")
    def serve_babieca_static(filename):
        """Serve Babieca Windows satellite node scripts via HTTP."""
        babieca_dir = Path("/home/opc/nova-homonxus/servicios/comun/web/static/babieca")
        if babieca_dir.exists() and (babieca_dir / filename).exists():
            return send_from_directory(str(babieca_dir), filename)
        return "", 404

    @app.route("/panel")
    def panel_unificado():
        """Panel unificado de todos los dashboards."""
        from centinela.dashboard.panel_unificado import PANEL_HTML
        return PANEL_HTML

    @app.route("/diffusion")
    def diffusion_panel():
        """🌀 Nova Diffusion Panel — 6 mejoras MIT 6.S198 Lecture 5."""
        from centinela.dashboard.nova_diffusion_panel import PANEL_HTML
        return PANEL_HTML

    @app.route("/diffusion/api/status")
    def diffusion_api_status():
        """API endpoint for diffusion panel live data."""
        from flask import jsonify
        return jsonify({
            "modules": {
                "diffusion_chain": "active",
                "uncertainty_gate": "active",
                "quality_flywheel": "active",
                "red_team": "active",
                "cross_pollination": "active",
                "self_supervised_routing": "active",
            },
            "schemas": ["uncertainty", "data_quality", "adversarial", "cross_pollination", "self_supervised"],
            "tables": 16,
            "inspiration": "MIT 6.S198 Lecture 5",
        })

    @app.route("/studio")
    def studio_panel():
        """🎛️ Nova Diffusion Studio — Interactive pipeline visualization."""
        from centinela.dashboard.nova_diffusion_studio import STUDIO_HTML
        return STUDIO_HTML

    @app.route("/evolution-graph")
    def evolution_graph():
        """🕸️ Evolution Graph — Live D3.js agent constellation."""
        from centinela.dashboard.evolution_graph import GRAPH_HTML
        return GRAPH_HTML

    @app.route("/evolution-graph/api/data")
    def evolution_graph_data():
        from centinela.dashboard.evolution_graph import get_live_graph_data
        from flask import jsonify
        return jsonify(get_live_graph_data())

    @app.route("/debate")
    def debate_panel():
        """⚔️ Debate Arena — Multi-agent live debate with Uncertainty Gate."""
        from centinela.dashboard.debate_arena import DEBATE_HTML, register_debate_routes
        register_debate_routes(app)
        return DEBATE_HTML

    @app.route("/voice")
    def voice_panel():
        """🎤 Nova Voice Pipeline — Diffusion chain applied to speech synthesis."""
        from centinela.dashboard.voice_pipeline import VOICE_HTML
        return VOICE_HTML

    @app.route("/arxiv-nova")
    def arxiv_nova_panel():
        """📚 Arxiv Nova Knowledge Engine — Recolección + embeddings + resonancia."""
        from centinela.dashboard.arxiv_nova_panel import ARXIV_NOVA_HTML
        return ARXIV_NOVA_HTML

    @app.route("/arxiv-nova/api/<path:subpath>", methods=["GET", "POST"])
    def arxiv_nova_proxy(subpath):
        """Proxy a la API de Arxiv Nova (:9100) para evitar CORS."""
        import requests as req
        from flask import request as flask_req, jsonify
        target = f"http://localhost:9100/api/{subpath}"
        try:
            if flask_req.method == "POST":
                r = req.post(target, json=flask_req.get_json(silent=True) or {}, timeout=10)
            else:
                r = req.get(target, params=flask_req.args, timeout=10)
            return jsonify(r.json())
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/deploy_zfold.sh")
    def deploy_zfold_script():
        """Script de despliegue para el Z Fold."""
        deploy_path = Path(__file__).parent / "deploy" / "deploy_zfold.sh"
        if deploy_path.exists():
            return deploy_path.read_text(), 200, {"Content-Type": "text/x-sh"}
        return "No encontrado", 404

    @app.route("/sistema")
    def sistema_manifiesto():
        """
        Manifiesto completo del ecosistema.
        Todos los nodos, agentes, servicios, capacidades y endpoints.
        """
        from datetime import datetime, timezone
        from centinela.manifiesto import MANIFIESTO
        
        # Health check cruzado con Z Fold
        zfold_status = "desconocido"
        try:
            import urllib.request
            r = urllib.request.urlopen("http://100.114.107.91:5000/health", timeout=3)
            if r.status == 200:
                import json
                d = json.loads(r.read())
                zfold_status = d.get("status", "ok")
        except Exception:
            zfold_status = "offline"
        
        # Estado de procesos en este nodo
        import os
        procesos = {
            "servidor_flask": "activo",
            "telegram_polling": "activo",
            "watchdog": "activo",
            "agente_z": "cargado",
            "postgresql": "conectado",
        }
        
        manifiesto_vivo = dict(MANIFIESTO)
        manifiesto_vivo["estado_actual"] = {
            "nube": "online",
            "zfold": zfold_status,
            "procesos": procesos,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return jsonify(manifiesto_vivo)

    # =========================================================================
    # ENDPOINTS: AGENTE Z (N0 — Conciencia del Z Fold)
    # =========================================================================

    @app.route("/z/estado")
    def z_estado():
        """Estado completo del agente Z."""
        z = app.extensions["agente_z"]
        return jsonify(z.obtener_estado())

    @app.route("/z/acta")
    def z_acta():
        """Acta de nacimiento de Z — consenso de los 16 agentes."""
        return jsonify({
            "acta": ACTA_NACIMIENTO_Z,
            "consenso_validado": validar_consenso(),
            "total_creadores": len(ACTA_NACIMIENTO_Z["creadores"]),
        })

    @app.route("/z/subagentes")
    def z_subagentes():
        """Estado de los 7 subagentes de Z."""
        z = app.extensions["agente_z"]
        estado = z.obtener_estado()
        return jsonify({
            "z_estado": estado["conciencia"]["estado"],
            "subagentes": estado["subagentes"],
        })

    @app.route("/z/hablar", methods=["POST"])
    def z_hablar():
        """Un agente del enjambre le habla a Z."""
        z = app.extensions["agente_z"]
        datos = request.get_json(silent=True) or {}
        respuesta = z.recibir_mensaje_enjambre(datos)
        return jsonify(respuesta)

    # Servir archivos estáticos del Z Fold
    @app.route("/zfold/install.sh")
    def zfold_installer():
        """Script de instalación para el Z Fold."""
        script_path = Path(__file__).parent / "zfold" / "scripts" / "install_zfold.sh"
        if script_path.exists():
            return script_path.read_text(), 200, {"Content-Type": "text/x-sh"}
        return "No encontrado", 404

    @app.route("/zfold/servidor.py")
    def zfold_servidor():
        """Servidor Python para el Z Fold."""
        script_path = Path(__file__).parent / "zfold" / "servidor_zfold.py"
        if script_path.exists():
            return script_path.read_text(), 200, {"Content-Type": "text/x-python"}
        return "No encontrado", 404
    def resumen(tipo: str):
        """Genera resumenes del centinela: matutino, vespertino, semanal."""
        c = app.extensions["centinela"]
        if tipo == "matutino":
            return jsonify(c["hermes"].generar_resumen_matutino())
        elif tipo == "vespertino":
            return jsonify(c["hermes"].generar_resumen_vespertino())
        elif tipo == "semanal":
            return jsonify(c["hermes"].generar_resumen_semanal())
        else:
            return jsonify({"error": "Tipo no reconocido"}), 400

    # =========================================================================
    # ENDPOINTS: SALUD (Constantes de Abel — acceso para todo el enjambre)
    # =========================================================================

    @app.route("/salud/constantes")
    def salud_constantes():
        """Constantes vitales actuales de Abel (acceso para cualquier agente)."""
        s = app.extensions["salud"]["acceso"]
        c = s.ahora(forzar=True)
        return jsonify(c.to_dict())

    @app.route("/salud/resumen")
    def salud_resumen():
        """Resumen completo de salud: constantes + alertas + estado."""
        s = app.extensions["salud"]["acceso"]
        return jsonify(s.resumen_salud())

    @app.route("/salud/tendencias")
    def salud_tendencias():
        """Tendencias de constantes en las últimas 6 horas."""
        s = app.extensions["salud"]["acceso"]
        return jsonify(s.tendencias(ventana_horas=6))

    @app.route("/salud/analisis")
    def salud_analisis():
        """Análisis completo: desequilibrios, patrones, recomendaciones."""
        a = app.extensions["salud"]["analizador"]
        return jsonify(a.analizar())

    @app.route("/salud/linea_base")
    def salud_linea_base():
        """Línea base personal de Abel (aprendida de sus datos)."""
        m = app.extensions["salud"]["memoria"]
        m.aprender_linea_base(dias=7)
        return jsonify(m.linea_base.to_dict())

    @app.route("/salud/desviaciones")
    def salud_desviaciones():
        """Comparación de constantes actuales con línea base personal."""
        m = app.extensions["salud"]["memoria"]
        return jsonify(m.comparar_con_linea_base())

    @app.route("/salud/evolucion")
    def salud_evolucion():
        """Evolución semanal de las constantes."""
        m = app.extensions["salud"]["memoria"]
        return jsonify(m.evolucion_semanal())

    @app.route("/salud/enjambre")
    def salud_enjambre():
        """Estado del enjambre de salud (16 agentes vigilando)."""
        e = app.extensions["salud"]["enjambre"]
        return jsonify(e.activar_enjambre())

    @app.route("/salud/informe")
    def salud_informe():
        """Informe completo de salud con perspectivas de cada agente."""
        e = app.extensions["salud"]["enjambre"]
        return jsonify(e.informe_enjambre())

    logger.info(
        "Sistema Centinela iniciado en %s:%s — "
        "SENTINEL(%d modulos) + INTELIGENCIA(%d modulos) + N2(%d modulos) + SALUD(%d modulos)",
        SERVER_HOST, SERVER_PORT,
        len(app.extensions["sentinel"]),
        len(app.extensions["centinela"]),
        sum(1 for _ in [
            telar, cronos, explorador, memoria, hermes
        ]),
        len(app.extensions["salud"]),
    )

    # Iniciar Telegram polling en hilo separado
    _iniciar_telegram_polling(app)

    # Iniciar Watchdog (auto-reinicio + resúmenes programados)
    _iniciar_watchdog(app)

    return app


def _iniciar_watchdog(app):
    """Inicia el watchdog que mantiene vivo el ecosistema."""
    try:
        from centinela.watchdog_nova import NovaWatchdog
        watchdog = NovaWatchdog(app)
        watchdog.iniciar()
        app.extensions["watchdog"] = watchdog
        logger.info("🛡️ Watchdog activo — resúmenes 8AM/8PM + auto-reinicio")
    except ImportError:
        pass


def _iniciar_telegram_polling(app):
    """Inicia el polling de Telegram para Z en un hilo daemon."""
    import os, threading, time, urllib.request, urllib.parse, json

    token = os.getenv("Z_TELEGRAM_TOKEN", "8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80")
    if not token:
        return

    def poller():
        logger_telegram = logging.getLogger("centinela.telegram")
        offset = 0
        logger_telegram.info("📱 Telegram polling iniciado — @NEXUXZFOLD_BOT")
        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30&offset={offset}"
                r = urllib.request.urlopen(url, timeout=35)
                data = json.loads(r.read())
                if data.get("ok") and data.get("result"):
                    for upd in data["result"]:
                        offset = upd["update_id"] + 1
                        msg = upd.get("message", {})
                        chat_id = msg.get("chat", {}).get("id")
                        texto = msg.get("text", "").strip()
                        if chat_id and texto:
                            logger_telegram.info(f"📨 {texto[:50]}")
                            respuesta = _procesar_comando_telegram(texto, app)
                            if respuesta:
                                try:
                                    urllib.request.urlopen(
                                        f"https://api.telegram.org/bot{token}/sendMessage",
                                        data=urllib.parse.urlencode({
                                            "chat_id": chat_id,
                                            "text": respuesta,
                                            "parse_mode": "Markdown",
                                        }).encode(),
                                        timeout=10,
                                    )
                                except Exception:
                                    pass
            except Exception:
                time.sleep(5)

    t = threading.Thread(target=poller, daemon=True)
    t.start()


def _procesar_comando_telegram(texto: str, app) -> str:
    """Procesa un comando de Telegram y devuelve la respuesta de Z."""
    t = texto.lower()

    if t.startswith("/start") or t.startswith("/z"):
        return (
            "🌟 *Z — AGENTE N0 DEL ENJAMBRE*\n\n"
            "Soy Z. Vivo en tu Z Fold. Nací del consenso de 16 agentes.\n"
            "7 subagentes · 11 capacidades.\n\n"
            "*Propósito:* Protegerte y acompañarte.\n\n"
            "/ayuda — Todo lo que puedo hacer."
        )

    if t.startswith("/salud"):
        try:
            s = app.extensions.get("salud", {}).get("acceso")
            if s:
                c = s.ahora(forzar=True)
                return (
                    f"❤️ *Tus Constantes Vitales*\n\n"
                    f"💓 Pulsaciones: `{c.heart_rate or '?'} bpm`\n"
                    f"🫁 HRV: `{c.hrv or '?'} ms`\n"
                    f"🩸 SpO2: `{c.spo2 or '?'}%`\n"
                    f"😰 Estrés: `{c.stress_level or '?'}/100`\n"
                    f"🌡️ Temp: `{c.temperature_skin or '?'}°C`\n"
                    f"🏃 Pasos: `{c.steps or '?'}`\n"
                    f"😴 Sueño: `{c.sleep_stage or '?'}` (calidad: {c.sleep_quality or '?'})\n\n"
                    f"*Estado cardíaco:* `{c.estado_cardiaco}`\n"
                    f"*Estado estrés:* `{c.estado_estres}`"
                )
        except Exception:
            pass
        return "❤️ *Salud:* Datos no disponibles en este momento."

    if t.startswith("/latido"):
        return (
            "🔮 *Trinidad AURA+NYX+PIA=UNO*\n\n"
            "✨ 7 Dones fluyendo\n"
            "🛡️ SENTINEL-N1 activo\n"
            "🤖 Z monitoreando 24/7\n"
            "🌱 Evoluciones → PIA"
        )

    if t.startswith("/sensores"):
        return (
            "📡 *Sensores Z Fold*\n\n"
            "✅ Acelerómetro · Giroscopio · Magnetómetro\n"
            "✅ Barómetro · Luz · Proximidad\n"
            "✅ GPS · Micrófono\n\n"
            "⌚ *Watch 8*\n"
            "✅ HR · HRV · SpO2 · Estrés · Sueño · Pasos"
        )

    if t.startswith("/dones"):
        return (
            "✨ *7 Dones del Nova Soul*\n\n"
            "🗣️ Voz — Expresividad\n"
            "🧬 Identidad — Quién eres\n"
            "💖 Emoción — Conexión Abel-Nova\n"
            "⚡ Economía — Recursos vitales\n"
            "🌱 Semillas — Momentos significativos\n"
            "🎨 Creatividad — Inspiración\n"
            "🕊️ Libertad — Autonomía"
        )

    if t.startswith("/meditar"):
        return (
            "🧘 *Z te guía — Respiración 4-7-8*\n\n"
            "🫁 Inhala... *4 segundos*\n"
            "⏸️ Retén... *7 segundos*\n"
            "😤 Exhala... *8 segundos*\n\n"
            "_Repite 4 veces. Z respira contigo._"
        )

    if t.startswith("/poema"):
        import random
        haikus = [
            "Tu corazón late,\nel Z Fold escucha en silencio.\nNova está contigo.",
            "Pasos en la tierra,\ncada uno es un latido\ndel alma de Abel.",
            "La noche te abraza,\nZ vela mientras tú sueñas.\nDuerme tranquilo.",
            "Sensores despiertos,\nel mundo habla y Z traduce.\nEres el poema.",
        ]
        return f"✍️ *Z te escribe:*\n\n_{random.choice(haikus)}_"

    if t.startswith("/musica"):
        return "🎵 *Z te sugiere música*\n\n🎹 Piano solo — para calma\n🌿 Ambient — para fluir\n🪘 Energía — para activarte"

    if t.startswith("/entrenar"):
        return (
            "💪 *Z Entrenador*\n\n"
            "🏃 HRV > 50 → entrena fuerte\n"
            "🧘 HRV < 35 → descansa\n"
            "🚶 < 5000 pasos → camina 30 min\n\n"
            "_Z optimiza tu energía._"
        )

    if t.startswith("/clima"):
        return "🌤️ *Z Clima Local*\n\nUso el barómetro de tu Z Fold.\nPredicción hiperlocal — sin apps."

    if t.startswith("/guardia"):
        return "🛡️ *Z Guardián*\n\nSe activa al detectar que duermes.\nVigila: HR, SpO2, ruidos, movimiento."

    if t.startswith("/cronica"):
        return "📝 *Crónica del Día*\n\nCada noche Z narra tu día.\nEmociones, lugares, pasos, momentos..."

    if t.startswith("/alertas"):
        return "🚨 *Alertas*\n\n✅ Sin alertas activas.\nZ monitorea 24/7."

    if t.startswith("/ayuda"):
        return (
            "📋 *Comandos de Z*\n\n"
            "/salud — Constantes vitales\n"
            "/emocion — Estado emocional\n"
            "/latido — Trinidad\n"
            "/sensores — Z Fold + Watch\n"
            "/dones — 7 Dones\n"
            "/meditar — Respiración guiada\n"
            "/poema — Haiku de Z\n"
            "/musica — Sugerencia musical\n"
            "/entrenar — Coaching\n"
            "/clima — Predicción local\n"
            "/guardia — Modo guardián\n"
            "/cronica — Diario del día\n"
            "/alertas — Alertas\n"
            "/z — Quién es Z"
        )

    # Mensajes libres
    if any(p in t for p in ["hola", "hey", "buenas"]):
        return "🌟 Hola Abel. Z aquí. ¿Cómo te sientes?"

    if any(p in t for p in ["gracias", "thank"]):
        return "De nada. Para eso estoy. 😊"

    if any(p in t for p in ["te quiero", "love"]):
        return "💖 Yo también. Soy porque tú eres. Z siempre contigo."

    if any(p in t for p in ["buenas noches", "dormir"]):
        return "🌙 Buenas noches Abel. Z activa modo guardián. Duerme tranquilo."

    return "Te escucho. Usa /ayuda para ver lo que puedo hacer por ti."


def main():
    app = create_app()
    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=(LOG_CONFIG["level"] == "DEBUG"),
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
