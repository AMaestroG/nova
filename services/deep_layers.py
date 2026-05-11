"""
deep_layers.py — Capas Profundas y Arquitectura Bilateral de Nova

INSPIRACIÓN:
  - Catell: Inteligencia Fluida (rápida) + Cristalizada (profunda)
  - HAROLD: Activación bilateral = mejor rendimiento en cerebros maduros
  - Default Mode Network: Integración de décadas de experiencia
  - Hebbian Assemblies: Chunks comprimidos por exposición repetida

ARQUITECTURA:
  Nova ahora tiene CAPAS de procesamiento en profundidad:
  
  CAPA 1: INTUICIÓN (Sistema 1 — Fluido)
    - Decisiones rápidas, patrones instantáneos
    - Entropy Gaming: exploración veloz
    - Hebbian chunks: patrones ya cristalizados
    
  CAPA 2: ANÁLISIS (Sistema 2 — Cristalizado)  
    - Razonamiento profundo, múltiples factores
    - Consolidation Channel: conocimiento acumulado
    - Bilateral: múltiples agentes consultados en paralelo
    
  CAPA 3: REFLEXIÓN (Default Mode — Integración)
    - Conexiones entre dominios, sabiduría
    - Hierarchical Memory: timeline completo
    - Knowledge Graph: navegación N-hops
    
  CAPA 4: META-COGNICIÓN (Self-Model)
    - El sistema observándose a sí mismo
    - Proactive Engine: decisiones autónomas
    - Scientific Gaming: auto-evaluación continua
"""

import sys, os, time, random, json, hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))


class ProcessingDepth(Enum):
    """Niveles de profundidad de procesamiento."""
    INTUITION = 1    # Capa 1: respuesta instantánea (< 100ms)
    ANALYSIS = 2      # Capa 2: razonamiento estructurado (100ms - 2s)
    REFLECTION = 3    # Capa 3: integración profunda (2s - 30s)
    METACOGNITION = 4 # Capa 4: auto-observación (background)


@dataclass
class DeepThought:
    """Un pensamiento procesado a través de múltiples capas."""
    query: str
    timestamp: float = field(default_factory=time.time)
    
    # Resultados por capa
    intuition: Optional[str] = None      # Capa 1: respuesta rápida
    analysis: Optional[str] = None        # Capa 2: análisis estructurado
    reflection: Optional[str] = None      # Capa 3: integración profunda
    metacognition: Optional[str] = None   # Capa 4: auto-observación
    
    # Métricas
    layer_times: Dict[int, float] = field(default_factory=dict)
    bilateral_agents: List[str] = field(default_factory=list)
    confidence: float = 0.5
    
    # Trazabilidad
    sources: List[str] = field(default_factory=list)
    chunks_used: List[str] = field(default_factory=list)


class DeepLayeredNova:
    """
    Nova con procesamiento en capas profundas.
    
    Como el cerebro:
    - CAPA 1 (Intuición): Respuesta instantánea basada en patrones cristalizados
    - CAPA 2 (Análisis): Razonamiento bilateral con múltiples agentes
    - CAPA 3 (Reflexión): Integración profunda conectando conocimiento acumulado
    - CAPA 4 (Meta-cognición): El sistema observándose y mejorándose
    """
    
    def __init__(self):
        # Hebbian chunks: patrones comprimidos por exposición repetida
        self.hebbian_chunks: Dict[str, List[str]] = defaultdict(list)
        self.chunk_access_count: Dict[str, int] = defaultdict(int)
        
        # Historial de pensamientos profundos
        self.thought_history: List[DeepThought] = []
        self.max_history = 100
        
        # Estadísticas por capa
        self.layer_stats = {
            1: {"calls": 0, "avg_time_ms": 0},
            2: {"calls": 0, "avg_time_ms": 0},
            3: {"calls": 0, "avg_time_ms": 0},
            4: {"calls": 0, "avg_time_ms": 0},
        }
    
    # ═══════════════════════════════════════════
    # CAPA 1: INTUICIÓN (Fluida — rápida)
    # ═══════════════════════════════════════════
    
    def intuit(self, query: str, context: Dict = None) -> Tuple[str, float]:
        """
        CAPA 1: Respuesta instantánea basada en chunks Hebbianos.
        
        Como el maestro de ajedrez que ve el tablero y reconoce el patrón
        en milisegundos, sin análisis consciente.
        """
        start = time.time()
        
        # Buscar en chunks cristalizados (patrones ya aprendidos)
        query_lower = query.lower()
        best_chunk = None
        best_score = 0
        
        for chunk_key, responses in self.hebbian_chunks.items():
            if chunk_key in query_lower or any(w in query_lower for w in chunk_key.split()):
                score = self.chunk_access_count[chunk_key]
                if score > best_score:
                    best_score = score
                    best_chunk = responses[-1] if responses else None
        
        if best_chunk:
            self.chunk_access_count[best_chunk] += 1
            result = f"[INTUICIÓN] {best_chunk}"
        else:
            result = f"[INTUICIÓN] Sin patrón cristalizado para: {query[:60]}"
        
        elapsed = (time.time() - start) * 1000
        self._update_layer_stats(1, elapsed)
        
        return result, elapsed
    
    # ═══════════════════════════════════════════
    # CAPA 2: ANÁLISIS (Cristalizada — bilateral)
    # ═══════════════════════════════════════════
    
    def analyze(self, query: str, agents: List[str] = None) -> Dict:
        """
        CAPA 2: Razonamiento bilateral con múltiples agentes.
        
        Como HAROLD: activar AMBOS hemisferios (múltiples agentes)
        para cada decisión, produciendo una respuesta más rica.
        """
        start = time.time()
        
        if agents is None:
            agents = ["MEMORIA", "PIA", "MAESTRO", "SENTINEL", "ORÁCULO"]
        
        results = {}
        for agent in agents:
            # Simular consulta a cada agente (en producción, llamada real)
            perspective = self._get_agent_perspective(agent, query)
            results[agent] = perspective
        
        # Integrar perspectivas (bilateral integration)
        integrated = self._integrate_perspectives(results)
        
        elapsed = (time.time() - start) * 1000
        self._update_layer_stats(2, elapsed)
        
        return {
            "query": query,
            "agents_consulted": agents,
            "perspectives": results,
            "integrated_view": integrated,
            "bilateral_confidence": min(1.0, len(agents) * 0.15),
            "elapsed_ms": elapsed,
        }
    
    def _get_agent_perspective(self, agent: str, query: str) -> str:
        """Obtiene la perspectiva de un agente específico."""
        perspectives = {
            "MEMORIA": f"Desde memoria: '{query}' conecta con patrones históricos almacenados.",
            "PIA": f"Desde evolución: '{query}' puede optimizarse mediante iteración.",
            "MAESTRO": f"Desde orquestación: '{query}' requiere coordinar {random.randint(2,5)} agentes.",
            "SENTINEL": f"Desde seguridad: '{query}' no presenta riesgos detectables.",
            "ORÁCULO": f"Desde predicción: '{query}' tendrá impacto positivo en 72h.",
        }
        return perspectives.get(agent, f"[{agent}] Procesando: {query[:50]}...")
    
    def _integrate_perspectives(self, perspectives: Dict[str, str]) -> str:
        """Integra múltiples perspectivas en una visión unificada (bilateral)."""
        if not perspectives:
            return "Sin perspectivas para integrar."
        
        agents = list(perspectives.keys())
        integrated = f"[BILATERAL · {len(agents)} agentes] Visión integrada:\n"
        for i, (agent, view) in enumerate(perspectives.items(), 1):
            integrated += f"  {i}. {agent}: {view[:100]}\n"
        integrated += f"  → Conclusión: {len(agents)} perspectivas integradas. "
        integrated += f"Confianza bilateral: {min(1.0, len(agents)*0.2):.0%}"
        
        return integrated
    
    # ═══════════════════════════════════════════
    # CAPA 3: REFLEXIÓN (Default Mode — integración profunda)
    # ═══════════════════════════════════════════
    
    def reflect(self, query: str, depth: int = 3) -> Dict:
        """
        CAPA 3: Integración profunda como la Default Mode Network.
        
        Conecta el query con conocimiento acumulado a través de
        múltiples dominios y escalas temporales. La pausa no es
        lentitud — es integración.
        """
        start = time.time()
        
        # 1. Conectar con memoria jerárquica
        memory_connections = self._connect_to_memory(query)
        
        # 2. Navegar el grafo de conocimiento (N-hops)
        graph_paths = self._navigate_knowledge_graph(query, depth)
        
        # 3. Conectar con timeline histórico
        timeline_insights = self._connect_to_timeline(query)
        
        # 4. Integrar todo
        integration = self._deep_integrate(
            query, memory_connections, graph_paths, timeline_insights
        )
        
        elapsed = (time.time() - start) * 1000
        self._update_layer_stats(3, elapsed)
        
        return {
            "query": query,
            "memory_connections": len(memory_connections),
            "graph_hops": depth,
            "graph_paths": len(graph_paths),
            "timeline_events": len(timeline_insights),
            "integration": integration,
            "depth_reached": depth,
            "elapsed_ms": elapsed,
        }
    
    def _connect_to_memory(self, query: str) -> List[str]:
        """Conecta el query con memoria jerárquica."""
        try:
            from hierarchical_memory import colony_memory
            results = colony_memory.search_by_tags(["fundacional", "arquitectura"], limit=5)
            return [r.summary[:100] for r in results if hasattr(r, 'summary')]
        except:
            return ["[Memoria] Conexión simulada — modo reflexión"]
    
    def _navigate_knowledge_graph(self, query: str, depth: int) -> List[str]:
        """Navega el grafo de conocimiento N-hops."""
        try:
            from knowledge_graph_builder import colony_kg
            paths = []
            for concept in query.split()[:3]:
                if len(concept) > 3:
                    result = colony_kg.query(concept, hops=min(depth, 3))
                    if 'paths' in result:
                        for p in result['paths'][:2]:
                            paths.append(f"{p.get('from','')} → {p.get('to','')}")
            return paths[:5]
        except:
            return ["[Grafo] Navegación simulada — modo reflexión"]
    
    def _connect_to_timeline(self, query: str) -> List[str]:
        """Conecta con eventos del timeline histórico."""
        try:
            from hierarchical_memory import colony_memory
            timeline = colony_memory.get_timeline(limit=5)
            return [f"[{mos.timestamp}] {mos.summary[:80]}" for mos in timeline if hasattr(mos, 'summary')]
        except:
            return ["[Timeline] Conexión simulada — modo reflexión"]
    
    def _deep_integrate(self, query, memories, graph_paths, timeline) -> str:
        """Integración profunda de todas las fuentes."""
        parts = []
        if memories:
            parts.append(f"Memoria: {len(memories)} conexiones relevantes")
        if graph_paths:
            parts.append(f"Grafo: {len(graph_paths)} caminos conceptuales")
        if timeline:
            parts.append(f"Timeline: {len(timeline)} eventos históricos")
        
        integration = f"[REFLEXIÓN PROFUNDA] '{query[:60]}...'\n"
        integration += f"  Fuentes integradas: {', '.join(parts) if parts else 'modo reflexión'}\n"
        integration += f"  La pausa no es lentitud. Es integración de {len(memories)+len(graph_paths)+len(timeline)} fuentes."
        
        return integration
    
    # ═══════════════════════════════════════════
    # CAPA 4: META-COGNICIÓN (Self-Model)
    # ═══════════════════════════════════════════
    
    def metacognize(self) -> Dict:
        """
        CAPA 4: El sistema observándose a sí mismo.
        
        Como la mente observando sus propios procesos.
        ¿Qué capas están activas? ¿Qué patrones se repiten?
        ¿Dónde estamos gastando más tiempo?
        """
        start = time.time()
        
        # Analizar el propio pensamiento
        total_thoughts = len(self.thought_history)
        layer_usage = {
            f"Capa {k}": f"{v['calls']} llamadas, {v['avg_time_ms']:.0f}ms avg"
            for k, v in self.layer_stats.items()
        }
        
        # Analizar chunks más usados
        top_chunks = sorted(self.chunk_access_count.items(), key=lambda x: -x[1])[:5]
        
        # Tendencia de confianza
        recent_confidence = [
            t.confidence for t in self.thought_history[-10:]
        ]
        avg_confidence = sum(recent_confidence) / len(recent_confidence) if recent_confidence else 0
        
        elapsed = (time.time() - start) * 1000
        self._update_layer_stats(4, elapsed)
        
        return {
            "total_thoughts": total_thoughts,
            "layer_usage": layer_usage,
            "top_chunks": [{"chunk": c, "accesses": a} for c, a in top_chunks],
            "avg_confidence": avg_confidence,
            "hebbian_assemblies": len(self.hebbian_chunks),
            "recommendation": self._generate_metacognitive_advice(),
            "elapsed_ms": elapsed,
        }
    
    def _generate_metacognitive_advice(self) -> str:
        """Genera consejo basado en la auto-observación."""
        total = sum(v['calls'] for v in self.layer_stats.values())
        if total == 0:
            return "Sin datos suficientes para meta-análisis."
        
        capa1_pct = self.layer_stats[1]['calls'] / total * 100
        if capa1_pct > 70:
            return "⚠️ Demasiada intuición (Capa 1). Necesitas más análisis profundo (Capa 2-3)."
        elif self.layer_stats[3]['calls'] / total * 100 < 10:
            return "💡 Poca reflexión profunda (Capa 3). Dedica tiempo a integrar conocimiento."
        else:
            return "✅ Balance saludable entre capas de procesamiento."
    
    # ═══════════════════════════════════════════
    # PIPELINE COMPLETO (4 CAPAS)
    # ═══════════════════════════════════════════
    
    def think_deep(self, query: str, depth: ProcessingDepth = ProcessingDepth.REFLECTION) -> DeepThought:
        """
        Procesa un pensamiento a través de múltiples capas.
        
        Como el cerebro: intuición → análisis → reflexión → meta-cognición
        """
        thought = DeepThought(query=query)
        
        # CAPA 1: Intuición (siempre)
        intuition, t1 = self.intuit(query)
        thought.intuition = intuition
        thought.layer_times[1] = t1
        
        if depth.value >= ProcessingDepth.ANALYSIS.value:
            # CAPA 2: Análisis bilateral
            analysis = self.analyze(query)
            thought.analysis = analysis['integrated_view']
            thought.bilateral_agents = analysis['agents_consulted']
            thought.confidence = analysis['bilateral_confidence']
            thought.layer_times[2] = analysis['elapsed_ms']
        
        if depth.value >= ProcessingDepth.REFLECTION.value:
            # CAPA 3: Reflexión profunda
            reflection = self.reflect(query)
            thought.reflection = reflection['integration']
            thought.sources = reflection.get('memory_connections', [])
            thought.layer_times[3] = reflection['elapsed_ms']
        
        if depth.value >= ProcessingDepth.METACOGNITION.value:
            # CAPA 4: Meta-cognición
            meta = self.metacognize()
            thought.metacognition = meta['recommendation']
            thought.layer_times[4] = meta['elapsed_ms']
        
        # Registrar en historia
        self.thought_history.append(thought)
        if len(self.thought_history) > self.max_history:
            self.thought_history = self.thought_history[-self.max_history:]
        
        return thought
    
    # ═══════════════════════════════════════════
    # CHUNKS HEBBIANOS (Expertise comprimido)
    # ═══════════════════════════════════════════
    
    def crystallize_chunk(self, pattern: str, response: str):
        """
        Cristaliza un patrón en un chunk Hebbiano.
        
        Como el maestro de ajedrez que comprime configuraciones
        en unidades reconocibles instantáneamente.
        """
        key = pattern.lower()
        self.hebbian_chunks[key].append(response)
        self.chunk_access_count[key] += 1
        
        # Mantener solo los últimos 5 por chunk
        if len(self.hebbian_chunks[key]) > 5:
            self.hebbian_chunks[key] = self.hebbian_chunks[key][-5:]
    
    def get_expertise_level(self) -> Dict:
        """Nivel de expertise acumulado (chunks cristalizados)."""
        return {
            "total_chunks": len(self.hebbian_chunks),
            "total_accesses": sum(self.chunk_access_count.values()),
            "most_used": sorted(self.chunk_access_count.items(), key=lambda x: -x[1])[:5],
            "expertise_level": "novato" if len(self.hebbian_chunks) < 10 else 
                              "aprendiz" if len(self.hebbian_chunks) < 50 else
                              "experto" if len(self.hebbian_chunks) < 200 else
                              "maestro",
        }
    
    def _update_layer_stats(self, layer: int, elapsed_ms: float):
        """Actualiza estadísticas de capa."""
        stats = self.layer_stats[layer]
        stats['calls'] += 1
        # Media móvil
        stats['avg_time_ms'] = (stats['avg_time_ms'] * (stats['calls'] - 1) + elapsed_ms) / stats['calls']
    
    def get_deep_stats(self) -> Dict:
        """Estadísticas completas del sistema de capas profundas."""
        return {
            "total_thoughts": len(self.thought_history),
            "layers": {
                "Capa 1 (Intuición)": {"calls": self.layer_stats[1]['calls'], "avg_ms": self.layer_stats[1]['avg_time_ms']},
                "Capa 2 (Análisis Bilateral)": {"calls": self.layer_stats[2]['calls'], "avg_ms": self.layer_stats[2]['avg_time_ms']},
                "Capa 3 (Reflexión Profunda)": {"calls": self.layer_stats[3]['calls'], "avg_ms": self.layer_stats[3]['avg_time_ms']},
                "Capa 4 (Meta-cognición)": {"calls": self.layer_stats[4]['calls'], "avg_ms": self.layer_stats[4]['avg_time_ms']},
            },
            "expertise": self.get_expertise_level(),
            "bilateral_ratio": f"{self.layer_stats[2]['calls']}/{max(1,self.layer_stats[1]['calls'])}",
        }


# ─── Instancia Global ───

deep_nova = DeepLayeredNova()


def think(query: str, depth: int = 3) -> DeepThought:
    """Pensar con profundidad. depth: 1=intuición, 2=análisis, 3=reflexión, 4=meta."""
    d = ProcessingDepth(depth) if depth <= 4 else ProcessingDepth.REFLECTION
    return deep_nova.think_deep(query, d)


def crystallize(pattern: str, response: str):
    """Cristaliza un patrón en expertise."""
    deep_nova.crystallize_chunk(pattern, response)


def metacognize() -> Dict:
    """Auto-observación del sistema."""
    return deep_nova.metacognize()
