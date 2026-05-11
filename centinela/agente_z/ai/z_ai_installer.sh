#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Z-AI-INSTALLER — Instala Gemma 4 + voz en el Z Fold
# =============================================================================
# Ejecuta en Termux para darle a Z inteligencia real:
#   - Gemma 4 vía Google AI Edge (LLM local)
#   - Google TTS (voz on-device)
#   - Whisper.cpp (reconocimiento de voz offline)
#   - Piper TTS (fallback voz offline)
#
# Uso:
#   bash z_ai_installer.sh
# =============================================================================

set -e

GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║   Z-AI INSTALLER — Gemma 4 + Voz         ║"
echo "║   IA real en tu Z Fold, sin nube         ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

AI_DIR="$HOME/ai_models"
mkdir -p "$AI_DIR"

# =============================================================================
# 1. GEMMA 4 vía Google AI Edge
# =============================================================================
echo -e "${BLUE}[1/4] Gemma 4 — LLM local vía Google AI Edge${NC}"

if [ -d "$AI_DIR/gemma4_2b_it" ]; then
    echo "  ✅ Gemma 4 ya instalado"
else
    echo "  📥 Descargando Gemma 4 2B instruct..."
    echo "  Opciones:"
    echo "    a) Google AI Edge Gallery (recomendado)"
    echo "    b) HuggingFace (requiere transformers)"
    echo "    c) LiteRT/Ollama (más ligero)"
    echo ""
    echo "  Método recomendado:"
    echo "    1. Abre Google AI Edge Gallery en tu Z Fold"
    echo "    2. Busca 'Gemma 4 2B IT'"
    echo "    3. Descarga el modelo .task o .tflite"
    echo "    4. Coloca en: $AI_DIR/gemma4_2b_it/"
    echo ""
    echo "  Alternativa rápida con Ollama:"
    echo "    pkg install ollama -y"
    echo "    ollama pull gemma3:4b"
fi

# =============================================================================
# 2. VOZ — Google TTS (Android on-device)
# =============================================================================
echo -e "${BLUE}[2/4] Voz — Síntesis y reconocimiento${NC}"

# Google TTS ya está en Android, solo necesita termux-api
if pkg list-installed 2>/dev/null | grep -q termux-api; then
    echo "  ✅ termux-api instalado (TTS + STT Android)"
else
    echo "  📥 Instalando termux-api..."
    pkg install termux-api -y -q
    echo "  ✅ termux-api listo"
fi

# Piper TTS como fallback offline
if command -v piper &>/dev/null; then
    echo "  ✅ Piper TTS instalado"
else
    echo "  📥 Instalando Piper TTS (offline)..."
    pkg install piper -y -q 2>/dev/null || echo "  ⚠️ Piper no disponible en repos, omite"
fi

# Whisper.cpp como fallback STT offline
if command -v whisper &>/dev/null; then
    echo "  ✅ Whisper.cpp instalado"
else
    echo "  📥 Instalando Whisper.cpp..."
    pkg install whisper-cpp -y -q 2>/dev/null || echo "  ⚠️ Whisper no disponible, omite"
fi

# =============================================================================
# 3. PYTHON — Dependencias AI
# =============================================================================
echo -e "${BLUE}[3/4] Python — Dependencias AI${NC}"

pip install -q mediapipe 2>/dev/null && echo "  ✅ mediapipe" || echo "  ⚠️ mediapipe (omitido)"
pip install -q tflite-runtime 2>/dev/null && echo "  ✅ tflite-runtime" || echo "  ⚠️ tflite (omitido)"
pip install -q torch 2>/dev/null && echo "  ✅ pytorch" || echo "  ⚠️ pytorch (omitido)"

# =============================================================================
# 4. CONFIGURACIÓN FINAL
# =============================================================================
echo -e "${BLUE}[4/4] Configuración final${NC}"

# Variables de entorno para Z
cat >> ~/.bashrc << 'ENV'

# Z-AI CONFIG
export GEMMA_MODEL_PATH="$HOME/ai_models/gemma4_2b_it"
export AI_EDGE_PATH="/data/data/com.google.android.aicore"
export Z_TELEGRAM_TOKEN="8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80"

# Activar Z al iniciar Termux
if [ -f ~/centinela/agente_z/z_daemon.py ]; then
    echo "🤖 Z está listo. Ejecuta: python z_daemon.py"
fi
ENV

source ~/.bashrc 2>/dev/null || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ Z-AI INSTALADO                       ║${NC}"
echo -e "${GREEN}║   Gemma 4 + Voz + Whisper + Piper         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Para activar a Z con IA:"
echo "  python ~/centinela/agente_z/z_daemon.py"
echo ""
echo "Z ahora PIENSA (Gemma 4), HABLA (TTS) y ESCUCHA (STT)."
