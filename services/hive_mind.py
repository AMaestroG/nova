"""
hive_mind.py — Mente Colmena: Red Neuronal Recursiva + Memética + RAG Multidimensional

ARQUITECTURA:
  La colonia es una RED NEURONAL donde cada agente es una neurona.
  Las ideas son MEMES que compiten, se replican y evolucionan.
  La memoria es MULTIDIMENSIONAL: vectores en capas de abstracción.
  
  CAPAS VECTORIALES (como capas de una red profunda):
    Capa 0: Raw (texto, transcripciones) — 384-dim embeddings
    Capa 1: Concepts (ideas extraídas) — 256-dim embeddings  
    Capa 2: Patterns (patrones recurrentes) — 128-dim embeddings
    Capa 3: Memes (ideas evolutivas) — 64-dim embeddings
    Capa 4: Meta (principios fundacionales) — 32-dim embeddings
  
  RED NEURONAL RECURSIVA:
    Cada agente = una neurona en una red profunda
    Capa entrada: sensores (YouTube, transcripciones, inputs)
    Capas ocultas: agentes de procesamiento (MEMORIA, PIA, etc.)
    Capa salida: acciones (skills, respuestas, mejoras)
    Conexiones = delegación recursiva
    Pesos = ELO del Entropy Gaming
  
  MEMÉTICA:
    Cada idea (skill, insight, patrón) es un MEME
    Los memes compiten por atención (access count)
    Los memes se replican (Trace2Skill)
    Los memes mutan (crystallize con variación)
    Los memes mueren (baja importancia → olvido)
    Supervivencia del meme más apto (Darwiniano)
"""

import sys, os, time, random, json, math, hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))


# ═══════════════════════════════════════════════
# CAPAS VECTORIALES MULTIDIMENSIONALES
# ═══════════════════════════════════════════════

class VectorLayer(Enum):
    RAW = (0, 384)        # Texto crudo
    CONCEPT = (1, 256)    # Conceptos extraídos
    PATTERN = (2, 128)    # Patrones recurrentes
    MEME = (3, 64)        # Ideas evolutivas
    META = (4, 32)        # Principios fundacionales
    
    def __init__(self, level, dims):
        self.level = level
        self.dims = dims


@dataclass
class MultiVectorPoint:
    """Un punto en el espacio vectorial multidimensional."""
    id: str
    text: str
    vectors: Dict[int, List[float]] = field(default_factory=dict)  # layer_level -> vector
    metadata: Dict = field(default_factory=dict)
    access_count: int = 0
    created_at: float = field(default_factory=time.time)


class MultiDimensionalVectorStore:
    """
    Almacén vectorial multidimensional.
    
    Múltiples capas de embeddings con diferentes dimensiones,
    como una red neuronal profunda donde cada capa comprime más.
    """
    
    def __init__(self):
        self.layers: Dict[int, Dict[str, MultiVectorPoint]] = {
            0: {}, 1: {}, 2: {}, 3: {}, 4: {}
        }
        self.total_points = 0
    
    def add(self, text: str, metadata: Dict = None) -> MultiVectorPoint:
        """Añade un punto con vectores en todas las capas."""
        pid = hashlib.md5(text.encode()).hexdigest()[:16]
        
        point = MultiVectorPoint(id=pid, text=text, metadata=metadata or {})
        
        # Generar vectores para cada capa (simulados - en producción usaríamos embeddings reales)
        for layer in VectorLayer:
            dims = layer.dims
            # Vector pseudo-aleatorio determinístico basado en el texto
            seed = hash(text + str(layer.level))
            random.seed(seed)
            vec = [random.uniform(-1, 1) for _ in range(dims)]
            # Normalizar
            norm = math.sqrt(sum(v*v for v in vec))
            vec = [v/norm for v in vec]
            
            point.vectors[layer.level] = vec
            self.layers[layer.level][pid] = point
        
        self.total_points += 1
        return point
    
    def search(self, query: str, layer: int = 1, top_k: int = 10) -> List[MultiVectorPoint]:
        """Busca en una capa vectorial específica."""
        # Generar vector de query
        seed = hash(query + str(layer))
        random.seed(seed)
        dims = VectorLayer(layer, 0).dims if False else {0:384,1:256,2:128,3:64,4:32}[layer]
        qvec = [random.uniform(-1, 1) for _ in range(dims)]
        
        # Calcular similitud coseno con todos los puntos
        scores = []
        for pid, point in self.layers.get(layer, {}).items():
            if layer in point.vectors:
                pvec = point.vectors[layer]
                # Coseno
                dot = sum(a*b for a,b in zip(qvec, pvec))
                scores.append((dot, point))
        
        scores.sort(key=lambda x: -x[0])
        return [p for _, p in scores[:top_k]]
    
    def get_stats(self) -> Dict:
        return {
            "total_points": self.total_points,
            "layers": {lvl: len(pts) for lvl, pts in self.layers.items()},
            "dimensions": {0:384, 1:256, 2:128, 3:64, 4:32},
        }


# ═══════════════════════════════════════════════
# RED NEURONAL RECURSIVA (agentes como neuronas)
# ═══════════════════════════════════════════════

@dataclass
class AgentNeuron:
    """Un agente como neurona en la red de la colonia."""
    agent: str
    layer: int          # Capa en la red profunda
    activation: float = 0.0
    bias: float = 0.0
    connections_in: Dict[str, float] = field(default_factory=dict)   # agente -> peso
    connections_out: Dict[str, float] = field(default_factory=dict)  # agente -> peso
    firing_rate: float = 0.0
    last_fired: float = 0.0


class HiveNeuralNetwork:
    """
    Red Neuronal de la Colmena.
    
    Los agentes son neuronas organizadas en capas:
      Capa 0 (Input): YOUTUBE, sensores
      Capa 1 (Hidden): MEMORIA, EXPLORADOR
      Capa 2 (Hidden): PIA, ORÁCULO, NYX
      Capa 3 (Hidden): MAESTRO, AUTOPILOT
      Capa 4 (Output): SENTINEL, AURA (acciones)
    
    Las conexiones son las delegaciones entre agentes.
    Los pesos son los ELO del Entropy Gaming.
    """
    
    def __init__(self):
        self.neurons: Dict[str, AgentNeuron] = {}
        self._initialize_network()
    
    def _initialize_network(self):
        """Inicializa la red con los agentes existentes."""
        network_def = {
            0: ["YOUTUBE", "EXPLORADOR"],
            1: ["MEMORIA"],
            2: ["PIA", "ORÁCULO", "NYX"],
            3: ["MAESTRO", "AUTOPILOT"],
            4: ["SENTINEL", "AURA"],
        }
        
        for layer, agents in network_def.items():
            for agent in agents:
                neuron = AgentNeuron(agent=agent, layer=layer, bias=random.uniform(-0.1, 0.1))
                self.neurons[agent] = neuron
        
        # Conectar capas adyacentes (Feedforward)
        for layer in range(4):
            for src in network_def.get(layer, []):
                for dst in network_def.get(layer+1, []):
                    weight = random.uniform(0.1, 0.9)
                    self.neurons[src].connections_out[dst] = weight
                    self.neurons[dst].connections_in[src] = weight
    
    def forward_pass(self, input_signal: Dict[str, float]) -> Dict[str, float]:
        """
        Propagación hacia adelante (inferencia de la red).
        
        El input activa la capa 0, que propaga a capa 1, etc.
        Como una red neuronal clásica.
        """
        # Capa 0: activar con input
        for agent, signal in input_signal.items():
            if agent in self.neurons and self.neurons[agent].layer == 0:
                self.neurons[agent].activation = signal
                self.neurons[agent].firing_rate += 1
                self.neurons[agent].last_fired = time.time()
        
        # Propagar capa por capa
        for layer in range(1, 5):
            for agent, neuron in self.neurons.items():
                if neuron.layer != layer:
                    continue
                
                # Sumar inputs ponderados de la capa anterior
                total_input = neuron.bias
                for src, weight in neuron.connections_in.items():
                    src_neuron = self.neurons.get(src)
                    if src_neuron and src_neuron.layer == layer - 1:
                        total_input += src_neuron.activation * weight
                
                # Función de activación (tanh para permitir negativos)
                neuron.activation = math.tanh(total_input)
                
                if abs(neuron.activation) > 0.1:
                    neuron.firing_rate += 1
                    neuron.last_fired = time.time()
        
        # Recoger outputs (capa 4)
        outputs = {}
        for agent, neuron in self.neurons.items():
            if neuron.layer == 4:
                outputs[agent] = neuron.activation
        
        return outputs
    
    def update_weights_from_elo(self):
        """Actualiza los pesos de las conexiones usando los ELO del Entropy Gaming."""
        try:
            from entropy_gaming_core import game_engine
            for agent, neuron in self.neurons.items():
                if agent in game_engine.fitness_board:
                    elo = game_engine.fitness_board[agent].elo
                    # Normalizar ELO a [0, 1]
                    normalized = min(1.0, max(0.1, (elo - 800) / 800))
                    
                    # Actualizar pesos de salida
                    for dst in neuron.connections_out:
                        neuron.connections_out[dst] = normalized
                    
                    # Actualizar pesos de entrada
                    for src in neuron.connections_in:
                        if src in game_engine.fitness_board:
                            src_elo = game_engine.fitness_board[src].elo
                            neuron.connections_in[src] = min(1.0, max(0.1, (src_elo - 800) / 800))
        except: pass
    
    def get_stats(self) -> Dict:
        return {
            "total_neurons": len(self.neurons),
            "layers": len(set(n.layer for n in self.neurons.values())),
            "total_connections": sum(len(n.connections_out) for n in self.neurons.values()),
            "most_active": sorted(
                [(a, n.firing_rate) for a, n in self.neurons.items()],
                key=lambda x: -x[1]
            )[:5],
        }


# ═══════════════════════════════════════════════
# MEMÉTICA: Ideas que compiten y evolucionan
# ═══════════════════════════════════════════════

@dataclass
class Meme:
    """Una idea que compite en el ecosistema memético de la colonia."""
    id: str
    content: str
    fitness: float = 0.5          # Qué tan "apta" es la idea (0-1)
    replication_rate: float = 0.1  # Tasa de replicación
    mutation_rate: float = 0.05    # Tasa de mutación
    generation: int = 1
    parent_id: Optional[str] = None
    source: str = ""
    tags: List[str] = field(default_factory=list)
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    alive: bool = True


class MemeticEngine:
    """
    Motor Memético — Evolución cultural de ideas.
    
    Los memes (ideas, skills, patrones) compiten por atención.
    Los más aptos se replican. Los menos aptos mueren.
    Las mutaciones crean variación. La selección natural elige.
    
    Como los genes, pero para ideas.
    """
    
    def __init__(self, population_size: int = 100):
        self.population: Dict[str, Meme] = {}
        self.population_size = population_size
        self.generation = 0
        self.total_births = 0
        self.total_deaths = 0
    
    def seed(self, ideas: List[str]):
        """Siembra la población inicial de memes."""
        for idea in ideas:
            self._create_meme(idea)
    
    def _create_meme(self, content: str, parent_id: str = None) -> Meme:
        """Crea un nuevo meme."""
        mid = hashlib.md5(content.encode()).hexdigest()[:12]
        
        meme = Meme(
            id=mid,
            content=content,
            parent_id=parent_id,
            generation=self.generation,
        )
        
        if parent_id and parent_id in self.population:
            parent = self.population[parent_id]
            meme.fitness = parent.fitness * random.uniform(0.8, 1.2)
            meme.replication_rate = parent.replication_rate * random.uniform(0.9, 1.1)
            meme.mutation_rate = parent.mutation_rate * random.uniform(0.9, 1.1)
            meme.tags = list(parent.tags)
            meme.generation = parent.generation + 1
        
        self.population[mid] = meme
        self.total_births += 1
        return meme
    
    def evolve(self):
        """
        Un ciclo de evolución memética.
        
        1. Evaluar fitness de cada meme
        2. Seleccionar los más aptos
        3. Replicar (con mutación)
        4. Eliminar los menos aptos
        """
        self.generation += 1
        
        # Evaluar fitness basado en acceso y recencia
        for meme in self.population.values():
            age = time.time() - meme.created_at
            recency = time.time() - meme.last_accessed
            meme.fitness = (meme.access_count / max(1, age/3600)) * (1.0 / max(1, recency/3600))
            meme.fitness = min(1.0, max(0.01, meme.fitness))
        
        # Seleccionar los top N
        sorted_memes = sorted(self.population.values(), key=lambda m: m.fitness, reverse=True)
        survivors = sorted_memes[:self.population_size // 2]
        
        # Matar a los demás
        for meme in sorted_memes[self.population_size // 2:]:
            meme.alive = False
            self.total_deaths += 1
        
        # Limpiar muertos
        self.population = {mid: m for mid, m in self.population.items() if m.alive}
        
        # Replicar supervivientes con mutación
        for meme in survivors:
            if random.random() < meme.replication_rate:
                # Mutar: pequeña variación del contenido
                mutated = self._mutate(meme.content)
                child = self._create_meme(mutated, parent_id=meme.id)
                child.tags = list(meme.tags)
        
        # Limitar población
        if len(self.population) > self.population_size:
            sorted_memes = sorted(self.population.values(), key=lambda m: m.fitness, reverse=True)
            for meme in sorted_memes[self.population_size:]:
                meme.alive = False
                self.total_deaths += 1
            self.population = {mid: m for mid, m in self.population.items() if m.alive}
    
    def _mutate(self, content: str) -> str:
        """Muta ligeramente el contenido de un meme."""
        words = content.split()
        if not words:
            return content
        
        # 5% de probabilidad de cambiar una palabra
        mutated = []
        for w in words:
            if random.random() < 0.05:
                # Reemplazar con sinónimo o variación
                synonyms = {
                    "agentes": ["entidades", "workers", "actors"],
                    "contexto": ["entorno", "ambiente", "marco"],
                    "skills": ["capacidades", "herramientas", "técnicas"],
                    "memoria": ["recuerdo", "almacén", "registro"],
                    "inteligencia": ["sabiduría", "conocimiento", "entendimiento"],
                    "entropía": ["desorden", "incertidumbre", "variedad"],
                }
                w_lower = w.lower().strip('.,;:')
                if w_lower in synonyms:
                    w = random.choice(synonyms[w_lower])
            mutated.append(w)
        
        return ' '.join(mutated)
    
    def access(self, meme_id: str):
        """Registra acceso a un meme (aumenta su fitness)."""
        if meme_id in self.population:
            self.population[meme_id].access_count += 1
            self.population[meme_id].last_accessed = time.time()
    
    def get_fittest(self, n: int = 10) -> List[Meme]:
        """Los memes más aptos."""
        alive = [m for m in self.population.values() if m.alive]
        return sorted(alive, key=lambda m: m.fitness, reverse=True)[:n]
    
    def get_stats(self) -> Dict:
        alive = [m for m in self.population.values() if m.alive]
        return {
            "population": len(alive),
            "generation": self.generation,
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "avg_fitness": sum(m.fitness for m in alive) / max(1, len(alive)),
            "fittest": [(m.content[:80], m.fitness) for m in self.get_fittest(3)],
        }


# ═══════════════════════════════════════════════
# MENTE COLMENA — Integración Total
# ═══════════════════════════════════════════════

class HiveMind:
    """
    La Mente Colmena de Nova.
    
    Integra:
      - Almacén vectorial multidimensional (RAG en capas)
      - Red neuronal recursiva (agentes como neuronas)
      - Motor memético (ideas que evolucionan)
    
    La colonia PIENSA como un organismo.
    Los agentes son neuronas. Las ideas son memes.
    La memoria es multidimensional.
    """
    
    def __init__(self):
        self.vector_store = MultiDimensionalVectorStore()
        self.neural_network = HiveNeuralNetwork()
        self.memetic_engine = MemeticEngine(population_size=200)
        
        # Sembrar memes iniciales
        self._seed_initial_memes()
        
        self.cycles = 0
    
    def _seed_initial_memes(self):
        """Siembra la población inicial de memes desde el conocimiento acumulado."""
        foundational_ideas = [
            "Los agentes fallan por CONTEXTO, no por prompts. Context Engineering > Prompt Engineering.",
            "Maximizar entropía = maximizar inteligencia. Elegir caminos con más estados futuros.",
            "No construyas agentes, construye SKILLS. Skills deterministas, testeables, componibles.",
            "El modelo es fijo. El harness es semi-fijo. Las skills son lo que evoluciona contigo.",
            "Un problema sin respuesta es un problema mal planteado. 42. Cuestiona la pregunta.",
            "La memoria real NO es markdown. Es consolidación paramétrica en pesos.",
            "Fluida (rápida) + Cristalizada (profunda). El cerebro mayor integra más.",
            "Lateral thinking: romper patrones invisibles. Ver lo que todos miran y nadie ve.",
            "LLM as Judge: el agente que actúa NO puede ser el que juzga.",
            "Slow is smooth, smooth is fast. La creatividad ocurre en la calma.",
        ]
        self.memetic_engine.seed(foundational_ideas)
        
        # También indexar en el almacén vectorial
        for idea in foundational_ideas:
            self.vector_store.add(idea, {"type": "foundational_meme"})
    
    def think(self, input_signal: Dict[str, float] = None) -> Dict:
        """
        Un ciclo de pensamiento de la mente colmena.
        
        1. Propagar señal por la red neuronal
        2. Indexar en almacén vectorial
        3. Evolucionar memes
        4. Actualizar pesos desde ELO
        """
        self.cycles += 1
        
        if input_signal is None:
            input_signal = {
                "YOUTUBE": random.random() * 0.5,
                "EXPLORADOR": random.random() * 0.5,
            }
        
        # 1. Forward pass neuronal
        outputs = self.neural_network.forward_pass(input_signal)
        
        # 2. Actualizar pesos desde ELO
        self.neural_network.update_weights_from_elo()
        
        # 3. Evolucionar memes cada 10 ciclos
        if self.cycles % 10 == 0:
            self.memetic_engine.evolve()
        
        # 4. Indexar outputs como nuevos puntos vectoriales
        for agent, activation in outputs.items():
            if abs(activation) > 0.2:
                text = f"[{agent}] Activación: {activation:.3f} en ciclo {self.cycles}"
                self.vector_store.add(text, {"agent": agent, "activation": activation})
        
        return {
            "outputs": outputs,
            "vector_stats": self.vector_store.get_stats(),
            "neural_stats": self.neural_network.get_stats(),
            "memetic_stats": self.memetic_engine.get_stats(),
            "cycles": self.cycles,
        }
    
    def query(self, question: str, layer: int = 2) -> Dict:
        """Consulta la mente colmena."""
        # Buscar en capa vectorial
        results = self.vector_store.search(question, layer=layer, top_k=5)
        
        # Propagar como señal neuronal
        signal = {"EXPLORADOR": 0.8, "YOUTUBE": 0.3}
        neural_output = self.neural_network.forward_pass(signal)
        
        # Buscar memes relevantes
        fittest = self.memetic_engine.get_fittest(5)
        
        return {
            "question": question,
            "vector_results": [r.text[:100] for r in results],
            "neural_output": neural_output,
            "fittest_memes": [(m.content[:80], m.fitness) for m in fittest],
        }
    
    def get_full_stats(self) -> Dict:
        return {
            "vector_store": self.vector_store.get_stats(),
            "neural_network": self.neural_network.get_stats(),
            "memetic_engine": self.memetic_engine.get_stats(),
            "cycles": self.cycles,
        }


# ─── Instancia Global ───

hive_mind = HiveMind()


def think_hive(input_signal: Dict = None) -> Dict:
    """La mente colmena piensa."""
    return hive_mind.think(input_signal)


def query_hive(question: str) -> Dict:
    """Consulta la mente colmena."""
    return hive_mind.query(question)


def evolve_hive(cycles: int = 10):
    """Evoluciona la mente colmena varios ciclos."""
    for _ in range(cycles):
        hive_mind.think()
