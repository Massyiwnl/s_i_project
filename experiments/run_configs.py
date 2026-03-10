import subprocess
import os

SEEDS = [42, 123, 456, 789, 1337]

def run_experiment(instance_name):
    print(f"\n=================================================")
    print(f" AVVIO ESPERIMENTO AUTOMATICO - ISTANZA {instance_name}")
    print(f"=================================================")
    
    for seed in SEEDS:
        print(f"> Esecuzione Simulazione con Seed {seed}...")
        # Lancia main.py da terminale, passa gli argomenti e forza la disabilitazione GUI
        cmd = ["python", "-m", "src.main", "--instance", instance_name, "--seed", str(seed)]
        subprocess.run(cmd)
        
    print(f"Esperimento sull'Istanza {instance_name} completato!\n")

if __name__ == '__main__':
    # Esegue in cascata 5 run (impiegherà pochissimi secondi senza GUI)
    run_experiment('A')
    # Se vuoi testare l'istanza B per la configurazione C3, decommenta la riga sotto:
    #run_experiment('B')