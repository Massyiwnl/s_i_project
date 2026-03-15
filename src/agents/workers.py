from src.agents.base_agent import BaseAgent
from src.decision_making import evaluate_utility, get_valid_local_moves
from src.config import STRESS_MAX, WAREHOUSE, ENTRANCE, EXIT, EMPTY,EMERGENCY_DROP_BATTERY


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

        # FIX: usa STRESS_MAX // 2 (=7) da config invece dell'8 hardcoded
        if self.stuck_ticks > STRESS_MAX // 2:
            if self._dodge_step(env):
                return

        # Pickup opportunistico: se l'agente cammina sopra un oggetto
        # durante stati diversi da RETURN_BASE e RETURN_HOME.
        # FIX: aggiunto RETURN_HOME alla lista di stati esclusi per evitare
        # un doppio-pickup dopo che _handle_retrieve ha gia' raccolto l'oggetto.
        if (not self.carrying
                and self.state not in ['RETURN_BASE', 'RETURN_HOME']
                and env.is_object_at(self.pos[0], self.pos[1])):
            self.carrying = True
            self.carrying_obj = self.pos
            self.mark_taken(self.pos[0], self.pos[1])
            env.pick_up_object(self.pos[0], self.pos[1])
            self.target_obj = None
            self.state = 'RETURN_HOME'
            return

        if self.state == 'EXIT_WAREHOUSE':
            if env.grid[self.pos[0]][self.pos[1]] not in [WAREHOUSE, ENTRANCE, EXIT]:
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
        """
        FIX: restituisce l'oggetto piu' vicino (distanza Manhattan) invece del
        primo trovato nell'ordine di iterazione del dizionario. La versione
        originale poteva inviare il worker verso un oggetto lontano ignorandone
        uno adiacente, riducendo l'efficienza della fase di recupero.
        """
        best_obj = None
        best_dist = float('inf')
        for cell, data in self.local_map.items():
            if data.get('status') in ['FOUND', 'ABANDONED']:
                dist = abs(cell[0] - self.pos[0]) + abs(cell[1] - self.pos[1])
                if dist < best_dist:
                    best_dist = dist
                    best_obj = cell
        if best_obj is not None:
            self.target_obj = best_obj
            return True
        self.target_obj = None
        return False

    def _handle_explore(self, env):
        weights = {'home': -0.1, 'explore': 1.0, 'object': 2.0}
        result = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)

    def _handle_retrieve(self, env):
        """
        FIX: raccolta atomica nel tick in cui l'agente raggiunge il target.
        La versione originale segnava TAKEN nella local_map ma non chiamava
        pick_up_object ne' impostava carrying=True nello stesso tick, creando
        una finestra di race condition in cui un altro agente poteva raccogliere
        l'oggetto nel tick intermedio.
        """
        if self.local_map.get(self.target_obj, {}).get('status') == 'TAKEN':
            self.state = 'EXPLORE'
            self.target_obj = None
            return

        if self.pos == self.target_obj:
            if env.is_object_at(self.pos[0], self.pos[1]):
                # Raccolta atomica: pickup + aggiornamento stato nello stesso tick
                self.carrying = True
                self.carrying_obj = self.pos
                self.mark_taken(self.pos[0], self.pos[1])
                env.pick_up_object(self.pos[0], self.pos[1])
                self.state = 'RETURN_HOME'
            else:
                # Oggetto gia' preso da un altro agente nel frattempo
                self.mark_taken(self.pos[0], self.pos[1])
                self.state = 'EXPLORE'
            self.target_obj = None
            return

        self._move_towards_target(env, self.target_obj)

    def _handle_return_home(self, env, tick):
        # Consegna: l'agente e' sulla cella di tipo WAREHOUSE (2)
        if env.grid[self.pos[0]][self.pos[1]] == WAREHOUSE and self.carrying:
            env.deliver_object(self.carrying_obj[0], self.carrying_obj[1])
            env.log_traffic(self.pos[0], self.pos[1])
            self.carrying = False
            self.carrying_obj = None
            self.state = 'EXIT_WAREHOUSE'
            return

        # Se sulla cella ENTRANCE (3), cerca la cella WAREHOUSE adiacente
        if env.grid[self.pos[0]][self.pos[1]] == ENTRANCE:
            valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
            for nr, nc in valid_moves:
                if env.grid[nr][nc] == 2:
                    self._try_move(env, nr, nc)
                    return

        # Emergenza batteria: abbandono forzato
        if self.battery <= EMERGENCY_DROP_BATTERY and self.carrying:
            self.carrying = False
            self.mark_abandoned(self.pos[0], self.pos[1], tick)
            env.drop_abandoned_object(self.pos[0], self.pos[1])
            self.carrying_obj = None
            self.state = 'RETURN_BASE'
            return # Interrompiamo subito la funzione, non c'è più motivo di valutare i pesi per il magazzino

        weights = {'home': 5.0, 'explore': 0.5, 'object': 0.0}
        result = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)

    def _handle_exit_warehouse(self, env):
        """
        FIX: usa self.pos == wh['entrance'] e self.pos == wh['exit'] per
        confrontare tuple con tuple (dopo la normalizzazione in environment.load).
        La versione originale usava list(self.pos) == wh['entrance'] che
        falliva dopo la normalizzazione a tuple.
        """
        current_wh = None
        for wh in env.warehouses:
            # wh['area'] e' ancora lista di liste, quindi usiamo list(self.pos)
            # wh['entrance'] e wh['exit'] sono tuple dopo load(), quindi self.pos
            if (list(self.pos) in wh['area']
                    or self.pos == wh['entrance']
                    or self.pos == wh['exit']):
                current_wh = wh
                break

        if current_wh:
            target_exit = current_wh['exit']  # gia' tuple dopo normalizzazione
            if self.pos != target_exit:
                self._move_towards_target(env, target_exit)
            else:
                valid_moves = get_valid_local_moves(env, self.pos[0], self.pos[1])
                for nr, nc in valid_moves:
                    if env.grid[nr][nc] == EMPTY:
                        self._try_move(env, nr, nc)
                        break
        else:
            self.state = 'EXPLORE'


class Worker2(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)

    def _handle_explore(self, env):
        # Strategia aggressiva: priorita' agli oggetti, ignora home
        weights = {'home': 0.0, 'explore': 0.3, 'object': 3.0}
        result = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)


class Worker3(Worker1):
    def __init__(self, agent_id):
        super().__init__(agent_id)

    def _handle_explore(self, env):
        # Strategia bilanciata: buona esplorazione e buona attenzione agli oggetti
        weights = {'home': 0.5, 'explore': 0.8, 'object': 2.5}
        result = evaluate_utility(env, self.pos[0], self.pos[1], weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)