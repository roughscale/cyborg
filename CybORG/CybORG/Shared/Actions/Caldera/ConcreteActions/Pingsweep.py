from ipaddress import IPv4Network

from CybORG.Shared import Observation
from CybORG.Shared.Actions.Caldera.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo_subnet, lo
from CybORG.Simulator.State import State


class Pingsweep(ConcreteAction):
    """
    Concrete action that simulates a pingsweep, returning a list of active ip addresses on a subnet.
    """
    def __init__(self, agent: str, subnet: IPv4Network):
        super().__init__(agent)
        self.subnet = subnet

    def sim_execute(self, state: State) -> Observation:
        self.state = state
        """
        Executes a pingsweep in the simulator.
        """
        obs = Observation()

        # Collect ip addresses
        if self.subnet == lo_subnet:
            # Loopback address triviality
            obs.set_success(True)
            obs.add_interface_info(hostid=str(lo_subnet), subnet=lo_subnet, ip_address=lo)
        else:
            # Check NACL rules allow subnet to be scanned and ICMP is not banned.
            available_ports = self.check_routable([state.subnets[i.subnet] for i in state.hosts[from_host].interfaces if i.subnet != lo_subnet], [state.subnets[self.subnet]])
            if 'ICMP' not in available_ports and 'all' not in available_ports:
                obs.set_success(False)
                return obs
            # Return ip addresses.
            target_hosts = []
            for host in state.subnets[self.subnet].ip_addresses:
                obs.set_success(True)
                target_hosts.append(state.ip_addresses[host])
                obs.add_interface_info(hostid=str(host), ip_address=host, subnet=self.subnet)

        return obs
