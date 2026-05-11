#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Script de instalación del Sistema Centinela para Termux en Samsung Z Fold
# Nova Homonexus - MAYORDOMO
#
# Este script configura Termux para ejecutar el daemon de sensores Centinela
# que lee todos los sensores del Samsung Z Fold y los envía al servidor Nova.
#
# USO:
#   chmod +x install.sh
#   ./install.sh
#
# REQUISITOS:
#   - Termux instalado desde F-Droid (NO desde Google Play)
#   - Termux:API instalado desde F-Droid
#   - Samsung Z Fold con Android 13+
#   - Conexión a Internet (WiFi recomendada)
# =============================================================================

set -e

# Colores para output
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${AZUL}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         SISTEMA CENTINELA - Instalación en Termux          ║"
echo "║         Samsung Z Fold + Galaxy Watch 8 Classic            ║"
echo "║         Nova Homonexus - MAYORDOMO                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# 1. VERIFICAR ENTORNO
# =============================================================================
echo -e "${AZUL}[1/7] Verificando entorno Termux...${NC}"

# Verificar que estamos en Termux
if [ ! -d "/data/data/com.termux" ] && [ ! -d "/data/data/com.termux.fdroid" ]; then
    echo -e "${ROJO}ERROR: Este script debe ejecutarse en Termux (Android)${NC}"
    echo "Descarga Termux desde F-Droid: https://f-droid.org/packages/com.termux/"
    exit 1
fi

echo -e "${VERDE}  ✓ Entorno Termux detectado${NC}"

# =============================================================================
# 2. SOLICITAR PERMISOS
# =============================================================================
echo -e "${AZUL}[2/7] Solicitando permisos de Android...${NC}"

# Permiso para sensores
termux-sensor -l > /dev/null 2>&1 || {
    echo -e "${AMARILLO}  ⚠ Solicitando permiso de sensores...${NC}"
    echo "  Acepta el permiso 'body_sensors' cuando aparezca"
    sleep 2
}

# Permiso para ubicación
termux-location -p > /dev/null 2>&1 || {
    echo -e "${AMARILLO}  ⚠ Solicitando permiso de ubicación...${NC}"
    echo "  Acepta el permiso 'access_fine_location' cuando aparezca"
    sleep 2
}

# Permiso para cámara
termux-camera-photo > /dev/null 2>&1 || {
    echo -e "${AMARILLO}  ⚠ Solicitando permiso de cámara...${NC}"
    echo "  Acepta el permiso 'camera' cuando aparezca"
    sleep 2
}

# Permiso para almacenamiento
termux-setup-storage > /dev/null 2>&1 || {
    echo -e "${AMARILLO}  ⚠ Solicitando permiso de almacenamiento...${NC}"
    sleep 2
}

echo -e "${VERDE}  ✓ Permisos solicitados${NC}"

# =============================================================================
# 3. ACTUALIZAR E INSTALAR PAQUETES
# =============================================================================
echo -e "${AZUL}[3/7] Actualizando repositorios e instalando paquetes...${NC}"

pkg update -y
pkg upgrade -y

# Paquetes esenciales
pkg install -y \
    python \
    python-pip \
    git \
    termux-api \
    termux-tools \
    openssh \
    curl \
    jq \
    tmux \
    nano

echo -e "${VERDE}  ✓ Paquetes instalados${NC}"

# =============================================================================
# 4. INSTALAR DEPENDENCIAS PYTHON
# =============================================================================
echo -e "${AZUL}[4/7] Instalando dependencias Python...${NC}"

pip install --upgrade pip
pip install \
    requests \
    websocket-client \
    psutil \
    python-dateutil

echo -e "${VERDE}  ✓ Dependencias Python instaladas${NC}"

# =============================================================================
# 5. CONFIGURAR DIRECTORIO Y SCRIPTS
# =============================================================================
echo -e "${AZUL}[5/7] Configurando scripts del Centinela...${NC}"

# Crear directorio
CENTINELA_DIR="$HOME/centinela"
mkdir -p "$CENTINELA_DIR"
mkdir -p "$CENTINELA_DIR/logs"
mkdir -p "$CENTINELA_DIR/data"

# Crear archivo de configuración local
cat > "$CENTINELA_DIR/config_local.sh" << 'CONFIGEOF'
# =============================================================================
# Configuración local del Sistema Centinela
# Edita este archivo con los datos de tu servidor Nova
# =============================================================================

# Dirección IP del servidor Nova (cambiar por la IP real)
export CENTINELA_SERVER="http://192.168.1.100:9088"

# API Key del sistema Centinela
export CENTINELA_API_KEY="nexus-centinela-key-2026"

# ID de este dispositivo
export CENTINELA_DEVICE_ID="samsung_zfold_01"

# Modo mock (true = datos simulados, false = sensores reales)
export CENTINELA_MOCK="false"

# Nivel de log (DEBUG, INFO, WARNING, ERROR)
export CENTINELA_LOG_LEVEL="INFO"
CONFIGEOF

chmod +x "$CENTINELA_DIR/config_local.sh"

# Crear script de inicio
cat > "$CENTINELA_DIR/iniciar_centinela.sh" << 'STARTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Iniciar Sistema Centinela en Termux
# =============================================================================

# Cargar configuración
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/config_local.sh"

echo "╔══════════════════════════════════════════════╗"
echo "║   Iniciando Sistema Centinela               ║"
echo "║   Dispositivo: $CENTINELA_DEVICE_ID"
echo "║   Servidor: $CENTINELA_SERVER"
echo "╚══════════════════════════════════════════════╝"

# Verificar conectividad con el servidor
echo "Verificando conexion con el servidor..."
if curl -s -o /dev/null -w "%{http_code}" "$CENTINELA_SERVER/api/centinela/status" \
    -H "X-API-Key: $CENTINELA_API_KEY" | grep -q "200"; then
    echo "✓ Servidor disponible"
else
    echo "⚠ Servidor no responde. Verifica la IP en config_local.sh"
    echo "  Continuando de todas formas..."
fi

# Iniciar daemon
echo "Iniciando daemon de sensores..."
cd "$SCRIPT_DIR"
python termux_sensor_daemon.py \
    --server "$CENTINELA_SERVER" \
    --api-key "$CENTINELA_API_KEY" \
    --device-id "$CENTINELA_DEVICE_ID"

if [ "$CENTINELA_MOCK" = "true" ]; then
    python termux_sensor_daemon.py \
        --server "$CENTINELA_SERVER" \
        --api-key "$CENTINELA_API_KEY" \
        --device-id "$CENTINELA_DEVICE_ID" \
        --mock
fi
STARTEOF

chmod +x "$CENTINELA_DIR/iniciar_centinela.sh"

# Copiar el daemon Python
cp "$(dirname "$0")/termux_sensor_daemon.py" "$CENTINELA_DIR/" 2>/dev/null || {
    echo -e "${AMARILLO}  ⚠ No se encontró termux_sensor_daemon.py en el directorio actual${NC}"
    echo "  Descargando desde el servidor..."
    source "$CENTINELA_DIR/config_local.sh"
    curl -s -o "$CENTINELA_DIR/termux_sensor_daemon.py" \
        "$CENTINELA_SERVER/static/termux_sensor_daemon.py" || {
        echo -e "${ROJO}  ✗ No se pudo descargar el daemon${NC}"
        echo "  Copia manualmente termux_sensor_daemon.py a $CENTINELA_DIR/"
    }
}

echo -e "${VERDE}  ✓ Scripts configurados en $CENTINELA_DIR${NC}"

# =============================================================================
# 6. CONFIGURAR INICIO AUTOMÁTICO (OPCIONAL)
# =============================================================================
echo -e "${AZUL}[6/7] Configurar inicio automático? (opcional)${NC}"
echo -n "  ¿Iniciar Centinela al abrir Termux? [s/N]: "
read -r AUTO_START

if [ "$AUTO_START" = "s" ] || [ "$AUTO_START" = "S" ]; then
    # Añadir al .bashrc
    if ! grep -q "centinela" "$HOME/.bashrc" 2>/dev/null; then
        cat >> "$HOME/.bashrc" << 'BASHRCEOF'

# =============================================================================
# Inicio automático del Sistema Centinela
# =============================================================================
if [ -f "$HOME/centinela/iniciar_centinela.sh" ]; then
    echo "Sistema Centinela listo. Ejecuta: ./centinela/iniciar_centinela.sh"
fi
BASHRCEOF
        echo -e "${VERDE}  ✓ Inicio automático configurado${NC}"
    else
        echo -e "${AMARILLO}  ⚠ Ya existe configuración de Centinela en .bashrc${NC}"
    fi
fi

# =============================================================================
# 7. RESUMEN FINAL
# =============================================================================
echo
echo -e "${AZUL}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${AZUL}║${NC}              ${VERDE}INSTALACIÓN COMPLETADA${NC}                           ${AZUL}║${NC}"
echo -e "${AZUL}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${VERDE}  📁 Directorio:${NC}     $CENTINELA_DIR"
echo -e "${VERDE}  📝 Config:${NC}         $CENTINELA_DIR/config_local.sh"
echo -e "${VERDE}  🚀 Iniciar:${NC}        $CENTINELA_DIR/iniciar_centinela.sh"
echo -e "${VERDE}  📊 Logs:${NC}           $CENTINELA_DIR/logs/"
echo
echo -e "${AMARILLO}  ⚠ ANTES DE INICIAR:${NC}"
echo "  1. Edita la configuración:"
echo "     nano $CENTINELA_DIR/config_local.sh"
echo "     → Cambia CENTINELA_SERVER por la IP de tu servidor Nova"
echo "     → Cambia CENTINELA_API_KEY si es necesario"
echo
echo "  2. Verifica conectividad:"
echo "     curl \$CENTINELA_SERVER/api/centinela/status"
echo
echo "  3. Inicia el daemon:"
echo "     cd $CENTINELA_DIR && bash iniciar_centinela.sh"
echo
echo -e "${AZUL}  💡 Para monitoreo en tiempo real, usa tmux:${NC}"
echo "     tmux new-session -s centinela"
echo "     ./iniciar_centinela.sh"
echo "     # Ctrl+B, D para desconectar"
echo "     tmux attach -t centinela  # para reconectar"
echo
echo -e "${AZUL}  📱 Sensores del Z Fold que se leerán:${NC}"
echo "     • Acelerómetro    • Giroscopio      • Magnetómetro"
echo "     • Barómetro       • Proximidad      • Luz ambiental"
echo "     • Gravedad        • Acel. lineal    • Rotación"
echo "     • Contador pasos  • GPS             • NFC"
echo
echo -e "${AZUL}  ⌚ Galaxy Watch 8 Classic (vía Health Connect):${NC}"
echo "     • Ritmo cardíaco  • ECG             • Presión arterial"
echo "     • SpO2            • Temperatura     • Estrés"
echo "     • Sueño           • Pasos           • Bioimpedancia (BIA)"
echo
echo -e "${AMARILLO}  ⚡ RECOMENDACIONES:${NC}"
echo "  • Mantén el Z Fold conectado a carga durante monitoreo prolongado"
echo "  • Usa WiFi en lugar de datos móviles para menor latencia"
echo "  • Activa 'No molestar' para evitar interrupciones"
echo "  • Mantén Termux abierto (o usa termux-wake-lock)"
echo
echo -e "${VERDE}  ¡Sistema Centinela listo para desplegar!${NC}"
