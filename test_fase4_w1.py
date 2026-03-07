from src.environment import Environment
from src.agents.workers import Worker1

def test_worker1():
    env = Environment()
    env.load('data/A.json')
    
    w1 = Worker1(agent_id=1)
    env.spawn_queue.append(w1)
    active_agents = []
    
    # Tick 1: Deploy
    env.try_spawn_next(active_agents)
    w1.decide_action(env, 1)
    assert w1.state == 'EXPLORE', "L'agente non è passato in EXPLORE dopo il deploy!"
    
    # Inseriamo un oggetto falso vicino a lui per forzare il rilevamento
    w1.pos = (2, 2)
    env._objects_truth.add((2, 3))
    
    # Tick 2: Esplora e vede l'oggetto
    w1.decide_action(env, 2)
    assert w1.state == 'MOVE_TO_OBJECT', "L'agente Greedy non ha agganciato l'oggetto visibile!"
    assert w1.target_obj == (2, 3), "L'agente non ha impostato il target corretto!"
    
    print("Fase 4 (Worker 1) OK - Test superato!")

if __name__ == '__main__':
    test_worker1()