import json
from src.config import (
    EMPTY, WALL, WAREHOUSE, ENTRANCE, EXIT, 
    EVAPORATION_RATE
)

class Environment:
    def __init__(self):
        self.grid = []
        self.warehouses = []
        self.n = 0
        self._objects_truth = set() # PRIVATO: ground truth degli oggetti
        self.stigma_map = []
        self.occupancy = set()      # Insieme di tuple (r, c) degli agenti attivi
        self.traffic_log = {}       # {(r, c): count} per heatmap
        self.delivered = 0
        self.spawn_queue = []       # Agenti in attesa di dispiegamento

    def load(self, path):
        """Carica l'ambiente dal file JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.grid = data['grid']
        self.warehouses = data['warehouses']
        self.n = data['metadata']['grid_size']
        self._objects_truth = set(map(tuple, data.get('objects', [])))
        
        # Inizializza mappe accessorie
        self.stigma_map = [[0.0] * self.n for _ in range(self.n)]
        self.traffic_log = {}
        self.occupancy = set()
        self.delivered = 0
        self.spawn_queue = []

    def is_object_at(self, r, c):
        """Chiamato SOLO dal sensore visivo, mai direttamente dagli agenti."""
        return (r, c) in self._objects_truth

    def deliver_object(self, r, c):
        """Rimuove l'oggetto dal simulatore e incrementa il contatore."""
        self._objects_truth.discard((r, c))
        self.delivered += 1

    def drop_abandoned_object(self, r, c):
        """Rimette l'oggetto a terra se l'agente è costretto ad abbandonarlo per la batteria."""
        self._objects_truth.add((r, c))

    def pick_up_object(self, r, c):
        """Rimuove l'oggetto dalla mappa (simulando il pick-up)."""
        self._objects_truth.discard((r, c))
        
    def _warehouse_of(self, r, c, cell_type):
        """Trova a quale magazzino appartiene una determinata cella ENTRANCE o EXIT."""
        for wh in self.warehouses:
            if wh[cell_type] == [r, c]:
                return wh
        return None

    def is_walkable(self, r, c, agent_r=None, agent_c=None):
        """Verifica se una cella è percorribile, includendo la logica dei sensi unici."""
        if r < 0 or r >= self.n or c < 0 or c >= self.n:
            return False
            
        val = self.grid[r][c]
        if val == WALL:
            return False
            
        if val == ENTRANCE and agent_r is not None and agent_c is not None:
            wh = self._warehouse_of(r, c, 'entrance')
            if wh is None: 
                return True
            return self._coming_from_outside(r, c, agent_r, agent_c, wh['side'])
            
        if val == EXIT and agent_r is not None and agent_c is not None:
            wh = self._warehouse_of(r, c, 'exit')
            if wh is None: 
                return True
            return self._coming_from_inside(r, c, agent_r, agent_c, wh['side'])
            
        return True # EMPTY, WAREHOUSE

    def _coming_from_outside(self, r, c, ar, ac, side):
        """Verifica che l'agente entri nel magazzino dalla direzione corretta."""
        if side == 'top':    return ar < r
        if side == 'bottom': return ar > r
        if side == 'left':   return ac < c
        if side == 'right':  return ac > c
        return True

    def _coming_from_inside(self, r, c, ar, ac, side):
        """Verifica che l'agente esca dal magazzino nella direzione corretta."""
        if side == 'top':    return ar > r
        if side == 'bottom': return ar < r
        if side == 'left':   return ac > c
        if side == 'right':  return ac < c
        return True

    def update_stigma(self):
        """Evaporazione del feromone stigmergico."""
        for r in range(self.n):
            for c in range(self.n):
                if self.stigma_map[r][c] > 0:
                    self.stigma_map[r][c] *= (1.0 - EVAPORATION_RATE)
                    if self.stigma_map[r][c] < 0.01:
                        self.stigma_map[r][c] = 0.0

    def log_traffic(self, r, c):
        """Registra il passaggio su ENTRANCE/EXIT per la heatmap dei colli di bottiglia."""
        if (r, c) not in self.traffic_log:
            self.traffic_log[(r, c)] = 0
        self.traffic_log[(r, c)] += 1

    def try_spawn_next(self, active_agents):
        """Gestisce il dispiegamento (spawn) di un nuovo agente nella griglia."""
        if self.spawn_queue and (0, 0) not in self.occupancy:
            agent = self.spawn_queue.pop(0)
            agent.pos = (0, 0)
            agent.state = 'DEPLOY'
            active_agents.append(agent)
            self.occupancy.add((0, 0))