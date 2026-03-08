import random
from src.agents.base_agent import BaseAgent
from src.pathfinding import astar, real_distance
from src.sensors import get_visible_objects, detect_agents_in_radius
from src.config import VISION_RADIUS, ENTRANCE, EXIT, WAREHOUSE, COMM_RADIUS, CONGESTION_MALUS, STIGMA_ON, ENERGY_MARGIN

class Worker1(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.state = 'DEPLOY'
        self.target_obj = None
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
       
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}
        if self.state == 'DEPLOY':
            self._handle_deploy(env, tick)
        elif self.state == 'EXPLORE':
            self._handle_explore(env, tick)
        elif self.state == 'MOVE_TO_OBJECT':
            self._handle_move_to_object(env, tick)
        elif self.state == 'RETURN_TO_WAREHOUSE':
            self._handle_return_to_warehouse(env, tick)
        elif self.state == 'DELIVER':
            self._handle_deliver(env,tick)

    
    def _try_move(self, env, nr, nc, tick):
        """Tenta di muoversi. GESTIONE COLLISIONI: STANDBY PURO (Niente backtracking)"""
        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.cached_path = [] # Muro o controsenso, ricalcola
            return False

        if (nr, nc) in env.occupancy:
            # RISOLUZIONE DEADLOCK BASE: Ricalcola il percorso per evitare stalli infiniti
            self.cached_path = [] 
            return False  

        # Movimento normale
        env.occupancy.remove(self.pos)
        self.previous_pos = self.pos
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)

        self.local_map[self.pos] = {'status': 'VISITED', 'ts': tick}
        return True

    def _handle_deploy(self, env, tick):
        for dr, dc in [(0, 1), (1, 0)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                self.state = 'EXPLORE'
                return

    def _handle_explore(self, env, tick):
        for cell, data in self.local_map.items():
            if data.get('status') == 'FOUND':
                self.target_obj = cell
                self.state = 'MOVE_TO_OBJECT'
                self.cached_path = astar(env, self.pos, self.target_obj)
                return

        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                break

    def _handle_move_to_object(self, env, tick):
        # 1. Controllo Stigmergico (Fase 5): se un compagno mi ha avvisato via wireless
        # che ha già preso lui l'oggetto, abortisco immediatamente il viaggio!
        if self.local_map.get(self.target_obj, {}).get('status') == 'TAKEN':
            self.state = 'EXPLORE'
            self.target_obj = None
            self.cached_path = []
            return

        # 2. Arrivo sul target
        if self.pos == self.target_obj:
            # Controllo fisico finale: l'oggetto è ancora per terra?
            if env.is_object_at(self.pos[0], self.pos[1]):
                self.carrying = True
                self.carrying_obj = self.target_obj
                self.mark_taken(self.pos[0], self.pos[1])
                env.pick_up_object(self.pos[0], self.pos[1]) # Rimuove l'oggetto dal terreno!
                
                self.target_obj = self.nearest_entrance(env)
                self.cached_path = astar(env, self.pos, self.target_obj)
                self.state = 'RETURN_TO_WAREHOUSE'
            else:
                # Falso allarme! L'oggetto è stato preso da un compagno fuori raggio radar.
                # Me lo segno come TAKEN per non tornarci più e riprendo l'esplorazione.
                self.mark_taken(self.pos[0], self.pos[1]) 
                self.state = 'EXPLORE'
                self.target_obj = None
                self.cached_path = []
            return

        # 3. Movimento normale verso il target (con fix anti-deadlock)
        if not self.cached_path:
            self.cached_path = astar(env, self.pos, self.target_obj)
        
        if self.cached_path:
            if self.cached_path[0] == self.pos:
                self.cached_path.pop(0)
                
            if self.cached_path:
                next_step = self.cached_path[0]
                if self._try_move(env, next_step[0], next_step[1], tick):
                    self.cached_path.pop(0)

    def _handle_return_to_warehouse(self, env, tick):
        if self.pos == self.target_obj:
            env.log_traffic(self.pos[0], self.pos[1])
            self.state = 'DELIVER'
            wh = env._warehouse_of(self.pos[0], self.pos[1], 'entrance')
            if wh:
                self.target_obj = tuple(wh['exit'])
                self.cached_path = astar(env, self.pos, self.target_obj)
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

    def _handle_deliver(self, env, tick):
        if not self.cached_path:
            self.cached_path = astar(env, self.pos, self.target_obj)
            
        if self.cached_path:
            # FIX: Rimuove la cella di partenza 
            if self.cached_path[0] == self.pos:
                self.cached_path.pop(0)
                
            if self.cached_path:
                next_step = self.cached_path[0]
                if self._try_move(env, next_step[0], next_step[1], tick):
                    self.cached_path.pop(0)
                    
        # Consegna effettiva solo al target
        if self.pos == self.target_obj:
            if self.carrying_obj:
                env.deliver_object(self.carrying_obj[0], self.carrying_obj[1])
                self.carrying = False
                self.carrying_obj = None
                
            env.log_traffic(self.pos[0], self.pos[1])
            self.state = 'EXPLORE'
            self.target_obj = None
            self.cached_path = []

    def _handle_return_safe(self, env, tick):
        if self.carrying:
            self.carrying = False
            self.mark_abandoned(self.pos[0], self.pos[1], tick)
            self.carrying_obj = None

            env.drop_abandoned_object(self.pos[0], self.pos[1])

        if self.pos == self.target_obj:
            self.state = 'STANDBY' 
            return

        if not self.cached_path:
            self.cached_path = astar(env, self.pos, self.target_obj)
            
        if self.cached_path:
            # FIX: Rimuove la cella di partenza
            if self.cached_path[0] == self.pos:
                self.cached_path.pop(0)
                
            if self.cached_path:
                next_step = self.cached_path[0]
                if self._try_move(env, next_step[0], next_step[1], tick):
                    self.cached_path.pop(0)

class Worker2(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)

    def _apply_congestion_avoidance(self, env):
        if not STIGMA_ON or not self.cached_path:
            return
        count = detect_agents_in_radius(env.occupancy, self.pos[0], self.pos[1], COMM_RADIUS)
        if count >= 2:
            next_step = self.cached_path[0]
            env.stigma_map[next_step[0]][next_step[1]] += CONGESTION_MALUS
            self.cached_path = astar(env, self.pos, self.target_obj, stigma_map=env.stigma_map)

    def _handle_move_to_object(self, env, tick):
        self._apply_congestion_avoidance(env)
        super()._handle_move_to_object(env, tick)

    def _handle_return_to_warehouse(self, env, tick):
        self._apply_congestion_avoidance(env)
        super()._handle_return_to_warehouse(env, tick)


class Worker3(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.ignored_targets = set()

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

        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        if self.state == 'DEPLOY':
            self._handle_deploy(env, tick)
        elif self.state == 'EXPLORE':
            self._handle_explore(env, tick)
        elif self.state == 'MOVE_TO_OBJECT':
            self._handle_move_to_object(env, tick)
        elif self.state == 'RETURN_TO_WAREHOUSE':
            self._handle_return_to_warehouse(env, tick)
        elif self.state == 'DELIVER':
            self._handle_deliver(env, tick)

    def _handle_explore(self, env, tick):
        best_target = None
        for cell, data in self.local_map.items():
            if data.get('status') == 'FOUND' and cell not in self.ignored_targets:
                d_obj = real_distance(env, self.pos, cell)
                entrance = self.nearest_entrance(env)
                d_wh = real_distance(env, cell, entrance) if entrance else float('inf')
                
                if self.battery > (d_obj + d_wh) * ENERGY_MARGIN:
                    best_target = cell
                    break
                else:
                    self.ignored_targets.add(cell)
        
        if best_target:
            self.target_obj = best_target
            self.state = 'MOVE_TO_OBJECT'
            self.cached_path = astar(env, self.pos, self.target_obj)
            return

        frontier = []
        for (r, c), data in self.local_map.items():
            if data.get('status') == 'VISITED':
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) not in self.local_map and env.is_walkable(nr, nc, r, c):
                        frontier.append((nr, nc))
        
        # Ottimizzazione Worker3: ricerca rapida
        if frontier:
            frontier.sort(key=lambda x: abs(x[0] - self.pos[0]) + abs(x[1] - self.pos[1]))
            target_cell = frontier[0]
            path = astar(env, self.pos, target_cell)
            if path and len(path) > 1:
                next_step = path[1]
                self._try_move(env, next_step[0], next_step[1], tick)
            return
            
        direzioni = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(direzioni)
        for dr, dc in direzioni:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if self._try_move(env, nr, nc, tick):
                break