import json
import random
from collections import deque
from src.config import (
    WALL, ENTRANCE, EXIT,
    EVAPORATION_RATE, STIGMA_ON, DEPLOY_RADIUS
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
        self.pheromone_base = []
        self.intentions = {}

        self.occupancy = set()
        # traffic_log: conta le consegne per cella (chiamato in _handle_return_home).
        # Traccia solo i punti di deposito degli oggetti nei magazzini.
        self.traffic_log = {}
        # movement_log: conta i passaggi di tutti gli agenti per ogni cella
        # (chiamato in _try_move). Traccia il traffico reale di movimento
        # e permette di generare la vera heatmap dei colli di bottiglia.
        self.movement_log = {}
        self.delivered = 0
        self.spawn_queue = deque()
        self.active_agents = []

        # Set delle celle con feromone > 0 per update_stigma O(|celle_attive|)
        self.active_pheromone_cells = set()

    def load(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.grid = data['grid']
        self.warehouses = data['warehouses']
        self.n = data['metadata']['grid_size']
        self._objects_truth = set(map(tuple, data.get('objects', [])))

        for wh in self.warehouses:
            wh['entrance'] = tuple(wh['entrance'])
            wh['exit'] = tuple(wh['exit'])

        self.pheromone_explore = [[0.0] * self.n for _ in range(self.n)]
        self.pheromone_object = [[0.0] * self.n for _ in range(self.n)]
        self._init_home_gradient()
        self._init_base_gradient()

        self.intentions = {}
        self.traffic_log = {}
        self.movement_log = {}
        self.occupancy = set()
        self.delivered = 0
        self.spawn_queue = deque()
        self.active_agents = []
        self.active_pheromone_cells = set()

    def _init_home_gradient(self):
        """
        Gradiente BFS statico verso l'ingresso dei magazzini.
        Valore iniziale proporzionale alla mappa (self.n * self.n) per garantire
        gradiente positivo su qualsiasi dimensione di griglia.
        """
        self.pheromone_home = [[0.0] * self.n for _ in range(self.n)]
        queue = deque()
        max_val = float(self.n * self.n)

        for wh in self.warehouses:
            r, c = wh['entrance']
            self.pheromone_home[r][c] = max_val
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
                        self.pheromone_home[nr][nc] = max(0.0, current_val - 1.0)
                        queue.append((nr, nc))

    def _init_base_gradient(self):
        """
        Gradiente BFS statico verso lo spawn (0,0) per il ritorno sicuro.
        """
        self.pheromone_base = [[0.0] * self.n for _ in range(self.n)]
        max_val = float(self.n * self.n)
        queue = deque([(0, 0)])
        self.pheromone_base[0][0] = max_val
        visited = set([(0, 0)])

        while queue:
            r, c = queue.popleft()
            current_val = self.pheromone_base[r][c]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.n and 0 <= nc < self.n and self.grid[nr][nc] != WALL:
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        self.pheromone_base[nr][nc] = max(0.0, current_val - 1.0)
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
            if wh[cell_type] == (r, c):
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
            if wh is None:
                return True
            return self._coming_from_outside(r, c, agent_r, agent_c, wh['side'])

        if val == EXIT and agent_r is not None and agent_c is not None:
            wh = self._warehouse_of(r, c, 'exit')
            if wh is None:
                return True
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
        if not STIGMA_ON:
            return

        cells_to_remove = set()
        for (r, c) in self.active_pheromone_cells:
            if self.pheromone_explore[r][c] > 0:
                self.pheromone_explore[r][c] *= (1.0 - EVAPORATION_RATE)
                if self.pheromone_explore[r][c] < 0.01:
                    self.pheromone_explore[r][c] = 0.0

            if self.pheromone_object[r][c] > 0:
                self.pheromone_object[r][c] *= (1.0 - EVAPORATION_RATE * 2)
                if self.pheromone_object[r][c] < 0.01:
                    self.pheromone_object[r][c] = 0.0

            if (self.pheromone_explore[r][c] == 0.0
                    and self.pheromone_object[r][c] == 0.0):
                cells_to_remove.add((r, c))

        self.active_pheromone_cells -= cells_to_remove

    def clear_intentions(self):
        self.intentions.clear()

    def log_traffic(self, r, c):
        """Registra una consegna avvenuta nella cella (r, c) di magazzino."""
        if (r, c) not in self.traffic_log:
            self.traffic_log[(r, c)] = 0
        self.traffic_log[(r, c)] += 1

    def log_movement(self, r, c):
        """
        Registra il passaggio di un agente nella cella (r, c).
        Chiamato in base_agent._try_move ad ogni spostamento fisico effettivo.
        Alimenta la vera heatmap dei colli di bottiglia, distinta da traffic_log
        che traccia solo i punti di consegna nei magazzini.
        """
        if (r, c) not in self.movement_log:
            self.movement_log[(r, c)] = 0
        self.movement_log[(r, c)] += 1

    def try_spawn_next(self, active_agents):
        if not self.spawn_queue:
            return

        candidates = []
        for dr in range(-DEPLOY_RADIUS, DEPLOY_RADIUS + 1):
            for dc in range(-DEPLOY_RADIUS, DEPLOY_RADIUS + 1):
                if abs(dr) + abs(dc) <= DEPLOY_RADIUS:
                    r, c = dr, dc
                    if (0 <= r < self.n and 0 <= c < self.n
                            and self.is_walkable(r, c)
                            and (r, c) not in self.occupancy):
                        candidates.append((r, c))

        if candidates:
            spawn_pos = random.choice(candidates)
            agent = self.spawn_queue.popleft()
            agent.pos = spawn_pos
            agent.state = 'EXPLORE'
            active_agents.append(agent)
            self.occupancy.add(spawn_pos)