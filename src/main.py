import random
import os
from src.config import MAX_TICKS, NUM_OBJECTS, SEED, GUI
from src.environment import Environment
from src.utils.logger import Logger
from src.utils.renderer import Renderer

from src.agents.workers import Worker1
from src.agents.scouts import Scout2
from src.agents.workers import Worker1, Worker2
from src.agents.workers import Worker1, Worker2, Worker3
from src.agents.scouts import Scout1, Scout2

from src.communication import exchange_messages

def main():
    env = Environment()
    INSTANCE = 'A'
    env.load(f'data/{INSTANCE}.json')
    
    logger = Logger()
    renderer = Renderer(env) if GUI else None
    
    active_agents = []

    env.spawn_queue.append(Worker1(agent_id=1))
    env.spawn_queue.append(Scout2(agent_id=2))
    env.spawn_queue.append(Worker2(agent_id=3))
    env.spawn_queue.append(Worker3(agent_id=4))
    env.spawn_queue.append(Scout1(agent_id=5))
    
    # [!] Qui nella FASE 4 popoleremo env.spawn_queue con le istanze dei nostri Worker e Scout
    
    tick = 0
    while tick < MAX_TICKS:
        env.try_spawn_next(active_agents)
        random.shuffle(active_agents)  # Desincronizzazione naturale
        
        for agent in active_agents:
            agent.decide_action(env, tick) # Decommenteremo questo nella FASE 4
            agent.battery -= 1
            logger.log(tick, agent)

        # FASE 5: Fase di Comunicazione dello Sciame 
        exchange_messages(active_agents, tick)
        # ---------------------------------------------------------
         
        env.update_stigma()
        
        if renderer:
            renderer.draw(active_agents, tick)
            
        # Early stopping
        if env.delivered == NUM_OBJECTS:
            print(f'Completato al tick {tick}')
            break
            
        tick += 1
        
    # Crea cartella outputs/logs se non esiste
    os.makedirs('outputs/logs', exist_ok=True)
    logger.dump(f'outputs/logs/{INSTANCE}_seed{SEED}.json')
    print("Simulazione terminata.")

    # ... fine del ciclo while ...
    
    log_file = f'outputs/logs/{INSTANCE}_seed{SEED}.json'
    logger.dump(log_file)
    
    #Generazione Report Tabellare
    from src.utils.analyzer import SimulationAnalyzer
    analyzer = SimulationAnalyzer(log_file)
    analyzer.generate_tabular_report(f'outputs/logs/{INSTANCE}_report.txt')
    
    metrics = analyzer.get_summary_metrics()
    print("\n--- SINTESI SIMULAZIONE ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")

if __name__ == '__main__':
    main()