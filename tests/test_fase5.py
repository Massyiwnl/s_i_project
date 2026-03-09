from src.environment import Environment
from src.agents.workers import Worker1
from src.agents.scouts import Scout2
from src.communication import exchange_messages

def test_fase5():
    env = Environment()
    
    # Creiamo due agenti
    w1 = Worker1(agent_id=1)
    s2 = Scout2(agent_id=2)
    
    # Li posizioniamo molto vicini (distanza 1, entro il COMM_RADIUS)
    w1.pos = (10, 10)
    s2.pos = (10, 11)
    
    # W1 scopre un oggetto leggendario al tick 5
    oggetto_segreto = (20, 20)
    w1.local_map[oggetto_segreto] = {'status': 'FOUND', 'ts': 5}
    
    assert oggetto_segreto not in s2.local_map, "Inizialmente lo Scout non dovrebbe conoscere l'oggetto!"
    
    active_agents = [w1, s2]
    
    # Attiviamo la comunicazione al tick 6
    exchange_messages(active_agents, tick=6)
    
    # Verifichiamo il passaparola
    assert oggetto_segreto in s2.local_map, "Lo Scout non ha ricevuto l'informazione da W1!"
    assert s2.local_map[oggetto_segreto]['status'] == 'FOUND', "Lo status dell'oggetto trasferito è errato!"
    assert s2.local_map[oggetto_segreto]['ts'] == 5, "Il timestamp originale (5) non è stato conservato!"
    
    print("Fase 5 OK - La Mente Alveare (Comunicazione FIPA-ACL) è attiva e funzionante!")

if __name__ == '__main__':
    test_fase5()