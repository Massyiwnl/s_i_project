import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

SEEDS = [42, 123, 456, 789, 1337]

def analyze_configuration(instance_name):
    ticks, energies, failures, delivered = [], [], [], []
    expl_100, expl_250, expl_500 = [], [], []
    
    # Matrice vuota 25x25 per la Heatmap aggregata
    heatmap_data = np.zeros((25, 25))

    for seed in SEEDS:
        filepath = f'outputs/logs/run_{instance_name}_seed{seed}.json'
        if not os.path.exists(filepath):
            print(f"ATTENZIONE: File {filepath} non trovato. Salto.")
            continue
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            metrics = data.get('metrics', {})
            
            ticks.append(metrics.get('ticks_total', 0))
            energies.append(metrics.get('avg_energy_consumed', 0))
            failures.append(metrics.get('critical_failures', 0))
            delivered.append(metrics.get('delivered', 0))
            
            # Estrazione esplorazione
            expl = metrics.get('exploration_percent', {})
            if 'tick_100' in expl: expl_100.append(expl['tick_100'])
            if 'tick_250' in expl: expl_250.append(expl['tick_250'])
            if 'tick_500' in expl: expl_500.append(expl['tick_500'])

            # Aggregazione Traffico per Heatmap
            traffic = metrics.get('traffic_log', {})
            for coord_str, count in traffic.items():
                r, c = map(int, coord_str.strip('()').split(','))
                heatmap_data[r][c] += count

    if not ticks:
        print(f"Nessun dato per l'Istanza {instance_name}. Hai avviato run_configs.py prima?")
        return

    # --- STAMPA DEL REPORT STATISTICO ---
    print(f"\n===== REPORT STATISTICO - CONFIGURAZIONE (Istanza {instance_name}) =====")
    print(f"Run analizzate: {len(ticks)}")
    print(f"Oggetti Consegnati:      {np.mean(delivered):.2f} ± {np.std(delivered):.2f} (su 10)")
    print(f"Tick completamento:      {np.mean(ticks):.2f} ± {np.std(ticks):.2f}")
    print(f"Energia media consumata: {np.mean(energies):.2f} ± {np.std(energies):.2f}")
    print(f"Fallimenti Critici:      {np.mean(failures):.2f} ± {np.std(failures):.2f}")
    
    if expl_100: print(f"% Esplorata Tick 100:    {np.mean(expl_100):.1f}% ± {np.std(expl_100):.1f}%")
    if expl_250: print(f"% Esplorata Tick 250:    {np.mean(expl_250):.1f}% ± {np.std(expl_250):.1f}%")
    if expl_500: print(f"% Esplorata Tick 500:    {np.mean(expl_500):.1f}% ± {np.std(expl_500):.1f}%")
    print("===================================================================\n")

    # --- GENERAZIONE HEATMAP EVACUATION DYNAMICS ---
    os.makedirs('outputs/heatmaps', exist_ok=True)
    plt.figure(figsize=(10, 8))
    
    # Mascheriamo gli zeri per colorare solo le zone transitate
    masked_data = np.ma.masked_where(heatmap_data == 0, heatmap_data)
    
    sns.heatmap(masked_data, cmap="YlOrRd", annot=False, cbar_kws={'label': 'Passaggi cumulativi (5 run)'}, square=True)
    plt.title(f'Heatmap Colli di Bottiglia (Evacuation) - Istanza {instance_name}')
    plt.xlabel('Colonne')
    plt.ylabel('Righe')
    plt.gca().invert_yaxis() # Importantissimo: inverte la Y per pareggiare la vista della grid logica!
    
    out_path = f'outputs/heatmaps/heatmap_congestione_{instance_name}.png'
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"--> Heatmap salvata in: {out_path}\n")

if __name__ == '__main__':
    #analyze_configuration('A')
    analyze_configuration('B') # Decommenta per la mappa B