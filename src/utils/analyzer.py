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
            self.metadata = self.data.get('metadata', {})
            
        self.agent_stats = self._compute_agent_stats()

    def _compute_agent_stats(self):
        """Elabora gli eventi per calcolare le statistiche di ogni singolo agente."""
        stats = {}
        
        for e in self.events:
            a_id = e['id']
            if a_id not in stats:
                stats[a_id] = {
                    'id': a_id,
                    'type': e.get('agent_type', 'Unknown'), # Se loggato, altrimenti 'Unknown'
                    'distance_covered': 0,
                    'deliveries': 0,
                    'abandoned': 0,
                    'final_state': e['state'],
                    'battery_remaining': e['battery'],
                    'ticks_alive': 0,
                    'state_counts': {'EXPLORE': 0, 'RETRIEVE': 0, 'RETURN_HOME': 0, 'RETURN_BASE': 0, 'EXIT_WAREHOUSE': 0},
                    '_last_pos': e['pos'],
                    '_last_carrying': e['carrying']
                }
            
            agent = stats[a_id]
            agent['ticks_alive'] += 1
            agent['final_state'] = e['state']
            agent['battery_remaining'] = e['battery']
            
            # Conta il tempo speso in ogni stato
            if e['state'] in agent['state_counts']:
                agent['state_counts'][e['state']] += 1
            else:
                agent['state_counts'][e['state']] = 1
                
            # Calcola la distanza (se la posizione è cambiata)
            if e['pos'] != agent['_last_pos']:
                agent['distance_covered'] += 1
                agent['_last_pos'] = e['pos']
                
            # Calcola consegne e abbandoni basandosi sul flag carrying
            if agent['_last_carrying'] and not e['carrying']:
                # Se ha lasciato l'oggetto in magazzino o base, è una consegna
                if e['state'] in ['EXIT_WAREHOUSE', 'FINISHED', 'EXPLORE']:
                    agent['deliveries'] += 1
                # Se la batteria è bassissima ed era in return home, è un abbandono
                elif e['battery'] <= 2 or e['state'] == 'DEAD':
                    agent['abandoned'] += 1
            
            agent['_last_carrying'] = e['carrying']
            
        return stats

    def generate_agent_stats_csv(self, output_path):
        """Genera un file CSV con le metriche dettagliate per ogni agente."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        headers = [
            'Agent_ID', 'Final_State', 'Battery_Remaining', 'Distance_Covered', 
            'Deliveries', 'Abandoned_Objects', 'Ticks_Alive', 
            'Pct_Explore', 'Pct_ReturnHome'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for a_id, data in self.agent_stats.items():
                ticks = data['ticks_alive']
                pct_explore = round((data['state_counts'].get('EXPLORE', 0) / ticks) * 100, 2) if ticks > 0 else 0
                pct_return = round((data['state_counts'].get('RETURN_HOME', 0) / ticks) * 100, 2) if ticks > 0 else 0
                
                row = [
                    data['id'],
                    data['final_state'],
                    data['battery_remaining'],
                    data['distance_covered'],
                    data['deliveries'],
                    data['abandoned'],
                    data['ticks_alive'],
                    f"{pct_explore}%",
                    f"{pct_return}%"
                ]
                writer.writerow(row)
        print(f"Statistiche Agenti (CSV) salvate in: {output_path}")

    def generate_global_summary_csv(self, output_path, seed, instance):
        """Genera o appende i dati globali della simulazione a un file CSV."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        file_exists = os.path.isfile(output_path)
        
        # Calcolo metriche globali
        total_ticks = self.events[-1]['tick'] if self.events else 0
        total_deliveries = sum(a['deliveries'] for a in self.agent_stats.values())
        total_abandoned = sum(a['abandoned'] for a in self.agent_stats.values())
        dead_agents = sum(1 for a in self.agent_stats.values() if a['final_state'] == 'DEAD')
        total_distance = sum(a['distance_covered'] for a in self.agent_stats.values())
        
        headers = [
            'Instance', 'Seed', 'Total_Ticks', 'Total_Deliveries', 
            'Total_Abandoned', 'Dead_Agents', 'Total_Distance'
        ]
        
        with open(output_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
                
            writer.writerow([
                instance, seed, total_ticks, total_deliveries, 
                total_abandoned, dead_agents, total_distance
            ])
        print(f"Sommario Globale (CSV) aggiornato in: {output_path}")

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