from src.agents.base_agent import BaseAgent
from src.pathfinding import evaluate_utility

class Scout1(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.utility_weights = {'home': -0.1, 'explore': 1.0, 'object': 0.0}

    def decide_action(self, env, tick):
        # Se ha finito il suo compito, aspetta solo lo spegnimento della batteria
        if self.state in ['DEAD', 'FINISHED']: return
        
        self.check_battery(env)
        self._sync_with_neighbors(env, tick)
        self._scan_environment(env, tick)

        if self.stuck_ticks > 2:
            if self._dodge_step(env):
                return

        if self.state == 'RETURN_BASE':
            self._handle_return_base(env)
        else:
            self.state = 'EXPLORE'
            self._handle_explore(env)

    def _handle_explore(self, env):
        nr, nc = evaluate_utility(env, self.pos[0], self.pos[1], self.utility_weights)
        self._try_move(env, nr, nc)


class Scout2(Scout1):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.utility_weights = {'home': -0.1, 'explore': 0.5, 'object': 1.5}