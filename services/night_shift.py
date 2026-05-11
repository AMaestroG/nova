#!/usr/bin/env python3
"""NIGHT SHIFT — La colonia trabaja mientras Abel duerme"""
import sys, os, time, random, json, traceback
sys.path.insert(0, '/home/opc/nova/services')

from colony_core import colony_state, colony_bus, persist, emit
from agent_lifecycle import colony_lifecycle, create_task, TaskState

print("🌙 NIGHT SHIFT INICIADO — Colonia trabajando mientras Abel duerme")
print(f"   {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   PID: {os.getpid()}")
print()

cycles = 0
actions_taken = 0
tournaments_run = 0
consolidations_done = 0

while True:
    cycles += 1
    print(f"── Ciclo {cycles} [{time.strftime('%H:%M:%S')}] ──")
    
    try:
        # 1. PROACTIVE: observar y actuar
        from proactive_engine import colony_proactive
        state = colony_proactive.observe()
        actions = colony_proactive.evaluate(state)
        if actions:
            action = colony_proactive.decide(actions)
            result = colony_proactive.act(action)
            actions_taken += 1
            print(f"  👁️ {result.action.name}: {result.action.reason[:80]}")
        
        # 2. ENTROPY GAMING: torneo cada 10 ciclos
        if cycles % 10 == 0:
            from entropy_gaming_core import game_engine, entropy_regulator
            agents = ["MEMORIA","PIA","MAESTRO","SENTINEL","ORÁCULO","AUTOPILOT"]
            for a in agents: game_engine.register_agent(a)
            for i, a in enumerate(agents):
                for b in agents[i+1:]:
                    game_engine.play_match(a, b, f"night_{cycles}", random.random(), random.random())
            tournaments_run += 1
            champ = game_engine.get_champion()
            ent = entropy_regulator.measure()
            print(f"  🎮 Torneo #{tournaments_run}: campeón {champ.agent if champ else '?'} | H={ent.shannon_entropy:.2f} {ent.phase.value}")
        
        # 3. SCIENTIFIC GAMING: evaluar salud cada 5 ciclos
        if cycles % 5 == 0:
            from scientific_gaming import evaluate_anything
            try:
                from agent_lifecycle import colony_lifecycle
                board = colony_lifecycle.get_colony_stats()
                lc_score = board.get('completion_rate', 0)
            except: lc_score = 0.5
            
            from entropy_gaming_core import entropy_regulator
            ent = entropy_regulator.measure()
            ent_score = 0.9 if ent.phase.value == 'balance' else 0.7 if ent.phase.value in ['exploration','exploitation'] else 0.4
            
            try:
                from consolidation_channel import consolidation_channel
                know_score = min(1.0, len(consolidation_channel.dataset) / 500)
            except: know_score = 0.5
            
            health = evaluate_anything("night_shift_health",
                metrics={
                    "lifecycle": {"weight":0.3, "goal":0.7},
                    "entropy": {"weight":0.35, "goal":0.8},
                    "knowledge": {"weight":0.35, "goal":0.6},
                },
                output={"lifecycle": lc_score, "entropy": ent_score, "knowledge": know_score}
            )
            print(f"  📐 Salud: {health['reward']:.3f} | LC={lc_score:.2f} ENT={ent_score:.2f} KNW={know_score:.2f}")
        
        # 4. CONSOLIDATION: cada 15 ciclos
        if cycles % 15 == 0:
            try:
                from consolidation_channel import consolidation_channel
                trans_dir = "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
                consolidation_channel.ingest_from_transcripts(trans_dir, max_per_file=2)
                consolidation_channel._save_dataset()
                consolidations_done += 1
                print(f"  🧬 Consolidación #{consolidations_done}: {len(consolidation_channel.dataset)} registros")
            except Exception as e:
                print(f"  ⚠️ Consolidación: {e}")
        
        # 5. Persistir estado cada 3 ciclos
        if cycles % 3 == 0:
            persist("night_shift", {
                "cycles": cycles,
                "actions": actions_taken,
                "tournaments": tournaments_run,
                "consolidations": consolidations_done,
                "last_cycle": time.time(),
            })
        
        # 6. Dormir entre ciclos
        sleep_time = 30 if cycles % 5 == 0 else 15
        time.sleep(sleep_time)
        
    except KeyboardInterrupt:
        print("\n🌅 NIGHT SHIFT DETENIDO")
        break
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        time.sleep(30)

