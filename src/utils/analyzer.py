import json
import os
import csv

class SimulationAnalyzer:
    def __init__(self, log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        if isinstance(self.data, list):
            self.events = self.data
            self.metadata = {}
        else:
            self.events = self.data.get('events', [])

    def generate_tabular_report(self, output_path):
        """Genera un report leggibile con gli eventi salienti dello sciame."""
        report = []
        header = f"{'TICK':<8} | {'ID':<4} | {'EVENTO':<25} | {'POSIZIONE':<12} | {'BATT':<6} | {'CARICO'}"
        report.append(header)
        report.append("-" * len(header))

        last_states = {}
        last_carrying = {}

        for e in self.events:
            idx = e['id']
            state = e['state']
            pos = f"({e['pos'][0]},{e['pos'][1]})"
            batt = e['battery']
            carrying = "SI" if e['carrying'] else "NO"

            # Logica per decidere cosa mostrare nella tabella
            is_interesting = False
            desc = ""

            # 1. Cambio di stato (es. da EXPLORE a MOVE_TO_OBJECT)
            if idx not in last_states or last_states[idx] != state:
                is_interesting = True
                desc = f"Stato: {state}"
                last_states[idx] = state

            # 2. Raccolta o Consegna (cambio flag carrying)
            if idx in last_carrying and last_carrying[idx] != e['carrying']:
                is_interesting = True
                desc = "RACCOLTA OGGETTO" if e['carrying'] else "CONSEGNA EFFETTUATA"
                last_carrying[idx] = e['carrying']
            else:
                last_carrying[idx] = e['carrying']

            # 3. Emergenza batteria (prima volta che va sotto soglia critica)
            if state == "LOW_BATTERY" and (idx not in last_states or last_states.get(f"low_{idx}") is None):
                is_interesting = True
                desc = "!!! EMERGENCY LOW BATT !!!"
                last_states[f"low_{idx}"] = True

            if is_interesting:
                line = f"{e['tick']:<8} | {idx:<4} | {desc:<25} | {pos:<12} | {batt:<6} | {carrying}"
                report.append(line)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
        print(f"Report tabellare generato con successo: {output_path}")

    def get_summary_metrics(self):
        """Estrae metriche riassuntive per il feedback rapido."""
        if not self.events:
            return {"Errore": "Nessun dato trovato"}
            
        final_tick = self.events[-1]['tick']
        # Contiamo quante volte compare un cambio verso 'SI' nel flag carrying
        # per stimare gli oggetti presi (approssimativo ma utile)
        
        return {
            "Tick Totali": final_tick,
            "Eventi Registrati": len(self.events),
            "Agenti Attivi": len(set(e['id'] for e in self.events))
        }