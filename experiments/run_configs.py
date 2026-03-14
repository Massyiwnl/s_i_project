import subprocess
import sys

# FIX: rimosso 'import os' che era importato ma mai usato nel file.

SEEDS = [42, 123, 456, 789, 1337]
# Timeout massimo in secondi per singola run. Evita blocchi infiniti
# in caso di deadlock permanente o loop non terminante nella simulazione.
RUN_TIMEOUT = 300  # 5 minuti per run


def run_experiment(instance_name):
    print(f"\n=================================================")
    print(f" AVVIO ESPERIMENTO AUTOMATICO - ISTANZA {instance_name}")
    print(f"=================================================")

    failed = []

    for seed in SEEDS:
        print(f"> Esecuzione Simulazione con Seed {seed}...")

        # FIX: aggiunto '--no-gui' al comando.
        # La versione originale non passava alcun flag per disabilitare la GUI,
        # ma config.GUI e' True di default. Questo causava l'apertura di una
        # finestra matplotlib bloccante per ogni run, rendendo l'esecuzione
        # automatica impossibile senza intervento manuale dell'utente.
        cmd = [
            sys.executable, "-m", "src.main",
            "--instance", instance_name,
            "--seed", str(seed),
            "--no-gui"
        ]

        # FIX: aggiunto timeout e controllo sul returncode.
        # La versione originale non controllava se main.py avesse avuto successo:
        # un crash silenzioso (es. file JSON assente, eccezione non gestita)
        # veniva ignorato e il loop continuava, lasciando file di log mancanti
        # che analyze_results.py avrebbe poi saltato senza avvertire del problema.
        # Il timeout previene il blocco su run che non terminano mai.
        try:
            result = subprocess.run(cmd, timeout=RUN_TIMEOUT)
            if result.returncode != 0:
                print(f"  ATTENZIONE: run seed={seed} terminata con errore "
                      f"(returncode={result.returncode}).")
                failed.append(seed)
            else:
                print(f"  OK: seed={seed} completata.")

        except subprocess.TimeoutExpired:
            print(f"  ERRORE: run seed={seed} superato il timeout di {RUN_TIMEOUT}s. "
                  f"La simulazione non ha terminato. Seed saltato.")
            failed.append(seed)

    print(f"\nEsperimento sull'Istanza {instance_name} completato!")
    if failed:
        print(f"  Run fallite (seeds): {failed}")
    else:
        print(f"  Tutte le run completate con successo.")
    print()


if __name__ == '__main__':
    # Esegue in cascata 5 run (pochissimi secondi senza GUI)
    run_experiment('A')
    # FIX: il commento originale era invertito — era B ad essere attiva, non A.
    # Per testare l'istanza B (configurazione C3), decommenta la riga sotto:
    # run_experiment('B')