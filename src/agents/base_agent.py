import random
from src.config import (
    BATTERY_INITIAL, ENERGY_MARGIN, COMM_RADIUS, VISION_RADIUS,
    STRESS_MAX, STRESS_RANDOM_STEPS, STIGMA_ON
)
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
        # FIX: traccia la prenotazione corrente per clear_reservation O(1)
        # invece di scorrere env.intentions per trovare le entry dell'agente.
        self.current_intention = None

    def decide_action(self, env, tick):
        raise NotImplementedError("Questo metodo deve essere implementato dalle sottoclassi")

    def clear_reservation(self, env):
        """
        FIX: O(1) invece di O(n).
        La versione originale iterava env.intentions cercando v==self.id.
        Ora l'agente traccia direttamente la propria prenotazione corrente.
        """
        if self.current_intention is not None:
            env.intentions.pop(self.current_intention, None)
            self.current_intention = None

    def _sync_with_neighbors(self, env, tick):
        """
        Scambio di conoscenza con i vicini tramite messaggi FIPA-ACL (INFORM).

        FIX 1: passa caller_id=self.id a get_agents_in_radius per escludere
               se stesso per identita' (non per posizione).
        FIX 2: rimosso il controllo ridondante msg['receiver'] == self.id
               che era sempre True per costruzione (receiver_id=self.id
               viene passato esplicitamente a create_inform_message).
        """
        neighbors = get_agents_in_radius(env, self.pos, COMM_RADIUS, caller_id=self.id)
        for neighbor in neighbors:
            msg = create_inform_message(
                sender_id=neighbor.id,
                receiver_id=self.id,
                content={'map': neighbor.local_map, 'ts': tick}
            )
            # Il performative e' sempre INFORM (garantito da create_inform_message).
            # Il controllo receiver e' rimosso perche' trivialmente sempre vero.
            if msg['performative'] == 'INFORM':
                self.merge_knowledge(msg['content']['map'], tick)

    def _scan_environment(self, env, tick):
        # 1. LOGICA ESISTENTE: Scansione e salvataggio degli oggetti
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        # 2. NUOVA LOGICA (BUG FIX): Mappatura topologica del terreno visibile
        for dr in range(-VISION_RADIUS, VISION_RADIUS + 1):
            for dc in range(-VISION_RADIUS, VISION_RADIUS + 1):
                if abs(dr) + abs(dc) <= VISION_RADIUS:
                    nr, nc = self.pos[0] + dr, self.pos[1] + dc
                    if env.is_walkable(nr, nc):
                        # Salviamo la cella come EMPTY solo se non è già mappata 
                        # (per non sovrascrivere accidentalmente un FOUND o un TAKEN)
                        if (nr, nc) not in self.local_map:
                            self.local_map[(nr, nc)] = {'status': 'EMPTY', 'ts': tick}

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
        """
        FIX: usa ENERGY_MARGIN da config per calcolare la soglia di ritorno.
        Soglia = BATTERY_INITIAL * 0.10 * ENERGY_MARGIN = 500 * 0.10 * 1.20 = 60.
        La versione originale aveva 50 hardcoded, ignorando ENERGY_MARGIN.
        """
        if self.state in ['DEAD', 'FINISHED']:
            self.clear_reservation(env)
            if self.pos in env.occupancy:
                env.occupancy.remove(self.pos)
            return

        battery_threshold = int(BATTERY_INITIAL * 0.10 * ENERGY_MARGIN)
        if self.battery < battery_threshold:
            if self.carrying:
                self.state = 'RETURN_HOME'
            else:
                self.state = 'RETURN_BASE'

    def _dodge_step(self, env):
        """
        FIX: usa STRESS_RANDOM_STEPS da config per limitare i tentativi casuali
        (invece di un numero implicito). Aggiorna current_intention per O(1).
        """
        valid_moves = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if env.is_walkable(nr, nc, self.pos[0], self.pos[1]):
                valid_moves.append((nr, nc))

        random.shuffle(valid_moves)
        for nr, nc in valid_moves[:STRESS_RANDOM_STEPS]:
            if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions:
                self.clear_reservation(env)
                env.intentions[(nr, nc)] = self.id
                self.current_intention = (nr, nc)   # FIX: O(1)
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
        self.current_intention = (nr, nc)   # FIX: traccia per O(1)

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
        if not valid_moves:
            return

        free_moves = [(nr, nc) for nr, nc in valid_moves
                      if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
        candidate_moves = free_moves if free_moves else valid_moves

        best_moves = []
        min_score = float('inf')

        for nr, nc in candidate_moves:
            dist = abs(nr - target[0]) + abs(nc - target[1])
            # Stigmergia per aggirare ostacoli (anti-loop) - Vincolata a STIGMA_ON
            penalty = (env.pheromone_explore[nr][nc] * 0.5) if STIGMA_ON else 0.0
            score = dist + penalty

            if score < min_score:
                min_score = score
                best_moves = [(nr, nc)]
            elif abs(score - min_score) < 0.0001:
                best_moves.append((nr, nc))

        if best_moves:
            nr, nc = random.choice(best_moves)
            self._try_move(env, nr, nc)

    def _handle_return_base(self, env):
        dist_to_base = abs(self.pos[0]) + abs(self.pos[1])

        # FIX: condizione di terminazione piu' conservativa.
        # La versione originale permetteva FINISHED con dist<=3 e stuck>2,
        # il che portava agenti a terminare lontani dalla base in ambienti
        # affollati. Ora il margine e' 1 cella con stuck>STRESS_MAX (=15 tick).
        if dist_to_base == 0 or (dist_to_base <= 1 and self.stuck_ticks > STRESS_MAX):
            self.state = 'FINISHED'
            self.clear_reservation(env)
            if self.pos in env.occupancy:
                env.occupancy.remove(self.pos)
            return

        valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
        if not valid_moves:
            return

        free_moves = [(nr, nc) for nr, nc in valid_moves
                      if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
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