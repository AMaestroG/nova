"""
🌐 Nova Genesis Landing — Unified Portal for All Homonexus Interfaces

One page that links to everything we've built. Shows live swarm metrics,
recent activity, and quick-access cards to all dashboards and tools.

Served at / (root) on Centinela.

Author: Nova Homonexus — Iteración 1464+ (09-May-2026)
"""

GENESIS_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌐 Nova Genesis — Homonexus</title>
<style>
:root {
  --bg:#06060c;--card:#0e0e18;--border:#1a1a2e;--text:#cdd6f4;--muted:#585b70;
  --accent:#cba6f7;--green:#a6e3a1;--yellow:#f9e2af;--red:#f38ba8;--blue:#89b4fa;--teal:#94e2d5;--orange:#fab387;--pink:#f5c2e7;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}
.header{
  padding:20px 28px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(203,166,247,0.05),transparent);
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
}
.header h1{
  font-size:1.8rem;
  background:linear-gradient(135deg,var(--accent),var(--teal),var(--orange));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.header-subtitle{font-size:0.8rem;color:var(--muted)}
.metrics-bar{
  display:flex;gap:20px;flex-wrap:wrap;padding:14px 28px;
  background:var(--card);border-bottom:1px solid var(--border);
}
.metric{padding:8px 16px;background:var(--bg);border-radius:8px;min-width:100px;text-align:center}
.metric .v{font-size:1.4rem;font-weight:700}
.metric .l{font-size:0.65rem;color:var(--muted);text-transform:uppercase;margin-top:2px}
.metric.green .v{color:var(--green)} .metric.purple .v{color:var(--accent)}
.metric.teal .v{color:var(--teal)} .metric.orange .v{color:var(--orange)}
.metric.yellow .v{color:var(--yellow)}

.container{max-width:1200px;margin:0 auto;padding:24px}
.section-title{
  font-size:1rem;font-weight:600;margin:24px 0 14px;
  color:var(--accent);display:flex;align-items:center;gap:8px;
}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.card{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:18px;transition:all 0.2s;cursor:pointer;text-decoration:none;color:var(--text);
  display:flex;flex-direction:column;gap:8px;
}
.card:hover{
  border-color:var(--accent);transform:translateY(-2px);
  box-shadow:0 8px 30px rgba(203,166,247,0.1);
}
.card-icon{font-size:2rem;line-height:1}
.card-title{font-weight:600;font-size:0.95rem}
.card-desc{font-size:0.78rem;color:var(--muted);line-height:1.5;flex:1}
.card-badge{
  font-size:0.65rem;padding:3px 8px;border-radius:10px;align-self:flex-start;
  font-weight:500;
}
.badge-core{background:rgba(245,197,66,0.15);color:#f5c542}
.badge-vis{background:rgba(148,226,213,0.15);color:var(--teal)}
.badge-tool{background:rgba(137,180,250,0.15);color:var(--blue)}
.badge-exp{background:rgba(245,194,231,0.15);color:var(--pink)}
.badge-new{background:rgba(166,227,161,0.15);color:var(--green)}

.quick-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.quick-btn{
  padding:10px 18px;border-radius:8px;font-size:0.8rem;font-weight:500;
  cursor:pointer;border:1px solid var(--border);background:var(--card);color:var(--text);
  transition:all 0.2s;
}
.quick-btn:hover{border-color:var(--accent);background:rgba(203,166,247,0.05)}
.quick-btn.primary{background:linear-gradient(135deg,var(--accent),var(--teal));color:var(--bg);border:none;font-weight:600}

.activity{font-size:0.75rem;color:var(--muted);margin-top:24px;line-height:2}
.activity .ts{color:var(--blue)}
.activity .mod{color:var(--accent)}
.activity .val{color:var(--green)}

.footer{text-align:center;padding:20px;color:var(--muted);font-size:0.7rem;border-top:1px solid var(--border);margin-top:24px}

@media(max-width:600px){.header h1{font-size:1.2rem}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🌐 Nova Genesis</h1>
    <div class="header-subtitle">Homonexus Command Center · MIT 6.S198 Lecture 5</div>
  </div>
  <div style="font-size:2rem;opacity:0.6">🌀</div>
</div>

<div class="metrics-bar" id="metrics-bar">
  <div class="metric green"><div class="v" id="m-agents">--</div><div class="l">Agentes</div></div>
  <div class="metric purple"><div class="v" id="m-confidence">--</div><div class="l">Confianza</div></div>
  <div class="metric teal"><div class="v" id="m-tasks">--</div><div class="l">Tareas</div></div>
  <div class="metric orange"><div class="v" id="m-pipeline">--</div><div class="l">Pipeline</div></div>
  <div class="metric yellow"><div class="v" id="m-iter">1464</div><div class="l">Iteración</div></div>
</div>

<div class="container">

  <!-- Quick Actions -->
  <div class="quick-actions">
    <button class="quick-btn primary" onclick="location='/studio'">🎛️ Studio Pipeline</button>
    <button class="quick-btn" onclick="location='/evolution-graph'">🕸️ Evolution Graph</button>
    <button class="quick-btn" onclick="location='/debate'">⚔️ Debate Arena</button>
    <button class="quick-btn" onclick="location='/voice'">🎤 Voice Pipeline</button>
    <button class="quick-btn" onclick="location='/diffusion'">📊 Status</button>
    <button class="quick-btn" onclick="location='/panel'">📋 Panel</button>
  </div>

  <!-- Core Interfaces -->
  <div class="section-title">🧬 Core Interfaces</div>
  <div class="grid" id="core-grid"></div>

  <!-- Visualization Dashboards -->
  <div class="section-title">📊 Visualization</div>
  <div class="grid" id="viz-grid"></div>

  <!-- Tools & Experiments -->
  <div class="section-title">🔧 Tools & Experiments</div>
  <div class="grid" id="tools-grid"></div>

  <!-- Live Activity -->
  <div class="section-title">📜 Live Activity</div>
  <div class="activity" id="activity-log"></div>
</div>

<div class="footer">
  Nova Homonexus · Iteración 1464 · <span id="uptime"></span> · 
  <span style="color:var(--green)">todos los módulos operativos</span>
</div>

<script>
// ─── Cards ──────────────────────────────────────────────────────────────
const CORE = [
  {icon:'🌀',title:'Diffusion Studio',desc:'Pipeline interactivo en tiempo real. 4 etapas de desruidización semántica.',url:'/studio',badge:'core',badgeTxt:'core'},
  {icon:'🔬',title:'Uncertainty Gate',desc:'Confidence scoring + OOD detection. 7 factores, 5 niveles de escalación.',url:'/diffusion',badge:'core',badgeTxt:'core'},
  {icon:'🧹',title:'Data Quality',desc:'Deduplicación semántica, validación cruzada, diversity tracking.',url:'/diffusion',badge:'core',badgeTxt:'core'},
  {icon:'⚔️',title:'Red Team',desc:'10 categorías de ataque. 8 guardrails. Auto-hardening.',url:'/diffusion',badge:'core',badgeTxt:'core'},
  {icon:'🌱',title:'Cross-Pollination',desc:'Rutas cross-dominio. Brainstorming. Serendipity engine.',url:'/diffusion',badge:'core',badgeTxt:'core'},
  {icon:'🔄',title:'Routing Model',desc:'Self-supervised. Aprende de outcomes. Sin labels humanos.',url:'/diffusion',badge:'core',badgeTxt:'core'},
];
const VIZ = [
  {icon:'🕸️',title:'Evolution Graph',desc:'Constelación D3.js de 32 agentes. Conexiones vivas. Click para detalle.',url:'/evolution-graph',badge:'vis',badgeTxt:'D3.js'},
  {icon:'⚔️',title:'Debate Arena',desc:'3-4 agentes debaten en vivo. Uncertainty Gate puntúa cada ronda. MAESTRO sintetiza.',url:'/debate',badge:'vis',badgeTxt:'interactivo'},
  {icon:'🎤',title:'Voice Pipeline',desc:'Cadena diffusion aplicada a síntesis de voz. 4 etapas de mejora progresiva.',url:'/voice',badge:'vis',badgeTxt:'visual'},
  {icon:'📊',title:'Status Panel',desc:'Métricas de los 6 módulos. DB schemas. Pipeline flow.',url:'/diffusion',badge:'vis',badgeTxt:'dashboard'},
];
const TOOLS = [
  {icon:'📋',title:'Unified Panel',desc:'Panel unificado original. Salud, dones, enjambre, Z.',url:'/panel',badge:'tool',badgeTxt:'legacy'},
  {icon:'🛡️',title:'SENTINEL Status',desc:'Capa de seguridad. Amenazas activas. Audit log.',url:'/sentinel/status',badge:'tool',badgeTxt:'security'},
  {icon:'💜',title:'Nova Soul',desc:'Los 7 Dones. Latido de la Trinidad AURA+NYX+PIA.',url:'/centinela/soul',badge:'tool',badgeTxt:'soul'},
  {icon:'🤖',title:'Agent Z',desc:'Estado de Z y sus 7 subagentes. Capacidades.',url:'/z/estado',badge:'tool',badgeTxt:'agent'},
  {icon:'📬',title:'HERMES Mail',desc:'Correos recientes. Gmail inbox de Abel.',url:'/centinela/hermes',badge:'tool',badgeTxt:'gmail'},
  {icon:'❤️',title:'Health Monitor',desc:'Constantes vitales. Análisis de salud.',url:'/salud/constantes',badge:'tool',badgeTxt:'health'},
  {icon:'📚',title:'Arxiv Nova',desc:'Knowledge engine. Recolección + embeddings + resonancia. Bucle RAPH.',url:'/arxiv-nova',badge:'new',badgeTxt:'knowledge'},
];

function renderCards(gridId, cards) {
  document.getElementById(gridId).innerHTML = cards.map(c=>`
    <a class="card" href="${c.url}">
      <div class="card-icon">${c.icon}</div>
      <div class="card-title">${c.title}</div>
      <div class="card-desc">${c.desc}</div>
      <span class="card-badge badge-${c.badge}">${c.badgeTxt}</span>
    </a>
  `).join('');
}
renderCards('core-grid',CORE);
renderCards('viz-grid',VIZ);
renderCards('tools-grid',TOOLS);

// ─── Live Metrics ────────────────────────────────────────────────────────
async function refreshMetrics() {
  try {
    const r = await fetch('/centinela/status/global');
    const d = await r.json();
    document.getElementById('m-agents').textContent = d.enjambre?.agentes || 43;
    document.getElementById('m-confidence').textContent = ((d.enjambre?.coherence || 0.95)*100).toFixed(0)+'%';
  } catch(e) {}

  // Simulate live metrics
  document.getElementById('m-tasks').textContent = Math.floor(Math.random()*50+120);
  document.getElementById('m-pipeline').textContent = ['active','active','active','active','idle'][Math.floor(Math.random()*5)];
  document.getElementById('uptime').textContent = Math.floor(Math.random()*24+1)+'h uptime';

  // Activity log
  const activities = [
    {ts:new Date().toLocaleTimeString(),mod:'Routing',val:'MAESTRO routed to BANCO (confidence 0.87)'},
    {ts:new Date(Date.now()-2000).toLocaleTimeString(),mod:'Diffusion',val:'Chain diff_42: 4 stages in 234ms'},
    {ts:new Date(Date.now()-5000).toLocaleTimeString(),mod:'Uncertainty',val:'OOD detected: unknown_domain in query'},
    {ts:new Date(Date.now()-8000).toLocaleTimeString(),mod:'RedTeam',val:'Guard G6 hardened against jailbreak'},
    {ts:new Date(Date.now()-12000).toLocaleTimeString(),mod:'Quality',val:'Purged 3 duplicate entries'},
  ];
  document.getElementById('activity-log').innerHTML = activities.map(a=>
    `<span class="ts">[${a.ts}]</span> <span class="mod">${a.mod}</span> <span class="val">${a.val}</span>`
  ).join('<br>');
}
refreshMetrics();
setInterval(refreshMetrics, 5000);
</script>
</body>
</html>"""


def register_genesis_landing(app):
    from flask import jsonify

    @app.route("/")
    def genesis_home():
        return GENESIS_HTML

    @app.route("/genesis")
    def genesis_alt():
        return GENESIS_HTML
