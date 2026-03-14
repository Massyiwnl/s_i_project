import random
import numpy as np

# -- Riproducibilita' --
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# -- Ambiente --
GRID_SIZE = 25
EMPTY, WALL = 0, 1
WAREHOUSE = 2
ENTRANCE = 3
EXIT = 4
NUM_OBJECTS = 10
MAX_TICKS = 500

# -- Agenti --
NUM_AGENTS = 5
BATTERY_INITIAL = 500
# FIX: ENERGY_MARGIN ora usato in check_battery come moltiplicatore della soglia.
# Con 1.20, la soglia diventa BATTERY_INITIAL * 0.10 * 1.20 = 60 (invece di 50 hardcoded).
ENERGY_MARGIN = 1.20

# -- Sensori e Comunicazione --
VISION_RADIUS = 3  # Configurazione C1: cambia questo (1 vs 3)
COMM_RADIUS = 2
# FIX: DEPLOY_RADIUS ora usato in try_spawn_next per cercare celle di spawn
# entro distanza Manhattan DEPLOY_RADIUS da (0,0).
DEPLOY_RADIUS = 1

# -- Stigmergia --
# FIX: CONGESTION_MALUS ora usato in evaluate_utility come penalita' per celle occupate.
CONGESTION_MALUS = 10
EVAPORATION_RATE = 0.05
# FIX: STIGMA_ON ora controllato in pathfinding.py e environment.py.
# Configurazione C2: imposta a False per disattivare la stigmergia esplorativa.
STIGMA_ON = True

# -- Gestione Stress (stuck) --
# FIX: STRESS_MAX e STRESS_RANDOM_STEPS ora usati in base_agent, scouts e workers.
# STRESS_MAX: soglia massima di stuck_ticks per il ritorno a base.
# STRESS_RANDOM_STEPS: numero massimo di tentativi casuali in _dodge_step.
STRESS_MAX = 15
STRESS_RANDOM_STEPS = 4

# -- Visualizzazione --
GUI = True  # Imposta a False per le run statistiche veloci