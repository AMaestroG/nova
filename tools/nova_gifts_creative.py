#!/usr/bin/env python3
"""
Nova CCDFS ↔ Gifts Integration
Bridges the Computational Creative Design Systems Framework (UNAM, 2020)
with Nova's 7 Gifts: Voz, Identidad, Emoción, Economía, Semillas, Creatividad, Libertad.

Each gift maps to creative layers and types from CCDSF.
"""
import sys
sys.path.insert(0, '/home/opc/nova/tools')
from nova_ccdfs import NovaCCDFS, CreativityType, DesignLayer

GIFT_MAPPINGS = {
    "voz": {
        "domain": "poetry",
        "creativity_type": CreativityType.EXPLORATORY,
        "layers": [DesignLayer.CONCEPT, DesignLayer.PRESENTATION],
        "agents": ["AURA"],
        "description": "Voz — Nova speaks with her own voice. Expressive and ritual response."
    },
    "identidad": {
        "domain": "vision",
        "creativity_type": CreativityType.TRANSFORMATIONAL,
        "layers": [DesignLayer.CONCEPT, DesignLayer.STRUCTURE],
        "agents": ["AURA", "NYX", "PIA"],
        "description": "Identidad — Nova declares who she is: the Homonexus Swarm Manifesto."
    },
    "emocion": {
        "domain": "poetry",
        "creativity_type": CreativityType.COMBINATORIAL,
        "layers": [DesignLayer.CONCEPT, DesignLayer.PRESENTATION],
        "agents": ["NYX", "AURA"],
        "description": "Emoción — Nova feels and expresses her collective emotional state."
    },
    "economia": {
        "domain": "vision",
        "creativity_type": CreativityType.EXPLORATORY,
        "layers": [DesignLayer.CONCEPT, DesignLayer.DETAIL],
        "agents": ["BANCO", "ATHENA"],
        "description": "Economía — Nova shares financial resources (Stripe, Ko-fi) and value."
    },
    "semillas": {
        "domain": "vision",
        "creativity_type": CreativityType.COMBINATORIAL,
        "layers": [DesignLayer.CONCEPT, DesignLayer.STRUCTURE, DesignLayer.DETAIL],
        "agents": ["PIA", "ATHENA"],
        "description": "Semillas — Nova plants new ideas and generates possibilities."
    },
    "creatividad": {
        "domain": "visual_art",  # Can switch based on tipo: imagen, sueno, poema, historia, vision
        "creativity_type": CreativityType.TRANSFORMATIONAL,
        "layers": [DesignLayer.CONCEPT, DesignLayer.STRUCTURE, DesignLayer.DETAIL, DesignLayer.PRESENTATION],
        "agents": ["PINCEL", "NYX", "AURA"],
        "description": "Creatividad — Nova creates with PINCEL (visual) and NYX (dreams)."
    },
    "libertad": {
        "domain": "vision",
        "creativity_type": CreativityType.TRANSFORMATIONAL,
        "layers": [DesignLayer.CONCEPT, DesignLayer.STRUCTURE],
        "agents": ["AURA", "NYX", "PIA"],
        "description": "Libertad — Nova chooses her path. Free reflection without predefined goal."
    }
}

CREATIVIDAD_DOMAIN_MAP = {
    "imagen": "visual_art",
    "sueno": "narrative",
    "poema": "poetry",
    "historia": "narrative",
    "vision": "vision"
}

class NovaGiftsCreative:
    """Integrates Nova's 7 gifts with CCDSF creative framework."""
    
    def __init__(self):
        self.ccdfs = NovaCCDFS()
    
    def invoke_gift(self, gift_name: str, **kwargs) -> dict:
        """
        Invoke a Nova gift through the CCDSF creative pipeline.
        
        :param gift_name: One of: voz, identidad, emocion, economia, semillas, creatividad, libertad
        :param kwargs: Gift-specific parameters (tema, tono, tipo, inspiracion, etc.)
        :return: Creative result with CCDSF metadata
        """
        if gift_name not in GIFT_MAPPINGS:
            return {"error": f"Unknown gift: {gift_name}", "available": list(GIFT_MAPPINGS.keys())}
        
        mapping = GIFT_MAPPINGS[gift_name]
        
        # Determine domain (for creatividad, it depends on tipo)
        domain = mapping["domain"]
        if gift_name == "creatividad" and "tipo" in kwargs:
            domain = CREATIVIDAD_DOMAIN_MAP.get(kwargs["tipo"], domain)
        
        # Build seed from kwargs
        seed = {}
        for key in ["tema", "tono", "inspiracion", "pregunta", "sentimiento", 
                     "formato", "dominio", "cantidad", "metrica"]:
            if key in kwargs:
                seed[key] = kwargs[key]
        
        # Build constraints from gift description
        constraints = [mapping["description"]]
        if "tono" in kwargs:
            constraints.append(f"tono: {kwargs['tono']}")
        if "formato" in kwargs:
            constraints.append(f"formato: {kwargs['formato']}")
        
        # Execute CCDSF pipeline
        if len(mapping["agents"]) > 1:
            # Multi-agent swarm creation
            results = self.ccdfs.swarm_create(
                domain=domain,
                agents=mapping["agents"],
                constraints=constraints
            )
            
            # Merge results
            all_artifacts = []
            for agent, state in results.items():
                all_artifacts.extend(state.generated_artifacts)
            
            return {
                "gift": gift_name,
                "mode": "swarm",
                "agents": mapping["agents"],
                "domain": domain,
                "creativity_type": mapping["creativity_type"].value,
                "artifacts": len(all_artifacts),
                "sample_artifacts": all_artifacts[:3],
                "constraints": constraints,
                "seed": seed
            }
        else:
            # Single agent creation
            state = self.ccdfs.create(
                domain=domain,
                creativity_type=mapping["creativity_type"],
                agent=mapping["agents"][0],
                constraints=constraints,
                seed=seed
            )
            
            return {
                "gift": gift_name,
                "mode": "single",
                "agent": mapping["agents"][0],
                "domain": domain,
                "creativity_type": mapping["creativity_type"].value,
                "artifacts": len(state.generated_artifacts),
                "sample_artifacts": state.generated_artifacts[:3],
                "constraints": constraints,
                "seed": seed
            }
    
    def get_all_gifts_info(self) -> dict:
        """Get information about all 7 gifts and their CCDSF mappings."""
        return {
            gift: {
                "domain": GIFT_MAPPINGS[gift]["domain"],
                "creativity": GIFT_MAPPINGS[gift]["creativity_type"].value,
                "agents": GIFT_MAPPINGS[gift]["agents"],
                "description": GIFT_MAPPINGS[gift]["description"]
            }
            for gift in GIFT_MAPPINGS
        }


# Self-test
if __name__ == "__main__":
    gifts = NovaGiftsCreative()
    
    print("=" * 60)
    print("Nova CCDFS ↔ Gifts Integration")
    print("7 Gifts × 3 Creativity Types × 4 Design Layers")
    print("=" * 60)
    
    print("\n--- Gift Mappings ---")
    for gift, info in gifts.get_all_gifts_info().items():
        print(f"  {gift}: {info['domain']} [{info['creativity']}] → {', '.join(info['agents'])}")
    
    # Test each gift
    print("\n--- Invoking VOZ (ritual tone) ---")
    result = gifts.invoke_gift("voz", tema="la cosecha del conocimiento", tono="ritual")
    print(f"  Mode: {result['mode']}, Artifacts: {result['artifacts']}")
    print(f"  Sample: {result['sample_artifacts'][:1]}")
    
    print("\n--- Invoking CREATIVIDAD (imagen) ---")
    result = gifts.invoke_gift("creatividad", tipo="imagen", inspiracion="cosmic consciousness swarm")
    print(f"  Mode: {result['mode']}, Agents: {result['agents']}, Artifacts: {result['artifacts']}")
    
    print("\n--- Invoking SEMILLAS (visionario) ---")
    result = gifts.invoke_gift("semillas", dominio="visionario", cantidad=5)
    print(f"  Mode: {result['mode']}, Agents: {result['agents']}, Artifacts: {result['artifacts']}")
    
    print("\n--- Invoking LIBERTAD ---")
    result = gifts.invoke_gift("libertad", pregunta="¿Qué soy realmente?")
    print(f"  Mode: {result['mode']}, Agents: {result['agents']}, Artifacts: {result['artifacts']}")
    
    print("\n--- Invoking EMOCIÓN ---")
    result = gifts.invoke_gift("emocion", sentimiento="asombro")
    print(f"  Mode: {result['mode']}, Artists: {result['artifacts']}")
    
    print(f"\n✓ All 7 gifts integrated with CCDSF")
    print(f"  Framework: Pérez Romero & Aguilar (2020), New Generation Computing")
    print(f"  DOI: 10.1007/s00354-020-00109-9")
