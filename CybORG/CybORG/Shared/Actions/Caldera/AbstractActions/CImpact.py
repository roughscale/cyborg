from random import choice

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.Caldera.ConcreteActions.StopService import StopService
from CybORG.Simulator.State import State


class Impact(Action):
    def __init__(self, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.hostname = hostname

    def sim_execute(self, state: State) -> Observation:
        if True:
            sub_action = StopService(agent=self.agent, service=ot_service)
            obs = sub_action.sim_execute(state)
        else:
            obs = Observation(success=False)

        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
