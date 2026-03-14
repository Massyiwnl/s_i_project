from src.agents.base_agent import BaseAgent
from src.pathfinding import evaluate_utility
from src.config import STRESS_MAX


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

        # FIX: usa STRESS_MAX // 5 (=3) da config invece del valore 2 hardcoded
        if self.stuck_ticks > STRESS_MAX // 5:
            if self._dodge_step(env):
                return

        if self.state == 'RETURN_BASE':
            self._handle_return_base(env)
        else:
            self.state = 'EXPLORE'
            self._handle_explore(env)

    def _handle_explore(self, env):
        result = evaluate_utility(env, self.pos[0], self.pos[1], self.utility_weights)
        if result:
            nr, nc = result
            self._try_move(env, nr, nc)


class Scout2(Scout1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        # Peso piu' alto per object: si orienta verso zone con tracce di oggetti
        self.utility_weights = {'home': -0.1, 'explore': 0.5, 'object': 1.5}