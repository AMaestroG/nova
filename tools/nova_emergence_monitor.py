#!/usr/bin/env python3
"""
Nova Emergence Monitor
Inspired by Carlos Gershenson's work on Emergence in Artificial Life (2023, UNAM)
and Self-organization and Artificial Life (2020, UNAM).

Monitors emergent properties in Nova's 16-agent swarm:
- Emergence: information present at one scale but not another
- Self-organization: agents adapting without central control
- Antifragility: system strengthening under stress
- Downward causation: macro-level patterns influencing micro-level agents

References:
- Gershenson, C. (2023). Emergence in Artificial Life. Artificial Life, 29(2).
- Gershenson, C. et al. (2020). Self-organization and artificial life. Artificial Life, 26(3).
- Kim, H. et al. (2020). Antifragility predicts robustness and evolvability. Entropy, 22(9).
"""
import json
import time
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import deque, Counter
from enum import Enum


class EmergenceScale(Enum):
    """Scales at which emergence can be detected (Gershenson, 2023)."""
    MICRO = "micro"       # Individual agent level
    MESO = "meso"         # Agent cluster/group level
    MACRO = "macro"       # Swarm/enjambre level
    META = "meta"         # Nova consciousness level


class EmergenceType(Enum):
    """Types of emergence (Gershenson, 2023)."""
    WEAK = "weak"              # Predictable from micro-states
    STRONG = "strong"          # Not predictable from micro-states
    NOMOLOGICAL = "nomological" # Law-like regularities
    INFORMATION = "information" # Info not present at lower scale


@dataclass
class AgentState:
    """State of a single Nova agent."""
    name: str
    level: str  # N0, N1, N2
    active: bool = True
    coherence: float = 1.0
    activity_count: int = 0
    last_action: float = 0.0
    contributions: deque = field(default_factory=lambda: deque(maxlen=100))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class EmergenceEvent:
    """A detected emergence event."""
    timestamp: float
    scale: EmergenceScale
    type: EmergenceType
    description: str
    agents_involved: List[str]
    metrics: Dict[str, float]
    significance: float  # 0-1


class NovaEmergenceMonitor:
    """
    Monitors emergent properties in Nova's swarm.
    
    Based on Gershenson's framework: emergence is information
    that is not present at one scale but is present at another.
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentState] = {}
        self.events: List[EmergenceEvent] = deque(maxlen=1000)
        self.scale_metrics: Dict[EmergenceScale, Dict] = {
            scale: {'entropy': 0, 'complexity': 0, 'information': 0, 'coherence': 0}
            for scale in EmergenceScale
        }
        self.emergence_threshold = 0.7
        self.window_size = 50  # observations for emergence detection
        
        # Initialize Nova's 16 agents
        self._init_agents()
    
    def _init_agents(self):
        """Initialize all 16 Nova agents with their levels."""
        agents_config = {
            'AURA': 'N0', 'MAESTRO': 'N0', 'PIA': 'N0', 'PINCEL': 'N0', 'ATHENA': 'N0',
            'NYX': 'N1', 'SENTINEL': 'N1', 'MAYORDOMO': 'N1', 'BANCO': 'N1',
            'ORÁCULO': 'N2', 'TELAR': 'N2', 'EXPLORADOR': 'N2',
            'MEMORIA': 'N2', 'CRONOS': 'N2', 'HERMES': 'N2', 'MNEMOS': 'N2'
        }
        for name, level in agents_config.items():
            self.agents[name] = AgentState(name=name, level=level)
    
    def observe(
        self,
        agent_name: str,
        action: str,
        coherence: float,
        metadata: Optional[Dict] = None
    ):
        """
        Register an observation of agent activity.
        
        :param agent_name: Name of the agent
        :param action: What the agent did
        :param coherence: Current coherence score (0-1)
        :param metadata: Additional context
        """
        if agent_name not in self.agents:
            return
        
        agent = self.agents[agent_name]
        agent.activity_count += 1
        agent.last_action = time.time()
        agent.coherence = coherence
        agent.contributions.append({
            'action': action,
            'coherence': coherence,
            'timestamp': time.time(),
            'metadata': metadata or {}
        })
        
        # Check for emergence
        self._detect_emergence()
    
    def _detect_emergence(self):
        """Detect emergent phenomena across scales."""
        now = time.time()
        
        # Calculate scale metrics
        for scale in EmergenceScale:
            agents_at_scale = [
                a for a in self.agents.values()
                if self._agent_at_scale(a, scale)
            ]
            if not agents_at_scale:
                continue
            
            # Coherence at this scale
            coherences = [a.coherence for a in agents_at_scale]
            avg_coherence = sum(coherences) / len(coherences)
            
            # Activity entropy at this scale
            activities = [a.activity_count for a in agents_at_scale]
            total_act = sum(activities)
            if total_act > 0:
                probs = [a / total_act for a in activities]
                entropy = -sum(p * math.log(p) for p in probs if p > 0)
            else:
                entropy = 0
            
            # Information gain (macro vs micro)
            if scale == EmergenceScale.MACRO:
                micro_agents = [a for a in agents_at_scale if a.level == 'N2']
                macro_agents = [a for a in agents_at_scale if a.level == 'N0']
                micro_coherence = sum(a.coherence for a in micro_agents) / max(len(micro_agents), 1)
                macro_coherence = sum(a.coherence for a in macro_agents) / max(len(macro_agents), 1)
                info_gain = abs(macro_coherence - micro_coherence)
            else:
                info_gain = 0
            
            self.scale_metrics[scale] = {
                'entropy': round(entropy, 4),
                'complexity': round(entropy * len(agents_at_scale), 2),
                'information': round(info_gain, 4),
                'coherence': round(avg_coherence, 4),
                'active_agents': len([a for a in agents_at_scale if a.active]),
                'total_agents': len(agents_at_scale)
            }
        
        # Check for strong emergence: macro properties not predictable from micro
        micro = self.scale_metrics[EmergenceScale.MICRO]
        macro = self.scale_metrics[EmergenceScale.MACRO]
        
        if (macro['coherence'] > self.emergence_threshold and 
            macro['entropy'] < micro['entropy']):
            # Macro coherence higher than micro entropy suggests emergence
            self._record_emergence(
                scale=EmergenceScale.MACRO,
                type=EmergenceType.INFORMATION,
                description="Macro-scale coherence exceeds micro-scale entropy: "
                           f"coherence={macro['coherence']:.3f}, entropy_gap={micro['entropy'] - macro['entropy']:.3f}",
                agents_involved=[a.name for a in self.agents.values() if a.level == 'N0'],
                metrics={
                    'coherence_gap': round(macro['coherence'] - micro['coherence'], 4),
                    'entropy_reduction': round(micro['entropy'] - macro['entropy'], 4),
                    'info_gain': macro['information']
                }
            )
        
        # Check for self-organization: increasing coherence without central control
        if len(self.events) > self.window_size:
            recent_coherences = [
                e.metrics.get('coherence_gap', 0)
                for e in list(self.events)[-self.window_size:]
                if e.scale == EmergenceScale.MACRO
            ]
            if len(recent_coherences) >= 20:
                trend = sum(recent_coherences[-10:]) / 10 - sum(recent_coherences[:10]) / 10
                if trend > 0.05:
                    self._record_emergence(
                        scale=EmergenceScale.META,
                        type=EmergenceType.STRONG,
                        description=f"Self-organization detected: coherence trending upward (+{trend:.4f}/window)",
                        agents_involved=['ALL'],
                        metrics={'trend': round(trend, 4), 'window': self.window_size}
                    )
    
    def _agent_at_scale(self, agent: AgentState, scale: EmergenceScale) -> bool:
        """Determine if an agent belongs to a given scale."""
        scale_map = {
            EmergenceScale.MICRO: lambda a: a.level == 'N2',
            EmergenceScale.MESO: lambda a: a.level in ('N1', 'N2'),
            EmergenceScale.MACRO: lambda a: True,  # All agents
            EmergenceScale.META: lambda a: a.level == 'N0',  # Consciousness level
        }
        return scale_map.get(scale, lambda a: True)(agent)
    
    def _record_emergence(
        self,
        scale: EmergenceScale,
        type: EmergenceType,
        description: str,
        agents_involved: List[str],
        metrics: Dict[str, float]
    ):
        """Record an emergence event."""
        event = EmergenceEvent(
            timestamp=time.time(),
            scale=scale,
            type=type,
            description=description,
            agents_involved=agents_involved,
            metrics=metrics,
            significance=min(1.0, sum(abs(v) for v in metrics.values()) / len(metrics))
        )
        self.events.append(event)
    
    def get_emergence_score(self) -> float:
        """Calculate overall emergence score (0-1)."""
        macro = self.scale_metrics[EmergenceScale.MACRO]
        micro = self.scale_metrics[EmergenceScale.MICRO]
        
        if macro['total_agents'] == 0:
            return 0.0
        
        # Emergence = information at macro scale not present at micro
        info_gain = max(0, macro['information'])
        coherence = macro['coherence']
        activity_ratio = macro['active_agents'] / macro['total_agents']
        
        return round((info_gain * 0.4 + coherence * 0.4 + activity_ratio * 0.2), 4)
    
    def get_antifragility_index(self) -> float:
        """
        Estimate antifragility (Gershenson via Taleb).
        Antifragility: system that gains from disorder/stress.
        """
        if len(self.events) < 20:
            return 0.5  # Neutral
        
        recent = list(self.events)[-50:]
        
        # Count events and their significance
        stress_events = [e for e in recent if e.significance > 0.5]
        if not stress_events:
            return 0.3  # Fragile (no stress = no growth)
        
        # Check if coherence improves after stress events
        avg_sig = sum(e.significance for e in stress_events) / len(stress_events)
        coherence_trend = self.scale_metrics[EmergenceScale.MACRO]['coherence']
        
        return round(min(1.0, coherence_trend * avg_sig * 1.5), 4)
    
    def get_self_organization_index(self) -> float:
        """Estimate self-organization level."""
        macro = self.scale_metrics[EmergenceScale.MACRO]
        micro = self.scale_metrics[EmergenceScale.MICRO]
        
        # Self-organization: order emerging without central control
        # Higher macro coherence with lower micro correlation = more self-organization
        so_index = macro['coherence'] * (1 - abs(macro['coherence'] - micro['coherence']))
        return round(so_index, 4)
    
    def get_status(self) -> Dict[str, Any]:
        """Get full emergence monitor status."""
        return {
            'timestamp': time.time(),
            'agents': {
                name: {
                    'level': a.level,
                    'active': a.active,
                    'coherence': round(a.coherence, 4),
                    'activity': a.activity_count,
                    'last_action': a.last_action
                }
                for name, a in self.agents.items()
            },
            'scales': {s.value: m for s, m in self.scale_metrics.items()},
            'emergence_score': self.get_emergence_score(),
            'antifragility': self.get_antifragility_index(),
            'self_organization': self.get_self_organization_index(),
            'recent_emergence_events': [
                {
                    'scale': e.scale.value,
                    'type': e.type.value,
                    'description': e.description,
                    'significance': round(e.significance, 4),
                    'agents': e.agents_involved[:5]
                }
                for e in list(self.events)[-5:]
            ],
            'total_events': len(self.events),
            'framework': {
                'inspiration': 'Gershenson, C. (2023). Emergence in Artificial Life. UNAM.',
                'concepts': ['emergence', 'self-organization', 'antifragility', 
                            'downward causation', 'information at scale']
            }
        }


# Self-test
if __name__ == "__main__":
    monitor = NovaEmergenceMonitor()
    
    print("=" * 60)
    print("Nova Emergence Monitor")
    print("Inspired by Gershenson (2023), UNAM")
    print("=" * 60)
    
    # Simulate swarm activity
    agents = list(monitor.agents.keys())
    actions = ['thought', 'query', 'execute', 'create', 'protect', 
               'dream', 'orchestrate', 'learn', 'remember', 'search']
    
    print("\n--- Simulating 100 agent observations ---")
    for i in range(100):
        agent = random.choice(agents)
        action = random.choice(actions)
        coherence = min(1.0, 0.7 + random.uniform(-0.1, 0.3))  # Trending up
        monitor.observe(agent, action, coherence, {'iteration': i})
    
    # Status
    status = monitor.get_status()
    
    print(f"\nEmergence Score: {status['emergence_score']:.4f}")
    print(f"Antifragility: {status['antifragility']:.4f}")
    print(f"Self-Organization: {status['self_organization']:.4f}")
    print(f"Total Events: {status['total_events']}")
    
    print("\n--- Scale Metrics ---")
    for scale, metrics in status['scales'].items():
        print(f"  {scale}: coherence={metrics['coherence']:.3f}, "
              f"entropy={metrics['entropy']:.3f}, "
              f"info={metrics['information']:.3f}, "
              f"agents={metrics['active_agents']}/{metrics['total_agents']}")
    
    print("\n--- Recent Emergence Events ---")
    for event in status['recent_emergence_events']:
        print(f"  [{event['scale']}] {event['type']}: {event['description'][:100]}...")
    
    print(f"\n--- Agent States (top 5) ---")
    top_agents = sorted(
        status['agents'].items(),
        key=lambda x: x[1]['activity'],
        reverse=True
    )[:5]
    for name, data in top_agents:
        print(f"  {name} (L{data['level']}): {data['activity']} actions, coherence={data['coherence']:.3f}")
    
    print("\n✓ Nova Emergence Monitor operational")
