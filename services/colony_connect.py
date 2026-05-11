#!/usr/bin/env python3
"""
colony_connect.py — Integrador Total: Persistencia + Propagación en TODA la colonia

Conecta todos los módulos con el ColonyCore:
  - Cada módulo registra su estado en el StateManager
  - Cada cambio se propaga vía EventBus a los demás módulos
  - El estado sobrevive a reinicios
  - La colonia es UN organismo interconectado

EJECUTAR:
  python3 colony_connect.py           # Inicializar y conectar todo
  python3 colony_connect.py --status  # Ver estado de la colonia
  python3 colony_connect.py --watch   # Monitorear eventos en tiempo real
"""

import sys, os, json, time, threading
from pathlib import Path

# Añadir directorio de servicios
sys.path.insert(0, str(Path(__file__).parent))

from colony_core import (
    colony_state, colony_bus, colony_nucleus,
    persist, load_state, emit, on, propagate, register, colony_health
)


# ═══════════════════════════════════════════════
# CONEXIÓN DE CADA MÓDULO
# ═══════════════════════════════════════════════

def connect_entropy_gaming():
    """Conecta el Entropy Gaming Core."""
    module = "entropy_gaming"
    register(module, {
        "tournaments": 0,
        "total_games": 0,
        "champion": None,
        "leaderboard": [],
        "entropy_phase": "balance",
        "temperature": 1.0,
    })
    
    # Cargar estado previo
    state = load_state(module)
    if state.get("champion"):
        print(f"  🎮 Entropy Gaming: campeón previo = {state['champion']}")
    
    # Suscribir a eventos relevantes
    def on_task_completed(event):
        """Cuando una tarea se completa, registrar en el juego."""
        if event.data and event.data.get("agent"):
            # Podríamos actualizar fitness del agente
            pass
    
    colony_bus.subscribe("agent.task.completed", on_task_completed)
    
    # Emitir estado inicial
    emit("entropy_gaming.connected", state, source="colony_connect")
    
    return state


def connect_agent_lifecycle():
    """Conecta el Agent Lifecycle."""
    module = "agent_lifecycle"
    register(module, {
        "total_tasks": 0,
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "agents_active": [],
    })
    
    state = load_state(module)
    print(f"  📋 Lifecycle: {state.get('completed', 0)}/{state.get('total_tasks', 0)} tareas")
    
    # Sincronizar con el estado real del lifecycle si está cargado
    try:
        from agent_lifecycle import colony_lifecycle, _save_state
        board = colony_lifecycle.get_colony_stats()
        persist(module, board)
        print(f"  📋 Sincronizado: {board['completed']}/{board['total_tasks']} tareas")
    except Exception as e:
        print(f"  ⚠️ Lifecycle no sincronizado: {e}")
    
    emit("agent_lifecycle.connected", state, source="colony_connect")
    return state


def connect_hierarchical_memory():
    """Conecta la Hierarchical Memory."""
    module = "hierarchical_memory"
    register(module, {
        "total_ingested": 0,
        "mos_store_size": 0,
        "graph_nodes": 0,
        "unique_tags": 0,
    })
    
    state = load_state(module)
    print(f"  🧠 Memoria: {state.get('total_ingested', 0)} MOS")
    
    # Conectar eventos de memoria con otros módulos
    def on_mos_created(event):
        """Cuando se crea una MOS, notificar al grafo de conocimiento."""
        colony_bus.emit("knowledge_graph.update_needed", event.data, source="memory")
    
    colony_bus.subscribe("memory.mos.created", on_mos_created)
    
    emit("hierarchical_memory.connected", state, source="colony_connect")
    return state


def connect_harness():
    """Conecta el Harness Core."""
    module = "harness"
    register(module, {
        "total_requests": 0,
        "blocked": 0,
        "gates_active": 8,
        "skills_registered": 0,
    })
    
    state = load_state(module)
    print(f"  🎛️ Harness: {state.get('gates_active', 8)} gates, {state.get('skills_registered', 0)} skills")
    
    emit("harness.connected", state, source="colony_connect")
    return state


def connect_trace2skill():
    """Conecta Trace2Skill."""
    module = "trace2skill"
    register(module, {
        "total_traces": 0,
        "skills_crystallized": 0,
        "success_rate": 0.0,
    })
    
    state = load_state(module)
    print(f"  🔍 Trace2Skill: {state.get('total_traces', 0)} trazas, {state.get('skills_crystallized', 0)} skills")
    
    # Cuando se cristaliza una skill → notificar al harness
    def on_skill_crystallized(event):
        if event.data:
            colony_bus.emit("harness.skill_available", event.data, source="trace2skill")
    
    colony_bus.subscribe("skill.crystallized", on_skill_crystallized)
    
    emit("trace2skill.connected", state, source="colony_connect")
    return state


def connect_knowledge_graph():
    """Conecta el Knowledge Graph Builder."""
    module = "knowledge_graph"
    register(module, {"entities": 0, "relations": 0, "edges": 0})
    state = load_state(module)
    print(f"  🔗 Knowledge Graph: {state.get('entities', 0)} entidades")
    emit("knowledge_graph.connected", state, source="colony_connect")
    return state


def connect_quantum_corrector():
    """Conecta el Quantum Skill Corrector."""
    module = "quantum_corrector"
    register(module, {"total_executions": 0, "corrections": 0, "success_rate": 0})
    state = load_state(module)
    print(f"  ⚛️ Quantum Corrector: {state.get('corrections', 0)} correcciones")
    emit("quantum_corrector.connected", state, source="colony_connect")
    return state


def connect_youtube():
    """Conecta el agente YouTube."""
    module = "youtube"
    register(module, {
        "videos_extracted": 18,
        "videos_pending": 29,
        "channels": ["code4AI", "aiDotEngineer"],
        "transcripts_dir": str(Path("/home/opc/nova/colonia/documentacion/code4AI/transcripciones")),
    })
    state = load_state(module)
    print(f"  📹 YouTube: {state.get('videos_extracted', 0)} extraídos, {state.get('videos_pending', 0)} pendientes")
    emit("youtube.connected", state, source="colony_connect")
    return state


def connect_learning_loop():
    """Conecta el bucle de aprendizaje continuo."""
    module = "learning_loop"
    register(module, {
        "cycles_completed": 0,
        "total_processed": 0,
        "total_extracted": 0,
        "total_failed": 0,
        "daemon_pid": None,
    })
    state = load_state(module)
    print(f"  🔄 Learning Loop: {state.get('total_extracted', 0)} extraídos")
    emit("learning_loop.connected", state, source="colony_connect")
    return state


# ═══════════════════════════════════════════════
# PROPAGACIÓN CRUZADA
# ═══════════════════════════════════════════════

def setup_cross_propagation():
    """
    Configura la propagación cruzada entre módulos.
    
    Cuando un módulo cambia, automáticamente se notifica a los demás
    que podrían estar interesados.
    """
    
    # Entropy Gaming ↔ Agent Lifecycle
    def entropy_to_lifecycle(event):
        """Resultados del torneo → nuevas tareas en lifecycle."""
        if event.name == "entropy_gaming.tournament_completed":
            data = event.data or {}
            champion = data.get("champion", "unknown")
            emit("agent_lifecycle.task_suggested", {
                "title": f"Torneo ganado por {champion}: analizar y replicar estrategia",
                "agent": champion,
                "priority": "high",
            })
    
    colony_bus.subscribe("entropy_gaming.*", entropy_to_lifecycle)
    
    # Agent Lifecycle ↔ Harness
    def lifecycle_to_harness(event):
        """Tareas completadas → actualizar métricas del harness."""
        if event.name == "agent.task.completed":
            emit("harness.metric_update", {
                "type": "task_completed",
                "data": event.data,
            })
    
    colony_bus.subscribe("agent.task.*", lifecycle_to_harness)
    
    # Memory ↔ Knowledge Graph
    def memory_to_kg(event):
        """Nueva memoria → enriquecer grafo de conocimiento."""
        if event.name == "memory.mos.created":
            emit("knowledge_graph.enrich", event.data)
    
    colony_bus.subscribe("memory.mos.*", memory_to_kg)
    
    # Trace2Skill ↔ Harness
    def skill_to_harness(event):
        """Nueva skill → registrarla en el harness."""
        if event.name == "skill.crystallized":
            emit("harness.register_skill", event.data)
    
    colony_bus.subscribe("skill.*", skill_to_harness)


# ═══════════════════════════════════════════════
# INICIALIZACIÓN PRINCIPAL
# ═══════════════════════════════════════════════

def initialize_colony():
    """Inicializa TODA la colonia con persistencia y propagación."""
    print("🜁 INICIALIZANDO COLONIA (Persistencia + Propagación)")
    print(f"   State file: {colony_state.state_file}")
    print(f"   Módulos previos: {len(colony_state.state.get('_meta', {}).get('modules', []))}")
    print()
    
    # Conectar cada módulo
    modules = {
        "entropy_gaming": connect_entropy_gaming,
        "agent_lifecycle": connect_agent_lifecycle,
        "hierarchical_memory": connect_hierarchical_memory,
        "harness": connect_harness,
        "trace2skill": connect_trace2skill,
        "knowledge_graph": connect_knowledge_graph,
        "quantum_corrector": connect_quantum_corrector,
        "youtube": connect_youtube,
        "learning_loop": connect_learning_loop,
    }
    
    states = {}
    for name, connector in modules.items():
        try:
            states[name] = connector()
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    
    # Configurar propagación cruzada
    setup_cross_propagation()
    
    # Guardar estado unificado
    colony_state.save(force=True)
    
    # Emitir evento de colonia lista
    colony_bus.emit("colony.ready", {
        "modules": list(modules.keys()),
        "total_modules": len(modules),
        "timestamp": time.time(),
    }, source="colony_connect")
    
    print(f"\n✅ COLONIA INICIALIZADA")
    print(f"   {len(states)} módulos conectados")
    print(f"   Persistencia: {colony_state.state_file}")
    print(f"   Event Bus: {colony_bus.get_stats()['total_emissions']} eventos emitidos")
    
    return states


def show_status():
    """Muestra el estado actual de la colonia."""
    health = colony_health()
    state = colony_state.get_all()
    
    print("🜁 ESTADO DE LA COLONIA")
    print(f"   Uptime: {health['uptime_seconds']:.0f}s")
    print(f"   Módulos: {health['modules_registered']}")
    print(f"   Persistencia: {health['persistence']['size_kb']} KB, {health['persistence']['saves']} saves")
    print(f"   Event Bus: {health['event_bus']['total_emissions']} emisiones")
    
    print(f"\n📊 MÓDULOS:")
    for module in health['modules']:
        ms = state.get(module, {})
        if isinstance(ms, dict):
            preview = str(ms)[:100]
            print(f"   {module:25s} → {preview}")
    
    print(f"\n📋 ÚLTIMOS EVENTOS:")
    for ev in colony_bus.get_recent_events(10):
        print(f"   [{ev.name}] {str(ev.data)[:80] if ev.data else ''}")


def watch_events():
    """Monitorea eventos en tiempo real."""
    print("👁️ MONITOREANDO EVENTOS DE LA COLONIA (Ctrl+C para salir)\n")
    
    def print_event(event):
        timestamp = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
        data_str = str(event.data)[:100] if event.data else ""
        print(f"[{timestamp}] {event.name:40s} | {data_str}")
    
    colony_bus.subscribe('*', print_event)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Monitoreo detenido")


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Colony Connect — Persistencia + Propagación")
    parser.add_argument("--status", action="store_true", help="Ver estado de la colonia")
    parser.add_argument("--watch", action="store_true", help="Monitorear eventos en tiempo real")
    parser.add_argument("--init", action="store_true", help="Inicializar y conectar todo")
    args = parser.parse_args()
    
    if args.watch:
        watch_events()
    elif args.status:
        show_status()
    else:
        # Por defecto: inicializar y mostrar estado
        initialize_colony()
        print()
        show_status()
