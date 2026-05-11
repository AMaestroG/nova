"""
recursive_delegation.py — Delegación Recursiva en la Colmena

CONCEPTO: Cada agente puede dividir su tarea en subtareas y delegarlas
a otros agentes, que a su vez pueden sub-delegar RECURSIVAMENTE.
Como una red neuronal profunda: cada capa procesa y propaga.

ARQUITECTURA DEL ÁRBOL DE DELEGACIÓN:

                    MAESTRO (origen)
                   /      |      \
              PIA       MEMORIA   SENTINEL
             /    \        |         |
        WORKER1 WORKER2  SUB1    SUB2
           |               |
        SUB-SUB1        SUB-SUB1

CADA NODO:
  - Recibe una tarea
  - Decide si puede resolverla directamente
  - Si no: la divide en subtareas y las delega recursivamente
  - Espera resultados de las subtareas
  - Fusiona resultados y los devuelve al padre

PROFUNDIDAD MÁXIMA: 4 niveles (configurable)
TIMEOUT POR NIVEL: 30s
"""

import sys, os, time, random, json, hashlib, threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))


class DelegationStatus(Enum):
    PENDING = "pending"
    DELEGATED = "delegated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    MERGED = "merged"


@dataclass
class DelegationNode:
    """Un nodo en el árbol de delegación recursiva."""
    node_id: str
    task: str
    agent: str
    parent_id: Optional[str] = None
    depth: int = 0
    status: DelegationStatus = DelegationStatus.PENDING
    
    # Subtareas delegadas
    children: List[str] = field(default_factory=list)
    
    # Resultados
    result: Any = None
    sub_results: Dict[str, Any] = field(default_factory=dict)
    
    # Métricas
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    delegation_chain: List[str] = field(default_factory=list)


class RecursiveDelegationEngine:
    """
    Motor de Delegación Recursiva.
    
    Implementa un árbol de delegación donde cada agente puede
    subdividir su tarea y delegar recursivamente.
    """
    
    def __init__(self, max_depth: int = 4, timeout_per_level: float = 30.0):
        self.max_depth = max_depth
        self.timeout_per_level = timeout_per_level
        
        # Árbol de delegación
        self.nodes: Dict[str, DelegationNode] = {}
        self.root_nodes: List[str] = []
        
        # Registro de capacidades de agentes
        self.agent_capabilities: Dict[str, List[str]] = defaultdict(list)
        self._register_default_capabilities()
        
        # Estadísticas
        self.total_delegations = 0
        self.max_depth_reached = 0
        self.delegation_chains: List[List[str]] = []
    
    def _register_default_capabilities(self):
        """Registra capacidades por defecto de cada agente."""
        self.agent_capabilities = {
            "MAESTRO": ["orchestrate", "plan", "delegate", "coordinate"],
            "PIA": ["evolve", "optimize", "learn", "improve", "mutate"],
            "MEMORIA": ["remember", "retrieve", "index", "store", "search"],
            "SENTINEL": ["verify", "validate", "audit", "secure", "monitor"],
            "ORÁCULO": ["predict", "forecast", "analyze", "project"],
            "AUTOPILOT": ["automate", "cycle", "monitor", "repeat"],
            "EXPLORADOR": ["explore", "discover", "search", "investigate"],
            "YOUTUBE": ["extract", "transcribe", "index_video"],
        }
    
    # ═══════════════════════════════════════════
    # API DE DELEGACIÓN RECURSIVA
    # ═══════════════════════════════════════════
    
    def delegate(self, task: str, agent: str = "MAESTRO", 
                 parent_id: str = None, depth: int = 0) -> DelegationNode:
        """
        Delega una tarea a un agente, que puede sub-delegar recursivamente.
        
        Args:
            task: Descripción de la tarea
            agent: Agente asignado
            parent_id: Nodo padre (si es sub-delegación)
            depth: Profundidad actual en el árbol
        
        Returns:
            Nodo de delegación creado
        """
        if depth >= self.max_depth:
            return self._create_leaf_node(task, agent, parent_id, depth)
        
        node_id = f"del_{len(self.nodes)}_{hashlib.md5(task.encode()).hexdigest()[:8]}"
        
        node = DelegationNode(
            node_id=node_id,
            task=task,
            agent=agent,
            parent_id=parent_id,
            depth=depth,
        )
        
        # Registrar cadena de delegación
        if parent_id and parent_id in self.nodes:
            parent = self.nodes[parent_id]
            node.delegation_chain = parent.delegation_chain + [agent]
            parent.children.append(node_id)
        else:
            node.delegation_chain = [agent]
            self.root_nodes.append(node_id)
        
        self.nodes[node_id] = node
        self.total_delegations += 1
        self.max_depth_reached = max(self.max_depth_reached, depth)
        
        # El agente decide cómo proceder
        node = self._agent_decides(node)
        
        return node
    
    def _agent_decides(self, node: DelegationNode) -> DelegationNode:
        """
        El agente decide si ejecutar directamente o sub-delegar.
        
        Lógica de decisión:
        - Si la tarea es simple → ejecutar directamente
        - Si la tarea es compleja → dividir en subtareas y delegar
        - Si profundidad >= max_depth → ejecutar directamente (hoja)
        """
        task_lower = node.task.lower()
        capabilities = self.agent_capabilities.get(node.agent, ["process"])
        
        # Determinar complejidad
        complexity = self._assess_complexity(node.task)
        
        if complexity == "simple" or node.depth >= self.max_depth:
            # Ejecutar directamente
            node.status = DelegationStatus.PROCESSING
            node.result = self._execute_directly(node)
            node.status = DelegationStatus.COMPLETED
            node.completed_at = time.time()
            node.duration_ms = (node.completed_at - node.created_at) * 1000
        
        elif complexity in ("medium", "complex"):
            # Sub-dividir y delegar
            node.status = DelegationStatus.DELEGATED
            subtasks = self._decompose_task(node.task, node.agent)
            
            for sub_agent, sub_task in subtasks:
                if node.depth + 1 < self.max_depth:
                    child = self.delegate(
                        task=sub_task,
                        agent=sub_agent,
                        parent_id=node.node_id,
                        depth=node.depth + 1,
                    )
                    node.sub_results[child.node_id] = child.result
            
            # Fusionar resultados de subtareas
            if node.sub_results:
                node.result = self._merge_results(node)
                node.status = DelegationStatus.MERGED
            else:
                node.result = self._execute_directly(node)
                node.status = DelegationStatus.COMPLETED
            
            node.completed_at = time.time()
            node.duration_ms = (node.completed_at - node.created_at) * 1000
        
        return node
    
    def _assess_complexity(self, task: str) -> str:
        """Evalúa la complejidad de una tarea."""
        task_lower = task.lower()
        
        # Señales de alta complejidad
        complex_signals = [
            "analizar", "optimizar", "reestructurar", "migrar",
            "refactorizar", "rediseñar", "arquitectura", "sistema completo",
            "analyze", "optimize", "restructure", "migrate", "architecture"
        ]
        
        # Señales de complejidad media
        medium_signals = [
            "procesar", "indexar", "extraer", "consolidar", "evaluar",
            "process", "index", "extract", "consolidate", "evaluate"
        ]
        
        complex_count = sum(1 for s in complex_signals if s in task_lower)
        medium_count = sum(1 for s in medium_signals if s in task_lower)
        
        if complex_count >= 2:
            return "complex"
        elif complex_count >= 1 or medium_count >= 2:
            return "medium"
        else:
            return "simple"
    
    def _decompose_task(self, task: str, agent: str) -> List[Tuple[str, str]]:
        """
        Descompone una tarea en subtareas y asigna agentes.
        
        Returns:
            Lista de (agente, subtarea)
        """
        task_lower = task.lower()
        subtasks = []
        
        # Patrones de descomposición por tipo de tarea
        if any(w in task_lower for w in ["analizar", "optimizar", "analyze", "optimize"]):
            subtasks = [
                ("MEMORIA", f"Recuperar datos históricos sobre: {task[:60]}"),
                ("PIA", f"Identificar patrones de mejora en: {task[:60]}"),
                ("ORÁCULO", f"Predecir impacto de cambios en: {task[:60]}"),
            ]
        elif any(w in task_lower for w in ["extraer", "transcribir", "extract"]):
            subtasks = [
                ("EXPLORADOR", f"Buscar fuentes para: {task[:60]}"),
                ("YOUTUBE", f"Extraer contenido de: {task[:60]}"),
                ("MEMORIA", f"Indexar resultado de: {task[:60]}"),
            ]
        elif any(w in task_lower for w in ["verificar", "validar", "verify", "audit"]):
            subtasks = [
                ("SENTINEL", f"Auditar seguridad de: {task[:60]}"),
                ("MEMORIA", f"Comparar con patrones históricos: {task[:60]}"),
            ]
        elif any(w in task_lower for w in ["plan", "coordinar", "orquestar"]):
            subtasks = [
                ("PIA", f"Ejecutar optimización para: {task[:60]}"),
                ("SENTINEL", f"Validar resultado de: {task[:60]}"),
                ("AUTOPILOT", f"Automatizar ciclo de: {task[:60]}"),
            ]
        else:
            # Descomposición genérica
            subtasks = [
                ("MEMORIA", f"Procesar y almacenar: {task[:50]}"),
                ("PIA", f"Buscar mejoras en: {task[:50]}"),
            ]
        
        return subtasks
    
    def _execute_directly(self, node: DelegationNode) -> str:
        """Ejecuta una tarea directamente (sin sub-delegar)."""
        return (f"[{node.agent}·N{node.depth}] "
                f"Tarea completada directamente: {node.task[:80]}... "
                f"({len(node.delegation_chain)} niveles de delegación)")
    
    def _merge_results(self, node: DelegationNode) -> str:
        """Fusiona resultados de subtareas delegadas."""
        if not node.sub_results:
            return self._execute_directly(node)
        
        parts = []
        for child_id, result in node.sub_results.items():
            child = self.nodes.get(child_id)
            if child:
                parts.append(f"{child.agent}: {str(result)[:60]}")
        
        merged = (f"[{node.agent}·FUSIÓN·N{node.depth}] "
                  f"{len(parts)} subtareas fusionadas:\n  " + "\n  ".join(parts))
        return merged
    
    def _create_leaf_node(self, task: str, agent: str, parent_id: str, depth: int) -> DelegationNode:
        """Crea un nodo hoja (profundidad máxima alcanzada)."""
        node_id = f"leaf_{len(self.nodes)}_{hashlib.md5(task.encode()).hexdigest()[:6]}"
        node = DelegationNode(
            node_id=node_id, task=task, agent=agent,
            parent_id=parent_id, depth=depth,
        )
        node.status = DelegationStatus.PROCESSING
        node.result = f"[HOJA·{agent}] Ejecutado en profundidad máxima ({depth}): {task[:60]}"
        node.status = DelegationStatus.COMPLETED
        node.completed_at = time.time()
        
        self.nodes[node_id] = node
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)
        
        return node
    
    # ═══════════════════════════════════════════
    # CONSULTAS Y VISUALIZACIÓN
    # ═══════════════════════════════════════════
    
    def get_tree(self, node_id: str = None) -> Dict:
        """Obtiene el árbol de delegación en formato JSON."""
        if node_id is None:
            # Devolver todos los árboles raíz
            return {
                "total_delegations": self.total_delegations,
                "max_depth": self.max_depth_reached,
                "roots": [self.get_tree(rid) for rid in self.root_nodes],
            }
        
        node = self.nodes.get(node_id)
        if not node:
            return {}
        
        return {
            "node_id": node.node_id,
            "agent": node.agent,
            "task": node.task[:100],
            "depth": node.depth,
            "status": node.status.value,
            "result": str(node.result)[:150] if node.result else None,
            "duration_ms": node.duration_ms,
            "children": [self.get_tree(cid) for cid in node.children],
            "delegation_chain": node.delegation_chain,
        }
    
    def print_tree(self, node_id: str = None, indent: int = 0):
        """Imprime el árbol de delegación de forma visual."""
        if node_id is None:
            for rid in self.root_nodes:
                self.print_tree(rid, 0)
            return
        
        node = self.nodes.get(node_id)
        if not node:
            return
        
        prefix = "  " * indent
        icon = "✅" if node.status in [DelegationStatus.COMPLETED, DelegationStatus.MERGED] else "🔄"
        chain = " → ".join(node.delegation_chain) if node.delegation_chain else node.agent
        
        print(f"{prefix}{icon} [{node.agent}] N{node.depth} | {node.task[:60]}...")
        
        if node.children:
            for cid in node.children:
                self.print_tree(cid, indent + 1)
    
    def get_stats(self) -> Dict:
        """Estadísticas de delegación recursiva."""
        completed = sum(1 for n in self.nodes.values() 
                       if n.status in [DelegationStatus.COMPLETED, DelegationStatus.MERGED])
        return {
            "total_delegations": self.total_delegations,
            "max_depth_reached": self.max_depth_reached,
            "completed": completed,
            "completion_rate": completed / max(1, len(self.nodes)),
            "avg_chain_length": sum(len(n.delegation_chain) for n in self.nodes.values()) / max(1, len(self.nodes)),
            "agents_used": list(set(n.agent for n in self.nodes.values())),
            "longest_chain": max(self.delegation_chains, key=len) if self.delegation_chains else [],
        }


# ─── Instancia Global ───

recursive_engine = RecursiveDelegationEngine(max_depth=4)


def delegate_recursive(task: str, agent: str = "MAESTRO") -> Dict:
    """Delega una tarea recursivamente y devuelve el árbol completo."""
    node = recursive_engine.delegate(task, agent)
    return recursive_engine.get_tree(node.node_id)


def delegate_and_print(task: str, agent: str = "MAESTRO"):
    """Delega e imprime el árbol visualmente."""
    print(f"\n🜁 DELEGACIÓN RECURSIVA: '{task[:60]}...'")
    print(f"{'─'*60}")
    node = recursive_engine.delegate(task, agent)
    recursive_engine.print_tree(node.node_id)
    print(f"{'─'*60}")
    print(f"📊 {recursive_engine.total_delegations} delegaciones, "
          f"profundidad máx: {recursive_engine.max_depth_reached}")
    return node
