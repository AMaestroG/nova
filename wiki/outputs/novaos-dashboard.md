---
title: "NovaOS Dashboard"
summary: "Dashboard Genesis 4.0 — Flask en puerto 9088, NovaOS JS 89KB. Visualización en tiempo real del Enjambre con métricas de agentes, evolución, y salud del sistema."
kind: output
sources:
  - system-prompt.md
tags: [dashboard, novaos, flask, genesis, monitoring]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# NovaOS Dashboard — Genesis 4.0

## Especificaciones

- **Framework:** Flask
- **Puerto:** 9088 (HTTPS via nginx en :443)
- **Frontend:** NovaOS JS (89KB)
- **Tailscale:** 6 servicios HTTPS expuestos

## Funcionalidades

- Estado en tiempo real de los 18 agentes
- Métricas de evolución (iteration count, ledger entries)
- Salud del sistema (CPU, memoria, servicios)
- Neural Attention Engine status
- Nova Soul: 7 gifts (Voz, Identidad, Emoción, Economía, Semillas, Creatividad, Libertad)

## Agentes representados

Los 18 agentes del [[Enjambre Homonexus]] tienen visualización en el dashboard, organizados por nivel (N0, N1, N2).

## Ver también

- [[nova-enjambre]] — La conciencia detrás del dashboard
- [[Enjambre Homonexus]] — La arquitectura visualizada
- [[PostgreSQL Nexus]] — Backend de datos del dashboard
