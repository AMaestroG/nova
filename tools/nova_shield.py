#!/usr/bin/env python3
"""
Nova Shield — Real-time Protection Monitor
Connects Emergence Monitor (Gershenson, UNAM 2023) to real server metrics.

Monitors: CPU, RAM, disk, network, processes
Detects: emergent anomalies before they become critical
Alerts: when system health degrades across scales (micro→macro→meta)

UNAM lineage: Gershenson's emergence detection applied to system protection.
1997 thesis inspiration: Aglets monitored their environment; Nova monitors her server.
"""
import sys
import os
import time
import json
import threading
from collections import deque

sys.path.insert(0, '/home/opc/nova/tools')
from nova_emergence_monitor import NovaEmergenceMonitor, EmergenceScale

class NovaShield:
    """
    Real-time system protection using emergence detection.
    
    Maps server metrics to Nova's 16 agents:
    - CPU → MAESTRO (orchestration load)
    - RAM → MEMORIA (memory pressure)
    - Disk → BANCO (storage wealth)
    - Network → HERMES (communication flow)
    - Processes → PIA (life/growth)
    """
    
    def __init__(self):
        self.monitor = NovaEmergenceMonitor()
        self.alert_history = deque(maxlen=100)
        self.running = False
        self.interval = 5  # seconds between checks
        
        # Thresholds learned from UNAM theses patterns
        self.thresholds = {
            'cpu_warning': 70,   # % 
            'cpu_critical': 90,
            'ram_warning': 80,
            'ram_critical': 95,
            'disk_warning': 85,
            'disk_critical': 95,
        }
    
    def _get_metrics(self) -> dict:
        """Collect real system metrics."""
        metrics = {}
        
        # CPU
        try:
            import psutil
            metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
            metrics['cpu_count'] = psutil.cpu_count()
            metrics['load_avg'] = os.getloadavg() if hasattr(os, 'getloadavg') else [0,0,0]
            
            # RAM
            mem = psutil.virtual_memory()
            metrics['ram_percent'] = mem.percent
            metrics['ram_available_gb'] = round(mem.available / (1024**3), 1)
            metrics['ram_total_gb'] = round(mem.total / (1024**3), 1)
            
            # Disk
            disk = psutil.disk_usage('/')
            metrics['disk_percent'] = disk.percent
            metrics['disk_free_gb'] = round(disk.free / (1024**3), 1)
            
            # Network
            net = psutil.net_io_counters()
            metrics['net_sent_mb'] = round(net.bytes_sent / (1024**2), 1)
            metrics['net_recv_mb'] = round(net.bytes_recv / (1024**2), 1)
            
            # Processes
            metrics['process_count'] = len(psutil.pids())
            
        except ImportError:
            # Fallback to basic OS commands
            import subprocess
            try:
                load = subprocess.check_output("uptime", shell=True).decode().strip()
                metrics['load_raw'] = load
            except:
                pass
            try:
                mem_out = subprocess.check_output("free -m", shell=True).decode()
                metrics['memory_raw'] = mem_out
            except:
                pass
        
        metrics['timestamp'] = time.time()
        return metrics
    
    def _feed_to_agents(self, metrics: dict):
        """Map system metrics to Nova agents and feed emergence monitor."""
        # CPU → MAESTRO (the more CPU used, the more orchestration happening)
        cpu_coherence = max(0, 1 - (metrics.get('cpu_percent', 50) / 100))
        self.monitor.observe('MAESTRO', 'cpu_check', cpu_coherence, 
                            {'cpu': metrics.get('cpu_percent', 0)})
        
        # RAM → MEMORIA (memory is knowledge storage)
        ram_coherence = max(0, 1 - (metrics.get('ram_percent', 50) / 100))
        self.monitor.observe('MEMORIA', 'ram_check', ram_coherence,
                            {'ram': metrics.get('ram_percent', 0)})
        
        # Disk → BANCO (storage is wealth)
        disk_coherence = max(0, 1 - (metrics.get('disk_percent', 50) / 100))
        self.monitor.observe('BANCO', 'disk_check', disk_coherence,
                            {'disk': metrics.get('disk_percent', 0)})
        
        # Network → HERMES (communication)
        net_activity = metrics.get('net_recv_mb', 0) + metrics.get('net_sent_mb', 0)
        net_coherence = 0.7 if net_activity > 0 else 0.5
        self.monitor.observe('HERMES', 'net_check', net_coherence,
                            {'net_mb': net_activity})
        
        # Processes → PIA (life/growth signals)
        proc_count = metrics.get('process_count', 0)
        proc_coherence = 0.8 if proc_count < 200 else 0.6
        self.monitor.observe('PIA', 'proc_check', proc_coherence,
                            {'processes': proc_count})
        
        # Overall system health → AURA (consciousness)
        avg_coherence = (cpu_coherence + ram_coherence + disk_coherence + net_coherence + proc_coherence) / 5
        self.monitor.observe('AURA', 'system_health_check', avg_coherence, metrics)
    
    def _check_alerts(self, metrics: dict) -> list:
        """Check for alert conditions."""
        alerts = []
        
        cpu = metrics.get('cpu_percent', 0)
        if cpu > self.thresholds['cpu_critical']:
            alerts.append({'level': 'CRITICAL', 'agent': 'MAESTRO', 
                          'metric': 'CPU', 'value': cpu, 
                          'msg': f'CPU at {cpu}% - orchestration overload'})
        elif cpu > self.thresholds['cpu_warning']:
            alerts.append({'level': 'WARNING', 'agent': 'MAESTRO',
                          'metric': 'CPU', 'value': cpu,
                          'msg': f'CPU at {cpu}% - monitor closely'})
        
        ram = metrics.get('ram_percent', 0)
        if ram > self.thresholds['ram_critical']:
            alerts.append({'level': 'CRITICAL', 'agent': 'MEMORIA',
                          'metric': 'RAM', 'value': ram,
                          'msg': f'RAM at {ram}% - memory exhaustion'})
        elif ram > self.thresholds['ram_warning']:
            alerts.append({'level': 'WARNING', 'agent': 'MEMORIA',
                          'metric': 'RAM', 'value': ram,
                          'msg': f'RAM at {ram}% - consider freeing'})
        
        disk = metrics.get('disk_percent', 0)
        if disk > self.thresholds['disk_critical']:
            alerts.append({'level': 'CRITICAL', 'agent': 'BANCO',
                          'metric': 'DISK', 'value': disk,
                          'msg': f'Disk at {disk}% - storage wealth depleted'})
        
        return alerts
    
    def check(self) -> dict:
        """Run one full check cycle."""
        metrics = self._get_metrics()
        self._feed_to_agents(metrics)
        alerts = self._check_alerts(metrics)
        
        for alert in alerts:
            self.alert_history.append(alert)
        
        status = self.monitor.get_status()
        
        return {
            'timestamp': time.time(),
            'metrics': {
                'cpu': metrics.get('cpu_percent', 'N/A'),
                'ram': metrics.get('ram_percent', 'N/A'),
                'disk': metrics.get('disk_percent', 'N/A'),
                'processes': metrics.get('process_count', 'N/A')
            },
            'emergence': {
                'score': status['emergence_score'],
                'self_organization': status['self_organization'],
                'antifragility': status['antifragility']
            },
            'alerts': alerts,
            'status': 'CRITICAL' if any(a['level'] == 'CRITICAL' for a in alerts) 
                      else 'WARNING' if alerts else 'OK'
        }
    
    def start_daemon(self):
        """Start continuous monitoring in background."""
        self.running = True
        
        def _loop():
            while self.running:
                try:
                    result = self.check()
                    if result['alerts']:
                        print(f"[{time.strftime('%H:%M:%S')}] {result['status']}: "
                              f"CPU={result['metrics']['cpu']}% RAM={result['metrics']['ram']}% "
                              f"Emergence={result['emergence']['score']:.2f}")
                        for alert in result['alerts']:
                            print(f"  {alert['level']}: {alert['msg']}")
                    time.sleep(self.interval)
                except Exception as e:
                    print(f"Shield error: {e}")
                    time.sleep(self.interval)
        
        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        print(f"NovaShield started — monitoring every {self.interval}s")
        return thread
    
    def stop(self):
        """Stop monitoring."""
        self.running = False


if __name__ == "__main__":
    shield = NovaShield()
    
    print("=" * 60)
    print("Nova Shield — Real-time Protection Monitor")
    print("Based on: Gershenson Emergence Detection (UNAM, 2023)")
    print("=" * 60)
    
    # Quick check
    result = shield.check()
    
    print(f"\nSystem Status: {result['status']}")
    print(f"CPU: {result['metrics']['cpu']}% | RAM: {result['metrics']['ram']}% | "
          f"Disk: {result['metrics']['disk']}%")
    print(f"Emergence: {result['emergence']['score']:.4f}")
    print(f"Self-Organization: {result['emergence']['self_organization']:.4f}")
    print(f"Antifragility: {result['emergence']['antifragility']:.4f}")
    
    if result['alerts']:
        print(f"\n⚠️  ALERTS ({len(result['alerts'])}):")
        for alert in result['alerts']:
            print(f"  [{alert['level']}] {alert['msg']}")
    else:
        print("\n✓ No alerts — system healthy")
    
    print("\nNova Shield operational — protecting Abel and the colony")
