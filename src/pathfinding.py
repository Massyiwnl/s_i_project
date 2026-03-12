import random

def get_valid_local_moves(env, r, c):
    """Restituisce le celle adiacenti percorribili (Regola locale)."""
    moves = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if env.is_walkable(nr, nc, agent_r=r, agent_c=c):
            moves.append((nr, nc))
    return moves

def evaluate_utility(env, r, c, weights):
    """
    Decision Making in Certezza/Incertezza: 
    Calcola l'utilità di ogni mossa adiacente basandosi sui feromoni e stigmergia.
    weights = {'home': float, 'explore': float, 'object': float}
    """
    valid_moves = get_valid_local_moves(env, r, c)
    if not valid_moves:
        return r, c # Nessuna mossa disponibile (stallo locale)

    # --- FIX 2: PREVENZIONE CONGESTIONI (Evitamento Dinamico) ---
    # Isoliamo le mosse libere. Se tutti i varchi sono bloccati, ripieghiamo 
    # su quelle valide accettando momentaneamente lo stallo/attesa.
    free_moves = [(nr, nc) for nr, nc in valid_moves if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
    candidate_moves = free_moves if free_moves else valid_moves
    # ------------------------------------------------------------

    best_moves = []
    max_utility = float('-inf')

    for nr, nc in candidate_moves:
        utility = 0.0
        
        # 1. Attrazione verso il magazzino (Feromone statico)
        utility += env.pheromone_home[nr][nc] * weights.get('home', 0.0)
        
        # 2. Attrazione verso tracce di oggetti scoperti da altri
        utility += env.pheromone_object[nr][nc] * weights.get('object', 0.0)
        
        # 3. REPULSIONE dalle zone già esplorate (Stigmergia esplorativa)
        # Sottraiamo il feromone esplorativo: più è alto, meno è utile andarci
        utility -= env.pheromone_explore[nr][nc] * weights.get('explore', 0.0)
        
        if utility > max_utility:
            max_utility = utility
            best_moves = [(nr, nc)]
        elif utility == max_utility:
            best_moves.append((nr, nc))
            
    # Incertezza di Knight / Esplorazione Stocastica: se ci sono più opzioni 
    # di pari utilità (o in esplorazione cieca), scegliamo casualmente
    return random.choice(best_moves)