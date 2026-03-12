import random
from src.agents.base_agent import BaseAgent
from src.pathfinding import evaluate_utility, get_valid_local_moves

class Worker1(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.target_obj = None

    def decide_action(self, env, tick):
        if self.state in ['DEAD', 'FINISHED']: 
            self.clear_reservation(env)
            if self.pos in env.occupancy:
                env.occupancy.remove(self.pos)
            return
        
        self.check_battery(env)
        self._sync_with_neighbors(env, tick)
        self._scan_environment(env, tick)
        
        if self.stuck_ticks > 8:
            if self._dodge_step(env):
                return
                
        if not self.carrying and self.state != 'RETURN_BASE' and env.is_object_at(self.pos[0], self.pos[1]):
            self.carrying = True
            self.carrying_obj = self.pos
            self.mark_taken(self.pos[0], self.pos[1])
            env.pick_up_object(self.pos[0], self.pos[1])
            self.target_obj = None
            self.state = 'RETURN_HOME'
            return 
        
        if self.state == 'EXIT_WAREHOUSE':
            if env.grid[self.pos[0]][self.pos[1]] not in [2, 3, 4]:
                self.state = 'EXPLORE'
                self.clear_reservation(env)
        elif self.state not in ['RETURN_HOME', 'RETURN_BASE']:
            if self.carrying:
                self.state = 'RETURN_HOME'
            elif self._has_found_object():
                self.state = 'RETRIEVE'
            else:
                self.state = 'EXPLORE'

        if self.state == 'EXPLORE':
            self._handle_explore(env)
        elif self.state == 'RETRIEVE':
            self._handle_retrieve(env)
        elif self.state == 'RETURN_HOME':
            self._handle_return_home(env, tick)
        elif self.state == 'EXIT_WAREHOUSE':
            self._handle_exit_warehouse(env)
        elif self.state == 'RETURN_BASE':
            self._handle_return_base(env)

    def _has_found_object(self):
        for cell, data in self.local_map.items():
            if data.get('status') == 'FOUND':
                self.target_obj = cell
                return True
        self.target_obj = None
        return False

    def _handle_explore(self, env):
        weights = {'home': -0.1, 'explore': 1.0, 'object': 2.0}
        nr, nc = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        self._try_move(env, nr, nc)

    def _handle_retrieve(self, env):
        if self.local_map.get(self.target_obj, {}).get('status') == 'TAKEN':
            self.state = 'EXPLORE'
            self.target_obj = None
            return

        if self.pos == self.target_obj:
            self.mark_taken(self.pos[0], self.pos[1])
            self.target_obj = None
            self.state = 'EXPLORE'
            return

        self._move_towards_target(env, self.target_obj)

    def _handle_return_home(self, env, tick):
        if env.grid[self.pos[0]][self.pos[1]] == 2 and self.carrying:
            env.deliver_object(self.carrying_obj[0], self.carrying_obj[1])
            env.log_traffic(self.pos[0], self.pos[1])
            self.carrying = False
            self.carrying_obj = None
            self.state = 'EXIT_WAREHOUSE' 
            return
        
        if env.grid[self.pos[0]][self.pos[1]] == 3:
            valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
            for nr, nc in valid_moves:
                if env.grid[nr][nc] == 2:
                    self._try_move(env, nr, nc)
                    return

        if self.battery <= 2 and self.carrying:
            self.carrying = False
            self.mark_abandoned(self.pos[0], self.pos[1], tick)
            env.drop_abandoned_object(self.pos[0], self.pos[1])
            self.carrying_obj = None

        # --- FIX BUG LOOP RITORNO: Peso trasformato da -0.2 a 0.5 ---
        # Avendo un peso negativo in una funzione che SOTTRAE, creavamo una Somma
        # (Attrazione fatale per le proprie tracce).
        # Ora è positivo, quindi garantisce corretta REPULSIONE (evita le scie).
        weights = {'home': 5.0, 'explore': 0.5, 'object': 0.0}
        nr, nc = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        self._try_move(env, nr, nc)

    def _handle_exit_warehouse(self, env):
        current_wh = None
        for wh in env.warehouses:
            if list(self.pos) in wh['area'] or list(self.pos) == wh['entrance'] or list(self.pos) == wh['exit']:
                current_wh = wh
                break
                
        if current_wh:
            target_exit = tuple(current_wh['exit'])
            if self.pos != target_exit:
                self._move_towards_target(env, target_exit)
            else:
                valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
                for nr, nc in valid_moves:
                    if env.grid[nr][nc] == 0:
                        self._try_move(env, nr, nc)
                        break
        else:
            self.state = 'EXPLORE'


class Worker2(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
    
    def _handle_explore(self, env):
        weights = {'home': 0.0, 'explore': 0.3, 'object': 3.0} 
        nr, nc = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        self._try_move(env, nr, nc)

class Worker3(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        
    def _handle_explore(self, env):
        weights = {'home': 0.5, 'explore': 0.8, 'object': 2.5}
        nr, nc = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        self._try_move(env, nr, nc)