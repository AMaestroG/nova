#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# INSTALADOR COMPLETO — Nova Centinela en Z Fold (Termux)
# =============================================================================
# Un solo comando para convertir tu Z Fold en el servidor centinela.
#
# Uso en Termux:
#   curl -sL http://TU_SERVIDOR:9088/static/install_zfold.sh | bash
#   o
#   bash install_zfold.sh
# =============================================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║   NOVA CENTINELA — Z FOLD INSTALLER      ║"
echo "║   Convierte tu Z Fold en el servidor      ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

CENTINELA_DIR="$HOME/centinela"
SERVER_URL="${1:-http://192.168.1.100:9088}"

# 1. Paquetes esenciales
echo -e "${BLUE}[1/6] Instalando paquetes...${NC}"
pkg update -y -q && pkg upgrade -y -q
pkg install -y -q python python-pip termux-api curl git tmux openssh termux-services

# 2. Dependencias Python
echo -e "${BLUE}[2/6] Instalando dependencias Python...${NC}"
pip install -q flask flask-cors requests websocket-client psutil

# 3. Directorios
echo -e "${BLUE}[3/6] Creando estructura...${NC}"
mkdir -p "$CENTINELA_DIR"/{data,logs,scripts}

# 4. Descargar servidor (si hay conexión al servidor)
echo -e "${BLUE}[4/6] Descargando archivos del servidor...${NC}"
if curl -s --connect-timeout 3 "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "  Conectado al servidor Nova. Descargando módulos..."
    curl -sL "$SERVER_URL/static/servidor_zfold.py" -o "$CENTINELA_DIR/servidor_zfold.py" 2>/dev/null || true
    curl -sL "$SERVER_URL/static/termux_sensor_daemon.py" -o "$CENTINELA_DIR/termux_sensor_daemon.py" 2>/dev/null || true
else
    echo "  Sin conexión al servidor. Usa archivos locales."
fi

# 5. Auto-arranque con termux-boot
echo -e "${BLUE}[5/6] Configurando auto-arranque...${NC}"
mkdir -p ~/.termux/boot/
cat > ~/.termux/boot/start-centinela.sh << 'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
# Auto-inicio del centinela al encender el Z Fold
termux-wake-lock acquire centinela
cd ~/centinela
python servidor_zfold.py --modo solo --puerto 5000 &
python termux_sensor_daemon.py --server http://localhost:5000 --device-id samsung_zfold_01 &
BOOT
chmod +x ~/.termux/boot/start-centinela.sh
echo "  Auto-arranque configurado (requiere Termux:Boot de F-Droid)"

# 6. Comandos rápidos
echo -e "${BLUE}[6/6] Creando comandos rápidos...${NC}"
mkdir -p ~/bin
cat > ~/bin/zfold << 'ALIAS'
#!/bin/bash
case "${1:-}" in
    start)  cd ~/centinela && python servidor_zfold.py --modo solo ;;
    stop)   pkill -f servidor_zfold ;;
    status) curl -s http://localhost:5000/health | python -m json.tool ;;
    dashboard) termux-open-url http://localhost:5000/dashboard ;;
    sensores) cd ~/centinela && python termux_sensor_daemon.py --mock --server http://localhost:5000 ;;
    *) echo "Uso: zfold {start|stop|status|dashboard|sensores}" ;;
esac
ALIAS
chmod +x ~/bin/zfold
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ Z FOLD — SERVIDOR CENTINELA LISTO   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Comandos en tu Z Fold:"
echo "  zfold start        — Iniciar servidor centinela"
echo "  zfold stop         — Detener servidor"
echo "  zfold status       — Ver estado"
echo "  zfold dashboard    — Abrir dashboard en navegador"
echo "  zfold sensores     — Iniciar daemon de sensores (modo prueba)"
echo ""
echo "Endpoints (en tu Z Fold):"
echo "  http://localhost:5000/health"
echo "  http://localhost:5000/constantes"
echo "  http://localhost:5000/latido"
echo "  http://localhost:5000/dashboard"
echo ""
echo "Desde otros dispositivos en tu red:"
echo "  http://<IP_DEL_ZFOLD>:5000/dashboard"
echo ""
echo "Para exponer a internet (opcional):"
echo "  tailscale serve 5000"
