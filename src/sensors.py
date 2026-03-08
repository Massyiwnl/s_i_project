from src.config import WALL

def has_line_of_sight(env, r1, c1, r2, c2):
    """
    Raycasting con risoluzione ambiguità diagonale per raggio 1-3.
    """
    if r1 == r2:
        step = 1 if c2 > c1 else -1
        for c in range(c1 + step, c2, step):
            if env.grid[r1][c] == WALL: return False
        return True
        
    if c1 == c2:
        step = 1 if r2 > r1 else -1
        for r in range(r1 + step, r2, step):
            if env.grid[r][c1] == WALL: return False
        return True

    # Risoluzione ambiguità diagonale
    dr = 1 if r2 > r1 else -1
    dc = 1 if c2 > c1 else -1
    
    # Verifichiamo entrambi i cammini a L per il primo step
    path1_clear = (env.grid[r1+dr][c1] != WALL) and (env.grid[r1+dr][c1+dc] != WALL)
    path2_clear = (env.grid[r1][c1+dc] != WALL) and (env.grid[r1+dr][c1+dc] != WALL)
    
    # Poiché il raggio visivo max è 3, l'approssimazione a L è sufficiente per simulare
    # lo sbirciare dietro l'angolo. Se almeno un lato è libero, c'è visuale.
    return path1_clear or path2_clear

def get_visible_objects(env, r, c, radius):
    """Restituisce le coordinate degli oggetti nel raggio visivo dell'agente."""
    visible = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if abs(dr) + abs(dc) <= radius: # Area a rombo (Manhattan)
                nr, nc = r + dr, c + dc
                if 0 <= nr < env.n and 0 <= nc < env.n:
                    if env.is_object_at(nr, nc) and has_line_of_sight(env, r, c, nr, nc):
                        visible.append((nr, nc))
    return visible

def detect_adjacent_agents(occupancy, r, c):
    """Restituisce il numero di agenti nelle 4 celle adiacenti (per il DEPLOY)."""
    count = 0
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        if (r + dr, c + dc) in occupancy:
            count += 1
    return count

def detect_agents_in_radius(occupancy, r, c, radius):
    """Conta gli agenti nel raggio specificato (senza occlusione)."""
    count = 0
    for occ_r, occ_c in occupancy:
        if (occ_r, occ_c) != (r, c):
            if abs(occ_r - r) + abs(occ_c - c) <= radius:
                count += 1
    return count