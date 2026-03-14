import sys
import argparse
import random
import os
import numpy as np
import matplotlib.pyplot as plt

from src.config import MAX_TICKS, NUM_OBJECTS, SEED, GUI, WALL
from src.environment import Environment
from src.utils.logger import Logger
from src.utils.renderer import Renderer

from src.agents.workers import Worker1, Worker2, Worker3
from src.agents.scouts import Scout1, Scout2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', type=str, default='A', choices=['A', 'B', 'A2'])
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--gui', action='store_true')
    # FIX: aggiunto --no-gui per disabilitare esplicitamente il renderer
    # da riga di comando. Necessario per run_configs.py che lancia main.py
    # in subprocess: senza questo flag, config.GUI=True apre una finestra
    # matplotlib bloccante per ogni run, impedendo l'esecuzione automatica.
    # Precedenza: --no-gui > --gui > valore di config.GUI
    parser.add_argument('--no-gui', action='store_true',
                        help='Disabilita la GUI (sovrascrive config.GUI e --gui)')
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    env = Environment()
    env.load(f'data/{args.instance}.json')

    logger = Logger()

    # FIX: --no-gui ha precedenza assoluta su --gui e su config.GUI
    if args.no_gui:
        use_gui = False
    elif args.gui:
        use_gui = True
    else:
        use_gui = GUI

    renderer = Renderer(env) if use_gui else None

    active_agents = []

    env.spawn_queue.append(Worker1(agent_id=1))
    env.spawn_queue.append(Scout2(agent_id=2))
    env.spawn_queue.append(Worker2(agent_id=3))
    env.spawn_queue.append(Worker3(agent_id=4))
    env.spawn_queue.append(Scout1(agent_id=5))

    total_walkable = sum(
        1 for r in range(env.n) for c in range(env.n)
        if env.grid[r][c] != WALL
    )

    os.makedirs('outputs/logs', exist_ok=True)
    log_file = f'outputs/logs/run_{args.instance}_seed{args.seed}.json'

    tick = 0
    finished_logged = set()

    try:
        while tick < MAX_TICKS:
            env.clear_intentions()

            env.try_spawn_next(active_agents)
            env.active_agents = active_agents

            random.shuffle(active_agents)

            for agent in active_agents:
                if agent.state == 'DEAD':
                    continue

                if agent.state == 'FINISHED':
                    if agent.id not in finished_logged:
                        logger.log(tick, agent)
                        finished_logged.add(agent.id)
                    continue

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
                if renderer.should_quit:
                    print("Simulazione interrotta dall'utente.")
                    plt.close('all') # <--- AGGIUNGI QUESTA RIGA
                    break

            if tick in [100, 250, MAX_TICKS - 1]:
                logger.record_exploration(tick, active_agents, total_walkable)

            if env.delivered == NUM_OBJECTS:
                print(f'Completato al tick {tick}')
                break

            tick += 1

    finally:
        logger.record_exploration(tick, active_agents, total_walkable)
        logger.dump(log_file, env, tick)
        print("Simulazione terminata.")
        print(f"Log salvato in: {log_file}")

    try:
        from src.utils.analyzer import SimulationAnalyzer
        analyzer = SimulationAnalyzer(log_file)

        report_file = f'outputs/logs/run_{args.instance}_seed{args.seed}_report.txt'
        analyzer.generate_tabular_report(report_file)

        agent_csv_file = f'outputs/logs/run_{args.instance}_seed{args.seed}_agents.csv'
        analyzer.generate_agent_stats_csv(agent_csv_file)

        global_csv_file = 'outputs/logs/experiments_summary.csv'
        analyzer.generate_global_summary_csv(global_csv_file, args.seed, args.instance)

        metrics = analyzer.get_summary_metrics()
        print("\n--- SINTESI SIMULAZIONE ---")
        for k, v in metrics.items():
            print(f"{k}: {v}")

    except FileNotFoundError as e:
        print(f"File di log non trovato per l'analisi: {e}")
    except (KeyError, ValueError) as e:
        print(f"Dati del log malformati: {e}")
    except ImportError as e:
        print(f"Modulo analyzer non disponibile: {e}")


if __name__ == '__main__':
    main()