from src.config import WALL


def _segment_clear(env, from_r, from_c, to_r, to_c):
    """
    Verifica che un segmento rettilineo (orizzontale o verticale) da
    (from_r, from_c) a (to_r, to_c) non attraversi alcun muro.
    Controlla tutte le celle del segmento, esclusa la cella di partenza.
    """
    if from_r == to_r and from_c == to_c:
        return True  # nessuno spostamento richiesto

    dr = 0 if to_r == from_r else (1 if to_r > from_r else -1)
    dc = 0 if to_c == from_c else (1 if to_c > from_c else -1)

    r, c = from_r + dr, from_c + dc
    while True:
        # FIX: bounds check esplicito prima di accedere a env.grid
        # Senza questo, indici negativi (es. r=-1) NON sollevano IndexError
        # in Python ma accedono all'ultima riga/colonna silenziosamente,
        # producendo LOS errata sui bordi della griglia.
        if not (0 <= r < env.n and 0 <= c < env.n):
            return False
        if env.grid[r][c] == WALL:
            return False
        if r == to_r and c == to_c:
            return True
        r += dr
        c += dc


def has_line_of_sight(env, r1, c1, r2, c2):
    """
    Controllo LOS a forma di L (Manhattan con occlusione).

    FIX 1: bounds check in _segment_clear previene accesso a grid[-1].
    FIX 2: controlla TUTTE le celle intermedie lungo entrambi i percorsi a L,
           non solo la prima e l'ultima. Questo corregge il bug per cui oggetti
           separati da due muri consecutivi risultavano visibili.

    Logica: dati due punti, esistono due percorsi a L:
      - Path 1: prima verticale (r1,c1)->(r2,c1), poi orizzontale (r2,c1)->(r2,c2)
      - Path 2: prima orizzontale (r1,c1)->(r1,c2), poi verticale (r1,c2)->(r2,c2)
    Se almeno uno dei due e' libero, c'e' line-of-sight.
    """
    # Il target non deve essere un muro
    if env.grid[r2][c2] == WALL:
        return False

    # Stessa cella: visibilita' immediata
    if r1 == r2 and c1 == c2:
        return True

    # Percorso puramente orizzontale o verticale: un solo segmento
    if r1 == r2:
        return _segment_clear(env, r1, c1, r2, c2)
    if c1 == c2:
        return _segment_clear(env, r1, c1, r2, c2)

    # Percorso a L: verifica entrambe le varianti
    # Path 1: verticale poi orizzontale
    path1 = (_segment_clear(env, r1, c1, r2, c1) and
             _segment_clear(env, r2, c1, r2, c2))

    # Path 2: orizzontale poi verticale
    path2 = (_segment_clear(env, r1, c1, r1, c2) and
             _segment_clear(env, r1, c2, r2, c2))

    return path1 or path2


def get_visible_objects(env, r, c, radius):
    """Restituisce le coordinate degli oggetti nel raggio visivo (Distanza Manhattan)."""
    visible = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if abs(dr) + abs(dc) <= radius:
                nr, nc = r + dr, c + dc
                if 0 <= nr < env.n and 0 <= nc < env.n:
                    if env.is_object_at(nr, nc) and has_line_of_sight(env, r, c, nr, nc):
                        visible.append((nr, nc))
    return visible

# FIX: detect_adjacent_agents e detect_agents_in_radius erano dead code
# (non chiamate in nessun modulo del progetto). Rimosse per pulizia.