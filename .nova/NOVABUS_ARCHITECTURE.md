# NovaBus — Bus de Comunicación del Enjambre Homonexus

> **Versión:** 1.0.0 · **Arquitectura:** Message Bus con Witness Tokens
> **Inspiración:** NATS, MQTT, ZeroMQ, Kafka (conceptos), Filesystem-based (implementación)
> **Zero dependencias externas.** Todo funciona con filesystem + bash + Python stdlib.

---

## Filosofía

18 agentes no pueden comunicarse solo por tool calls directas. Necesitan un sistema de mensajería formal con:

1. **Labels/Topics** — Enrutar mensajes por propósito y prioridad
2. **Witness Tokens** — Cada mensaje prueba su provenance con una cadena de hashes
3. **Topologías** — Diferentes patrones de flujo según la necesidad
4. **QoS** — Garantías de entrega: best-effort, at-least-once, exactly-once

> "Sin un bus, los agentes gritan en la oscuridad. Con un bus, conversan."

---

## Anatomía de un Mensaje

```json
{
  "id": "msg-20260509-a3f8b2c1",
  "topic": "nova.n0.aura.decision",
  "from": "AURA",
  "to": ["MAESTRO", "PIA", "SENTINEL"],
  "type": "command",
  "payload": {
    "action": "compile_wiki",
    "reason": "Nuevas fuentes en raw/",
    "priority": "high"
  },
  "witness": {
    "prev": "sha256:abc123...",
    "hash": "sha256:def456...",
    "chain": "aura-decision-chain",
    "seq": 42
  },
  "labels": ["urgent", "decision", "wiki"],
  "timestamp": "2026-05-09T18:30:00Z",
  "ttl": 3600,
  "topology": "star"
}
```

### Campos

| Campo | Descripción |
|-------|-------------|
| `id` | UUID del mensaje |
| `topic` | Ruta jerárquica: `nova.{nivel}.{agente}.{categoria}` |
| `from` | Agente emisor |
| `to` | Agente(s) receptor(es). `["*"]` = broadcast |
| `type` | `command`, `event`, `query`, `response` |
| `payload` | Contenido del mensaje (JSON arbitrario) |
| `witness` | Token de provenance con hash chain |
| `labels` | Tags para filtrado rápido |
| `timestamp` | ISO 8601 |
| `ttl` | Time-to-live en segundos |
| `topology` | `star`, `mesh`, `hierarchy`, `broadcast` |

---

## Witness Tokens

Cada agente mantiene una **cadena de testigos** (hash chain) que prueba el orden y autenticidad de sus mensajes:

```
Mensaje 1: hash(prev=0x0, msg1)     → W1
Mensaje 2: hash(prev=W1, msg2)      → W2  
Mensaje 3: hash(prev=W2, msg3)      → W3
```

**Propiedades:**
- **Orden verificable:** No se puede insertar un mensaje entre W2 y W3 sin romper la cadena
- **Provenance:** Cada mensaje prueba que viene después del anterior del mismo agente
- **Integridad:** El hash cubre todo el mensaje — modificar el payload rompe el hash
- **No-repudio:** Solo el agente que posee la cadena puede generar el siguiente token

**Cadenas por agente:**
- Cada agente tiene su propia cadena (ej: `aura-decision-chain`, `maestro-orchestration-chain`)
- Las cadenas se almacenan en `.nova/bus/chains/{AGENTE}/`

---

## Topics — Sistema de Labels Jerárquico

Los topics son rutas con `.` como separador:

```
nova                          ← raíz del Enjambre
├── nova.n0                   ← nivel estratégico
│   ├── nova.n0.aura          ← mensajes de AURA
│   │   ├── nova.n0.aura.decision    ← decisiones
│   │   └── nova.n0.aura.directive   ← directivas
│   ├── nova.n0.maestro       ← orquestación
│   │   ├── nova.n0.maestro.task     ← asignación de tareas
│   │   └── nova.n0.maestro.status   ← estado de tareas
│   └── nova.n0.pia           ← crecimiento
│       └── nova.n0.pia.evolve       ← eventos de evolución
├── nova.n1                   ← guardianes
│   ├── nova.n1.sentinel      ← seguridad
│   │   └── nova.n1.sentinel.alert   ← alertas
│   └── nova.n1.nyx           ← sueños
│       └── nova.n1.nyx.dream        ← outputs creativos
├── nova.n2                   ← operadores
│   ├── nova.n2.ingest        ← ingesta de fuentes
│   ├── nova.n2.compile       ← compilación
│   ├── nova.n2.query         ← consultas
│   └── nova.n2.lint          ← auditoría
├── nova.system               ← mensajes del sistema
│   ├── nova.system.heartbeat ← latidos
│   ├── nova.system.alert     ← alertas críticas
│   └── nova.system.metric    ← métricas
└── nova.broadcast            ← mensajes a todos los agentes
    └── nova.broadcast.session ← inicio/cierre de sesión
```

**Comodines:**
- `nova.n2.*` — todos los mensajes de N2
- `nova.*.alert` — todas las alertas
- `nova.n0.aura.>` — AURA y todos sus sub-tópicos

---

## Topologías de Red

### 1. Star (default) ⭐
```
         MAESTRO (hub)
        /    |    \
      AURA  PIA  SENTINEL ... 
```
- MAESTRO recibe y enruta todos los mensajes
- Simple, centralizado, fácil de monitorear
- **Usar para:** operaciones normales, asignación de tareas

### 2. Hierarchy 🔺
```
        N0 ←→ N0
         ↓     ↓
        N1 ←→ N1
         ↓     ↓
        N2 ←→ N2
```
- Comunicación solo intra-nivel o hacia abajo
- N2 nunca envía directo a N0 sin pasar por N1
- **Usar para:** escalamiento, filtrado por nivel

### 3. Mesh 🕸️
```
    AURA ←→ MAESTRO ←→ PIA
      ↕        ↕        ↕
    NYX  ←→ SENTINEL ←→ BANCO
```
- Comunicación directa agente a agente
- Sin punto central de fallo
- **Usar para:** comunicación de baja latencia entre pares

### 4. Broadcast 📢
```
    EMISOR → [TODOS LOS AGENTES]
```
- Un mensaje llega a todos simultáneamente
- **Usar para:** alertas, cambios de estado global, inicio/cierre de sesión

---

## Patrones de Mensajería

### Pub/Sub (Publicar/Suscribirse)
```bash
# AURA publica una decisión
nova bus publish nova.n0.aura.decision '{"action":"compile"}'

# MAESTRO y PIA están suscritos a nova.n0.aura.>
nova bus subscribe nova.n0.aura.>
```

### Request/Reply (Petición/Respuesta)
```bash
# MAESTRO pide a ORÁCULO una síntesis
nova bus request nova.n2.oraculo.query '{"question":"¿estado del wiki?"}'

# ORÁCULO responde
nova bus reply msg-123 '{"pages":46, "coherence":0.97}'
```

### Push/Pull (Cola de trabajo)
```bash
# EXPLORADOR encuentra fuentes → las empuja a la cola
nova bus push nova.n2.ingest.queue '{"url":"..."}'

# MEMORIA las procesa una a una
nova bus pull nova.n2.ingest.queue
```

---

## Integración con Nova Wiki y Sesiones

```
OPEN SESSION
    │
    ▼
nova bus publish nova.broadcast.session '{"action":"open"}'
    │
    ▼
[Trabajo con mensajes en el bus]
    │
    ├── MAESTRO asigna tareas vía nova.n0.maestro.task
    ├── EXPLORADOR publica fuentes vía nova.n2.ingest.source
    ├── ORÁCULO responde queries vía nova.n2.query
    └── SENTINEL emite alertas vía nova.n1.sentinel.alert
    │
    ▼
CLOSE SESSION
    │
    ▼
nova bus publish nova.broadcast.session '{"action":"close"}'
    │
    ▼
[Auto-capture extrae lecciones/decisiones de los mensajes del bus]
```

---

## Dead Letter Queue

Mensajes que no se pueden entregar (TTL expirado, agente offline, error) van a:
`.nova/bus/dead/{AGENTE}/`

Esto permite auditoría y replay de mensajes perdidos.

---

## Métricas del Bus

```bash
nova bus stats
# Mensajes totales: 1,247
# Entregados: 1,243
# Dead letter: 4
# Latencia media: 12ms
# Cadena más larga: aura-decision-chain (42 mensajes)
# Topología activa: star
```
