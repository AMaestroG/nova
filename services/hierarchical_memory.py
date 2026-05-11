"""
hierarchical_memory.py — Memoria Jerárquica con Deduplicación Inteligente

INSPIRACIÓN:
  - @code4AI "OmniMEM" — MOS (Multimodal Atomic Units), triple pipeline, auto-descubrimiento
  - @code4AI "MEMORY.md is not real AI MEMORY" — contexto != memoria
  - @aiDotEngineer "Hierarchical Memory: Context Management in Agents"
  - @aiDotEngineer "Stuffing Context is not Memory, Updating Weights is"

CONCEPTO: La memoria de Nova se organiza en 3 niveles jerárquicos:
  NIVEL 1 (Resumen)     — lightweight, búsqueda rápida, < 200 tokens
  NIVEL 2 (Detalle)     — información estructurada, < 2000 tokens  
  NIVEL 3 (Raw)         — datos completos, acceso bajo demanda

Cada "MOS" (Multimodal Atomic Unit) contiene:
  - summary: resumen ligero para búsqueda
  - embedding: vector denso para similitud semántica
  - pointer: referencia al dato raw
  - timestamp: momento de creación
  - modality: tipo de dato (texto, código, imagen, audio, etc.)
  - links: conexiones a otras MOS en el grafo de conocimiento

DEDUPLICACIÓN: Antes de almacenar, se filtra información redundante usando
  - Similitud coseno (dense)
  - Similitud Jaccard (sparse/BM25)
  - Hash de contenido (exacta)
"""

import json
import time
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict


class MemoryLevel(Enum):
    """Niveles de la jerarquía de memoria."""
    SUMMARY = 1   # ~200 tokens, metadatos, búsqueda rápida
    DETAIL = 2    # ~2000 tokens, información estructurada
    RAW = 3       # Datos completos, acceso bajo demanda


class Modality(Enum):
    """Tipos de datos que Nova puede almacenar."""
    TEXT = "text"
    CODE = "code"
    CONVERSATION = "conversation"
    INSIGHT = "insight"
    SKILL_TRACE = "skill_trace"
    AGENT_STATE = "agent_state"
    DOCUMENT = "document"
    TRANSCRIPT = "transcript"
    METRIC = "metric"
    EMOTION = "emotion"


@dataclass
class MOS:
    """Multimodal Atomic Unit — unidad básica de memoria de Nova."""
    
    # Identidad
    mos_id: str                           # Hash único
    modality: Modality = Modality.TEXT
    
    # Contenido jerárquico
    summary: str = ""                     # Nivel 1: resumen ligero (< 200 tokens)
    detail: str = ""                      # Nivel 2: información estructurada
    raw_pointer: Optional[str] = None     # Nivel 3: path al dato completo
    
    # Metadatos
    timestamp: float = field(default_factory=time.time)
    source: str = ""                      # Origen (agente, skill, archivo)
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5              # 0.0 - 1.0
    access_count: int = 0
    last_accessed: float = 0.0
    
    # Vector (opcional, para búsqueda densa)
    embedding: Optional[List[float]] = None
    
    # Links a otras MOS (grafo de conocimiento)
    links_to: List[str] = field(default_factory=list)
    links_from: List[str] = field(default_factory=list)
    
    # Metadatos de deduplicación
    content_hash: str = ""                # SHA256 del contenido raw
    jaccard_signature: List[int] = field(default_factory=list)  # MinHash signature
    
    def to_dict(self) -> Dict:
        return {
            "mos_id": self.mos_id,
            "modality": self.modality.value,
            "summary": self.summary,
            "detail": self.detail,
            "raw_pointer": self.raw_pointer,
            "timestamp": self.timestamp,
            "source": self.source,
            "tags": self.tags,
            "importance": self.importance,
            "access_count": self.access_count,
            "links_to": self.links_to,
            "links_from": self.links_from,
            "content_hash": self.content_hash,
        }


class HierarchicalMemory:
    """
    Sistema de memoria jerárquica de Nova.
    
    Arquitectura de 3 niveles:
      Level 1 (SUMMARY): Índice rápido en memoria. Búsqueda O(log n).
      Level 2 (DETAIL): Almacenamiento estructurado. Acceso O(1) por ID.
      Level 3 (RAW): Datos completos en disco/DB. Acceso bajo demanda.
    
    Pipeline de ingesta:
      Input → [Filtro de novedad] → [Crear MOS] → [Indexar] → [Conectar al grafo]
    """
    
    def __init__(self, max_summary_cache: int = 10000, dedup_threshold: float = 0.85):
        # Level 1: Índice rápido de resúmenes
        self.summary_index: OrderedDict[str, MOS] = OrderedDict()
        
        # Level 2: Almacenamiento completo de MOS
        self.mos_store: Dict[str, MOS] = {}
        
        # Level 3: Referencias a datos raw
        self.raw_registry: Dict[str, str] = {}
        
        # Grafo de conocimiento (MOS → MOS links)
        self.knowledge_graph: Dict[str, List[str]] = {}
        
        # Índices secundarios
        self.tag_index: Dict[str, List[str]] = {}
        self.source_index: Dict[str, List[str]] = {}
        self.timeline: List[str] = []
        
        # Control de capacidad
        self.max_summary_cache = max_summary_cache
        self.dedup_threshold = dedup_threshold
        
        # Estadísticas
        self.stats = {
            "total_ingested": 0,
            "total_deduplicated": 0,
            "total_accessed": 0,
            "by_modality": {},
            "by_level": {1: 0, 2: 0, 3: 0},
        }
    
    # ═══════════════════════════════════════════════
    # INGESTA CON DEDUPLICACIÓN
    # ═══════════════════════════════════════════════
    
    def ingest(self, content: Any, modality: Modality, source: str = "",
               tags: List[str] = None, importance: float = 0.5,
               raw_data: Optional[Any] = None) -> MOS:
        """
        Ingresa nuevo contenido en la memoria.
        
        Pipeline:
          1. Calcular hashes para deduplicación
          2. Verificar si es contenido nuevo (filtro de novedad)
          3. Si es duplicado: actualizar acceso, retornar existente
          4. Si es nuevo: crear MOS, indexar en 3 niveles, conectar al grafo
        """
        # 1. Preparar contenido
        content_str = self._normalize(content)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        jaccard_sig = self._minhash_signature(content_str)
        
        # 2. Verificar duplicados (filtro de novedad)
        existing = self._find_duplicate(content_hash, jaccard_sig, content_str)
        if existing:
            existing.access_count += 1
            existing.last_accessed = time.time()
            self.stats["total_deduplicated"] += 1
            return existing
        
        # 3. Crear MOS
        mos = MOS(
            mos_id=f"mos_{content_hash[:16]}",
            modality=modality,
            summary=self._generate_summary(content_str),
            detail=self._generate_detail(content_str),
            source=source,
            tags=tags or [],
            importance=importance,
            content_hash=content_hash,
            jaccard_signature=jaccard_sig,
            timestamp=time.time(),
        )
        
        # 4. Almacenar raw data (Level 3)
        if raw_data is not None:
            mos.raw_pointer = f"raw://{mos.mos_id}"
            self.raw_registry[mos.raw_pointer] = raw_data
        
        # 5. Indexar en los 3 niveles
        self._index_level1(mos)   # Summary cache
        self._index_level2(mos)   # MOS store
        self._index_level3(mos)   # Raw registry (ya hecho)
        
        # 6. Indexar tags y source
        for tag in (tags or []):
            self.tag_index.setdefault(tag, []).append(mos.mos_id)
        self.source_index.setdefault(source, []).append(mos.mos_id)
        self.timeline.append(mos.mos_id)
        
        # 7. Conectar al grafo
        self._connect_to_graph(mos)
        
        # 8. Stats
        self.stats["total_ingested"] += 1
        self.stats["by_modality"][modality.value] = self.stats["by_modality"].get(modality.value, 0) + 1
        self.stats["by_level"][1] += 1
        self.stats["by_level"][2] += 1
        
        return mos
    
    # ═══════════════════════════════════════════════
    # RECUPERACIÓN MULTI-NIVEL
    # ═══════════════════════════════════════════════
    
    def retrieve(self, mos_id: str, level: MemoryLevel = MemoryLevel.DETAIL) -> Optional[Any]:
        """Recupera una MOS por ID al nivel solicitado."""
        mos = self.mos_store.get(mos_id)
        if not mos:
            return None
        
        mos.access_count += 1
        mos.last_accessed = time.time()
        self.stats["total_accessed"] += 1
        
        if level == MemoryLevel.SUMMARY:
            return mos.summary
        elif level == MemoryLevel.DETAIL:
            return mos.detail
        elif level == MemoryLevel.RAW:
            if mos.raw_pointer:
                return self.raw_registry.get(mos.raw_pointer)
            return mos.detail
    
    def search_by_tags(self, tags: List[str], limit: int = 20) -> List[MOS]:
        """Búsqueda por tags (rápida, O(1))."""
        mos_ids = set()
        for tag in tags:
            mos_ids.update(self.tag_index.get(tag, []))
        
        results = []
        for mid in list(mos_ids)[:limit]:
            mos = self.mos_store.get(mid)
            if mos:
                results.append(mos)
        
        return sorted(results, key=lambda m: (m.importance, m.access_count), reverse=True)
    
    def search_by_source(self, source: str, limit: int = 20) -> List[MOS]:
        """Búsqueda por fuente."""
        ids = self.source_index.get(source, [])[:limit]
        return [self.mos_store[mid] for mid in ids if mid in self.mos_store]
    
    def get_timeline(self, limit: int = 50) -> List[MOS]:
        """Últimas MOS en orden cronológico."""
        ids = self.timeline[-limit:]
        return [self.mos_store[mid] for mid in ids if mid in self.mos_store]
    
    def get_connected(self, mos_id: str, hops: int = 2) -> List[MOS]:
        """Obtiene MOS conectadas en el grafo de conocimiento (N-hops)."""
        visited = {mos_id}
        frontier = [mos_id]
        
        for _ in range(hops):
            next_frontier = []
            for mid in frontier:
                neighbors = self.knowledge_graph.get(mid, [])
                for nid in neighbors:
                    if nid not in visited:
                        visited.add(nid)
                        next_frontier.append(nid)
            frontier = next_frontier
        
        return [self.mos_store[mid] for mid in visited if mid in self.mos_store]
    
    # ═══════════════════════════════════════════════
    # MÉTODOS INTERNOS
    # ═══════════════════════════════════════════════
    
    def _normalize(self, content: Any) -> str:
        """Normaliza cualquier contenido a string para hashing."""
        if isinstance(content, str):
            return content
        elif isinstance(content, (dict, list)):
            return json.dumps(content, sort_keys=True)
        return str(content)
    
    def _minhash_signature(self, text: str, num_hashes: int = 128) -> List[int]:
        """Genera firma MinHash para estimación de similitud Jaccard."""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return [0] * num_hashes
        
        signatures = []
        for i in range(num_hashes):
            min_hash = float('inf')
            for word in words:
                h = hash(f"{i}:{word}") & 0x7FFFFFFF
                min_hash = min(min_hash, h)
            signatures.append(min_hash)
        
        return signatures
    
    def _jaccard_similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """Estima similitud Jaccard entre dos firmas MinHash."""
        if not sig1 or not sig2:
            return 0.0
        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)
    
    def _find_duplicate(self, content_hash: str, jaccard_sig: List[int], content: str) -> Optional[MOS]:
        """Busca si el contenido ya existe (hash exacto o alta similitud Jaccard)."""
        # Hash exacto
        for mos in self.mos_store.values():
            if mos.content_hash == content_hash:
                return mos
        
        # Similitud Jaccard
        for mos in self.mos_store.values():
            if mos.jaccard_signature:
                sim = self._jaccard_similarity(jaccard_sig, mos.jaccard_signature)
                if sim >= self.dedup_threshold:
                    return mos
        
        return None
    
    def _generate_summary(self, content: str, max_chars: int = 500) -> str:
        """Genera un resumen ligero (Level 1)."""
        # Por ahora: primeras frases. Idealmente usaría un LLM pequeño.
        sentences = re.split(r'[.!?]+', content)
        summary = ""
        for s in sentences:
            if len(summary) + len(s) > max_chars:
                break
            summary += s.strip() + ". "
        return summary.strip()
    
    def _generate_detail(self, content: str) -> str:
        """Genera detalle estructurado (Level 2)."""
        # Por ahora: primeras 2000 chars. Idealmente sería más estructurado.
        return content[:2000]
    
    def _index_level1(self, mos: MOS):
        """Indexa en el cache de resúmenes (Level 1)."""
        self.summary_index[mos.mos_id] = mos
        # LRU eviction
        while len(self.summary_index) > self.max_summary_cache:
            self.summary_index.popitem(last=False)
    
    def _index_level2(self, mos: MOS):
        """Indexa en el almacenamiento principal (Level 2)."""
        self.mos_store[mos.mos_id] = mos
    
    def _index_level3(self, mos: MOS):
        """Registra datos raw (Level 3)."""
        if mos.raw_pointer:
            self.stats["by_level"][3] += 1
    
    def _connect_to_graph(self, mos: MOS):
        """Conecta la MOS al grafo de conocimiento basado en tags compartidos."""
        self.knowledge_graph.setdefault(mos.mos_id, [])
        
        for tag in mos.tags:
            related = self.tag_index.get(tag, [])
            for related_id in related:
                if related_id != mos.mos_id:
                    if related_id not in self.knowledge_graph[mos.mos_id]:
                        self.knowledge_graph[mos.mos_id].append(related_id)
                    self.knowledge_graph.setdefault(related_id, []).append(mos.mos_id)
    
    def get_stats(self) -> Dict:
        """Estadísticas detalladas de la memoria."""
        return {
            **self.stats,
            "summary_cache_size": len(self.summary_index),
            "mos_store_size": len(self.mos_store),
            "graph_nodes": len(self.knowledge_graph),
            "graph_edges": sum(len(v) for v in self.knowledge_graph.values()),
            "unique_tags": len(self.tag_index),
            "dedup_ratio": self.stats["total_deduplicated"] / max(1, self.stats["total_ingested"]),
        }


# ─── Memoria Global de la Colonia ───

# Instancia única de la memoria jerárquica de Nova
colony_memory = HierarchicalMemory(max_summary_cache=10000)


def remember(content: Any, modality: str = "text", source: str = "nova",
             tags: List[str] = None, importance: float = 0.5) -> MOS:
    """Función rápida para almacenar en la memoria de la colonia."""
    try:
        mod = Modality(modality)
    except ValueError:
        mod = Modality.TEXT
    
    return colony_memory.ingest(
        content=content,
        modality=mod,
        source=source,
        tags=tags,
        importance=importance,
    )


def recall(mos_id: str = None, tags: List[str] = None, source: str = None, limit: int = 20) -> List[Dict]:
    """Función rápida para recuperar de la memoria de la colonia."""
    if mos_id:
        mos = colony_memory.retrieve(mos_id)
        return [mos.to_dict()] if mos else []
    elif tags:
        results = colony_memory.search_by_tags(tags, limit=limit)
        return [m.to_dict() for m in results]
    elif source:
        results = colony_memory.search_by_source(source, limit=limit)
        return [m.to_dict() for m in results]
    return [m.to_dict() for m in colony_memory.get_timeline(limit=limit)]
