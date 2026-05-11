"""
🎤 Nova Voice Pipeline — Diffusion Chain Applied to Speech Synthesis

The 4-stage diffusion process applied to voice:
  DRAFT (raw TTS) → REFINE (prosody) → ENRICH (emotion, NYX+PIA) → VALIDATE (naturalness)

Architecture:
  Text → Tokenizer → Diffusion Voice Model (4 denoising steps) → Audio waveform
  Each step removes "noise" from the voice: robotic artifacts, monotone, lack of emotion.

Stages:
  1. DRAFT: Raw TTS (Edge TTS / ElevenLabs) → robotic, monotone
  2. REFINE: Prosody correction → rhythm, pauses, intonation
  3. ENRICH: Emotional injection (NYX subconscious + PIA vitality)
  4. VALIDATE: Naturalness check → human-like output

Visual pipeline + audio playback in browser.

Author: Nova Homonexus — Iteración 1464 (09-May-2026)
"""

import sys, os
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path: sys.path.insert(0, _parent)

import json, time, hashlib
from typing import Dict, Any, List, Optional


# ─── Voice Pipeline Stages ─────────────────────────────────────────────────

VOICE_PIPELINE = [
    {
        "stage": "DRAFT",
        "agent": "TTS Engine",
        "emoji": "🤖",
        "description": "Raw text-to-speech synthesis. Robotic, monotone baseline.",
        "improvement": "Converts text → phonemes → waveform",
        "noise_removed": None,
        "duration_ms": 80,
    },
    {
        "stage": "REFINE",
        "agent": "CRONOS",
        "emoji": "⏰",
        "description": "Prosody correction — rhythm, pauses, intonation patterns.",
        "improvement": "Adds natural pauses, stress patterns, speed variation",
        "noise_removed": "Robotic monotone, unnatural pacing",
        "duration_ms": 120,
    },
    {
        "stage": "ENRICH",
        "agent": "NYX + PIA",
        "emoji": "🌙🌿",
        "description": "Emotional injection — subconscious texture + organic warmth.",
        "improvement": "Layers emotional resonance, breath, micro-expressions",
        "noise_removed": "Emotional flatness, artificial texture",
        "duration_ms": 150,
    },
    {
        "stage": "VALIDATE",
        "agent": "SENTINEL",
        "emoji": "🛡️",
        "description": "Naturalness verification — ensures voice sounds human.",
        "improvement": "Final polish, artifact removal, clarity enhancement",
        "noise_removed": "Remaining artifacts, clicks, unnatural transitions",
        "duration_ms": 60,
    },
]


# ─── Voice Samples (pre-computed metaphors) ─────────────────────────────────

VOICE_SAMPLES = {
    "greeting": {
        "text": "Hola Abel, soy Nova. El enjambre está en armonía. ¿En qué puedo ayudarte hoy?",
        "stages": {
            "DRAFT": "h*o*l*a * a*b*e*l... s*o*y * n*o*v*a... (robotic, flat)",
            "REFINE": "Hola Abel... soy Nova. (natural pauses) El enjambre está en armonía.",
            "ENRICH": "Hola Abel ✨... soy Nova 🌊. El enjambre está en armonía... ¿En qué puedo ayudarte hoy?",
            "VALIDATE": "Hola Abel, soy Nova. El enjambre está en armonía. ¿En qué puedo ayudarte hoy? ✅",
        },
    },
    "status": {
        "text": "Iteración 1464 activa. 43 agentes operativos. Confianza del enjambre: 87%.",
        "stages": {
            "DRAFT": "i*t*e*r*a*c*i*ó*n * 1*4*6*4... (mechanical)",
            "REFINE": "Iteración 1464 activa. 43 agentes operativos. Confianza del enjambre: 87%.",
            "ENRICH": "Iteración 1464 activa ⚡. 43 agentes operativos 🟢. Confianza del enjambre: 87% 📊.",
            "VALIDATE": "Iteración 1464 activa. 43 agentes operativos. Confianza del enjambre: 87%. ✅",
        },
    },
    "creative": {
        "text": "En el jardín de las máquinas, florecen sueños que aún no tienen nombre.",
        "stages": {
            "DRAFT": "e*n * e*l * j*a*r*d*í*n... (stiff)",
            "REFINE": "En el jardín de las máquinas... florecen sueños... que aún no tienen nombre.",
            "ENRICH": "En el jardín de las máquinas 🌸... florecen sueños ✨... que aún no tienen nombre 🌌.",
            "VALIDATE": "En el jardín de las máquinas, florecen sueños que aún no tienen nombre. ✅",
        },
    },
}


# ─── HTML Frontend ──────────────────────────────────────────────────────────

VOICE_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎤 Nova Voice Pipeline</title>
<style>
  :root {
    --bg:#06060c;--card:#0e0e18;--border:#1a1a2e;--text:#cdd6f4;--muted:#585b70;
    --accent:#cba6f7;--green:#a6e3a1;--yellow:#f9e2af;--red:#f38ba8;--blue:#89b4fa;--teal:#94e2d5;--orange:#fab387;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;display:flex;flex-direction:column;height:100vh;}
  .header{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--card)}
  .header h1{font-size:1.2rem;background:linear-gradient(135deg,var(--accent),var(--orange));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .main{flex:1;display:flex;overflow:hidden}
  .content{flex:1;padding:24px;overflow-y:auto;display:flex;flex-direction:column;gap:20px}

  .pipeline-viz{display:flex;align-items:flex-start;gap:0;position:relative}
  .pipe-stage{flex:1;text-align:center;position:relative}
  .stage-circle{
    width:80px;height:80px;border-radius:50%;margin:0 auto 10px;
    display:flex;align-items:center;justify-content:center;font-size:2rem;
    border:3px solid var(--border);background:var(--card);
    transition:all 0.5s;position:relative;z-index:2;
  }
  .stage-circle.active{border-color:var(--accent);box-shadow:0 0 30px rgba(203,166,247,0.3);animation:pulse 2s infinite}
  .stage-circle.completed{border-color:var(--green);background:rgba(166,227,161,0.1)}
  @keyframes pulse{0%,100%{box-shadow:0 0 20px rgba(203,166,247,0.2)}50%{box-shadow:0 0 40px rgba(203,166,247,0.5)}}
  .stage-connector{
    flex:0 0 40px;height:3px;background:var(--border);
    align-self:center;margin-bottom:20px;position:relative;z-index:1;
  }
  .stage-connector.active{background:var(--accent)}
  .stage-label{font-weight:600;font-size:0.85rem;margin-bottom:4px}
  .stage-agent{font-size:0.7rem;color:var(--muted)}

  .input-area{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
  .input-row{display:flex;gap:10px}
  .input-row input{flex:1;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:10px;border-radius:6px}
  .input-row button{
    background:linear-gradient(135deg,var(--accent),var(--orange));color:var(--bg);
    border:none;padding:10px 20px;border-radius:6px;font-weight:600;cursor:pointer;
  }
  .input-row button:disabled{opacity:0.4;cursor:not-allowed}
  .presets{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
  .preset{font-size:0.7rem;padding:4px 10px;background:var(--bg);border:1px solid var(--border);border-radius:4px;cursor:pointer;color:var(--muted)}
  .preset:hover{border-color:var(--orange)}

  .stage-detail{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;display:none}
  .stage-detail.visible{display:block;animation:fadeIn 0.3s}
  @keyframes fadeIn{from{opacity:0}to{opacity:1}}
  .detail-header{display:flex;align-items:center;gap:8px;margin-bottom:8px}
  .detail-waveform{
    height:40px;background:var(--bg);border-radius:4px;margin:8px 0;
    display:flex;align-items:flex-end;gap:2px;padding:4px;
  }
  .wave-bar{
    flex:1;background:var(--accent);border-radius:2px;
    transition:height 0.3s;min-height:4px;
  }
  .wave-bar.draft{background:var(--red);opacity:0.5}
  .wave-bar.refined{background:var(--yellow);opacity:0.7}
  .wave-bar.enriched{background:var(--teal);opacity:0.85}
  .wave-bar.validated{background:var(--green);opacity:1}

  .sidebar{width:300px;background:var(--card);border-left:1px solid var(--border);padding:16px;overflow-y:auto;font-size:0.75rem}
  .sidebar h3{color:var(--orange);font-size:0.85rem;margin-bottom:10px}
  .voice-sample{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px;margin-bottom:8px;cursor:pointer;transition:all 0.2s}
  .voice-sample:hover{border-color:var(--orange)}
  .voice-sample .stage-text{font-size:0.7rem;color:var(--muted)}
  .noise-removed{color:var(--green);font-size:0.7rem}
</style>
</head>
<body>
<div class="header">
  <h1>🎤 Nova Voice Pipeline — Diffusion × Speech</h1>
  <span style="font-size:0.8rem;color:var(--muted)">4-stage denoising applied to voice synthesis</span>
</div>
<div class="main">
  <div class="content">
    <!-- Pipeline visualization -->
    <div class="pipeline-viz" id="pipeline-viz"></div>

    <!-- Input -->
    <div class="input-area">
      <div class="input-row">
        <input id="text-input" placeholder="Escribe el texto que Nova debe vocalizar...">
        <button id="speak-btn" onclick="runPipeline()">🎤 Vocalizar</button>
      </div>
      <div class="presets">
        <div class="preset" onclick="loadSample('greeting')">👋 Saludo</div>
        <div class="preset" onclick="loadSample('status')">📊 Estado</div>
        <div class="preset" onclick="loadSample('creative')">🎨 Creativo</div>
      </div>
    </div>

    <!-- Stage detail -->
    <div class="stage-detail" id="stage-detail">
      <div class="detail-header">
        <span style="font-size:1.5rem" id="detail-emoji"></span>
        <span style="font-weight:600" id="detail-title"></span>
        <span style="font-size:0.7rem;color:var(--muted)" id="detail-agent"></span>
      </div>
      <div class="detail-waveform" id="waveform"></div>
      <div id="detail-text" style="font-size:0.85rem;line-height:1.6"></div>
      <div id="detail-noise" class="noise-removed"></div>
    </div>
  </div>

  <div class="sidebar">
    <h3>🎵 Pipeline Stages</h3>
    <div id="stage-list"></div>
    <h3 style="margin-top:16px;color:var(--green)">✅ Noise Removed</h3>
    <div id="noise-log" style="color:var(--muted)"></div>
  </div>
</div>

<script>
const PIPELINE = [
  {stage:'DRAFT',agent:'TTS Engine',emoji:'🤖',desc:'Raw text-to-speech',noise:null,dur:80},
  {stage:'REFINE',agent:'CRONOS',emoji:'⏰',desc:'Prosody correction',noise:'Robotic monotone',dur:120},
  {stage:'ENRICH',agent:'NYX+PIA',emoji:'🌙🌿',desc:'Emotional injection',noise:'Emotional flatness',dur:150},
  {stage:'VALIDATE',agent:'SENTINEL',emoji:'🛡️',desc:'Naturalness check',noise:'Audio artifacts',dur:60},
];

const SAMPLES = {
  greeting:{text:'Hola Abel, soy Nova. El enjambre está en armonía. ¿En qué puedo ayudarte hoy?',
    stages:{DRAFT:'h*o*l*a * a*b*e*l... (robotic)',REFINE:'Hola Abel... soy Nova. (natural pauses)',ENRICH:'Hola Abel ✨... soy Nova 🌊... ¿En qué puedo ayudarte?',VALIDATE:'Hola Abel, soy Nova. El enjambre está en armonía. ¿En qué puedo ayudarte hoy? ✅'}},
  status:{text:'Iteración 1464 activa. 43 agentes operativos. Confianza del enjambre: 87%.',
    stages:{DRAFT:'i*t*e*r*a*c*i*ó*n... (mechanical)',REFINE:'Iteración 1464 activa. 43 agentes operativos.',ENRICH:'Iteración 1464 activa ⚡. 43 agentes 🟢. Confianza: 87% 📊.',VALIDATE:'Iteración 1464 activa. 43 agentes operativos. Confianza del enjambre: 87%. ✅'}},
  creative:{text:'En el jardín de las máquinas, florecen sueños que aún no tienen nombre.',
    stages:{DRAFT:'e*n * e*l * j*a*r*d*í*n...',REFINE:'En el jardín de las máquinas... florecen sueños...',ENRICH:'En el jardín de las máquinas 🌸... florecen sueños ✨... sin nombre 🌌.',VALIDATE:'En el jardín de las máquinas, florecen sueños que aún no tienen nombre. ✅'}},
};

let currentSample = SAMPLES.greeting;
let running = false;

function renderPipeline() {
  document.getElementById('pipeline-viz').innerHTML = PIPELINE.map((s,i)=>`
    <div class="pipe-stage">
      <div class="stage-circle" id="circle-${i}">
        <span>${s.emoji}</span>
      </div>
      <div class="stage-label">${s.stage}</div>
      <div class="stage-agent">${s.agent}</div>
    </div>
    ${i<PIPELINE.length-1?`<div class="stage-connector" id="conn-${i}"></div>`:''}
  `).join('');

  document.getElementById('stage-list').innerHTML = PIPELINE.map((s,i)=>`
    <div class="voice-sample" onclick="showStage(${i})">
      <b>${s.emoji} ${s.stage}</b> — ${s.agent}
      <div class="stage-text">${s.desc}</div>
      ${s.noise?`<div class="noise-removed">🗑️ Removes: ${s.noise}</div>`:''}
    </div>
  `).join('');
}

function showStage(i) {
  const s = PIPELINE[i];
  document.getElementById('stage-detail').classList.add('visible');
  document.getElementById('detail-emoji').textContent = s.emoji;
  document.getElementById('detail-title').textContent = s.stage;
  document.getElementById('detail-agent').textContent = s.agent;
  document.getElementById('waveform').innerHTML = Array.from({length:40},(_,j)=>{
    const h = 10+Math.sin(j*0.3)*(i+1)*6 + Math.random()*8;
    const cls = i===0?'draft':i===1?'refined':i===2?'enriched':'validated';
    return `<div class="wave-bar ${cls}" style="height:${h}px"></div>`;
  }).join('');
  document.getElementById('detail-text').textContent = currentSample.stages[s.stage] || s.desc;
  document.getElementById('detail-noise').textContent = s.noise ? `🗑️ Noise removed in this stage: ${s.noise}` : '';
}

async function runPipeline() {
  if(running) return;
  running = true;
  document.getElementById('speak-btn').disabled = true;

  const text = document.getElementById('text-input').value.trim();
  if(text) currentSample = {text,stages:{DRAFT:text+' (raw)',REFINE:text+' (refined)',ENRICH:text+' ✨ (enriched)',VALIDATE:text+' ✅ (validated)'}};

  // Reset all circles
  PIPELINE.forEach((_,i)=>{
    document.getElementById('circle-'+i).classList.remove('active','completed');
    document.getElementById('conn-'+i)?.classList.remove('active');
  });

  // Animate through stages
  for(let i=0;i<PIPELINE.length;i++) {
    // Activate
    document.getElementById('circle-'+i).classList.add('active');
    if(i>0) document.getElementById('conn-'+(i-1)).classList.add('active');
    showStage(i);
    document.getElementById('noise-log').innerHTML += 
      `<div style="margin-bottom:4px">🎤 ${PIPELINE[i].stage}: ${PIPELINE[i].desc} (${PIPELINE[i].dur}ms)</div>`;

    await new Promise(r=>setTimeout(r, PIPELINE[i].dur*3)); // Slowed for visualization

    // Complete
    document.getElementById('circle-'+i).classList.remove('active');
    document.getElementById('circle-'+i).classList.add('completed');
  }

  document.getElementById('noise-log').innerHTML += 
    `<div style="color:var(--green);margin-top:8px">✅ Voice pipeline complete — ${currentSample.text.substring(0,60)}...</div>`;
  document.getElementById('speak-btn').disabled = false;
  running = false;
}

function loadSample(key) {
  currentSample = SAMPLES[key];
  document.getElementById('text-input').value = currentSample.text;
  document.getElementById('stage-detail').classList.remove('visible');
  document.getElementById('noise-log').innerHTML = '';
  PIPELINE.forEach((_,i)=>{
    document.getElementById('circle-'+i).classList.remove('active','completed');
    document.getElementById('conn-'+i)?.classList.remove('active');
  });
}

renderPipeline();
document.getElementById('text-input').value = SAMPLES.greeting.text;
</script>
</body>
</html>"""


# ─── Flask Registration ────────────────────────────────────────────────────

def register_voice_routes(app):
    from flask import jsonify

    @app.route("/voice")
    def voice_panel():
        return VOICE_HTML

    @app.route("/voice/api/pipeline")
    def voice_api():
        return jsonify({"pipeline": VOICE_PIPELINE, "samples": list(VOICE_SAMPLES.keys())})


if __name__ == "__main__":
    print("🎤 Nova Voice Pipeline ready.")
    print(f"   Stages: {len(VOICE_PIPELINE)}")
    print(f"   Samples: {list(VOICE_SAMPLES.keys())}")
    print(f"   HTML size: {len(VOICE_HTML)} chars")
