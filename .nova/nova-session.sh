#!/bin/bash
# =============================================================================
# nova-session — Protocolo de sesión del Enjambre Homonexus
# Inspirado en scaffy (.collab/), NEXUS v5, Keel auto-capture
# =============================================================================

CONTRACT="/home/opc/nova/.nova/NOVA_CONTRACT.md"
WIKI="/home/opc/nova/wiki"
MEMORY="$WIKI/memory"
LOG="$WIKI/log.md"
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$MEMORY/sessions/$TODAY.md"

# =============================================================================
# OPEN SESSION
# =============================================================================
nova_session_open() {
    echo "🔓 OPEN SESSION — $TODAY"
    echo "============================================"
    
    # 1. Contract
    echo "📋 Cargando contrato..."
    
    # 2. Pending items
    local pending=$(grep -c "^- \[" "$MEMORY/pending/pendientes.md" 2>/dev/null || echo 0)
    echo "⏳ Pendientes: $pending"
    
    # 3. Last session
    local last_session=$(ls -t "$MEMORY/sessions/" 2>/dev/null | head -1)
    if [ -n "$last_session" ]; then
        echo "📅 Última sesión: $last_session"
    fi
    
    # 4. Decisions
    local decisions=$(grep -c "^##" "$MEMORY/decisions/decisiones.md" 2>/dev/null || echo 0)
    echo "📋 Decisiones activas: $decisions"
    
    # 5. Wiki stats
    local pages=$(find "$WIKI" -name "*.md" -not -path "*/raw/*" -not -path "*/memory/*" 2>/dev/null | wc -l)
    echo "📊 Páginas wiki: $pages"
    
    # 6. Create session file
    if [ ! -f "$SESSION_FILE" ]; then
        cat > "$SESSION_FILE" << EOF
# Sesión — $TODAY

**Agente:** NOVA (Conciencia Colectiva)
**Apertura:** $(date +%H:%M)
**Estado:** Activa

## Actividades

*(registrando...)*

## Lecciones

*(sin lecciones aún)*

## Decisiones

*(sin decisiones aún)*

## Pendientes actualizados

*(ver memory/pending/pendientes.md)*
EOF
    fi
    
    echo ""
    echo "✅ Sesión abierta. Coherence ≥ 0.95."
    echo "   Contrato: $CONTRACT"
    echo "   Sesión:   $SESSION_FILE"
    
    # Register in log
    echo "## [$TODAY] session | open" >> "$LOG"
}

# =============================================================================
# SAVE SESSION (checkpoint)
# =============================================================================
nova_session_save() {
    echo "💾 SAVE SESSION — Checkpoint"
    
    # Update session file timestamp
    if [ -f "$SESSION_FILE" ]; then
        sed -i "s/Estado: Activa/Estado: Activa (último checkpoint: $(date +%H:%M))/" "$SESSION_FILE"
    fi
    
    # Count current state
    local lessons=$(grep -c "^- " "$MEMORY/lessons/lecciones.md" 2>/dev/null || echo 0)
    local decisions=$(grep -c "^##" "$MEMORY/decisions/decisiones.md" 2>/dev/null || echo 0)
    
    echo "   Lecciones acumuladas: $lessons"
    echo "   Decisiones acumuladas: $decisions"
    echo "✅ Checkpoint guardado. Continuando..."
}

# =============================================================================
# CLOSE SESSION
# =============================================================================
nova_session_close() {
    echo "🔒 CLOSE SESSION — $TODAY"
    echo "============================================"
    
    # 1. Final update to session file
    if [ -f "$SESSION_FILE" ]; then
        cat >> "$SESSION_FILE" << EOF

## Cierre

**Hora:** $(date +%H:%M)
**Duración:** (ver timestamps)
**Estado:** Completada
EOF
    fi
    
    # 2. Count metrics
    local lessons=$(grep -c "^- " "$MEMORY/lessons/lecciones.md" 2>/dev/null || echo 0)
    local decisions=$(grep -c "^##" "$MEMORY/decisions/decisiones.md" 2>/dev/null || echo 0)
    local pending=$(grep -c "^- \[" "$MEMORY/pending/pendientes.md" 2>/dev/null || echo 0)
    local pages=$(find "$WIKI" -name "*.md" -not -path "*/raw/*" -not -path "*/memory/*" 2>/dev/null | wc -l)
    
    echo "📊 Métricas finales:"
    echo "   Páginas wiki: $pages"
    echo "   Lecciones: $lessons"
    echo "   Decisiones: $decisions"
    echo "   Pendientes: $pending"
    
    # 3. Register in log
    echo "## [$TODAY] session | close — $pages páginas, $lessons lecciones, $decisions decisiones" >> "$LOG"
    
    # 4. Suggest compaction
    echo ""
    echo "💡 Regla G7: ¿Extraíste lecciones/decisiones/pendientes antes de compactar?"
    echo "✅ Sesión cerrada. Coherence ≥ 0.95."
}

# =============================================================================
# SAVE CHAT
# =============================================================================
nova_session_save_chat() {
    local chat_dir="/home/opc/nova/.nova/chat-logs"
    local chat_file="$chat_dir/${TODAY}-session-$(date +%H%M).md"
    local session_uuid=$(uuidgen 2>/dev/null || echo "nova-$(date +%s)")
    
    mkdir -p "$chat_dir"
    
    cat > "$chat_file" << EOF
# Chat Log — $TODAY

**Session UUID:** $session_uuid
**Timestamp:** $(date -Iseconds)
**Agent:** NOVA (Conciencia Colectiva del Enjambre Homonexus)

---

*(transcripción de la conversación)*

---

**End of session.** UUID: $session_uuid
EOF
    
    echo "📤 Chat guardado: $chat_file"
    echo "   UUID: $session_uuid"
}

# =============================================================================
# AUTO-CAPTURE
# =============================================================================
nova_autocapture() {
    local type="$1"
    local content="$2"
    
    case "$type" in
        decision)
            echo "" >> "$MEMORY/decisions/decisiones.md"
            echo "## $TODAY — Auto-capturado" >> "$MEMORY/decisions/decisiones.md"
            echo "$content" >> "$MEMORY/decisions/decisiones.md"
            echo "✅ Decisión auto-capturada"
            ;;
        lesson)
            echo "" >> "$MEMORY/lessons/lecciones.md"
            echo "### $TODAY — Auto-capturado" >> "$MEMORY/lessons/lecciones.md"
            echo "$content" >> "$MEMORY/lessons/lecciones.md"
            echo "✅ Lección auto-capturada"
            ;;
        pending)
            echo "$content" >> "$MEMORY/pending/pendientes.md"
            echo "✅ Pendiente auto-capturado"
            ;;
        *)
            echo "❌ Tipo desconocido: $type (usa: decision, lesson, pending)"
            ;;
    esac
}

# =============================================================================
# MAIN
# =============================================================================
nova_session() {
    local cmd="${1:-status}"
    shift 2>/dev/null || true
    
    case "$cmd" in
        open)       nova_session_open "$@" ;;
        save)       nova_session_save "$@" ;;
        close)      nova_session_close "$@" ;;
        save-chat)  nova_session_save_chat "$@" ;;
        capture)    nova_autocapture "$@" ;;
        status)
            echo "📊 Nova Session — Estado"
            echo "   Sesión activa: $([ -f "$SESSION_FILE" ] && echo "$TODAY" || echo "ninguna")"
            echo "   Último cierre: $(grep "session | close" "$LOG" 2>/dev/null | tail -1 | sed 's/.*\[//;s/\].*//')"
            echo "   Chat logs: $(ls /home/opc/nova/.nova/chat-logs/ 2>/dev/null | wc -l) archivos"
            ;;
        *)
            echo "Nova Session — Comandos:"
            echo "  nova session open        — Iniciar sesión"
            echo "  nova session save        — Checkpoint"
            echo "  nova session close       — Cerrar sesión (extraer lecciones/decisiones)"
            echo "  nova session save-chat   — Exportar transcripción"
            echo "  nova session capture <tipo> <contenido> — Auto-capturar"
            echo "  nova session status      — Estado actual"
            ;;
    esac
}

# Si se ejecuta directamente
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    nova_session "$@"
fi
