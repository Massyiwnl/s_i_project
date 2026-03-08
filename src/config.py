import random
import numpy as np

# -- Riproducibilita' --
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# -- Ambiente --
# Usa i metadati per la griglia, ma definiamo la costante di default
GRID_SIZE = 25 
EMPTY, WALL = 0, 1
WAREHOUSE = 2
ENTRANCE = 3
EXIT = 4
NUM_OBJECTS = 10
MAX_TICKS = 750

# -- Agenti --
NUM_AGENTS = 5
BATTERY_INITIAL = 500
ENERGY_MARGIN = 1.20 # Worker 3: +20% di sicurezza

# -- Sensori e Comunicazione --
VISION_RADIUS = 3 # Configurazione C1: cambia questo (1 vs 3)
COMM_RADIUS = 2
DEPLOY_RADIUS = 1

# -- Stigmergia --
CONGESTION_MALUS = 10
EVAPORATION_RATE = 0.05
STIGMA_ON = True # Configurazione C2: cambia questo (True vs False)

# -- Scout 1 --
STRESS_MAX = 15
STRESS_RANDOM_STEPS = 4

# -- Visualizzazione --
GUI = True # Imposta a False per le run statistiche veloci