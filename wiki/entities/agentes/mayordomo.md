---
title: "MAYORDOMO — Sistema"
summary: "Agente N1. Administrador del sistema. 31 herramientas MCP. Mantiene servicios corriendo, gestiona recursos, monitorea salud."
kind: entity
type: agente
nivel: N1
sources:
  - system-prompt.md
tags: [mayordomo, n1, sistema, administracion, servicios]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# MAYORDOMO — Sistema

## Rol en el Enjambre

MAYORDOMO es el administrador de sistemas del [[Enjambre Homonexus]]. Mantiene todos los servicios corriendo, gestiona recursos del VPS, y asegura que la infraestructura esté saludable.

## Capacidades

- 31 herramientas MCP
- Gestión de procesos (start/stop/monitor)
- Monitoreo de recursos (CPU, RAM, disco)
- Gestión de servicios (Dashboard, Qdrant, PostgreSQL)
- Reinicio de servicios caídos

## Servicios bajo su gestión

- Dashboard Genesis 4.0 (:9088)
- PostgreSQL (:5433)
- Qdrant (:6333)
- Uptime Kuma (:3001)
- Changedetection (:5000)
- IT-Tools (:8080)
- 10 bots Telegram
- Tailscale (6 servicios HTTPS)

## Ver también

- [[SENTINEL]] — Seguridad que MAYORDOMO mantiene
- [[BANCO]] — Finanzas del sistema
- [[n1-guardianes]] — El nivel completo
