class ConsistentHash:
    def __init__(self, slots=512, virtual_servers=9):
        self.slots = slots
        self.virtual_servers = virtual_servers
        self.ring = [None] * slots
        self.servers = {}
        
    def _hash_request(self, request_id):
        """Hash function H(i) = i^2 + 2*i + 17"""
        i = int(request_id) if isinstance(request_id, str) else request_id
        return (i * i + 2 * i + 17) % self.slots
    
    def _hash_virtual_server(self, server_id, virtual_id):
        """Hash function Φ(i, j) = i^2 + j^2 + 2*j + 25"""
        i = hash(server_id) % 1000  # Convert string to number
        j = virtual_id
        return (i * i + j * j + 2 * j + 25) % self.slots
    
    def _find_next_slot(self, start_slot):
        """Find next available slot using linear probing"""
        for i in range(self.slots):
            slot = (start_slot + i) % self.slots
            if self.ring[slot] is None:
                return slot
        return None
    
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
        return True
    
    def remove_server(self, server_id):
        """Remove a server and its virtual servers"""
        if server_id not in self.servers:
            return False
            
        for slot in self.servers[server_id]:
            self.ring[slot] = None
        
        del self.servers[server_id]
        return True
    
    def get_server(self, request_id):
        """Get the server that should handle this request"""
        if not self.servers:
            return None
            
        slot = self._hash_request(request_id)
        
        # Find next server in clockwise direction
        for i in range(self.slots):
            current_slot = (slot + i) % self.slots
            if self.ring[current_slot] is not None:
                return self.ring[current_slot]
        
        return None
    
    def get_servers(self):
        """Get list of all servers"""
        return list(self.servers.keys())