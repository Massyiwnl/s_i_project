import json
import os
# FIX: import spostato in cima al file invece di essere dentro il metodo dump.
# La versione originale nascondeva questa dipendenza: guardando gli import
# del modulo sembrava dipendere solo da json e os, mentre in realta' aveva
# una dipendenza implicita da src.config che emergeva solo a runtime.
from src.config import BATTERY_INITIAL, NUM_AGENTS


class Logger:
    def __init__(self):
        self.events = []
        self.exploration_stats = {}  # Salvera' % esplorazione a tick 100, 250, MAX-1

    def log(self, tick, agent):
        """Registra lo stato dell'agente al tick corrente."""
        self.events.append({
            'tick': tick,
            'id': agent.id,
            'agent_type': agent.__class__.__name__,
            'pos': list(agent.pos),
            'battery': agent.battery,
            'carrying': agent.carrying,
            'state': agent.state
        })

    def record_exploration(self, tick, active_agents, total_walkable):
        """Calcola l'unione di tutte le mappe locali degli agenti."""
        explored = set()
        for a in active_agents:
            if hasattr(a, 'local_map'):
                explored.update(a.local_map.keys())

        percent = (len(explored) / total_walkable * 100) if total_walkable > 0 else 0
        self.exploration_stats[f'tick_{tick}'] = round(percent, 2)

    def dump(self, path, env, final_tick):
        """Salva il log completo in un singolo shot a fine simulazione."""
        critical_failures = sum(
            1 for a in env.active_agents if a.state == 'DEAD' and a.battery <= 0
        )

        num_agents = NUM_AGENTS if NUM_AGENTS > 0 else len(env.active_agents)
        if num_agents == 0:
            num_agents = 1

        avg_energy = (
            sum((BATTERY_INITIAL - a.battery) for a in env.active_agents) / num_agents
        )

        # FIX: chiavi traffic_log serializzate come str([r, c]) invece di str((r, c)).
        # La versione originale produceva chiavi tipo "(5, 3)" che non erano
        # rileggibili come coordinate senza parsing manuale della stringa.
        # La nuova versione produce "[5, 3]" facilmente parsabile con json.loads().
        metadata = {
            'ticks_total': final_tick,
            'delivered': env.delivered,
            'critical_failures': critical_failures,
            'avg_energy_consumed': round(avg_energy, 2),
            'exploration_percent': self.exploration_stats,
            'traffic_log': {str(list(k)): v for k, v in env.traffic_log.items()}
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'metadata': metadata, 'events': self.events}, f, indent=2)