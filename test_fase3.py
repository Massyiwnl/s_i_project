from src.environment import Environment
from src.agents.base_agent import BaseAgent

# Creiamo una classe fittizia per testare la BaseAgent
class DummyAgent(BaseAgent):
    def decide_action(self, env, tick):
        pass

def test_fase3():
    env = Environment()
    env.load('data/A.json')
    
    agente = DummyAgent(agent_id=1)
    agente.pos = (1, 1) # Posizioniamolo in alto a sinistra
    
    # 1. Test Entrata Più Vicina
    best_entrance = agente.nearest_entrance(env)
    assert best_entrance is not None, "Non ha trovato alcuna entrata"
    
    # 2. Test Merge Knowledge (Regola di priorità TAKEN)
    agente.mark_taken(10, 10)
    mappa_in_arrivo = {(10, 10): {'status': 'UNKNOWN', 'ts': 9999}}
    agente.merge_knowledge(mappa_in_arrivo, tick=5)
    
    assert agente.local_map[(10, 10)]['status'] == 'TAKEN', "Errore critico: merge_knowledge ha sovrascritto lo status TAKEN!"
    
    print("Fase 3 OK - Tutti i test superati!")

if __name__ == "__main__":
    test_fase3()