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
                    'type': e.get('agent_type', 'Unknown'),
                    'distance_covered': 0,
                    'deliveries': 0,
                    'abandoned': 0,
                    'final_state': e['state'],
                    'battery_remaining': e['battery'],
                    'ticks_alive': 0,
                    'state_counts': {
                        'EXPLORE': 0, 'RETRIEVE': 0, 'RETURN_HOME': 0,
                        'RETURN_BASE': 0, 'EXIT_WAREHOUSE': 0
                    },
                    '_last_pos': e['pos'],
                    '_last_carrying': e['carrying']
                }

            agent = stats[a_id]
            agent['ticks_alive'] += 1
            agent['final_state'] = e['state']
            agent['battery_remaining'] = e['battery']

            if e['state'] in agent['state_counts']:
                agent['state_counts'][e['state']] += 1
            else:
                agent['state_counts'][e['state']] = 1

            if e['pos'] != agent['_last_pos']:
                agent['distance_covered'] += 1
                agent['_last_pos'] = e['pos']

            if agent['_last_carrying'] and not e['carrying']:
                if e['state'] in ['EXIT_WAREHOUSE', 'FINISHED', 'EXPLORE']:
                    agent['deliveries'] += 1
                elif e['battery'] <= 2 or e['state'] == 'DEAD':
                    agent['abandoned'] += 1

            agent['_last_carrying'] = e['carrying']

        return stats

    def _safe_makedirs(self, path):
        """
        FIX: os.makedirs con stringa vuota solleva FileNotFoundError su Linux
        quando output_path e' un nome file senza directory (es. 'output.csv').
        """
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    def generate_agent_stats_csv(self, output_path):
        """Genera un file CSV con le metriche dettagliate per ogni agente."""
        self._safe_makedirs(output_path)

        # FIX: aggiunto 'Agent_Type' tra le colonne.
        # La versione originale calcolava il campo 'type' in _compute_agent_stats
        # ma non lo scriveva mai nel CSV, rendendo impossibile distinguere
        # le performance per tipo di agente senza incrociare file separati.
        headers = [
            'Agent_ID', 'Agent_Type', 'Final_State', 'Battery_Remaining',
            'Distance_Covered', 'Deliveries', 'Abandoned_Objects', 'Ticks_Alive',
            'Pct_Explore', 'Pct_ReturnHome'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for a_id, data in self.agent_stats.items():
                ticks = data['ticks_alive']
                pct_explore = (
                    round((data['state_counts'].get('EXPLORE', 0) / ticks) * 100, 2)
                    if ticks > 0 else 0
                )
                pct_return = (
                    round((data['state_counts'].get('RETURN_HOME', 0) / ticks) * 100, 2)
                    if ticks > 0 else 0
                )

                row = [
                    data['id'],
                    data['type'],           # FIX: ora incluso
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
        """
        Genera o appende i dati globali della simulazione a un file CSV.
        FIX: deduplicazione — se esiste gia' una riga con stessa istanza e seed,
        non viene scritta di nuovo. La versione originale accumulava righe
        duplicate ad ogni run con gli stessi parametri, inquinando i dati
        sperimentali.
        """
        self._safe_makedirs(output_path)
        file_exists = os.path.isfile(output_path)

        total_ticks = self.events[-1]['tick'] if self.events else 0
        total_deliveries = sum(a['deliveries'] for a in self.agent_stats.values())
        total_abandoned = sum(a['abandoned'] for a in self.agent_stats.values())
        dead_agents = sum(
            1 for a in self.agent_stats.values() if a['final_state'] == 'DEAD'
        )
        total_distance = sum(a['distance_covered'] for a in self.agent_stats.values())

        headers = [
            'Instance', 'Seed', 'Total_Ticks', 'Total_Deliveries',
            'Total_Abandoned', 'Dead_Agents', 'Total_Distance'
        ]

        # FIX: controllo duplicati prima di scrivere
        if file_exists:
            with open(output_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing = list(reader)
            is_duplicate = any(
                str(row.get('Instance')) == str(instance)
                and str(row.get('Seed')) == str(seed)
                for row in existing
            )
            if is_duplicate:
                print(f"Sommario gia' presente per Instance={instance}, Seed={seed}. Riga non aggiunta.")
                return

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

            is_interesting = False
            desc = ""

            # 1. Cambio di stato
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

            # FIX: rimosso il controllo su state == "LOW_BATTERY" che era dead code
            # permanente: quello stato non esiste nella macchina a stati del progetto.
            # Gli stati validi sono: EXPLORE, RETRIEVE, RETURN_HOME, RETURN_BASE,
            # EXIT_WAREHOUSE, DEAD, FINISHED. Il meccanismo di batteria bassa
            # e' gestito tramite la transizione a RETURN_BASE.

            if is_interesting:
                line = f"{e['tick']:<8} | {idx:<4} | {desc:<25} | {pos:<12} | {batt:<6} | {carrying}"
                report.append(line)

        self._safe_makedirs(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
        print(f"Report tabellare generato con successo: {output_path}")

    def get_summary_metrics(self):
        """
        Estrae metriche riassuntive per il feedback rapido.
        FIX: aggiunge consegne, abbandoni, agenti morti e distanza totale
        che erano gia' calcolati in _compute_agent_stats ma non inclusi
        nel dizionario restituito.
        """
        if not self.events:
            return {"Errore": "Nessun dato trovato"}

        final_tick = self.events[-1]['tick']
        total_deliveries = sum(a['deliveries'] for a in self.agent_stats.values())
        total_abandoned = sum(a['abandoned'] for a in self.agent_stats.values())
        dead_agents = sum(
            1 for a in self.agent_stats.values() if a['final_state'] == 'DEAD'
        )
        total_distance = sum(a['distance_covered'] for a in self.agent_stats.values())

        return {
            "Tick Totali": final_tick,
            "Eventi Registrati": len(self.events),
            "Agenti Attivi": len(set(e['id'] for e in self.events)),
            "Consegne Totali": total_deliveries,
            "Abbandoni Totali": total_abandoned,
            "Agenti Morti": dead_agents,
            "Distanza Totale Percorsa": total_distance
        }