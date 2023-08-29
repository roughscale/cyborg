from ipaddress import IPv4Network

from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo_subnet, lo
from CybORG.Simulator.Environment import Environment


class Pingsweep(ConcreteAction):
    """
    Concrete action that simulates a pingsweep, returning a list of active ip addresses on a subnet.
    """
    def __init__(self, session: int,agent: str,target_session: int, subnet: IPv4Network):
        super().__init__(session,agent)
        self.target_session = target_session
        self.subnet = subnet

    def sim_execute(self, environment: Environment) -> Observation:
        self.environment = environment
        """
        Executes a pingsweep in the simulator.
        """
        obs = Observation()

        #print("Subnet: {0}".format(self.subnet))
        #print("session: {0}".format(self.session))
        #print("target_session: {0}".format(self.target_session))
        # Check the session running the code exists and is active.
        if self.session not in environment.sessions[self.agent]:
            obs.set_success(False)
            return obs
        from_host = environment.sessions[self.agent][self.session].host
        #print("from_host: {0}".format(from_host))
        session = environment.sessions[self.agent][self.session]
        #print("session active: {0}".format(session.active))
        if not session.active:
            obs.set_success(False)
            return obs

        # Check the target session exists and is active.
        if self.target_session in environment.sessions[self.agent]:
            target_session = environment.sessions[self.agent][self.target_session]
            #print("target session active: {0}".format(target_session.active))
        else:
            obs.set_success(False)
            return obs
        if not target_session.active:
            obs.set_success(False)
            return obs

        # Collect ip addresses
        if self.subnet == lo_subnet:
            # Loopback address triviality
            obs.set_success(True)
            obs.add_interface_info(hostid=str(lo_subnet), subnet=lo_subnet, ip_address=lo)
        else:
            # Check NACL rules allow subnet to be scanned and ICMP is not banned.
            available_ports = self.check_routable([environment.subnets[str(i.subnet)] for i in environment.hosts[from_host].interfaces if i.subnet != lo_subnet], [environment.subnets[str(self.subnet)]])
            if 'ICMP' not in available_ports and 'all' not in available_ports:
                obs.set_success(False)
                return obs
            # Return ip addresses.
            target_hosts = []
            for host in environment.subnets[str(self.subnet)].ip_addresses:
                obs.set_success(True)
                target_hosts.append(environment.ip_addresses[str(host)])
                # FULLY OBS ASSUMPTION: that agent has full knowledge of ALL host to ip address mappings within the target environment
                # do reverse ip lookup
                hostid = environment.ip_addresses[str(host)]
                obs.add_interface_info(hostid=hostid, ip_address=host, subnet=self.subnet)

        return obs
