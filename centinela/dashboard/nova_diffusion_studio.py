"""
🎛️ Nova Diffusion Studio — Frontend HTML Panel

Rich interactive visualization of the diffusion pipeline.
Shows each stage in real-time via WebSocket.

Served at /studio on Centinela (:9088)
"""

STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎛️ Nova Diffusion Studio</title>
<style>
  :root {
    --bg: #06060c;
    --card: #0e0e18;
    --border: #1a1a2e;
    --text: #cdd6f4;
    --muted: #585b70;
    --accent: #cba6f7;
    --green: #a6e3a1;
    --yellow: #f9e2af;
    --red: #f38ba8;
    --blue: #89b4fa;
    --teal: #94e2d5;
    --orange: #fab387;
    --surface: #11111b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  .header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
  }
  .header h1 {
    font-size: 1.3rem;
    background: linear-gradient(135deg, var(--accent), var(--teal));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .header-status {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.8rem;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dot-live { background: var(--green); animation: pulse 2s infinite; }
  .dot-idle { background: var(--muted); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
  .input-area {
    padding: 20px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .input-row {
    display: flex;
    gap: 10px;
  }
  .input-row input {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.2s;
  }
  .input-row input:focus {
    border-color: var(--accent);
  }
  .input-row button {
    background: linear-gradient(135deg, var(--accent), var(--teal));
    color: var(--bg);
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    font-size: 1rem;
    transition: opacity 0.2s;
  }
  .input-row button:hover { opacity: 0.9; }
  .input-row button:disabled { opacity: 0.4; cursor: not-allowed; }

  .pipeline {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .stage-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    transition: all 0.3s;
    opacity: 0.4;
  }
  .stage-card.active {
    border-color: var(--accent);
    opacity: 1;
    box-shadow: 0 0 20px rgba(203,166,247,0.1);
  }
  .stage-card.completed {
    border-color: var(--green);
    opacity: 0.8;
  }
  .stage-card.error {
    border-color: var(--red);
  }
  .stage-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .stage-icon {
    font-size: 1.4rem;
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 6px;
  }
  .stage-title {
    font-weight: 600;
    font-size: 0.95rem;
    flex: 1;
  }
  .stage-badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 500;
  }
  .badge-pending { background: rgba(108,112,134,0.2); color: var(--muted); }
  .badge-active { background: rgba(203,166,247,0.2); color: var(--accent); }
  .badge-done { background: rgba(166,227,161,0.2); color: var(--green); }
  .badge-error { background: rgba(243,139,168,0.2); color: var(--red); }
  .stage-detail {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 4px;
  }
  .stage-progress {
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    margin-top: 8px;
    overflow: hidden;
  }
  .stage-progress-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.3s;
    width: 0%;
  }

  .result-area {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 20px;
    max-height: 250px;
    overflow-y: auto;
  }
  .result-area h3 {
    font-size: 0.9rem;
    color: var(--accent);
    margin-bottom: 10px;
  }
  .result-content {
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
  }
  .metrics {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .metric-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 0.8rem;
  }
  .metric-box .label { color: var(--muted); font-size: 0.7rem; }
  .metric-box .value { font-weight: 600; }

  .sidebar {
    width: 280px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    padding: 16px;
    overflow-y: auto;
    font-size: 0.75rem;
  }
  .sidebar h3 {
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 12px;
  }
  .event-log {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    line-height: 1.8;
  }
  .event-log .ts { color: var(--blue); }
  .event-log .stage { color: var(--accent); }
  .event-log .info { color: var(--muted); }
  .event-log .err { color: var(--red); }
</style>
</head>
<body>

<div class="header">
  <h1>🎛️ Nova Diffusion Studio</h1>
  <div class="header-status">
    <span id="ws-status"><span class="dot dot-idle"></span> disconnected</span>
    <span id="task-count" style="color:var(--muted);">0 tasks</span>
  </div>
</div>

<div class="input-area">
  <div class="input-row">
    <input type="text" id="query-input" placeholder="Escribe tu pregunta y observa el pipeline en tiempo real..."
           onkeydown="if(event.key==='Enter')execute()">
    <button id="execute-btn" onclick="execute()">▶ Ejecutar</button>
  </div>
  <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">
    <button onclick="setQuery('What is the state of AI safety research?')" style="font-size:0.7rem;padding:4px 10px;background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:4px;cursor:pointer;">AI Safety</button>
    <button onclick="setQuery('Explain quantum computing in simple terms')" style="font-size:0.7rem;padding:4px 10px;background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:4px;cursor:pointer;">Quantum</button>
    <button onclick="setQuery('Generate a creative poem about neural networks')" style="font-size:0.7rem;padding:4px 10px;background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:4px;cursor:pointer;">Poem</button>
    <button onclick="setQuery('How do I optimize Python code for performance?')" style="font-size:0.7rem;padding:4px 10px;background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:4px;cursor:pointer;">Python</button>
  </div>
</div>

<div class="main">
  <div class="pipeline" id="pipeline"></div>
  <div class="sidebar">
    <h3>📜 Event Log</h3>
    <div class="event-log" id="event-log"></div>
  </div>
</div>

<div class="result-area" id="result-area" style="display:none;">
  <h3>📤 Response</h3>
  <div id="metrics-row" class="metrics"></div>
  <div class="result-content" id="result-content"></div>
</div>

<script>
// ─── State ──────────────────────────────────────────────────────────────
const STAGES = [
  { id: 'routing', icon: '🔄', title: 'Self-Supervised Routing', agent: 'Statistical Model' },
  { id: 'cross_pollination', icon: '🌱', title: 'Cross-Pollination Engine', agent: 'Cross-Domain Router' },
  { id: 'diffusion', icon: '🌀', title: 'Diffusion Reasoning Chain', agent: 'MAESTRO→ORÁCULO→MEMORIA→SENTINEL' },
  { id: 'uncertainty', icon: '🔬', title: 'Uncertainty Gate', agent: 'SENTINEL' },
  { id: 'quality', icon: '🧹', title: 'Data Quality Flywheel', agent: 'ORÁCULO+MEMORIA' },
];
let currentTask = null;
let ws = null;
let taskCount = 0;

// ─── WebSocket ──────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = proto + '//' + location.host + '/ws/studio';
  ws = new WebSocket(url);

  ws.onopen = () => {
    document.getElementById('ws-status').innerHTML = '<span class="dot dot-live"></span> connected';
    addEvent('system', 'WebSocket connected');
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.event === 'stage_start') {
      activateStage(msg.data.stage, msg.data.agent, msg.data.detail);
      addEvent(msg.data.stage, '▶ Started: ' + msg.data.detail);
    } else if (msg.event === 'stage_progress') {
      updateProgress(msg.data.stage, msg.data.progress);
    } else if (msg.event === 'stage_complete') {
      completeStage(msg.data.stage, msg.data.preview);
      addEvent(msg.data.stage, '✓ Done: ' + (msg.data.preview || '').substring(0,60));
    } else if (msg.event === 'pipeline_complete') {
      showResult(msg.data);
      addEvent('pipeline', '✅ Complete — confidence: ' + msg.data.confidence.toFixed(2));
      taskCount++;
      document.getElementById('task-count').textContent = taskCount + ' tasks';
      document.getElementById('execute-btn').disabled = false;
    } else if (msg.event === 'pipeline_error') {
      errorStage('unknown', msg.data.error);
      addEvent('error', '❌ ' + msg.data.error, true);
      document.getElementById('execute-btn').disabled = false;
    }
  };

  ws.onclose = () => {
    document.getElementById('ws-status').innerHTML = '<span class="dot dot-idle"></span> disconnected';
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => {
    document.getElementById('ws-status').innerHTML = '<span class="dot dot-idle"></span> error';
  };
}

// ─── Pipeline Rendering ─────────────────────────────────────────────────
function renderStages() {
  const container = document.getElementById('pipeline');
  container.innerHTML = STAGES.map((s, i) => `
    <div class="stage-card" id="stage-${s.id}">
      <div class="stage-header">
        <div class="stage-icon">${s.icon}</div>
        <div class="stage-title">${s.title}</div>
        <span class="stage-badge badge-pending" id="badge-${s.id}">pending</span>
      </div>
      <div class="stage-detail" id="detail-${s.id}">${s.agent}</div>
      <div class="stage-progress">
        <div class="stage-progress-bar" id="progress-${s.id}"></div>
      </div>
    </div>
  `).join('');
}

function activateStage(id, agent, detail) {
  const card = document.getElementById('stage-' + id);
  const badge = document.getElementById('badge-' + id);
  const detailEl = document.getElementById('detail-' + id);
  if (card) {
    card.classList.remove('completed', 'error');
    card.classList.add('active');
  }
  if (badge) { badge.textContent = 'active'; badge.className = 'stage-badge badge-active'; }
  if (detailEl) detailEl.textContent = detail || agent;
}

function updateProgress(id, progress) {
  const bar = document.getElementById('progress-' + id);
  if (bar) bar.style.width = (progress * 100) + '%';
}

function completeStage(id, preview) {
  const card = document.getElementById('stage-' + id);
  const badge = document.getElementById('badge-' + id);
  const detailEl = document.getElementById('detail-' + id);
  const bar = document.getElementById('progress-' + id);
  if (card) { card.classList.remove('active'); card.classList.add('completed'); }
  if (badge) { badge.textContent = 'done'; badge.className = 'stage-badge badge-done'; }
  if (detailEl && preview) detailEl.textContent = preview;
  if (bar) bar.style.width = '100%';
}

function errorStage(id, error) {
  const card = document.getElementById('stage-' + id);
  if (card) { card.classList.remove('active'); card.classList.add('error'); }
}

// ─── Result ─────────────────────────────────────────────────────────────
function showResult(data) {
  const area = document.getElementById('result-area');
  area.style.display = 'block';
  document.getElementById('result-content').textContent = data.response || '';
  document.getElementById('metrics-row').innerHTML = `
    <div class="metric-box"><div class="label">Confidence</div><div class="value">${(data.confidence*100).toFixed(0)}%</div></div>
    <div class="metric-box"><div class="label">Time</div><div class="value">${data.total_elapsed_ms.toFixed(0)}ms</div></div>
    <div class="metric-box"><div class="label">Stages</div><div class="value">${data.stages_completed || 5}</div></div>
    <div class="metric-box"><div class="label">Agent</div><div class="value">${data.routing?.agent || 'N/A'}</div></div>
  `;
}

// ─── Event Log ──────────────────────────────────────────────────────────
function addEvent(stage, msg, isError) {
  const log = document.getElementById('event-log');
  const now = new Date().toLocaleTimeString();
  const cls = isError ? 'err' : (stage === 'system' ? 'info' : 'stage');
  log.innerHTML += `<div><span class="ts">[${now}]</span> <span class="${cls}">${stage}</span> ${msg}</div>`;
  log.scrollTop = log.scrollHeight;
}

// ─── Execute ────────────────────────────────────────────────────────────
function execute() {
  const input = document.getElementById('query-input');
  const query = input.value.trim();
  if (!query) return;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'execute', query: query }));
    document.getElementById('execute-btn').disabled = true;
    resetPipeline();
  } else {
    addEvent('error', 'WebSocket not connected — cannot execute', true);
  }
}

function setQuery(text) {
  document.getElementById('query-input').value = text;
}

function resetPipeline() {
  document.getElementById('result-area').style.display = 'none';
  renderStages();
}

// ─── Init ───────────────────────────────────────────────────────────────
renderStages();
connectWS();
addEvent('system', 'Nova Diffusion Studio loaded — 5-stage pipeline ready');
</script>

</body>
</html>"""


# ─── Flask Registration ────────────────────────────────────────────────────

def register_studio_routes(app, sock=None):
    """
    Register Studio routes on Flask app with WebSocket support.

    Usage in centinela/app.py:
        from centinela.dashboard.nova_diffusion_studio import register_studio_routes
        register_studio_routes(app, sock)
    """
    from flask import jsonify, request
    import queue
    import json
    import threading

    @app.route("/studio")
    def studio_panel():
        return STUDIO_HTML

    @app.route("/studio/api/status")
    def studio_api_status():
        try:
            from servicios.comun.neural.studio_pipeline import get_studio_engine
            engine = get_studio_engine()
            return jsonify({"ok": True, **engine.get_stats()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    @app.route("/studio/api/execute", methods=["POST"])
    def studio_api_execute():
        """HTTP fallback for execution (when WebSocket not available)."""
        data = request.get_json() or {}
        query = data.get("query", "")
        if not query:
            return jsonify({"ok": False, "error": "No query provided"})

        try:
            from servicios.comun.neural.studio_pipeline import execute_with_studio
            result = execute_with_studio(query)
            return jsonify({"ok": True, **result})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    # WebSocket endpoint
    if sock:
        @sock.route("/ws/studio")
        def studio_ws(ws):
            """WebSocket for real-time pipeline streaming."""
            q = queue.Queue(maxsize=100)

            while True:
                try:
                    data = ws.receive(timeout=30)
                    if data is None:
                        break

                    msg = json.loads(data)
                    if msg.get("action") == "execute":
                        query = msg.get("query", "")
                        if query:
                            # Execute in background thread
                            def run():
                                try:
                                    from servicios.comun.neural.studio_pipeline import execute_with_studio
                                    execute_with_studio(query, ws_queue=q)
                                except Exception as e:
                                    q.put_nowait(json.dumps({
                                        "event": "pipeline_error",
                                        "data": {"error": str(e)},
                                        "timestamp": __import__('time').time(),
                                    }))

                            threading.Thread(target=run, daemon=True).start()

                            # Stream events from queue to WebSocket
                            while True:
                                try:
                                    event = q.get(timeout=60)
                                    ws.send(event)
                                except queue.Empty:
                                    break

                except Exception:
                    break
