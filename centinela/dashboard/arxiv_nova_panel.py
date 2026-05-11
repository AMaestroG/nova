"""
Arxiv Nova Panel — Dashboard integrado en Genesis 4.0
Panel HTML nativo que consume la API de Arxiv Nova (:9100)
Parte del Enjambre Homonexus — PINCEL + MAESTRO
"""

ARXIV_NOVA_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arxiv Nova — Knowledge Engine</title>
<style>
:root {
  --bg: #0a0a1a; --card: #12122a; --accent: #f59e0b; --accent2: #8b5cf6;
  --text: #e2e8f0; --muted: #94a3b8; --green: #10b981; --red: #ef4444;
  --border: rgba(139,92,246,0.2);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;
  background-image:radial-gradient(ellipse at top,#1a1040 0%,var(--bg) 70%)}
.container{max-width:1300px;margin:0 auto;padding:1.5rem}
header{text-align:center;padding:2rem 0 1.5rem;border-bottom:1px solid var(--border);margin-bottom:1.5rem}
header h1{font-size:2rem;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
header p{color:var(--muted);margin-top:.3rem;font-size:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin-bottom:1.5rem}
.card{background:var(--card);border-radius:14px;padding:1.2rem;border:1px solid var(--border)}
.card h3{color:var(--accent);margin-bottom:.8rem;font-size:.85rem;text-transform:uppercase;letter-spacing:.05em}
.stat-big{font-size:2rem;font-weight:700;color:var(--green)}
.stat-sm{color:var(--muted);font-size:.8rem}
.phase{display:inline-block;padding:.2rem .7rem;border-radius:20px;font-size:.75rem;font-weight:600}
.phase-REQUEST{background:rgba(59,130,246,.2);color:#60a5fa}
.phase-ASSESS{background:rgba(139,92,246,.2);color:#a78bfa}
.phase-PLAN{background:rgba(245,158,11,.2);color:#fbbf24}
.phase-HANDLE{background:rgba(16,185,129,.2);color:#34d399}
.phase-idle{background:rgba(148,163,184,.2);color:#94a3b8}
.btn{display:inline-block;padding:.4rem 1.2rem;border-radius:20px;border:1px solid var(--accent);color:var(--accent);cursor:pointer;background:transparent;font-size:.8rem;transition:all .2s;margin:.2rem;text-decoration:none}
.btn:hover{background:var(--accent);color:#000}
.btn-primary{background:var(--accent);color:#000;font-weight:600}
.btn-primary:hover{background:#d97706}
.actions{display:flex;gap:.5rem;margin:1rem 0;flex-wrap:wrap}
.concept-tag{display:inline-block;padding:.25rem .6rem;margin:.15rem;border-radius:15px;font-size:.8rem;background:rgba(139,92,246,.15);color:#c4b5fd}
.concept-tag.hot{background:rgba(245,158,11,.2);color:#fbbf24}
.paper-row{padding:.6rem;border-bottom:1px solid rgba(139,92,246,.08);cursor:pointer;transition:background .15s}
.paper-row:hover{background:rgba(139,92,246,.05)}
.paper-title{font-weight:600;font-size:.9rem}
.paper-meta{font-size:.75rem;color:var(--muted);margin-top:.2rem}
.resonance-bar{height:3px;background:rgba(139,92,246,.15);border-radius:2px;margin-top:.3rem}
.resonance-fill{height:100%;background:var(--accent);border-radius:2px;transition:width .5s}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
@media(max-width:800px){.row2{grid-template-columns:1fr}}
.scroll-box{max-height:450px;overflow-y:auto}
#toast{position:fixed;bottom:1.5rem;right:1.5rem;background:var(--accent2);color:#fff;padding:.8rem 1.5rem;border-radius:10px;display:none;z-index:1000;font-weight:600}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📚 Arxiv Nova Knowledge Engine</h1>
    <p>Bucle RAPH · 100 papers · 20 conceptos semilla · Enjambre Homonexus</p>
  </header>

  <div class="actions">
    <button class="btn btn-primary" onclick="triggerRAPH()">🔄 Ciclo RAPH Completo</button>
    <button class="btn" onclick="collectPapers()">📥 Recolectar (R)</button>
    <button class="btn" onclick="analyzePapers()">🔮 Analizar (A)</button>
    <button class="btn" onclick="embedPapers()">🧠 Indexar (H)</button>
    <button class="btn" onclick="loadAll()">↻ Refresh</button>
  </div>

  <div class="grid" id="stats-grid">
    <div class="card"><h3>Total Papers</h3><div class="stat-big" id="st-total">—</div><div class="stat-sm">recolectados</div></div>
    <div class="card"><h3>Procesados</h3><div class="stat-big" id="st-proc">—</div><div class="stat-sm">con embeddings</div></div>
    <div class="card"><h3>Resonancia Media</h3><div class="stat-big" id="st-res">—</div><div class="stat-sm">score coseno</div></div>
    <div class="card"><h3>RAPH</h3><div class="stat-big" style="font-size:1.3rem"><span class="phase phase-idle" id="st-phase">idle</span></div><div class="stat-sm" id="st-cycles">ciclos: —</div></div>
  </div>

  <div class="row2">
    <div class="card">
      <h3>🔮 Conceptos Resonantes</h3>
      <div id="concepts-box">Cargando...</div>
    </div>
    <div class="card">
      <h3>📄 Papers Recientes</h3>
      <div class="scroll-box" id="papers-box">Cargando...</div>
    </div>
  </div>
</div>
<div id="toast"></div>

<script>
const ARXIV_API = '/arxiv-nova/api';  // Via Genesis proxy

function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',3000)}

async function loadAll(){
  try{
    const[status,concepts,papers]=await Promise.all([
      fetch(ARXIV_API+'/status').then(r=>r.json()).catch(()=>null),
      fetch(ARXIV_API+'/concepts').then(r=>r.json()).catch(()=>null),
      fetch(ARXIV_API+'/papers?limit=12').then(r=>r.json()).catch(()=>null)
    ]);
    if(status){
      document.getElementById('st-total').textContent=status.database?.total_papers||'—';
      document.getElementById('st-proc').textContent=status.database?.processed||'—';
      document.getElementById('st-res').textContent=(status.database?.avg_resonance||0).toFixed(3);
      document.getElementById('st-cycles').textContent='ciclos: '+(status.raph_cycles||0);
      const ph=status.scheduler?.current_phase||'idle';
      const pe=document.getElementById('st-phase');
      pe.textContent=ph;pe.className='phase phase-'+ph;
    }
    if(concepts){
      document.getElementById('concepts-box').innerHTML=(concepts.top_concepts||[]).slice(0,14).map(c=>
        `<span class="concept-tag${c.weight>0.5?' hot':''}">${c.concept} <small>(${c.count})</small></span>`
      ).join('')||'<span class="stat-sm">Sin conceptos aún</span>';
    }
    if(papers){
      document.getElementById('papers-box').innerHTML=(papers.papers||[]).map(p=>{
        const score=(p.resonance_score||0)*100;
        return `<div class="paper-row" onclick="window.open('${p.url||'#'}','_blank')" title="Click para abrir en arxiv">
          <div class="paper-title">${p.title}</div>
          <div class="paper-meta">${(p.authors||'').substring(0,70)} · ${p.arxiv_id}</div>
          <div class="resonance-bar"><div class="resonance-fill" style="width:${score}%"></div></div>
        </div>`;
      }).join('')||'<span class="stat-sm">Sin papers aún</span>';
    }
  }catch(e){console.error(e)}
}

async function triggerRAPH(){toast('🔄 Ejecutando ciclo RAPH...');await fetch(ARXIV_API+'/raph',{method:'POST'});toast('✅ RAPH completado!');setTimeout(loadAll,2000)}
async function collectPapers(){toast('📥 Recolectando...');await fetch(ARXIV_API+'/collect',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"max_results":50}'});toast('✅ Recolectado!');loadAll()}
async function analyzePapers(){toast('🔮 Analizando...');await fetch(ARXIV_API+'/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"limit":30}'});toast('✅ Analizado!');loadAll()}
async function embedPapers(){toast('🧠 Indexando...');await fetch(ARXIV_API+'/embed',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"limit":30}'});toast('✅ Indexado!');loadAll()}

loadAll();
setInterval(loadAll,60000);
</script>
</body>
</html>"""


def register_arxiv_nova(app):
    """Registra la ruta del panel Arxiv Nova en la app Flask"""
    @app.route("/arxiv-nova")
    def arxiv_nova_panel():
        return ARXIV_NOVA_HTML

    @app.route("/arxiv-nova/api/proxy/<path:subpath>")
    def arxiv_nova_proxy(subpath):
        """Proxy a la API de Arxiv Nova (:9100) para evitar CORS"""
        import requests as req
        from flask import request, jsonify
        target = f"http://localhost:9100/api/{subpath}"
        try:
            if request.method == 'POST':
                r = req.post(target, json=request.get_json(silent=True) or {}, timeout=10)
            else:
                r = req.get(target, params=request.args, timeout=10)
            return jsonify(r.json())
        except Exception as e:
            return jsonify({"error": str(e)}), 502
