from ipaddress import IPv4Network

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.Caldera.ConcreteActions.Pingsweep import Pingsweep


class DiscoverRemoteSystems(Action):
    """
    High level action that discovers active ip addresses on a subnet.

    Calls the low level action Pingsweep.
    """
    def __init__(self, agent: str, subnet: IPv4Network):
        super().__init__()
        self.subnet = subnet
        self.agent = agent

    def sim_execute(self, state) -> Observation:
        # run pingsweep on the target subnet from selected session
        sub_action = Pingsweep(agent=self.agent, subnet=self.subnet)
        obs = sub_action.sim_execute(state)
        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.subnet}"
