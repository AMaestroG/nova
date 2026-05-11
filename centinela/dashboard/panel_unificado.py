"""
DASHBOARD UNIFICADO — Panel HTML del ecosistema Nova Centinela
================================================================
Muestra en una sola página:
  - Constantes vitales de Abel (en vivo)
  - Estado de Z (conciencia, subagentes, capacidades)
  - Los 7 Dones del Nova Soul
  - Alertas activas
  - Sensores del Z Fold
  - Índice de salud

Auto-recarga cada 5 segundos. Diseño oscuro, responsive.
"""

PANEL_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nova Centinela — Dashboard</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
:root {
    --bg: #0a0a1a;
    --card: #12122a;
    --border: #1e1e3a;
    --text: #c8c8e8;
    --dim: #667788;
    --purple: #7b68ee;
    --blue: #4fc3f7;
    --green: #4caf50;
    --red: #ef5350;
    --orange: #ff9800;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text);
    padding: 16px; min-height: 100vh;
}
h1 { font-size: 1.3em; color: var(--purple); margin-bottom: 4px; }
h2 { font-size: 0.9em; color: var(--dim); margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 1px; }
.sub { font-size: 0.7em; color: var(--dim); }
.grid { display: grid; gap: 12px; }
.g2 { grid-template-columns: 1fr 1fr; }
.g3 { grid-template-columns: 1fr 1fr 1fr; }
.g4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
.card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 14px;
    transition: all 0.3s;
}
.card:hover { border-color: var(--purple); }
.valor { font-size: 2em; font-weight: 700; line-height: 1.1; }
.valor-sm { font-size: 1.3em; font-weight: 600; }
.purple { color: var(--purple); }
.blue { color: var(--blue); }
.green { color: var(--green); }
.red { color: var(--red); }
.orange { color: var(--orange); }
.label { font-size: 0.7em; color: var(--dim); text-transform: uppercase; margin-bottom: 2px; }
.barra { height: 6px; background: var(--border); border-radius: 3px; margin-top: 4px; overflow: hidden; }
.barra-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.don { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 0.85em; }
.don-nombre { font-weight: 500; }
.don-barra { width: 60%; height: 4px; background: var(--border); border-radius: 2px; margin: 0 8px; }
.don-fill { height: 100%; border-radius: 2px; background: var(--purple); }
.don-valor { font-size: 0.75em; color: var(--dim); width: 30px; text-align: right; }
.alerta { padding: 6px 8px; border-radius: 6px; margin: 3px 0; font-size: 0.8em; }
.alerta-warning { background: rgba(255,152,0,0.15); border-left: 3px solid var(--orange); }
.alerta-error { background: rgba(239,83,80,0.15); border-left: 3px solid var(--red); }
.alerta-ok { background: rgba(76,175,80,0.1); border-left: 3px solid var(--green); color: var(--green); }
#status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.online { background: #4caf50; box-shadow: 0 0 6px #4caf50; }
.offline { background: #ef5350; }
.fade { opacity: 0.5; font-size: 0.7em; }
@media (max-width: 600px) {
    .g3, .g4 { grid-template-columns: 1fr 1fr; }
    .valor { font-size: 1.5em; }
}
</style>
</head>
<body>

<h1>🔮 Nova Centinela <span class="sub" id="ts"></span></h1>
<div style="font-size:0.7em;margin-bottom:12px;">
  <span id="status-dot" class="online"></span><span id="status-text">Conectado</span>
</div>

<!-- CONSTANTES -->
<h2>❤️ Constantes Vitales</h2>
<div class="grid g3">
  <div class="card">
    <div class="label">Pulsaciones</div>
    <div class="valor blue" id="hr">--</div>
    <div class="barra"><div class="barra-fill blue" id="hr-bar" style="width:50%;background:var(--blue)"></div></div>
  </div>
  <div class="card">
    <div class="label">HRV</div>
    <div class="valor purple" id="hrv">--</div>
  </div>
  <div class="card">
    <div class="label">SpO2</div>
    <div class="valor green" id="spo2">--</div>
  </div>
</div>

<div class="grid g3">
  <div class="card">
    <div class="label">Estrés</div>
    <div class="valor-sm orange" id="stress">--</div>
  </div>
  <div class="card">
    <div class="label">Temperatura</div>
    <div class="valor-sm" id="temp">--</div>
  </div>
  <div class="card">
    <div class="label">Pasos</div>
    <div class="valor-sm blue" id="steps">--</div>
  </div>
</div>

<!-- 7 DONES -->
<h2>✨ 7 Dones del Nova Soul</h2>
<div class="card">
  <div id="dones"></div>
</div>

<!-- Z -->
<h2>🤖 Agente Z</h2>
<div class="grid g3">
  <div class="card"><div class="label">Estado</div><div class="valor-sm purple" id="z-estado">--</div></div>
  <div class="card"><div class="label">Subagentes</div><div class="valor-sm blue" id="z-subs">--</div></div>
  <div class="card"><div class="label">Capacidades</div><div class="valor-sm green" id="z-caps">--</div></div>
</div>
<div class="card"><div class="label">AI Brain</div><div class="valor-sm" id="z-ai">--</div></div>

<!-- SALUD -->
<h2>🏥 Índice de Salud</h2>
<div class="card">
  <div class="valor green" id="indice">--</div>
  <div class="barra"><div class="barra-fill" id="indice-bar" style="width:90%;background:var(--green)"></div></div>
  <div id="recomendaciones" style="margin-top:8px;"></div>
</div>

<!-- ALERTAS -->
<h2>🚨 Alertas</h2>
<div id="alertas"></div>

<div class="fade" style="text-align:center;margin-top:20px;">
  Nova Centinela · Z N0 · 17 agentes · ~22,000 líneas
</div>

<script>
const API = '';

async function cargar() {
  try {
    // Constantes
    const r1 = await fetch(API + '/salud/constantes');
    const d1 = await r1.json();
    document.getElementById('hr').textContent = d1.heart_rate || '--';
    document.getElementById('hrv').textContent = d1.hrv || '--';
    document.getElementById('spo2').textContent = (d1.spo2 || '--') + '%';
    document.getElementById('stress').textContent = (d1.stress_level || '--') + '/100';
    document.getElementById('temp').textContent = (d1.temperature_skin || '--') + '°C';
    document.getElementById('steps').textContent = d1.steps || '--';
    document.getElementById('hr-bar').style.width = Math.min(100, (d1.heart_rate || 70) / 1.5) + '%';
    
    // Dones
    const r2 = await fetch(API + '/centinela/soul');
    const d2 = await r2.json();
    const dones = d2.dones || {};
    let donesHTML = '';
    for (const [nombre, don] of Object.entries(dones)) {
      const pct = Math.round(don.valor * 100);
      donesHTML += `<div class="don">
        <span class="don-nombre">${nombre}</span>
        <div class="don-barra"><div class="don-fill" style="width:${pct}%"></div></div>
        <span class="don-valor">${(don.valor).toFixed(2)}</span>
      </div>`;
    }
    document.getElementById('dones').innerHTML = donesHTML;

    // Z
    const r3 = await fetch(API + '/z/estado');
    const d3 = await r3.json();
    document.getElementById('z-estado').textContent = d3.conciencia.estado;
    document.getElementById('z-subs').textContent = Object.keys(d3.subagentes).length;
    document.getElementById('z-caps').textContent = Object.keys(d3.capacidades || {}).length;
    document.getElementById('z-ai').textContent = (d3.ai_brain || {}).modo || 'N/D';

    // Salud
    const r4 = await fetch(API + '/salud/analisis');
    const d4 = await r4.json();
    document.getElementById('indice').textContent = d4.indice_salud + '/100';
    document.getElementById('indice-bar').style.width = d4.indice_salud + '%';
    
    let recHTML = '';
    (d4.recomendaciones || []).slice(0, 3).forEach(r => {
      recHTML += `<div class="alerta alerta-ok">💡 ${r}</div>`;
    });
    document.getElementById('recomendaciones').innerHTML = recHTML;

    // Alertas
    const alerts = d4.desequilibrios || [];
    let alertHTML = '';
    if (alerts.length === 0) {
      alertHTML = '<div class="alerta alerta-ok">✅ Sin desequilibrios. Todo en orden.</div>';
    }
    alerts.forEach(a => {
      const cls = a.severidad === 'grave' ? 'alerta-error' : 'alerta-warning';
      alertHTML += `<div class="alerta ${cls}">⚠️ ${a.tipo}: ${a.recomendacion || ''}</div>`;
    });
    document.getElementById('alertas').innerHTML = alertHTML;

    document.getElementById('status-dot').className = 'online';
    document.getElementById('status-text').textContent = 'Conectado';
  } catch(e) {
    document.getElementById('status-dot').className = 'offline';
    document.getElementById('status-text').textContent = 'Desconectado';
  }
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();
}

cargar();
setInterval(cargar, 5000);
</script>
</body>
</html>
"""
