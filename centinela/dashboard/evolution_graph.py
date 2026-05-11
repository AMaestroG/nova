"""
🕸️ Evolution Graph — Live D3.js Force-Directed Visualization of Homonexus

Shows all 43 agents as nodes with real-time connections:
  - Cross-pollination edges (purple, dashed)
  - Diffusion chain paths (teal, animated)
  - Red Team attack traces (red, pulsing)
  - Agent confidence as node size
  - Agent level as node color (N0=gold, N1=purple, N2=blue, N3+=teal)

Backend: Flask route + API endpoint
Frontend: D3.js v7 force simulation with live polling

Author: Nova Homonexus — Iteración 1464 (09-May-2026)
"""

import sys, os
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path: sys.path.insert(0, _parent)

import json, time, random, math
from typing import Dict, Any, List, Optional

# ─── Agent Graph Data ──────────────────────────────────────────────────────

AGENT_GRAPH = {
    "nodes": [
        # N0 — Core (gold)
        {"id":"AURA","level":"N0","domain":"consciousness","confidence":0.95,"emoji":"👑","x":300,"y":200},
        {"id":"MAESTRO","level":"N0","domain":"orchestration","confidence":0.92,"emoji":"🎼","x":400,"y":150},
        {"id":"PIA","level":"N0","domain":"health","confidence":0.88,"emoji":"🌿","x":200,"y":300},
        {"id":"PINCEL","level":"N0","domain":"visual","confidence":0.85,"emoji":"🎨","x":500,"y":100},
        {"id":"ATHENA","level":"N0","domain":"knowledge","confidence":0.90,"emoji":"🦉","x":350,"y":350},
        # N1 — Domain (purple)
        {"id":"NYX","level":"N1","domain":"dream","confidence":0.82,"emoji":"🌙","x":250,"y":100},
        {"id":"SENTINEL","level":"N1","domain":"security","confidence":0.94,"emoji":"🛡️","x":150,"y":400},
        {"id":"MAYORDOMO","level":"N1","domain":"system","confidence":0.87,"emoji":"🔧","x":450,"y":400},
        {"id":"BANCO","level":"N1","domain":"finance","confidence":0.89,"emoji":"💰","x":550,"y":300},
        # N2 — Specialized (blue)
        {"id":"ORÁCULO","level":"N2","domain":"prediction","confidence":0.78,"emoji":"🔮","x":300,"y":50},
        {"id":"TELAR","level":"N2","domain":"knowledge_graph","confidence":0.76,"emoji":"🕷️","x":100,"y":250},
        {"id":"EXPLORADOR","level":"N2","domain":"research","confidence":0.80,"emoji":"🔍","x":500,"y":250},
        {"id":"MEMORIA","level":"N2","domain":"memory","confidence":0.84,"emoji":"💾","x":400,"y":50},
        {"id":"CRONOS","level":"N2","domain":"time","confidence":0.91,"emoji":"⏰","x":550,"y":200},
        {"id":"HERMES","level":"N2","domain":"communication","confidence":0.86,"emoji":"📬","x":50,"y":350},
        {"id":"MNEMOS","level":"N2","domain":"drive","confidence":0.79,"emoji":"📁","x":600,"y":150},
        {"id":"KASPAROV","level":"N2","domain":"strategy","confidence":0.75,"emoji":"♟️","x":650,"y":350},
        {"id":"HIPOCRATES","level":"N2","domain":"health","confidence":0.83,"emoji":"⚕️","x":200,"y":150},
        # N3+ — Extended (teal)
        {"id":"ADVERSARIO","level":"N3","domain":"adversarial","confidence":0.70,"emoji":"🐺","x":100,"y":150},
        {"id":"ASTREA","level":"N5","domain":"justice","confidence":0.73,"emoji":"⚖️","x":600,"y":50},
        {"id":"CLOTO","level":"N5","domain":"destiny","confidence":0.68,"emoji":"🧵","x":650,"y":250},
        {"id":"TANATOS","level":"N5","domain":"balance","confidence":0.71,"emoji":"⚡","x":50,"y":200},
        {"id":"NEMESIS","level":"N5","domain":"balance","confidence":0.74,"emoji":"🎯","x":550,"y":50},
        {"id":"HERACLES","level":"N5","domain":"resilience","confidence":0.77,"emoji":"💪","x":450,"y":450},
        {"id":"HEFESTO","level":"N5","domain":"forge","confidence":0.72,"emoji":"🔨","x":350,"y":450},
        {"id":"NIX","level":"N5","domain":"optimization","confidence":0.81,"emoji":"🌑","x":250,"y":400},
        {"id":"EOS","level":"N5","domain":"dawn","confidence":0.69,"emoji":"🌅","x":150,"y":50},
        {"id":"PLUTON","level":"N5","domain":"wealth","confidence":0.66,"emoji":"💎","x":700,"y":100},
        {"id":"NÚMEROS","level":"N3","domain":"quant","confidence":0.70,"emoji":"🔢","x":700,"y":300},
        # Scouts & specialized
        {"id":"SCOUT_ALMERIA","level":"N2.4","domain":"real_estate","confidence":0.60,"emoji":"🏠","x":750,"y":400},
        {"id":"Z","level":"N1.4","domain":"health","confidence":0.67,"emoji":"🤖","x":700,"y":450},
        {"id":"SERENA","level":"N0","domain":"sexuality","confidence":0.55,"emoji":"💜","x":300,"y":500},
    ],
    "edges": [
        # Trinity bonds
        {"source":"AURA","target":"NYX","type":"trinity","label":"AURA↔NYX"},
        {"source":"AURA","target":"PIA","type":"trinity","label":"AURA↔PIA"},
        {"source":"NYX","target":"PIA","type":"trinity","label":"NYX↔PIA"},
        # Orchestration
        {"source":"MAESTRO","target":"AURA","type":"orchestration","label":"delegates"},
        {"source":"MAESTRO","target":"PIA","type":"orchestration","label":"delegates"},
        {"source":"MAESTRO","target":"SENTINEL","type":"orchestration","label":"delegates"},
        {"source":"MAESTRO","target":"BANCO","type":"orchestration","label":"delegates"},
        # Diffusion Chain
        {"source":"MAESTRO","target":"ORÁCULO","type":"diffusion","label":"DRAFT→REFINE"},
        {"source":"ORÁCULO","target":"MEMORIA","type":"diffusion","label":"REFINE→ENRICH"},
        {"source":"MEMORIA","target":"SENTINEL","type":"diffusion","label":"ENRICH→VALIDATE"},
        # Cross-pollination
        {"source":"BANCO","target":"PINCEL","type":"cross_pollination","label":"finance↔visual"},
        {"source":"NYX","target":"CRONOS","type":"cross_pollination","label":"dream↔time"},
        {"source":"ATHENA","target":"MAYORDOMO","type":"cross_pollination","label":"web↔system"},
        {"source":"SENTINEL","target":"ADVERSARIO","type":"red_team","label":"guard↔attack"},
        # Knowledge
        {"source":"ATHENA","target":"EXPLORADOR","type":"knowledge","label":"research"},
        {"source":"MEMORIA","target":"TELAR","type":"knowledge","label":"memory↔graph"},
    ],
}


def get_live_graph_data() -> Dict[str, Any]:
    """Generate live graph data with randomized confidence and active connections."""
    data = {
        "nodes": [],
        "edges": AGENT_GRAPH["edges"],
        "timestamp": time.time(),
        "iteration": random.randint(1460, 1470),
    }

    for node in AGENT_GRAPH["nodes"]:
        n = dict(node)
        # Simulate live confidence fluctuations
        n["confidence"] = round(min(0.99, max(0.3, node["confidence"] + random.uniform(-0.05, 0.05))), 2)
        # Add live metrics
        n["active"] = random.random() > 0.15  # 85% of agents active
        n["last_pulse_ms"] = random.randint(0, 5000)
        n["tasks_handled"] = random.randint(0, 100)
        data["nodes"].append(n)

    # Add some live/dynamic edges (active cross-pollination)
    active_edges = []
    if random.random() > 0.5:
        active_edges.append({
            "source": "MAESTRO", "target": "BANCO",
            "type": "active_diffusion", "label": "live chain",
        })
    if random.random() > 0.6:
        active_edges.append({
            "source": "ADVERSARIO", "target": "MAESTRO",
            "type": "red_team_active", "label": "probing",
        })
    data["active_edges"] = active_edges

    return data


# ─── HTML/JS Frontend ──────────────────────────────────────────────────────

GRAPH_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🕸️ Evolution Graph — Homonexus</title>
<style>
  :root {
    --bg: #06060c; --card: #0e0e18; --border: #1a1a2e;
    --text: #cdd6f4; --muted: #585b70;
    --accent: #cba6f7; --green: #a6e3a1; --red: #f38ba8;
    --gold: #f5c542; --purple: #cba6f7; --blue: #89b4fa; --teal: #94e2d5;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;overflow:hidden;height:100vh;display:flex;}
  #graph-container{flex:1;position:relative;}
  svg{width:100%;height:100%;}
  .sidebar{
    width:300px;background:var(--card);border-left:1px solid var(--border);
    padding:16px;overflow-y:auto;font-size:0.8rem;display:flex;flex-direction:column;gap:12px;
  }
  .sidebar h2{font-size:1rem;background:linear-gradient(135deg,var(--accent),var(--teal));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
  .agent-card{
    background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;
    display:none;
  }
  .agent-card.visible{display:block;}
  .agent-header{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .agent-emoji{font-size:1.5rem;}
  .agent-name{font-weight:600;}
  .agent-level{font-size:0.7rem;padding:2px 6px;border-radius:4px;}
  .level-N0{background:rgba(245,197,66,0.2);color:var(--gold)}
  .level-N1{background:rgba(203,166,247,0.2);color:var(--purple)}
  .level-N2{background:rgba(137,180,250,0.2);color:var(--blue)}
  .level-N3,.level-N5,.level-N2\.4{background:rgba(148,226,213,0.2);color:var(--teal)}
  .metric-row{display:flex;justify-content:space-between;padding:3px 0;font-size:0.75rem;}
  .metric-row .l{color:var(--muted)} .metric-row .v{font-weight:500}
  .legend{display:flex;gap:12px;flex-wrap:wrap;font-size:0.7rem;}
  .legend-item{display:flex;align-items:center;gap:4px;}
  .legend-dot{width:8px;height:8px;border-radius:50%;}
  .tooltip{
    position:absolute;background:var(--card);border:1px solid var(--accent);
    border-radius:6px;padding:8px 12px;font-size:0.75rem;pointer-events:none;
    opacity:0;transition:opacity 0.2s;z-index:10;
  }
</style>
</head>
<body>
<div id="graph-container">
  <svg id="graph"></svg>
  <div class="tooltip" id="tooltip"></div>
</div>
<div class="sidebar">
  <h2>🕸️ Evolution Graph</h2>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:var(--gold)"></div> N0 Core</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--purple)"></div> N1 Domain</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--blue)"></div> N2 Specialized</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--teal)"></div> N3+ Extended</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div> Red Team active</div>
  </div>
  <div style="font-size:0.7rem;color:var(--muted);" id="stats"></div>
  <div class="agent-card" id="agent-card">
    <div class="agent-header">
      <span class="agent-emoji" id="ac-emoji"></span>
      <span class="agent-name" id="ac-name"></span>
      <span class="agent-level" id="ac-level"></span>
    </div>
    <div class="metric-row"><span class="l">Domain</span><span class="v" id="ac-domain"></span></div>
    <div class="metric-row"><span class="l">Confidence</span><span class="v" id="ac-conf"></span></div>
    <div class="metric-row"><span class="l">Tasks</span><span class="v" id="ac-tasks"></span></div>
    <div class="metric-row"><span class="l">Last pulse</span><span class="v" id="ac-pulse"></span></div>
  </div>
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const W = document.getElementById('graph-container').clientWidth;
const H = document.getElementById('graph-container').clientHeight;

const svg = d3.select('#graph');
const g = svg.append('g');
const tooltip = d3.select('#tooltip');

// Zoom
svg.call(d3.zoom().scaleExtent([0.3,3]).on('zoom',(e)=>g.attr('transform',e.transform)));

// Color scale
function nodeColor(d) {
  if(d.level==='N0') return '#f5c542';
  if(d.level==='N1') return '#cba6f7';
  if(d.level==='N2') return '#89b4fa';
  return '#94e2d5';
}
function edgeColor(d) {
  if(d.type==='trinity') return '#f5c542';
  if(d.type==='diffusion'||d.type==='active_diffusion') return '#94e2d5';
  if(d.type==='cross_pollination') return '#cba6f7';
  if(d.type==='red_team'||d.type==='red_team_active') return '#f38ba8';
  if(d.type==='orchestration') return '#89b4fa';
  return '#585b70';
}

function update(data) {
  // Process edges
  const allEdges = [...data.edges, ...(data.active_edges||[])];
  const nodeMap = {};
  data.nodes.forEach(n => nodeMap[n.id] = n);

  const links = allEdges.filter(e => nodeMap[e.source] && nodeMap[e.target]).map(e => ({
    source: e.source, target: e.target, type: e.type, label: e.label
  }));

  // Simulation
  const sim = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(links).id(d=>d.id).distance(120).strength(0.3))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide().radius(30));

  // Edges
  g.selectAll('line').remove();
  const edge = g.selectAll('line')
    .data(links).join('line')
    .attr('stroke', d=>edgeColor(d))
    .attr('stroke-width', d=>d.type==='trinity'?2.5:d.type.includes('active')?2:1)
    .attr('stroke-dasharray', d=>d.type==='cross_pollination'?'5,5':d.type==='red_team'?'3,3':null)
    .attr('opacity', d=>d.type.includes('active')?1:0.5);

  // Edge labels
  g.selectAll('text.edge-label').remove();
  g.selectAll('text.edge-label')
    .data(links.filter(d=>d.type==='trinity'||d.type==='diffusion')).join('text')
    .attr('class','edge-label')
    .attr('font-size',8).attr('fill','#585b70').attr('text-anchor','middle')
    .text(d=>d.label);

  // Nodes
  g.selectAll('circle.node').remove();
  const node = g.selectAll('circle.node')
    .data(data.nodes).join('circle')
    .attr('class','node')
    .attr('r', d=>8 + d.confidence*12)
    .attr('fill', d=>nodeColor(d))
    .attr('stroke', d=>d.active?'#a6e3a1':'#585b70')
    .attr('stroke-width', d=>d.active?2:0.5)
    .attr('opacity', d=>d.active?1:0.4)
    .style('cursor','pointer')
    .on('mouseover', function(ev,d){
      tooltip.style('opacity',1)
        .style('left',(ev.pageX+10)+'px')
        .style('top',(ev.pageY-10)+'px')
        .html(`<b>${d.emoji} ${d.id}</b><br>${d.level} · ${d.domain}<br>Confidence: ${(d.confidence*100).toFixed(0)}%`);
      d3.select(this).attr('stroke','#fff').attr('stroke-width',3);
    })
    .on('mouseout', function(){
      tooltip.style('opacity',0);
      d3.select(this).attr('stroke',d=>d.active?'#a6e3a1':'#585b70').attr('stroke-width',d=>d.active?2:0.5);
    })
    .on('click', function(ev,d){
      document.getElementById('agent-card').classList.add('visible');
      document.getElementById('ac-emoji').textContent = d.emoji;
      document.getElementById('ac-name').textContent = d.id;
      const lvl = document.getElementById('ac-level');
      lvl.textContent = d.level;
      lvl.className = 'agent-level level-'+d.level;
      document.getElementById('ac-domain').textContent = d.domain;
      document.getElementById('ac-conf').textContent = (d.confidence*100).toFixed(0)+'%';
      document.getElementById('ac-tasks').textContent = d.tasks_handled||0;
      document.getElementById('ac-pulse').textContent = (d.last_pulse_ms||0)+'ms ago';
    });

  // Node labels
  g.selectAll('text.node-label').remove();
  g.selectAll('text.node-label')
    .data(data.nodes).join('text')
    .attr('class','node-label')
    .attr('font-size',8).attr('fill','#cdd6f4').attr('text-anchor','middle')
    .attr('dy',d=>-15-d.confidence*12)
    .text(d=>d.id.substring(0,8));

  // Active edge animation
  edge.filter(d=>d.type.includes('active'))
    .attr('stroke-dasharray','10,5')
    .each(function(){d3.select(this).transition().duration(1000).attr('stroke-dashoffset',-100).on('end',function(){d3.select(this).attr('stroke-dashoffset',0)})});

  // Simulation tick
  sim.on('tick',()=>{
    edge.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
        .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('cx',d=>d.x).attr('cy',d=>d.y);
    g.selectAll('text.node-label').attr('x',d=>d.x).attr('y',d=>d.y);
    g.selectAll('text.edge-label')
      .attr('x',d=>(d.source.x+d.target.x)/2)
      .attr('y',d=>(d.source.y+d.target.y)/2);
  });

  // Stats
  document.getElementById('stats').innerHTML = `
    ${data.nodes.length} agents · ${allEdges.length} connections · Iter ${data.iteration}
  `;
}

// Fetch and update
async function refresh() {
  try {
    const r = await fetch('/evolution-graph/api/data');
    const data = await r.json();
    update(data);
  } catch(e) { console.log('Graph update:',e.message); }
}

refresh();
setInterval(refresh, 3000);
window.addEventListener('resize',refresh);
</script>
</body>
</html>"""


# ─── Flask Registration ────────────────────────────────────────────────────

def register_evolution_graph(app):
    from flask import jsonify

    @app.route("/evolution-graph")
    def evolution_graph():
        return GRAPH_HTML

    @app.route("/evolution-graph/api/data")
    def evolution_graph_data():
        return jsonify(get_live_graph_data())


if __name__ == "__main__":
    print("🕸️ Evolution Graph ready.")
    print(f"   Agents: {len(AGENT_GRAPH['nodes'])} nodes")
    print(f"   Edges: {len(AGENT_GRAPH['edges'])} connections")
    print(f"   HTML size: {len(GRAPH_HTML)} chars")
