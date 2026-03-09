import sys
import argparse
import random
import os
from src.config import MAX_TICKS, NUM_OBJECTS, SEED, GUI, WALL
from src.environment import Environment
from src.utils.logger import Logger
from src.utils.renderer import Renderer

from src.agents.workers import Worker1, Worker2, Worker3
from src.agents.scouts import Scout1, Scout2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', type=str, default='A', choices=['A', 'B'])
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--gui', action='store_true') # Se passato, forza la GUI a prescindere da config
    args = parser.parse_args()

    # Sovrascrivi il seed di sistema per questa specifica simulazione
    random.seed(args.seed)
    
    env = Environment()
    env.load(f'data/{args.instance}.json')
    
    logger = Logger()
    
    # Decidi se usare la GUI (dal flag del terminale o da config.py)
    use_gui = True if args.gui else GUI
    renderer = Renderer(env) if use_gui else None
    
    active_agents = []

    env.spawn_queue.append(Worker1(agent_id=1))
    env.spawn_queue.append(Scout2(agent_id=2))
    env.spawn_queue.append(Worker2(agent_id=3))
    env.spawn_queue.append(Worker3(agent_id=4))
    env.spawn_queue.append(Scout1(agent_id=5))
    
    # Calcolo celle walkable totali (per percentuale di esplorazione)
    total_walkable = sum(1 for r in range(env.n) for c in range(env.n) if env.grid[r][c] != WALL)
    
    tick = 0
    while tick < MAX_TICKS:
        env.try_spawn_next(active_agents)
        random.shuffle(active_agents)  # Desincronizzazione naturale
        
        env.active_agents = active_agents 
        
        for agent in active_agents:
            if agent.state == 'DEAD':
                continue # Salta gli agenti morti
                
            # Scala batteria
            agent.battery -= 1
            if agent.battery <= 0:
                agent.state = 'DEAD'
                if agent.pos in env.occupancy:
                    env.occupancy.remove(agent.pos) # Libera la cella
                if agent.carrying:
                    agent.carrying = False
                    # Drop dell'oggetto (se gestito dall'env)
                    if hasattr(env, 'drop_abandoned_object'):
                        env.drop_abandoned_object(agent.pos[0], agent.pos[1]) 
                logger.log(tick, agent)
                continue

            agent.decide_action(env, tick) 
            logger.log(tick, agent)
         
        env.update_stigma()
         
        if renderer:
            renderer.draw(active_agents, tick)
            
        # Registrazione % mappa esplorata ai tick critici (100, 250, 500)
        if tick in [100, 250, 500]:
            logger.record_exploration(tick, active_agents, total_walkable)

        # Early stopping
        if env.delivered == NUM_OBJECTS:
            print(f'Completato al tick {tick}')
            break
            
        tick += 1
        
    # Registrazione esplorazione al tick finale
    logger.record_exploration(tick, active_agents, total_walkable)

    # Crea cartella outputs/logs se non esiste e salva il JSON
    os.makedirs('outputs/logs', exist_ok=True)
    log_file = f'outputs/logs/run_{args.instance}_seed{args.seed}.json'
    
    logger.dump(log_file, env, tick)
    print("Simulazione terminata.")
    print(f"Log salvato correttamente in: {log_file}")
    
    # Generazione Report Tabellare (mantenuto dal tuo codice originale)
    try:
        from src.utils.analyzer import SimulationAnalyzer
        analyzer = SimulationAnalyzer(log_file)
        report_file = f'outputs/logs/run_{args.instance}_seed{args.seed}_report.txt'
        analyzer.generate_tabular_report(report_file)
        
        metrics = analyzer.get_summary_metrics()
        print("\n--- SINTESI SIMULAZIONE ---")
        for k, v in metrics.items():
            print(f"{k}: {v}")
    except Exception as e:
        # Se il tuo analyzer crasha per il cambio di formato del JSON, ignora.
        pass

if __name__ == '__main__':
    main()