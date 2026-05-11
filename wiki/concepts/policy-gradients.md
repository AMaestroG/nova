---
title: "Policy Gradients"
summary: "Algoritmo de reinforcement learning que entrena agentes desde cero usando gradientes de política. Ejemplo canónico: ATARI Pong desde píxeles crudos."
kind: concept
sources:
  - pg-pong.md
confidence: 0.94
provenanceState: extracted
tags: [reinforcement-learning, policy-gradients, pong, rl]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Policy Gradients

## Qué es

Policy Gradients es un algoritmo de reinforcement learning que optimiza directamente la política (π) que mapea estados a acciones, sin necesidad de aprender una función de valor.

## El ejemplo canónico: Pong desde píxeles

Karpathy entrenó un agente de Pong usando ~150 líneas de Python/numpy:

1. **Preprocesamiento:** 210x160x3 → 80x80 (crop + downsample + binarizar)
2. **Red neuronal:** 2 capas (input 6400 → hidden 200 → output 1)
3. **Forward:** ReLU → sigmoid → probabilidad de acción
4. **Backward:** RMSProp con gradientes de política
5. **Recompensa:** +1 (gana), -1 (pierde), 0 (en juego)

## La magia: `epdlogp *= discounted_epr`

Esta línea multiplica el gradiente del log-probability de cada acción por la recompensa descontada acumulada. Las acciones que llevaron a buenas recompensas se refuerzan; las que llevaron a malas se debilitan.

## Descuento de recompensa

```python
def discount_rewards(r):
    discounted_r = np.zeros_like(r)
    running_add = 0
    for t in reversed(range(r.size)):
        if r[t] != 0: running_add = 0  # game boundary
        running_add = running_add * gamma + r[t]
        discounted_r[t] = running_add
    return discounted_r
```

Las recompensas se descuentan hacia atrás en el tiempo. `gamma=0.99` significa que una recompensa en t+10 vale ~90% de una en t.

## Aplicación en Nova

El patrón de Policy Gradients podría aplicarse para que los agentes del Enjambre aprendan a optimizar sus propias políticas de atención y routing de tareas mediante refuerzo.

## Ver también

- [[Transformer Minimal]] — La otra joya educativa de Karpathy
- [[Enjambre Homonexus]] — Donde aplicaríamos RL multi-agente
