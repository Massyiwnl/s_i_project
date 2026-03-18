import random
from src.config import (
    BATTERY_INITIAL, ENERGY_MARGIN, COMM_RADIUS, VISION_RADIUS,
    STRESS_MAX, STRESS_RANDOM_STEPS, STIGMA_ON, EXPLORE_PENALTY_WEIGHT
)
from src.communication import get_agents_in_radius, create_inform_message
from src.sensors import get_visible_objects
from src.decision_making import get_valid_local_moves


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
        self.current_intention = None

    def decide_action(self, env, tick):
        raise NotImplementedError("Questo metodo deve essere implementato dalle sottoclassi")

    def clear_reservation(self, env):
        """O(1): rimuove solo la prenotazione corrente dell'agente."""
        if self.current_intention is not None:
            env.intentions.pop(self.current_intention, None)
            self.current_intention = None

    def _sync_with_neighbors(self, env, tick):
        """
        Scambio di conoscenza con i vicini tramite messaggi FIPA-ACL (INFORM).
        Filtra per caller_id=self.id invece che per posizione.
        """
        neighbors = get_agents_in_radius(env, self.pos, COMM_RADIUS, caller_id=self.id)
        for neighbor in neighbors:
            msg = create_inform_message(
                sender_id=neighbor.id,
                receiver_id=self.id,
                content={'map': neighbor.local_map, 'ts': tick}
            )
            if msg['performative'] == 'INFORM':
                self.merge_knowledge(msg['content']['map'], tick)

    def _scan_environment(self, env, tick):
        """
        Aggiorna la mappa locale con cio' che l'agente percepisce nel raggio visivo.

        Fase 1: salva gli oggetti visibili come FOUND.
        Fase 2: mappa le celle vuote percorribili come EMPTY (fix % esplorazione).
        La navigazione dei Worker non e' influenzata: _has_found_object cerca
        solo FOUND e ABANDONED, mai EMPTY.

        Il deposito di pheromone_object sugli oggetti visibili e' responsabilita'
        esclusiva degli Scout (override in scouts.py). I Worker non depositano
        mai pheromone_object: questo garantisce che il segnale abbia un unico
        significato — "qui c'e' un oggetto scoperto da uno Scout" — senza
        confondersi con le scie di ritorno al magazzino.
        """
        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            if obj not in self.local_map or self.local_map[obj].get('status') != 'TAKEN':
                self.local_map[obj] = {'status': 'FOUND', 'ts': tick}

        for dr in range(-VISION_RADIUS, VISION_RADIUS + 1):
            for dc in range(-VISION_RADIUS, VISION_RADIUS + 1):
                if abs(dr) + abs(dc) <= VISION_RADIUS:
                    nr, nc = self.pos[0] + dr, self.pos[1] + dc
                    if env.is_walkable(nr, nc):
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
        """Soglia = BATTERY_INITIAL * 0.10 * ENERGY_MARGIN = 60."""
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
        """Tentativo di sblocco casuale, limitato a STRESS_RANDOM_STEPS tentativi."""
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
                self.current_intention = (nr, nc)
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
        self.current_intention = (nr, nc)

        if self.pos in env.occupancy:
            env.occupancy.remove(self.pos)
        self.pos = (nr, nc)
        env.occupancy.add(self.pos)
        self.stuck_ticks = 0

        # Deposito feromone esplorativo: tutti gli agenti, ad ogni spostamento.
        # Serve alla repulsione anti-loop (Configurazione C2) e alla heatmap.
        env.pheromone_explore[self.pos[0]][self.pos[1]] += 10.0
        env.active_pheromone_cells.add(self.pos)

        # NOTA: pheromone_object NON viene piu' depositato qui.
        # Il deposito e' responsabilita' esclusiva degli Scout in _scan_environment:
        # solo loro lo depositano sulla cella esatta degli oggetti scoperti.
        # Questo garantisce che il segnale pheromone_object significhi sempre e solo
        # "qui c'e' un oggetto non ancora raccolto", senza ambiguita' con le scie
        # di ritorno al magazzino che producevano il paradosso ACO precedente.

        # Registro del passaggio per la heatmap dei colli di bottiglia.
        env.log_movement(self.pos[0], self.pos[1])

        return True

    def _move_towards_target(self, env, target):
        """
        Movimento diretto verso un target con anti-loop stigmergico.
        Rispetta STIGMA_ON e usa EXPLORE_PENALTY_WEIGHT da config.
        """
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
            penalty = env.pheromone_explore[nr][nc] * EXPLORE_PENALTY_WEIGHT if STIGMA_ON else 0.0
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