from src.config import BATTERY_INITIAL, ENERGY_MARGIN
from src.pathfinding import real_distance

def manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

class BaseAgent:
    def __init__(self, agent_id):
        self.id = agent_id
        self.state = 'STANDBY'  # Lo stato iniziale prima del DEPLOY
        self.pos = (0, 0)
        self.battery = BATTERY_INITIAL
        self.carrying = False
        self.carrying_obj = None
        self.local_map = {}
        self.cached_path = []

    def nearest_entrance(self, env):
        """Trova la cella ENTRANCE più vicina usando la Distanza di Manhattan (Euristica veloce)."""
        min_dist = float('inf')
        best_entrance = None
        for wh in env.warehouses:
            er, ec = wh['entrance']
            dist = manhattan_distance(self.pos, (er, ec))
            if dist < min_dist:
                min_dist = dist
                best_entrance = (er, ec)
        return best_entrance

    def check_battery(self, env):
        """Commuta in RETURN_SAFE per mettersi in salvo prima di morire."""
        if self.state in ['RETURN_SAFE', 'DEAD']:
            return # Se sta già scappando o è morto, ignora.
            
        target = self.nearest_entrance(env)
        if not target: return
            
        dist = manhattan_distance(self.pos, target)
        # Se la batteria basta a malapena per il ritorno + margine di sicurezza
        if self.battery <= (dist * ENERGY_MARGIN) + 5: 
            self.state = 'RETURN_SAFE'
            self.target_obj = target
            self.cached_path = [] # Forza ricalcolo

    def decide_action(self, env, tick):
        """Metodo astratto che verrà sovrascritto da Scout e Worker."""
        raise NotImplementedError("Questo metodo deve essere implementato dalle sottoclassi")

    def merge_knowledge(self, incoming_map, tick):
        """Sincronizza la mappa locale con una in arrivo, rispettando i timestamp."""
        for cell, data in incoming_map.items():
            existing = self.local_map.get(cell)
            # Priorità assoluta: se l'oggetto è già stato preso, non sovrascrivere mai
            if existing and existing['status'] == 'TAKEN':
                continue
                
            # Aggiorna se non avevamo il dato, o se il nuovo dato è più fresco
            if existing is None or data['ts'] > existing['ts']:
                self.local_map[cell] = data

    def mark_taken(self, r, c):
        """Marca un oggetto come raccolto con timestamp infinito."""
        self.local_map[(r, c)] = {'status': 'TAKEN', 'ts': float('inf')}

    def mark_abandoned(self, r, c, tick):
        """Marca un oggetto come abbandonato per esaurimento batteria."""
        self.local_map[(r, c)] = {'status': 'ABANDONED', 'ts': tick}

    def _yield_step(self, env, tick):
        """L'agente a bassa priorità tenta di cedere il passo spostandosi su una cella libera adiacente."""
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if env.is_walkable(nr, nc, self.pos[0], self.pos[1]) and (nr, nc) not in env.occupancy:
                # Cede il passo spostandosi lateralmente o all'indietro
                env.occupancy.remove(self.pos)
                self.pos = (nr, nc)
                env.occupancy.add(self.pos)
                
                # Invalida il path corrente (dovrà ricalcolare la strada dal nuovo punto)
                self.cached_path = []
                self.local_map[self.pos] = {'status': 'VISITED', 'ts': tick}
                return True
        return False # Nessuno spazio per cedere il passo (stallo totale)