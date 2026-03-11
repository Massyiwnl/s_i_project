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
    parser.add_argument('--gui', action='store_true')
    args = parser.parse_args()

    random.seed(args.seed)
    
    env = Environment()
    env.load(f'data/{args.instance}.json')
    
    logger = Logger()
    
    use_gui = True if args.gui else GUI
    renderer = Renderer(env) if use_gui else None
    
    active_agents = []

    env.spawn_queue.append(Worker1(agent_id=1))
    env.spawn_queue.append(Scout2(agent_id=2))
    env.spawn_queue.append(Worker2(agent_id=3))
    env.spawn_queue.append(Worker3(agent_id=4))
    env.spawn_queue.append(Scout1(agent_id=5))
    
    total_walkable = sum(1 for r in range(env.n) for c in range(env.n) if env.grid[r][c] != WALL)
    
    tick = 0
    while tick < MAX_TICKS:
        env.clear_intentions()
        
        env.try_spawn_next(active_agents)
        random.shuffle(active_agents) 
        
        env.active_agents = active_agents 
        
        for agent in active_agents:
            # Gli agenti morti vengono ignorati
            if agent.state == 'DEAD':
                continue 
                
            # Gli agenti FINISHED (parcheggiati) non consumano batteria
            if agent.state == 'FINISHED':
                logger.log(tick, agent)
                continue
                
            # Gli agenti attivi consumano batteria
            agent.battery -= 1
            if agent.battery <= 0:
                agent.state = 'DEAD'
                if agent.pos in env.occupancy:
                    env.occupancy.remove(agent.pos)
                if agent.carrying:
                    agent.carrying = False
                    if hasattr(env, 'drop_abandoned_object'):
                        env.drop_abandoned_object(agent.pos[0], agent.pos[1]) 
                logger.log(tick, agent)
                continue

            agent.decide_action(env, tick) 
            logger.log(tick, agent)
         
        env.update_stigma()
         
        if renderer:
            renderer.draw(active_agents, tick)
            
        if tick in [100, 250, 500]:
            logger.record_exploration(tick, active_agents, total_walkable)

        if env.delivered == NUM_OBJECTS:
            print(f'Completato al tick {tick}')
            break
            
        tick += 1
        
    logger.record_exploration(tick, active_agents, total_walkable)

    os.makedirs('outputs/logs', exist_ok=True)
    log_file = f'outputs/logs/run_{args.instance}_seed{args.seed}.json'
    
    logger.dump(log_file, env, tick)
    print("Simulazione terminata.")
    print(f"Log salvato in: {log_file}")
    
    try:
        from src.utils.analyzer import SimulationAnalyzer
        analyzer = SimulationAnalyzer(log_file)
        
        # 1. Report Testuale originale
        report_file = f'outputs/logs/run_{args.instance}_seed{args.seed}_report.txt'
        analyzer.generate_tabular_report(report_file)
        
        # 2. NUOVO: Tabella CSV per i singoli agenti
        agent_csv_file = f'outputs/logs/run_{args.instance}_seed{args.seed}_agents.csv'
        analyzer.generate_agent_stats_csv(agent_csv_file)
        
        # 3. NUOVO: Tabella CSV globale (si appende in automatico per ogni run)
        global_csv_file = f'outputs/logs/experiments_summary.csv'
        analyzer.generate_global_summary_csv(global_csv_file, args.seed, args.instance)
        
        metrics = analyzer.get_summary_metrics()
        print("\n--- SINTESI SIMULAZIONE ---")
        for k, v in metrics.items():
            print(f"{k}: {v}")
    except Exception as e:
        print(f"Errore durante l'analisi dei log: {e}")

if __name__ == '__main__':
    main()