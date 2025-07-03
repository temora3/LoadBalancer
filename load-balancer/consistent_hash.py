## Improved Load Balancer using Consistent Hashing
## This implementation uses better hash functions to ensure more uniform distribution
## of requests across multiple servers.

import hashlib

class ConsistentHash:
    def __init__(self, slots=512, virtual_servers=200):
        self.slots = slots
        self.virtual_servers = virtual_servers  # Increased to 200 for better distribution
        self.ring = [None] * slots
        self.servers = {}
        self.sorted_keys = []  # Keep track of sorted positions for efficient lookups
     
    def _hash_request(self, request_id):
        """Improved hash function using multiple rounds for better distribution"""
        # Convert to string and apply multiple hash rounds
        hash_str = str(request_id).encode('utf-8')
        
        # First round with SHA-256
        hash_obj = hashlib.sha256(hash_str)
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Second round with different salt for better distribution
        salted = f"{hash_int}:salt".encode('utf-8')
        hash_obj2 = hashlib.sha256(salted)
        final_hash = int(hash_obj2.hexdigest(), 16)
        
        return final_hash % self.slots
    
    def _hash_virtual_server(self, server_id, virtual_id):
        """Improved hash function for virtual servers using SHA-256"""
        # Combine server_id and virtual_id for unique hash
        combined = f"{server_id}:{virtual_id}".encode('utf-8')
        hash_obj = hashlib.sha256(combined)
        hash_int = int(hash_obj.hexdigest(), 16)
        return hash_int % self.slots
    
    def _find_next_slot(self, start_slot):
        """Find next available slot using linear probing"""
        for i in range(self.slots):
            slot = (start_slot + i) % self.slots
            if self.ring[slot] is None:
                return slot
        return None
    
    def _update_sorted_keys(self):
        """Update sorted list of occupied positions for efficient lookups"""
        self.sorted_keys = []
        for i in range(self.slots):
            if self.ring[i] is not None:
                self.sorted_keys.append(i)
        self.sorted_keys.sort()
    
    def add_server(self, server_id):
        """Add a server with its virtual servers"""
        if server_id in self.servers:
            return False
            
        virtual_slots = []
        for j in range(self.virtual_servers):
            slot = self._hash_virtual_server(server_id, j)
            
            # Handle collisions with linear probing
            if self.ring[slot] is not None:
                slot = self._find_next_slot(slot)
                if slot is None:
                    # Rollback if no space
                    for vs in virtual_slots:
                        self.ring[vs] = None
                    return False
            
            self.ring[slot] = server_id
            virtual_slots.append(slot)
        
        self.servers[server_id] = virtual_slots
        self._update_sorted_keys()
        return True
    
    def remove_server(self, server_id):
        """Remove a server and its virtual servers"""
        if server_id not in self.servers:
            return False
            
        for slot in self.servers[server_id]:
            self.ring[slot] = None
        
        del self.servers[server_id]
        self._update_sorted_keys()
        return True
    
    def get_server(self, request_id):
        """Get the server that should handle this request using binary search"""
        if not self.servers:
            return None
        
        if not self.sorted_keys:
            return None
            
        slot = self._hash_request(request_id)
        
        # Binary search for the first key >= slot
        left, right = 0, len(self.sorted_keys) - 1
        result_idx = 0  # Default to first server if not found
        
        while left <= right:
            mid = (left + right) // 2
            if self.sorted_keys[mid] >= slot:
                result_idx = mid
                right = mid - 1
            else:
                left = mid + 1
        
        # If we went past the end, wrap around to the beginning
        if result_idx >= len(self.sorted_keys) or self.sorted_keys[result_idx] < slot:
            result_idx = 0
        
        return self.ring[self.sorted_keys[result_idx]]
    
    def get_servers(self):
        """Get list of all servers"""
        return list(self.servers.keys())
    
    def get_distribution_stats(self, num_requests=10000):
        """Get distribution statistics for testing"""
        if not self.servers:
            return {}
            
        request_counts = {server: 0 for server in self.servers.keys()}
        
        for i in range(num_requests):
            server = self.get_server(i)
            if server:
                request_counts[server] += 1
        
        return request_counts