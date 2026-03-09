from src.environment import Environment

def test_fase1():
    env = Environment()
    env.load('data/A.json')
    
    assert len(env.grid) == 25 and len(env.grid[0]) == 25, "Errore caricamento griglia"
    assert len(env.warehouses) == 4, "Errore caricamento magazzini"
    assert env.delivered == 0, "Counter delivered errato"
    
    # Test senso unico
    wh = env.warehouses[0]
    er, ec = wh['entrance']
    
    # Se il magazzino 0 ha lato 'top', l'entrata corretta è da Nord (riga precedente)
    assert env.is_walkable(er, ec, er-1, ec) == True, "L'agente non riesce a entrare da Nord"
    # Un agente che arriva da Sud (interno magazzino o oltre) non può usare la ENTRANCE in controsenso
    assert env.is_walkable(er, ec, er+1, ec) == False, "L'agente riesce a entrare in controsenso da Sud!"
    
    print("Fase 1 OK - Tutti i test superati!")

if __name__ == "__main__":
    test_fase1()