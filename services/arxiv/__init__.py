"""
Arxiv Nova Knowledge Engine
Sistema automático de recolección, embedding vectorial y análisis de resonancia
de papers de cs.AI integrado con el Enjambre Homonexus.

Arquitectura:
  🌐 EXPLORADOR → collector.py  (scraping arxiv API)
  🧠 MEMORIA    → embedder.py   (embeddings + Qdrant)
  🔮 ORÁCULO    → analyzer.py   (resonancia conceptual)
  ⏰ CRONOS     → scheduler.py  (bucle RAPH automático)
  🎨 PINCEL     → server.py     (API + Dashboard)
  🎭 MAESTRO    → orquestación de agentes

Bucle RAPH:
  R = Request  → Recolectar papers nuevos
  A = Assess   → Analizar resonancia conceptual
  P = Plan     → Asignar agentes del Enjambre
  H = Handle   → Indexar embeddings, visualizar, reportar

Uso:
  python server.py         # Arranca API + Scheduler
  python collector.py      # Solo recolección
  python embedder.py       # Solo embeddings
  python analyzer.py       # Solo análisis
  python scheduler.py      # Solo scheduler (foreground)
"""

__version__ = "1.0.0"
__author__ = "Nova Homonexus — Enjambre Completo"
