import json
from collections import deque
from src.config import (
    EMPTY, WALL, WAREHOUSE, ENTRANCE, EXIT, 
    EVAPORATION_RATE
)

class Environment:
    def __init__(self):
        self.grid = []
        self.warehouses = []
        self.n = 0
        self._objects_truth = set()
        
        self.pheromone_explore = [] 
        self.pheromone_object = []  
        self.pheromone_home = []    
        self.pheromone_base = []    # NUOVO GRADIENTE PER IL RITORNO INFALLIBILE
        self.intentions = {}        
        
        self.occupancy = set()
        self.traffic_log = {}
        self.delivered = 0
        self.spawn_queue = []
        self.active_agents = []

    def load(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.grid = data['grid']
        self.warehouses = data['warehouses']
        self.n = data['metadata']['grid_size']
        self._objects_truth = set(map(tuple, data.get('objects', [])))
        
        self.pheromone_explore = [[0.0] * self.n for _ in range(self.n)]
        self.pheromone_object = [[0.0] * self.n for _ in range(self.n)]
        self._init_home_gradient() 
        self._init_base_gradient() # Inizializza il gradiente di rientro
        
        self.intentions = {}
        self.traffic_log = {}
        self.occupancy = set()
        self.delivered = 0
        self.spawn_queue = []
        self.active_agents = []

    def _init_home_gradient(self):
        self.pheromone_home = [[0.0] * self.n for _ in range(self.n)]
        queue = deque()
        for wh in self.warehouses:
            r, c = wh['entrance']
            self.pheromone_home[r][c] = 100.0
            queue.append((r, c))
            
        visited = set(queue)
        while queue:
            r, c = queue.popleft()
            current_val = self.pheromone_home[r][c]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.n and 0 <= nc < self.n and self.grid[nr][nc] != WALL:
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        self.pheromone_home[nr][nc] = current_val - 1.0 
                        queue.append((nr, nc))

    def _init_base_gradient(self):
        """Genera un gradiente stigmergico statico infallibile verso lo Spawn (0,0)."""
        self.pheromone_base = [[0.0] * self.n for _ in range(self.n)]
        queue = deque([(0, 0)])
        self.pheromone_base[0][0] = 1000.0 # Valore altissimo all'origine
        visited = set([(0, 0)])
        
        while queue:
            r, c = queue.popleft()
            current_val = self.pheromone_base[r][c]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.n and 0 <= nc < self.n and self.grid[nr][nc] != WALL:
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        self.pheromone_base[nr][nc] = current_val - 1.0 
                        queue.append((nr, nc))

    def is_object_at(self, r, c):
        return (r, c) in self._objects_truth

    def deliver_object(self, r, c):
        self._objects_truth.discard((r, c))
        self.delivered += 1

    def drop_abandoned_object(self, r, c):
        self._objects_truth.add((r, c))

    def pick_up_object(self, r, c):
        self._objects_truth.discard((r, c))
        
    def _warehouse_of(self, r, c, cell_type):
        for wh in self.warehouses:
            if wh[cell_type] == [r, c]:
                return wh
        return None

    def is_walkable(self, r, c, agent_r=None, agent_c=None):
        if r < 0 or r >= self.n or c < 0 or c >= self.n:
            return False
            
        val = self.grid[r][c]
        if val == WALL:
            return False
            
        if val == ENTRANCE and agent_r is not None and agent_c is not None:
            wh = self._warehouse_of(r, c, 'entrance')
            if wh is None: return True
            return self._coming_from_outside(r, c, agent_r, agent_c, wh['side'])
            
        if val == EXIT and agent_r is not None and agent_c is not None:
            wh = self._warehouse_of(r, c, 'exit')
            if wh is None: return True
            return self._coming_from_inside(r, c, agent_r, agent_c, wh['side'])
            
        return True

    def _coming_from_outside(self, r, c, ar, ac, side):
        if side == 'top':    return ar > r
        if side == 'bottom': return ar < r
        if side == 'left':   return ac > c
        if side == 'right':  return ac < c
        return True

    def _coming_from_inside(self, r, c, ar, ac, side):
        if side == 'top':    return ar < r
        if side == 'bottom': return ar > r
        if side == 'left':   return ac < c
        if side == 'right':  return ac > c
        return True

    def update_stigma(self):
        for r in range(self.n):
            for c in range(self.n):
                if self.pheromone_explore[r][c] > 0:
                    self.pheromone_explore[r][c] *= (1.0 - EVAPORATION_RATE)
                    if self.pheromone_explore[r][c] < 0.01: 
                        self.pheromone_explore[r][c] = 0.0
                
                if self.pheromone_object[r][c] > 0:
                    self.pheromone_object[r][c] *= (1.0 - EVAPORATION_RATE * 2)
                    if self.pheromone_object[r][c] < 0.01: 
                        self.pheromone_object[r][c] = 0.0

    def clear_intentions(self):
        self.intentions.clear()

    def log_traffic(self, r, c):
        if (r, c) not in self.traffic_log:
            self.traffic_log[(r, c)] = 0
        self.traffic_log[(r, c)] += 1

    def try_spawn_next(self, active_agents):
        if self.spawn_queue and (0, 0) not in self.occupancy:
            agent = self.spawn_queue.pop(0)
            agent.pos = (0, 0)
            agent.state = 'EXPLORE'
            active_agents.append(agent)
            self.occupancy.add((0, 0))