import random
from src.config import STIGMA_ON, CONGESTION_MALUS


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
    Calcola l'utilita' di ogni mossa adiacente basandosi sui feromoni e stigmergia.
    weights = {'home': float, 'explore': float, 'object': float}

    FIX 1: STIGMA_ON controlla se la repulsione esplorativa e' attiva
           (Configurazione C2 del progetto).
    FIX 2: CONGESTION_MALUS penalizza le celle occupate/riservate quando
           l'agente e' costretto a muoversi su di esse (fallback da free_moves).
    FIX 3: confronto float con abs() < 1e-9 invece di == per evitare errori
           di rappresentazione in virgola mobile.
    """
    valid_moves = get_valid_local_moves(env, r, c)
    if not valid_moves:
        return r, c  # Stallo locale: rimane fermo (incrementa stuck_ticks)

    # Isola le mosse libere da occupancy e intentions
    free_moves = [(nr, nc) for nr, nc in valid_moves
                  if (nr, nc) not in env.occupancy and (nr, nc) not in env.intentions]
    candidate_moves = free_moves if free_moves else valid_moves

    best_moves = []
    max_utility = float('-inf')

    for nr, nc in candidate_moves:
        utility = 0.0

        # 1. Penalita' di congestione: celle fisicamente occupate o riservate
        #    (FIX: usa CONGESTION_MALUS da config invece di valore hardcoded)
        if (nr, nc) in env.occupancy or (nr, nc) in env.intentions:
            utility -= CONGESTION_MALUS

        # 2. Attrazione verso il magazzino (Feromone statico)
        utility += env.pheromone_home[nr][nc] * weights.get('home', 0.0)

        # 3. Attrazione verso tracce di oggetti scoperti da altri
        utility += env.pheromone_object[nr][nc] * weights.get('object', 0.0)

        # 4. Repulsione dalle zone gia' esplorate (Stigmergia esplorativa)
        #    FIX: attiva solo se STIGMA_ON e' True (Configurazione C2)
        if STIGMA_ON:
            utility -= env.pheromone_explore[nr][nc] * weights.get('explore', 0.0)

        if utility > max_utility:
            max_utility = utility
            best_moves = [(nr, nc)]
        # FIX: confronto float sicuro con tolleranza assoluta invece di ==
        # (due utilita' matematicamente uguali possono differire di ~1e-15
        # a causa della rappresentazione IEEE 754)
        elif abs(utility - max_utility) < 1e-9:
            best_moves.append((nr, nc))

    # Incertezza di Knight / Esplorazione Stocastica: scelta casuale tra pari utilita'
    return random.choice(best_moves)