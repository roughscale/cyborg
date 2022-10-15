## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.
from ipaddress import IPv4Address
from typing import Optional

from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo, lo_subnet
from CybORG.Shared.Enums import SessionType, ProcessType, OperatingSystemType, DecoyType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Environment import Environment
from CybORG.Simulator.Process import Process


class SSHBruteForce(ExploitAction):
    def __init__(self, ip_address: IPv4Address, agent: str, session: int, target_session: int):
        super().__init__(session=session, agent=agent, ip_address=ip_address,
                target_session=target_session)
        self.ip_address = ip_address
        self.target_session = target_session

    def sim_execute(self, environment: Environment):
        self.environment = environment
        length_of_wordlist = 10
        obs = Observation()
        if self.session not in environment.sessions[self.agent]:
            obs.set_success(False)
            return obs
        from_host: Host = environment.hosts[environment.sessions['Red'][self.session].host]
        session = environment.sessions['Red'][self.session]

        if not session.active:
            obs.set_success(False)
            return obs

        # determine which ports can communicate between which subnets
        originating_ip_address = None
        if self.ip_address == lo:
            target_host: Host = from_host
            originating_ip_address = self.ip_address
        else:
            target_host: Host = environment.hosts[environment.ip_addresses[self.ip_address]]
            ports = self.check_routable(
                [environment.subnets[str(i.subnet)] for i in from_host.interfaces if i.ip_address != lo],
                [s for s in environment.subnets.values() if IPv4Address(self.ip_address) in s.cidr])
            if ports is None or (22 not in ports and 'all' not in ports):
                obs.set_success(False)
                return obs
            from_subnet, to_subnet = ports[22] if 22 in ports else ports['all']
            # calculate the originating ip address
            for i in from_host.interfaces:
                if i.ip_address != lo:
                    if i.subnet == from_subnet:
                        originating_ip_address = i.ip_address

        # find out if smb is open
        vuln_proc: Optional[Process] = None
        for proc in target_host.processes:
            if proc.process_type == ProcessType.SSH:
                for conn in proc.connections:
                    if 'local_port' in conn and conn['local_port'] == 22:
                        vuln_proc = proc
                        break
                if vuln_proc is not None:
                    break

        if vuln_proc is None:
            obs.set_success(False)
            return obs
        # FULLY OBS ASSUMPTION: Agent has full knowledge of ALL host to ip address mappings in target environment
        hostid = environment.ip_addresses[self.ip_address]
        obs.add_process(hostid=hostid, local_address=self.ip_address, local_port=22, status="open",
                        process_type='SSH')

        # test if there is a bruteforceable user-pass on the system
        user = None
        for u in target_host.users:
            if u.bruteforceable:
                user = u
                break

        for i in range(length_of_wordlist):
            target_host.events['NetworkConnections'].append({'remote_address': originating_ip_address,
                                                             'remote_port': from_host.get_ephemeral_port(),
                                                             'local_address': self.ip_address,
                                                             'local_port': 22
                                                             })

        if user is not None and not (vuln_proc.decoy_type & DecoyType.EXPLOIT):
            obs.set_success(True)

            new_proc = target_host.add_process(name="sshd", ppid=vuln_proc.pid, path=vuln_proc.path, user=user.username, process_type="ssh")

            if bool(vuln_proc.decoy_type & DecoyType.SANDBOXING_EXPLOIT):

                new_session = environment.add_session(host=target_host.hostname, agent=self.agent,
                                            user=user.username, session_type="ssh", parent=session, process=new_proc.pid,
                                            is_escalate_sandbox=True)
            else:

                new_session = environment.add_session(host=target_host.hostname, agent=self.agent,
                                            user=user.username, session_type="ssh", parent=session, process=new_proc.pid)

            remote_port = target_host.get_ephemeral_port()
            new_connection = {"local_port": 22,
                              "Application Protocol": "tcp",
                              "remote_address": originating_ip_address,
                              "remote_port": remote_port,
                              "local_address": self.ip_address}
            new_proc.connections.append(new_connection)
            target_host.events['NetworkConnections'].append({'remote_address': originating_ip_address,
                                                             'remote_port': remote_port,
                                                             'local_address': self.ip_address,
                                                             'local_port': 22
                                                             })

            remote_port_dict = {'local_port': remote_port,
                                "Application Protocol": "ssh",
                                "local_address": originating_ip_address,
                                "remote_address": self.ip_address,
                                "remote_port": 22
                                }
            from_host.get_process(session.pid).connections.append(remote_port_dict)
            # FULLY OBS ASSUMPTION: Agent has full knowledge of ALL host to ip address mappings in target environment
            origin_hostid = environment.ip_addresses[str(originating_ip_address)]
            hostid = environment.ip_addresses[self.ip_address]

            obs.add_process(hostid=origin_hostid, local_address=originating_ip_address, remote_address=self.ip_address,
                            local_port=remote_port, remote_port=22)
            obs.add_process(hostid=hostid, local_address=self.ip_address, remote_address=originating_ip_address,
                            local_port=22, remote_port=remote_port, process_type='ssh')
            obs.add_session_info(hostid=hostid, username=user.username, session_id=new_session.ident, session_type="ssh", agent=self.agent)
            obs.add_user_info(hostid=hostid, username=user.username, password=user.password, uid=user.uid)

            obs.add_system_info(hostid=hostid, hostname=target_host.hostname, os_type=target_host.os_type)
            # for multi-homed hosts, also return the details of the other interfaces
            # Q whether this should be a separate action.  However this info will be
            # automatically retrieved in C2 frameworks upon sucessful installation of
            # C2 agent.
            target_interface = target_host.get_interface(ip_address=self.ip_address)
            for interface in target_host.interfaces:
                  if interface.ip_address != lo and interface.ip_address != target_interface.ip_address:
                       obs.add_interface_info(hostid=hostid,ip_address=interface.ip_address, subnet=interface.subnet)
        else:
            obs.set_success(False)
        return obs
