import json
import os

class Logger:
    def __init__(self):
        self.events = []
        self.exploration_stats = {} # Salverà % esplorazione a tick 100, 250, 500

    def log(self, tick, agent):
        self.events.append({
            'tick': tick,
            'id': agent.id,
            'pos': list(agent.pos),
            'battery': agent.battery,
            'carrying': agent.carrying,
            'state': agent.state
        })

    def record_exploration(self, tick, active_agents, total_walkable):
        """Calcola l'unione di tutte le mappe locali degli agenti"""
        explored = set()
        for a in active_agents:
            explored.update(a.local_map.keys())
        
        percent = (len(explored) / total_walkable * 100) if total_walkable > 0 else 0
        self.exploration_stats[f'tick_{tick}'] = percent

    def dump(self, path, env, final_tick):
        """Salva in un singolo shot a fine simulazione"""
        # Calcolo fallimenti critici
        critical_failures = sum(1 for a in env.active_agents if a.state == 'DEAD' and a.battery <= 0)
        
        # Calcolo energia media consumata
        from src.config import BATTERY_INITIAL, NUM_AGENTS
        num_agents = NUM_AGENTS if NUM_AGENTS > 0 else len(env.active_agents)
        if num_agents == 0: num_agents = 1 # Evita divisione per zero
        
        avg_energy = sum((BATTERY_INITIAL - a.battery) for a in env.active_agents) / num_agents

        metrics = {
            'ticks_total': final_tick,
            'delivered': env.delivered,
            'critical_failures': critical_failures,
            'avg_energy_consumed': avg_energy,
            'exploration_percent': self.exploration_stats,
            'traffic_log': {str(k): v for k, v in env.traffic_log.items()} # Convertito in stringa per JSON
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump({'metrics': metrics, 'events': self.events}, f, indent=2)