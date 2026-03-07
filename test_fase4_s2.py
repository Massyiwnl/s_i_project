from src.environment import Environment
from src.agents.scouts import Scout2

def test_scout2():
    env = Environment()
    env.load('data/A.json')
    
    s2 = Scout2(agent_id=2)
    env.spawn_queue.append(s2)
    active_agents = []
    
    # Tick 1: Deploy
    env.try_spawn_next(active_agents)
    s2.decide_action(env, 1)
    assert s2.state == 'EXPLORE', "Lo Scout 2 non è passato in EXPLORE!"
    
    # Raccogliamo la sua posizione iniziale post-deploy
    pos_iniziale = s2.pos
    
    # Facciamolo camminare per 10 tick e verifichiamo che non crashi
    # e che popoli la mappa locale con celle VISITED
    for t in range(2, 12):
        s2.decide_action(env, t)
        
    celle_visitate = [c for c, data in s2.local_map.items() if data['status'] == 'VISITED']
    assert len(celle_visitate) > 0, "Lo Scout 2 non sta salvando la memoria delle celle VISITATE!"
    
    print(f"Fase 4.2 (Scout 2) OK - Ha esplorato {len(celle_visitate)} celle uniche!")

if __name__ == '__main__':
    test_scout2()