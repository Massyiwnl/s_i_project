import random
import os
from src.config import MAX_TICKS, NUM_OBJECTS, SEED, GUI
from src.environment import Environment
from src.utils.logger import Logger
from src.utils.renderer import Renderer

from src.agents.workers import Worker1, Worker2, Worker3
from src.agents.scouts import Scout1, Scout2



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
        
        # ---> AGGIUNGI QUESTA RIGA <---
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

        # Ora la comunicazione avviene in decide_action
         
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