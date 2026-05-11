#!/bin/bash
# =============================================================================
# NOVA CENTINELA — RUN
# Un comando para despertar todo el ecosistema.
# =============================================================================
set -e
cd "$(dirname "$0")/.."

export Z_TELEGRAM_TOKEN="${Z_TELEGRAM_TOKEN:-8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80}"
export Z_TELEGRAM_CHAT_ID="${Z_TELEGRAM_CHAT_ID:-8519133640}"

echo "🔮 Nova Centinela — Iniciando..."
echo ""

# Matar procesos anteriores
fuser -k 9088/tcp 2>/dev/null || true
sleep 1

# Iniciar servidor
echo "🌐 Iniciando servidor Flask :9088..."
python3 -B -c "
import sys, os
sys.path.insert(0, '.')
from centinela.app import create_app
app = create_app()
app.run(host='0.0.0.0', port=9088, debug=False, use_reloader=False)
" &

sleep 4

# Verificar
if curl -s http://localhost:9088/health > /dev/null 2>&1; then
    echo "✅ Servidor Flask: ONLINE"
else
    echo "❌ Servidor no respondió"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ECOSISTEMA CENTINELA — VIVO        ║"
echo "╠══════════════════════════════════════╣"
echo "║  🌐 http://localhost:9088/health     ║"
echo "║  🖥️  http://localhost:9088/panel      ║"
echo "║  📱 @NEXUXZFOLD_BOT (Telegram)       ║"
echo "║  🛡️  Watchdog: resúmenes 8AM/8PM     ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "PID del servidor: $!"
echo "Logs: tail -f /tmp/centinela.log"

# Mantener vivo
wait
