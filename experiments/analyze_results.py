import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import GRID_SIZE

SEEDS = [42, 123, 456, 789, 1337]


def analyze_configuration(instance_name):
    ticks, energies, failures, delivered = [], [], [], []
    expl_100, expl_250, expl_last = [], [], []

    # Matrice per la heatmap dei punti di consegna (traffic_log)
    delivery_heatmap = np.zeros((GRID_SIZE, GRID_SIZE))

    # Matrice per la vera heatmap dei colli di bottiglia (movement_log)
    movement_heatmap = np.zeros((GRID_SIZE, GRID_SIZE))

    for seed in SEEDS:
        filepath = f'outputs/logs/run_{instance_name}_seed{seed}.json'
        if not os.path.exists(filepath):
            print(f"ATTENZIONE: File {filepath} non trovato. Salto.")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = data.get('metadata', {})

        ticks.append(metadata.get('ticks_total', 0))
        energies.append(metadata.get('avg_energy_consumed', 0))
        failures.append(metadata.get('critical_failures', 0))
        delivered.append(metadata.get('delivered', 0))

        # Estrazione esplorazione
        expl = metadata.get('exploration_percent', {})
        if 'tick_100' in expl:
            expl_100.append(expl['tick_100'])
        if 'tick_250' in expl:
            expl_250.append(expl['tick_250'])
        # Prende dinamicamente l'ultimo checkpoint disponibile nel log.
        # Non cerca una chiave fissa ('tick_499') perche' le run che completano
        # tutti gli oggetti prima del timeout terminano a un tick variabile
        # (es. tick_322) e quella e' l'unica chiave finale presente nel log.
        if expl:
            last_key = max(expl.keys(), key=lambda k: int(k.split('_')[1]))
            expl_last.append(expl[last_key])

        # Aggregazione punti di consegna (traffic_log) per heatmap 1
        traffic = metadata.get('traffic_log', {})
        for coord_str, count in traffic.items():
            coords = json.loads(coord_str)
            r, c = coords[0], coords[1]
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                delivery_heatmap[r][c] += count

        # Aggregazione passaggi di movimento (movement_log) per heatmap 2
        movement = metadata.get('movement_log', {})
        for coord_str, count in movement.items():
            coords = json.loads(coord_str)
            r, c = coords[0], coords[1]
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                movement_heatmap[r][c] += count

    if not ticks:
        print(f"Nessun dato per l'Istanza {instance_name}. "
              f"Hai avviato run_configs.py prima?")
        return

    # --- REPORT STATISTICO ---
    print(f"\n===== REPORT STATISTICO - CONFIGURAZIONE (Istanza {instance_name}) =====")
    print(f"Run analizzate:          {len(ticks)}")
    print(f"Oggetti Consegnati:      {np.mean(delivered):.2f} ± {np.std(delivered):.2f} "
          f"(su 10)")
    print(f"Tick completamento:      {np.mean(ticks):.2f} ± {np.std(ticks):.2f}")
    print(f"Energia media consumata: {np.mean(energies):.2f} ± {np.std(energies):.2f}")
    print(f"Fallimenti Critici:      {np.mean(failures):.2f} ± {np.std(failures):.2f}")

    if expl_100:
        print(f"% Esplorata Tick 100:    "
              f"{np.mean(expl_100):.1f}% ± {np.std(expl_100):.1f}%")
    if expl_250:
        print(f"% Esplorata Tick 250:    "
              f"{np.mean(expl_250):.1f}% ± {np.std(expl_250):.1f}%")
    if expl_last:
        print(f"% Esplorata Tick finale: "
              f"{np.mean(expl_last):.1f}% ± {np.std(expl_last):.1f}%")
    print("===================================================================\n")

    os.makedirs('outputs/heatmaps', exist_ok=True)

    # --- HEATMAP 1: PUNTI DI CONSEGNA ---
    # Mostra le celle di magazzino in cui gli oggetti sono stati effettivamente
    # depositati. Traccia la distribuzione del carico tra i magazzini disponibili.
    fig1 = plt.figure(figsize=(10, 8))
    masked_delivery = np.ma.masked_where(delivery_heatmap == 0, delivery_heatmap)
    sns.heatmap(
        masked_delivery,
        cmap="Blues",
        annot=False,
        cbar_kws={'label': f'Consegne cumulative ({len(ticks)} run)'},
        square=True
    )
    plt.title(f'Punti di Consegna - Istanza {instance_name}')
    plt.xlabel('Colonne')
    plt.ylabel('Righe')
    plt.gca().invert_yaxis()
    out_path1 = f'outputs/heatmaps/heatmap_consegne_{instance_name}.png'
    plt.savefig(out_path1, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"--> Heatmap Punti di Consegna salvata in: {out_path1}")

    # --- HEATMAP 2: COLLI DI BOTTIGLIA (traffico reale) ---
    # Mostra le celle piu' attraversate da tutti gli agenti durante il movimento.
    # Le zone rosse intense sono i veri colli di bottiglia della mappa:
    # corridoi obbligati, incroci critici, zone ad alta densita' di transito.
    fig2 = plt.figure(figsize=(10, 8))
    masked_movement = np.ma.masked_where(movement_heatmap == 0, movement_heatmap)
    sns.heatmap(
        masked_movement,
        cmap="YlOrRd",
        annot=False,
        cbar_kws={'label': f'Passaggi cumulativi ({len(ticks)} run)'},
        square=True
    )
    plt.title(f'Heatmap Colli di Bottiglia (Traffico Agenti) - Istanza {instance_name}')
    plt.xlabel('Colonne')
    plt.ylabel('Righe')
    plt.gca().invert_yaxis()
    out_path2 = f'outputs/heatmaps/heatmap_bottleneck_{instance_name}.png'
    plt.savefig(out_path2, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"--> Heatmap Colli di Bottiglia salvata in: {out_path2}\n")


if __name__ == '__main__':
    #analyze_configuration('A')
    # Per analizzare l'istanza B (configurazione C3), decommentare:
    analyze_configuration('B')