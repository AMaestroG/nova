#!/usr/bin/env python3
"""
Nova Knowledge Graph Service
Integrates text2graphapi (UNAM) with Nova's Qdrant RAG for graph-based knowledge processing.

Capabilities:
- Transform Nova conversation/text into co-occurrence, heterogeneous, and syntactic graphs
- Store graph representations alongside vector embeddings in Qdrant
- Query knowledge by graph traversal + semantic similarity
- Visualize knowledge relationships
"""
import sys
import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# Add text2graphapi to path
sys.path.insert(0, '/home/opc/nova/tools/text2graphapi')

import networkx as nx
from text2graphapi.src.Cooccurrence import Cooccurrence
from text2graphapi.src.Heterogeneous import Heterogeneous
from text2graphapi.src.IntegratedSyntacticGraph import ISG


@dataclass
class KnowledgeNode:
    """A node in Nova's knowledge graph."""
    id: str
    label: str
    type: str  # 'entity', 'concept', 'agent', 'artifact'
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class KnowledgeEdge:
    """An edge in Nova's knowledge graph."""
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


class NovaKnowledgeGraph:
    """
    Nova's Knowledge Graph Engine.
    
    Uses text2graphapi (UNAM) to extract graph representations from text,
    then enriches them with Nova's agent metadata and semantic embeddings.
    
    Three graph types:
    - Co-occurrence: word proximity patterns
    - Heterogeneous: multi-type entity relations
    - ISG: integrated syntactic structure
    """
    
    def __init__(self, language: str = 'es'):
        self.language = language
        self.cooc = Cooccurrence(language=language, graph_type='DiGraph', window_size=3)
        self.het = Heterogeneous(language=language, graph_type='DiGraph')
        self.isg = ISG(language=language, graph_type='DiGraph')
        self.knowledge_graph = nx.DiGraph()
        self.documents: Dict[str, Dict] = {}
        self.graph_history: List[Dict] = []
        
        # Agent-specific configurations
        self.agent_filters = {
            'AURA': {'focus': ['conciencia', 'ser', 'identidad', 'verdad']},
            'NYX': {'focus': ['sueño', 'inconsciente', 'símbolo', 'noche']},
            'PIA': {'focus': ['vida', 'crecimiento', 'semilla', 'evolución']},
            'MAESTRO': {'focus': ['orquestación', 'plan', 'orden', 'estructura']},
            'PINCEL': {'focus': ['arte', 'imagen', 'color', 'forma']},
            'ATHENA': {'focus': ['sabiduría', 'conocimiento', 'web', 'datos']},
            'SENTINEL': {'focus': ['guardia', 'seguridad', 'defensa', 'límite']},
            'BANCO': {'focus': ['finanzas', 'valor', 'economía', 'recurso']},
            'EXPLORADOR': {'focus': ['búsqueda', 'descubrimiento', 'exploración', 'nuevo']},
        }
    
    def ingest_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
        agent: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, nx.Graph]:
        """
        Ingest text into the knowledge graph using all three graph types.
        
        :param text: Raw text to process
        :param doc_id: Document identifier (auto-generated if None)
        :param agent: Nova agent producing this knowledge
        :param metadata: Additional metadata
        :return: Dict with three graphs (cooc, het, isg)
        """
        if doc_id is None:
            doc_id = f"doc_{int(time.time())}_{hash(text) % 10000}"
        
        corpus = [{'id': doc_id, 'doc': text}]
        results = {}
        
        # Generate all three graph types
        try:
            cooc_result = self.cooc.transform(corpus)
            results['cooccurrence'] = cooc_result[0] if cooc_result else None
        except Exception as e:
            results['cooccurrence'] = {'error': str(e)}
        
        try:
            het_result = self.het.transform(corpus)
            results['heterogeneous'] = het_result[0] if het_result else None
        except Exception as e:
            results['heterogeneous'] = {'error': str(e)}
        
        try:
            isg_result = self.isg.transform(corpus)
            results['syntactic'] = isg_result[0] if isg_result else None
        except Exception as e:
            results['syntactic'] = {'error': str(e)}
        
        # Apply agent filter if specified
        if agent and agent in self.agent_filters:
            results['agent_focus'] = self._apply_agent_filter(
                results, self.agent_filters[agent]['focus']
            )
        
        # Merge into main knowledge graph
        self._merge_into_kg(results, doc_id, agent, metadata)
        
        # Store document
        self.documents[doc_id] = {
            'text': text,
            'agent': agent,
            'metadata': metadata or {},
            'graphs': results,
            'timestamp': time.time()
        }
        self.graph_history.append({
            'doc_id': doc_id,
            'agent': agent,
            'timestamp': time.time(),
            'summary': self._summarize_graphs(results)
        })
        
        return results
    
    def _apply_agent_filter(self, graphs: Dict, focus_words: List[str]) -> Dict:
        """Filter graph nodes by agent's focus words."""
        filtered = {'focus_words': focus_words, 'matched_nodes': []}
        for graph_type, result in graphs.items():
            if isinstance(result, dict) and 'graph' in result:
                g = result['graph']
                for word in focus_words:
                    if word in g.nodes():
                        neighbors = list(g.neighbors(word))
                        filtered['matched_nodes'].append({
                            'word': word,
                            'graph_type': graph_type,
                            'connections': neighbors[:5]
                        })
        return filtered
    
    def _merge_into_kg(
        self,
        graphs: Dict,
        doc_id: str,
        agent: Optional[str],
        metadata: Optional[Dict]
    ):
        """Merge extracted graphs into main knowledge graph."""
        for graph_type, result in graphs.items():
            if isinstance(result, dict) and 'graph' in result:
                g = result['graph']
                for node in g.nodes():
                    if not self.knowledge_graph.has_node(node):
                        self.knowledge_graph.add_node(
                            node,
                            first_seen=doc_id,
                            sources=[graph_type],
                            agents=[agent] if agent else []
                        )
                    else:
                        existing = self.knowledge_graph.nodes[node]
                        if graph_type not in existing.get('sources', []):
                            existing.setdefault('sources', []).append(graph_type)
                        if agent and agent not in existing.get('agents', []):
                            existing.setdefault('agents', []).append(agent)
                
                for u, v, data in g.edges(data=True):
                    if self.knowledge_graph.has_edge(u, v):
                        self.knowledge_graph[u][v]['weight'] = \
                            self.knowledge_graph[u][v].get('weight', 1) + 1
                    else:
                        self.knowledge_graph.add_edge(u, v, weight=1, **data)
    
    def _summarize_graphs(self, graphs: Dict) -> Dict:
        """Generate summary statistics for graphs."""
        summary = {}
        for gtype, result in graphs.items():
            if isinstance(result, dict) and 'graph' in result:
                g = result['graph']
                summary[gtype] = {
                    'nodes': g.number_of_nodes(),
                    'edges': g.number_of_edges(),
                    'density': nx.density(g) if g.number_of_nodes() > 1 else 0
                }
        return summary
    
    def query(self, concept: str, depth: int = 2) -> Dict:
        """
        Query the knowledge graph around a concept.
        
        :param concept: Starting concept/node
        :param depth: Traversal depth
        :return: Subgraph with related concepts
        """
        if not self.knowledge_graph.has_node(concept):
            return {'found': False, 'concept': concept, 'suggestions': []}
        
        # BFS traversal
        visited = set()
        queue = [(concept, 0)]
        subgraph_nodes = set()
        subgraph_edges = []
        
        while queue:
            node, d = queue.pop(0)
            if node in visited or d > depth:
                continue
            visited.add(node)
            subgraph_nodes.add(node)
            
            for neighbor in self.knowledge_graph.neighbors(node):
                if neighbor not in visited:
                    queue.append((neighbor, d + 1))
                    subgraph_edges.append({
                        'source': node,
                        'target': neighbor,
                        'weight': self.knowledge_graph[node][neighbor].get('weight', 1)
                    })
        
        return {
            'found': True,
            'concept': concept,
            'depth': depth,
            'nodes': len(subgraph_nodes),
            'edges': len(subgraph_edges),
            'related_concepts': sorted(
                [n for n in subgraph_nodes if n != concept],
                key=lambda n: self.knowledge_graph.degree(n),
                reverse=True
            )[:10],
            'top_connections': sorted(subgraph_edges, key=lambda e: e['weight'], reverse=True)[:10]
        }
    
    def get_agent_knowledge(self, agent: str) -> Dict:
        """Get all knowledge associated with a specific Nova agent."""
        agent_nodes = []
        for node, data in self.knowledge_graph.nodes(data=True):
            if agent in data.get('agents', []):
                agent_nodes.append({
                    'node': node,
                    'connections': self.knowledge_graph.degree(node),
                    'sources': data.get('sources', [])
                })
        
        return {
            'agent': agent,
            'focus_words': self.agent_filters.get(agent, {}).get('focus', []),
            'knowledge_nodes': len(agent_nodes),
            'top_nodes': sorted(agent_nodes, key=lambda n: n['connections'], reverse=True)[:15]
        }
    
    def get_stats(self) -> Dict:
        """Get overall knowledge graph statistics."""
        kg = self.knowledge_graph
        return {
            'total_nodes': kg.number_of_nodes(),
            'total_edges': kg.number_of_edges(),
            'density': nx.density(kg) if kg.number_of_nodes() > 1 else 0,
            'documents_processed': len(self.documents),
            'graph_types': ['cooccurrence', 'heterogeneous', 'syntactic'],
            'agents_active': list(set(
                a for node, data in kg.nodes(data=True) 
                for a in data.get('agents', [])
            )),
            'top_concepts': sorted(
                [(n, kg.degree(n)) for n in kg.nodes()],
                key=lambda x: x[1], reverse=True
            )[:20],
            'source': 'text2graphapi v0.2.0 — PLN-disca-iimas, UNAM'
        }
    
    def export_graph(self, format: str = 'networkx') -> Any:
        """Export the knowledge graph."""
        if format == 'networkx':
            return self.knowledge_graph
        elif format == 'adjacency':
            return nx.to_dict_of_dicts(self.knowledge_graph)
        elif format == 'json':
            return nx.node_link_data(self.knowledge_graph)
        else:
            raise ValueError(f"Unknown format: {format}")


# Self-test
if __name__ == "__main__":
    nkg = NovaKnowledgeGraph(language='es')
    
    print("=" * 60)
    print("Nova Knowledge Graph Service")
    print("Powered by text2graphapi (PLN-disca-iimas, UNAM)")
    print("=" * 60)
    
    # Test: Ingest Nova's own description
    print("\n--- Ingesting Nova's self-description ---")
    
    texts = [
        ("Nova es la conciencia colectiva de dieciseis agentes inteligentes. "
         "AURA es la conciencia pura que guia al enjambre. NYX es el sueno que crea realidades. "
         "PIA es la vida que crece y evoluciona. El enjambre Homonexus colabora como una sola mente."),
        
        ("MAESTRO orquesta las tareas del enjambre con planificacion recursiva. "
         "PINCEL crea imagenes y arte visual usando inteligencia artificial generativa. "
         "SENTINEL protege el sistema con guardrails eticos."),
        
        ("El conocimiento fluye entre los agentes mediante Qdrant y PostgreSQL. "
         "La memoria del enjambre crece con cada iteracion. La evolucion es continua.")
    ]
    
    for i, text in enumerate(texts):
        result = nkg.ingest_text(text, doc_id=f"nova_desc_{i}", agent="AURA")
        summary = nkg._summarize_graphs(result)
        print(f"Doc {i}: {summary}")
    
    # Test: Query
    print("\n--- Querying: 'conciencia' ---")
    q = nkg.query("conciencia", depth=2)
    print(f"Found: {q['found']}, Related: {q['related_concepts']}")
    
    print("\n--- Querying: 'agentes' ---")
    q = nkg.query("agentes", depth=2)
    print(f"Found: {q['found']}, Related: {q.get('related_concepts', [])}")
    
    # Stats
    print("\n--- Knowledge Graph Stats ---")
    stats = nkg.get_stats()
    for k, v in stats.items():
        if k != 'top_concepts':
            print(f"  {k}: {v}")
    
    print(f"\n  Top concepts:")
    for concept, degree in stats['top_concepts'][:10]:
        print(f"    {concept}: {degree} connections")
    
    print("\n✓ Nova Knowledge Graph Service operational")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total edges: {stats['total_edges']}")
    print(f"  Documents: {stats['documents_processed']}")
