from flask import Flask, request, jsonify, Response
import requests
import subprocess
import os
import random
import string
import threading
import time
import hashlib
from consistent_hash import ConsistentHash

app = Flask(__name__)


class LoadBalancer:
    def __init__(self):
        self.consistent_hash = ConsistentHash()
        self.servers = {}  # server_id -> container_name mapping
        self.network_name = "net1"
        self.server_image = "server:latest"
        self.lock = threading.Lock()
        self.request_counter = 0  # Add request counter for better distribution
        
        # Initialize with 3 default servers
        self._initialize_servers()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
    
    def _generate_random_name(self):
        """Generate random server name"""
        return 'Server_' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    def _initialize_servers(self):
        """Initialize with 3 default servers"""
        for i in range(1, 4):
            server_name = f"Server_{i}"
            if self._spawn_server(server_name):
                self.servers[server_name] = server_name
                self.consistent_hash.add_server(server_name)
    
    def _spawn_server(self, server_name):
        """Spawn a new server container"""
        try:
            cmd = [
                'sudo', 'docker', 'run',
                '--name', server_name,
                '--network', self.network_name,
                '--network-alias', server_name,
                '-e', f'SERVER_ID={server_name}',
                '-d',
                self.server_image
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error spawning server {server_name}: {e}")
            return False
    
    def _remove_server_container(self, server_name):
        """Remove a server container"""
        try:
            subprocess.run(['sudo', 'docker', 'stop', server_name], 
                         capture_output=True, text=True)
            subprocess.run(['sudo', 'docker', 'rm', server_name], 
                         capture_output=True, text=True)
            return True
        except Exception as e:
            print(f"Error removing server {server_name}: {e}")
            return False
    
    def _health_check_loop(self):
        """Continuously check server health"""
        while True:
            time.sleep(10)  # Check every 10 seconds
            self._check_server_health()
    
    def _check_server_health(self):
        """Check health of all servers and replace failed ones"""
        with self.lock:
            failed_servers = []
            
            for server_name in list(self.servers.keys()):
                try:
                    response = requests.get(f'http://{server_name}:5000/heartbeat', timeout=5)
                    if response.status_code != 200:
                        failed_servers.append(server_name)
                except:
                    failed_servers.append(server_name)
            
            # Replace failed servers
            for server_name in failed_servers:
                print(f"Server {server_name} failed, replacing...")
                self._remove_server_container(server_name)
                self.consistent_hash.remove_server(server_name)
                del self.servers[server_name]
                
                # Spawn replacement
                new_name = self._generate_random_name()
                if self._spawn_server(new_name):
                    self.servers[new_name] = new_name
                    self.consistent_hash.add_server(new_name)
                    print(f"Replaced with {new_name}")
    
    def _generate_request_id(self):
        """Generate a unique request ID for better distribution"""
        with self.lock:
            self.request_counter += 1
            # Combine counter with timestamp and random component for uniqueness
            timestamp = int(time.time() * 1000000)  # microseconds
            random_part = random.randint(1000, 9999)
            return f"{self.request_counter}_{timestamp}_{random_part}"

# Global load balancer instance
lb = LoadBalancer()

# API endpoints for the load balancer
@app.route('/rep', methods=['GET'])
def get_replicas():
    with lb.lock:
        return jsonify({
            "message": {
                "N": len(lb.servers),
                "replicas": list(lb.servers.keys())
            },
            "status": "successful"
        }), 200

@app.route('/add', methods=['POST'])
def add_servers():
    data = request.get_json()
    
    if not data or 'n' not in data:
        return jsonify({
            "message": "<Error> Invalid request format",
            "status": "failure"
        }), 400
    
    n = data['n']
    hostnames = data.get('hostnames', [])
    
    if len(hostnames) > n:
        return jsonify({
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }), 400
    
    with lb.lock:
        new_servers = []
        
        # Use provided hostnames or generate random ones
        for i in range(n):
            if i < len(hostnames):
                server_name = hostnames[i]
            else:
                server_name = lb._generate_random_name()
            
            if lb._spawn_server(server_name):
                lb.servers[server_name] = server_name
                lb.consistent_hash.add_server(server_name)
                new_servers.append(server_name)
        
        return jsonify({
            "message": {
                "N": len(lb.servers),
                "replicas": list(lb.servers.keys())
            },
            "status": "successful"
        }), 200

@app.route('/rm', methods=['DELETE'])
def remove_servers():
    data = request.get_json()
    
    if not data or 'n' not in data:
        return jsonify({
            "message": "<Error> Invalid request format",
            "status": "failure"
        }), 400
    
    n = data['n']
    hostnames = data.get('hostnames', [])
    
    if len(hostnames) > n:
        return jsonify({
            "message": "<Error> Length of hostname list is more than removable instances",
            "status": "failure"
        }), 400
    
    with lb.lock:
        servers_to_remove = []
        
        # Select servers to remove
        if hostnames:
            servers_to_remove.extend(hostnames)
            remaining = n - len(hostnames)
            if remaining > 0:
                available = [s for s in lb.servers.keys() if s not in hostnames]
                servers_to_remove.extend(random.sample(available, min(remaining, len(available))))
        else:
            servers_to_remove = random.sample(list(lb.servers.keys()), min(n, len(lb.servers)))
        
        # Remove servers
        for server_name in servers_to_remove:
            if server_name in lb.servers:
                lb._remove_server_container(server_name)
                lb.consistent_hash.remove_server(server_name)
                del lb.servers[server_name]
        
        return jsonify({
            "message": {
                "N": len(lb.servers),
                "replicas": list(lb.servers.keys())
            },
            "status": "successful"
        }), 200

# Route all requests to the appropriate server based on consistent hashing
@app.route('/<path:path>', methods=['GET'])
def route_request(path):
    # Generate unique request ID for better distribution
    request_id = lb._generate_request_id()
    
    with lb.lock:
        server = lb.consistent_hash.get_server(request_id)
        
        if not server:
            return jsonify({
                "message": "<Error> No servers available",
                "status": "failure"
            }), 500
        
        try:
            response = requests.get(f'http://{server}:5000/{path}', timeout=10)
            return Response(
                response.content,
                status=response.status_code,
                headers=dict(response.headers)
            )
        except:
            return jsonify({
                "message": f"<Error> '/{path}' endpoint does not exist in server replicas",
                "status": "failure"
            }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)