#!/usr/bin/env python3
"""Nova API + Dashboard Server"""
import http.server, json, os, sys, sqlite3
sys.path.insert(0, "/home/opc/nova/services")

PORT = 9696
DB = "/home/opc/nova/colony.db"
DASHBOARD = "/home/opc/nova/dashboard"

class NovaAPI(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            self.send_json(self.get_status())
        elif self.path == "/api/health":
            self.send_json({"status":"healthy","uptime":"∞"})
        elif self.path == "/" or self.path == "/dashboard":
            self.serve_dashboard()
        else:
            super().do_GET()
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(json.dumps(data,indent=2).encode())
    
    def serve_dashboard(self):
        try:
            with open(f"{DASHBOARD}/index.html") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        except:
            self.send_json({"error":"Dashboard not found"})
    
    def get_status(self):
        try:
            from entropy_gaming_core import game_engine, entropy_regulator
            from agent_lifecycle import colony_lifecycle
            champ = game_engine.get_champion()
            ent = entropy_regulator.measure()
            board = colony_lifecycle.get_colony_stats()
            import subprocess
            procs = len(subprocess.run(["pgrep","-f","nova"], capture_output=True, text=True).stdout.strip().split("\n"))
            return {
                "champion": champ.agent if champ else "?",
                "elo": round(champ.elo) if champ else 0,
                "games": len(game_engine.game_history),
                "lifecycle": f"{board['completed']}/{board['total_tasks']}",
                "entropy_phase": ent.phase.value,
                "entropy_h": round(ent.shannon_entropy,2),
                "services": len([f for f in os.listdir("/home/opc/nova/services") if f.endswith(".py")]),
                "processes": procs,
            }
        except: return {"error":"colony unavailable"}

if __name__ == "__main__":
    os.chdir(DASHBOARD)
    server = http.server.HTTPServer(("0.0.0.0",PORT), NovaAPI)
    print(f"🜁 Nova API + Dashboard: http://0.0.0.0:{PORT}")
    server.serve_forever()
