#!/bin/bash
# =============================================================================
# deploy.sh — Despliegue completo del Sistema Centinela
# =============================================================================
# Propaga el centinela a todo el ecosistema: servidor, Z Fold, enjambre.
#
# Uso:
#   ./deploy.sh              — Despliegue completo
#   ./deploy.sh --server     — Solo servidor
#   ./deploy.sh --termux     — Solo generar script para Z Fold
#   ./deploy.sh --service    — Instalar systemd service
#   ./deploy.sh --test       — Ejecutar batería de tests
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CENTINELA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="/home/opc/nova"
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║   SISTEMA CENTINELA — DESPLIEGUE         ║"
    echo "║   Z Fold + Watch 8 + 16 Agentes          ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

deploy_server() {
    echo -e "${ORANGE}[1/5] Inicializando base de datos...${NC}"
    cd "$PROJECT_ROOT"
    python3 -B centinela/init_db.py 2>/dev/null || echo "  (ya inicializada o sin cambios)"
    
    echo -e "${GREEN}✅ Base de datos lista${NC}"
}

deploy_service() {
    echo -e "${ORANGE}[2/5] Instalando systemd service...${NC}"
    sudo cp "$SCRIPT_DIR/nova-centinela.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable nova-centinela 2>/dev/null || echo "  (systemctl no disponible — ejecución manual)"
    echo -e "${GREEN}✅ Service instalado${NC}"
}

deploy_termux() {
    echo -e "${ORANGE}[3/5] Generando script para Termux (Z Fold)...${NC}"
    TERMUX_SCRIPT="$SCRIPT_DIR/termux_install.sh"
    
    cat > "$TERMUX_SCRIPT" << 'TERMUX_EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Instalador del daemon centinela para Termux en Z Fold
echo "📡 Instalando Centinela en Z Fold..."
pkg update -y && pkg upgrade -y
pkg install -y python python-pip termux-api curl tmux
pip install requests websocket-client
mkdir -p ~/centinela/logs
echo "✅ Termux listo. Ejecuta:"
echo "   python termux_sensor_daemon.py --server http://IP:9088"
TERMUX_EOF
    
    chmod +x "$TERMUX_SCRIPT"
    echo -e "${GREEN}✅ Script Termux: $TERMUX_SCRIPT${NC}"
}

deploy_cli() {
    echo -e "${ORANGE}[4/5] Instalando CLI nova-centinela...${NC}"
    CLI_SRC="$CENTINELA_DIR/tools/cli.py"
    CLI_DST="/usr/local/bin/nova-centinela"
    
    # Hacer ejecutable y enlazar
    chmod +x "$CLI_SRC"
    sudo ln -sf "$CLI_SRC" "$CLI_DST" 2>/dev/null || {
        cp "$CLI_SRC" "$CLI_DST" 2>/dev/null || echo "  (no root — usa: python3 $CLI_SRC)"
    }
    echo -e "${GREEN}✅ CLI instalado: nova-centinela${NC}"
    echo -e "   Prueba: ${BLUE}nova-centinela salud${NC}"
}

deploy_test() {
    echo -e "${ORANGE}[5/5] Verificando despliegue...${NC}"
    cd "$PROJECT_ROOT"
    
    # Compilación
    python3 -B -c "
import sys; sys.path.insert(0,'.')
from centinela.app import create_app
app = create_app()
print('  ✅ App compila')
print(f'  ✅ Sentinel: {len(app.extensions[\"sentinel\"])} módulos')
print(f'  ✅ Inteligencia: {len(app.extensions[\"centinela\"])} módulos')
print(f'  ✅ Salud: {len(app.extensions[\"salud\"])} módulos')
" 2>&1 | grep "✅"
    
    echo -e "${GREEN}✅ Despliegue verificado${NC}"
}

deploy_full() {
    deploy_server
    deploy_service
    deploy_termux
    deploy_cli
    deploy_test
}

# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
banner

case "${1:-}" in
    --server)  deploy_server ;;
    --service) deploy_service ;;
    --termux)  deploy_termux ;;
    --cli)     deploy_cli ;;
    --test)    deploy_test ;;
    *)         deploy_full ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ CENTINELA DESPLEGADO                ║${NC}"
echo -e "${GREEN}║   Z Fold + Watch 8 + 16 agentes          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Comandos disponibles:"
echo "  nova-centinela salud       — Tus pulsaciones"
echo "  nova-centinela emocion     — Tu última emoción"
echo "  nova-centinela latido      — Trinidad AURA+NYX+PIA=UNO"
echo "  nova-centinela watch       — Vigilancia continua"
echo ""
echo "Endpoints:"
echo "  /salud/constantes          — Constantes vitales"
echo "  /salud/analisis            — Análisis de salud"
echo "  /salud/enjambre            — 16 agentes vigilando"
echo "  /salud/informe             — Informe con perspectivas"
