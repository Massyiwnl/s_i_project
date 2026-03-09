from src.environment import Environment
from src.agents.workers import Worker2
from src.pathfinding import astar

def test_worker2():
    env = Environment()
    env.load('data/A.json')
    
    w2 = Worker2(agent_id=3)
    w2.pos = (5, 5)
    env.occupancy.add(w2.pos)
    
    # Diamo a W2 un target e facciamogli calcolare il percorso base
    w2.target_obj = (10, 5)
    w2.state = 'MOVE_TO_OBJECT'
    percorso_iniziale = astar(env, w2.pos, w2.target_obj)
    w2.cached_path = percorso_iniziale.copy()
    
    # SIMULIAMO LA FOLLA: aggiungiamo 2 agenti fittizi adiacenti (entro COMM_RADIUS)
    env.occupancy.add((4, 5))
    env.occupancy.add((5, 4))
    
    # Tick: W2 valuta la situazione prima di muoversi
    w2.decide_action(env, 1)
    
    # Verifichiamo che abbia percepito il pericolo e "sporcato" la mappa stigmergica
    cella_pianificata = percorso_iniziale[0]
    malus = env.stigma_map[cella_pianificata[0]][cella_pianificata[1]]
    
    assert malus > 0, "Il Worker 2 non ha applicato il malus stigmergico nonostante la folla!"
    
    print(f"Fase 4.3 (Worker 2) OK - Ha evitato la folla e piazzato {malus} di feromone negativo!")

if __name__ == '__main__':
    test_worker2()