from src.config import COMM_RADIUS

def get_agents_in_radius(env, pos, radius):
    """
    Simula il raggio di rete wireless dell'agente.
    Cerca nell'ambiente gli altri agenti attivi e restituisce quelli a portata.
    """
    neighbors = []
    
    # Verifica che l'ambiente abbia la lista aggiornata degli agenti
    if hasattr(env, 'active_agents'):
        for agent in env.active_agents:
            # Ignora se stesso o gli agenti morti
            if agent.pos == pos or agent.state == 'DEAD':
                continue 
                
            # Calcolo Distanza di Manhattan
            dist = abs(pos[0] - agent.pos[0]) + abs(pos[1] - agent.pos[1])
            if dist <= radius:
                neighbors.append(agent)
                
    return neighbors

def create_inform_message(sender_id, receiver_id, content):
    """
    Costruisce la struttura standard del messaggio FIPA-ACL (Performative: INFORM)
    come richiesto dalle direttive del progetto.
    """
    return {
        'performative': 'INFORM',
        'sender': sender_id,
        'receiver': receiver_id,
        'content': content
    }