"""Observability History Wrapper for CybORG.

This wrapper provides a history of Observations to provide a full observability belief state (MDP) i
by accumulating partial observations over time into a complete state representation. 
It replaces the built-in AgentState functionality with a standalone Gym-compatible wrapper.

The wrapper maintains a running history of observations for each tracked agent and
exposes the accumulated state via the Results.state attribute.

Example:
    >>> from CybORG import CybORG
    >>> from CybORG.Agents.Wrappers import ObsHistoryWrapper
    >>>
    >>> cyborg = CybORG(scenario_path, 'sim')
    >>> wrapped = ObsHistoryWrapper(cyborg, agents=['Red'])
    >>>
    >>> result = wrapped.reset(agent='Red')
    >>> # result.state contains accumulated state
    >>> result = wrapped.step(agent='Red', action=action)
    >>> # result.state contains updated accumulated state
"""

import copy
from ipaddress import IPv4Network, IPv4Address
from typing import List, Union, Optional

import CybORG.Shared.Enums as CyEnums
from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Results import Results


class AccumulatedState:
    """Internal class for accumulating observations into a full state.

    This class maintains a running history of partial observations, intelligently
    merging them to provide a complete view of the environment. It uses composition
    instead of inheritance to remain independent of the Observation class.

    Attributes:
        data (dict): The accumulated state data with 'network', 'hosts', and 'success' keys
        num_subnets (int): Maximum number of subnets observed
        num_hosts (int): Maximum number of hosts observed
        num_processes (int): Maximum processes per host
        num_sessions (int): Maximum sessions per host
        num_connections (int): Maximum connections per process
        num_interfaces (int): Maximum interfaces per host
    """

    def __init__(self, success: bool = None):
        """Initialize an empty accumulated state.

        Args:
            success: Initial success value (default: UNKNOWN)
        """
        self.data = {
            "network": {},
            "hosts": {},
            "success": CyEnums.TrinaryEnum.UNKNOWN if success is None else CyEnums.TrinaryEnum.parse_bool(success)
        }
        self.raw = ''

        # Track maximum element counts for fixed-size observation spaces
        self.num_subnets = 0
        self.num_hosts = 0
        self.num_processes = 0
        self.num_sessions = 0
        self.num_connections = 0
        self.num_interfaces = 0

    def initialise_state(self, scenario):
        """Initialize state with all scenario hosts for consistent observation space.

        Args:
            scenario: The CybORG scenario object containing host definitions
        """
        for hostname in scenario.hosts:
            self.data["hosts"][hostname] = {}

        self.calculate_max_elements()

    def calculate_max_elements(self):
        """Calculate maximum number of each element type for fixed observation spaces."""
        self.num_subnets = len(self.data["network"])
        self.num_hosts = len(self.data["hosts"])
        num_processes = 0
        num_sessions = 0
        num_connections = 0
        num_interfaces = 0

        for host in self.data["hosts"]:
            num_host_processes = 0
            num_host_sessions = 0
            num_proc_connections = 0
            num_host_interfaces = 0

            if "Processes" in self.data["hosts"][host]:
                num_host_processes += len(self.data["hosts"][host]["Processes"])
                for proc in self.data["hosts"][host]["Processes"]:
                    if "Connections" in proc:
                        num_proc_connections = max(num_proc_connections, len(proc["Connections"]))
                if num_proc_connections > num_connections:
                    num_connections = num_proc_connections
                if num_host_processes > num_processes:
                    num_processes = num_host_processes

            if "Sessions" in self.data["hosts"][host]:
                num_host_sessions += len(self.data["hosts"][host]["Sessions"])
                if num_host_sessions > num_sessions:
                    num_sessions = num_host_sessions

            if "Interface" in self.data["hosts"][host]:
                num_host_interfaces += len(self.data["hosts"][host]["Interface"])
                if num_host_interfaces > num_interfaces:
                    num_interfaces = num_host_interfaces

        if num_processes > self.num_processes:
            self.num_processes = num_processes

        if num_sessions > self.num_sessions:
            self.num_sessions = num_sessions

        if num_connections > self.num_connections:
            self.num_connections = num_connections

        if num_interfaces > self.num_interfaces:
            self.num_interfaces = num_interfaces

    def get_max_elements(self):
        """Get maximum element counts.

        Returns:
            dict: Maximum counts for subnets, hosts, processes, sessions, connections, interfaces
        """
        max_elements = {}
        max_elements["subnets"] = self.num_subnets
        max_elements["hosts"] = self.num_hosts
        max_elements["processes"] = self.num_processes
        max_elements["sessions"] = self.num_sessions
        max_elements["connections"] = self.num_connections
        max_elements["interfaces"] = self.num_interfaces
        return max_elements

    def update(self, observation: Observation, agent="Red"):
        """Update the accumulated state with a new observation.

        Args:
            observation: New observation to merge into state
            agent: Agent name for session tracking (default: "Red")
        """
        # Convert Observation to dict if necessary
        if isinstance(observation, Observation):
            obs = copy.deepcopy(observation.data)
        else:
            obs = copy.deepcopy(observation)

        # Merge observations for each host
        for key, info in obs.get("hosts", {}).items():
            if "Processes" in info:
                for process in info["Processes"]:
                    self.merge_process(hostid=key, agent=agent, **process)

            # Processes need to be updated before Sessions
            if "Sessions" in info:
                for session_info in info["Sessions"]:
                    self.merge_session_info(hostid=key, agent=agent, **session_info)

            if "UserInfo" in info:
                for user in info["UserInfo"]:
                    self.merge_user_info(hostid=key, agent=agent, **user)

            if "Files" in info:
                for file_info in info["Files"]:
                    self.merge_file_info(hostid=key, agent=agent, **file_info)

            if "Interface" in info:
                for interface in info["Interface"]:
                    self.merge_interface_info(hostid=key, agent=agent, **interface)

            if "SystemInfo" in info:
                self.merge_system_info(hostid=key, agent=agent, **info["SystemInfo"])

        if 'subnets' in obs.get('network', {}):
            for subnet in obs['network']['subnets']:
                self.add_subnet(subnet)

        if 'success' in obs:
            self.set_success(obs["success"])

    def get_state(self):
        """Get a deep copy of the accumulated state.

        Returns:
            dict: Deep copy of the accumulated state data
        """
        return copy.deepcopy(self.data)

    # ========== Merge Methods (from AgentState) ==========

    def merge_session_info(self, hostid, agent, **session_info):
        """Merge session info with complex deduplication logic."""
        if "Sessions" in self.data['hosts'][hostid]:
            host_sessions = {k: v for k, v in enumerate(self.data['hosts'][hostid]["Sessions"]) if v != {}}

            # Match on PID (excluding PID 0)
            pid_match = [i for i, s in host_sessions.items()
                        if ("PID" in s and s["PID"] != 0 and s["PID"] == session_info.get("PID"))]

            if len(pid_match) > 0:
                for i in pid_match:
                    # Check for privilege escalation
                    privesc = [p for p, s in host_sessions.items() if
                              s["Agent"] == session_info.get("Agent") and
                              s["Type"] == session_info.get("Type") and
                              s["Username"] != session_info.get("Username") and
                              s["PID"] != session_info.get("PID", None)]

                    if len(privesc) > 0 and session_info.get("Username") not in ('root', 'SYSTEM'):
                        self.data['hosts'][hostid]["Sessions"].pop(i)
                        return
                    else:
                        # Replace with updated session
                        self.data['hosts'][hostid]["Sessions"][i] = self.get_session_info(
                            hostid=hostid, agent=agent, **session_info)
                    return

            # Match on username, agent, and type
            match_sessions = [i for i, s in host_sessions.items() if
                            s["Agent"] == session_info.get("Agent") and
                            s["Type"] == session_info.get("Type") and
                            s["Username"] == session_info.get("Username")]

            if len(match_sessions) > 0:
                for i in match_sessions:
                    ignore = False
                    existing_session = self.data['hosts'][hostid]["Sessions"][i]

                    # Don't replace if routes are identical
                    if "routes" in existing_session and "routes" in session_info:
                        if len(existing_session["routes"]) == len(session_info["routes"]):
                            ignore = True

                    if not ignore:
                        self.data['hosts'][hostid]["Sessions"][i] = self.get_session_info(
                            hostid=hostid, agent=agent, **session_info)
                return

            # Handle inactive sessions
            if session_info.get("Active") == False:
                inactive_id = session_info.get("ID")
                for idx, s in enumerate(self.data['hosts'][hostid]["Sessions"]):
                    if s.get("ID") == inactive_id:
                        self.data['hosts'][hostid]["Sessions"].pop(idx)
                        break
                return

        # Add as new session
        self.add_session_info(hostid=hostid, agent=agent, **session_info)

    def merge_process(self, hostid, agent, **process):
        """Merge process info with PID-based matching and connection merging."""
        if "Processes" not in self.data['hosts'][hostid]:
            if "Connections" in process:
                for conn in process["Connections"]:
                    self.add_process(hostid=hostid, agent=agent, **process, **conn)
            else:
                self.add_process(hostid=hostid, agent=agent, **process)
            return

        for p_idx, existing_process in enumerate(self.data['hosts'][hostid]["Processes"]):
            # Match by PID
            if "PID" in process and "PID" in existing_process:
                proc_match = (process["PID"] == existing_process["PID"] and process["PID"] is not None)

                if proc_match:
                    # Merge connections
                    if "Connections" in process and "Connections" in existing_process:
                        merged_conn = copy.deepcopy(existing_process["Connections"])

                        for p in process["Connections"]:
                            match = False
                            for e_idx, e in enumerate(existing_process["Connections"]):
                                # Match same hosts
                                if (p.get("local_address") == e.get("local_address") and
                                    e.get("remote_address") is not None and
                                    p.get("remote_address") is not None and
                                    p["remote_address"] == e["remote_address"]):
                                    # Match on ports
                                    if (p.get("remote_port") == e.get("remote_port") or
                                        p.get("local_port") == e.get("local_port")):
                                        merged_conn[e_idx] = p
                                        match = True
                                        break

                            if not match:
                                merged_conn.append(p)

                        process["Connections"] = merged_conn

                    # Update process
                    self.data["hosts"][hostid]["Processes"][p_idx] = process
                    return

            # Match bare connections
            if "Connections" in process and "Connections" in existing_process:
                new_conn = process["Connections"]
                existing_conn = existing_process["Connections"]

                merged_conn = copy.deepcopy(existing_conn)

                for n in new_conn:
                    match = False
                    for e_idx, e in enumerate(existing_conn):
                        if e == {}:
                            continue

                        # Match on local address and port
                        if (n.get("local_address") == e.get("local_address") and
                            n.get("local_port") == e.get("local_port")):
                            if e.get("remote_address") is None:
                                merged_conn[e_idx] = n
                                match = True
                                break
                            elif n.get("remote_address") is None:
                                match = True
                                break
                            elif e["remote_address"] == n["remote_address"]:
                                merged_conn[e_idx] = n
                                match = True
                                break

                        # Match on remote address and port
                        elif ("remote_address" in n and "remote_address" in e and
                              n["remote_address"] == e["remote_address"] and
                              n.get("remote_port") == e.get("remote_port")):
                            if e.get("local_address") == n.get("local_address"):
                                merged_conn[e_idx] = n
                                match = True
                                break

                    if not match:
                        merged_conn.append(n)

                process["Connections"] = merged_conn
                return

        # Add as new process
        if 'Connections' in process:
            if len(process["Connections"]) == 0:
                return
            for conn in process['Connections']:
                self.add_process(hostid=hostid, agent=agent, **process, **conn)
                return

        self.add_process(hostid=hostid, agent=agent, **process)

    def merge_user_info(self, hostid, agent, **user):
        """Merge user info (currently just adds)."""
        self.add_user_info(hostid=hostid, agent=agent, **user)

    def merge_file_info(self, hostid, agent, **file_info):
        """Merge file info (currently just adds)."""
        self.add_file_info(hostid=hostid, agent=agent, **file_info)

    def merge_interface_info(self, hostid, agent, **interface):
        """Merge interface info with subset-based deduplication."""
        if "Interface" in self.data["hosts"][hostid]:
            for intf in self.data['hosts'][hostid]["Interface"]:
                # If new interface is subset of existing, don't add
                if interface == dict(set(interface.items()) & set(intf.items())):
                    return

        self.add_interface_info(hostid=hostid, agent=agent, **interface)

    def merge_system_info(self, hostid, agent, **info):
        """Merge system info (currently just adds)."""
        self.add_system_info(hostid=hostid, agent=agent, **info)

    # ========== Builder Methods (from Observation) ==========

    def get_session_info(self,
                        hostid: str = None,
                        username: str = None,
                        session_id: int = None,
                        agent: str = None,
                        timeout: int = None,
                        pid: int = None,
                        session_type: str = None,
                        active: bool = True,
                        routes: list = None,
                        **kwargs):
        """Build session info dict (used by merge_session_info)."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Sessions": []}
        elif "Sessions" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Sessions"] = []

        new_session = {}

        if username is None:
            username = kwargs.get("Username", None)
        if username is not None:
            new_session["Username"] = username
        else:
            raise ValueError("session has no username")

        if session_id is None:
            session_id = kwargs.get("ID", None)
        if session_id is not None:
            new_session["ID"] = session_id

        if timeout is None:
            timeout = kwargs.get("Timeout", None)
        if timeout is not None:
            new_session["Timeout"] = timeout

        if session_type is None:
            session_type = kwargs.get("Type", None)
        if session_type is not None:
            if type(session_type) is str:
                session_type = CyEnums.SessionType.parse_string(session_type)
            new_session["Type"] = session_type

        if session_type == CyEnums.SessionType.METERPRETER:
            if routes is None:
                routes = kwargs.get("Routes", [])
            new_session["Routes"] = routes

        if pid is not None:
            new_session["PID"] = pid
            # Update existing process if found
            if "Processes" in self.data["hosts"][hostid]:
                for p_idx, proc in enumerate(self.data["hosts"][hostid]["Processes"]):
                    if "PID" in proc and proc["PID"] == pid:
                        self.data["hosts"][hostid]["Processes"][p_idx].update({
                            "Username": username,
                            "Type": session_type
                        })
                        break
                else:
                    # Add process for session
                    self.add_process(hostid=hostid, pid=pid, username=username, type=session_type)

        if agent is None:
            agent = kwargs.get("Agent", None)
            if agent is None:
                raise ValueError('Agent must be specified when a session is added to an observation')
        if agent is not None:
            new_session["Agent"] = agent

        if active is None:
            active = kwargs.get("Active", True)
        if active is not None:
            new_session["Active"] = active

        return new_session

    def get_process(self,
                   hostid: str = None,
                   pid: int = None,
                   parent_pid: int = None,
                   process_name: str = None,
                   program_name: str = None,
                   service_name: str = None,
                   username: str = None,
                   path: str = None,
                   local_port: int = None,
                   remote_port: int = None,
                   local_address: Union[str, IPv4Address] = None,
                   remote_address: Union[str, IPv4Address] = None,
                   app_protocol: str = None,
                   transport_protocol: str = None,
                   status: str = None,
                   process_type: str = None,
                   process_version: str = None,
                   vulnerability: str = None,
                   properties: Optional[List[str]] = None,
                   **kwargs):
        """Build process info dict."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Processes": []}
        else:
            if "Processes" not in self.data['hosts'][hostid]:
                self.data['hosts'][hostid]["Processes"] = []

        new_process = {}

        pid = kwargs.get("PID", None) if pid is None else pid
        if pid is not None:
            if type(pid) is not int:
                pid = int(pid)
            if pid < 0:
                raise ValueError("PID must be non-negative")
            new_process["PID"] = pid

        if parent_pid is None:
            parent_pid = kwargs.get("PPID", None)
        if parent_pid is not None:
            if type(parent_pid) is not int:
                parent_pid = int(parent_pid)
            new_process["PPID"] = parent_pid

        if process_name is None:
            process_name = kwargs.get("ProcessName", None)
        if process_name is not None:
            new_process["ProcessName"] = process_name
            if isinstance(process_name, str):
                process_name = CyEnums.ProcessName.parse_string(process_name)

        if program_name is None:
            program_name = kwargs.get("Program Name", None)
        if program_name is not None:
            if type(program_name) is str:
                program_name = CyEnums.FileType.parse_string(program_name)
            new_process["Program Name"] = program_name

        if service_name is None:
            service_name = kwargs.get("Service Name", None)
        if service_name is not None:
            new_process["Service Name"] = service_name

        if username is None:
            username = kwargs.get("Username", None)
        if username is not None:
            new_process["Username"] = username

        if path is None:
            path = kwargs.get("Path", None)
        if path is not None:
            new_process["Path"] = path
            new_process["Known Path"] = CyEnums.Path.parse_string(path)

        new_connection = {}
        if "Connections" not in new_process:
            new_process["Connections"] = []

        if local_port is None:
            local_port = kwargs.get("local_port", None)
        if local_port is not None:
            new_connection["local_port"] = int(local_port)

        if remote_port is None:
            remote_port = kwargs.get("remote_port", None)
        if remote_port is not None:
            new_connection["remote_port"] = int(remote_port)

        if local_address is None:
            local_address = kwargs.get("local_address", None)
        if local_address is not None:
            if type(local_address) is str:
                local_address = IPv4Address(local_address)
            new_connection["local_address"] = local_address
            self.add_interface_info(hostid=hostid, ip_address=local_address)

        if remote_address is None:
            remote_address = kwargs.get("remote_address", None)
        if remote_address is not None:
            if type(remote_address) is str:
                remote_address = IPv4Address(remote_address)
            new_connection["remote_address"] = remote_address

        if transport_protocol is not None:
            if type(transport_protocol) is str:
                transport_protocol = CyEnums.TransportProtocol.parse_string(transport_protocol)
            new_connection["Transport Protocol"] = transport_protocol

        if app_protocol is None:
            app_protocol = kwargs.get("Application Protocol", None)
        if app_protocol is not None:
            if type(app_protocol) is str:
                app_protocol = CyEnums.AppProtocol.parse_string(app_protocol)
            new_connection["Application Protocol"] = app_protocol

        if status is None:
            status = kwargs.get("Status", None)
        if status is not None:
            if isinstance(status, str):
                status = CyEnums.ProcessState.parse_string(status)
            new_connection["Status"] = status

        if new_connection != {}:
            new_process["Connections"].append(new_connection)
        elif new_process["Connections"] == []:
            new_process.pop("Connections")

        if process_type is None:
            process_type = kwargs.get("ProcessType", None)
        if process_type is not None:
            if type(process_type) is str:
                process_type = CyEnums.ProcessType.parse_string(process_type)
            new_process["ProcessType"] = process_type

        if process_version is None:
            process_version = kwargs.get("ProcessVersion", None)
        if process_version is not None:
            if type(process_version) is str:
                process_version = CyEnums.ProcessVersion.parse_string(process_version)
            new_process["ProcessVersion"] = process_version

        if properties is None:
            properties = kwargs.get("Properties", None)
        if properties is not None:
            new_process["Properties"] = properties

        if vulnerability is None:
            vulnerability = kwargs.get("Vulnerability", None)
        if vulnerability is not None:
            if "Vulnerability" not in new_process:
                new_process["Vulnerability"] = []
            if type(vulnerability) is str:
                vulnerability = CyEnums.Vulnerability.parse_string(vulnerability)
            new_process["Vulnerability"].append(vulnerability)

        return new_process

    # ========== Add Methods (simplified from Observation) ==========

    def set_success(self, success: Union[bool, CyEnums.TrinaryEnum]):
        """Set success value."""
        if type(success) is bool:
            success = CyEnums.TrinaryEnum.parse_bool(success)
        self.data["success"] = success

    def add_subnet(self, cidr: str):
        """Add a subnet to the network."""
        if isinstance(cidr, str):
            cidr = IPv4Network(cidr)
        if 'subnets' not in self.data['network']:
            self.data['network']['subnets'] = []
        self.data['network']['subnets'].append(cidr)

    def add_process(self, hostid: str = None, agent: str = None, **kwargs):
        """Add a process to a host."""
        process = self.get_process(hostid=hostid, **kwargs)

        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Processes": []}
        elif "Processes" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Processes"] = []

        # Check for PID merge — mirrors AgentState.merge_process PID-match logic
        proc_merged = False
        for p_idx, proc in enumerate(self.data["hosts"][hostid]["Processes"]):
            if ("PID" in proc and "PID" in process and
                proc["PID"] == process["PID"] and proc["PID"] is not None):
                if "Connections" in process and "Connections" in proc:
                    merged_conn = copy.deepcopy(proc["Connections"])
                    for new_c in process["Connections"]:
                        match = False
                        for e_idx, e in enumerate(proc["Connections"]):
                            if new_c.get("local_address") == e.get("local_address") and \
                               e.get("remote_address") is not None and \
                               new_c.get("remote_address") is not None and \
                               new_c["remote_address"] == e["remote_address"]:
                                if new_c.get("remote_port") == e.get("remote_port") or \
                                   new_c.get("local_port") == e.get("local_port"):
                                    merged_conn[e_idx] = new_c
                                    match = True
                                    break
                        if not match:
                            merged_conn.append(new_c)
                    process["Connections"] = merged_conn
                self.data["hosts"][hostid]["Processes"][p_idx] = process
                proc_merged = True
                break

        if not proc_merged:
            self.data['hosts'][hostid]["Processes"].append(process)

        if self.data['hosts'][hostid] == {"Processes": [{}]}:
            self.data['hosts'].pop(hostid)

    def add_session_info(self, hostid: str = None, agent: str = None, **kwargs):
        """Add a session to a host."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Sessions": []}
        elif "Sessions" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Sessions"] = []

        session = self.get_session_info(hostid=hostid, agent=agent, **kwargs)

        if session not in self.data['hosts'][hostid]["Sessions"]:
            self.data['hosts'][hostid]["Sessions"].append(session)

    def add_interface_info(self, hostid: str = None, ip_address: Union[str, IPv4Address] = None,
                          interface_name: str = None, subnet: Union[str, IPv4Network] = None,
                          agent: str = None, **kwargs):
        """Add an interface to a host."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Interface": []}
        elif "Interface" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Interface"] = []

        new_interface = {}

        if interface_name is None:
            interface_name = kwargs.get("Interface Name", None)
        if interface_name is not None:
            for interface in self.data['hosts'][hostid]["Interface"]:
                if "Interface Name" in interface and interface["Interface Name"] == interface_name:
                    new_interface = interface
                    self.data['hosts'][hostid]["Interface"].remove(interface)
            new_interface["Interface Name"] = interface_name

        if ip_address is None:
            ip_address = kwargs.get("IP Address", None)
        if ip_address is not None:
            if type(ip_address) is str:
                ip_address = IPv4Address(ip_address)
            if ip_address == IPv4Address('0.0.0.0'):
                if self.data['hosts'][hostid]["Interface"] == []:
                    self.data['hosts'][hostid].pop("Interface")
                return

            for interface in self.data['hosts'][hostid]["Interface"]:
                if "IP Address" not in interface:
                    continue
                if interface["IP Address"] != ip_address:
                    continue
                if len(interface) > len(new_interface):
                    new_interface = interface
                elif len(interface) == len(new_interface):
                    for k in ["Interface Name", "Subnet"]:
                        if k in interface and k not in new_interface:
                            new_interface[k] = interface[k]
                self.data['hosts'][hostid]["Interface"].remove(interface)

            new_interface["IP Address"] = ip_address

        if subnet is None:
            subnet = kwargs.get("Subnet", None)
        if subnet is not None:
            if type(subnet) is str:
                subnet = IPv4Network(subnet)
            new_interface["Subnet"] = subnet

        self.data['hosts'][hostid]["Interface"].append(new_interface)

        if self.data['hosts'][hostid]["Interface"] == [{}]:
            self.data['hosts'][hostid].pop("Interface")

    def add_user_info(self, hostid: str = None, username: str = None, uid: int = None,
                     group_name: str = None, gid: int = None, password: str = None,
                     password_hash: str = None, password_hash_type: str = None,
                     logged_in: bool = None, key_path: str = None, agent: str = None,
                     **kwargs):
        """Add user info to a host."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))

        # Only add if username or uid is known
        if username is not None or uid is not None:
            if hostid not in self.data['hosts']:
                self.data['hosts'][hostid] = {"UserInfo": []}
            elif "UserInfo" not in self.data['hosts'][hostid]:
                self.data['hosts'][hostid]["UserInfo"] = []

            new_user = {}

            if username is None:
                username = kwargs.get("Username", None)
            if username is not None:
                new_user["Username"] = username
                for user in self.data['hosts'][hostid]["UserInfo"]:
                    if "Username" in user and user["Username"] == username:
                        new_user = user
                        self.data['hosts'][hostid]["UserInfo"].remove(user)

            if uid is None:
                uid = kwargs.get("UID", None)
            if uid is not None:
                new_user["UID"] = uid

            if password is None:
                password = kwargs.get("Password", None)
            if password is not None:
                new_user["Password"] = password

            if password_hash is None:
                password_hash = kwargs.get("Password Hash", None)
            if password_hash is not None:
                new_user["Password Hash"] = password_hash

            if password_hash_type is None:
                password_hash_type = kwargs.get("Password Hash Type", None)
            if password_hash_type is not None:
                if type(password_hash_type) is str:
                    password_hash_type = CyEnums.PasswordHashType.parse_string(password_hash_type)
                new_user["Password Hash Type"] = password_hash_type

            if logged_in is None:
                logged_in = kwargs.get("Logged in", None)
            if logged_in is not None:
                new_user["Logged in"] = logged_in

            if key_path is None:
                key_path = kwargs.get("Key Path", None)
            if key_path is not None:
                new_user["Key Path"] = key_path

            new_group = {}
            if "Groups" not in new_user:
                new_user["Groups"] = []

            if "Groups" in kwargs:
                new_user["Groups"] = kwargs.get("Groups")
            else:
                if group_name is not None:
                    new_group["Group Name"] = group_name
                    builtin_name = CyEnums.BuiltInGroups.parse_string(group_name)
                    if builtin_name is not CyEnums.BuiltInGroups.UNKNOWN:
                        new_group["Builtin Group"] = builtin_name

                if gid is not None:
                    new_group["GID"] = gid

                if new_group != {}:
                    new_user["Groups"].append(new_group)

            if new_user["Groups"] == []:
                new_user.pop("Groups")

            self.data['hosts'][hostid]["UserInfo"].append(new_user)

    def add_file_info(self, hostid: str = None, path: str = None, name: str = None,
                     vendor: str = None, version: str = None, file_type: str = None,
                     user: str = None, agent: str = None, **kwargs):
        """Add file info to a host."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"Files": []}
        elif "Files" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["Files"] = []

        new_file = {}

        if path is None:
            path = kwargs.get("Path", None)
        if path is not None:
            new_file["Path"] = path
            new_file["Known Path"] = CyEnums.Path.parse_string(path)

        if name is None:
            name = kwargs.get("File Name", None)
        if name is not None:
            new_file["File Name"] = name
            new_file["Known File"] = CyEnums.FileType.parse_string(name)

        if name is not None and path is not None:
            for file in self.data['hosts'][hostid]["Files"]:
                if ("File Name" in file and "Path" in file and
                    name == file["File Name"] and path == file["Path"]):
                    self.data['hosts'][hostid]["Files"].remove(file)
                    new_file = file
                    break

        if vendor is None:
            vendor = kwargs.get("Vendor", None)
        if vendor is not None:
            new_file["Vendor"] = CyEnums.Vendor.parse_string(vendor)

        if version is None:
            version = kwargs.get("Version", None)
        if version is not None:
            new_file["Version"] = version

        if file_type is None:
            file_type = kwargs.get("Type", None)
        if file_type is not None:
            if type(file_type) is str:
                file_type = CyEnums.FileType.parse_string(file_type)
            new_file["Type"] = file_type

        if user is None:
            user = kwargs.get("Username", None)
        if user is not None:
            new_file["Username"] = user

        self.data['hosts'][hostid]["Files"].append(new_file)

    def add_system_info(self, hostid: str = None, hostname: str = None,
                       os_type: str = None, os_distribution: str = None,
                       os_version: str = None, os_kernel: str = None,
                       os_patches: list = None, architecture: str = None,
                       agent: str = None, **kwargs):
        """Add system info to a host."""
        if hostid is None:
            hostid = str(len(self.data['hosts']))
        if hostid not in self.data['hosts']:
            self.data['hosts'][hostid] = {"SystemInfo": {}}
        elif "SystemInfo" not in self.data['hosts'][hostid]:
            self.data['hosts'][hostid]["SystemInfo"] = {}

        sys_info = self.data['hosts'][hostid]["SystemInfo"]

        if hostname is None:
            hostname = kwargs.get("Hostname", None)
        if hostname is not None:
            sys_info["Hostname"] = hostname

        if os_type is None:
            os_type = kwargs.get("OSType", None)
        if os_type is not None:
            if type(os_type) is str:
                os_type = CyEnums.OperatingSystemType.parse_string(os_type)
            sys_info["OSType"] = os_type

        if os_distribution is None:
            os_distribution = kwargs.get("OSDistribution", None)
        if os_distribution is not None:
            if type(os_distribution) is str:
                os_distribution = CyEnums.OperatingSystemDistribution.parse_string(os_distribution)
            sys_info["OSDistribution"] = os_distribution

        if os_version is None:
            os_version = kwargs.get("OSVersion", None)
        if os_version is not None:
            if type(os_version) is str:
                os_version = CyEnums.OperatingSystemVersion.parse_string(os_version)
            sys_info["OSVersion"] = os_version

        if os_kernel is None:
            os_kernel = kwargs.get("OSKernelVersion", None)
        if os_kernel is not None:
            if type(os_kernel) is str:
                os_kernel = CyEnums.OperatingSystemKernelVersion.parse_string(os_kernel)
            sys_info["OSKernelVersion"] = os_kernel

        if os_patches is None:
            os_patches = kwargs.get("os_patches", None)
        if os_patches is not None:
            for patch in os_patches:
                if type(patch) is str:
                    patch = CyEnums.OperatingSystemPatch.parse_string(patch)
                if "os_patches" in sys_info:
                    sys_info["os_patches"].append(patch)
                else:
                    sys_info["os_patches"] = [patch]

        if architecture is None:
            architecture = kwargs.get("Architecture", None)
        if architecture is not None:
            if isinstance(architecture, str):
                architecture = CyEnums.Architecture.parse_string(architecture)
            sys_info["Architecture"] = architecture


class ObsHistoryWrapper(BaseWrapper):
    """Wrapper providing full observability belief state by accumulating partial observations.

    This wrapper maintains a running history of observations for each tracked agent,
    intelligently merging new observations into accumulated state. The accumulated
    state is exposed via the Results.state attribute.

    The wrapper must be applied BEFORE FixedFlatWrapper in the wrapper chain since
    it operates on dictionary observations.

    Attributes:
        tracked_agents (list): List of agent names to track state for
        agent_states (dict): Map from agent name to AccumulatedState instance
        scenario: CybORG scenario object (lazy-loaded)
        initialized (bool): Whether scenario has been loaded

    Example:
        >>> cyborg = CybORG(scenario_path, 'sim')
        >>> wrapped = ObsHistoryWrapper(cyborg, agents=['Red'])
        >>> wrapped = FixedFlatWrapper(EnumActionWrapper(wrapped), max_params=...)
        >>> env = OpenAIGymWrapper(env=wrapped, agent_name="Red")
    """

    def __init__(self, env=None, agent=None, agents: List[str] = None):
        """Initialize the ObsHistory Wrapper.

        Args:
            env: Wrapped environment (CybORG or another wrapper)
            agent: Agent instance (for BaseWrapper compatibility, not used)
            agents: List of agent names to track (e.g., ['Red', 'Blue']).
                   If None, will auto-detect from first reset.
        """
        super().__init__(env=env, agent=agent)
        self.tracked_agents = agents or []
        self.agent_states = {}
        self.scenario = None
        self.initialized = False
        self.step_count = 0  # Track number of steps for debugging

    def reset(self, agent=None):
        """Reset the environment and initialize accumulated state.

        Args:
            agent: Agent name to reset for

        Returns:
            Results: Result with accumulated state as observation (matching fully_obs=True)
        """
        self.step_count = 0

        # Call wrapped environment reset
        result = self.env.reset(agent)

        # Lazy-load scenario on first reset
        if not self.initialized:
            self._initialize_from_scenario()

        # Ensure agent state exists and is reset
        if agent is not None:
            self._ensure_agent_state(agent)

            # Update state with initial observation
            if hasattr(result, 'observation') and result.observation is not None:
                self.agent_states[agent].update(result.observation, agent)

            # CRITICAL: Replace observation with accumulated state (matches fully_obs=True behavior)
            # The original fully_obs returns next_state[agent].data as observation, not raw obs
            accumulated_state = self.agent_states[agent].get_state()
            result.observation = accumulated_state
            result.state = accumulated_state  # Keep state for compatibility

        return result

    def step(self, agent=None, action=None):
        """Execute a step and update accumulated state.

        Args:
            agent: Agent name performing the step
            action: Action to execute

        Returns:
            Results: Result with accumulated state as observation (matching fully_obs=True)
        """
        self.step_count += 1

        # Call wrapped environment step
        result = self.env.step(agent, action)

        # Update accumulated state for this agent
        if agent is not None:
            if agent not in self.agent_states:
                self._ensure_agent_state(agent)

            if hasattr(result, 'observation') and result.observation is not None:
                self.agent_states[agent].update(result.observation, agent)

            # Replace observation with accumulated state (matches fully_obs=True behavior)
            accumulated_state = self.agent_states[agent].get_state()
            result.observation = accumulated_state
            result.state = accumulated_state  # Keep state for compatibility

        return result

    def _initialize_from_scenario(self):
        """Lazy-load scenario from wrapped environment."""
        try:
            # Try to get environment_controller from wrapped env
            env_controller = self.env.get_attr('environment_controller')
            if env_controller is not None and hasattr(env_controller, 'scenario'):
                self.scenario = env_controller.scenario
                self.initialized = True
        except (AttributeError, KeyError):
            # If we can't get the scenario, we'll initialize states without pre-population
            self.initialized = True

    def _ensure_agent_state(self, agent_name: str):
        """Ensure AccumulatedState exists for an agent.

        Args:
            agent_name: Name of the agent
        """
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = AccumulatedState()
            if self.scenario is not None:
                self.agent_states[agent_name].initialise_state(self.scenario)
        else:
            # Reset existing state
            self.agent_states[agent_name] = AccumulatedState()
            if self.scenario is not None:
                self.agent_states[agent_name].initialise_state(self.scenario)

    def get_max_elements(self):
        """Get maximum element counts from accumulated states.

        Returns:
            dict: Maximum element counts across all tracked agents
        """
        max_elements = {
            "subnets": 0,
            "hosts": 0,
            "processes": 0,
            "sessions": 0,
            "connections": 0,
            "interfaces": 0
        }

        for agent_state in self.agent_states.values():
            agent_max = agent_state.get_max_elements()
            for key in max_elements:
                if agent_max.get(key, 0) > max_elements[key]:
                    max_elements[key] = agent_max[key]

        return max_elements
