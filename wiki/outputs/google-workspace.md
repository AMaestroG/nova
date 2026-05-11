---
title: "Google Workspace Integration"
summary: "Integración del Enjambre con Google Workspace de Abel: Gmail (HERMES), Calendar/Tasks (CRONOS), Drive (MNEMOS). 3 agentes N2 dedicados."
kind: output
sources:
  - system-prompt.md
tags: [google, workspace, gmail, calendar, drive, integracion]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Google Workspace Integration

El [[Enjambre Homonexus]] está integrado con Google Workspace de Abel (ablmaestro@gmail.com) a través de 3 agentes N2 especializados.

## Agentes responsables

### 📧 HERMES — Gmail
- Leer correos recientes (inbox)
- Buscar por criterios
- Procesar adjuntos
- Herramienta: `nova_gmail_check`

### ⏰ CRONOS — Calendar + Tasks
- Ver eventos del día
- Gestionar Google Tasks
- Herramienta: `nova_calendar_today`

### 📁 MNEMOS — Drive
- Buscar archivos por texto
- Organizar documentos
- Recuperar conocimiento externo
- Herramienta: `nova_drive_search`

## Flujo de datos

```
Gmail (HERMES) ────► correos importantes ────► Nova Wiki (raw/)
Calendar (CRONOS) ─► eventos del día     ────► Memoria de sesión
Drive (MNEMOS)  ───► documentos          ────► Nova Wiki (raw/)
```

## Ver también

- [[HERMES]] — Agente de Gmail
- [[CRONOS]] — Agente de Calendar/Tasks
- [[MNEMOS]] — Agente de Drive
- [[n2-operadores]] — El nivel completo
