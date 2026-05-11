"""
Panel de visualización del Sistema Centinela
Integración con dashboard Genesis 4.0
Nova Homonexus - MAYORDOMO

Genera un panel HTML/JS interactivo que se sirve desde el dashboard
existente en puerto 9088.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from flask import Blueprint, render_template_string, jsonify, current_app

from centinela.config import DEVICE_ZFOLD_ID, DEVICE_WATCH8_ID

logger = logging.getLogger("centinela.dashboard")

dashboard_bp = Blueprint(
    "centinela_dashboard", __name__, url_prefix="/centinela"
)


# =============================================================================
# RUTA PRINCIPAL DEL PANEL
# =============================================================================
@dashboard_bp.route("/")
def panel_centinela():
    """Sirve el panel HTML del Sistema Centinela."""
    return render_template_string(PANEL_HTML)


@dashboard_bp.route("/api/panel-data")
def panel_data():
    """
    API interna para el panel. Devuelve datos agregados
    para renderizar el dashboard.
    """
    try:
        from sqlalchemy import func, desc
        from centinela.db.models import (
            SensorLectura, Ubicacion, HealthRecord,
            Emocion, Alerta, SesionMonitoreo,
        )

        from flask import g
        session = g.get("db_session") or current_app.extensions.get("sqlalchemy", {}).get("session")
        ahora = datetime.now(timezone.utc)

        # Últimos datos
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

        # Últimas 100 lecturas de health para gráficas
        health_reciente = (
            session.query(HealthRecord)
            .order_by(HealthRecord.timestamp.desc())
            .limit(100)
            .all()
        )

        # Últimas 50 emociones
        emociones_recientes = (
            session.query(Emocion)
            .order_by(Emocion.timestamp.desc())
            .limit(50)
            .all()
        )

        # Alertas activas
        alertas_activas = (
            session.query(Alerta)
            .filter(Alerta.resuelta == False)
            .order_by(Alerta.timestamp.desc())
            .limit(20)
            .all()
        )

        # Sesión activa
        sesion = (
            session.query(SesionMonitoreo)
            .filter(
                SesionMonitoreo.estado == "activa",
                SesionMonitoreo.device_id == DEVICE_ZFOLD_ID,
            )
            .order_by(SesionMonitoreo.inicio.desc())
            .first()
        )

        # Conteos de la última hora
        hace_1h = ahora - __import__("datetime").timedelta(hours=1)
        total_sensores = (
            session.query(func.count(SensorLectura.id))
            .filter(SensorLectura.timestamp > hace_1h)
            .scalar()
        )

        return jsonify({
            "ultimo_sensor": ultimo_sensor.to_dict() if ultimo_sensor else None,
            "ultima_ubicacion": ultima_ubicacion.to_dict() if ultima_ubicacion else None,
            "ultimo_health": ultimo_health.to_dict() if ultimo_health else None,
            "ultima_emocion": ultima_emocion.to_dict() if ultima_emocion else None,
            "health_historico": [
                {
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    "heart_rate": h.heart_rate,
                    "spo2": h.spo2,
                    "stress_level": h.stress_level,
                    "hrv": h.hrv,
                }
                for h in reversed(health_reciente)
            ],
            "emociones_historico": [
                {
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "emocion": e.emocion_detectada,
                    "confianza": e.confianza,
                }
                for e in reversed(emociones_recientes)
            ],
            "alertas": [a.to_dict() for a in alertas_activas],
            "sesion": sesion.to_dict() if sesion else None,
            "total_sensores_hora": total_sensores,
            "timestamp": ahora.isoformat(),
        })

    except Exception as e:
        logger.error("Error en panel data: %s", str(e))
        return jsonify({"error": str(e)}), 500


# =============================================================================
# PANEL HTML
# =============================================================================
PANEL_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Centinela - Nova Homonexus</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">
    </script>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js">
    </script>
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: #1a1f2e;
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --accent-purple: #8b5cf6;
            --border: #1e293b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        .header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-status {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .status-dot.online { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
        .status-dot.offline { background: var(--accent-red); box-shadow: 0 0 8px var(--accent-red); }
        .status-dot.warning { background: var(--accent-yellow); box-shadow: 0 0 8px var(--accent-yellow); }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 1.5rem;
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: border-color 0.3s;
        }

        .card:hover {
            border-color: var(--accent-cyan);
        }

        .card-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }

        .card-value {
            font-size: 2rem;
            font-weight: 700;
        }

        .card-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }

        .col-span-3 { grid-column: span 3; }
        .col-span-4 { grid-column: span 4; }
        .col-span-6 { grid-column: span 6; }
        .col-span-8 { grid-column: span 8; }
        .col-span-12 { grid-column: span 12; }

        .grid-sensors {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 0.5rem;
        }

        .sensor-item {
            background: rgba(6, 182, 212, 0.05);
            border: 1px solid rgba(6, 182, 212, 0.1);
            border-radius: 8px;
            padding: 0.75rem;
            text-align: center;
        }

        .sensor-item .name {
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .sensor-item .value {
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0.25rem;
        }

        .sensor-item .unit {
            font-size: 0.7rem;
            color: var(--text-secondary);
        }

        .emotion-display {
            text-align: center;
            padding: 1rem;
        }

        .emotion-display .emotion-name {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .emotion-display .emotion-confidence {
            font-size: 1rem;
            color: var(--text-secondary);
        }

        .confidence-bar {
            width: 100%;
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            margin-top: 0.5rem;
            overflow: hidden;
        }

        .confidence-bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }

        .alert-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
        }

        .alert-item:last-child { border-bottom: none; }

        .alert-severity {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .alert-severity.critical { background: var(--accent-red); }
        .alert-severity.warning { background: var(--accent-yellow); }
        .alert-severity.info { background: var(--accent-cyan); }

        .alert-message {
            font-size: 0.875rem;
            flex: 1;
        }

        .alert-time {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        #map {
            height: 300px;
            border-radius: 8px;
            z-index: 1;
        }

        .chart-container {
            position: relative;
            height: 200px;
        }

        @media (max-width: 768px) {
            .col-span-3, .col-span-4, .col-span-6, .col-span-8 {
                grid-column: span 12;
            }
            .header {
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ SISTEMA CENTINELA</h1>
        <div class="header-status">
            <div class="status-indicator">
                <span class="status-dot" id="zfold-status"></span>
                <span>Z Fold</span>
            </div>
            <div class="status-indicator">
                <span class="status-dot" id="watch-status"></span>
                <span>Watch 8</span>
            </div>
            <div class="status-indicator">
                <span class="status-dot" id="ws-status"></span>
                <span>WebSocket</span>
            </div>
            <span id="clock" style="font-size:0.875rem;color:var(--text-secondary)"></span>
        </div>
    </div>

    <div class="container">
        <!-- TARJETAS RESUMEN -->
        <div class="card col-span-3">
            <div class="card-title">Ritmo Cardiaco</div>
            <div class="card-value" id="hr-value">--</div>
            <div class="card-label" id="hr-label">bpm</div>
        </div>
        <div class="card col-span-3">
            <div class="card-title">SpO2</div>
            <div class="card-value" id="spo2-value">--</div>
            <div class="card-label" id="spo2-label">%</div>
        </div>
        <div class="card col-span-3">
            <div class="card-title">Estres</div>
            <div class="card-value" id="stress-value">--</div>
            <div class="card-label" id="stress-label">%</div>
        </div>
        <div class="card col-span-3">
            <div class="card-title">HRV</div>
            <div class="card-value" id="hrv-value">--</div>
            <div class="card-label" id="hrv-label">ms</div>
        </div>

        <!-- MAPA -->
        <div class="card col-span-6">
            <div class="card-title">Ubicacion GPS</div>
            <div id="map"></div>
        </div>

        <!-- EMOCION -->
        <div class="card col-span-6">
            <div class="card-title">Deteccion Emocional</div>
            <div class="emotion-display">
                <div class="emotion-name" id="emotion-name">--</div>
                <div class="emotion-confidence" id="emotion-confidence">Confianza: --</div>
                <div class="confidence-bar">
                    <div class="confidence-bar-fill" id="emotion-bar"
                         style="width:0%;background:var(--accent-cyan)"></div>
                </div>
                <div style="margin-top:0.75rem;font-size:0.8rem;color:var(--text-secondary)"
                     id="emotion-secondary"></div>
            </div>
        </div>

        <!-- GRAFICA HR -->
        <div class="card col-span-6">
            <div class="card-title">Frecuencia Cardiaca (ultimos 100 registros)</div>
            <div class="chart-container">
                <canvas id="hr-chart"></canvas>
            </div>
        </div>

        <!-- GRAFICA SPO2 / STRESS -->
        <div class="card col-span-6">
            <div class="card-title">SpO2 y Estres</div>
            <div class="chart-container">
                <canvas id="multi-chart"></canvas>
            </div>
        </div>

        <!-- SENSORES ACTIVOS -->
        <div class="card col-span-6">
            <div class="card-title">Ultimas Lecturas de Sensores</div>
            <div class="grid-sensors" id="sensors-grid">
                <div style="color:var(--text-secondary);font-size:0.875rem">
                    Esperando datos...
                </div>
            </div>
        </div>

        <!-- ALERTAS -->
        <div class="card col-span-6">
            <div class="card-title">Alertas Activas</div>
            <div id="alertas-list">
                <div style="color:var(--text-secondary);font-size:0.875rem">
                    Sin alertas activas
                </div>
            </div>
        </div>

        <!-- HISTORIAL EMOCIONES -->
        <div class="card col-span-12">
            <div class="card-title">Historial Emocional</div>
            <div class="chart-container" style="height:100px">
                <canvas id="emotion-chart"></canvas>
            </div>
        </div>
    </div>

    <script>
    // =========================================================================
    // CONFIGURACIÓN
    // =========================================================================
    const API_BASE = '/centinela/api';
    const WS_URL = 'ws://' + window.location.host + '/ws/centinela';
    const API_KEY = 'nexus-centinela-key-2026';
    const REFRESH_INTERVAL = 3000; // 3 segundos

    // =========================================================================
    // ESTADO GLOBAL
    // =========================================================================
    let state = {
        healthHistory: [],
        emotionHistory: [],
        alertas: [],
        ultimaUbicacion: null,
    };

    // =========================================================================
    // MAPA
    // =========================================================================
    let map = L.map('map').setView([19.4326, -99.1332], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
    }).addTo(map);
    let marker = L.marker([19.4326, -99.1332]).addTo(map);

    // =========================================================================
    // GRÁFICAS
    // =========================================================================
    let hrChart = new Chart(document.getElementById('hr-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'HR (bpm)',
                data: [],
                borderColor: '#06b6d4',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: {
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    let multiChart = new Chart(document.getElementById('multi-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'SpO2 (%)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    yAxisID: 'y',
                },
                {
                    label: 'Estres (%)',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
            scales: {
                x: { display: false },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 80,
                    max: 100,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: { color: '#10b981' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 0,
                    max: 100,
                    grid: { display: false },
                    ticks: { color: '#f59e0b' }
                }
            }
        }
    });

    let emotionChart = new Chart(document.getElementById('emotion-chart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Emocion',
                data: [],
                backgroundColor: [],
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8', maxRotation: 45 } },
                y: { display: false }
            }
        }
    });

    // =========================================================================
    // COLORES POR EMOCIÓN
    // =========================================================================
    const EMOTION_COLORS = {
        'neutro': '#94a3b8',
        'feliz': '#10b981',
        'triste': '#6366f1',
        'enojado': '#ef4444',
        'ansioso': '#f59e0b',
        'estresado': '#dc2626',
        'relajado': '#06b6d4',
        'sorprendido': '#8b5cf6',
        'asustado': '#e11d48',
        'confundido': '#f97316',
    };

    // =========================================================================
    // WEBSOCKET
    // =========================================================================
    let ws = null;

    function conectarWebSocket() {
        try {
            ws = new WebSocket(WS_URL);
            ws.onopen = function() {
                document.getElementById('ws-status').className = 'status-dot online';
                ws.send(API_KEY);
                ws.send(JSON.stringify({ accion: 'suscribir', canal: 'todo' }));
            };
            ws.onclose = function() {
                document.getElementById('ws-status').className = 'status-dot offline';
                setTimeout(conectarWebSocket, 5000);
            };
            ws.onerror = function() {
                document.getElementById('ws-status').className = 'status-dot warning';
            };
            ws.onmessage = function(event) {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.tipo === 'health' && msg.datos) {
                        actualizarHealth(msg.datos);
                    }
                    if (msg.tipo === 'emocion' && msg.datos) {
                        actualizarEmocion(msg.datos);
                    }
                    if (msg.tipo === 'ubicacion' && msg.datos) {
                        actualizarUbicacion(msg.datos);
                    }
                    if (msg.tipo === 'alerta' && msg.datos) {
                        actualizarAlertas();
                    }
                } catch(e) {}
            };
        } catch(e) {
            document.getElementById('ws-status').className = 'status-dot offline';
        }
    }

    // =========================================================================
    // ACTUALIZACIONES
    // =========================================================================
    function actualizarHealth(data) {
        if (data.heart_rate) {
            document.getElementById('hr-value').textContent = data.heart_rate;
            const hr = data.heart_rate;
            let color = '#10b981';
            if (hr < 50 || hr > 140) color = '#ef4444';
            else if (hr < 60 || hr > 100) color = '#f59e0b';
            document.getElementById('hr-value').style.color = color;
        }
        if (data.spo2) {
            document.getElementById('spo2-value').textContent = data.spo2.toFixed(1);
            const spo2 = data.spo2;
            document.getElementById('spo2-value').style.color =
                spo2 < 90 ? '#ef4444' : spo2 < 95 ? '#f59e0b' : '#10b981';
        }
        if (data.stress_level !== null && data.stress_level !== undefined) {
            document.getElementById('stress-value').textContent = data.stress_level;
            const s = data.stress_level;
            document.getElementById('stress-value').style.color =
                s > 80 ? '#ef4444' : s > 60 ? '#f59e0b' : '#10b981';
        }
        if (data.hrv) {
            document.getElementById('hrv-value').textContent = data.hrv.toFixed(1);
        }
    }

    function actualizarEmocion(data) {
        const nameEl = document.getElementById('emotion-name');
        const confEl = document.getElementById('emotion-confidence');
        const barEl = document.getElementById('emotion-bar');

        nameEl.textContent = data.emocion_detectada || '--';
        nameEl.style.color = EMOTION_COLORS[data.emocion_detectada] || '#94a3b8';

        const confianza = (data.confianza || 0) * 100;
        confEl.textContent = 'Confianza: ' + confianza.toFixed(1) + '%';
        barEl.style.width = confianza + '%';
        barEl.style.background = EMOTION_COLORS[data.emocion_detectada] || '#06b6d4';

        if (data.emociones_secundarias && data.emociones_secundarias.length > 0) {
            const sec = data.emociones_secundarias.slice(0, 3);
            document.getElementById('emotion-secondary').textContent =
                'Secundarias: ' + sec.map(e =>
                    e.emocion + ' (' + (e.confianza * 100).toFixed(0) + '%)'
                ).join(', ');
        }
    }

    function actualizarUbicacion(data) {
        if (data.lat && data.lon) {
            marker.setLatLng([data.lat, data.lon]);
            map.setView([data.lat, data.lon], map.getZoom());
            state.ultimaUbicacion = data;
        }
    }

    function actualizarSensores(data) {
        if (!data || !data.valor) return;
        const grid = document.getElementById('sensors-grid');
        const tipo = data.tipo_sensor || 'desconocido';
        const valor = data.valor;
        const unidad = data.unidad || '';

        let valorStr = '';
        if (typeof valor === 'object') {
            valorStr = Object.entries(valor)
                .map(([k, v]) => k + ': ' + (typeof v === 'number' ? v.toFixed(2) : v))
                .join(' | ');
        } else {
            valorStr = valor;
        }

        // Buscar si ya existe el sensor
        let existing = grid.querySelector('[data-sensor="' + tipo + '"]');
        if (existing) {
            existing.querySelector('.value').textContent = valorStr;
        } else {
            const div = document.createElement('div');
            div.className = 'sensor-item';
            div.setAttribute('data-sensor', tipo);
            div.innerHTML = `
                <div class="name">${tipo}</div>
                <div class="value">${valorStr}</div>
                <div class="unit">${unidad}</div>
            `;
            grid.appendChild(div);
        }
    }

    function actualizarAlertas() {
        fetch(API_BASE + '/panel-data')
            .then(r => r.json())
            .then(data => {
                const list = document.getElementById('alertas-list');
                if (!data.alertas || data.alertas.length === 0) {
                    list.innerHTML = '<div style="color:var(--text-secondary);font-size:0.875rem">Sin alertas activas</div>';
                    return;
                }
                list.innerHTML = data.alertas.map(a => `
                    <div class="alert-item">
                        <div class="alert-severity ${a.severidad}"></div>
                        <div class="alert-message">${a.mensaje}</div>
                        <div class="alert-time">${new Date(a.timestamp).toLocaleTimeString()}</div>
                    </div>
                `).join('');
            });
    }

    function actualizarGraficas(data) {
        if (data.health_historico && data.health_historico.length > 0) {
            const labels = data.health_historico.map(h =>
                new Date(h.timestamp).toLocaleTimeString()
            );
            const hrs = data.health_historico.map(h => h.heart_rate);
            const spo2s = data.health_historico.map(h => h.spo2);
            const stresses = data.health_historico.map(h => h.stress_level);

            hrChart.data.labels = labels;
            hrChart.data.datasets[0].data = hrs;
            hrChart.update();

            multiChart.data.labels = labels;
            multiChart.data.datasets[0].data = spo2s;
            multiChart.data.datasets[1].data = stresses;
            multiChart.update();
        }

        if (data.emociones_historico && data.emociones_historico.length > 0) {
            const labels = data.emociones_historico.map(e =>
                new Date(e.timestamp).toLocaleTimeString()
            );
            const values = data.emociones_historico.map(e => e.confianza * 100);
            const colors = data.emociones_historico.map(e =>
                EMOTION_COLORS[e.emocion] || '#94a3b8'
            );

            emotionChart.data.labels = labels;
            emotionChart.data.datasets[0].data = values;
            emotionChart.data.datasets[0].backgroundColor = colors;
            emotionChart.update();
        }
    }

    function actualizarEstado(data) {
        const zfold = document.getElementById('zfold-status');
        const watch = document.getElementById('watch-status');

        if (data.ultimo_sensor) {
            zfold.className = 'status-dot online';
            actualizarSensores(data.ultimo_sensor);
        } else {
            zfold.className = 'status-dot offline';
        }

        if (data.ultimo_health) {
            watch.className = 'status-dot online';
            actualizarHealth(data.ultimo_health);
        } else {
            watch.className = 'status-dot offline';
        }

        if (data.ultima_ubicacion) {
            actualizarUbicacion(data.ultima_ubicacion);
        }

        if (data.ultima_emocion) {
            actualizarEmocion(data.ultima_emocion);
        }

        actualizarGraficas(data);
    }

    // =========================================================================
    // RELOJ
    // =========================================================================
    function actualizarReloj() {
        document.getElementById('clock').textContent =
            new Date().toLocaleTimeString();
    }

    // =========================================================================
    // CARGA INICIAL Y REFRESH
    // =========================================================================
    function cargarDatos() {
        fetch(API_BASE + '/panel-data')
            .then(r => r.json())
            .then(data => {
                actualizarEstado(data);
                state.alertas = data.alertas || [];
            })
            .catch(err => {
                console.error('Error cargando datos:', err);
            });
    }

    // Inicializar
    conectarWebSocket();
    cargarDatos();
    actualizarReloj();
    setInterval(cargarDatos, REFRESH_INTERVAL);
    setInterval(actualizarReloj, 1000);
    </script>
</body>
</html>
"""
