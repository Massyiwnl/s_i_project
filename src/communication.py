from src.config import COMM_RADIUS

def exchange_messages(active_agents, tick):
    """
    Simula il protocollo di comunicazione FIPA-ACL (Performative: INFORM).
    Gli agenti a distanza <= COMM_RADIUS si scambiano le mappe locali.
    """
    n = len(active_agents)
    # Doppio ciclo per valutare tutte le coppie uniche di agenti attivi
    for i in range(n):
        for j in range(i + 1, n):
            agent_a = active_agents[i]
            agent_b = active_agents[j]
            
            # Calcolo distanza di Manhattan tra i due agenti
            dist = abs(agent_a.pos[0] - agent_b.pos[0]) + abs(agent_a.pos[1] - agent_b.pos[1])
            
            # Se i loro raggi di comunicazione si intersecano
            if dist <= COMM_RADIUS:
                # 1. Costruzione dei messaggi FIPA-ACL
                msg_from_a = {
                    'performative': 'INFORM',
                    'sender': agent_a.id,
                    'receiver': agent_b.id,
                    'content': agent_a.local_map
                }
                
                msg_from_b = {
                    'performative': 'INFORM',
                    'sender': agent_b.id,
                    'receiver': agent_a.id,
                    'content': agent_b.local_map
                }
                
                # 2. Scambio delle conoscenze (sincronizzazione dei timestamp)
                agent_b.merge_knowledge(msg_from_a['content'], tick)
                agent_a.merge_knowledge(msg_from_b['content'], tick)