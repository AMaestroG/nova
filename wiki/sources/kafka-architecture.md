---
title: "Kafka Architecture — Lecciones para NovaBus"
summary: "Análisis de arquitectura Kafka extraído de video tutorial: topics, particiones, consumer groups, serialización. Lecciones aplicadas a NovaBus v2.0."
kind: source
sources:
  - https://www.youtube.com/watch?v=example
confidence: 0.92
provenanceState: extracted
tags: [kafka, novabus, arquitectura, mensajeria]
createdAt: "2026-05-09T19:00:00Z"
updatedAt: "2026-05-09T19:00:00Z"
---

# Kafka Architecture — Lecciones para NovaBus

## Conceptos clave extraídos

1. **Topics**: buzones donde llegan eventos. NovaBus implementa topics jerárquicos (`nova.banking.transaction`).
2. **Particiones**: cada topic se divide en N particiones para paralelismo. NovaBus usa particiones virtuales por hash de clave.
3. **Consumer Groups**: grupos independientes consumiendo el mismo topic con offsets propios. NovaBus v2.0 implementa esto con `consumer-group`.
4. **Serialización**: eventos → binario para eficiencia. NovaBus implementa message envelope con gzip + base64.
5. **Retención TTL**: eventos viven 1-7 días. NovaBus tiene `retention` con TTL configurable.
6. **Dead Letter Queue**: NovaBus ya tenía esto nativo (Kafka requiere external).
7. **Witness Tokens**: NovaBus tiene hash chain SHA-256 (Kafka no tiene equivalente nativo).

## Comparación con el ejemplo bancario

| Componente | Ejemplo Kafka | Equivalente NovaBus |
|-----------|---------------|---------------------|
| Producer | API HTTP → serializa → topic | `nova bus publish` |
| Topics | transacciones, fraudes, alertas, métricas | `nova.banking.*` |
| Consumer: Persistencia | → PostgreSQL | MEMORIA → PostgreSQL |
| Consumer: Fraude | → evalúa → topic alertas | SENTINEL → evalúa → alerta |
| Consumer: Métricas | → Prometheus → Grafana | `nova bus stats` + dashboard HTML |
| Dashboard | Grafana en tiempo real | Nova Dashboard Genesis 4.0 |

## Ver también
- [[NovaBus Architecture]]
- [[LLM Wiki Pattern]]
