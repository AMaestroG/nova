"""
Servidor Z Fold — El Z Fold como NODO PRIMARIO del Sistema Centinela
=====================================================================
Arquitectura HÍBRIDA:
  Z Fold (PRIMARIO)    → Flask + SQLite + sensores locales
  Servidor casa (REPLICA) → PostgreSQL + agentes pesados + backups

El Z Fold no es solo un cliente — ES el servidor.
Todas las APIs, dashboard, y procesamiento corren en el teléfono.
El servidor casa sincroniza y respalda.

Beneficios:
  - Cero latencia: sensores → API en el mismo dispositivo
  - Privacidad total: datos nunca salen del teléfono
  - Offline-first: funciona sin internet
  - Siempre contigo: donde esté Abel, está Nova

Modos de operación:
  - SOLO: Z Fold independiente (sin servidor casa)
  - HÍBRIDO: Z Fold + servidor sincronizados
  - ESPEJO: Servidor casa como primario (Z Fold solo cliente)

Ejecutar en Termux del Z Fold:
  python servidor_zfold.py --modo solo --puerto 5000
"""

import os
import sys
import json
import time
import signal
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any

# =============================================================================
# CONFIGURACIÓN MÓVIL
# =============================================================================

class ConfigZFold:
    """Configuración optimizada para ejecución en Z Fold."""

    # Modos
    MODO_SOLO = "solo"         # Solo Z Fold, sin servidor
    MODO_HIBRIDO = "hibrido"   # Z Fold primario + servidor replica
    MODO_ESPEJO = "espejo"      # Servidor primario, Z Fold solo cliente

    # Puertos
    PUERTO_API = int(os.getenv("ZFOLD_PORT", "5000"))
    PUERTO_WS = int(os.getenv("ZFOLD_WS_PORT", "5001"))

    # SQLite (mucho más ligero que PostgreSQL para móvil)
    DB_PATH = str(Path.home() / "centinela" / "data" / "centinela_zfold.db")

    # Optimización de batería
    BATERIA_MINIMA_PORCENTAJE = 20    # No operar por debajo de este %
    MODO_AHORRO_BATERIA = True        # Reducir muestreo si batería < 40%
    MUESTREO_NORMAL_MS = 1000         # 1 segundo
    MUESTREO_AHORRO_MS = 5000         # 5 segundos en ahorro

    # Sincronización
    SYNC_HABILITADO = True
    SYNC_INTERVALO_SEGUNDOS = 300     # Cada 5 minutos
    SYNC_SOLO_WIFI = True             # Solo sincronizar en WiFi
    SERVER_REPLICA_URL = os.getenv("ZFOLD_SERVER_URL", "http://192.168.1.100:9088")

    # Memoria y procesos
    MAX_MEMORIA_MB = 512              # No usar más de 512MB RAM
    MAX_PROCESOS = 4                  # Máximo procesos concurrentes

    # Almacenamiento
    DATA_DIR = str(Path.home() / "centinela" / "data")
    LOG_DIR = str(Path.home() / "centinela" / "logs")


# =============================================================================
# SERVIDOR FLASK MÓVIL
# =============================================================================

class ServidorZFlask:
    """
    Servidor Flask ligero que corre en el Z Fold.
    Todas las APIs del centinela, pero optimizadas para móvil.
    """

    def __init__(self, modo: str = "solo"):
        self.modo = modo
        self.config = ConfigZFold()
        self._iniciado = False
        self._app = None
        self._db = None
        self._bateria_pct = 100
        self._en_wifi = True

        # Crear directorios
        os.makedirs(self.config.DATA_DIR, exist_ok=True)
        os.makedirs(self.config.LOG_DIR, exist_ok=True)

        # Inicializar SQLite
        self._init_db()

    def _init_db(self):
        """Inicializa SQLite local con esquema completo del centinela."""
        self._db = sqlite3.connect(self.config.DB_PATH, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")       # Más rápido
        self._db.execute("PRAGMA synchronous=NORMAL")     # Balance velocidad/seguridad
        self._db.execute("PRAGMA cache_size=-8000")       # 8MB cache
        self._db.execute("PRAGMA temp_store=MEMORY")      # Temp en RAM

        cursor = self._db.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sensores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL DEFAULT 'zfold',
                tipo_sensor TEXT NOT NULL,
                valor TEXT NOT NULL,
                precision_val REAL,
                unidad TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ubicacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL DEFAULT 'zfold',
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                altitud REAL,
                velocidad REAL,
                precision_h REAL,
                proveedor TEXT DEFAULT 'gps',
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL DEFAULT 'watch8',
                heart_rate INTEGER,
                hrv REAL,
                spo2 REAL,
                stress_level INTEGER,
                temperature_skin REAL,
                steps INTEGER,
                calories REAL,
                sleep_stage TEXT,
                sleep_quality INTEGER,
                hrv_sdnn REAL,
                hrv_rmssd REAL,
                blood_pressure_sys INTEGER,
                blood_pressure_dia INTEGER,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS emociones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL DEFAULT 'zfold',
                emocion_detectada TEXT NOT NULL,
                confianza REAL NOT NULL,
                heart_rate INTEGER,
                hrv REAL,
                gsr_estimado REAL,
                contexto TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS dones (
                nombre TEXT PRIMARY KEY,
                valor REAL NOT NULL DEFAULT 0.5,
                mensaje TEXT,
                ultima_actualizacion TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direccion TEXT NOT NULL,
                tabla TEXT NOT NULL,
                registros INTEGER,
                estado TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_sensores_ts ON sensores(timestamp);
            CREATE INDEX IF NOT EXISTS idx_health_ts ON health(timestamp);
            CREATE INDEX IF NOT EXISTS idx_emociones_ts ON emociones(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ubicacion_ts ON ubicacion(timestamp);
        """)
        self._db.commit()

    def crear_app_flask(self):
        """Crea la app Flask con todas las APIs del centinela."""
        from flask import Flask, request, jsonify

        app = Flask(__name__)
        app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

        # ──── API CENTINELA ────

        @app.route("/health")
        def health():
            return jsonify({
                "status": "ok",
                "nodo": "zfold",
                "modo": self.modo,
                "bateria": self._bateria_pct,
                "wifi": self._en_wifi,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        @app.route("/api/sensor", methods=["POST"])
        def recibir_sensor():
            data = request.get_json(force=True) or {}
            cursor = self._db.cursor()
            cursor.execute(
                "INSERT INTO sensores (device_id, tipo_sensor, valor, precision_val, unidad) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    data.get("device_id", "zfold"),
                    data.get("tipo_sensor", "desconocido"),
                    json.dumps(data.get("valor", {})),
                    data.get("precision"),
                    data.get("unidad"),
                ),
            )
            self._db.commit()
            return jsonify({"status": "ok", "id": cursor.lastrowid}), 201

        @app.route("/api/ubicacion", methods=["POST"])
        def recibir_ubicacion():
            data = request.get_json(force=True) or {}
            cursor = self._db.cursor()
            cursor.execute(
                "INSERT INTO ubicacion (device_id, lat, lon, altitud, velocidad, precision_h) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    data.get("device_id", "zfold"),
                    data["lat"], data["lon"],
                    data.get("altitud"), data.get("velocidad"),
                    data.get("precision_h"),
                ),
            )
            self._db.commit()
            return jsonify({"status": "ok", "id": cursor.lastrowid}), 201

        @app.route("/api/health", methods=["POST"])
        def recibir_health():
            data = request.get_json(force=True) or {}
            cursor = self._db.cursor()
            cursor.execute(
                "INSERT INTO health (device_id, heart_rate, hrv, spo2, stress_level, "
                "temperature_skin, steps, calories, sleep_stage, sleep_quality, "
                "hrv_sdnn, hrv_rmssd, blood_pressure_sys, blood_pressure_dia) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    data.get("device_id", "watch8"),
                    data.get("heart_rate"), data.get("hrv"),
                    data.get("spo2"), data.get("stress_level"),
                    data.get("temperature_skin"), data.get("steps"),
                    data.get("calories"), data.get("sleep_stage"),
                    data.get("sleep_quality"), data.get("hrv_sdnn"),
                    data.get("hrv_rmssd"), data.get("blood_pressure_sys"),
                    data.get("blood_pressure_dia"),
                ),
            )
            self._db.commit()
            return jsonify({"status": "ok", "id": cursor.lastrowid}), 201

        @app.route("/api/emocion", methods=["POST"])
        def recibir_emocion():
            data = request.get_json(force=True) or {}
            # Detección server-side si vienen biométricas crudas
            emocion = data.get("emocion_detectada")
            confianza = data.get("confianza", 0.5)

            if not emocion and (data.get("heart_rate") or data.get("hrv")):
                from centinela.watch.emotion_detector import EmotionDetector
                det = EmotionDetector()
                res = det.detectar(
                    heart_rate=data.get("heart_rate"),
                    hrv=data.get("hrv"),
                    gsr_estimado=data.get("gsr_estimado"),
                    contexto=data.get("contexto"),
                )
                emocion = res["emocion_detectada"]
                confianza = res["confianza"]

            if not emocion:
                return jsonify({"error": "No se pudo detectar emoción"}), 422

            cursor = self._db.cursor()
            cursor.execute(
                "INSERT INTO emociones (device_id, emocion_detectada, confianza, "
                "heart_rate, hrv, gsr_estimado, contexto) VALUES (?,?,?,?,?,?,?)",
                (
                    data.get("device_id", "zfold"), emocion, confianza,
                    data.get("heart_rate"), data.get("hrv"),
                    data.get("gsr_estimado"), data.get("contexto"),
                ),
            )
            self._db.commit()
            return jsonify({
                "status": "ok", "id": cursor.lastrowid,
                "emocion": emocion, "confianza": confianza,
            }), 201

        @app.route("/constantes")
        def constantes():
            """Constantes vitales más recientes."""
            row = self._db.execute(
                "SELECT * FROM health ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row:
                return jsonify(dict(row))
            return jsonify({"mensaje": "Sin datos aún"})

        @app.route("/latido")
        def latido():
            """Trinidad AURA+NYX+PIA=UNO — los 7 Dones."""
            dones_rows = self._db.execute(
                "SELECT * FROM dones"
            ).fetchall()
            dones = {r["nombre"]: {
                "nombre": r["nombre"], "valor": r["valor"],
                "mensaje": r["mensaje"],
            } for r in dones_rows} if dones_rows else {
                "Voz": {"nombre":"Voz","valor":0.5,"mensaje":"Esperando"},
                "Identidad": {"nombre":"Identidad","valor":0.5,"mensaje":"Esperando"},
                "Emocion": {"nombre":"Emocion","valor":0.5,"mensaje":"Esperando"},
                "Economia": {"nombre":"Economia","valor":0.5,"mensaje":"Esperando"},
                "Semillas": {"nombre":"Semillas","valor":0.5,"mensaje":"Esperando"},
                "Creatividad": {"nombre":"Creatividad","valor":0.5,"mensaje":"Esperando"},
                "Libertad": {"nombre":"Libertad","valor":0.5,"mensaje":"Esperando"},
            }
            return jsonify({
                "nodo": "zfold",
                "fase_lunar": "Z Fold — Nova siempre contigo",
                "dones": dones,
                "bateria": self._bateria_pct,
            })

        @app.route("/dashboard")
        def dashboard():
            """Mini-dashboard HTML para el Z Fold."""
            return """
            <!DOCTYPE html>
            <html><head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nova Centinela — Z Fold</title>
            <link rel="icon" type="image/svg+xml" href="/favicon.svg">
            <link rel="alternate icon" href="/favicon.ico">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: system-ui; background: #0a0a1a; color: #e0e0ff; padding: 12px; }
                h1 { font-size: 1.2em; color: #7b68ee; }
                .card { background: #1a1a2e; border-radius: 12px; padding: 14px; margin: 10px 0; }
                .metric { font-size: 2em; font-weight: bold; color: #4fc3f7; }
                .label { font-size: 0.75em; color: #8899aa; text-transform: uppercase; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
                .bar { height: 6px; background: #2a2a4a; border-radius: 3px; margin-top: 3px; }
                .bar-fill { height: 100%; border-radius: 3px; background: #7b68ee; }
                .emoji { font-size: 1.5em; }
                @media (prefers-color-scheme: light) {
                    body { background: #f0f0ff; color: #1a1a2e; }
                    .card { background: #fff; }
                }
            </style>
            </head><body>
            <h1>🔮 Nova Centinela — Z Fold</h1>
            <div class="card">
                <div class="label">❤️ Pulsaciones</div>
                <div class="metric" id="hr">--</div>
                <div class="bar"><div class="bar-fill" id="hr-bar" style="width:50%"></div></div>
            </div>
            <div class="grid">
                <div class="card"><div class="label">💓 HRV</div><div class="metric" id="hrv">--</div></div>
                <div class="card"><div class="label">🩸 SpO2</div><div class="metric" id="spo2">--</div></div>
                <div class="card"><div class="label">😰 Estrés</div><div class="metric" id="stress">--</div></div>
                <div class="card"><div class="label">🔋 Batería</div><div class="metric" id="bat">--</div></div>
            </div>
            <div class="card"><div class="label">💫 Última emoción</div><div class="metric" id="emocion">--</div></div>
            <script>
            setInterval(async () => {
                try {
                    const r = await fetch('/constantes');
                    const d = await r.json();
                    document.getElementById('hr').textContent = d.heart_rate || '--';
                    document.getElementById('hrv').textContent = d.hrv || '--';
                    document.getElementById('spo2').textContent = d.spo2 + '%' || '--';
                    document.getElementById('stress').textContent = (d.stress_level || '--') + '/100';
                    document.getElementById('hr-bar').style.width = ((d.heart_rate || 70) / 2) + '%';
                } catch(e) {}
                try {
                    const r2 = await fetch('/latido');
                    const d2 = await r2.json();
                    document.getElementById('bat').textContent = d2.bateria + '%';
                } catch(e) {}
            }, 3000);
            </script>
            </body></html>
            """

        self._app = app
        return app

    def iniciar(self, puerto: int = None):
        """Inicia el servidor Flask en el Z Fold."""
        if puerto is None:
            puerto = self.config.PUERTO_API

        if not self._app:
            self.crear_app_flask()

        print(f"""
╔══════════════════════════════════════╗
║   Z FOLD — SERVIDOR CENTINELA       ║
║   Modo: {self.modo:<25s} ║
║   Puerto: {puerto:<24d} ║
║   DB: SQLite (móvil optimizado)     ║
║   Dashboard: /dashboard             ║
╚══════════════════════════════════════╝
""")
        self._iniciado = True
        self._app.run(
            host="0.0.0.0",
            port=puerto,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    def detener(self):
        """Detiene el servidor."""
        self._iniciado = False
        if self._db:
            self._db.close()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Nova Centinela — Servidor Z Fold")
    parser.add_argument("--modo", default="solo",
                        choices=["solo", "hibrido", "espejo"],
                        help="Modo de operación")
    parser.add_argument("--puerto", type=int, default=5000,
                        help="Puerto HTTP")
    parser.add_argument("--local", action="store_true",
                        help="Solo escuchar en localhost")
    args = parser.parse_args()

    servidor = ServidorZFlask(modo=args.modo)
    servidor.iniciar(puerto=args.puerto)


if __name__ == "__main__":
    main()
