from src.agents.base_agent import BaseAgent
from src.decision_making import evaluate_utility
from src.sensors import get_visible_objects
from src.config import STRESS_MAX, VISION_RADIUS, STIGMA_ON


class Scout1(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.utility_weights = {'home': -0.1, 'explore': 1.0, 'object': 0.0}

    def decide_action(self, env, tick):
        if self.state in ['DEAD', 'FINISHED']:
            return

        self.check_battery(env)
        self._sync_with_neighbors(env, tick)
        self._scan_environment(env, tick)

        if self.stuck_ticks > STRESS_MAX // 5:
            if self._dodge_step(env):
                return

        if self.state == 'RETURN_BASE':
            self._handle_return_base(env)
        else:
            self.state = 'EXPLORE'
            self._handle_explore(env)

    def _scan_environment(self, env, tick):
        """
        Override di BaseAgent._scan_environment.

        Aggiunge il deposito stigmergico di pheromone_object sulle celle
        degli oggetti visibili, esclusivamente per gli agenti Scout.

        Ruolo dello Scout nel sistema di feromoni:
          - pheromone_explore: depositato camminando (ereditato da BaseAgent)
          - pheromone_object:  depositato sulla cella esatta dell'oggetto scoperto

        I Worker non depositano mai pheromone_object. Questo garantisce che il
        segnale abbia un unico significato non ambiguo: "qui c'e' un oggetto
        non ancora raccolto, segnalato da uno Scout". I Worker in fase EXPLORE
        seguono questo segnale (peso 'object' nella funzione di utilita') per
        convergere verso le zone con oggetti reali, senza il paradosso ACO
        della versione precedente dove la scia puntava verso il magazzino
        invece che verso la sorgente.

        Valore di deposito (8.0) calibrato deliberatamente piu' basso rispetto
        al vecchio deposito durante il ritorno (20.0) per due ragioni:
          1. La scoperta avviene una sola volta per oggetto, mentre il vecchio
             deposito si accumulava per tutti i passi del percorso di ritorno.
          2. Un valore basso permette una evaporazione rapida post-raccolta,
             riducendo il rischio di phantom attraction (Worker attratti verso
             celle vuote dove l'oggetto e' stato gia' raccolto).
        """
        # Fase 1 + Fase 2: comportamento base (FOUND e EMPTY nella local_map)
        super()._scan_environment(env, tick)

        # Fase 3 (solo Scout): deposito pheromone_object sugli oggetti visibili
        if not STIGMA_ON:
            return  # rispetta il flag globale della Configurazione C2

        visible_objs = get_visible_objects(env, self.pos[0], self.pos[1], VISION_RADIUS)
        for obj in visible_objs:
            # deposita solo se l'oggetto e' ancora fisicamente presente nell'ambiente
            # (non gia' raccolto da un altro agente in questo tick)
            if env.is_object_at(obj[0], obj[1]):
                env.pheromone_object[obj[0]][obj[1]] += 8.0
                env.active_pheromone_cells.add(obj)

    def _handle_explore(self, env):
        result = evaluate_utility(env, self.pos[0], self.pos[1], self.utility_weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)


class Scout2(Scout1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        # Peso object piu' alto: una volta che ha depositato feromone sugli oggetti,
        # tende a tornare verso zone con alta concentrazione di pheromone_object,
        # rinforzando il segnale sugli oggetti non ancora raccolti.
        self.utility_weights = {'home': -0.1, 'explore': 0.5, 'object': 0.0}