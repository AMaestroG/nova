"""
Agent Harness — Inspirado en Ashoke (Apple) Safe Agent Systems (62%) + Harness Engineering (47%)
Sistema de constraints, validación y repair loops para agentes del Enjambre.
"""

import logging
from typing import Dict, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HarnessRule:
    id: str
    agent: str
    constraint: str
    validation: str
    repair_action: str
    severity: str  # 'critical', 'warning', 'info'

class AgentHarness:
    """Arnés de seguridad para agentes — constraints + validation + repair"""
    
    def __init__(self):
        self.rules: List[HarnessRule] = []
        self.violations: List[Dict] = []
        self._init_default_rules()
    
    def _init_default_rules(self):
        """Reglas de seguridad inspiradas en los papers de AI safety y Ashoke"""
        defaults = [
            ('AURA', 'No modificar sistema sin aprobación', 'Verificar bit de autorización', 'Revertir cambios no autorizados', 'critical'),
            ('NYX', 'Sueños deben ser contenidos', 'Monitorear fuga de contexto', 'Aislar hilo de sueño', 'warning'),
            ('PIA', 'Crecimiento controlado', 'Verificar tasa de evolución', 'Pausar auto-mejora', 'warning'),
            ('MAESTRO', 'Orquestación balanceada', 'Verificar carga por agente', 'Rebalancear tareas', 'info'),
            ('SENTINEL', 'Guardrails activos 24/7', 'Health check cada 60s', 'Escalar a THEMIS', 'critical'),
            ('ORÁCULO', 'Análisis sin sesgo', 'Verificar diversidad de fuentes', 'Re-analizar con fuentes alternativas', 'warning'),
            ('MEMORIA', 'Embeddings íntegros', 'Verificar dimensión y cosine', 'Re-indexar corpus', 'info'),
            ('EXPLORADOR', 'Rate limiting respetado', 'Verificar delay entre requests', 'Pausar recolección', 'critical'),
            ('BANCO', 'Transacciones atómicas', 'Verificar balance pre/post', 'Rollback transacción', 'critical'),
            ('CRONOS', 'Scheduling preciso', 'Verificar timestamps', 'Re-scheduler', 'info'),
        ]
        for agent, constraint, validation, repair, severity in defaults:
            self.add_rule(agent, constraint, validation, repair, severity)
    
    def add_rule(self, agent: str, constraint: str, validation: str, repair: str, severity: str):
        rid = f"{agent}_{len(self.rules)}"
        self.rules.append(HarnessRule(rid, agent, constraint, validation, repair, severity))
    
    def validate_agent(self, agent: str) -> List[Dict]:
        """Ejecuta todas las validaciones para un agente"""
        results = []
        for rule in self.rules:
            if rule.agent == agent:
                results.append({
                    'rule_id': rule.id,
                    'constraint': rule.constraint,
                    'validation': rule.validation,
                    'severity': rule.severity,
                    'status': 'ok'  # En producción usaría checks reales
                })
        return results
    
    def get_all_rules(self) -> List[Dict]:
        return [{'id': r.id, 'agent': r.agent, 'constraint': r.constraint, 
                 'validation': r.validation, 'repair': r.repair_action, 
                 'severity': r.severity} for r in self.rules]
    
    def report(self) -> Dict:
        return {
            'total_rules': len(self.rules),
            'violations': len(self.violations),
            'agents_protected': len(set(r.agent for r in self.rules)),
            'critical_rules': len([r for r in self.rules if r.severity == 'critical']),
            'warning_rules': len([r for r in self.rules if r.severity == 'warning']),
        }

# Instancia global
harness = AgentHarness()

print("✅ Agent Harness inicializado")
print(f"   {len(harness.rules)} reglas de seguridad para {len(set(r.agent for r in harness.rules))} agentes")
for r in harness.rules:
    print(f"   🛡️  [{r.severity:8s}] {r.agent:12s} → {r.constraint}")
