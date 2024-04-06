# Copyright DST Group. Licensed under the MIT license.
from ipaddress import IPv4Address, IPv4Network
from typing import List

from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo_subnet, lo
from CybORG.Shared.Actions.MSFActionsFolder.MSFScannerFolder.MSFScanner import MSFScanner
from CybORG.Shared.Enums import InterfaceType, SessionType, ProcessType, ProcessVersion, AppProtocol
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.State import State

# msf module is auxiliary/scanner/portscan/tcp
class MSFPortscan(MSFScanner):
    def __init__(self, ip_address: IPv4Address, session: int, agent: str):
        super().__init__(session, agent)
        self.ip_address = ip_address

    def sim_execute(self, state: State, session_handler = None):
        obs = Observation()

        server_sessions = [ s for s in state.sessions['Red'] if s.ident == self.session]
        if self.session not in [ s.ident for s in server_sessions if s.session_type == SessionType.MSF_SERVER and s.active]:
            # invalid server session
            obs.set_success(False)
            return obs

        # choose first server session
        session = server_sessions[0]
        from_host = session.host

        if str(self.ip_address) == "127.0.0.1":
            target_host = state.hosts[from_host]
        else:
            target_host = state.hosts[state.ip_addresses[self.ip_address]]

        target_subnet = None
        ports = None
        if self.ip_address == lo:
            target_subnet = lo_subnet
            from_interface = [i for i in target_host.interfaces if i.ip_address == lo][0]
            # from ConcreteActions/Portscan
            ports = [ "all" ]
        else:
            # this identifies the subnet of ip address
            for subnet in state.subnets.values():
                if self.ip_address in subnet.ip_addresses:
                    target_subnet = subnet.cidr
                    break

            # this checks if the remote address is routeable from the server session
            session, from_interface = self.get_local_source_interface(local_session=session, remote_address=self.ip_address, state=state)
            
            # from ConcreteActions/Portscan
            if from_interface is not None and from_interface.subnet != lo:
              # checks what ports are accessible from the originating host
              ports = self.check_routable([ state.subnets[from_interface.subnet] ], [s for s in state.subnets.values() if self.ip_address in s.cidr])

        if from_interface is None:
            obs.set_success(False)
            return obs

        # from ConcreteActions/Portscan
        if ports is None or ports == []:
            obs.set_success(False)
            return obs

        obs.set_success(True)

        for process in target_host.processes:
            for conn in process.connections:
                # multiple connections per process ?
                # From ConcreteActions/Portscan
                if 'local_port' in conn and (conn['local_port'] in ports or 'all' in ports):
                    if self.ip_address == IPv4Address("127.0.0.1"):
                        if (conn['local_address'] == IPv4Address("127.0.0.1") or conn['local_address'] == IPv4Address("0.0.0.0")) and 'remote_address' not in conn:
                            hostid = state.ip_addresses[self.ip_address]
                            obs.add_process(hostid=hostid, local_port=conn["local_port"], local_address=self.ip_address)
                    # lets break this up
                    elif (conn['local_address'] == IPv4Address("0.0.0.0") or conn['local_address'] == self.ip_address) and 'remote_address' not in conn:
                                # does this process also add to the list of ports in the ActionSpace??
                                # multi homed hosts have more than 1 ip address
                                hostid = state.ip_addresses[self.ip_address]
                                # given that this may return multiple entries of the same port and ip address
                                # limit duplication in the Observation
                                if hostid not in obs.data["hosts"] or "Processes" not in obs.data["hosts"][hostid]:
                                    obs.add_process(hostid=hostid, local_port=conn["local_port"], local_address=self.ip_address)
                                elif "Processes" in obs.data["hosts"][hostid]:
                                    existing_proc_obs = obs.data["hosts"][hostid]["Processes"]
                                    for proc in existing_proc_obs:
                                        if "Connections" in proc:
                                          for c in proc["Connections"]:
                                              if c["local_port"] != conn["local_port"] and \
                                                 c["local_address"] != self.ip_address:
                                                   obs.add_process(hostid=hostid, local_port=conn["local_port"], local_address=self.ip_address)
        return obs

    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        output = session_handler.execute_module(mtype='auxiliary', mname='scanner/portscan/tcp',
                                                opts={'RHOSTS': str(self.ip_address),
                                                      'PORTS': '21,22,80,111,135,139,443,445,8000,8009,8010,8020,8027,8080'})
        session_handler._log_debug(output)
        obs.add_raw_obs(output)
        try:
            for values in output.split('\n'):
                if values.find('TCP OPEN') != -1:
                    # new port is open
                    port = values.split(f"{self.ip_address}:")[-1].split(" ")[0]
                    obs.add_process(hostid=str(self.ip_address), local_port=int(port), local_address=self.ip_address)
                    obs.set_success(True)
        except Exception as e:
            session_handler._log_debug(
                f"Error occured in MSFPortscan output parsing with output: {output} and error {e}")
            raise e
        """" EXAMPLE VALUE OF RESULT
        'VERBOSE => false
        SSL = > false
        SSLVersion = > Auto
        SSLVerifyMode = > PEER
        ConnectTimeout = > 10
        TCP::max_send_size = > 0
        TCP::send_delay = > 0
        THREADS = > 1
        ShowProgress = > true
        ShowProgressPercent = > 10
        PORTS = > 1 - 10000
        TIMEOUT = > 1000
        CONCURRENCY = > 10
        DELAY = > 0
        JITTER = > 0
        RHOSTS = > 127.0.0.1
        [+] 127.0.0.1: - 127.0.0.1: 22 - TCP OPEN
        [+] 127.0.0.1: - 127.0.0.1: 5432 - TCP OPEN
        [*] 127.0.0.1: - Scanned 1 of 1 hosts(100 % complete)
        [*] Auxiliary module execution completed'
        """
        return obs

    def __str__(self):
        return super(MSFPortscan, self).__str__() + f", Target: {self.ip_address}"
