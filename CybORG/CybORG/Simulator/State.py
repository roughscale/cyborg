## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.
import copy
from datetime import datetime, timedelta
from ipaddress import IPv4Network, IPv4Address
from math import log2
from random import sample, choice

from CybORG.Shared import Scenario
from CybORG.Shared.Enums import SessionType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.Session import Session
from CybORG.Simulator.Subnet import Subnet
from CybORG.Simulator.TrueState import TrueState


class State:
    """Simulates the Network State.

    This class contains all the data for the simulated network, including ips, subnets, hosts and sessions.
    The methods mostly modify the network state, but tend to delegate most of the work to the Host class.
    """
    def __init__(self, scenario):
        self.scenario = scenario
        self.subnet_name_to_cidr = None  # contains mapping of subnet names to subnet cidrs
        self.ip_addresses = None  # contains mapping of ip addresses to hostnames

        self.hosts = None  # contains mapping of hostnames to host objects
        self.sessions = None  # contains mapping of agent names to mapping of session id to session objects
        self.subnets = None  # contains mapping of subnet cidrs to subnet objects

        self.sessions_count = {}  # contains a mapping of agent name to number of sessions
        self.hostname_to_interface = {} # contains a mapping of hostname interfaces to ip addresses

        self._initialise_state(scenario)
        self.step = 0
        self.original_time = datetime(2020, 1, 1, 0, 0)
        self.time = copy.deepcopy(self.original_time)

        self.external_hosts = [ "Attacker0" ] # list of hostnames that are external of the system

    def get_true_state(self, info: dict) -> TrueState:
        true_obs = TrueState()
        if info is None:
            raise ValueError('None is not a valid argument for the get true state function in the State class')
        elif info == {}:
            raise ValueError('Empty info is not a valid argument for the get true state function in the State class')
        else:
            if 'network' in info and 'subnets' in info['network']:
                for name, cidr in self.subnets.items():
                    # cidr of type Subnet. need to use str representation
                    if str(cidr) in info['network']['subnets']:
                        true_obs.add_subnet(cidr=str(cidr))
            for hostname, host in self.hosts.items():
                if hostname in info['hosts']:
                    if 'Processes' in info['hosts'][hostname] and hostname not in self.external_hosts:
                        for process in host.processes:
                            obs = process.get_state()
                            for o in obs:
                                true_obs.add_process(hostid=hostname, **o)
                    if 'Interfaces' in info['hosts'][hostname] and hostname not in self.external_hosts:
                        if info['hosts'][hostname]['Interfaces'] == 'All':
                            for interface in host.interfaces:
                                true_obs.add_interface_info(hostid=hostname, **interface.get_state())
                        elif info['hosts'][hostname]['Interfaces'] == 'IP Address':
                            for interface in host.interfaces:
                                if interface.name != 'lo':
                                    true_obs.add_interface_info(hostid=hostname, ip_address=interface.ip_address)
                        else:
                            raise NotImplementedError(f"{info[hostname]['Interfaces']} cannot be collected from state")
                    if 'Sessions' in info['hosts'][hostname]: # need to set up starting session on external/learning agent host
                        if info['hosts'][hostname]['Sessions'] == 'All':
                            for agent_name, sessions in host.sessions.items():
                                for session in sessions:
                                    true_obs.add_session_info(hostid=hostname,
                                                              **self.sessions[agent_name][session].get_state())
                        else:
                            agent_name = info['hosts'][hostname]['Sessions']
                            if agent_name in host.sessions:
                                for session in host.sessions[agent_name]:
                                    true_obs.add_session_info(hostid=hostname,
                                                              **self.sessions[agent_name][session].get_state())
                    if 'Files' in info['hosts'][hostname] and hostname not in self.external_hosts:
                        for file in host.files:
                            true_obs.add_file_info(hostid=hostname, **file.get_state())
                    if 'UserInfo' in info['hosts'][hostname] and hostname not in self.external_hosts:
                        for user in host.users:
                            obs = user.get_state()
                            for o in obs:
                                true_obs.add_user_info(hostid=hostname, **o)
                    if 'SystemInfo' in info['hosts'][hostname]:
                        true_obs.add_system_info(hostid=hostname, **host.get_state())
                    if 'Services' in info['hosts'][hostname] and hostname not in self.external_hosts:
                        if 'All' in info['hosts'][hostname]['Services']:
                            for service, service_info in host.services.items():
                                true_obs.add_process(hostid=hostname, service_name=service, pid=service_info['process'])
                        else:
                            for service_name in info['hosts'][hostname]['Services']:
                                if service_name in host.services:
                                    true_obs.add_process(hostid=hostname, service_name=service_name, pid=host.services[service_name]['process'])
        # how do we add dynamic information (ie processes to be discovered, ephemeral ports, etc)
        return true_obs

    def reset(self):
        # only reset state (don't re-initialise with randomisation)
        only_reset_state=True
        print("State reset: CIDR randomness disabled {}".format(only_reset_state))
        self._initialise_state(self.scenario, reset=only_reset_state)
        self.step = 0
        self.time = copy.deepcopy(self.original_time)

    def _initialise_state(self, scenario: Scenario, reset=False):
        # reset parameter resets the environment without changing the network state configuration
        # ie the network state will retain existing configuration (ip and subnet addressing)
        # otherwise, the network state will be created with address randomisation
        # We should remove this once we have convering algorithms
        if not reset:
          self.subnet_name_to_cidr = {}  # contains mapping of subnet names to subnet cidrs
          self.ip_addresses = {}  # contains mapping of ip addresses to hostnames

          self.hosts = {}  # contains mapping of hostnames to host objects
          self.sessions = {}  # contains mapping of agent names to mapping of session id to session objects
          self.subnets = {}  # contains mapping of subnet cidrs to subnet objects. dict keys of type IPv4Network

          self.sessions_count = {}  # contains a mapping of agent name to number of sessions
          self.hostname_to_interface = {}

          count = 0
          # randomly generate subnets cidrs for all subnets in scenario and IP addresses for all hosts in those subnets and create Subnet objects
          # using fixed size subnets (VLSM maybe viable alternative if required)
          maximum_subnet_size = max([scenario.get_subnet_size(i) for i in scenario.subnets])
          subnets_cidrs = sample(
            list(IPv4Network("10.0.0.0/16").subnets(new_prefix=32 - max(int(log2(maximum_subnet_size + 5)), 4))),
            len(scenario.subnets))
          for subnet_name in scenario.subnets:
            subnet_cidr = choice(list(subnets_cidrs[count].subnets(
                new_prefix=32 - max(int(log2(scenario.get_subnet_size(subnet_name) + 5)), 4))))
            count += 1
            self.subnet_name_to_cidr[subnet_name] = subnet_cidr
            ip_address_selection = sample(list(subnet_cidr.hosts()), len(scenario.get_subnet_hosts(subnet_name)))
            allocated = 0
            for hostname in scenario.get_subnet_hosts(subnet_name):
                self.ip_addresses[ip_address_selection[allocated]] = hostname
                interface = {"ip_address": ip_address_selection[allocated], "subnet": subnet_cidr}
                if hostname in self.hostname_to_interface:
                    self.hostname_to_interface[hostname].append(interface)
                else:
                    self.hostname_to_interface[hostname] = [interface]
                allocated += 1
            # subnet_cidr is of type IPv4Network.  Do we need to use string representation for dict keys?
            #print("_initialise state")
            #print(subnet_cidr)
            #print(type(subnet_cidr))
            self.subnets[subnet_cidr] = Subnet(cidr=subnet_cidr, ip_addresses=ip_address_selection,
                                               nacls=scenario.get_subnet_nacls(subnet_name), name=subnet_name)

        # create host objects for all host names in the scenario
        for hostname in scenario.hosts:
            host_info = scenario.get_host(hostname)
            self.hosts[hostname] = Host(system_info=host_info['SystemInfo'], processes=host_info['Processes'],
                                        users=host_info['UserInfo'], interfaces=self.hostname_to_interface[hostname],
                                        hostname=hostname, info=host_info.get('info'), services=host_info.get('Services'))

        for agent in scenario.agents:
            agent_info = scenario.get_agent_info(agent)
            self.sessions[agent] = {}
            self.sessions_count[agent] = 0
            # instantiate parentless sessions first
            for starting_session in agent_info.starting_sessions:
                if starting_session.parent is None:
                    self.sessions[agent][len(self.sessions[agent])] = self.hosts[starting_session.hostname].add_session(
                        username=starting_session.username,
                        agent=agent,
                        parent=None,
                        pid=starting_session.pid,
                        session_type=starting_session.session_type,
                        ident=self.sessions_count[agent],
                        name=starting_session.name,
                        artifacts=starting_session.event_artifacts)
                    self.sessions_count[agent] += 1
            for starting_session in agent_info.starting_sessions:
                if starting_session.parent is not None:
                    if starting_session.parent in [i.name for i in self.sessions[agent].values()]:
                        parent = self.sessions[agent][
                            {i.name: id for id, i in self.sessions[agent].items()}[starting_session.parent]]
                    else:
                        raise ValueError(
                            f"Parent session: {starting_session.parent} of session: {starting_session} not in agent's session list")
                    self.sessions[agent][len(self.sessions[agent])] = self.hosts[starting_session.hostname].add_session(
                        username=starting_session.username,
                        agent=agent,
                        session_type=starting_session.session_type,
                        ident=self.sessions_count[agent],
                        parent=parent,
                        name=starting_session.name,
                        artifacts=starting_session.event_artifacts)
                    self.sessions_count[agent] += 1

            for host in self.hosts.values():
                host.create_backup()

    # mandated process being supplied to function
    def add_session(self, host: str, user: str, agent: str, parent: int, process: int, session_type: str = "shell",
            timeout: int = 0, is_escalate_sandbox: bool = False, active: bool = True) -> Session:
        """Adds a session of a selected type to a dict as a selected user"""
        # Add idempotency (Don't create a session if the same already exists)
        # this gets the list of sessions from the simulated environment (total sessions within env)
        existing_sessions = self.sessions
        print("add_session: existing sessions")
        for idx, sess in existing_sessions[agent].items():
            # session similarity will depend (at the moment) upon user, host, session_type, active
            print(host,user,SessionType.parse_string(session_type),active)
            print(sess.host,sess.username,sess.session_type,sess.active)
            #print(type(SessionType.parse_string(session_type)))
            #print(type(sess.session_type))
            if user == sess.username and SessionType.parse_string(session_type) == sess.session_type and host == sess.host and active == sess.active:
               # if we mandate process (pid) being added at session creation we could limit the similarity to pid matching!
               # don't match according to pid, especially if pids are common across hosts
               #if process == sess.pid:
               print("re-using matching host,user,type session")
               return sess

        # need to reuse inactive session idents
        ident=None
        for i in range(self.sessions_count[agent]):
            if i not in self.sessions[agent].keys():
                ident = i
        
        if ident is None:
           ident = self.sessions_count[agent]
           self.sessions_count[agent] += 1
           
        if parent in self.sessions[agent]:
            parent = self.sessions[agent][parent]
        new_session = self.hosts[host].add_session(username=user, ident=ident, timeout=timeout, pid=process,
                                                   session_type=session_type, agent=agent, parent=parent,
                                                   is_escalate_sandbox=is_escalate_sandbox)
        self.sessions[agent][ident] = new_session
        return new_session

    def add_file(self, host: str, name: str, path: str, user: str = None, user_permissions: str = None,
                 group: str = None, group_permissions: int = None, default_permissions: int = None):
        host = self.hosts[host]
        return host.add_file(name, path, user, user_permissions, group, group_permissions, default_permissions)

    def add_user(self, host: str = None, username: str = None, password: str = None, password_hash_type: str = None):
        host = self.hosts[host]
        return host.add_user(username=username, password=password, password_hash_type=password_hash_type)

    def remove_process(self, hostname: str, pid: int):
        host = self.hosts[hostname]
        process = host.get_process(pid)
        if process is not None:
            agent, session = self.get_session_from_pid(hostname=hostname, pid=pid)
            host.processes.remove(process)
            if process.pid in [i['process'] for i in host.services.values() if i['active']]:
                process.pid = None
                host.add_process(**process.__dict__)
                service = True
            else:
                service = False
            if session is not None:
                host.sessions[agent].remove(session)
                session = self.sessions[agent].pop(session)
                if service:
                    session_reloaded = self.add_session(host=host.hostname, user=session.user,
                                                        session_type=session.session_type, agent=session.agent,
                                                        parent=session.parent, timeout=session.timeout)

    def get_session_from_pid(self, hostname, pid):
        for agent, sessions in self.sessions.items():
            for session in sessions:
                if self.sessions[agent][session].pid == pid and self.sessions[agent][session].host == hostname:
                    return agent, session
        return None, None

    def get_sessions_by_host(self, agent, hostname):
        # returns a list of Session objects for the specified host
        if agent not in self.sessions:
            return None
        host_sessions = []
        for session in self.sessions[agent]:
            if self.sessions[agent][session].host == hostname:
                host_sessions.append(self.sessions[agent][session])
        return host_sessions

    def reboot_host(self, hostname):
        host = self.hosts[hostname]
        for agent, sessions in host.sessions.items():
            for session in sessions:
                self.sessions[agent].pop(session)
                for other_session in self.sessions[agent].values():
                    if other_session.session_type == SessionType.MSF_SERVER and session in other_session.routes:
                        other_session.routes.pop(session)
        host.sessions = {}
        host.processes = []
        for file in host.files:
            if file.path == "/tmp/":
                host.files.remove(file)

        # start back up
        for process in host.default_process_info:
            process["user"] = host.get_user(process.get("Username"))
            host.processes.append(
                Process(pid=process.get('PID'), parent_pid=process.get('PPID'), username=process.get('user'),
                        process_name=process.get('ProcessName'), path=process.get('Path'),
                        open_ports=process.get('Connections')))

        for servicename, service in host.services.items():
            if service['active']:
                self.start_service(hostname, servicename)

    def stop_service(self, hostname: str, service_name: str):
        # stops a service, its process, and associated sessions
        process = self.hosts[hostname].stop_service(service_name)
        self.remove_process(hostname, process)

    def start_service(self, hostname: str, service_name: str):
        # stops a service, its process, and associated sessions
        process, session = self.hosts[hostname].start_service(service_name)
        if session is not None:
            self.add_session(host=hostname, process=process, user=session.user, session_type=session.session_type,
                             agent=session.agent, parent=session.parent, timeout=session.timeout)

    def get_subnet_containing_ip_address(self, ip_address: IPv4Address) -> Subnet:
        for subnet in self.subnets.values():
            if subnet.contains_ip_address(ip_address):
                return subnet
        raise ValueError(f"No Subnet contains the ip address {ip_address}")

    def get_dict(self):
        removed_keys=['scenario','time','original_time']
        tmp = copy.deepcopy(self.__dict__)
        output = { k: v for k,v in tmp.items() if k not in removed_keys }
        for name,obj in output['hosts'].items():
            output["hosts"][name] = obj.get_dict()
        return output
