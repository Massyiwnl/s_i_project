import heapq

def manhattan_distance(r1, c1, r2, c2):
    return abs(r1 - r2) + abs(c1 - c2)

def astar(env, start, goal, stigma_map=None):
    """
    Calcola il cammino minimo da start a goal usando A*.
    Rispetta i sensi unici passando la cella precedente a is_walkable.
    """
    if start == goal:
        return [start]

    open_set = []
    heapq.heappush(open_set, (0, 0, start))
    came_from = {}
    g_score = {start: 0}
    
    # Counter per evitare conflitti nell'heapq se f_score è identico
    counter = 1 

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1] # Inverte per avere [start, ..., goal]

        r, c = current
        # Controllo le 4 direzioni: Nord, Sud, Est, Ovest
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            
            # Qui applichiamo la logica dei sensi unici: l'agente sta in (r,c) e vuole andare in (nr,nc)
            if env.is_walkable(nr, nc, agent_r=r, agent_c=c):
                # Costo base del passo
                step_cost = 1 
                # Aggiunta malus stigmergico se fornito
                if stigma_map:
                    step_cost += stigma_map[nr][nc]
                
                tentative_g_score = g_score[current] + step_cost
                neighbor = (nr, nc)

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + manhattan_distance(nr, nc, goal[0], goal[1])
                    heapq.heappush(open_set, (f_score, counter, neighbor))
                    counter += 1

    return [] # Nessun percorso trovato

def real_distance(env, start, goal):
    """Calcola la distanza reale sul tracciato, considerando i muri e i sensi unici."""
    path = astar(env, start, goal)
    if not path:
        return float('inf')
    return len(path) - 1