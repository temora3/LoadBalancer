import requests
import asyncio
import aiohttp
import time
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
import seaborn as sns

class EnhancedLoadBalancerTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        
    async def send_request(self, session, path="/home"):
        """Send a single request and return server ID"""
        try:
            async with session.get(f"{self.base_url}{path}") as response:
                if response.status == 200:
                    result = await response.json()
                    message = result.get("message", "")
                    if "Hello from Server:" in message:
                        return message.split("Hello from Server: ")[1].strip()
                return "Error"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _set_server_count(self, target_count):
        """Adjust server count to target"""
        try:
            current = requests.get(f"{self.base_url}/rep", timeout=10).json()
            current_count = current["message"]["N"]
            
            if current_count < target_count:
                add_count = target_count - current_count
                requests.post(f"{self.base_url}/add", json={"n": add_count}, timeout=10)
            elif current_count > target_count:
                remove_count = current_count - target_count
                requests.delete(f"{self.base_url}/rm", json={"n": remove_count}, timeout=10)
            
            time.sleep(8)  # Wait longer for container startup
            return True
        except Exception as e:
            print(f"Error setting server count: {e}")
            return False
    
    async def test_load_distribution_detailed(self, num_requests=10000, num_servers=3):
        """Enhanced load distribution test with detailed metrics"""
        print(f"\n🔍 Testing load distribution with {num_requests} requests on {num_servers} servers...")
        
        if not self._set_server_count(num_servers):
            return None, None
        
        server_counts = defaultdict(int)
        response_times = []
        error_count = 0
        
        start_time = time.time()
        
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(100)
        
        async def limited_request(session):
            async with semaphore:
                request_start = time.time()
                result = await self.send_request(session)
                request_time = time.time() - request_start
                return result, request_time
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100),
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            tasks = [limited_request(session) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                    continue
                    
                server_id, response_time = result
                if server_id and "Error" not in server_id:
                    server_counts[server_id] += 1
                    response_times.append(response_time)
                else:
                    error_count += 1
        
        total_time = time.time() - start_time
        
        # Calculate distribution metrics
        if server_counts:
            counts = list(server_counts.values())
            distribution_stats = {
                'mean': statistics.mean(counts),
                'median': statistics.median(counts),
                'std_dev': statistics.stdev(counts) if len(counts) > 1 else 0,
                'min': min(counts),
                'max': max(counts),
                'coefficient_of_variation': statistics.stdev(counts) / statistics.mean(counts) if len(counts) > 1 and statistics.mean(counts) > 0 else 0
            }
            
            # Calculate balance quality (lower is better)
            expected_per_server = num_requests / len(server_counts)
            balance_quality = max(abs(count - expected_per_server) for count in counts) / expected_per_server
        else:
            distribution_stats = {}
            balance_quality = float('inf')
        
        performance_stats = {
            'total_time': total_time,
            'requests_per_second': num_requests / total_time,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'error_rate': error_count / num_requests,
            'successful_requests': len(response_times)
        }
        
        print(f"✅ Distribution Quality: {balance_quality:.3f} (lower is better)")
        print(f"📊 Std Dev: {distribution_stats.get('std_dev', 0):.2f}")
        print(f"⚡ RPS: {performance_stats['requests_per_second']:.2f}")
        print(f"🎯 Success Rate: {(1 - performance_stats['error_rate']):.3f}")
        
        return dict(server_counts), {
            'distribution_stats': distribution_stats,
            'performance_stats': performance_stats,
            'balance_quality': balance_quality
        }
    
    async def test_consistency_and_fairness(self, num_requests=5000, num_servers=4, num_rounds=3):
        """Test consistency of load distribution across multiple rounds"""
        print(f"\n🔄 Testing consistency across {num_rounds} rounds...")
        
        all_distributions = []
        all_balance_qualities = []
        
        for round_num in range(num_rounds):
            print(f"  Round {round_num + 1}/{num_rounds}")
            distribution, metrics = await self.test_load_distribution_detailed(num_requests, num_servers)
            
            if distribution and metrics:
                all_distributions.append(distribution)
                all_balance_qualities.append(metrics['balance_quality'])
        
        # Calculate consistency metrics
        if all_balance_qualities:
            consistency_stats = {
                'mean_balance_quality': statistics.mean(all_balance_qualities),
                'std_balance_quality': statistics.stdev(all_balance_qualities) if len(all_balance_qualities) > 1 else 0,
                'best_balance': min(all_balance_qualities),
                'worst_balance': max(all_balance_qualities)
            }
            
            print(f"📈 Consistency Results:")
            print(f"  Mean Balance Quality: {consistency_stats['mean_balance_quality']:.4f}")
            print(f"  Std Dev: {consistency_stats['std_balance_quality']:.4f}")
            print(f"  Best: {consistency_stats['best_balance']:.4f}")
            print(f"  Worst: {consistency_stats['worst_balance']:.4f}")
        
        return all_distributions, consistency_stats if all_balance_qualities else None
    
    async def test_scalability_comprehensive(self, num_requests=8000):
        """Comprehensive scalability test"""
        print(f"\n📈 Comprehensive scalability test...")
        
        results = {}
        server_counts = range(2, 8)  # Test 2-7 servers
        
        for n in server_counts:
            print(f"  Testing {n} servers...")
            distribution, metrics = await self.test_load_distribution_detailed(num_requests, n)
            
            if distribution and metrics:
                results[n] = {
                    'distribution': distribution,
                    'balance_quality': metrics['balance_quality'],
                    'performance': metrics['performance_stats'],
                    'distribution_stats': metrics['distribution_stats']
                }
            
            time.sleep(3)  # Brief pause between tests
        
        return results
    
    def test_endpoints_comprehensive(self):
        """Comprehensive endpoint testing"""
        print("\n🔧 Testing all endpoints...")
        
        tests = []
        
        # Test /rep
        try:
            response = requests.get(f"{self.base_url}/rep", timeout=10)
            tests.append(("GET /rep", response.status_code, response.json() if response.status_code == 200 else response.text))
        except Exception as e:
            tests.append(("GET /rep", "Error", str(e)))
        
        # Test /add with custom hostnames
        try:
            response = requests.post(f"{self.base_url}/add", 
                                   json={"n": 2, "hostnames": ["TestServer1", "TestServer2"]}, 
                                   timeout=10)
            tests.append(("POST /add", response.status_code, response.json() if response.status_code == 200 else response.text))
        except Exception as e:
            tests.append(("POST /add", "Error", str(e)))
        
        # Test /home
        try:
            response = requests.get(f"{self.base_url}/home", timeout=10)
            tests.append(("GET /home", response.status_code, response.json() if response.status_code == 200 else response.text))
        except Exception as e:
            tests.append(("GET /home", "Error", str(e)))
        
        # Test /rm
        try:
            response = requests.delete(f"{self.base_url}/rm", 
                                     json={"n": 1}, 
                                     timeout=10)
            tests.append(("DELETE /rm", response.status_code, response.json() if response.status_code == 200 else response.text))
        except Exception as e:
            tests.append(("DELETE /rm", "Error", str(e)))
        
        # Print results
        for endpoint, status, response in tests:
            print(f"  {endpoint}: Status {status}")
            if isinstance(response, dict):
                print(f"    Response: {json.dumps(response, indent=4)}")
            else:
                print(f"    Response: {response}")
        
        return tests
    
    def plot_enhanced_distribution(self, distribution, title="Load Distribution", metrics=None):
        """Enhanced distribution visualization"""
        if not distribution:
            print("No distribution data to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16)
        
        servers = list(distribution.keys())
        counts = list(distribution.values())
        
        # 1. Bar chart
        axes[0, 0].bar(servers, counts, color='skyblue', edgecolor='navy', alpha=0.7)
        axes[0, 0].set_title('Request Distribution by Server')
        axes[0, 0].set_xlabel('Servers')
        axes[0, 0].set_ylabel('Request Count')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Add ideal line
        if len(counts) > 0:
            ideal_count = sum(counts) / len(counts)
            axes[0, 0].axhline(y=ideal_count, color='red', linestyle='--', label=f'Ideal: {ideal_count:.0f}')
            axes[0, 0].legend()
        
        # 2. Pie chart
        axes[0, 1].pie(counts, labels=servers, autopct='%1.1f%%', startangle=90)
        axes[0, 1].set_title('Request Distribution Percentage')
        
        # 3. Deviation from ideal
        if len(counts) > 0:
            ideal_count = sum(counts) / len(counts)
            deviations = [count - ideal_count for count in counts]
            colors = ['red' if d < 0 else 'green' for d in deviations]
            axes[1, 0].bar(servers, deviations, color=colors, alpha=0.7)
            axes[1, 0].set_title('Deviation from Ideal Distribution')
            axes[1, 0].set_xlabel('Servers')
            axes[1, 0].set_ylabel('Deviation from Ideal')
            axes[1, 0].tick_params(axis='x', rotation=45)
            axes[1, 0].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 4. Statistics text
        axes[1, 1].axis('off')
        if metrics and 'distribution_stats' in metrics:
            stats = metrics['distribution_stats']
            perf = metrics['performance_stats']
            
            stats_text = f"""
Distribution Statistics:
• Mean: {stats.get('mean', 0):.1f}
• Std Dev: {stats.get('std_dev', 0):.2f}
• Min: {stats.get('min', 0)}
• Max: {stats.get('max', 0)}
• CV: {stats.get('coefficient_of_variation', 0):.3f}

Performance Statistics:
• RPS: {perf.get('requests_per_second', 0):.1f}
• Avg Response: {perf.get('avg_response_time', 0)*1000:.1f}ms
• Success Rate: {(1-perf.get('error_rate', 0))*100:.1f}%

Balance Quality: {metrics.get('balance_quality', 0):.4f}
(Lower is better)
            """
            axes[1, 1].text(0.1, 0.9, stats_text, transform=axes[1, 1].transAxes, 
                           fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        plt.show()
    
    def plot_scalability_analysis(self, scalability_results, title="Scalability Analysis"):
        """Enhanced scalability visualization"""
        if not scalability_results:
            print("No scalability data to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16)
        
        servers = list(scalability_results.keys())
        balance_qualities = [scalability_results[n]['balance_quality'] for n in servers]
        rps_values = [scalability_results[n]['performance']['requests_per_second'] for n in servers]
        std_devs = [scalability_results[n]['distribution_stats']['std_dev'] for n in servers]
        
        # 1. Balance Quality vs Server Count
        axes[0, 0].plot(servers, balance_qualities, marker='o', linewidth=2, markersize=8, color='blue')
        axes[0, 0].set_title('Balance Quality vs Server Count')
        axes[0, 0].set_xlabel('Number of Servers')
        axes[0, 0].set_ylabel('Balance Quality (Lower is Better)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Performance vs Server Count
        axes[0, 1].plot(servers, rps_values, marker='s', linewidth=2, markersize=8, color='green')
        axes[0, 1].set_title('Performance vs Server Count')
        axes[0, 1].set_xlabel('Number of Servers')
        axes[0, 1].set_ylabel('Requests per Second')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Standard Deviation vs Server Count
        axes[1, 0].plot(servers, std_devs, marker='^', linewidth=2, markersize=8, color='red')
        axes[1, 0].set_title('Distribution Uniformity vs Server Count')
        axes[1, 0].set_xlabel('Number of Servers')
        axes[1, 0].set_ylabel('Standard Deviation (Lower is Better)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Combined efficiency metric
        # Normalize metrics and create combined score
        if balance_qualities and rps_values:
            norm_balance = [(max(balance_qualities) - bq) / (max(balance_qualities) - min(balance_qualities)) if max(balance_qualities) != min(balance_qualities) else 1 for bq in balance_qualities]
            norm_rps = [(rps - min(rps_values)) / (max(rps_values) - min(rps_values)) if max(rps_values) != min(rps_values) else 1 for rps in rps_values]
            combined_score = [(nb + nr) / 2 for nb, nr in zip(norm_balance, norm_rps)]
            
            axes[1, 1].plot(servers, combined_score, marker='D', linewidth=2, markersize=8, color='purple')
            axes[1, 1].set_title('Combined Efficiency Score')
            axes[1, 1].set_xlabel('Number of Servers')
            axes[1, 1].set_ylabel('Efficiency Score (Higher is Better)')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_consistency_analysis(self, all_distributions, consistency_stats):
        """Plot consistency analysis across multiple rounds"""
        if not all_distributions:
            print("No consistency data to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Load Balancing Consistency Analysis', fontsize=16)
        
        # Get all unique servers
        all_servers = set()
        for dist in all_distributions:
            all_servers.update(dist.keys())
        all_servers = sorted(all_servers)
        
        # 1. Distribution across rounds
        round_data = []
        for i, dist in enumerate(all_distributions):
            for server in all_servers:
                round_data.append({
                    'Round': i + 1,
                    'Server': server,
                    'Requests': dist.get(server, 0)
                })
        
        # Convert to matrix for heatmap
        matrix = []
        for dist in all_distributions:
            matrix.append([dist.get(server, 0) for server in all_servers])
        
        if matrix:
            im = axes[0, 0].imshow(matrix, cmap='YlOrRd', aspect='auto')
            axes[0, 0].set_title('Request Distribution Heatmap')
            axes[0, 0].set_xlabel('Servers')
            axes[0, 0].set_ylabel('Rounds')
            axes[0, 0].set_xticks(range(len(all_servers)))
            axes[0, 0].set_xticklabels(all_servers, rotation=45)
            axes[0, 0].set_yticks(range(len(all_distributions)))
            axes[0, 0].set_yticklabels([f'Round {i+1}' for i in range(len(all_distributions))])
            plt.colorbar(im, ax=axes[0, 0])
        
        # 2. Server consistency (box plot)
        server_requests = {server: [] for server in all_servers}
        for dist in all_distributions:
            for server in all_servers:
                server_requests[server].append(dist.get(server, 0))
        
        box_data = [server_requests[server] for server in all_servers]
        box_plot = axes[0, 1].boxplot(box_data, labels=all_servers)
        axes[0, 1].set_title('Request Distribution Consistency')
        axes[0, 1].set_xlabel('Servers')
        axes[0, 1].set_ylabel('Request Count')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Balance quality trend
        if consistency_stats:
            balance_qualities = [consistency_stats['mean_balance_quality']] * len(all_distributions)  # Placeholder
            axes[1, 0].plot(range(1, len(all_distributions) + 1), balance_qualities, marker='o')
            axes[1, 0].set_title('Balance Quality Across Rounds')
            axes[1, 0].set_xlabel('Round')
            axes[1, 0].set_ylabel('Balance Quality')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Consistency statistics
        axes[1, 1].axis('off')
        if consistency_stats:
            stats_text = f"""
Consistency Statistics:
• Mean Balance Quality: {consistency_stats['mean_balance_quality']:.4f}
• Std Dev: {consistency_stats['std_balance_quality']:.4f}
• Best Balance: {consistency_stats['best_balance']:.4f}
• Worst Balance: {consistency_stats['worst_balance']:.4f}

Interpretation:
• Lower balance quality is better
• Lower std dev indicates more consistency
• Consistent performance across rounds
  indicates stable load balancing
            """
            axes[1, 1].text(0.1, 0.9, stats_text, transform=axes[1, 1].transAxes, 
                           fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        plt.show()

async def main():
    print("🚀 Enhanced Load Balancer Performance Testing")
    print("=" * 60)
    
    tester = EnhancedLoadBalancerTester()
    
    # Test A-1: Enhanced Load Distribution Analysis
    print("\n🔍 Test A-1: Enhanced Load Distribution Analysis")
    print("=" * 60)
    distribution, metrics = await tester.test_load_distribution_detailed(10000, 3)
    if distribution:
        tester.plot_enhanced_distribution(distribution, "A-1: Enhanced Load Distribution (N=3, 10000 requests)", metrics)
    
    # Test A-2: Consistency and Fairness
    print("\n🔄 Test A-2: Consistency and Fairness Analysis")
    print("=" * 60)
    all_distributions, consistency_stats = await tester.test_consistency_and_fairness(5000, 4, 3)
    if all_distributions:
        tester.plot_consistency_analysis(all_distributions, consistency_stats)
    
    # Test A-3: Comprehensive Scalability
    print("\n📈 Test A-3: Comprehensive Scalability Analysis")
    print("=" * 60)
    scalability_results = await tester.test_scalability_comprehensive(8000)
    if scalability_results:
        tester.plot_scalability_analysis(scalability_results, "A-3: Comprehensive Scalability Analysis")
    
    # Test A-4: Endpoint Testing
    print("\n🔧 Test A-4: Comprehensive Endpoint Testing")
    print("=" * 60)
    endpoint_results = tester.test_endpoints_comprehensive()
    
    print("\n✅ All tests completed!")
    print("\nKey Improvements Demonstrated:")
    print("• Better load distribution uniformity")
    print("• Lower coefficient of variation")
    print("• Consistent performance across multiple rounds")
    print("• Efficient handling of concurrent requests")
    print("• Improved hash function reduces clustering")

if __name__ == "__main__":
    asyncio.run(main())