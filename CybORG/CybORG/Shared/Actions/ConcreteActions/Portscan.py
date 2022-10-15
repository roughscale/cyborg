from ipaddress import IPv4Address, IPv4Network

from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Environment import Environment


class Portscan(ConcreteAction):
    def __init__(self, session: int, agent: str, ip_address: str, target_session: int):
        super().__init__(session, agent)
        self.ip_address = ip_address
        self.target_session = target_session

    def sim_execute(self, environment: Environment) -> Observation:
        self.environment = environment
        obs = Observation()
        if self.session not in environment.sessions[self.agent]:
            obs.set_success(False)
            return obs
        from_host = environment.sessions['Red'][self.session].host
        session = environment.sessions['Red'][self.session]

        if not session.active:
            obs.set_success(False)
            return obs
        if self.ip_address == str(lo):
            target_host: Host = environment.hosts[from_host]
            ports = ['all']
        else:
            target_host: Host = environment.hosts[environment.ip_addresses[str(self.ip_address)]]
            ports = self.check_routable([environment.subnets[str(i.subnet)] for i in environment.hosts[from_host].interfaces if i.ip_address != lo], [s for s in environment.subnets.values() if IPv4Address(self.ip_address) in IPv4Network(s.cidr)])
            print("PortScan ports: {0}".format(ports))

        if ports is None or ports == []:
            obs.set_success(False)
            return obs

        obs.set_success(True)

        for process in target_host.processes:
            for conn in process.connections:
                if 'local_port' in conn and (conn['local_port'] in ports or 'all' in ports) and 'remote_port' not in conn:
                    from_subnet, to_subnet = ports[conn['local_port']] if conn['local_port'] in ports else ports['all']
                    # calculate the originating ip address
                    for i in environment.hosts[from_host].interfaces:
                        if i.ip_address != lo:
                            if i.subnet == from_subnet:
                                originating_ip_address = i.ip_address
                    # internal so avoids nacls
                    # FULLY OBS ASSUMPTION: Agent has full knowledge of ALL host to ip address mappings in target environment
                    hostid = environment.ip_addresses[self.ip_address]
                    obs.add_process(hostid=hostid, local_port=conn["local_port"], local_address=self.ip_address)
                    target_host.events['NetworkConnections'].append({'local_address': self.ip_address,
                                                                     'local_port': conn["local_port"],
                                                                     'remote_address': originating_ip_address,
                                                                     'remote_port': target_host.get_ephemeral_port()})
        return obs
