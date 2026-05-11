"""
Arxiv Nova — Flask API Server (PINCEL + HERMES)
API REST + Dashboard para el motor de conocimiento Arxiv-Nova.
Puerto: 9099. Integrado con Dashboard Genesis 4.0 (:9088).
Agentes: PINCEL (visualización), HERMES (notificaciones).
"""

import logging
import json
from datetime import datetime, date
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

from config import config
from db import (
    get_stats, get_top_resonant_papers, get_top_concepts,
    get_emerging_concepts, get_papers_by_date_range
)
from collector import ArxivCollector
from embedder import ArxivEmbedder
from analyzer import ResonanceAnalyzer
from scheduler import scheduler

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Lazy-loaded services
_collector = None
_embedder = None
_analyzer = None


def get_collector():
    global _collector
    if _collector is None:
        _collector = ArxivCollector()
    return _collector


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = ArxivEmbedder()
    return _embedder


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = ResonanceAnalyzer()
    return _analyzer


# ─── API ENDPOINTS ───

@app.route("/api/status")
def api_status():
    """Estado general del motor Arxiv-Nova"""
    stats = get_stats()
    sched_status = scheduler.get_status()
    return jsonify({
        "service": "arxiv-nova",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": stats,
        "scheduler": sched_status,
        "agents": config.NOVA_AGENTS,
        "raph_cycles": scheduler.cycles_completed,
    })


@app.route("/api/papers")
def api_papers():
    """Lista papers (con filtros opcionales)"""
    limit = request.args.get("limit", 50, type=int)
    resonant_only = request.args.get("resonant", "false").lower() == "true"

    if resonant_only:
        papers = get_top_resonant_papers(limit)
    else:
        # Get recent papers
        papers = get_papers_by_date_range(
            date.today() - __import__("datetime").timedelta(days=7),
            date.today(),
        )[:limit]

    return jsonify({
        "count": len(papers),
        "papers": [
            {
                "arxiv_id": p["arxiv_id"],
                "title": p["title"],
                "authors": p.get("authors", ""),
                "resonance_score": p.get("resonance_score", 0),
                "resonance_concepts": p.get("resonance_concepts", ""),
                "nova_tags": p.get("nova_tags", ""),
                "url": p.get("url", ""),
            }
            for p in papers
        ],
    })


@app.route("/api/papers/<arxiv_id>")
def api_paper_detail(arxiv_id):
    """Detalle de un paper por arxiv_id (búsqueda semántica)"""
    embedder = get_embedder()
    results = embedder.search_similar(f"arxiv_id:{arxiv_id}", top_k=1)
    if results:
        return jsonify(results[0])
    return jsonify({"error": "Paper not found"}), 404


@app.route("/api/search")
def api_search():
    """Búsqueda semántica de papers por concepto/texto"""
    query = request.args.get("q", "")
    top_k = request.args.get("top_k", 10, type=int)
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    try:
        embedder = get_embedder()
        results = embedder.search_similar(query, top_k=top_k)
        return jsonify({
            "query": query,
            "results": results,
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        # Fallback: search in PostgreSQL by title/abstract
        from db import get_conn
        import psycopg2.extras
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT arxiv_id, title, abstract, resonance_score 
                       FROM arxiv_papers 
                       WHERE title ILIKE %s OR abstract ILIKE %s 
                       ORDER BY resonance_score DESC LIMIT %s""",
                    (f"%{query}%", f"%{query}%", top_k),
                )
                rows = [dict(r) for r in cur.fetchall()]
        return jsonify({
            "query": query,
            "results": [
                {"arxiv_id": r["arxiv_id"], "title": r["title"],
                 "abstract": (r.get("abstract") or "")[:300],
                 "score": float(r.get("resonance_score", 0))}
                for r in rows
            ],
            "mode": "fallback_sql",
        })


@app.route("/api/concepts")
def api_concepts():
    """Conceptos de resonancia (top + emergentes)"""
    top = get_top_concepts(30)
    emerging = get_emerging_concepts(10)
    return jsonify({
        "top_concepts": [
            {"concept": c["concept"], "weight": c["weight"], "count": c["papers_count"]}
            for c in top
        ],
        "emerging_concepts": [
            {"concept": c["concept"], "weight": c["weight"], "count": c["papers_count"]}
            for c in emerging
        ],
    })


@app.route("/api/collect", methods=["POST"])
def api_collect():
    """Dispara recolección manual (REQUEST del RAPH)"""
    max_results = request.json.get("max_results", 50) if request.is_json else 50
    collector = get_collector()
    stats = collector.collect_and_store(max_results=max_results)
    return jsonify({
        "status": "ok",
        "phase": "REQUEST",
        "stats": stats,
    })


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Dispara análisis de resonancia manual (ASSESS del RAPH)"""
    limit = request.json.get("limit", 30) if request.is_json else 30
    analyzer = get_analyzer()
    result = analyzer.analyze_papers(limit=limit)
    return jsonify({
        "status": "ok",
        "phase": "ASSESS",
        "result": result,
    })


@app.route("/api/embed", methods=["POST"])
def api_embed():
    """Dispara indexación de embeddings manual (HANDLE del RAPH)"""
    limit = request.json.get("limit", 30) if request.is_json else 30
    embedder = get_embedder()
    result = embedder.index_papers(limit=limit)
    return jsonify({
        "status": "ok",
        "phase": "HANDLE",
        "result": result,
    })


@app.route("/api/raph", methods=["POST"])
def api_raph_cycle():
    """Dispara un ciclo RAPH completo manual"""
    result = scheduler.trigger_manual_cycle()
    return jsonify({
        "status": "ok",
        "result": result,
    })


@app.route("/api/report")
def api_report():
    """Reporte completo de resonancia"""
    analyzer = get_analyzer()
    report = analyzer.get_resonance_report()
    return jsonify(report)


# ─── DASHBOARD HTML ───

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arxiv Nova — Knowledge Engine</title>
    <style>
        :root {
            --bg: #0a0a1a;
            --card: #12122a;
            --accent: #7c3aed;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --green: #10b981;
            --gold: #f59e0b;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { 
            background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif;
            min-height: 100vh;
            background-image: radial-gradient(ellipse at top, #1a1040 0%, var(--bg) 70%);
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        header {
            text-align: center; padding: 3rem 0 2rem;
            border-bottom: 1px solid rgba(124,58,237,0.3);
            margin-bottom: 2rem;
        }
        header h1 { font-size: 2.5rem; background: linear-gradient(135deg, #7c3aed, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        header p { color: var(--muted); margin-top: 0.5rem; font-size: 1.1rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card {
            background: var(--card); border-radius: 16px; padding: 1.5rem;
            border: 1px solid rgba(124,58,237,0.2);
            transition: all 0.3s;
        }
        .card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card h3 { color: var(--accent); margin-bottom: 1rem; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-value { font-size: 2.5rem; font-weight: 700; color: var(--green); }
        .stat-label { color: var(--muted); font-size: 0.9rem; }
        .phase-indicator { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
        .phase-REQUEST { background: rgba(59,130,246,0.2); color: #60a5fa; }
        .phase-ASSESS { background: rgba(139,92,246,0.2); color: #a78bfa; }
        .phase-PLAN { background: rgba(245,158,11,0.2); color: #fbbf24; }
        .phase-HANDLE { background: rgba(16,185,129,0.2); color: #34d399; }
        .phase-idle { background: rgba(148,163,184,0.2); color: #94a3b8; }
        .concept-tag {
            display: inline-block; padding: 0.3rem 0.7rem; margin: 0.2rem;
            border-radius: 20px; font-size: 0.85rem;
            background: rgba(124,58,237,0.15); color: #c4b5fd;
        }
        .concept-tag.hot { background: rgba(245,158,11,0.2); color: #fbbf24; }
        .paper-row {
            padding: 0.75rem; border-bottom: 1px solid rgba(124,58,237,0.1);
            transition: background 0.2s;
        }
        .paper-row:hover { background: rgba(124,58,237,0.05); }
        .paper-title { font-weight: 600; }
        .paper-meta { font-size: 0.85rem; color: var(--muted); }
        .resonance-bar {
            height: 4px; background: rgba(124,58,237,0.2); border-radius: 2px; margin-top: 0.5rem;
        }
        .resonance-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.5s; }
        .btn {
            display: inline-block; padding: 0.5rem 1.5rem; border-radius: 25px;
            border: 1px solid var(--accent); color: var(--accent); cursor: pointer;
            background: transparent; font-size: 0.9rem; transition: all 0.3s;
            text-decoration: none;
        }
        .btn:hover { background: var(--accent); color: white; }
        .btn-primary { background: var(--accent); color: white; }
        .btn-primary:hover { background: #6d28d9; }
        .actions { display: flex; gap: 1rem; margin: 1.5rem 0; flex-wrap: wrap; }
        #toast {
            position: fixed; bottom: 2rem; right: 2rem;
            background: var(--accent); color: white; padding: 1rem 2rem;
            border-radius: 12px; display: none; z-index: 1000;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 Arxiv Nova Knowledge Engine</h1>
            <p>Recolección • Embeddings • Resonancia • Enjambre</p>
            <p style="font-size:0.85rem;color:var(--muted);margin-top:0.5rem">
                Bucle RAPH cada {{ interval }}h • Agentes: EXPLORADOR, MEMORIA, ORÁCULO, MAESTRO, PINCEL
            </p>
        </header>

        <div class="actions">
            <button class="btn btn-primary" onclick="triggerRAPH()">🔄 Ejecutar Ciclo RAPH</button>
            <button class="btn" onclick="collectPapers()">📥 Recolectar Papers</button>
            <button class="btn" onclick="analyzePapers()">🔮 Analizar Resonancia</button>
            <button class="btn" onclick="embedPapers()">🧠 Indexar Embeddings</button>
            <button class="btn" onclick="location.reload()">↻ Refresh</button>
        </div>

        <div class="grid" id="stats-grid">
            <div class="card"><h3>Total Papers</h3><div class="stat-value" id="total-papers">—</div><div class="stat-label">recolectados</div></div>
            <div class="card"><h3>Procesados</h3><div class="stat-value" id="processed-papers">—</div><div class="stat-label">con embeddings</div></div>
            <div class="card"><h3>Resonancia Media</h3><div class="stat-value" id="avg-resonance">—</div><div class="stat-label">score promedio</div></div>
            <div class="card"><h3>Estado RAPH</h3><div class="stat-value" style="font-size:1.5rem"><span class="phase-indicator" id="raph-phase">idle</span></div><div class="stat-label" id="raph-cycles">ciclos: —</div></div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>🔮 Top Conceptos Resonantes</h3>
                <div id="top-concepts">Cargando...</div>
            </div>
            <div class="card">
                <h3>📄 Papers Recientes</h3>
                <div id="recent-papers" style="max-height:400px;overflow-y:auto">Cargando...</div>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        const API = '/api';

        async function fetchJSON(url) {
            const r = await fetch(url);
            return r.json();
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg; t.style.display = 'block';
            setTimeout(() => t.style.display = 'none', 3000);
        }

        async function loadDashboard() {
            try {
                const [status, concepts, papers] = await Promise.all([
                    fetchJSON(API + '/status'),
                    fetchJSON(API + '/concepts'),
                    fetchJSON(API + '/papers?limit=15'),
                ]);

                document.getElementById('total-papers').textContent = status.database.total_papers;
                document.getElementById('processed-papers').textContent = status.database.processed;
                document.getElementById('avg-resonance').textContent = status.database.avg_resonance.toFixed(3);
                document.getElementById('raph-cycles').textContent = 'ciclos: ' + status.raph_cycles;
                
                const phase = status.scheduler.current_phase || 'idle';
                const phaseEl = document.getElementById('raph-phase');
                phaseEl.textContent = phase;
                phaseEl.className = 'phase-indicator phase-' + phase;

                // Top concepts
                const conceptsDiv = document.getElementById('top-concepts');
                conceptsDiv.innerHTML = (concepts.top_concepts || []).slice(0, 12).map(c => {
                    const isHot = c.weight > 0.8;
                    return `<span class="concept-tag${isHot ? ' hot' : ''}">${c.concept} <small>(${c.count})</small></span>`;
                }).join('') || '<span style="color:var(--muted)">No hay conceptos aún</span>';

                // Recent papers
                const papersDiv = document.getElementById('recent-papers');
                papersDiv.innerHTML = (papers.papers || []).map(p => {
                    const score = (p.resonance_score || 0) * 100;
                    return `<div class="paper-row">
                        <div class="paper-title">${p.title}</div>
                        <div class="paper-meta">${p.authors?.substring(0,80) || ''} • ${p.arxiv_id}</div>
                        <div class="resonance-bar"><div class="resonance-fill" style="width:${score}%"></div></div>
                    </div>`;
                }).join('') || '<span style="color:var(--muted)">No hay papers aún</span>';

            } catch(e) {
                console.error(e);
            }
        }

        async function triggerRAPH() {
            showToast('🔄 Ejecutando ciclo RAPH...');
            const r = await fetch(API + '/raph', {method:'POST'});
            const data = await r.json();
            showToast('✅ Ciclo RAPH completado!');
            setTimeout(loadDashboard, 2000);
        }

        async function collectPapers() {
            showToast('📥 Recolectando papers...');
            await fetch(API + '/collect', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({max_results:50})});
            showToast('✅ Papers recolectados!');
            loadDashboard();
        }

        async function analyzePapers() {
            showToast('🔮 Analizando resonancia...');
            await fetch(API + '/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({limit:30})});
            showToast('✅ Análisis completado!');
            loadDashboard();
        }

        async function embedPapers() {
            showToast('🧠 Generando embeddings...');
            await fetch(API + '/embed', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({limit:30})});
            showToast('✅ Embeddings indexados!');
            loadDashboard();
        }

        loadDashboard();
        setInterval(loadDashboard, 30000); // Auto-refresh cada 30s
    </script>
</body>
</html>"""


@app.route("/")
def dashboard():
    """Dashboard principal del motor Arxiv-Nova"""
    return render_template_string(
        DASHBOARD_HTML,
        interval=config.RAPH_INTERVAL_HOURS,
    )


# ─── MAIN ───

def run_server():
    """Arranca el servidor Flask + scheduler en background"""
    logger.info(f"🌐 PINCEL: Starting Arxiv Nova server on port {config.FLASK_PORT}")

    # Start RAPH scheduler in background
    scheduler.start(background=True)

    # Run Flask
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_server()
