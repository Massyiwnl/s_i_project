from src.config import WALL

def has_line_of_sight(env, r1, c1, r2, c2):
    """
    Manhattan con Occlusione (richiesto dal README):
    Controlla che all'interno del bounding box tra i due punti non vi sia un muro
    che blocca palesemente la vista.
    """
    # Se il target è un muro, non lo vediamo come cella calpestabile
    if env.grid[r2][c2] == WALL: return False
    
    # Controllo di occlusione semplificato (L-shape check per distanze Manhattan brevi)
    dr = 1 if r2 > r1 else -1 if r2 < r1 else 0
    dc = 1 if c2 > c1 else -1 if c2 < c1 else 0
    
    path1_clear = True
    path2_clear = True
    
    # Verifica percorso 1 (prima verticale, poi orizzontale)
    if dr != 0:
        if env.grid[r1+dr][c1] == WALL: path1_clear = False
    if dc != 0 and path1_clear:
        if env.grid[r2][c1+dc] == WALL: path1_clear = False

    # Verifica percorso 2 (prima orizzontale, poi verticale)
    if dc != 0:
        if env.grid[r1][c1+dc] == WALL: path2_clear = False
    if dr != 0 and path2_clear:
        if env.grid[r1+dr][c2] == WALL: path2_clear = False
        
    return path1_clear or path2_clear

def get_visible_objects(env, r, c, radius):
    """Restituisce le coordinate degli oggetti nel raggio visivo (Distanza Manhattan)."""
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
    count = 0
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        if (r + dr, c + dc) in occupancy:
            count += 1
    return count

def detect_agents_in_radius(occupancy, r, c, radius):
    count = 0
    for occ_r, occ_c in occupancy:
        if (occ_r, occ_c) != (r, c):
            if abs(occ_r - r) + abs(occ_c - c) <= radius:
                count += 1
    return count