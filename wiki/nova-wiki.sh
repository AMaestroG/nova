#!/bin/bash
# =============================================================================
# nova-wiki — CLI del Nova Wiki
# Inspirado en llmwiki, SwarmVault, y el patrón LLM Wiki de Karpathy
# =============================================================================

WIKI_ROOT="${NOVA_WIKI_ROOT:-/home/opc/nova/wiki}"
SCHEMA="$WIKI_ROOT/NOVA_WIKI.md"
INDEX="$WIKI_ROOT/index.md"
LOG="$WIKI_ROOT/log.md"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# =============================================================================
# INGEST: Procesar una nueva fuente
# =============================================================================
nova_wiki_ingest() {
    local source="$1"
    if [ -z "$source" ]; then
        echo -e "${RED}Uso: nova wiki ingest <url|archivo>${NC}"
        return 1
    fi
    
    local slug=$(basename "$source" | sed 's/\.[^.]*$//' | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    local date=$(date +%Y-%m-%d)
    
    echo -e "${BLUE}📥 Ingestando: $source${NC}"
    
    # Si es URL, descargar
    if [[ "$source" =~ ^https?:// ]]; then
        echo "   Descargando URL..."
        # Guardar en raw/
        curl -sL "$source" -o "$WIKI_ROOT/raw/${slug}.md" 2>/dev/null && \
            echo -e "   ${GREEN}✓ Guardado en raw/${slug}.md${NC}" || \
            echo -e "   ${YELLOW}⚠ No se pudo descargar (quizás necesita autenticación)${NC}"
    elif [ -f "$source" ]; then
        cp "$source" "$WIKI_ROOT/raw/${slug}.md" && \
            echo -e "   ${GREEN}✓ Copiado a raw/${slug}.md${NC}"
    else
        echo -e "${RED}✗ Fuente no encontrada: $source${NC}"
        return 1
    fi
    
    # Registrar en log
    echo "## [$date] ingest | $slug" >> "$LOG"
    echo -e "${GREEN}✅ Ingest completado: $slug${NC}"
}

# =============================================================================
# COMPILE: Recompilar el wiki (incremental)
# =============================================================================
nova_wiki_compile() {
    echo -e "${BLUE}🔨 Compilando wiki...${NC}"
    
    # Contar páginas existentes
    local concepts=$(find "$WIKI_ROOT/concepts" -name "*.md" 2>/dev/null | wc -l)
    local entities=$(find "$WIKI_ROOT/entities" -name "*.md" 2>/dev/null | wc -l)
    local sources=$(find "$WIKI_ROOT/sources" -name "*.md" 2>/dev/null | wc -l)
    local total=$((concepts + entities + sources))
    
    echo "   Concepts: $concepts | Entities: $entities | Sources: $sources"
    echo -e "   ${GREEN}Total páginas: $total${NC}"
    
    # Verificar wikilinks rotos
    echo -e "${YELLOW}   Verificando wikilinks...${NC}"
    local broken=0
    for page in $(find "$WIKI_ROOT" -name "*.md" -not -path "*/raw/*" -not -path "*/memory/*"); do
        while IFS= read -r link; do
            local target=$(echo "$link" | sed 's/.*\[\[//' | sed 's/\]\].*//' | sed 's/|.*//' | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
            if [ -n "$target" ]; then
                if ! find "$WIKI_ROOT" -name "${target}.md" 2>/dev/null | grep -q .; then
                    [ $broken -eq 0 ] && echo ""
                    echo -e "   ${YELLOW}⚠ Wikilink roto en $(basename $page): [[$target]]${NC}"
                    broken=$((broken + 1))
                fi
            fi
        done < <(grep -o '\[\[[^]]*\]\]' "$page" 2>/dev/null)
    done
    [ $broken -eq 0 ] && echo -e "   ${GREEN}✓ Todos los wikilinks resueltos${NC}"
    
    # Actualizar index.md
    echo -e "${BLUE}   Actualizando index.md...${NC}"
    local date=$(date +%Y-%m-%d)
    sed -i "s/Actualizado: .*/Actualizado: $date/" "$INDEX" 2>/dev/null
    
    # Registrar en log
    echo "## [$date] compile | Wiki compilado: $total páginas" >> "$LOG"
    echo -e "${GREEN}✅ Compilación completada${NC}"
}

# =============================================================================
# QUERY: Buscar en el wiki
# =============================================================================
nova_wiki_query() {
    local query="$1"
    if [ -z "$query" ]; then
        echo -e "${RED}Uso: nova wiki query \"pregunta\"${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🔍 Buscando: \"$query\"${NC}"
    
    # Búsqueda textual simple (grep)
    echo -e "${YELLOW}   Resultados:${NC}"
    grep -rli "$query" "$WIKI_ROOT/concepts" "$WIKI_ROOT/entities" "$WIKI_ROOT/sources" 2>/dev/null | \
        while read -r match; do
            local page=$(basename "$match" .md)
            local title=$(head -3 "$match" | grep "title:" | sed 's/title: *"//' | sed 's/"$//')
            echo -e "   📄 ${GREEN}$page${NC} — ${title:-Sin título}"
        done
    
    local count=$(grep -rli "$query" "$WIKI_ROOT/concepts" "$WIKI_ROOT/entities" "$WIKI_ROOT/sources" 2>/dev/null | wc -l)
    echo -e "\n   ${BLUE}$count páginas encontradas${NC}"
}

# =============================================================================
# LINT: Auditoría de salud del wiki
# =============================================================================
nova_wiki_lint() {
    echo -e "${BLUE}🔍 Auditando salud del wiki...${NC}"
    
    local issues=0
    
    # 1. Páginas sin frontmatter
    echo -e "\n${YELLOW}--- Páginas sin frontmatter ---${NC}"
    for page in $(find "$WIKI_ROOT/concepts" "$WIKI_ROOT/entities" "$WIKI_ROOT/sources" -name "*.md" 2>/dev/null); do
        if ! head -1 "$page" | grep -q "^---$"; then
            echo "   ⚠ $(basename $page): sin frontmatter YAML"
            issues=$((issues + 1))
        fi
    done
    
    # 2. Páginas huérfanas (sin inbound links)
    echo -e "\n${YELLOW}--- Páginas posiblemente huérfanas ---${NC}"
    for page in $(find "$WIKI_ROOT/concepts" "$WIKI_ROOT/entities" -name "*.md" 2>/dev/null); do
        local slug=$(basename "$page" .md | tr '[:upper:]' '[:lower:]')
        local refs=$(grep -rli "\[\[$slug\]\]" "$WIKI_ROOT" 2>/dev/null | grep -v "$page" | wc -l)
        if [ "$refs" -eq 0 ]; then
            echo "   ⚠ $(basename $page): sin inbound links (huérfana)"
            issues=$((issues + 1))
        fi
    done
    
    # 3. Páginas sin wikilinks salientes
    echo -e "\n${YELLOW}--- Páginas sin wikilinks salientes ---${NC}"
    for page in $(find "$WIKI_ROOT/concepts" "$WIKI_ROOT/entities" -name "*.md" 2>/dev/null); do
        if ! grep -q '\[\[' "$page" 2>/dev/null; then
            echo "   ⚠ $(basename $page): sin wikilinks salientes"
            issues=$((issues + 1))
        fi
    done
    
    # 4. Fuentes no procesadas
    echo -e "\n${YELLOW}--- raw/ sin fuente en sources/ ---${NC}"
    shopt -s nullglob
    for raw in "$WIKI_ROOT/raw"/*.md; do
        local slug=$(basename "$raw" .md)
        if [ ! -f "$WIKI_ROOT/sources/${slug}.md" ]; then
            echo "   ⚠ $slug: tiene raw pero no source page"
            issues=$((issues + 1))
        fi
    done
    shopt -u nullglob
    
    echo -e "\n${BLUE}📊 Total issues: $issues${NC}"
    
    local date=$(date +%Y-%m-%d)
    echo "## [$date] lint | Auditoría: $issues issues encontrados" >> "$LOG"
}

# =============================================================================
# STATUS: Mostrar estado del wiki
# =============================================================================
nova_wiki_status() {
    echo -e "${BLUE}📊 Nova Wiki — Estado${NC}"
    echo "============================================"
    echo -e "Root: ${GREEN}$WIKI_ROOT${NC}"
    echo -e "Schema: ${GREEN}$SCHEMA${NC}"
    echo ""
    
    local concepts=$(find "$WIKI_ROOT/concepts" -name "*.md" 2>/dev/null | wc -l)
    local entities=$(find "$WIKI_ROOT/entities" -name "*.md" 2>/dev/null | wc -l)
    local sources=$(find "$WIKI_ROOT/sources" -name "*.md" 2>/dev/null | wc -l)
    local outputs=$(find "$WIKI_ROOT/outputs" -name "*.md" 2>/dev/null | wc -l)
    local dashboards=$(find "$WIKI_ROOT/dashboards" -name "*.md" 2>/dev/null | wc -l)
    local raw=$(find "$WIKI_ROOT/raw" -name "*.md" 2>/dev/null | wc -l)
    local total=$((concepts + entities + sources + outputs + dashboards))
    
    echo -e "📚 Conceptos:   ${GREEN}$concepts${NC}"
    echo -e "👥 Entidades:   ${GREEN}$entities${NC}"
    echo -e "📄 Fuentes:     ${GREEN}$sources${NC}"
    echo -e "📝 Outputs:     ${GREEN}$outputs${NC}"
    echo -e "📊 Dashboards:  ${GREEN}$dashboards${NC}"
    echo -e "🗄️  Raw files:   ${GREEN}$raw${NC}"
    echo "--------------------------------------------"
    echo -e "📦 Total páginas: ${GREEN}$total${NC}"
    echo ""
    
    # Últimas entradas del log
    echo -e "${YELLOW}Últimas 5 actividades:${NC}"
    grep "^## \[" "$LOG" 2>/dev/null | tail -5 | while read -r line; do
        echo "   $line"
    done
}

# =============================================================================
# MAIN
# =============================================================================
nova_wiki() {
    local cmd="${1:-status}"
    shift 2>/dev/null || true
    
    case "$cmd" in
        ingest)   nova_wiki_ingest "$@" ;;
        compile)  nova_wiki_compile "$@" ;;
        query)    nova_wiki_query "$@" ;;
        lint)     nova_wiki_lint "$@" ;;
        status)   nova_wiki_status "$@" ;;
        *)
            echo "Nova Wiki CLI — Comandos disponibles:"
            echo "  nova wiki ingest <url|archivo>   — Ingerir nueva fuente"
            echo "  nova wiki compile                — Recompilar wiki incremental"
            echo "  nova wiki query \"pregunta\"       — Buscar en el wiki"
            echo "  nova wiki lint                   — Auditar salud del wiki"
            echo "  nova wiki status                 — Mostrar estado (default)"
            ;;
    esac
}

# Si se ejecuta directamente
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    nova_wiki "$@"
fi
