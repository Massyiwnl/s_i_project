import random
from src.agents.base_agent import BaseAgent
from src.sensors import get_visible_objects
from src.config import VISION_RADIUS, STRESS_MAX, STRESS_RANDOM_STEPS
from src.pathfinding import astar
from src.config import COMM_RADIUS

class Scout1(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.state = 'DEPLOY'
        self.previous_pos = None
        self.direction = 0  # 0:Nord, 1:Est, 2:Sud, 3:Ovest
        self.stress = 0
        self.random_steps = 0

    def decide_action(self, env, tick):
        self.check_battery(env)
        # 1. Comunicazione Multi-Agente Distribuita (Fase 5 Decentralizzata)
        from src.communication import get_agents_in_radius
        neighbors = get_agents_in_radius(env, self.pos, COMM_RADIUS)
        for neighbor in neighbors:
            self.merge_knowledge(neighbor.local_map, tick)
        
        # 2. Gestione Stato Emergenza Batteria
        if self.state == 'RETURN_SAFE':
            self._handle_return_safe(env, tick)
            return

        # Sensori visivi
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        # Macchina a Stati
        if self.state == 'DEPLOY':
            self._handle_deploy(env, tick)
        elif self.state == 'EXPLORE' or self.state == 'STANDBY':
            self._handle_explore(env, tick)

    def _handle_return_safe(self, env, tick):
        if self.pos == self.target_obj:
            self.state = 'STANDBY'
            return

        if not self.cached_path:
            self.cached_path = astar(env, self.pos, self.target_obj)
            
        if self.cached_path:
            # FIX: Rimuove la cella di partenza per evitare auto-collisioni
            if self.cached_path[0] == self.pos:
                self.cached_path.pop(0)
                
            if self.cached_path:
                next_step = self.cached_path[0]
                if self._try_move(env, next_step[0], next_step[1], tick):
                    self.cached_path.pop(0)
    
    def _try_move(self, env, nr, nc, tick):
        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            return False

        if (nr, nc) in env.occupancy:
            return False 

        env.occupancy.remove(self.pos)
        self.previous_pos = self.pos
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)
        
        # --- GESTIONE STRESS ---
        if self.pos in self.local_map and self.local_map[self.pos].get('status') == 'VISITED':
            self.stress += 1
        else:
            self.stress = 0
            
        # FIX STIGMERGIA: ts deve essere il tick corrente, non 0!
        self.local_map[self.pos] = {'status': 'VISITED', 'ts': tick}
        return True

    def _handle_deploy(self, env, tick):
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                if dr == -1: self.direction = 0
                elif dc == 1: self.direction = 1
                elif dr == 1: self.direction = 2
                else: self.direction = 3
                return

    def _handle_explore(self, env, tick):
        if self.random_steps > 0:
            self.random_steps -= 1
            self._random_move(env, tick)
            return

        if self.stress >= STRESS_MAX:
            self.stress = 0
            self.random_steps = STRESS_RANDOM_STEPS
            self._random_move(env, tick)
            return

        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        
        right_dir = (self.direction + 1) % 4
        dr, dc = dirs[right_dir]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.direction = right_dir
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                return

        dr, dc = dirs[self.direction]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                return

        left_dir = (self.direction - 1) % 4
        dr, dc = dirs[left_dir]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.direction = left_dir
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                return

        self.direction = (self.direction + 2) % 4
        dr, dc = dirs[self.direction]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if self._try_move(env, nr, nc, tick):
            self.state = 'EXPLORE'
            return
            
        self.state = 'STANDBY'

    def _random_move(self, env, tick):
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                if dr == -1: self.direction = 0
                elif dc == 1: self.direction = 1
                elif dr == 1: self.direction = 2
                else: self.direction = 3
                break

class Scout2(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.state = 'DEPLOY'
        self.previous_pos = None

    def decide_action(self, env, tick):
        self.check_battery(env)
          # 1. Comunicazione Multi-Agente Distribuita (Fase 5 Decentralizzata)
        from src.communication import get_agents_in_radius
        neighbors = get_agents_in_radius(env, self.pos, COMM_RADIUS)
        for neighbor in neighbors:
            self.merge_knowledge(neighbor.local_map, tick)
        
        # 2. Gestione Stato Emergenza Batteria
        if self.state == 'RETURN_SAFE':
            self._handle_return_safe(env, tick)
            return

        # 1. Sensori visivi per scoprire oggetti
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        # Macchina a Stati
        if self.state == 'DEPLOY':
            self._handle_deploy(env, tick)
        elif self.state == 'EXPLORE' or self.state == 'STANDBY':
            self._handle_explore(env, tick)

    def _handle_return_safe(self, env, tick):
        if self.pos == self.target_obj:
            self.state = 'STANDBY'
            return

        if not self.cached_path:
            self.cached_path = astar(env, self.pos, self.target_obj)
            
        if self.cached_path:
            # FIX: Rimuove la cella di partenza per evitare auto-collisioni
            if self.cached_path[0] == self.pos:
                self.cached_path.pop(0)
                
            if self.cached_path:
                next_step = self.cached_path[0]
                if self._try_move(env, next_step[0], next_step[1], tick):
                    self.cached_path.pop(0)
    
    def _try_move(self, env, nr, nc, tick):
        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            return False

        if (nr, nc) in env.occupancy:
            return False # STANDBY

        env.occupancy.remove(self.pos)
        self.previous_pos = self.pos
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)

        # FIX STIGMERGIA: ts deve essere il tick corrente, non 0!
        self.local_map[self.pos] = {'status': 'VISITED', 'ts': tick}
        return True

    def _handle_deploy(self, env, tick):
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                return

    def _handle_explore(self, env, tick):
        valid_moves = []
        weights = []

        for dr, dc in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            
            if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
                valid_moves.append((nr, nc))
                weight = 1.0 
                if (nr, nc) in self.local_map and self.local_map[(nr, nc)].get('status') == 'VISITED':
                    weight *= 0.30 
                weights.append(weight)

        if not valid_moves:
            self.state = 'STANDBY'
            return
            
        self.state = 'EXPLORE'
        
        chosen_move = random.choices(valid_moves, weights=weights, k=1)[0]
        self._try_move(env, chosen_move[0], chosen_move[1], tick)