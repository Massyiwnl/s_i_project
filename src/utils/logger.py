import json
import os

class Logger:
    def __init__(self):
        self.history = []

    def log(self, tick, agent):
        """Salva uno snapshot (fotografia) dello stato dell'agente."""
        snapshot = {
            "tick": tick,
            "id": agent.id,
            "pos": [agent.pos[0], agent.pos[1]],
            "state": agent.state,
            "battery": agent.battery,
            "carrying": agent.carrying
        }
        self.history.append(snapshot)

    def dump(self, path):
        """Salva l'intero storico in un file JSON a fine simulazione."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2)
        print(f"Log salvato correttamente in: {path}")