from src.environment import Environment
from src.agents.scouts import Scout1
from src.config import STRESS_MAX

def test_scout1():
    env = Environment()
    env.load('data/A.json')
    
    s1 = Scout1(agent_id=5)
    s1.pos = (10, 10) # Lo mettiamo in uno spazio libero
    env.occupancy.add(s1.pos)
    
    s1.state = 'EXPLORE'
    
    # 1. Forziamo il suo stress al limite (es. simuliamo che abbia camminato in tondo per troppo tempo)
    s1.stress = STRESS_MAX
    
    # 2. Eseguiamo un tick
    s1.decide_action(env, 1)
    
    # Se la logica ha funzionato, lo stress si è azzerato e l'agente è entrato in modalità "Random" per sbloccarsi
    assert s1.stress == 0, "Lo Scout 1 non ha azzerato lo stress dopo il picco!"
    assert s1.random_steps > 0, "Lo Scout 1 non ha attivato i passi casuali di sblocco!"
    
    print("Fase 4.5 (Scout 1) OK - Wall-Following e Gestione dello stress funzionanti!")

if __name__ == '__main__':
    test_scout1()