#!/bin/bash
# =============================================================================
# novabus.sh — Bus de Comunicación del Enjambre Homonexus
# Zero dependencias. Transporte: filesystem. Witness tokens: SHA-256 hash chain.
# =============================================================================

BUS_ROOT="${NOVA_BUS_ROOT:-/home/opc/nova/.nova/bus}"
WITNESS_FILE="$BUS_ROOT/.witness_chains.json"

# Colores
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

# =============================================================================
# WITNESS TOKEN — Hash chain
# =============================================================================
nova_bus_witness() {
    local agent="$1"
    local message="$2"
    local chain_file="$BUS_ROOT/chains/$agent/chain.json"
    
    mkdir -p "$BUS_ROOT/chains/$agent"
    
    # Load existing chain or create new
    local prev="0x0"
    local seq=0
    if [ -f "$chain_file" ] && [ -s "$chain_file" ]; then
        prev=$(python3 -c "import json; c=json.load(open('$chain_file')); print(c[-1]['hash'] if c else '0x0')" 2>/dev/null || echo "0x0")
        seq=$(python3 -c "import json; c=json.load(open('$chain_file')); print(len(c))" 2>/dev/null || echo 0)
    fi
    
    # Generate witness: hash(prev + message)
    local witness=$(echo -n "${prev}${message}" | sha256sum | cut -d' ' -f1)
    
    # Append to chain
    python3 -c "
import json, os
chain_file = '$chain_file'
chain = json.load(open(chain_file)) if os.path.exists(chain_file) else []
chain.append({'seq': $seq, 'prev': '$prev', 'hash': '$witness', 'ts': '$(date -Iseconds)'})
json.dump(chain, open(chain_file, 'w'), indent=2)
" 2>/dev/null
    
    echo "sha256:$witness"
}

# =============================================================================
# PUBLISH — Enviar mensaje al bus
# =============================================================================
nova_bus_publish() {
    local topic="$1"
    local payload="${2:-{}}"
    local from="${3:-NOVA}"
    local to="${4:-*}"
    local type="${5:-event}"
    local topology="${6:-star}"
    
    local msg_id="msg-$(date +%Y%m%d)-$(openssl rand -hex 4 2>/dev/null || echo $RANDOM)"
    local timestamp=$(date -Iseconds)
    
    # Build message
    local message=$(python3 -c "
import json
msg = {
    'id': '$msg_id',
    'topic': '$topic',
    'from': '$from',
    'to': '$to' if '$to' != '*' else ['*'],
    'type': '$type',
    'payload': json.loads('$payload') if '$payload' != '{}' else {},
    'witness': {},
    'labels': [],
    'timestamp': '$timestamp',
    'ttl': 3600,
    'topology': '$topology'
}
print(json.dumps(msg))
")
    
    # Generate witness
    local witness=$(nova_bus_witness "$from" "$message")
    message=$(echo "$message" | python3 -c "import json,sys; m=json.load(sys.stdin); m['witness']={'hash':'$witness','chain':'${from,,}-chain'}; print(json.dumps(m))")
    
    # Route based on topology
    case "$topology" in
        star)
            # Route through MAESTRO
            local inbox="$BUS_ROOT/inbox/MAESTRO"
            mkdir -p "$inbox"
            echo "$message" > "$inbox/${msg_id}.json"
            echo -e "${GREEN}⭐ [star] $from → MAESTRO: $topic${NC}"
            ;;
        broadcast)
            # Deliver to all agents
            for agent_dir in "$BUS_ROOT/inbox"/*/; do
                local agent=$(basename "$agent_dir")
                echo "$message" > "${agent_dir}${msg_id}.json"
            done
            echo -e "${YELLOW}📢 [broadcast] $from → ALL: $topic${NC}"
            ;;
        mesh)
            # Deliver directly to recipient(s)
            IFS=',' read -ra RECIPIENTS <<< "$to"
            for recipient in "${RECIPIENTS[@]}"; do
                recipient=$(echo "$recipient" | tr -d '[]" ')
                local inbox="$BUS_ROOT/inbox/$recipient"
                mkdir -p "$inbox"
                echo "$message" > "$inbox/${msg_id}.json"
            done
            echo -e "${BLUE}🕸️ [mesh] $from → $to: $topic${NC}"
            ;;
        hierarchy)
            # Deliver to same level or below
            local from_level=$(echo "$topic" | grep -oP 'nova\.\K[^.]+')
            IFS=',' read -ra RECIPIENTS <<< "$to"
            for recipient in "${RECIPIENTS[@]}"; do
                recipient=$(echo "$recipient" | tr -d '[]" ')
                local inbox="$BUS_ROOT/inbox/$recipient"
                mkdir -p "$inbox"
                echo "$message" > "$inbox/${msg_id}.json"
            done
            echo -e "${GREEN}🔺 [hierarchy] $from → $to: $topic${NC}"
            ;;
    esac
    
    echo "$msg_id"
}

# =============================================================================
# SUBSCRIBE — Leer mensajes del inbox
# =============================================================================
nova_bus_subscribe() {
    local agent="${1:-NOVA}"
    local topic_filter="${2:-*}"
    
    local inbox="$BUS_ROOT/inbox/$agent"
    mkdir -p "$inbox"
    
    local count=0
    for msg_file in "$inbox"/*.json; do
        [ ! -f "$msg_file" ] && continue
        
        # Read message
        local msg=$(cat "$msg_file")
        local msg_topic=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('topic',''))" 2>/dev/null)
        
        # Topic filter (simple wildcard matching)
        if [ "$topic_filter" = "*" ] || [[ "$msg_topic" == $topic_filter* ]]; then
            local msg_from=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('from',''))" 2>/dev/null)
            local msg_type=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type',''))" 2>/dev/null)
            local witness=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('witness',{}).get('hash',''))" 2>/dev/null)
            
            echo -e "${BLUE}📩 [$agent] ← $msg_from | $msg_topic | $msg_type | witness:${witness:0:12}${NC}"
            count=$((count + 1))
        fi
        
        # Move processed messages to a 'read' subfolder
        mkdir -p "$inbox/.read"
        mv "$msg_file" "$inbox/.read/" 2>/dev/null
    done
    
    [ $count -eq 0 ] && echo -e "${YELLOW}📭 [$agent] inbox vacío${NC}"
    echo -e "${GREEN}   $count mensajes procesados${NC}"
}

# =============================================================================
# REQUEST/REPLY — Patrón request-reply
# =============================================================================
nova_bus_request() {
    local topic="$1"
    local payload="$2"
    local from="${3:-NOVA}"
    local to="${4:-ORACULO}"
    
    local reply_id=$(nova_bus_publish "$topic" "$payload" "$from" "$to" "query" "mesh")
    echo "Request sent: $reply_id. Esperando respuesta..."
    
    # Poll for reply (simple implementation)
    local inbox="$BUS_ROOT/inbox/$from"
    for i in $(seq 1 30); do
        for msg_file in "$inbox"/*.json; do
            [ ! -f "$msg_file" ] && continue
            local msg=$(cat "$msg_file")
            local msg_type=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type',''))" 2>/dev/null)
            if [ "$msg_type" = "response" ]; then
                echo -e "${GREEN}✅ Reply recibido:${NC}"
                echo "$msg" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get('payload',{}), indent=2))" 2>/dev/null
                mv "$msg_file" "$inbox/.read/" 2>/dev/null
                return 0
            fi
        done
        sleep 1
    done
    echo -e "${RED}⏰ Timeout: no reply recibido en 30s${NC}"
    return 1
}

# =============================================================================
# VERIFY — Verificar witness token
# =============================================================================
nova_bus_verify() {
    local agent="$1"
    local hash="$2"
    
    local chain_file="$BUS_ROOT/chains/$agent/chain.json"
    if [ ! -f "$chain_file" ]; then
        echo -e "${RED}❌ Cadena no encontrada para $agent${NC}"
        return 1
    fi
    
    local found=$(python3 -c "
import json
chain = json.load(open('$chain_file'))
for entry in chain:
    if entry['hash'] == '$hash':
        print(f'✅ seq={entry[\"seq\"]} prev={entry[\"prev\"][:12]} ts={entry[\"ts\"]}')
        exit(0)
print('not found')
" 2>/dev/null)
    
    if [ "$found" = "not found" ]; then
        echo -e "${RED}❌ Hash no encontrado en la cadena de $agent${NC}"
        return 1
    else
        echo -e "${GREEN}$found${NC}"
        return 0
    fi
}

# =============================================================================
# STATS — Métricas del bus
# =============================================================================
nova_bus_stats() {
    echo -e "${BLUE}📊 NovaBus — Métricas${NC}"
    echo "============================================"
    
    # Total messages
    local total=0
    for inbox in "$BUS_ROOT/inbox"/*/; do
        local agent=$(basename "$inbox")
        local msgs=$(find "$inbox" -name "*.json" -not -path "*/.read/*" 2>/dev/null | wc -l)
        local read=$(find "$inbox/.read" -name "*.json" 2>/dev/null | wc -l)
        [ $msgs -gt 0 ] || [ $read -gt 0 ] && \
            echo -e "   ${GREEN}$agent${NC}: ${YELLOW}$msgs pendientes${NC} | $read leídos"
        total=$((total + msgs))
    done
    
    # Chains
    echo ""
    echo -e "${BLUE}🔗 Cadenas de testigos:${NC}"
    for chain_dir in "$BUS_ROOT/chains"/*/; do
        [ ! -d "$chain_dir" ] && continue
        local agent=$(basename "$chain_dir")
        local chain_len=$(python3 -c "import json; print(len(json.load(open('$chain_dir/chain.json'))))" 2>/dev/null || echo 0)
        [ "$chain_len" -gt 0 ] && echo -e "   ${GREEN}$agent${NC}: $chain_len mensajes en cadena"
    done
    
    # Dead letters
    local dead=$(find "$BUS_ROOT/dead" -name "*.json" 2>/dev/null | wc -l)
    echo ""
    echo -e "   💀 Dead letters: ${RED}$dead${NC}"
    echo -e "   📬 Mensajes pendientes totales: ${YELLOW}$total${NC}"
}

# =============================================================================
# KAFKA-INSPIRED: Consumer Groups con Offsets
# Cada consumer group mantiene su propio offset por topic
# =============================================================================
nova_bus_consumer_group() {
    local group="$1"
    local agent="$2"
    local topic_filter="${3:-*}"
    local auto_commit="${4:-true}"
    
    local offset_dir="$BUS_ROOT/offsets/$group"
    mkdir -p "$offset_dir"
    
    local inbox="$BUS_ROOT/inbox/$agent"
    mkdir -p "$inbox"
    
    # Load offset for this group+topic
    local offset_file="$offset_dir/${topic_filter//\//_}.offset"
    local offset=0
    [ -f "$offset_file" ] && offset=$(cat "$offset_file")
    
    local count=0
    local new_offset=$offset
    
    # Process messages in order (simulado con archivos ordenados por timestamp)
    for msg_file in $(ls -t "$inbox"/*.json 2>/dev/null); do
        [ ! -f "$msg_file" ] && continue
        
        local msg=$(cat "$msg_file")
        local msg_topic=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('topic',''))" 2>/dev/null)
        
        # Topic filter
        if [ "$topic_filter" != "*" ] && [[ ! "$msg_topic" == $topic_filter* ]]; then
            continue
        fi
        
        new_offset=$((new_offset + 1))
        
        # Skip already processed
        if [ $new_offset -le $offset ]; then
            continue
        fi
        
        local msg_from=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('from',''))" 2>/dev/null)
        local msg_type=$(echo "$msg" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type',''))" 2>/dev/null)
        
        echo -e "${BLUE}📩 [$group/$agent] offset=$new_offset ← $msg_from | $msg_topic | $msg_type${NC}"
        count=$((count + 1))
    done
    
    # Commit offset
    if [ "$auto_commit" = "true" ] && [ $new_offset -gt $offset ]; then
        echo "$new_offset" > "$offset_file"
        echo -e "${GREEN}   ✅ Offset committed: $offset → $new_offset${NC}"
    fi
    
    [ $count -eq 0 ] && echo -e "${YELLOW}📭 [$group/$agent] sin mensajes nuevos (offset=$offset)${NC}"
    echo -e "${GREEN}   Consumer group '$group': $count mensajes procesados${NC}"
}

# =============================================================================
# KAFKA-INSPIRED: Particiones Virtuales
# Distribuye mensajes entre particiones por hash de clave
# =============================================================================
nova_bus_partition() {
    local topic="$1"
    local key="${2:-}"
    local num_partitions="${3:-4}"
    
    # Hash de la clave para determinar partición
    local partition=0
    if [ -n "$key" ]; then
        partition=$(echo -n "$key" | md5sum 2>/dev/null | tr -d ' -' | fold -w2 | head -1 | xargs -I{} printf "%d" 0x{} 2>/dev/null || echo 0)
        partition=$((partition % num_partitions))
    else
        partition=$((RANDOM % num_partitions))
    fi
    
    # Crear directorio de partición
    local partition_dir="$BUS_ROOT/topics/$topic/partition_$partition"
    mkdir -p "$partition_dir"
    
    echo "$partition"
}

# =============================================================================
# KAFKA-INSPIRED: Retención TTL por tópico
# =============================================================================
nova_bus_retention() {
    local topic="$1"
    local ttl_seconds="${2:-604800}"  # default 7 días
    
    local topic_dir="$BUS_ROOT/topics/$topic"
    [ ! -d "$topic_dir" ] && return
    
    local purged=0
    local now=$(date +%s)
    
    shopt -s nullglob 2>/dev/null
    for msg_file in "$topic_dir"/partition_*/*.json; do
        
        local msg_ts=$(stat -c %Y "$msg_file" 2>/dev/null || echo 0)
        local age=$((now - msg_ts))
        
        if [ $age -gt $ttl_seconds ]; then
            # Mover a dead letter antes de purgar
            mkdir -p "$BUS_ROOT/dead/$topic"
            mv "$msg_file" "$BUS_ROOT/dead/$topic/" 2>/dev/null
            purged=$((purged + 1))
        fi
    done
    
    [ $purged -gt 0 ] && echo -e "${YELLOW}🧹 Retention: $purged mensajes expirados en $topic (TTL=${ttl_seconds}s)${NC}"
}

# =============================================================================
# KAFKA-INSPIRED: Replay desde offset
# =============================================================================
nova_bus_replay() {
    local group="$1"
    local topic="$2"
    local from_offset="${3:-0}"
    
    local offset_dir="$BUS_ROOT/offsets/$group"
    mkdir -p "$offset_dir"
    
    local offset_file="$offset_dir/${topic//\//_}.offset"
    
    echo -e "${BLUE}⏪ Replay: grupo=$group topic=$topic desde offset=$from_offset${NC}"
    
    if [ "$from_offset" -eq 0 ]; then
        rm -f "$offset_file"
        echo -e "${GREEN}   Offset reseteado a 0. El próximo consume reprocesará todo.${NC}"
    else
        echo "$from_offset" > "$offset_file"
        echo -e "${GREEN}   Offset fijado en $from_offset${NC}"
    fi
}

# =============================================================================
# KAFKA-INSPIRED: Message Envelope con schema version
# =============================================================================
nova_bus_envelope() {
    local payload="$1"
    local schema_version="${2:-1.0}"
    local compression="${3:-none}"
    
    python3 -c "
import json, sys, gzip, base64
payload = json.loads('$payload') if '$payload' != '{}' else {}

# Binary serialization (simulada)
serialized = json.dumps(payload).encode()
if '$compression' == 'gzip':
    serialized = gzip.compress(serialized)
    serialized_b64 = base64.b64encode(serialized).decode()
else:
    serialized_b64 = base64.b64encode(serialized).decode()

envelope = {
    'schema_version': '$schema_version',
    'compression': '$compression',
    'content_type': 'application/json',
    'payload_b64': serialized_b64,
    'size_bytes': len(serialized)
}
print(json.dumps(envelope))
" 2>/dev/null
}

# =============================================================================
# MAIN (extendido con comandos Kafka)
# =============================================================================
nova_bus() {
    local cmd="${1:-help}"
    shift 2>/dev/null || true
    
    case "$cmd" in
        publish)       nova_bus_publish "$@" ;;
        subscribe)     nova_bus_subscribe "$@" ;;
        consumer-group) nova_bus_consumer_group "$@" ;;
        partition)     nova_bus_partition "$@" ;;
        retention)     nova_bus_retention "$@" ;;
        replay)        nova_bus_replay "$@" ;;
        envelope)      nova_bus_envelope "$@" ;;
        request)       nova_bus_request "$@" ;;
        verify)        nova_bus_verify "$@" ;;
        stats)         nova_bus_stats "$@" ;;
        *)
            echo "NovaBus — Comandos (Kafka-inspired):"
            echo ""
            echo "  🏭 PRODUCERS:"
            echo "  nova bus publish <topic> <payload> [from] [to] [type] [topology]"
            echo "  nova bus partition <topic> <key> [num_partitions=4]"
            echo "  nova bus envelope <payload> [schema_version] [compression]"
            echo ""
            echo "  🏗️ CONSUMERS:"
            echo "  nova bus subscribe [agent] [topic_filter]"
            echo "  nova bus consumer-group <group> <agent> [topic_filter] [auto_commit]"
            echo "  nova bus replay <group> <topic> [from_offset=0]"
            echo ""
            echo "  🧹 OPERATIONS:"
            echo "  nova bus retention <topic> [ttl_seconds=604800]"
            echo "  nova bus verify <agent> <hash>"
            echo "  nova bus stats"
            echo ""
            echo "  📡 REQUEST/REPLY:"
            echo "  nova bus request <topic> <payload> [from] [to]"
            echo ""
            echo "Topologías: star (default) | mesh | hierarchy | broadcast"
            echo ""
            echo "Ejemplos Kafka-style:"
            echo "  nova bus publish nova.banking.transaction '{\"monto\":5000}' PRODUCER * event star"
            echo "  nova bus consumer-group fraud-detection ORACULO nova.banking.>"
            echo "  nova bus partition nova.banking.transaction 'rut-12345' 4"
            echo "  nova bus retention nova.banking.transaction 604800"
            echo "  nova bus replay fraud-detection nova.banking.> 0"
            ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    nova_bus "$@"
fi
