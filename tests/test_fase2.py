from src.environment import Environment
from src.decision_making import astar, real_distance

def test_fase2():
    env = Environment()
    env.load('data/A.json')
    
    # 1. Test A* basilare (Modificato: la cella 5,5 era un muro, usiamo 4,4 che è vuota)
    path = astar(env, (0, 0), (4, 4))
    assert len(path) > 0 and path[0] == (0, 0) and path[-1] == (4, 4), "Il percorso A* non è valido"
    
    # 2. Test validità percorso step-by-step
    for i in range(len(path) - 1):
        pr, pc = path[i]
        nr, nc = path[i + 1]
        assert env.is_walkable(nr, nc, pr, pc), f"Passo non percorribile: da ({pr},{pc}) a ({nr},{nc})"
        
    # 3. Test distanza reale vs Manhattan (i muri allungano il percorso)
    dist = real_distance(env, (0, 0), (10, 10))
    # Manhattan sarebbe 20, ma con i muri in mezzo la distanza reale deve essere per forza maggiore o uguale
    assert dist >= 20, f"La distanza reale ({dist}) calcolata è inferiore a quella di Manhattan pura!"
    
    print("Fase 2 OK - Tutti i test superati!")

if __name__ == "__main__":
    test_fase2()