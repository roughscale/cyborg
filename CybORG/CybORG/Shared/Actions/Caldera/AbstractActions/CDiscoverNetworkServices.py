from ipaddress import IPv4Address

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.Caldera.ConcreteActions.Portscan import Portscan


class DiscoverNetworkServices(Action):
    """
    High Level Action that allows an agent to identify services on a host as a prerequisite for running an exploit.

    Calls the low level action PortScan then modifies the observation. Must be used on a host to
    successfully run the high level action ExploitRemoteServices.
    """
    def __init__(self, agent: str, ip_address: IPv4Address):
        super().__init__()
        self.ip_address = ip_address
        self.agent = agent

    def sim_execute(self, state) -> Observation:
        # run portscan on the target ip address from the selected session
        sub_action = Portscan(agent=self.agent, ip_address=self.ip_address)
        obs = sub_action.sim_execute(state)
        if str(self.ip_address) in obs.data:
            for proc in obs.data[str(self.ip_address)]["Processes"]:
                for conn in proc['Connections']:
                    port = conn["local_port"]
        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.ip_address}"
