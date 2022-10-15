from ipaddress import IPv4Address

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.Portscan import Portscan


class DiscoverNetworkServices(Action):
    """
    High Level Action that allows an agent to identify services on a host as a prerequisite for running an exploit.

    Calls the low level action PortScan then modifies the observation. Must be used on a host to
    successfully run the high level action ExploitRemoteServices.
    """
    def __init__(self, session: int, agent: str, ip_address: str):
        super().__init__()
        self.ip_address = ip_address
        self.agent = agent
        self.session = session

    def sim_execute(self, environment) -> Observation:
        # find session inside or close to the target subnet
        session = self.session
        # run portscan on the target ip address from the selected session
        sub_action = Portscan(session=self.session, agent=self.agent, ip_address=self.ip_address, target_session=session)
        obs = sub_action.sim_execute(environment)

        # FULLY OBS ASSUMPTION: Agent has full knowledge of ALL host to ip address mappings in target environment
        for host in obs.data['hosts']:
          if host == environment.ip_addresses[self.ip_address]:
            for proc in obs.data['hosts'][host]["Processes"]:
                for conn in proc['Connections']:
                    port = conn["local_port"]
                    environment.sessions[self.agent][self.session].addport(self.ip_address, port)
        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.ip_address}"
