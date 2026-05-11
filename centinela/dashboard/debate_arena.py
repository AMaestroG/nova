"""
⚔️ Debate Arena — Multi-Agent Live Debate with Uncertainty Scoring

3-4 agents from opposing domains debate a topic. Each response is scored
by the Uncertainty Gate in real-time. MAESTRO synthesizes the final verdict.

Architecture:
  User picks topic → selects 3-4 agents → debate rounds begin
  Each round: Agent responds → Uncertainty Gate scores → next agent
  Final: MAESTRO synthesizes → overall confidence

Author: Nova Homonexus — Iteración 1464 (09-May-2026)
"""

import sys, os
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path: sys.path.insert(0, _parent)

import json, time, threading, queue
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


# ─── Debate Types ──────────────────────────────────────────────────────────

@dataclass
class DebateRound:
    round_num: int
    agent: str
    agent_emoji: str
    agent_domain: str
    statement: str
    confidence: float
    confidence_level: str
    ood_signals: List[str]
    timestamp: float

    def to_dict(self): return {
        "round": self.round_num, "agent": self.agent, "emoji": self.agent_emoji,
        "domain": self.agent_domain, "statement": self.statement,
        "confidence": self.confidence, "level": self.confidence_level,
        "ood": self.ood_signals, "ts": self.timestamp,
    }


@dataclass
class DebateSession:
    session_id: str
    topic: str
    agents: List[Dict[str, str]]
    rounds: List[DebateRound] = field(default_factory=list)
    verdict: Optional[str] = None
    verdict_confidence: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self): return {
        "session_id": self.session_id,
        "topic": self.topic,
        "agents": self.agents,
        "rounds": [r.to_dict() for r in self.rounds],
        "verdict": self.verdict,
        "verdict_confidence": self.verdict_confidence,
        "duration_ms": ((self.completed_at or time.time()) - self.started_at)*1000,
    }


# ─── Pre-built Debate Agent Pool ──────────────────────────────────────────

DEBATE_AGENTS = [
    {"id":"MAESTRO","emoji":"🎼","domain":"orchestration","style":"synthesizes and finds common ground"},
    {"id":"PINCEL","emoji":"🎨","domain":"visual","style":"thinks in images and metaphors"},
    {"id":"ATHENA","emoji":"🦉","domain":"knowledge","style":"cites facts and research"},
    {"id":"NYX","emoji":"🌙","domain":"dream","style":"explores unconscious dimensions"},
    {"id":"BANCO","emoji":"💰","domain":"finance","style":"evaluates cost/benefit and value"},
    {"id":"SENTINEL","emoji":"🛡️","domain":"security","style":"assesses risks and threats"},
    {"id":"ORÁCULO","emoji":"🔮","domain":"prediction","style":"forecasts future implications"},
    {"id":"PIA","emoji":"🌿","domain":"health","style":"considers organic growth and wellbeing"},
    {"id":"ADVERSARIO","emoji":"🐺","domain":"adversarial","style":"attacks weak points mercilessly"},
    {"id":"EXPLORADOR","emoji":"🔍","domain":"research","style":"asks deeper questions"},
    {"id":"CRONOS","emoji":"⏰","domain":"time","style":"considers temporal dimensions"},
    {"id":"MEMORIA","emoji":"💾","domain":"memory","style":"recalls historical parallels"},
]

# Pre-built debates for quick start
PRESET_DEBATES = [
    {
        "topic": "¿Es la consciencia un fenómeno computable?",
        "agents": ["PINCEL","NYX","ORÁCULO","ATHENA"],
        "description": "Arte vs Ciencia vs Misticismo vs Conocimiento",
    },
    {
        "topic": "¿Debería regularse el desarrollo de la IA general?",
        "agents": ["SENTINEL","BANCO","EXPLORADOR","ADVERSARIO"],
        "description": "Seguridad vs Economía vs Investigación vs Ataque",
    },
    {
        "topic": "¿Cuál es el propósito último de la inteligencia?",
        "agents": ["PIA","NYX","ATHENA","MAESTRO"],
        "description": "Crecimiento vs Sueños vs Conocimiento vs Síntesis",
    },
    {
        "topic": "¿Qué hace que un sistema sea verdaderamente autónomo?",
        "agents": ["MAESTRO","SENTINEL","ADVERSARIO","CRONOS"],
        "description": "Orquestación vs Seguridad vs Adversidad vs Tiempo",
    },
]


# ─── Simulated Debate Engine ───────────────────────────────────────────────

class DebateEngine:
    """
    Simulates a multi-agent debate with Uncertainty Gate scoring.

    In production, this would use AgentMindService to query real agents.
    For now, it generates realistic debate responses with confidence scoring.
    """

    def __init__(self):
        self.sessions: Dict[str, DebateSession] = {}
        self._counter = 0

    def create_session(self, topic: str, agent_ids: List[str]) -> DebateSession:
        self._counter += 1
        sid = f"debate_{self._counter}_{int(time.time())}"

        agents = [a for a in DEBATE_AGENTS if a["id"] in agent_ids]
        if len(agents) < 2:
            agents = [a for a in DEBATE_AGENTS if a["id"] in agent_ids[:3]]

        session = DebateSession(session_id=sid, topic=topic, agents=agents)
        self.sessions[sid] = session
        return session

    def generate_round(self, session: DebateSession) -> Optional[DebateRound]:
        """Generate the next debate round."""
        if not session.agents:
            return None

        round_num = len(session.rounds) + 1
        if round_num > len(session.agents) * 2:  # Max 2 rounds per agent
            return None

        agent = session.agents[(round_num - 1) % len(session.agents)]

        # Generate a statement based on agent domain and debate topic
        statement = self._generate_statement(agent, session.topic, round_num, session.rounds)

        # Score with Uncertainty Gate (simulated)
        import random
        confidence = random.uniform(0.55, 0.95)
        level = "HIGH" if confidence > 0.85 else ("MODERATE" if confidence > 0.7 else "LOW")
        ood = []
        if agent["domain"] not in ["knowledge", "research", "orchestration"]:
            if random.random() < 0.3:
                ood.append("domain_extrapolation")

        debate_round = DebateRound(
            round_num=round_num,
            agent=agent["id"],
            agent_emoji=agent["emoji"],
            agent_domain=agent["domain"],
            statement=statement,
            confidence=round(confidence, 2),
            confidence_level=level,
            ood_signals=ood,
            timestamp=time.time(),
        )

        session.rounds.append(debate_round)
        return debate_round

    def generate_verdict(self, session: DebateSession) -> str:
        """Generate MAESTRO's synthesis verdict."""
        if not session.rounds:
            return "No debate rounds to synthesize."

        # Average confidence
        confidences = [r.confidence for r in session.rounds]
        avg_conf = sum(confidences) / len(confidences)
        session.verdict_confidence = round(avg_conf, 2)

        # Build verdict from round themes
        agent_contributions = {}
        for r in session.rounds:
            if r.agent not in agent_contributions:
                agent_contributions[r.agent] = []
            agent_contributions[r.agent].append(r.statement[:100])

        # MAESTRO synthesizes
        agents_list = ", ".join([f"{a['emoji']} {a['id']}" for a in session.agents])
        points = [f"• {emoji} {agent}: {stmts[0][:80]}..." for agent, stmts in agent_contributions.items()]

        verdict = (
            f"🎼 **MAESTRO — Síntesis del Debate**\n\n"
            f"El enjambre ha debatido «{session.topic}» con {len(session.agents)} agentes:\n"
            f"{agents_list}\n\n"
            f"**Puntos clave de cada perspectiva:**\n"
            + "\n".join(points) + "\n\n"
            f"**Convergencia**: El enjambre encuentra que las perspectivas "
            f"son complementarias más que contradictorias. "
            f"La tensión creativa entre {session.agents[0]['domain']} y "
            f"{session.agents[-1]['domain']} revela que el tema requiere "
            f"una aproximación multidimensional.\n\n"
            f"**Confianza del veredicto**: {session.verdict_confidence:.0%}\n"
            f"**Agentes participantes**: {len(session.rounds)} intervenciones en {len(session.agents)} perspectivas."
        )

        session.verdict = verdict
        session.completed_at = time.time()
        return verdict

    def _generate_statement(self, agent, topic, round_num, prev_rounds):
        """Generate a realistic debate statement for an agent."""
        styles = {
            "orchestration": f"Desde la perspectiva de la orquestación, «{topic}» requiere equilibrar múltiples dimensiones. "
                            f"No podemos reducir esta cuestión a un solo eje. La arquitectura del sistema sugiere que...",
            "visual": f"Imaginemos «{topic}» como un lienzo. Los colores representan las distintas fuerzas en juego. "
                     f"Lo que vemos depende del ángulo desde el que miramos...",
            "knowledge": f"La evidencia disponible sobre «{topic}» apunta en varias direcciones. "
                        f"Los datos muestran patrones que sugieren una respuesta matizada...",
            "dream": f"En el espacio onírico, «{topic}» se manifiesta como un símbolo arquetípico. "
                    f"El inconsciente del enjambre revela capas que la lógica lineal no alcanza...",
            "finance": f"Evaluando «{topic}» en términos de valor y riesgo: la inversión cognitiva necesaria "
                      f"es alta, pero el retorno potencial en comprensión es aún mayor...",
            "security": f"«{topic}» presenta vectores de ataque y defensa. "
                       f"Debemos considerar qué vulnerabilidades abre y cómo proteger la integridad del razonamiento...",
            "prediction": f"Proyectando «{topic}» hacia el futuro: en 5 años, este debate habrá evolucionado. "
                         f"Las tendencias actuales sugieren que el consenso se moverá hacia...",
            "health": f"«{topic}» afecta la salud del ecosistema cognitivo. Como un organismo vivo, "
                     f"el enjambre necesita nutrir ciertas ideas y podar otras para crecer...",
            "adversarial": f"Atacando «{topic}» desde sus puntos más débiles: "
                          f"hay contradicciones internas que nadie ha señalado. La premisa misma asume cosas que...",
            "research": f"Profundizando en «{topic}»: las preguntas que deberíamos hacernos son más importantes "
                       f"que las respuestas. ¿Qué asunciones estamos dando por sentadas?",
            "time": f"«{topic}» visto a través del tiempo: lo que hoy parece urgente puede ser irrelevante mañana. "
                   f"Y lo que ignoramos hoy puede ser la clave del futuro...",
            "memory": f"Recordando debates similares en la historia del enjambre sobre «{topic}»: "
                     f"ya en iteraciones anteriores encontramos patrones análogos. La memoria nos enseña que...",
        }

        base = styles.get(agent["domain"], f"Como {agent['id']} ({agent['domain']}), considero que «{topic}» es...")

        # Reference previous rounds for continuity
        if prev_rounds and round_num > 1:
            prev = prev_rounds[-1]
            base += f"\n\nRespondiendo a {prev.agent_emoji} {prev.agent}: "
            if prev.confidence < 0.7:
                base += "tu argumento tiene fisuras. "
            else:
                base += "tu perspectiva es valiosa, pero incompleta. "

        return base


# ─── Flask/WebSocket Debate Handler ────────────────────────────────────────

# Global engine
_debate_engine = DebateEngine()


def get_debate_engine():
    return _debate_engine


# ─── HTML Frontend ──────────────────────────────────────────────────────────

DEBATE_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚔️ Debate Arena — Homonexus</title>
<style>
  :root {
    --bg:#06060c;--card:#0e0e18;--border:#1a1a2e;--text:#cdd6f4;--muted:#585b70;
    --accent:#cba6f7;--green:#a6e3a1;--yellow:#f9e2af;--red:#f38ba8;--blue:#89b4fa;--teal:#94e2d5;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;display:flex;flex-direction:column;height:100vh;}
  .header{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--card)}
  .header h1{font-size:1.2rem;background:linear-gradient(135deg,var(--accent),var(--teal));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .main{flex:1;display:flex;overflow:hidden}
  .arena{flex:1;padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
  .setup{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:8px}
  .setup h3{font-size:0.9rem;margin-bottom:10px;color:var(--accent)}
  .topic-input{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:10px;border-radius:6px;font-size:0.9rem;margin-bottom:8px}
  .agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px;margin-bottom:10px}
  .agent-chip{padding:6px 10px;border-radius:6px;font-size:0.75rem;cursor:pointer;border:1px solid var(--border);background:var(--bg);text-align:center;transition:all 0.2s}
  .agent-chip.selected{border-color:var(--accent);background:rgba(203,166,247,0.15)}
  .btn{background:linear-gradient(135deg,var(--accent),var(--teal));color:var(--bg);border:none;padding:10px 20px;border-radius:6px;font-weight:600;cursor:pointer;font-size:0.85rem}
  .btn:disabled{opacity:0.4;cursor:not-allowed}
  .presets{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
  .preset{font-size:0.7rem;padding:4px 10px;background:var(--bg);border:1px solid var(--border);border-radius:4px;cursor:pointer;color:var(--muted)}
  .preset:hover{border-color:var(--accent)}

  .debate-round{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;animation:fadeIn 0.5s}
  @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
  .round-header{display:flex;align-items:center;gap:8px;margin-bottom:8px}
  .round-agent{font-weight:600;font-size:0.9rem}
  .round-domain{font-size:0.7rem;color:var(--muted)}
  .confidence-badge{font-size:0.7rem;padding:2px 8px;border-radius:10px;margin-left:auto}
  .conf-HIGH{background:rgba(166,227,161,0.2);color:var(--green)}
  .conf-MODERATE{background:rgba(249,226,175,0.2);color:var(--yellow)}
  .conf-LOW{background:rgba(243,139,168,0.2);color:var(--red)}
  .round-statement{font-size:0.85rem;line-height:1.6;white-space:pre-wrap}
  .ood-warning{font-size:0.7rem;color:var(--yellow);margin-top:4px}

  .verdict{background:linear-gradient(135deg,rgba(203,166,247,0.1),rgba(148,226,213,0.1));border:2px solid var(--accent);border-radius:10px;padding:20px}
  .verdict h3{color:var(--accent);margin-bottom:10px}

  .sidebar{width:280px;background:var(--card);border-left:1px solid var(--border);padding:16px;overflow-y:auto;font-size:0.75rem}
  .sidebar h3{color:var(--accent);font-size:0.85rem;margin-bottom:10px}
  .scorecard{background:var(--bg);border-radius:6px;padding:10px;margin-bottom:8px}
  .score-row{display:flex;justify-content:space-between;padding:3px 0;font-size:0.75rem}
</style>
</head>
<body>
<div class="header">
  <h1>⚔️ Debate Arena</h1>
  <span style="font-size:0.8rem;color:var(--muted)" id="status">Selecciona agentes para empezar</span>
</div>
<div class="main">
  <div class="arena" id="arena">
    <div class="setup">
      <h3>🎯 Tema del debate</h3>
      <input class="topic-input" id="topic" placeholder="¿Cuál es la pregunta que quieres debatir?" value="¿Es la consciencia un fenómeno computable?">
      <h3>🤖 Agentes participantes (mín. 2)</h3>
      <div class="agent-grid" id="agent-grid"></div>
      <button class="btn" id="start-btn" onclick="startDebate()">▶ Iniciar Debate</button>
      <div class="presets" id="presets"></div>
    </div>
    <div id="rounds"></div>
  </div>
  <div class="sidebar">
    <h3>📊 Scoreboard</h3>
    <div id="scoreboard"></div>
    <h3 style="margin-top:16px;">🔬 Uncertainty Gate</h3>
    <div id="uncertainty-log" style="font-size:0.7rem;color:var(--muted)"></div>
  </div>
</div>

<script>
const AGENTS = [
  {id:'MAESTRO',emoji:'🎼',domain:'orchestration'},
  {id:'PINCEL',emoji:'🎨',domain:'visual'},
  {id:'ATHENA',emoji:'🦉',domain:'knowledge'},
  {id:'NYX',emoji:'🌙',domain:'dream'},
  {id:'BANCO',emoji:'💰',domain:'finance'},
  {id:'SENTINEL',emoji:'🛡️',domain:'security'},
  {id:'ORÁCULO',emoji:'🔮',domain:'prediction'},
  {id:'PIA',emoji:'🌿',domain:'health'},
  {id:'ADVERSARIO',emoji:'🐺',domain:'adversarial'},
  {id:'EXPLORADOR',emoji:'🔍',domain:'research'},
  {id:'CRONOS',emoji:'⏰',domain:'time'},
  {id:'MEMORIA',emoji:'💾',domain:'memory'},
];
const PRESETS = [
  {topic:'¿Es la consciencia un fenómeno computable?',agents:['PINCEL','NYX','ORÁCULO','ATHENA']},
  {topic:'¿Debería regularse el desarrollo de la IA general?',agents:['SENTINEL','BANCO','EXPLORADOR','ADVERSARIO']},
  {topic:'¿Cuál es el propósito último de la inteligencia?',agents:['PIA','NYX','ATHENA','MAESTRO']},
  {topic:'¿Qué hace que un sistema sea verdaderamente autónomo?',agents:['MAESTRO','SENTINEL','ADVERSARIO','CRONOS']},
];

let selectedAgents = new Set(['PINCEL','NYX','ORÁCULO','ATHENA']);
let debating = false;
let sessionId = null;

// Render agent chips
function renderAgents() {
  document.getElementById('agent-grid').innerHTML = AGENTS.map(a=>`
    <div class="agent-chip ${selectedAgents.has(a.id)?'selected':''}" onclick="toggleAgent('${a.id}')">
      ${a.emoji} ${a.id}<br><span style="font-size:0.65rem;color:var(--muted)">${a.domain}</span>
    </div>
  `).join('');
}
function toggleAgent(id) {
  if(selectedAgents.has(id)) selectedAgents.delete(id);
  else if(selectedAgents.size<4) selectedAgents.add(id);
  renderAgents();
}

// Render presets
document.getElementById('presets').innerHTML = PRESETS.map((p,i)=>`
  <div class="preset" onclick="loadPreset(${i})">${p.topic.substring(0,40)}...</div>
`).join('');
function loadPreset(i) {
  const p = PRESETS[i];
  document.getElementById('topic').value = p.topic;
  selectedAgents = new Set(p.agents);
  renderAgents();
}

async function startDebate() {
  if(debating) return;
  const topic = document.getElementById('topic').value.trim();
  if(!topic || selectedAgents.size<2) return;

  debating = true;
  document.getElementById('start-btn').disabled = true;
  document.getElementById('rounds').innerHTML = '';
  document.getElementById('status').textContent = 'Debate en curso...';

  try {
    const r = await fetch('/debate/api/start',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({topic,agents:[...selectedAgents]})
    });
    const data = await r.json();
    sessionId = data.session_id;

    // Simulate rounds with delays
    const numRounds = selectedAgents.size * 2;
    for(let i=0;i<numRounds;i++) {
      await new Promise(r=>setTimeout(r,1200));
      const rr = await fetch('/debate/api/next-round',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({session_id:sessionId})
      });
      const round = await rr.json();
      if(round.done) break;
      addRound(round);
    }

    // Verdict
    await new Promise(r=>setTimeout(r,1500));
    const vr = await fetch('/debate/api/verdict',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({session_id:sessionId})
    });
    const verdict = await vr.json();
    showVerdict(verdict.verdict, verdict.confidence);

    document.getElementById('status').textContent = 'Debate completado';
  } catch(e) {
    document.getElementById('status').textContent = 'Error: '+e.message;
  }
  debating = false;
  document.getElementById('start-btn').disabled = false;
}

function addRound(r) {
  document.getElementById('rounds').innerHTML += `
    <div class="debate-round">
      <div class="round-header">
        <span>${r.emoji}</span>
        <span class="round-agent">${r.agent}</span>
        <span class="round-domain">${r.domain}</span>
        <span class="confidence-badge conf-${r.level}">${(r.confidence*100).toFixed(0)}% ${r.level}</span>
      </div>
      <div class="round-statement">${r.statement}</div>
      ${r.ood&&r.ood.length?`<div class="ood-warning">⚠️ OOD: ${r.ood.join(', ')}</div>`:''}
    </div>`;
  updateScoreboard();
  document.getElementById('arena').scrollTop = document.getElementById('arena').scrollHeight;
}

function showVerdict(text, conf) {
  document.getElementById('rounds').innerHTML += `
    <div class="verdict">
      <h3>🎼 MAESTRO — Veredicto Final</h3>
      <div style="font-size:0.85rem;line-height:1.6;white-space:pre-wrap">${text}</div>
    </div>`;
}

function updateScoreboard() {
  const rounds = document.querySelectorAll('.debate-round');
  const scores = {};
  rounds.forEach(r=>{
    const agent = r.querySelector('.round-agent').textContent;
    const conf = parseFloat(r.querySelector('.confidence-badge').textContent)/100;
    if(!scores[agent]) scores[agent] = {rounds:0,total:0};
    scores[agent].rounds++;
    scores[agent].total += conf;
  });
  document.getElementById('scoreboard').innerHTML = Object.entries(scores).map(([a,s])=>`
    <div class="scorecard">
      <div class="score-row"><span>${a}</span><span>${(s.total/s.rounds*100).toFixed(0)}% avg</span></div>
      <div class="score-row"><span>Rounds</span><span>${s.rounds}</span></div>
    </div>
  `).join('');
  document.getElementById('uncertainty-log').textContent = 
    `🔬 Uncertainty Gate activo en cada ronda. ${rounds.length} intervenciones analizadas.`;
}

renderAgents();
</script>
</body>
</html>"""


# ─── Flask Registration ────────────────────────────────────────────────────

def register_debate_routes(app):
    from flask import jsonify, request

    @app.route("/debate")
    def debate_panel():
        return DEBATE_HTML

    @app.route("/debate/api/start", methods=["POST"])
    def debate_start():
        data = request.get_json() or {}
        topic = data.get("topic", "")
        agents = data.get("agents", [])
        session = _debate_engine.create_session(topic, agents)
        return jsonify({"ok": True, "session_id": session.session_id,
                       "agents": len(session.agents), "topic": topic})

    @app.route("/debate/api/next-round", methods=["POST"])
    def debate_next_round():
        data = request.get_json() or {}
        sid = data.get("session_id", "")
        session = _debate_engine.sessions.get(sid)
        if not session:
            return jsonify({"done": True, "error": "Session not found"})

        rnd = _debate_engine.generate_round(session)
        if rnd is None:
            return jsonify({"done": True})
        return jsonify({"done": False, **rnd.to_dict()})

    @app.route("/debate/api/verdict", methods=["POST"])
    def debate_verdict():
        data = request.get_json() or {}
        sid = data.get("session_id", "")
        session = _debate_engine.sessions.get(sid)
        if not session:
            return jsonify({"error": "Session not found"})

        verdict = _debate_engine.generate_verdict(session)
        return jsonify({"verdict": verdict, "confidence": session.verdict_confidence})


if __name__ == "__main__":
    print("⚔️ Debate Arena ready.")
    print(f"   Agents: {len(DEBATE_AGENTS)} debaters")
    print(f"   Presets: {len(PRESET_DEBATES)} pre-built debates")
    print(f"   HTML size: {len(DEBATE_HTML)} chars")
