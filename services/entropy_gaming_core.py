"""
entropy_gaming_core.py — Gamificación con Entropía en el Núcleo de Nova

INSPIRACIÓN:
  - DeepMind: AlphaZero self-play, juegos como banco de pruebas
  - @code4AI: HyEvo (evolución topológica), Darwin-Gödel HyperAgent
  - @aiDotEngineer: Agent Reinforcement Fine Tuning (OpenAI)
  - Teoría de la Información: Entropía de Shannon

CONCEPTO: Nova funciona como un JUEGO interno donde los agentes compiten,
cooperan y evolucionan. La ENTROPÍA es el regulador maestro:
  - Alta entropía → mucha exploración, diversidad, caos creativo
  - Baja entropía → mucha explotación, especialización, eficiencia
  - Entropía óptima → equilibrio exploración/explotación (borde del caos)

ARQUITECTURA DEL JUEGO:
  
  ┌──────────────────────────────────────────────────────┐
  │              ENTROPY GAMING CORE                     │
  │                                                      │
  │  ┌──────────────┐    ┌──────────────────────────┐   │
  │  │ Entropy      │───▶│ Game Engine              │   │
  │  │ Regulator    │    │                          │   │
  │  │              │◀───│ • Torneos (CASP-style)   │   │
  │  │ • Shannon H  │    │ • Self-Play (AlphaZero)  │   │
  │  │ • Diversity  │    │ • Fitness scoring        │   │
  │  │ • Novelty    │    │ • Selection pressure     │   │
  │  │ • Phase      │    │ • Mutation rate          │   │
  │  └──────────────┘    └──────────┬───────────────┘   │
  │                                 │                    │
  │                          ┌──────▼────────┐          │
  │                          │ Agent Arena   │          │
  │                          │               │          │
  │                          │ PIA vs MEMORIA│          │
  │                          │ MAESTRO vs    │          │
  │                          │ SENTINEL vs   │          │
  │                          │ EXPLORADOR    │          │
  │                          └───────────────┘          │
  └──────────────────────────────────────────────────────┘
"""

import math
import json
import time
import random
import hashlib
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import os


# ═══════════════════════════════════════════════
# ENTROPÍA: El Regulador Maestro
# ═══════════════════════════════════════════════

class EntropyPhase(Enum):
    """Fases de entropía del enjambre."""
    CHAOS = "chaos"           # Máxima exploración, sin explotación
    EXPLORATION = "exploration"  # Principalmente explorando
    BALANCE = "balance"       # Equilibrio óptimo (borde del caos)
    EXPLOITATION = "exploitation"  # Principalmente explotando
    STAGNATION = "stagnation" # Sin exploración, solo explotación


@dataclass
class EntropyState:
    """Estado entrópico del enjambre."""
    shannon_entropy: float = 0.0        # H = -Σ p(x) log p(x)
    diversity_index: float = 0.0         # Simpson: 1 - Σ p²
    novelty_rate: float = 0.0            # % de acciones nuevas vs repetidas
    surprise_mean: float = 0.0           # Sorpresa promedio (inverso de probabilidad)
    phase: EntropyPhase = EntropyPhase.BALANCE
    temperature: float = 1.0             # Temperatura para softmax/exploración
    mutation_rate: float = 0.1           # Tasa de mutación para evolución
    selection_pressure: float = 0.5      # Presión selectiva (0=aleatorio, 1=élite)


class EntropyRegulator:
    """
    Regulador de Entropía — el director de orquesta del juego.
    
    Mide la entropía del enjambre en tiempo real y ajusta los parámetros
    del juego para mantener el equilibrio óptimo (borde del caos).
    """
    
    def __init__(self, target_entropy: float = 1.5):
        self.target_entropy = target_entropy
        self.history: List[EntropyState] = []
        self.state = EntropyState()
        
        # Contadores para medir entropía
        self.action_counts: Dict[str, Counter] = defaultdict(Counter)
        self.total_actions = 0
        self.novel_actions = 0
        self.surprise_log: List[float] = []
        
        # Parámetros adaptativos
        self.temperature = 1.0
        self.mutation_rate = 0.1
        self.selection_pressure = 0.5
    
    def observe_action(self, agent: str, action: str, probability: float = 0.5):
        """
        Observa una acción de un agente para calcular entropía.
        
        Args:
            agent: Nombre del agente
            action: Acción realizada
            probability: Probabilidad estimada de la acción (1-p = sorpresa)
        """
        self.action_counts[agent][action] += 1
        self.total_actions += 1
        
        # ¿Es una acción nueva?
        if self.action_counts[agent][action] == 1:
            self.novel_actions += 1
        
        # Sorpresa = -log(probabilidad)
        surprise = -math.log(max(probability, 0.001))
        self.surprise_log.append(surprise)
        
        # Mantener solo últimos 1000
        if len(self.surprise_log) > 1000:
            self.surprise_log = self.surprise_log[-1000:]
    
    def measure(self) -> EntropyState:
        """
        Mide la entropía actual del enjambre.
        
        Calcula:
          - Entropía de Shannon: H = -Σ p(x) log₂ p(x)
          - Índice de diversidad de Simpson: D = 1 - Σ p(x)²
          - Tasa de novedad: acciones nuevas / total
          - Sorpresa media: promedio de -log(p)
        """
        if self.total_actions == 0:
            return EntropyState()
        
        # Consolidar todas las acciones
        all_actions = Counter()
        for agent_counts in self.action_counts.values():
            all_actions.update(agent_counts)
        
        total = sum(all_actions.values())
        if total == 0:
            return EntropyState()
        
        # Entropía de Shannon
        shannon_h = 0.0
        simpson_d = 0.0
        for count in all_actions.values():
            p = count / total
            shannon_h -= p * math.log2(p)
            simpson_d += p * p
        
        simpson_d = 1.0 - simpson_d  # Diversidad (0=todo igual, 1=todo diverso)
        
        # Novedad
        novelty = self.novel_actions / max(1, total)
        
        # Sorpresa media
        surprise_mean = sum(self.surprise_log) / max(1, len(self.surprise_log))
        
        # Determinar fase
        phase = self._determine_phase(shannon_h, novelty)
        
        # Ajustar parámetros según la fase
        self._adapt_parameters(shannon_h, phase)
        
        state = EntropyState(
            shannon_entropy=shannon_h,
            diversity_index=simpson_d,
            novelty_rate=novelty,
            surprise_mean=surprise_mean,
            phase=phase,
            temperature=self.temperature,
            mutation_rate=self.mutation_rate,
            selection_pressure=self.selection_pressure,
        )
        
        self.state = state
        self.history.append(state)
        
        return state
    
    def _determine_phase(self, entropy: float, novelty: float) -> EntropyPhase:
        """Determina la fase del enjambre basada en entropía."""
        if entropy < 0.5 and novelty < 0.05:
            return EntropyPhase.STAGNATION
        elif entropy < 1.0:
            return EntropyPhase.EXPLOITATION
        elif entropy > 3.0 and novelty > 0.3:
            return EntropyPhase.CHAOS
        elif entropy > 2.0:
            return EntropyPhase.EXPLORATION
        else:
            return EntropyPhase.BALANCE
    
    def _adapt_parameters(self, entropy: float, phase: EntropyPhase):
        """
        Adapta los parámetros del juego para mantener entropía óptima.
        
        Principio cibernético: si la entropía se desvía del objetivo,
        ajustar parámetros en dirección opuesta.
        """
        error = self.target_entropy - entropy
        
        # Temperatura: controla exploración (softmax)
        if phase == EntropyPhase.STAGNATION:
            self.temperature = min(5.0, self.temperature * 1.5)
            self.mutation_rate = min(0.5, self.mutation_rate * 1.3)
            self.selection_pressure = max(0.1, self.selection_pressure * 0.7)
        elif phase == EntropyPhase.EXPLOITATION:
            self.temperature = min(3.0, self.temperature * 1.15)
            self.mutation_rate = min(0.3, self.mutation_rate * 1.1)
        elif phase == EntropyPhase.CHAOS:
            self.temperature = max(0.3, self.temperature * 0.7)
            self.mutation_rate = max(0.02, self.mutation_rate * 0.5)
            self.selection_pressure = min(0.9, self.selection_pressure * 1.3)
        elif phase == EntropyPhase.EXPLORATION:
            self.temperature *= 0.9
            self.mutation_rate *= 0.9
        else:  # BALANCE
            self.temperature += error * 0.1
            self.temperature = max(0.5, min(2.0, self.temperature))
        
        # Mantener en rangos
        self.temperature = max(0.1, min(5.0, self.temperature))
        self.mutation_rate = max(0.01, min(0.5, self.mutation_rate))
        self.selection_pressure = max(0.05, min(0.95, self.selection_pressure))
    
    def get_phase_action(self) -> str:
        """Devuelve la acción recomendada según la fase actual."""
        phase = self.state.phase
        return {
            EntropyPhase.CHAOS: "FOCUS: Reduce exploration, increase selection pressure",
            EntropyPhase.EXPLORATION: "GUIDE: Slightly reduce temperature, keep exploring",
            EntropyPhase.BALANCE: "MAINTAIN: Perfect balance. Continue.",
            EntropyPhase.EXPLOITATION: "SHAKE: Increase temperature, force mutation",
            EntropyPhase.STAGNATION: "RESET: Maximum temperature, random restart, new blood",
        }.get(phase, "OBSERVE")


# ═══════════════════════════════════════════════
# GAME ENGINE: Torneos, Self-Play, Fitness
# ═══════════════════════════════════════════════

@dataclass
class AgentFitness:
    """Fitness de un agente en el juego."""
    agent: str
    score: float = 0.0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    elo: float = 1000.0           # Rating ELO
    creativity: float = 0.0        # Cuántas soluciones NO estándar genera
    efficiency: float = 0.0        # Tokens/CPU por tarea
    reliability: float = 0.0       # Tasa de éxito
    compound_skill_count: int = 0  # Skills generadas
    last_played: float = 0.0
    entropy_contribution: float = 0.0  # Cuánta entropía aporta al enjambre


@dataclass
class GameResult:
    """Resultado de un enfrentamiento entre agentes."""
    game_id: str
    agent_a: str
    agent_b: str
    winner: str                     # 'A', 'B', o 'draw'
    task: str
    score_a: float
    score_b: float
    duration_ms: float
    entropy_delta: float = 0.0       # Cambio en entropía después del juego
    timestamp: float = field(default_factory=time.time)


class GameEngine:
    """
    Motor de Juego — torneos, self-play, fitness.
    
    Torneos:
      - Round-robin: todos contra todos
      - Eliminación directa: bracket
      - Self-play: agente contra sí mismo (AlphaZero style)
    
    Fitness:
      - ELO rating (como ajedrez)
      - Creatividad (soluciones no estándar)
      - Eficiencia (recursos por tarea)
      - Fiabilidad (tasa de éxito)
    """
    
    def __init__(self, entropy_regulator: EntropyRegulator = None):
        self.entropy = entropy_regulator or EntropyRegulator()
        self.fitness_board: Dict[str, AgentFitness] = {}
        self.game_history: List[GameResult] = []
        self.tournament_count = 0
        self.k_factor = 32  # ELO K-factor
    
    def register_agent(self, agent: str, initial_elo: float = 1000.0):
        """Registra un agente en el juego."""
        if agent not in self.fitness_board:
            self.fitness_board[agent] = AgentFitness(
                agent=agent,
                elo=initial_elo,
                last_played=time.time(),
            )
    
    def play_match(self, agent_a: str, agent_b: str, task: str,
                   score_a: float, score_b: float, duration_ms: float = 0) -> GameResult:
        """
        Registra un enfrentamiento entre dos agentes.
        
        Actualiza ELO, fitness, y entropía.
        """
        self.register_agent(agent_a)
        self.register_agent(agent_b)
        
        # Determinar ganador
        if score_a > score_b:
            winner = 'A'
        elif score_b > score_a:
            winner = 'B'
        else:
            winner = 'draw'
        
        result = GameResult(
            game_id=f"game_{len(self.game_history)}_{int(time.time())}",
            agent_a=agent_a,
            agent_b=agent_b,
            winner=winner,
            task=task,
            score_a=score_a,
            score_b=score_b,
            duration_ms=duration_ms,
        )
        
        # Actualizar ELO
        self._update_elo(agent_a, agent_b, winner)
        
        # Actualizar fitness
        fa = self.fitness_board[agent_a]
        fb = self.fitness_board[agent_b]
        
        if winner == 'A':
            fa.wins += 1
            fb.losses += 1
        elif winner == 'B':
            fb.wins += 1
            fa.losses += 1
        else:
            fa.draws += 1
            fb.draws += 1
        
        fa.last_played = fb.last_played = time.time()
        fa.score = self._calculate_fitness(fa)
        fb.score = self._calculate_fitness(fb)
        
        # Medir entropía
        self.entropy.observe_action(agent_a, f"match_vs_{agent_b}", 0.5)
        self.entropy.observe_action(agent_b, f"match_vs_{agent_a}", 0.5)
        
        # Delta de entropía
        prev_entropy = self.entropy.state.shannon_entropy
        new_state = self.entropy.measure()
        result.entropy_delta = new_state.shannon_entropy - prev_entropy
        
        self.game_history.append(result)
        return result
    
    def _update_elo(self, agent_a: str, agent_b: str, winner: str):
        """Actualiza ratings ELO."""
        fa = self.fitness_board[agent_a]
        fb = self.fitness_board[agent_b]
        
        # Expected score
        ea = 1.0 / (1.0 + 10 ** ((fb.elo - fa.elo) / 400.0))
        eb = 1.0 - ea
        
        # Actual score
        if winner == 'A':
            sa, sb = 1.0, 0.0
        elif winner == 'B':
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5
        
        fa.elo += self.k_factor * (sa - ea)
        fb.elo += self.k_factor * (sb - eb)
    
    def _calculate_fitness(self, agent_fitness: AgentFitness) -> float:
        """Calcula fitness compuesto."""
        total_games = agent_fitness.wins + agent_fitness.losses + agent_fitness.draws
        if total_games == 0:
            return 0.0
        
        win_rate = agent_fitness.wins / total_games
        elo_factor = agent_fitness.elo / 2000.0  # Normalizado
        
        # Fitness = combinación de ELO, win rate, creatividad, eficiencia
        return (
            win_rate * 0.35 +
            elo_factor * 0.25 +
            agent_fitness.creativity * 0.15 +
            agent_fitness.efficiency * 0.15 +
            agent_fitness.reliability * 0.10
        )
    
    def run_tournament(self, agents: List[str], task_generator, rounds: int = 3) -> List[GameResult]:
        """
        Ejecuta un torneo round-robin entre agentes.
        
        Args:
            agents: Lista de agentes participantes
            task_generator: Función que genera tareas (task, scoring_fn)
            rounds: Rondas del torneo
        
        Returns:
            Lista de resultados
        """
        self.tournament_count += 1
        results = []
        
        print(f"\n🏆 TORNEO #{self.tournament_count} — {len(agents)} agentes, {rounds} rondas")
        print(f"   Fase entrópica: {self.entropy.state.phase.value}")
        print(f"   Temperatura: {self.entropy.temperature:.2f}")
        print(f"   Mutación: {self.entropy.mutation_rate:.0%}")
        
        for r in range(rounds):
            print(f"\n── Ronda {r+1}/{rounds} ──")
            
            # Emparejar agentes (todos contra todos)
            for i, agent_a in enumerate(agents):
                for agent_b in agents[i+1:]:
                    # Generar tarea
                    task, score_fn = task_generator()
                    
                    # Simular ejecución (en producción, llamaría a los agentes reales)
                    score_a = random.random() * self.entropy.temperature
                    score_b = random.random() * self.entropy.temperature
                    
                    # Añadir ventaja ELO
                    fa = self.fitness_board.get(agent_a, AgentFitness(agent_a))
                    fb = self.fitness_board.get(agent_b, AgentFitness(agent_b))
                    score_a *= (1 + (fa.elo - 1000) / 2000)
                    score_b *= (1 + (fb.elo - 1000) / 2000)
                    
                    result = self.play_match(agent_a, agent_b, task, score_a, score_b)
                    results.append(result)
                    
                    winner_name = agent_a if result.winner == 'A' else agent_b if result.winner == 'B' else 'empate'
                    print(f"  {agent_a:15s} vs {agent_b:15s} → {winner_name}")
        
        # Mostrar leaderboard
        self._show_leaderboard()
        
        # Medir entropía post-torneo
        state = self.entropy.measure()
        print(f"\n📊 Entropía post-torneo: H={state.shannon_entropy:.2f}, fase={state.phase.value}")
        print(f"   Acción recomendada: {self.entropy.get_phase_action()}")
        
        return results
    
    def self_play(self, agent: str, iterations: int = 100) -> List[GameResult]:
        """
        Self-play estilo AlphaZero: agente contra sí mismo.
        
        El agente juega contra versiones anteriores de sí mismo,
        aprendiendo de cada partida.
        """
        results = []
        print(f"\n🎮 SELF-PLAY: {agent} ({iterations} iteraciones)")
        
        for i in range(iterations):
            # El agente juega contra sí mismo con parámetros ligeramente diferentes
            temp = self.entropy.temperature * (1 + 0.1 * math.sin(i * 0.1))
            
            score_v1 = random.random() * temp
            score_v2 = random.random() * temp
            
            result = self.play_match(
                f"{agent}_v1", f"{agent}_v2",
                f"self_play_{i}",
                score_v1, score_v2
            )
            results.append(result)
            
            if i % 25 == 0:
                print(f"  Iteración {i}: {result.winner} (H={self.entropy.state.shannon_entropy:.2f})")
        
        return results
    
    def _show_leaderboard(self):
        """Muestra la tabla de clasificación."""
        ranked = sorted(self.fitness_board.values(), key=lambda f: f.score, reverse=True)
        print(f"\n📊 LEADERBOARD:")
        print(f"  {'Agente':15s} {'ELO':>6s} {'W':>4s} {'L':>4s} {'D':>4s} {'Score':>6s}")
        print(f"  {'─'*45}")
        for f in ranked:
            if f.wins + f.losses + f.draws > 0:
                print(f"  {f.agent:15s} {f.elo:6.0f} {f.wins:4d} {f.losses:4d} {f.draws:4d} {f.score:6.3f}")
    
    def get_champion(self) -> Optional[AgentFitness]:
        """Devuelve el agente con mayor fitness."""
        if not self.fitness_board:
            return None
        return max(self.fitness_board.values(), key=lambda f: f.score)
    
    def get_most_entropic(self) -> Optional[AgentFitness]:
        """Devuelve el agente que más entropía aporta (más creativo/diverso)."""
        if not self.fitness_board:
            return None
        return max(self.fitness_board.values(), key=lambda f: f.entropy_contribution)
    
    def evolve_population(self, survival_rate: float = 0.5):
        """
        Evoluciona la población de agentes.
        
        Los agentes con menor fitness son "eliminados" y reemplazados
        por mutaciones de los mejores (selección natural + entropía).
        """
        ranked = sorted(self.fitness_board.values(), key=lambda f: f.score, reverse=True)
        cutoff = int(len(ranked) * survival_rate)
        
        survivors = ranked[:cutoff]
        eliminated = ranked[cutoff:]
        
        print(f"\n🧬 EVOLUCIÓN:")
        print(f"   Supervivientes: {len(survivors)}")
        print(f"   Eliminados: {len(eliminated)}")
        print(f"   Tasa de mutación: {self.entropy.mutation_rate:.0%}")
        
        for agent in eliminated:
            # "Mutación": reiniciar con variación
            self.fitness_board[agent.agent] = AgentFitness(
                agent=agent.agent,
                elo=1000.0 + random.gauss(0, 100),
                creativity=random.random() * self.entropy.mutation_rate,
                entropy_contribution=random.random(),
            )
        
        return survivors, eliminated
    
    def get_stats(self) -> Dict:
        """Estadísticas completas del juego."""
        return {
            "tournaments": self.tournament_count,
            "total_games": len(self.game_history),
            "agents_registered": len(self.fitness_board),
            "champion": self.get_champion().agent if self.get_champion() else None,
            "entropy_state": {
                "shannon_h": self.entropy.state.shannon_entropy,
                "diversity": self.entropy.state.diversity_index,
                "novelty": self.entropy.state.novelty_rate,
                "phase": self.entropy.state.phase.value,
                "recommended_action": self.entropy.get_phase_action(),
            },
            "parameters": {
                "temperature": self.entropy.temperature,
                "mutation_rate": self.entropy.mutation_rate,
                "selection_pressure": self.entropy.selection_pressure,
            },
            "leaderboard": [
                {"agent": f.agent, "elo": f.elo, "score": f.score, "wins": f.wins}
                for f in sorted(self.fitness_board.values(), key=lambda x: -x.score)[:10]
                if f.wins + f.losses > 0
            ],
        }


# ═══════════════════════════════════════════════
# INSTANCIA GLOBAL DEL JUEGO
# ═══════════════════════════════════════════════

# El núcleo de juego de Nova
entropy_regulator = EntropyRegulator(target_entropy=1.5)
game_engine = GameEngine(entropy_regulator)


def register_in_game(agent: str):
    """Registra un agente en el juego."""
    game_engine.register_agent(agent)


def play_tournament(agents: List[str] = None, rounds: int = 3):
    """Ejecuta un torneo entre agentes."""
    if agents is None:
        agents = ["PIA", "MAESTRO", "SENTINEL", "MEMORIA", "EXPLORADOR", "ORÁCULO"]
    
    def random_task():
        tasks = [
            "optimizar_memoria", "verificar_seguridad", "predecir_tendencia",
            "buscar_informacion", "generar_resumen", "clasificar_datos",
        ]
        task = random.choice(tasks)
        return task, lambda: random.random()
    
    return game_engine.run_tournament(agents, random_task, rounds)


def get_game_state() -> Dict:
    """Obtiene el estado actual del juego."""
    return game_engine.get_stats()


def entropy_phase() -> str:
    """Fase entrópica actual y acción recomendada."""
    state = entropy_regulator.measure()
    return f"Fase: {state.phase.value} | H={state.shannon_entropy:.2f} | {entropy_regulator.get_phase_action()}"
