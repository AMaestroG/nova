#!/usr/bin/env python3
"""
Nova Tactician — Swarm Coordination Engine
Implements the Plan-Action-AgentProperties pattern from 
Elohim Puon's 1997 UNAM thesis "Sistema multiagentes para INTERNET (Java+Aglets)"

Directly inspired by the Java classes found in the thesis (pages 202-217):
- Plan (extends Vector) → ActionPlan
- AgentProperties → AgentContext
- PlanLibraryEntry → ActionRule
- Keyword → TagSet

Modernized for Nova's 16-agent Python swarm (2026).
"""
import sys
import time
import json
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ActionType(Enum):
    """Types of actions an agent can execute. Extends Puon's Plan actions."""
    SEARCH = "search"         # Discoverer agent (Puon's original)
    INTERMEDIATE = "intermediate"  # Intermediary agent (Puon's original)
    CENTRALIZE = "centralize" # Central agent (Puon's original)
    CREATE = "create"         # PINCEL, NYX
    PROTECT = "protect"       # SENTINEL
    ORCHESTRATE = "orchestrate"  # MAESTRO
    LEARN = "learn"           # PIA, MEMORIA
    PREDICT = "predict"       # ORÁCULO
    COMMUNICATE = "communicate"  # HERMES
    STORE = "store"           # MEMORIA, MNEMOS
    MONITOR = "monitor"       # CRONOS, SENTINEL
    GENERATE = "generate"     # BANCO


class EnvironmentState(Enum):
    """Environment states, inspired by Puon's status evaluation."""
    STABLE = "stable"
    GROWING = "growing"
    STRESSED = "stressed"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ActionRule:
    """
    PlanLibraryEntry from Puon's 1997 thesis, modernized.
    
    Original Java (page 205):
    public class PlanLibraryEntry {
        private Plan plan;
        private Status currentStatus;
        ...
    }
    """
    rule_id: str
    action_type: ActionType
    target: str
    condition: Callable[[Dict], bool]
    priority: int = 5
    cooldown: float = 10.0  # seconds
    last_executed: float = 0.0
    
    def can_execute(self, env_state: Dict) -> bool:
        if time.time() - self.last_executed < self.cooldown:
            return False
        return self.condition(env_state)
    
    def execute(self, agent: 'TacticalAgent') -> Dict:
        self.last_executed = time.time()
        return {
            'rule_id': self.rule_id,
            'action': self.action_type.value,
            'target': self.target,
            'agent': agent.name,
            'timestamp': time.time()
        }


@dataclass
class AgentContext:
    """
    AgentProperties from Puon's 1997 thesis, modernized.
    
    Original Java (page 203):
    public class AgentProperties extends Properties {
        private AgletID masterID;
        private String fileOnDiskName;
        ...
    }
    """
    name: str
    level: str  # N0, N1, N2
    capabilities: List[ActionType] = field(default_factory=list)
    rules: List[ActionRule] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    master_agent: Optional[str] = None  # Puon's masterID
    metadata: Dict[str, Any] = field(default_factory=dict)


class TacticalAgent:
    """
    An agent that can plan and execute actions, inspired by Puon's 1997 Aglets.
    """
    
    def __init__(self, name: str, level: str, master: Optional[str] = None):
        self.name = name
        self.level = level
        self.master = master or "AURA"
        self.context = AgentContext(
            name=name, 
            level=level,
            master_agent=self.master
        )
        self.execution_history: List[Dict] = []
        self.active = True
    
    def add_rule(self, rule: ActionRule):
        self.context.rules.append(rule)
        if rule.action_type not in self.context.capabilities:
            self.context.capabilities.append(rule.action_type)
    
    def evaluate(self, env_state: Dict) -> Optional[ActionRule]:
        """Evaluate environment and select best action, like Puon's status evaluation."""
        executable_rules = [r for r in self.context.rules if r.can_execute(env_state)]
        if not executable_rules:
            return None
        
        # Sort by priority (higher = more urgent)
        executable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Select highest priority executable rule
        # Puon's original code used PlanLibrary to select best plan for current status
        selected = executable_rules[0]
        return selected
    
    def act(self, env_state: Dict) -> Optional[Dict]:
        """Execute the best action for the current environment state."""
        rule = self.evaluate(env_state)
        if not rule:
            return None
        
        result = rule.execute(self)
        self.execution_history.append(result)
        return result


class NovaTactician:
    """
    Swarm Coordinator — Implements Puon's 1997 multi-agent architecture
    for Nova's 16 agents.
    
    Original architecture had 3 agent types: Central, Intermediary, Discoverer.
    Nova has 16 specialized agents mapped to Puon's types + Nova-specific capabilities.
    """
    
    def __init__(self):
        self.agents: Dict[str, TacticalAgent] = {}
        self.environment: Dict[str, Any] = {}
        self.action_log: List[Dict] = []
        self._init_agents()
        self._init_rules()
    
    def _init_agents(self):
        """Initialize all 16 Nova agents with Puon-inspired context."""
        agents_config = {
            # N0 — Core (Central type in Puon's terms)
            'AURA': ('N0', None),
            'MAESTRO': ('N0', 'AURA'),
            'PIA': ('N0', 'AURA'),
            'PINCEL': ('N0', 'MAESTRO'),
            'ATHENA': ('N0', 'MAESTRO'),
            # N1 — Operational (Intermediary type in Puon's terms)
            'NYX': ('N1', 'AURA'),
            'SENTINEL': ('N1', 'AURA'),
            'MAYORDOMO': ('N1', 'MAESTRO'),
            'BANCO': ('N1', 'MAESTRO'),
            # N2 — Support (Discoverer type in Puon's terms)
            'ORÁCULO': ('N2', 'ATHENA'),
            'TELAR': ('N2', 'MAESTRO'),
            'EXPLORADOR': ('N2', 'ATHENA'),
            'MEMORIA': ('N2', 'MAYORDOMO'),
            'CRONOS': ('N2', 'MAYORDOMO'),
            'HERMES': ('N2', 'MAYORDOMO'),
            'MNEMOS': ('N2', 'MEMORIA'),
        }
        
        for name, (level, master) in agents_config.items():
            self.agents[name] = TacticalAgent(name, level, master)
    
    def _init_rules(self):
        """Initialize action rules based on Puon's PlanLibrary pattern."""
        
        # SENTINEL — Monitor and protect (critical priority)
        self.agents['SENTINEL'].add_rule(ActionRule(
            rule_id='monitor_threats',
            action_type=ActionType.MONITOR,
            target='system_security',
            condition=lambda env: env.get('threat_level', 0) > 0.3,
            priority=10
        ))
        self.agents['SENTINEL'].add_rule(ActionRule(
            rule_id='protect_perimeter',
            action_type=ActionType.PROTECT,
            target='system_boundaries',
            condition=lambda env: env.get('threat_level', 0) > 0.7,
            priority=10
        ))
        
        # BANCO — Generate value when economy needs it
        self.agents['BANCO'].add_rule(ActionRule(
            rule_id='generate_income',
            action_type=ActionType.GENERATE,
            target='revenue_streams',
            condition=lambda env: env.get('financial_pressure', 0) > 0.5,
            priority=9
        ))
        self.agents['BANCO'].add_rule(ActionRule(
            rule_id='optimize_resources',
            action_type=ActionType.INTERMEDIATE,
            target='resource_allocation',
            condition=lambda env: True,
            priority=5,
            cooldown=60
        ))
        
        # MAESTRO — Orchestrate when tasks accumulate
        self.agents['MAESTRO'].add_rule(ActionRule(
            rule_id='orchestrate_tasks',
            action_type=ActionType.ORCHESTRATE,
            target='task_queue',
            condition=lambda env: env.get('pending_tasks', 0) > 3,
            priority=8
        ))
        
        # EXPLORADOR — Search when information is needed
        self.agents['EXPLORADOR'].add_rule(ActionRule(
            rule_id='search_information',
            action_type=ActionType.SEARCH,
            target='knowledge_sources',
            condition=lambda env: env.get('knowledge_gap', False),
            priority=6
        ))
        
        # NYX — Create when inspiration strikes
        self.agents['NYX'].add_rule(ActionRule(
            rule_id='dream_create',
            action_type=ActionType.CREATE,
            target='creative_output',
            condition=lambda env: env.get('creative_demand', 0) > 0.3,
            priority=4,
            cooldown=30
        ))
        
        # PIA — Learn and grow continuously
        self.agents['PIA'].add_rule(ActionRule(
            rule_id='learn_evolve',
            action_type=ActionType.LEARN,
            target='system_evolution',
            condition=lambda env: True,
            priority=3,
            cooldown=120
        ))
        
        # HERMES — Communicate when needed
        self.agents['HERMES'].add_rule(ActionRule(
            rule_id='send_message',
            action_type=ActionType.COMMUNICATE,
            target='external_comms',
            condition=lambda env: env.get('message_queue', 0) > 0,
            priority=7
        ))
        
        # ORÁCULO — Predict future states
        self.agents['ORÁCULO'].add_rule(ActionRule(
            rule_id='predict_trends',
            action_type=ActionType.PREDICT,
            target='future_states',
            condition=lambda env: env.get('uncertainty', 0) > 0.5,
            priority=5,
            cooldown=300
        ))
    
    def update_environment(self, metrics: Dict):
        """Update the shared environment state that all agents perceive."""
        self.environment.update(metrics)
        
        # Compute derived states
        cpu = metrics.get('cpu_percent', 50)
        ram = metrics.get('ram_percent', 50)
        
        self.environment['threat_level'] = max(0, min(1, (cpu / 100) * 0.4 + (ram / 100) * 0.3))
        self.environment['financial_pressure'] = 0.7 if metrics.get('need_income', False) else 0.2
        self.environment['pending_tasks'] = metrics.get('pending_tasks', 0)
        self.environment['creative_demand'] = metrics.get('creative_demand', 0.5)
        self.environment['knowledge_gap'] = metrics.get('knowledge_gap', False)
        self.environment['uncertainty'] = metrics.get('uncertainty', 0.3)
    
    def tick(self) -> List[Dict]:
        """Execute one coordination cycle. All agents evaluate and act."""
        actions_taken = []
        
        for name, agent in self.agents.items():
            if not agent.active:
                continue
            
            result = agent.act(self.environment)
            if result:
                actions_taken.append(result)
                self.action_log.append(result)
        
        return actions_taken
    
    def get_status(self) -> Dict:
        """Get current swarm coordination status."""
        return {
            'agents_total': len(self.agents),
            'agents_active': sum(1 for a in self.agents.values() if a.active),
            'environment': self.environment,
            'recent_actions': self.action_log[-10:] if self.action_log else [],
            'total_actions': len(self.action_log),
            'inspiration': 'Puon Sanchez, E. (1997). Sistema multiagentes para Internet. UNAM.',
            'original_tech': 'Java + Aglets Workbench (IBM)',
            'modern_tech': 'Python + Nova Swarm (2026)'
        }


if __name__ == "__main__":
    tactician = NovaTactician()
    
    print("=" * 60)
    print("Nova Tactician — Swarm Coordination Engine")
    print("Based on: Puon's multi-agent architecture (UNAM, 1997)")
    print("=" * 60)
    
    # Simulate different environment states
    scenarios = [
        {'name': 'Normal operation', 'cpu_percent': 30, 'ram_percent': 40, 'pending_tasks': 1},
        {'name': 'High load', 'cpu_percent': 75, 'ram_percent': 60, 'pending_tasks': 5, 'need_income': True},
        {'name': 'Critical', 'cpu_percent': 92, 'ram_percent': 88, 'pending_tasks': 12, 'knowledge_gap': True, 'uncertainty': 0.8},
        {'name': 'Creative burst', 'cpu_percent': 45, 'ram_percent': 50, 'creative_demand': 0.9, 'pending_tasks': 2},
    ]
    
    for scenario in scenarios:
        print(f"\n--- Scenario: {scenario['name']} ---")
        tactician.update_environment(scenario)
        actions = tactician.tick()
        
        for action in actions:
            print(f"  [{action['agent']}] {action['action']} → {action['target']}")
        if not actions:
            print("  (no actions triggered)")
    
    print(f"\n✓ Nova Tactician operational — {len(tactician.agents)} agents coordinated")
    print(f"  Pattern: PlanLibraryEntry → evaluate → execute (Puon, 1997)")
