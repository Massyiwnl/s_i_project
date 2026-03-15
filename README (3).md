# MAPD Swarm Intelligence — Sistema Multi-Agente Logistico

> Progetto di Artificial & Swarm Intelligence — A.A. 2025/2026  
> Massimiliano Cassia

---

## Indice

1. [Panoramica del progetto](#1-panoramica-del-progetto)
2. [Struttura del repository](#2-struttura-del-repository)
3. [Architettura del sistema](#3-architettura-del-sistema)
4. [Gli agenti](#4-gli-agenti)
5. [L'ambiente](#5-lambiente)
6. [Meccanismi di interazione](#6-meccanismi-di-interazione)
7. [Decision making e navigazione](#7-decision-making-e-navigazione)
8. [Configurazioni sperimentali](#8-configurazioni-sperimentali)
9. [Come eseguire il progetto](#9-come-eseguire-il-progetto)
10. [Analisi dei risultati](#10-analisi-dei-risultati)
11. [Parametri di configurazione](#11-parametri-di-configurazione)
12. [Limitazioni note e sviluppi futuri](#12-limitazioni-note-e-sviluppi-futuri)

---

## 1. Panoramica del progetto

Il progetto implementa un **sistema di simulazione multi-agente (ABM — Agent-Based Model)** ispirato al paradigma ACO (Ant Colony Optimization) per la gestione autonoma di un magazzino logistico su griglia.

Cinque agenti autonomi di tipo eterogeneo — **Scout** ed **Worker** — cooperano per individuare oggetti dispersi nella mappa e consegnarli ai magazzini, senza alcun coordinatore centrale. Il comportamento collettivo emerge dalle interazioni locali tra agenti e dall'ambiente condiviso tramite **stigmergia** (deposito ed evaporazione di feromoni) e **comunicazione diretta FIPA-ACL**.

### Perché un ABM e non un algoritmo classico

| Criterio | ABM (questo progetto) | Ottimizzazione classica |
|---|---|---|
| Gestione imprevisti | Adattamento locale in tempo reale | Ricalcolo globale necessario |
| Scalabilità | Aggiunta di agenti senza ridisegnare il sistema | Complessità cresce esponenzialmente |
| Comportamento emergente | Sì — non programmato esplicitamente | No — soluzione deterministica |
| Analisi dinamiche | Osserva *come* si raggiunge il risultato | Fornisce solo il risultato ottimo statico |

### Obiettivi di ottimizzazione multi-obiettivo

1. **Riduzione del tempo ciclo** — minimizzare i tick necessari per consegnare tutti gli oggetti
2. **Massimizzazione dell'utilizzo risorse** — ridurre i tick in cui gli agenti sono inattivi o bloccati
3. **Minimizzazione dei conflitti** — evitare deadlock, congestioni e race condition nel recupero degli oggetti

---

## 2. Struttura del repository

```
s_i_project/
│
├── src/                          # Codice sorgente principale
│   ├── config.py                 # Tutti i parametri configurabili del sistema
│   ├── environment.py            # Griglia, feromoni, occupancy, log di traffico
│   ├── communication.py          # Protocollo FIPA-ACL e raggio di comunicazione
│   ├── sensors.py                # Raggio visivo e line-of-sight (LOS)
│   ├── pathfinding.py            # Funzione di utilità locale e mosse valide
│   ├── main.py                   # Loop di simulazione principale
│   │
│   ├── agents/
│   │   ├── base_agent.py         # Classe base con comportamenti condivisi
│   │   ├── scouts.py             # Scout1, Scout2 — agenti esploratori
│   │   └── workers.py            # Worker1, Worker2, Worker3 — agenti operativi
│   │
│   └── utils/
│       ├── logger.py             # Registrazione eventi e serializzazione JSON
│       ├── analyzer.py           # Statistiche per agente e report CSV
│       ├── renderer.py           # Visualizzazione real-time con matplotlib
│       └── plotter.py            # Generazione tabelle visuali da CSV
│
├── experiments/
│   ├── run_configs.py            # Esecuzione automatica di più run in sequenza
│   └── analyze_results.py        # Report statistico e heatmap aggregate su 5 seed
│
├── data/
│   ├── A.json                    # Mappa istanza A (fornita dal professore)
│   └── B.json                    # Mappa istanza B (fornita dal professore)
│
├── tools/
│   └── visualize_environment.py  # Visualizzazione statica della mappa da JSON
│
└── outputs/
    ├── logs/                     # Log JSON delle simulazioni
    └── heatmaps/                 # Heatmap PNG generate da analyze_results.py
```

---

## 3. Architettura del sistema

Il sistema è strutturato a **tre livelli gerarchici** con separazione netta delle responsabilità.

### Livello 1 — Infrastruttura
`config.py`, `environment.py`, `communication.py`, `sensors.py`, `pathfinding.py`

Gestisce la griglia fisica, i feromoni, la percezione sensoriale e la funzione di decision making. Questo livello non conosce i tipi specifici di agenti.

### Livello 2 — Agenti
`base_agent.py`, `scouts.py`, `workers.py`

`BaseAgent` implementa tutti i comportamenti primitivi condivisi (percezione, comunicazione, movimento, gestione batteria, deposito feromoni). `Scout` e `Worker` estendono `BaseAgent` sovrascrivendo solo la strategia specifica, senza duplicare codice.

### Livello 3 — Orchestrazione e analisi
`main.py`, `logger.py`, `analyzer.py`, `renderer.py`, `run_configs.py`, `analyze_results.py`

Gestisce il loop di simulazione, il salvataggio dei dati, la visualizzazione real-time e l'analisi post-simulazione.

### Loop di simulazione (per ogni tick)

```
1. clear_intentions()           — reset prenotazioni celle
2. try_spawn_next()             — spawn agente dalla coda se cella libera
3. shuffle(active_agents)       — ordine casuale per fairness
4. per ogni agente:
   - decrementa batteria
   - chiama decide_action()     — percezione → decisione → azione
   - logger.log()
5. update_stigma()              — evaporazione feromoni dinamici
6. renderer.draw()              — aggiornamento GUI (se attiva)
7. record_exploration()         — checkpoint a tick 100, 250, finale
```

---

## 4. Gli agenti

### Stato interno comune (BaseAgent)

Ogni agente possiede le seguenti variabili di stato, coerenti con la definizione teorica di stato interno nei sistemi ABM:

| Variabile | Tipo | Descrizione |
|---|---|---|
| `id` | int | Identità univoca |
| `pos` | tuple (r, c) | Posizione corrente sulla griglia |
| `state` | str | Stato FSM corrente |
| `battery` | int | Energia rimanente |
| `carrying` | bool | Se sta trasportando un oggetto |
| `local_map` | dict | Mappa cognitiva dell'ambiente |
| `stuck_ticks` | int | Tick consecutivi senza movimento |
| `current_intention` | tuple | Cella prenotata per il prossimo passo |

### Macchina a stati finiti (FSM)

```
EXPLORE ──oggetto trovato──► RETRIEVE ──raggiunto──► RETURN_HOME ──consegnato──► EXIT_WAREHOUSE ──► EXPLORE
   │                                                       │
   │ batteria < soglia                          batteria < soglia (carico)
   ▼                                                       │
RETURN_BASE ──dist=0──► FINISHED                           │
                                               batteria ≤ EMERGENCY_DROP_BATTERY
                                                           ▼
                                                  abbandona oggetto → RETURN_BASE
```

### Scout1

- **Obiettivo:** massimizzare la copertura della mappa
- **Pesi utilità:** `{'home': -0.1, 'explore': 1.0, 'object': 0.0}`
- **Comportamento:** evita attivamente i magazzini (peso home negativo), privilegia zone inesplorate, ignora gli oggetti
- **Soglia stuck:** `STRESS_MAX // 5 = 3 tick`

### Scout2

- **Obiettivo:** esplorare con attenzione ai segnali di oggetti
- **Pesi utilità:** `{'home': -0.1, 'explore': 0.5, 'object': 1.5}`
- **Comportamento:** bilancia esplorazione e inseguimento di tracce feromone-oggetto
- **Differenza da Scout1:** raccoglie informazioni su zone con oggetti e le propaga allo sciame più efficacemente

### Worker1

- **Obiettivo:** raccogliere e consegnare oggetti con strategia bilanciata
- **Pesi esplorazione:** `{'home': -0.1, 'explore': 1.0, 'object': 2.0}`
- **Pesi ritorno:** `{'home': 5.0, 'explore': 0.5, 'object': 0.0}`
- **Risultato osservato:** agente più produttivo (5/10 consegne nel seed 42)

### Worker2

- **Obiettivo:** massimizzare il recupero di oggetti con strategia aggressiva
- **Pesi esplorazione:** `{'home': 0.0, 'explore': 0.3, 'object': 3.0}`
- **Nota:** il peso oggetto alto porta l'agente verso oggetti lontani dalla base, allungando i tempi di ritorno e riducendo paradossalmente il numero di cicli completati — risultato emergente non intuitivo

### Worker3

- **Obiettivo:** strategia intermedia con attenzione alla base
- **Pesi esplorazione:** `{'home': 0.5, 'explore': 0.8, 'object': 2.5}`
- **Caratteristica:** la componente `home` positiva lo mantiene più vicino ai magazzini durante l'esplorazione

---

## 5. L'ambiente

### Griglia e tipi di cella

La mappa è una griglia `GRID_SIZE × GRID_SIZE` (default 25×25) modellata come un **grafo planare** dove ogni cella è un nodo e ogni adiacenza ortogonale è un arco.

| Valore | Costante | Descrizione |
|---|---|---|
| 0 | `EMPTY` | Cella percorribile libera |
| 1 | `WALL` | Ostacolo non attraversabile |
| 2 | `WAREHOUSE` | Zona di deposito — trigger consegna |
| 3 | `ENTRANCE` | Accesso unidirezionale al magazzino |
| 4 | `EXIT` | Uscita unidirezionale dal magazzino |

`ENTRANCE` e `EXIT` sono percorribili solo nella direzione corretta (controllata da `_coming_from_outside` e `_coming_from_inside`) — impediscono movimenti anti-direzione nei corridoi di magazzino.

### Sistema di feromoni

Il sistema usa **quattro campi di feromoni** con semantiche distinte:

| Feromone | Tipo | Chi lo crea | Scopo |
|---|---|---|---|
| `pheromone_home` | Statico (BFS) | Sistema al caricamento | Guida verso il magazzino più vicino |
| `pheromone_base` | Statico (BFS) | Sistema al caricamento | Guida verso lo spawn `(0,0)` |
| `pheromone_explore` | Dinamico | Ogni agente in movimento | Repulsione dalle zone già visitate (anti-loop) |
| `pheromone_object` | Dinamico | Solo agenti carichi | Segnala rotte verso magazzini (traccia di ritorno) |

I gradienti statici usano valore iniziale `n²` per garantire positività su qualsiasi mappa quadrata di lato `n`. I feromoni dinamici evaporano con tasso `EVAPORATION_RATE` ad ogni tick tramite `update_stigma()`, che itera solo le celle attive (set `active_pheromone_cells`) invece dell'intera griglia — O(celle_attive) invece di O(n²).

### Log di traffico

| Log | Quando viene aggiornato | Scopo |
|---|---|---|
| `traffic_log` | Ad ogni consegna (`_handle_return_home`) | Identifica i magazzini più usati |
| `movement_log` | Ad ogni passo fisico (`_try_move`) | Alimenta la vera heatmap dei colli di bottiglia |

---

## 6. Meccanismi di interazione

Il progetto implementa entrambi i paradigmi di comunicazione trattati nel corso, usati in modo complementare.

### Comunicazione diretta — FIPA-ACL

```python
# Struttura del messaggio INFORM
{
    'performative': 'INFORM',
    'sender':       neighbor.id,
    'receiver':     self.id,
    'content': {
        'map': neighbor.local_map,
        'ts':  tick
    }
}
```

Ogni agente trasmette la propria `local_map` ai vicini entro raggio `COMM_RADIUS`. Il merge usa il timestamp per risolvere i conflitti: l'informazione più recente vince, tranne per lo stato `TAKEN` che è irrevocabile. La comunicazione è filtrata per `caller_id` (non per posizione) per escludere correttamente sé stessi.

### Comunicazione indiretta — Stigmergia

Gli agenti modificano l'ambiente depositando feromoni sulle celle attraversate. Gli altri agenti percepiscono queste modifiche e adattano il comportamento senza sapere chi ha lasciato la traccia. Questo è il meccanismo **spatially grounded** e anonimo: scalabile, robusto al fallimento dei singoli agenti, disaccoppiato nel tempo e nello spazio.

### Percezione sensoriale

Il raggio visivo è un **rombo Manhattan** di raggio `VISION_RADIUS`. La visibilità di ogni cella entro il rombo è verificata tramite controllo di occlusione **a forma di L** (`has_line_of_sight`): esistono due percorsi a L tra agente e target; se almeno uno è libero da muri, la cella è visibile.

```
Raggio 1: vede 4 celle adiacenti
Raggio 3: vede fino a 25 celle (rombo completo) con occlusione
```

---

## 7. Decision making e navigazione

### Funzione di utilità locale

Il decision making implementa il modello teorico di **decision making in contesto di incertezza** (Incertezza di Knight): l'agente non conosce il percorso globale e valuta solo la mossa immediata.

```python
utility  = pheromone_home[nr][nc]   * weights['home']
utility += pheromone_object[nr][nc] * weights['object']
if STIGMA_ON:
    utility -= pheromone_explore[nr][nc] * weights['explore']
if cella_occupata_o_prenotata:
    utility -= CONGESTION_MALUS   # penalità soft differenziale
```

`CONGESTION_MALUS` è una penalità **differenziale**: l'agente confronta simultaneamente celle libere e celle occupate, scegliendo quella con utilità netta massima. Non esclude a priori le celle occupate — le penalizza rispetto alle libere, permettendo di accettarle se significativamente più convenienti.

Tra mosse di pari utilità, la scelta è **stocastica** (`random.choice`) — implementazione dell'esplorazione stocastica per evitare comportamenti deterministici degeneri.

### Navigazione verso target noto

`_move_towards_target` minimizza la distanza Manhattan applicando una penalità esplorativa anti-loop (solo se `STIGMA_ON = True`):

```
score = distanza_manhattan + pheromone_explore[cella] * EXPLORE_PENALTY_WEIGHT
```

### Meccanismo anti-deadlock

Quando `stuck_ticks` supera la soglia (`STRESS_MAX // 2` per Worker, `STRESS_MAX // 5` per Scout), l'agente tenta fino a `STRESS_RANDOM_STEPS` passi casuali tra le celle libere adiacenti. Questo sblocca situazioni di stallo locale senza comunicazione esplicita.

### Selezione del target più vicino

`_has_found_object` seleziona l'oggetto recuperabile (stato `FOUND` o `ABANDONED`) con distanza Manhattan minima dalla posizione corrente — nearest neighbor selection sulla mappa locale.

---

## 8. Configurazioni sperimentali

Il progetto supporta tre configurazioni sperimentali che permettono di isolare l'impatto di singoli parametri:

### C1 — Raggio visivo (Vision Radius)

```python
VISION_RADIUS = 1   # Visione minima: solo 4 celle adiacenti
VISION_RADIUS = 3   # Visione estesa: rombo di 25 celle
```

Impatto atteso: con raggio 1 l'esplorazione è più lenta, la conoscenza si accumula più gradualmente, e gli oggetti vengono trovati più tardi. Con raggio 3 la copertura per tick è nettamente superiore ma il costo computazionale del controllo LOS aumenta.

### C2 — Stigmergia attiva/disattivata

```python
STIGMA_ON = True    # Feromoni esplorativi attivi (default)
STIGMA_ON = False   # Solo gradiente statico + CONGESTION_MALUS
```

Impatto atteso: senza stigmergia gli agenti tendono a rivisitare le stesse zone, riducendo l'efficienza esplorativa. I colli di bottiglia aumentano perché il meccanismo anti-congestione basato sul feromone esplorativo non è attivo.

### C3 — Confronto istanze A vs B

Due mappe con topologie diverse. L'istanza A presenta un corridoio obbligato centrale (collo di bottiglia concentrato). L'istanza B ha traffico più distribuito tra due cluster di magazzini.

---

## 9. Come eseguire il progetto

### Prerequisiti

```bash
pip install numpy matplotlib seaborn
```

### Singola simulazione con GUI

```bash
python -m src.main --instance A --seed 42
```

### Singola simulazione senza GUI (per esperimenti automatici)

```bash
python -m src.main --instance A --seed 42 --no-gui
```

### Esperimento automatico su 5 seed

```bash
# Esegue 5 run in sequenza senza GUI, con timeout e controllo errori
python experiments/run_configs.py
```

### Analisi statistica e generazione heatmap

```bash
# Genera report statistico e due heatmap (consegne + colli di bottiglia)
python experiments/analyze_results.py
```

### Visualizzazione statica della mappa

```bash
python tools/visualize_environment.py data/A.json outputs/mappa_A.png
```

### Output prodotti da ogni run

```
outputs/logs/
├── run_A_seed42.json              # Log completo con metadata ed eventi
├── run_A_seed42_report.txt        # Report tabellare eventi salienti
├── run_A_seed42_agents.csv        # Statistiche per agente
└── experiments_summary.csv        # Tabella aggregata di tutte le run

outputs/heatmaps/
├── heatmap_consegne_A.png         # Distribuzione punti di consegna
└── heatmap_bottleneck_A.png       # Colli di bottiglia (traffico reale agenti)
```

---

## 10. Analisi dei risultati

### Struttura del log JSON

```json
{
  "metadata": {
    "ticks_total": 322,
    "delivered": 10,
    "critical_failures": 0,
    "avg_energy_consumed": 321.0,
    "exploration_percent": {
      "tick_100": 59.32,
      "tick_250": 85.3,
      "tick_322": 95.28
    },
    "traffic_log":  { "[2, 11]": 4, "[11, 2]": 3, ... },
    "movement_log": { "[2, 11]": 20, "[4, 11]": 19, ... }
  },
  "events": [
    {
      "tick": 0, "id": 1, "agent_type": "Worker1",
      "pos": [0, 0], "battery": 499,
      "carrying": false, "state": "EXPLORE"
    },
    ...
  ]
}
```

### Metriche chiave per la valutazione

| Metrica | Descrizione | Fonte |
|---|---|---|
| `ticks_total` | Tick al completamento (< 500 = successo) | metadata |
| `delivered` | Oggetti consegnati (target: 10) | metadata |
| `critical_failures` | Agenti morti per batteria esaurita | metadata |
| `avg_energy_consumed` | Energia media consumata per agente | metadata |
| `exploration_percent` | % mappa conosciuta ai checkpoint | metadata |
| `movement_log` | Passaggi per cella — heatmap bottleneck | metadata |

### Risultati istanza A (seed 42 — run rappresentativa)

| Agente | Tipo | Consegne | Spostamenti | Stato finale |
|---|---|---|---|---|
| 1 | Worker1 | 5 | 312 | RETRIEVE |
| 2 | Scout2 | 0 | 317 | EXPLORE |
| 3 | Worker2 | 2 | 304 | EXPLORE |
| 4 | Worker3 | 3 | 304 | EXIT_WAREHOUSE |
| 5 | Scout1 | 0 | 318 | EXPLORE |

Completamento: **tick 322/500** — efficienza del 64%.  
Esplorazione finale: **95.28%** della mappa conosciuta.  
Rapporto mosse effettive/teoriche: **96.8%** — tempo di stallo minimo.

### Lettura delle heatmap

**`heatmap_consegne`** (colormap Blues) — mostra la distribuzione del carico tra i magazzini disponibili. Zone più scure = magazzini più usati. Permette di valutare se il sistema usa efficientemente tutti i depositi o si concentra su uno solo.

**`heatmap_bottleneck`** (colormap YlOrRd) — mostra i corridoi più transitati dagli agenti durante l'intera simulazione (aggregato su 5 run). Zone rosse intense = colli di bottiglia strutturali della mappa: corridoi obbligati che tutti gli agenti devono attraversare. Utile per identificare dove aggiungere percorsi alternativi per ridurre la congestione.

---

## 11. Parametri di configurazione

Tutti i parametri sono centralizzati in `src/config.py`. Modificare i valori lì si propaga automaticamente all'intero sistema senza toccare il codice degli agenti.

| Parametro | Default | Descrizione |
|---|---|---|
| `GRID_SIZE` | 25 | Lato della griglia quadrata |
| `NUM_OBJECTS` | 10 | Oggetti da raccogliere e consegnare |
| `MAX_TICKS` | 500 | Tick massimi per simulazione |
| `NUM_AGENTS` | 5 | Numero totale di agenti |
| `BATTERY_INITIAL` | 500 | Batteria iniziale di ogni agente |
| `ENERGY_MARGIN` | 1.20 | Moltiplicatore soglia ritorno (+20%) |
| `EMERGENCY_DROP_BATTERY` | 2 | Soglia abbandono forzato oggetto |
| `VISION_RADIUS` | 3 | Raggio visivo Manhattan (**C1**) |
| `COMM_RADIUS` | 2 | Raggio comunicazione FIPA-ACL |
| `DEPLOY_RADIUS` | 1 | Raggio di spawn attorno a (0,0) |
| `STIGMA_ON` | True | Attiva/disattiva stigmergia (**C2**) |
| `EVAPORATION_RATE` | 0.05 | Tasso evaporazione feromoni dinamici |
| `CONGESTION_MALUS` | 10 | Penalità soft per celle occupate |
| `EXPLORE_PENALTY_WEIGHT` | 0.5 | Peso penalità anti-loop in navigazione diretta |
| `STRESS_MAX` | 15 | Soglia massima stuck_ticks |
| `STRESS_RANDOM_STEPS` | 4 | Tentativi casuali in _dodge_step |
| `GUI` | True | Abilita renderer real-time |
| `SEED` | 42 | Seed di default per riproducibilità |

---

## 12. Limitazioni note e sviluppi futuri

### Limitazioni consapevoli

**Nessun apprendimento adattivo.** I pesi della funzione di utilità sono costanti per tutta la simulazione e tra run diverse. Un sistema con reinforcement learning modificherebbe i pesi in base ai risultati ottenuti, ma questo è al di fuori degli argomenti trattati nel corso.

**Nessuna negoziazione esplicita per le risorse.** I conflitti di pickup si risolvono tramite atomicità (chi arriva prima prende). Un protocollo FIPA completo con `REQUEST`/`PROPOSE`/`AGREE` permetterebbe prenotazioni esplicite degli oggetti, ma aumenterebbe il volume di messaggi di un ordine di grandezza.

**Mappa statica.** La topologia non cambia durante la simulazione. In un sistema reale, corridoi potrebbero bloccarsi e nuovi oggetti apparire dinamicamente.

**Paradosso del feromone oggetto.** `pheromone_object` viene depositato durante il ritorno al magazzino, non durante l'andata. La scia punta quindi verso il magazzino invece che verso la sorgente degli oggetti — un Worker che segue questa scia converge verso il deposito invece di trovare nuovi oggetti. Lasciato intenzionalmente come punto di discussione teorica sull'ACO.

**Heatmap aggregata.** `movement_log` somma i passaggi di tutti gli agenti indipendentemente da tipo e stato. Una versione più informativa avrebbe log separati per tipo di agente e per stato FSM.

### Possibili estensioni

- Aggiungere uno stato `PANIC` con pesi alterati per simulare comportamenti di evacuazione d'emergenza
- Dinamiche ambientali runtime: corridoi che si chiudono, zone che diventano inaccessibili
- Meccanismo di prenotazione oggetti tramite messaggi FIPA `REQUEST`/`AGREE`
- Normalizzazione dei gradienti BFS tra 0 e 1 per indipendenza dalla dimensione della mappa
- Log separati per tipo di agente in `movement_log` per analisi più granulari dei colli di bottiglia

---

## Struttura delle dipendenze tra moduli

```
config.py
    └── importato da tutti i moduli

environment.py
    └── usa: config.py

communication.py
    └── usa: (nessuna dipendenza interna)

sensors.py
    └── usa: config.py

pathfinding.py
    └── usa: config.py

base_agent.py
    └── usa: config, communication, sensors, pathfinding

scouts.py / workers.py
    └── usa: base_agent, pathfinding, config

main.py
    └── usa: config, environment, logger, renderer, workers, scouts

logger.py
    └── usa: config

analyzer.py
    └── usa: config

run_configs.py / analyze_results.py
    └── usa: config (analyze_results), subprocess (run_configs)
```

---

*Progetto sviluppato nell'ambito del corso di Artificial & Swarm Intelligence, A.A. 2025/2026.*
