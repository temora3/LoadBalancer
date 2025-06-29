import requests
import asyncio
import aiohttp
import time
import matplotlib.pyplot as plt
from collections import defaultdict
import json

class LoadBalancerTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        
    async def send_request(self, session, path="/home"):
        try:
            async with session.get(f"{self.base_url}{path}") as response:
                result = await response.json()
                return result.get("message", "")
        except:
            return "Error"
    
    async def test_load_distribution(self, num_requests=10000, num_servers=3):
        """Test A-1: Launch async requests and measure distribution"""
        print(f"Testing load distribution with {num_requests} requests on {num_servers} servers...")
        
        # Ensure we have the right number of servers
        self._set_server_count(num_servers)
        
        server_counts = defaultdict(int)
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.send_request(session) for _ in range(num_requests)]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                if "Hello from Server:" in response:
                    server_id = response.split("Hello from Server: ")[1]
                    server_counts[server_id] += 1
        
        return dict(server_counts)
    
    def _set_server_count(self, target_count):
        """Adjust server count to target"""
        current = requests.get(f"{self.base_url}/rep").json()
        current_count = current["message"]["N"]
        
        if current_count < target_count:
            # Add servers
            add_count = target_count - current_count
            requests.post(f"{self.base_url}/add", json={"n": add_count})
        elif current_count > target_count:
            # Remove servers
            remove_count = current_count - target_count
            requests.delete(f"{self.base_url}/rm", json={"n": remove_count})
        
        time.sleep(5)  # Wait for changes to take effect
    
    async def test_scalability(self, num_requests=10000):
        """Test A-2: Test scalability with different server counts"""
        results = {}
        
        for n in range(2, 7):
            print(f"Testing with {n} servers...")
            distribution = await self.test_load_distribution(num_requests, n)
            
            if distribution:
                avg_load = num_requests / len(distribution)
                results[n] = avg_load
            
            time.sleep(2)
        
        return results
    
    def test_endpoints(self):
        """Test A-3: Test all endpoints"""
        print("Testing all endpoints...")
        
        # Test /rep
        print("Testing /rep endpoint:")
        response = requests.get(f"{self.base_url}/rep")
        print(f"Status: {response.status_code}, Response: {response.json()}")
        
        # Test /add
        print("\nTesting /add endpoint:")
        response = requests.post(f"{self.base_url}/add", json={"n": 2, "hostnames": ["TestServer1", "TestServer2"]})
        print(f"Status: {response.status_code}, Response: {response.json()}")
        
        # Test /rm
        print("\nTesting /rm endpoint:")
        response = requests.delete(f"{self.base_url}/rm", json={"n": 1})
        print(f"Status: {response.status_code}, Response: {response.json()}")
        
        # Test /home
        print("\nTesting /home endpoint:")
        response = requests.get(f"{self.base_url}/home")
        print(f"Status: {response.status_code}, Response: {response.json()}")
    
    def plot_distribution(self, distribution, title="Load Distribution"):
        """Plot load distribution bar chart"""
        servers = list(distribution.keys())
        counts = list(distribution.values())
        
        plt.figure(figsize=(10, 6))
        plt.bar(servers, counts)
        plt.title(title)
        plt.xlabel("Servers")
        plt.ylabel("Request Count")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def plot_scalability(self, scalability_results, title="Scalability Analysis"):
        """Plot scalability line chart"""
        servers = list(scalability_results.keys())
        avg_loads = list(scalability_results.values())
        
        plt.figure(figsize=(10, 6))
        plt.plot(servers, avg_loads, marker='o')
        plt.title(title)
        plt.xlabel("Number of Servers")
        plt.ylabel("Average Load per Server")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

async def main():
    tester = LoadBalancerTester()
    
    # Test A-1: Load distribution
    print("=" * 50)
    print("Test A-1: Load Distribution Analysis")
    print("=" * 50)
    distribution = await tester.test_load_distribution(10000, 3)
    print("Distribution:", distribution)
    tester.plot_distribution(distribution, "A-1: Load Distribution (N=3, 10000 requests)")
    
    # Test A-2: Scalability
    print("\n" + "=" * 50)
    print("Test A-2: Scalability Analysis")
    print("=" * 50)
    scalability = await tester.test_scalability(10000)
    print("Scalability results:", scalability)
    tester.plot_scalability(scalability, "A-2: Scalability Analysis")
    
    # Test A-3: Endpoint testing
    print("\n" + "=" * 50)
    print("Test A-3: Endpoint Testing")
    print("=" * 50)
    tester.test_endpoints()

if __name__ == "__main__":
    asyncio.run(main())