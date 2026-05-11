"""
knowledge_graph_builder.py — Constructor de Grafos de Conocimiento desde Transcripciones

INSPIRACIÓN:
  - @code4AI "Quantum Knowledge Graphs in AI"
  - @code4AI "S-Path-RAG: RAG Without Text"  
  - @code4AI "GraphRAG Now Redundant? Implicit Reasoning Graphs"
  - @code4AI "Text vs K-Graphs: Why Your Multi-RAG System is Failing"

CONCEPTO: Extraer entidades y relaciones de cualquier texto (transcripciones, 
documentos) y construir un grafo de conocimiento que capture la estructura 
semántica. El grafo permite navegación N-hops y descubrimiento de conexiones 
implícitas (inferencia).

ARQUITECTURA:
  Texto → [Entity Extractor] → [Relation Builder] → [Graph DB] → [Query Engine]
"""

import re
import json
import hashlib
import time
from typing import Any, Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Entity:
    """Una entidad en el grafo de conocimiento."""
    id: str
    name: str
    type: str  # concept, person, technology, paper, method, framework, etc.
    mentions: int = 0
    sources: List[str] = field(default_factory=list)  # video_ids
    description: str = ""
    confidence: float = 0.5


@dataclass 
class Relation:
    """Una relación dirigida entre dos entidades."""
    source_id: str
    target_id: str
    type: str  # uses, extends, refutes, builds_on, part_of, similar_to
    weight: float = 1.0
    evidence: str = ""  # texto que evidencia la relación


class KnowledgeGraphBuilder:
    """
    Construye un grafo de conocimiento a partir de texto.
    
    Inspirado en S-Path-RAG: las entidades son nodos, las relaciones son aristas,
    y la recuperación navega el grafo por caminos estructurales (N-hops).
    """
    
    # Patrones de extracción de entidades
    ENTITY_PATTERNS = {
        "framework": [
            r'\b(?:framework|architecture|system)\s+(?:called|named|:)?\s+["\']?([A-Z][A-Za-z0-9_\-]+)["\']?',
            r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b',  # CamelCase = probable framework
        ],
        "technology": [
            r'\b(GPT-?\d[.\d]*|Claude|Gemini|DeepSeek|Qwen|Llama|BERT|Transformer)\b',
            r'\b(?:tool|library|package)\s+(?:called|named)?\s+["\']?(\w+)["\']?',
        ],
        "method": [
            r'\b(?:method|technique|approach|algorithm)\s+(?:called|named)?\s+["\']?([A-Z][A-Za-z0-9_\-]+)["\']?',
            r'\b((?:[A-Z][a-z]+-)*[A-Z][a-z]+(?:RAG|LM|AI|ML|RL|KG))\b',  # Acrónimos técnicos
        ],
        "concept": [
            r'\b(?:concept|idea|notion)\s+of\s+["\']?([a-zA-Z\s]{3,40}?)["\']?(?:\s*,|\s*\.|\s*\))',
            r'\b(knowledge\s+graph|vector\s+embedding|semantic\s+search|multi-agent\s+system|error\s+correction)\b',
        ],
        "paper": [
            r'\b(?:paper|study|research)\s+(?:by|from|titled)\s+["\']?([^"\',.;]{10,100}?)["\']?(?:\s*,|\s*\.|\s*\()',
        ],
    }
    
    # Patrones de relaciones
    RELATION_PATTERNS = {
        "uses": [r'(\w+)\s+(?:uses|utilizes|leverages|employs)\s+(\w+)'],
        "extends": [r'(\w+)\s+(?:extends|builds on|improves upon)\s+(\w+)'],
        "refutes": [r'(\w+)\s+(?:refutes|contradicts|challenges)\s+(\w+)'],
        "part_of": [r'(\w+)\s+is\s+(?:part of|a component of|a subset of)\s+(\w+)'],
        "similar_to": [r'(\w+)\s+is\s+(?:similar to|like|analogous to)\s+(\w+)'],
    }
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # node -> [(neighbor, relation_type)]
        
    def ingest_document(self, text: str, source_id: str = "") -> Dict:
        """
        Ingests un documento, extrae entidades y relaciones, y las añade al grafo.
        
        Returns:
            dict con 'entities_found', 'relations_found'
        """
        # Extraer entidades
        found_entities = self._extract_entities(text, source_id)
        
        # Extraer relaciones
        found_relations = self._extract_relations(text, found_entities)
        
        return {
            "entities_found": len(found_entities),
            "relations_found": found_relations if isinstance(found_relations, int) else len(found_relations),
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "source": source_id,
        }
    
    def _extract_entities(self, text: str, source_id: str) -> List[str]:
        """Extrae entidades del texto usando patrones regex."""
        found_ids = []
        
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    name = match.strip()
                    if len(name) < 3 or len(name) > 60:
                        continue
                    
                    entity_id = hashlib.md5(f"{entity_type}:{name.lower()}".encode()).hexdigest()[:12]
                    
                    if entity_id in self.entities:
                        self.entities[entity_id].mentions += 1
                        if source_id and source_id not in self.entities[entity_id].sources:
                            self.entities[entity_id].sources.append(source_id)
                    else:
                        self.entities[entity_id] = Entity(
                            id=entity_id,
                            name=name,
                            type=entity_type,
                            mentions=1,
                            sources=[source_id] if source_id else [],
                            confidence=0.6,
                        )
                    
                    found_ids.append(entity_id)
        
        return list(set(found_ids))
    
    def _extract_relations(self, text: str, entity_ids: List[str]) -> int:
        """Extrae relaciones entre entidades."""
        count = 0
        entity_names = {self.entities[eid].name.lower(): eid for eid in entity_ids if eid in self.entities}
        
        for rel_type, patterns in self.RELATION_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 2:
                        src_name = match[0].strip().lower()
                        tgt_name = match[1].strip().lower()
                        
                        if src_name in entity_names and tgt_name in entity_names:
                            rel = Relation(
                                source_id=entity_names[src_name],
                                target_id=entity_names[tgt_name],
                                type=rel_type,
                                weight=1.0,
                            )
                            self.relations.append(rel)
                            self.adjacency[rel.source_id].append((rel.target_id, rel.type))
                            count += 1
        
        return count
    
    def build_from_transcripts(self, transcript_dir: str, index_file: str = None) -> Dict:
        """
        Construye el grafo desde un directorio de transcripciones.
        
        Args:
            transcript_dir: Directorio con archivos .txt
            index_file: JSON opcional con títulos de videos
        
        Returns:
            Estadísticas de la construcción
        """
        import os
        
        total_entities = 0
        total_relations = 0
        docs_processed = 0
        
        for filename in sorted(os.listdir(transcript_dir)):
            if not filename.endswith('.txt') or filename.startswith('_'):
                continue
            
            filepath = os.path.join(transcript_dir, filename)
            text = open(filepath).read()
            # Limpiar metadatos
            lines = [l for l in text.split('\n') if not l.startswith('#')]
            text = '\n'.join(lines).strip()
            
            if len(text) < 500:
                continue
            
            video_id = filename.replace('.txt', '')
            result = self.ingest_document(text, source_id=video_id)
            total_entities += result['entities_found']
            total_relations += result['relations_found']
            docs_processed += 1
        
        return {
            "docs_processed": docs_processed,
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "total_edges": sum(len(v) for v in self.adjacency.values()),
            "entities_by_type": self._count_by_type(),
        }
    
    def query(self, entity_name: str, hops: int = 2) -> Dict:
        """
        Navega el grafo N-hops desde una entidad.
        
        Inspirado en S-Path-RAG: recuperación por caminos estructurales.
        """
        # Encontrar la entidad
        start_id = None
        for eid, entity in self.entities.items():
            if entity_name.lower() in entity.name.lower():
                start_id = eid
                break
        
        if not start_id:
            return {"error": f"Entidad '{entity_name}' no encontrada", "results": []}
        
        # BFS N-hops
        visited = {start_id: 0}
        queue = [(start_id, 0)]
        paths = []
        
        while queue:
            node_id, depth = queue.pop(0)
            if depth >= hops:
                continue
            
            for neighbor_id, rel_type in self.adjacency.get(node_id, []):
                if neighbor_id not in visited:
                    visited[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))
                    
                    paths.append({
                        "from": self.entities[node_id].name,
                        "to": self.entities[neighbor_id].name,
                        "relation": rel_type,
                        "depth": depth + 1,
                    })
        
        return {
            "start_entity": self.entities[start_id].name,
            "hops": hops,
            "nodes_visited": len(visited),
            "paths": paths,
        }
    
    def get_central_entities(self, top_n: int = 20) -> List[Dict]:
        """Entidades más centrales (por número de conexiones)."""
        centrality = [(eid, len(self.adjacency.get(eid, []))) for eid in self.entities]
        centrality.sort(key=lambda x: -x[1])
        
        return [
            {
                "name": self.entities[eid].name,
                "type": self.entities[eid].type,
                "connections": conn,
                "mentions": self.entities[eid].mentions,
            }
            for eid, conn in centrality[:top_n] if conn > 0
        ]
    
    def find_path(self, entity_a: str, entity_b: str, max_hops: int = 4) -> Optional[List[Dict]]:
        """Encuentra el camino más corto entre dos entidades (inferencia de conexiones implícitas)."""
        # Encontrar IDs
        id_a = None
        id_b = None
        for eid, entity in self.entities.items():
            if entity_a.lower() in entity.name.lower():
                id_a = eid
            if entity_b.lower() in entity.name.lower():
                id_b = eid
        
        if not id_a or not id_b:
            return None
        
        # BFS bidireccional simple
        visited = {id_a: (None, "")}
        queue = [id_a]
        
        while queue and len(visited) < max_hops * 10:
            node = queue.pop(0)
            depth = 0
            # Calcular depth desde la raíz
            path_node = node
            while path_node and visited.get(path_node):
                path_node = visited[path_node][0]
                if path_node:
                    depth += 1
            
            if depth >= max_hops:
                continue
            
            for neighbor, rel_type in self.adjacency.get(node, []):
                if neighbor not in visited:
                    visited[neighbor] = (node, rel_type)
                    queue.append(neighbor)
                    
                    if neighbor == id_b:
                        # Reconstruir camino
                        path = []
                        cur = id_b
                        while cur and cur in visited:
                            prev, rel = visited[cur]
                            if prev:
                                path.append({
                                    "from": self.entities[prev].name if prev in self.entities else prev,
                                    "to": self.entities[cur].name if cur in self.entities else cur,
                                    "relation": rel,
                                })
                            cur = prev
                        return list(reversed(path))
        
        return None  # No se encontró camino
    
    def _count_by_type(self) -> Dict[str, int]:
        """Cuenta entidades por tipo."""
        counts = defaultdict(int)
        for entity in self.entities.values():
            counts[entity.type] += 1
        return dict(counts)
    
    def get_stats(self) -> Dict:
        return {
            "entities": len(self.entities),
            "relations": len(self.relations),
            "edges": sum(len(v) for v in self.adjacency.values()),
            "by_type": self._count_by_type(),
            "density": len(self.relations) / max(1, len(self.entities) * (len(self.entities) - 1)),
        }


# ─── Instancia Global ───

colony_kg = KnowledgeGraphBuilder()


def build_kg_from_transcripts(transcript_dir: str) -> Dict:
    """Construye el grafo de conocimiento desde transcripciones."""
    return colony_kg.build_from_transcripts(transcript_dir)


def query_kg(entity: str, hops: int = 2) -> Dict:
    """Consulta el grafo de conocimiento."""
    return colony_kg.query(entity, hops=hops)


def find_connection(a: str, b: str) -> Optional[List[Dict]]:
    """Encuentra conexiones implícitas entre dos conceptos."""
    return colony_kg.find_path(a, b)
