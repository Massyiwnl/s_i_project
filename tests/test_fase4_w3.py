from src.environment import Environment
from src.agents.workers import Worker3

def test_worker3():
    env = Environment()
    env.load('data/A.json')
    
    env._objects_truth.clear()
    
    w3 = Worker3(agent_id=4)
    w3.pos = (20, 20) 
    env.occupancy.add(w3.pos) 
    
    w3.battery = 30 
    w3.local_map[(2, 2)] = {'status': 'FOUND', 'ts': 1}
    
    # 1. Test di Valutazione Energetica
    w3.state = 'EXPLORE'
    w3.decide_action(env, 1)
    
    assert w3.state != 'MOVE_TO_OBJECT', "Il Worker 3 ha accettato un task suicida senza energia!"
    assert (2, 2) in w3.ignored_targets, "Non ha aggiunto il target irraggiungibile agli ignorati!"
    
    # Reimpostiamo la posizione dell'agente a (20,20) perché al tick precedente si era mosso
    env.occupancy.remove(w3.pos)
    w3.pos = (20, 20)
    env.occupancy.add(w3.pos)
    
    # Salviamo la posizione esatta in cui farà cadere l'oggetto
    pos_abbandono = w3.pos
    
    # 2. Test Abbandono Oggetto
    w3.state = 'LOW_BATTERY'
    w3.carrying = True
    w3.carrying_obj = pos_abbandono
    
    w3.decide_action(env, 2)
    
    assert w3.carrying == False, "Il Worker 3 non ha lasciato cadere l'oggetto in emergenza!"
    assert w3.local_map[pos_abbandono]['status'] == 'ABANDONED', "L'oggetto non è stato marcato come ABANDONED!"
    assert pos_abbandono in env._objects_truth, "L'oggetto non è stato rimesso nella griglia (Ground Truth)!"
    
    print("Fase 4.4 (Worker 3) OK - Prevenzione e gestione rischi perfetti!")

if __name__ == '__main__':
    test_worker3()