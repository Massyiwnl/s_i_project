import random
from src.config import BATTERY_INITIAL, ENERGY_MARGIN, COMM_RADIUS, VISION_RADIUS
from src.communication import get_agents_in_radius, create_inform_message
from src.sensors import get_visible_objects
from src.pathfinding import get_valid_local_moves 

def manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

class BaseAgent:
    def __init__(self, agent_id):
        self.id = agent_id
        self.state = 'EXPLORE' 
        self.pos = (0, 0)
        self.battery = BATTERY_INITIAL
        self.carrying = False
        self.carrying_obj = None
        self.local_map = {}
        self.stuck_ticks = 0 

    def decide_action(self, env, tick):
        raise NotImplementedError("Questo metodo deve essere implementato dalle sottoclassi")

    def clear_reservation(self, env):
        keys_to_delete = [k for k, v in env.intentions.items() if v == self.id]
        for k in keys_to_delete:
            del env.intentions[k]

    def _sync_with_neighbors(self, env, tick):
        neighbors = get_agents_in_radius(env, self.pos, COMM_RADIUS)
        for neighbor in neighbors:
            msg = create_inform_message(
                sender_id=neighbor.id, 
                receiver_id=self.id, 
                content={'map': neighbor.local_map, 'ts': tick}
            )
            if msg['performative'] == 'INFORM' and msg['receiver'] == self.id:
                self.merge_knowledge(msg['content']['map'], tick)

    def _scan_environment(self, env, tick):
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

    def merge_knowledge(self, incoming_map, tick):
        for cell, data in incoming_map.items():
            existing = self.local_map.get(cell)
            if existing and existing['status'] == 'TAKEN':
                continue
            if existing is None or data['ts'] > existing['ts']:
                self.local_map[cell] = data

    def mark_taken(self, r, c):
        self.local_map[(r, c)] = {'status': 'TAKEN', 'ts': float('inf')}

    def mark_abandoned(self, r, c, tick):
        self.local_map[(r, c)] = {'status': 'ABANDONED', 'ts': tick}

    def check_battery(self, env):
        if self.state in ['DEAD', 'FINISHED']: 
            self.clear_reservation(env)
            if self.pos in env.occupancy:
                env.occupancy.remove(self.pos)
            return
        
        if self.battery < 50: 
            if self.carrying:
                self.state = 'RETURN_HOME' 
            else:
                self.state = 'RETURN_BASE' 

    def _dodge_step(self, env):
        valid_moves = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
                valid_moves.append((nr, nc))
                
        random.shuffle(valid_moves) 
        for nr, nc in valid_moves:
            if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions:
                self.clear_reservation(env) 
                env.intentions[(nr, nc)] = self.id
                if self.pos in env.occupancy:
                    env.occupancy.remove(self.pos)
                self.pos = (nr, nc)
                env.occupancy.add(self.pos)
                self.stuck_ticks = 0 
                return True
        return False

    def _try_move(self, env, nr, nc):
        if nr == self.pos[0] and nc == self.pos[1]:
            self.stuck_ticks += 1
            return True

        if not env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
            self.stuck_ticks += 1
            return False

        if (nr, nc) in env.intentions and env.intentions[(nr, nc)] != self.id:
            self.stuck_ticks += 1
            return False 

        if (nr, nc) in env.occupancy and (nr, nc) != self.pos:
            self.stuck_ticks += 1
            return False

        self.clear_reservation(env) 
        env.intentions[(nr, nc)] = self.id
        
        if self.pos in env.occupancy:
            env.occupancy.remove(self.pos)
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)
        self.stuck_ticks = 0 

        env.pheromone_explore[self.pos[0]][self.pos[1]] += 10.0
        if self.carrying:
            env.pheromone_object[self.pos[0]][self.pos[1]] += 20.0

        return True

    def _move_towards_target(self, env, target):
        valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
        if not valid_moves: return
        
        free_moves = [(nr, nc) for nr, nc in valid_moves if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
        candidate_moves = free_moves if free_moves else valid_moves
        
        best_moves = []
        min_score = float('inf')
        
        for nr, nc in candidate_moves:
            # 1. Distanza base da minimizzare
            dist = abs(nr - target[0]) + abs(nc - target[1])
            
            # --- FIX BUG DEL LOOP (Stigmergia per aggirare ostacoli) ---
            # Aggiungiamo il feromone esplorativo come "penalità" (come se la cella fosse più lontana).
            # L'agente si ricorderà di essere già stato qui ed eviterà di tornare indietro all'infinito!
            penalty = env.pheromone_explore[nr][nc] * 0.5 
            
            score = dist + penalty
            
            if score < min_score:
                min_score = score
                best_moves = [(nr, nc)]
            # Usiamo abs() per confronti sicuri tra numeri con la virgola (float)
            elif abs(score - min_score) < 0.0001: 
                best_moves.append((nr, nc))
                
        if best_moves:
            nr, nc = random.choice(best_moves)
            self._try_move(env, nr, nc)

    def _handle_return_base(self, env):
        dist_to_base = abs(self.pos[0]) + abs(self.pos[1])
        
        if dist_to_base == 0 or (dist_to_base <= 3 and self.stuck_ticks > 2):
            self.state = 'FINISHED' 
            self.clear_reservation(env)
            if self.pos in env.occupancy:
                env.occupancy.remove(self.pos)
            return
            
        valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
        if not valid_moves: return
        
        free_moves = [(nr, nc) for nr, nc in valid_moves if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
        candidate_moves = free_moves if free_moves else valid_moves
        
        best_moves = []
        max_val = float('-inf')
        for nr, nc in candidate_moves:
            val = env.pheromone_base[nr][nc] 
            if val > max_val:
                max_val = val
                best_moves = [(nr, nc)]
            elif val == max_val:
                best_moves.append((nr, nc))
                
        if best_moves:
            nr, nc = random.choice(best_moves)
            self._try_move(env, nr, nc)