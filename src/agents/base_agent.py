from src.config import BATTERY_INITIAL, ENERGY_MARGIN
from src.pathfinding import real_distance

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
        """Trova la cella ENTRANCE più vicina usando la distanza reale."""
        min_dist = float('inf')
        best_entrance = None
        for wh in env.warehouses:
            er, ec = wh['entrance']
            dist = real_distance(env, self.pos, (er, ec))
            if dist < min_dist:
                min_dist = dist
                best_entrance = (er, ec)
        return best_entrance

    def check_battery(self, env):
        """Controlla se la batteria è sotto la soglia critica e commuta lo stato."""
        target = self.nearest_entrance(env)
        if not target:
            return
            
        dist = real_distance(env, self.pos, target)
        if self.battery < dist * ENERGY_MARGIN:
            self.state = 'LOW_BATTERY'

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