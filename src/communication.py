from src.config import COMM_RADIUS


def get_agents_in_radius(env, pos, radius, caller_id=None):
    """
    Simula il raggio di rete wireless dell'agente.
    Cerca nell'ambiente gli altri agenti attivi e restituisce quelli a portata.

    il parametro caller_id permette di escludere l'agente chiamante
    per identita' (agent.id == caller_id)
    """
    neighbors = []

    if hasattr(env, 'active_agents'):
        for agent in env.active_agents:
            # FIX: escludi per ID, non per posizione
            if agent.id == caller_id or agent.state == 'DEAD':
                continue

            dist = abs(pos[0] - agent.pos[0]) + abs(pos[1] - agent.pos[1])
            if dist <= radius:
                neighbors.append(agent)

    return neighbors


def create_inform_message(sender_id, receiver_id, content):
    """
    Costruisce la struttura standard del messaggio FIPA-ACL
    (Performative: INFORM)
    """
    return {
        'performative': 'INFORM',
        'sender': sender_id,
        'receiver': receiver_id,
        'content': content
    }