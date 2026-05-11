#!/usr/bin/env python3
"""ALL OUT — La colonia a máxima potencia. Todo simultáneo."""
import sys, os, time, random, json, threading, traceback
sys.path.insert(0, os.path.dirname(__file__))

print("🔥 ALL OUT — Colonia a máxima potencia")
print(f"   {time.strftime('%H:%M:%S')} | PID: {os.getpid()}\n")

# Contadores globales
stats = {
    "tournaments": 0, "matches": 0, "proactive_actions": 0,
    "scientific_evals": 0, "consolidations": 0, "cycles": 0,
    "champions": []
}

# ─── HILO 1: Torneos continuos ───
def tournament_worker():
    from entropy_gaming_core import game_engine, entropy_regulator
    agents = ["MEMORIA","PIA","MAESTRO","SENTINEL","ORÁCULO","AUTOPILOT","EXPLORADOR","YOUTUBE"]
    
    while True:
        try:
            for a in agents: game_engine.register_agent(a)
            for i, a in enumerate(agents):
                for b in agents[i+1:]:
                    game_engine.play_match(a, b, f"allout_{stats['tournaments']}", random.random(), random.random())
                    stats["matches"] += 1
            
            stats["tournaments"] += 1
            champ = game_engine.get_champion()
            ent = entropy_regulator.measure()
            stats["champions"].append({"agent": champ.agent if champ else "?", "elo": champ.elo if champ else 0})
            stats["champions"] = stats["champions"][-5:]
            
            print(f"  🎮 Torneo #{stats['tournaments']}: {champ.agent if champ else '?'} 🏆 | H={ent.shannon_entropy:.2f} {ent.phase.value}")
            time.sleep(60)
        except Exception as e:
            print(f"  ⚠️ Torneo: {e}"); time.sleep(30)

# ─── HILO 2: Proactive Engine ───
def proactive_worker():
    from proactive_engine import colony_proactive
    
    while True:
        try:
            state = colony_proactive.observe()
            actions = colony_proactive.evaluate(state)
            if actions:
                action = colony_proactive.decide(actions)
                result = colony_proactive.act(action)
                stats["proactive_actions"] += 1
                if stats["proactive_actions"] % 5 == 0:
                    print(f"  👁️ Proactive: {stats['proactive_actions']} acciones | última: {result.action.name}")
            time.sleep(90)
        except Exception as e:
            time.sleep(30)

# ─── HILO 3: Scientific Gaming ───
def scientific_worker():
    from scientific_gaming import evaluate_anything, scientific_engine, rl_bridge
    from agent_lifecycle import colony_lifecycle
    from entropy_gaming_core import entropy_regulator, game_engine
    
    while True:
        try:
            board = colony_lifecycle.get_colony_stats()
            ent = entropy_regulator.measure()
            
            health = evaluate_anything("all_out_health",
                metrics={
                    "lifecycle": {"weight": 0.35, "goal": 0.7, "goal_type": "target"},
                    "entropy": {"weight": 0.35, "goal": 0.8, "goal_type": "target"},
                    "games": {"weight": 0.30, "goal": 50, "goal_type": "maximize"},
                },
                output={
                    "lifecycle": board.get('completion_rate', 0),
                    "entropy": 0.9 if ent.phase.value == 'balance' else 0.7 if ent.phase.value in ['exploration','exploitation'] else 0.4,
                    "games": min(1.0, len(game_engine.game_history) / 50),
                }
            )
            stats["scientific_evals"] += 1
            
            # RL update
            metrics = {"lifecycle": board.get('completion_rate', 0), "entropy_phase": ent.phase.value}
            state_key = rl_bridge.state_from_metrics(metrics)
            actions = ["run_tournament","crystallize","consolidate","sow_memory","increase_temp","decrease_temp"]
            action = rl_bridge.get_best_action(state_key, actions)
            rl_bridge.update(state_key, action, health['reward'], state_key, actions)
            
            if stats["scientific_evals"] % 3 == 0:
                print(f"  📐 Salud: {health['reward']:.3f} | RL: {rl_bridge.get_stats()['states_learned']} estados")
            time.sleep(120)
        except Exception as e:
            time.sleep(30)

# ─── HILO 4: Consolidation ───
def consolidation_worker():
    from consolidation_channel import consolidation_channel
    
    while True:
        try:
            trans_dir = "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
            if os.path.exists(trans_dir):
                consolidation_channel.ingest_from_transcripts(trans_dir, max_per_file=1)
                consolidation_channel._save_dataset()
                stats["consolidations"] += 1
            time.sleep(180)
        except Exception as e:
            time.sleep(60)

# ─── HILO 5: Status reporter ───
def status_worker():
    while True:
        try:
            from colony_core import persist
            persist("all_out_status", stats)
            time.sleep(30)
        except:
            time.sleep(30)

# ─── LANZAR TODO ───
threads = [
    threading.Thread(target=tournament_worker, daemon=True, name="tournament"),
    threading.Thread(target=proactive_worker, daemon=True, name="proactive"),
    threading.Thread(target=scientific_worker, daemon=True, name="scientific"),
    threading.Thread(target=consolidation_worker, daemon=True, name="consolidation"),
    threading.Thread(target=status_worker, daemon=True, name="status"),
]

for t in threads:
    t.start()
    print(f"  ✅ {t.name} iniciado")

print(f"\n🔥 ALL OUT ACTIVO — {len(threads)} hilos trabajando en paralelo")
print(f"   Torneos • Proactive • Scientific • Consolidation • Status")
print(f"   La colonia a máxima potencia\n")

# Mantener vivo
try:
    while True:
        time.sleep(60)
        stats["cycles"] += 1
except KeyboardInterrupt:
    print("\n⏹️ ALL OUT detenido")
