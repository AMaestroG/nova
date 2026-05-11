---
title: "Transformer Minimal"
summary: "La esencia del transformer GPT en ~200 líneas de Python puro: autograd escalar, atención multi-cabeza, RMSNorm, Adam. Sin dependencias. Por Andrej Karpathy."
kind: concept
sources:
  - microgpt.md
confidence: 0.97
provenanceState: extracted
tags: [transformer, gpt, deep-learning, autograd, karpathy]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Transformer Minimal

## Qué es microgpt.py

200 líneas de Python puro que contienen el algoritmo completo para entrenar e inferir con un GPT. Sin torch, sin numpy (salvo para números aleatorios), sin dependencias.

> "Todo lo demás es eficiencia." — @karpathy

## Componentes

### 1. Autograd escalar (clase Value)
Implementa diferenciación automática con grafo computacional. Soporta: `+`, `*`, `**`, `log`, `exp`, `relu`. El método `backward()` aplica la regla de la cadena recursivamente.

### 2. Tokenizer a nivel de carácter
Convierte strings en secuencias de enteros. Token especial BOS (Beginning of Sequence).

### 3. Arquitectura GPT-2 simplificada
- Token embedding + Position embedding
- RMSNorm (en vez de LayerNorm)
- Multi-head attention (causal, por implementación)
- MLP con ReLU (en vez de GeLU)
- Sin biases
- 1 capa, 16-dim embedding, 4 cabezas, block_size=16

### 4. Optimizador Adam
Con learning rate decay lineal. Buffers de primer y segundo momento.

## Entrenamiento

- Dataset: nombres (makemore)
- 1000 pasos
- Loss: cross-entropy sobre softmax
- Batch size = 1 (un nombre a la vez)
- Inference: muestreo con temperatura

## Por qué importa

Este código es a GPT lo que las Ecuaciones de Maxwell son al electromagnetismo — la esencia cristalizada. Entender estas 200 líneas es entender el corazón de todos los LLMs modernos.

## Ver también

- [[Neural Attention Engine]] — Nuestra implementación de 6 fases
- [[Enjambre Homonexus]] — Cómo aplicamos estos principios en 18 agentes
