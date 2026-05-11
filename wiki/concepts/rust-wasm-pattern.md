---
title: "Rust → WASM — Bridge Pattern para el Dashboard"
summary: "Patrón arquitectónico: compilar lógica en Rust a WebAssembly para ejecución en el navegador. Aplicable a Nova Dashboard Genesis 4.0 y extensiones Chrome."
kind: concept
sources:
  - https://www.youtube.com/watch?v=example-rust-wasm
confidence: 0.90
provenanceState: extracted
tags: [rust, wasm, browser, dashboard, performance]
createdAt: "2026-05-09T20:00:00Z"
updatedAt: "2026-05-09T20:00:00Z"
---

# Rust → WASM — Bridge Pattern

## El patrón

```
┌──────────────┐    wasm-bindgen    ┌──────────────────┐
│  Rust (lógica)│ ◄──────────────► │  JavaScript (UI)  │
│  • rápido     │    puente/glue    │  • HTML/CSS       │
│  • seguro     │                   │  • Chrome API      │
│  • portable   │                   │  • DOM             │
└──────────────┘                   └──────────────────┘
        │                                    │
        ▼                                    ▼
   compila a WASM                      fetch + init
   (binary .wasm)                      (raw bytes → module)
```

## Flujo

1. **Rust:** Escribir lógica de negocio en Rust
2. **wasm-bindgen:** Anotar funciones con `#[wasm_bindgen]` para exponerlas
3. **wasm-pack:** Compilar a WebAssembly (`wasm-pack build --target web`)
4. **JS:** Fetch del `.wasm`, convertir a bytes binarios, inicializar módulo
5. **Browser:** Llamar funciones Rust desde JavaScript

## Por qué importa para Nova

### 1. Dashboard Genesis 4.0 (Flask :9088)
El dashboard actual usa NovaOS JS (89KB). Podemos:
- Mover procesamiento pesado a WASM (métricas, parseo, búsqueda)
- Reducir latencia en el frontend
- Usar Rust para operaciones que requieren precisión (cálculo de coherence, hash chains)

### 2. Nova Chrome Extension
Podemos crear una extensión Chrome que:
- Muestre estado del Enjambre en tiempo real
- Permita queries al wiki desde el navegador
- Notifique eventos del bus (alertas, decisiones)
- Muestre métricas del NovaBus

### 3. Análogo al Enjambre
El patrón Rust↔JS bridge es análogo a nuestra arquitectura de agentes:
- **Rust = N2 (operadores):** Lógica pesada, eficiente, especializada
- **JS/HTML = N0 (interfaz):** Presentación, interacción
- **wasm-bindgen = NovaBus:** El puente que permite comunicación

## Demo: Nova Text Metrics (WASM)

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn count_words(text: &str) -> usize {
    text.split_whitespace().count()
}

#[wasm_bindgen]
pub fn count_chars(text: &str) -> usize {
    text.chars().count()
}

#[wasm_bindgen]
pub fn count_sentences(text: &str) -> usize {
    text.split(|c| c == '.' || c == '!' || c == '?')
        .filter(|s| !s.trim().is_empty())
        .count()
}
```

## Cómo integrar en Nova Dashboard

```html
<script type="module">
  import init, { count_words, count_chars } from './nova_wasm.js';
  
  async function loadWasm() {
    await init();
    // WASM listo — ahora podemos usar funciones Rust
    const words = count_words(novaWikiContent);
    document.getElementById('wiki-stats').textContent = words;
  }
  
  loadWasm();
</script>
```

## Ver también

- [[MCP Tools]] — Otro patrón de bridge (agentes ↔ herramientas)
- [[NovaBus Architecture]] — El bus como puente entre agentes
- [[NovaOS Dashboard]] — Donde se aplicaría WASM
- [[Neural Attention Engine]] — Candidato a compilar a WASM
