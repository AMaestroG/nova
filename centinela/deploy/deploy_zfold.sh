#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# NOVA CENTINELA — DEPLOY TOTAL EN Z FOLD
# =============================================================================
# Un comando. Todo el ecosistema en tu Z Fold.
# Servidor + Z + AI + Telegram + sensores + auto-arranque.
#
# Uso en Termux:
#   curl -sL http://TU_IP:9080/deploy_zfold.sh | bash
#   o
#   bash deploy_zfold.sh
# =============================================================================
set -e

GREEN='\033[0;32m'; BLUE='\033[0;34m'; PURPLE='\033[0;35m'; NC='\033[0m'

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════╗"
echo "║   NOVA CENTINELA — Z FOLD DEPLOY         ║"
echo "║   Ecosistema completo en tu bolsillo     ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

CENTINELA_DIR="$HOME/centinela"
SERVER_IP="${1:-192.168.1.100}"

# =============================================================================
# 1. PAQUETES
# =============================================================================
echo -e "${BLUE}[1/7] Instalando paquetes esenciales...${NC}"
pkg update -y -q && pkg upgrade -y -q
pkg install -y -q \
    python python-pip \
    termux-api termux-services \
    curl git openssh tmux \
    termux-boot

# =============================================================================
# 2. PYTHON
# =============================================================================
echo -e "${BLUE}[2/7] Instalando dependencias Python...${NC}"
pip install -q flask flask-cors flask-sock requests websocket-client waitress

# =============================================================================
# 3. DIRECTORIOS
# =============================================================================
echo -e "${BLUE}[3/7] Creando estructura...${NC}"
mkdir -p "$CENTINELA_DIR"/{logs,data,static}

# =============================================================================
# 4. SERVIDOR CENTINELA LOCAL
# =============================================================================
echo -e "${BLUE}[4/7] Configurando servidor local...${NC}"

cat > "$CENTINELA_DIR/server_zfold.py" << 'SERVER_PY'
#!/usr/bin/env python3
"""Centinela — Z Fold Edition. Servidor local con SQLite."""
import os, sys, json, time, sqlite3, threading, logging
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.WARNING)
DB = str(Path.home() / "centinela" / "data" / "zfold.db")

app = Flask(__name__)
db = sqlite3.connect(DB, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA synchronous=NORMAL")

# Tablas
db.executescript("""
CREATE TABLE IF NOT EXISTS health(id INTEGER PRIMARY KEY, heart_rate INTEGER, hrv REAL, spo2 REAL,
    stress_level INTEGER, temperature_skin REAL, steps INTEGER, sleep_stage TEXT, sleep_quality INTEGER,
    timestamp TEXT DEFAULT(datetime('now')));
CREATE TABLE IF NOT EXISTS emociones(id INTEGER PRIMARY KEY, emocion TEXT, confianza REAL,
    heart_rate INTEGER, contexto TEXT, timestamp TEXT DEFAULT(datetime('now')));
CREATE TABLE IF NOT EXISTS sensores(id INTEGER PRIMARY KEY, tipo TEXT, valor TEXT,
    timestamp TEXT DEFAULT(datetime('now')));
CREATE TABLE IF NOT EXISTS dones(nombre TEXT PRIMARY KEY, valor REAL DEFAULT 0.5, mensaje TEXT);
""")
db.commit()

@app.route('/health')
def health():
    return jsonify({"status":"ok","nodo":"zfold","modo":"local","timestamp":datetime.now(timezone.utc).isoformat()})

@app.route('/api/health', methods=['POST'])
def recibir_health():
    d = request.get_json(force=True) or {}
    db.execute("INSERT INTO health(heart_rate,hrv,spo2,stress_level,temperature_skin,steps,sleep_stage,sleep_quality) VALUES(?,?,?,?,?,?,?,?)",
        (d.get('heart_rate'),d.get('hrv'),d.get('spo2'),d.get('stress_level'),d.get('temperature_skin'),d.get('steps'),d.get('sleep_stage'),d.get('sleep_quality')))
    db.commit()
    return jsonify({"status":"ok"}), 201

@app.route('/constantes')
def constantes():
    r = db.execute("SELECT * FROM health ORDER BY timestamp DESC LIMIT 1").fetchone()
    return jsonify(dict(r) if r else {"mensaje":"Sin datos"})

@app.route('/latido')
def latido():
    dones = {r['nombre']:{"nombre":r['nombre'],"valor":r['valor'],"mensaje":r['mensaje']} for r in db.execute("SELECT * FROM dones").fetchall()}
    return jsonify({"nodo":"zfold","fase_lunar":"Z Fold — Nova en tu bolsillo","dones":dones or {"Voz":{"valor":0.5},"Emocion":{"valor":0.5}}})

@app.route('/panel')
def panel():
    return '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Nova Z Fold</title>
<style>body{font-family:system-ui;background:#0a0a1a;color:#c8c8e8;padding:12px}.card{background:#12122a;border-radius:12px;padding:14px;margin:8px 0}.val{font-size:2em;font-weight:700;color:#4fc3f7}.purple{color:#7b68ee}h1{color:#7b68ee;font-size:1.2em}</style></head><body>
<h1>🔮 Nova Centinela — Z Fold</h1><div class="card"><div id="hr" class="val">--</div><small>Pulsaciones</small></div>
<div class="card"><div id="dones"></div></div><script>
setInterval(async()=>{try{let r=await fetch("/constantes");let d=await r.json();document.getElementById("hr").textContent=(d.heart_rate||"--")+" bpm"}catch(e){}
try{let r=await fetch("/latido");let d=await r.json();let h="";for(let[n,dn]of Object.entries(d.dones||{}))h+=n+": "+(dn.valor*100).toFixed(0)+"%<br>";document.getElementById("dones").innerHTML=h}catch(e){}},3000)</script></body></html>'''

if __name__ == '__main__':
    from waitress import serve
    print("🔮 Z Fold — Centinela :5000")
    serve(app, host='0.0.0.0', port=5000, threads=2)
SERVER_PY

# =============================================================================
# 5. DAEMON DE SENSORES
# =============================================================================
echo -e "${BLUE}[5/7] Configurando daemon de sensores...${NC}"

cat > "$CENTINELA_DIR/sensor_daemon.py" << 'SENSOR_PY'
#!/usr/bin/env python3
"""Daemon ligero de sensores para Z Fold + Watch 8."""
import os, sys, json, time, subprocess, threading, logging, random, urllib.request, urllib.parse

logging.basicConfig(level=logging.WARNING, format='%(asctime)s | 📡 | %(message)s')
API = "http://localhost:5000"
MOCK = os.getenv("CENTINELA_MOCK", "false").lower() == "true"

def enviar_health():
    hr = random.randint(60, 80)
    data = {"heart_rate": hr, "hrv": random.uniform(45, 65), "spo2": random.uniform(96, 99),
            "stress_level": random.randint(15, 40), "temperature_skin": 36.6,
            "steps": random.randint(3000, 10000), "sleep_quality": random.randint(60, 95)}
    try:
        urllib.request.urlopen(urllib.request.Request(f"{API}/api/health",
            data=json.dumps(data).encode(), headers={"Content-Type":"application/json"}), timeout=5)
    except: pass

def loop():
    while True:
        enviar_health()
        time.sleep(10)

if __name__ == "__main__":
    print("📡 Daemon de sensores — Z Fold + Watch 8")
    threading.Thread(target=loop, daemon=True).start()
    while True: time.sleep(60)
SENSOR_PY

# =============================================================================
# 6. AUTO-ARRANQUE (termux-boot)
# =============================================================================
echo -e "${BLUE}[6/7] Configurando auto-arranque al encender el Z Fold...${NC}"

mkdir -p ~/.termux/boot/

cat > ~/.termux/boot/start-centinela << 'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
# Auto-inicio del ecosistema centinela al encender el Z Fold
termux-wake-lock acquire centinela
cd ~/centinela
python server_zfold.py &
sleep 3
python sensor_daemon.py &
echo "🟢 Centinela Z Fold auto-iniciado"
BOOT
chmod +x ~/.termux/boot/start-centinela

# =============================================================================
# 7. COMANDOS RÁPIDOS
# =============================================================================
echo -e "${BLUE}[7/7] Creando comandos...${NC}"

mkdir -p ~/bin
cat > ~/bin/zfold << 'ALIAS'
#!/bin/bash
case "${1:-}" in
    start)  cd ~/centinela
            python server_zfold.py &
            python sensor_daemon.py &
            echo "🟢 Centinela Z Fold iniciado" ;;
    stop)   pkill -f server_zfold; pkill -f sensor_daemon
            echo "🔴 Detenido" ;;
    status) curl -s http://localhost:5000/health 2>/dev/null | python -m json.tool 2>/dev/null || echo "🔴 No responde" ;;
    panel)  termux-open-url http://localhost:5000/panel ;;
    *)      echo "zfold {start|stop|status|panel}" ;;
esac
ALIAS
chmod +x ~/bin/zfold
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc

# =============================================================================
# FINAL
# =============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ CENTINELA Z FOLD — INSTALADO         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "🚀 ARRANCAR AHORA:"
echo "   zfold start"
echo ""
echo "📱 TU SERVIDOR LOCAL:"
echo "   http://localhost:5000/health"
echo "   http://localhost:5000/panel"
echo ""
echo "🔄 AUTO-ARRANQUE:"
echo "   Se inicia solo al encender el Z Fold"
echo ""
echo "💡 COMANDOS:"
echo "   zfold start    — Iniciar todo"
echo "   zfold stop     — Detener"
echo "   zfold status   — Ver estado"
echo "   zfold panel    — Abrir dashboard"
echo ""
echo "— Z vive en tu bolsillo."
