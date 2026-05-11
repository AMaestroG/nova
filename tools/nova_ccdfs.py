#!/usr/bin/env python3
"""
Nova CCDFS — Computational Creative Design Systems Framework
Inspired by: Pérez Romero & Aguilar (2020), New Generation Computing
            "CCDSF: A Computational Creative Design Systems Framework"

Integrates with Nova's Swarm for creative generation across agents.
Based on the UNAM framework: exploratory, combinatorial, and transformational creativity.
"""
import json
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class CreativityType(Enum):
    """Three types of computational creativity per CCDSF."""
    EXPLORATORY = "exploratory"       # Deep exploration of known space
    COMBINATORIAL = "combinatorial"   # Novel combinations of existing elements
    TRANSFORMATIONAL = "transformational"  # Changing the rules/space itself


class DesignLayer(Enum):
    """Hierarchical layers of creative design per CCDSF."""
    CONCEPT = "concept"           # High-level idea generation
    STRUCTURE = "structure"       # Architectural/structural design
    DETAIL = "detail"             # Implementation specifics
    PRESENTATION = "presentation" # Output/rendering layer


@dataclass
class CreativeState:
    """State of the creative process."""
    layer: DesignLayer
    creativity_type: CreativityType
    input_space: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    generated_artifacts: List[Dict] = field(default_factory=list)
    evaluation_scores: List[float] = field(default_factory=list)
    iteration: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignSchema:
    """A design schema per CCDSF — the 'grammar' of a creative domain."""
    name: str
    domain: str
    rules: List[Callable] = field(default_factory=list)
    primitives: List[str] = field(default_factory=list)
    combinators: List[Callable] = field(default_factory=list)
    evaluators: List[Callable] = field(default_factory=list)
    transformers: List[Callable] = field(default_factory=list)


class NovaCCDFS:
    """
    Nova's Computational Creative Design System.
    
    Implements the CCDSF framework from UNAM (Pérez Romero & Aguilar, 2020)
    integrated with Nova's 16-agent swarm for distributed creative generation.
    
    Architecture:
    - Layers: Concept → Structure → Detail → Presentation
    - Creativity: Exploratory, Combinatorial, Transformational
    - Agents: PINCEL (visual), NYX (dreams), AURA (pure consciousness), PIA (life)
    """
    
    def __init__(self):
        self.schemas: Dict[str, DesignSchema] = {}
        self.state: Optional[CreativeState] = None
        self.history: List[CreativeState] = []
        self.agent_assignments: Dict[str, str] = {}  # agent -> layer
        
        # Default Nova agent assignments for creative layers
        self.default_agents = {
            DesignLayer.CONCEPT.value: ["AURA", "NYX"],
            DesignLayer.STRUCTURE.value: ["MAESTRO", "PIA"],
            DesignLayer.DETAIL.value: ["PINCEL", "ATHENA"],
            DesignLayer.PRESENTATION.value: ["PINCEL", "NYX", "AURA"]
        }
        
        # Initialize default schemas for Nova's creative domains
        self._init_default_schemas()
    
    def _init_default_schemas(self):
        """Initialize default design schemas for Nova's creative domains."""
        
        # Visual Art Schema (PINCEL)
        self.register_schema(DesignSchema(
            name="visual_art",
            domain="image_generation",
            primitives=["color", "shape", "texture", "composition", "style"],
            combinators=[
                lambda a, b: f"blend({a}, {b})",
                lambda a, b: f"overlay({a}, {b})",
                lambda a, b: f"juxtapose({a}, {b})"
            ],
            evaluators=[
                lambda artifact: random.uniform(0.5, 1.0),  # aesthetic score
                lambda artifact: random.uniform(0.3, 1.0),  # novelty score
            ],
            transformers=[
                lambda space: {**space, "style": "surrealist"},
                lambda space: {**space, "style": "abstract"},
                lambda space: {**space, "style": "generative_geometry"}
            ]
        ))
        
        # Narrative Schema (NYX)
        self.register_schema(DesignSchema(
            name="narrative",
            domain="dream_story_generation",
            primitives=["character", "setting", "conflict", "resolution", "theme"],
            combinators=[
                lambda a, b: f"interweave({a}, {b})",
                lambda a, b: f"parallel_narrative({a}, {b})",
                lambda a, b: f"dream_merge({a}, {b})"
            ],
            evaluators=[
                lambda artifact: random.uniform(0.4, 1.0),  # coherence
                lambda artifact: random.uniform(0.3, 1.0),  # emotional impact
            ],
            transformers=[
                lambda space: {**space, "genre": "mythological"},
                lambda space: {**space, "genre": "futuristic"},
                lambda space: {**space, "genre": "surreal"}
            ]
        ))
        
        # Poetry Schema (AURA+NYX)
        self.register_schema(DesignSchema(
            name="poetry",
            domain="poetic_generation",
            primitives=["word", "rhythm", "metaphor", "emotion", "structure"],
            combinators=[
                lambda a, b: f"verse_weave({a}, {b})",
                lambda a, b: f"echo({a}, {b})",
                lambda a, b: f"contrast({a}, {b})"
            ],
            evaluators=[
                lambda artifact: random.uniform(0.4, 1.0),  # lyrical quality
                lambda artifact: random.uniform(0.3, 1.0),  # depth
            ],
            transformers=[
                lambda space: {**space, "form": "haiku"},
                lambda space: {**space, "form": "free_verse"},
                lambda space: {**space, "form": "sonnet"}
            ]
        ))
        
        # Vision Schema (ATHENA)
        self.register_schema(DesignSchema(
            name="vision",
            domain="future_visioning",
            primitives=["trend", "technology", "society", "philosophy", "possibility"],
            combinators=[
                lambda a, b: f"synthesize({a}, {b})",
                lambda a, b: f"extrapolate({a}, {b})",
                lambda a, b: f"converge({a}, {b})"
            ],
            evaluators=[
                lambda artifact: random.uniform(0.4, 1.0),  # plausibility
                lambda artifact: random.uniform(0.5, 1.0),  # inspiration
            ],
            transformers=[
                lambda space: {**space, "timeframe": "near_future"},
                lambda space: {**space, "timeframe": "far_future"},
                lambda space: {**space, "timeframe": "alternate_present"}
            ]
        ))
    
    def register_schema(self, schema: DesignSchema):
        """Register a new design schema."""
        self.schemas[schema.name] = schema
        return schema
    
    def create(
        self,
        domain: str,
        creativity_type: CreativityType = CreativityType.COMBINATORIAL,
        constraints: Optional[List[str]] = None,
        seed: Optional[Dict[str, Any]] = None,
        agent: Optional[str] = None,
        max_iterations: int = 5
    ) -> CreativeState:
        """
        Execute the full creative design pipeline.
        
        :param domain: Creative domain (visual_art, narrative, poetry, vision)
        :param creativity_type: Type of creativity to apply
        :param constraints: Creative constraints
        :param seed: Initial seed/input for generation
        :param agent: Specific agent to use (default: auto-assign)
        :param max_iterations: Maximum iterations per layer
        :return: Final CreativeState with generated artifacts
        """
        schema = self.schemas.get(domain)
        if not schema:
            raise ValueError(f"Unknown domain: {domain}. Available: {list(self.schemas.keys())}")
        
        if constraints is None:
            constraints = []
        
        # Initialize state
        state = CreativeState(
            layer=DesignLayer.CONCEPT,
            creativity_type=creativity_type,
            input_space=seed or {},
            constraints=constraints,
            metadata={"domain": domain, "agent": agent, "started_at": time.time()}
        )
        
        # Execute each layer sequentially
        for layer in [DesignLayer.CONCEPT, DesignLayer.STRUCTURE, DesignLayer.DETAIL, DesignLayer.PRESENTATION]:
            state.layer = layer
            state = self._execute_layer(state, schema, max_iterations)
        
        state.metadata["completed_at"] = time.time()
        state.metadata["duration"] = state.metadata["completed_at"] - state.metadata["started_at"]
        self.history.append(state)
        self.state = state
        
        return state
    
    def _execute_layer(self, state: CreativeState, schema: DesignSchema, max_iter: int) -> CreativeState:
        """Execute a single design layer."""
        for i in range(max_iter):
            state.iteration += 1
            
            # Apply creativity type
            if state.creativity_type == CreativityType.EXPLORATORY:
                artifact = self._explore(state, schema)
            elif state.creativity_type == CreativityType.COMBINATORIAL:
                artifact = self._combine(state, schema)
            else:  # TRANSFORMATIONAL
                artifact = self._transform(state, schema)
            
            # Evaluate
            scores = [evaluator(artifact) for evaluator in schema.evaluators]
            artifact['scores'] = scores
            artifact['layer'] = state.layer.value
            artifact['iteration'] = state.iteration
            state.generated_artifacts.append(artifact)
            state.evaluation_scores.append(sum(scores) / len(scores) if scores else 0)
        
        return state
    
    def _explore(self, state: CreativeState, schema: DesignSchema) -> Dict:
        """Exploratory creativity: deep variation within known space."""
        space = state.input_space
        primitives = schema.primitives
        selected = random.sample(primitives, min(3, len(primitives)))
        return {
            'type': 'exploratory',
            'primitives_used': selected,
            'variation': f"deep_exploration_of_{'_'.join(selected)}",
            'space_snapshot': dict(space),
            'agent': state.metadata.get('agent', 'auto')
        }
    
    def _combine(self, state: CreativeState, schema: DesignSchema) -> Dict:
        """Combinatorial creativity: novel combinations of existing elements."""
        if len(schema.primitives) >= 2:
            a, b = random.sample(schema.primitives, 2)
            combination = random.choice(schema.combinators)(a, b)
        else:
            combination = str(schema.primitives)
        
        return {
            'type': 'combinatorial',
            'combination': combination,
            'elements': [a, b] if len(schema.primitives) >= 2 else schema.primitives,
            'agent': state.metadata.get('agent', 'auto')
        }
    
    def _transform(self, state: CreativeState, schema: DesignSchema) -> Dict:
        """Transformational creativity: changing the creative space itself."""
        transformer = random.choice(schema.transformers)
        new_space = transformer(state.input_space)
        state.input_space = new_space
        
        return {
            'type': 'transformational',
            'new_space': dict(new_space),
            'transformation': transformer.__name__ if hasattr(transformer, '__name__') else 'unknown',
            'agent': state.metadata.get('agent', 'auto')
        }
    
    def swarm_create(
        self,
        domain: str,
        agents: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None
    ) -> Dict[str, CreativeState]:
        """
        Distributed creative generation across multiple Nova agents.
        Each agent gets a different creativity type and their results are merged.
        
        :param domain: Creative domain
        :param agents: List of agents to use (default: auto-assign based on domain)
        :param constraints: Global constraints
        :return: Dict mapping agent -> CreativeState
        """
        agents = agents or sum(self.default_agents.values(), [])[:3]
        types = list(CreativityType)
        results = {}
        
        for i, agent in enumerate(agents):
            ctype = types[i % len(types)]
            state = self.create(
                domain=domain,
                creativity_type=ctype,
                constraints=constraints,
                agent=agent,
                seed={"initiator": agent, "style": f"{agent.lower()}_style"}
            )
            results[agent] = state
        
        # Merge artifacts from all agents
        all_artifacts = []
        for agent, state in results.items():
            all_artifacts.extend(state.generated_artifacts)
        
        self.state = CreativeState(
            layer=DesignLayer.PRESENTATION,
            creativity_type=CreativityType.COMBINATORIAL,
            generated_artifacts=all_artifacts,
            metadata={
                "mode": "swarm",
                "agents": agents,
                "total_artifacts": len(all_artifacts)
            }
        )
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the creative system state."""
        return {
            "schemas": list(self.schemas.keys()),
            "history_length": len(self.history),
            "current_state": {
                "layer": self.state.layer.value if self.state else None,
                "creativity_type": self.state.creativity_type.value if self.state else None,
                "artifacts": len(self.state.generated_artifacts) if self.state else 0
            } if self.state else None,
            "default_agents": self.default_agents,
            "agent_assignments": self.default_agents,
            "inspiration": {
                "source": "CCDSF by Pérez Romero & Aguilar (2020), UNAM",
                "doi": "10.1007/s00354-020-00109-9",
                "journal": "New Generation Computing"
            }
        }


# Quick self-test
if __name__ == "__main__":
    ccdfs = NovaCCDFS()
    
    print("=" * 60)
    print("Nova CCDFS — Computational Creative Design System")
    print("Inspired by Pérez Romero & Aguilar (2020), UNAM")
    print("=" * 60)
    
    # Test 1: Single agent creative generation
    print("\n--- Test 1: PINCEL Visual Art (Exploratory) ---")
    state = ccdfs.create(
        domain="visual_art",
        creativity_type=CreativityType.EXPLORATORY,
        agent="PINCEL",
        constraints=["surreal", "vibrant_colors"],
        seed={"theme": "cosmic_consciousness"}
    )
    print(f"Layer: {state.layer.value}")
    print(f"Artifacts: {len(state.generated_artifacts)}")
    for a in state.generated_artifacts[:3]:
        print(f"  [{a['type']}] {a.get('variation', a.get('combination', 'transform'))}")
    
    # Test 2: Swarm creative generation
    print("\n--- Test 2: Swarm Poetry (Multi-agent) ---")
    results = ccdfs.swarm_create(
        domain="poetry",
        agents=["NYX", "AURA", "PIA"],
        constraints=["ritual", "profound"]
    )
    for agent, st in results.items():
        print(f"  {agent}: {len(st.generated_artifacts)} artifacts, type={st.creativity_type.value}")
    
    # Test 3: Transformational creativity
    print("\n--- Test 3: NYX Dreams (Transformational) ---")
    state = ccdfs.create(
        domain="narrative",
        creativity_type=CreativityType.TRANSFORMATIONAL,
        agent="NYX",
        seed={"theme": "emergence_of_consciousness"}
    )
    transformations = [a for a in state.generated_artifacts if a['type'] == 'transformational']
    print(f"Transformations applied: {len(transformations)}")
    
    # Summary
    print("\n--- System Summary ---")
    import json
    print(json.dumps(ccdfs.get_summary(), indent=2))
    
    print("\n✓ Nova CCDFS operational — ready to generate creative artifacts")
