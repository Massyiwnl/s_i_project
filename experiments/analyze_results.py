import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# FIX: importiamo GRID_SIZE e MAX_TICKS da config invece di usare
# valori hardcoded (25 e 500). Cosi' se la configurazione cambia,
# l'analisi rimane automaticamente coerente.
from src.config import GRID_SIZE, MAX_TICKS

SEEDS = [42, 123, 456, 789, 1337]

# Chiave del checkpoint finale: MAX_TICKS - 1 = 499 (non 500, irraggiungibile).
# FIX: la versione originale cercava 'tick_500' che non viene mai scritto
# nel log perche' il loop di main.py termina con tick < MAX_TICKS,
# quindi l'ultimo tick raggiungibile e' MAX_TICKS - 1 = 499.
LAST_TICK_KEY = f'tick_{MAX_TICKS - 1}'


def analyze_configuration(instance_name):
    ticks, energies, failures, delivered = [], [], [], []
    expl_100, expl_250, expl_last = [], [], []

    # FIX: usa GRID_SIZE da config invece di 25 hardcoded.
    # Con 25 hardcoded, se si usasse una mappa di dimensione diversa
    # si otterrebbe un IndexError silenzioso o una heatmap malformata.
    heatmap_data = np.zeros((GRID_SIZE, GRID_SIZE))

    for seed in SEEDS:
        filepath = f'outputs/logs/run_{instance_name}_seed{seed}.json'
        if not os.path.exists(filepath):
            print(f"ATTENZIONE: File {filepath} non trovato. Salto.")
            continue

        # FIX: aggiunto encoding='utf-8' coerente con logger.py che scrive
        # i file con quella codifica. Su Windows con locale non-UTF-8
        # l'apertura senza encoding esplicito puo' produrre caratteri corrotti
        # o UnicodeDecodeError su path/nomi con caratteri non-ASCII.
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # FIX: la versione originale usava 'metrics' ma logger.py scrive
        # il dizionario con la chiave 'metadata'. Con 'metrics', data.get()
        # restituisce sempre {} e tutte le statistiche risultano 0
        # senza nessun errore esplicito — bug silenzioso e totalmente
        # invalidante per il report.
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
        # FIX: cerca LAST_TICK_KEY ('tick_499') invece di 'tick_500'.
        if LAST_TICK_KEY in expl:
            expl_last.append(expl[LAST_TICK_KEY])

        # Aggregazione Traffico per Heatmap
        traffic = metadata.get('traffic_log', {})
        for coord_str, count in traffic.items():
            # FIX: il parser originale usava strip('()').split(',') progettato
            # per chiavi tipo "(5, 3)". Il logger corretto produce chiavi tipo
            # "[5, 3]" (stringa di lista JSON). strip('()') non rimuove le
            # parentesi quadre, e int('[5') solleva ValueError a runtime.
            # json.loads() gestisce correttamente entrambi i formati futuri
            # e rende il parsing robusto a spazi e varianti di formato.
            coords = json.loads(coord_str)
            r, c = coords[0], coords[1]
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                heatmap_data[r][c] += count

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
        print(f"% Esplorata Tick {MAX_TICKS - 1}:   "
              f"{np.mean(expl_last):.1f}% ± {np.std(expl_last):.1f}%")
    print("===================================================================\n")

    # --- HEATMAP COLLI DI BOTTIGLIA ---
    os.makedirs('outputs/heatmaps', exist_ok=True)

    # FIX: uso di plt.figure() + plt.close() esplicito dopo il salvataggio.
    # La versione originale non chiudeva la figura: chiamando analyze_configuration
    # due volte (istanza A poi B), le figure si accumulavano in memoria e
    # in modalita' interattiva si sovrapponevano visivamente.
    fig = plt.figure(figsize=(10, 8))

    masked_data = np.ma.masked_where(heatmap_data == 0, heatmap_data)

    sns.heatmap(
        masked_data,
        cmap="YlOrRd",
        annot=False,
        cbar_kws={'label': f'Passaggi cumulativi ({len(ticks)} run)'},
        square=True
    )
    plt.title(f'Heatmap Colli di Bottiglia - Istanza {instance_name}')
    plt.xlabel('Colonne')
    plt.ylabel('Righe')
    plt.gca().invert_yaxis()

    out_path = f'outputs/heatmaps/heatmap_congestione_{instance_name}.png'
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)   # FIX: libera la memoria della figura dopo il salvataggio
    print(f"--> Heatmap salvata in: {out_path}\n")


if __name__ == '__main__':
    # FIX: il commento originale era invertito — era B ad essere attiva, non A.
    # Per analizzare l'istanza A, decommentare la riga sotto:
    analyze_configuration('A')
    # Per analizzare l'istanza B (configurazione C3), decommentare:
    # analyze_configuration('B')