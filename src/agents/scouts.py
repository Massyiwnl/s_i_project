import random
from src.agents.base_agent import BaseAgent
from src.sensors import get_visible_objects
from src.config import VISION_RADIUS, STRESS_MAX, STRESS_RANDOM_STEPS

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
        if self.state == 'LOW_BATTERY':
            return

        # Sensori visivi
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        # Macchina a Stati
        if self.state == 'DEPLOY':
            self._handle_deploy(env)
        elif self.state == 'EXPLORE' or self.state == 'STANDBY':
            self._handle_explore(env)

    def _try_move(self, env, nr, nc):
        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            return False

        if (nr, nc) in env.occupancy:
            return False # STANDBY

        env.occupancy.remove(self.pos)
        self.previous_pos = self.pos
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)
        
        # --- GESTIONE STRESS ---
        if self.pos in self.local_map and self.local_map[self.pos].get('status') == 'VISITED':
            self.stress += 1
        else:
            self.stress = 0
            
        self.local_map[self.pos] = {'status': 'VISITED', 'ts': 0}
        return True

    def _handle_deploy(self, env):
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc):
                self.state = 'EXPLORE'
                # Imposta la direzione iniziale coerente col primo passo
                if dr == -1: self.direction = 0
                elif dc == 1: self.direction = 1
                elif dr == 1: self.direction = 2
                else: self.direction = 3
                return

    def _handle_explore(self, env):
        # 1. Se è in modalità "Panico/Sblocco", fa passi casuali
        if self.random_steps > 0:
            self.random_steps -= 1
            self._random_move(env)
            return

        # 2. Se lo stress è al massimo, innesca la modalità "Panico"
        if self.stress >= STRESS_MAX:
            self.stress = 0
            self.random_steps = STRESS_RANDOM_STEPS
            self._random_move(env)
            return

        # 3. WALL-FOLLOWING (Regola della mano destra)
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)] # N, E, S, W
        
        # Prova a girare a DESTRA
        right_dir = (self.direction + 1) % 4
        dr, dc = dirs[right_dir]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.direction = right_dir
            if self._try_move(env, nr, nc):
                self.state = 'EXPLORE'
                return

        # Prova DRITTO
        dr, dc = dirs[self.direction]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            if self._try_move(env, nr, nc):
                self.state = 'EXPLORE'
                return

        # Prova SINISTRA
        left_dir = (self.direction - 1) % 4
        dr, dc = dirs[left_dir]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.direction = left_dir
            if self._try_move(env, nr, nc):
                self.state = 'EXPLORE'
                return

        # U-TURN (Inversione a U nei vicoli ciechi)
        self.direction = (self.direction + 2) % 4
        dr, dc = dirs[self.direction]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if self._try_move(env, nr, nc):
            self.state = 'EXPLORE'
            return
            
        self.state = 'STANDBY'

    def _random_move(self, env):
        """Passo stocastico puro per spezzare il loop del wall-following."""
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc):
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
        if self.state == 'LOW_BATTERY':
            return

        # 1. Sensori visivi per scoprire oggetti
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        # Macchina a Stati
        if self.state == 'DEPLOY':
            self._handle_deploy(env)
        elif self.state == 'EXPLORE' or self.state == 'STANDBY':
            self._handle_explore(env)

    def _try_move(self, env, nr, nc):
        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            return False

        if (nr, nc) in env.occupancy:
            return False # STANDBY

        env.occupancy.remove(self.pos)
        self.previous_pos = self.pos
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)
        self.local_map[self.pos] = {'status': 'VISITED', 'ts': 0}
        return True

    def _handle_deploy(self, env):
        # Cerca di uscire dallo spawn (0,0)
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc):
                self.state = 'EXPLORE'
                return

    def _handle_explore(self, env):
        valid_moves = []
        weights = []

        # Valuta N, S, E, O
        for dr, dc in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            
            if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
                valid_moves.append((nr, nc))
                
                # --- LOGICA STIGMERGICA ---
                # Peso base 1.0 (equiparabile al 25% iniziale)
                weight = 1.0 
                # Se la cella è già stata visitata, riduce la probabilità del 70% (moltiplica per 0.30)
                if (nr, nc) in self.local_map and self.local_map[(nr, nc)].get('status') == 'VISITED':
                    weight *= 0.30 
                    
                weights.append(weight)

        # Se intrappolato, va in STANDBY per 1 tick
        if not valid_moves:
            self.state = 'STANDBY'
            return
            
        self.state = 'EXPLORE'
        
        # Scelta stocastica basata sui pesi stigmergici
        chosen_move = random.choices(valid_moves, weights=weights, k=1)[0]
        self._try_move(env, chosen_move[0], chosen_move[1])