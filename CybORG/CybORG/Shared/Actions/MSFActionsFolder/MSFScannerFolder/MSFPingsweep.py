# Copyright DST Group. Licensed under the MIT license.
from ipaddress import IPv4Address, IPv4Network

from CybORG.Shared.Actions.MSFActionsFolder.MSFScannerFolder.MSFScanner import MSFScanner
from CybORG.Shared.Enums import InterfaceType, SessionType, ProcessType, ProcessVersion, AppProtocol
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.State import State


# msf module is post/multi/gather/ping_sweep
class MSFPingsweep(MSFScanner):
    #def __init__(self, subnet: IPv4Network, session: int, agent: str):
    def __init__(self, subnet: IPv4Network, session: int, agent: str, target_session: int):
        # target_sessions are used for Metasploit sessions.
        # the initial implementation of this action uses a post-exploitation action 
        # within Metasploit (which requires an existing session)
        # however the Action within this Environment can also be used as an initial
        # reconnaissance of the environment (which is a pre-exploitation action and
        # doesn't have an existing session
        # 
        # an updated implementation has added a passthrough fping metasploit command
        # to backport this into the existing class definition, we use session 0 
        # to represent this client/target "shell" session on the attacker machine to perform this
        # pre-exploit pingsweep.
        #
        # metasploit sessions start of index 1
        super().__init__(session, agent)
        self.subnet = subnet
        self.target_session = target_session
        #self.lo = IPv4Address("127.0.0.1")

    def sim_execute(self, state: State, session_handler = None):
        obs = Observation()
        if self.session not in state.sessions[self.agent]:
            #print("session not in state sessions")
            obs.set_success(False)
            return obs
        from_host = state.sessions['Red'][self.session].host
        session = state.sessions['Red'][self.session]

        if session.session_type != SessionType.MSF_SERVER or not session.active:
            #print("session not MSF_SERVER type")
            obs.set_success(False)
            return obs

        # to Metasploit.
        # We look up the session handler for the required target_session.
        # in the AbstractActions/Pingsweep action, the MSF server session is 
        # passed as the target_session (indicating that the pingsweep is being
        # executed on the Attacker host and that all subnets in the target
        # environment can be scanned from the Attacker host.
        # maintain this assumption for now

        if self.target_session in state.sessions['Red']:
            target_session = state.sessions['Red'][self.target_session]
        else:
            #print("target session not in state sessions")
            obs.set_success(False)
            return obs

        if not (target_session.session_type == SessionType.METERPRETER or target_session.session_type == SessionType.MSF_SHELL) or not target_session.active:
            #print("target session not correct type")
            obs.set_success(False)
            return obs

        
        # why are we obtaining a target_session object from this method??
        # 
        # is there a better way to determine reachability of the subnet than this function.  
        # have a look at the ConcreteActions/Pingsweep code
        #target_session, from_interface = self.get_local_source_interface(local_session=target_session,
        #                                                                 remote_address=self.subnet.network_address,
        #                                                                 state=state)

        # TODO: implement the check_routable function to determine if the port is reachable

        #if from_interface is None:
        #    #print("from_interface is None")
        #    obs.set_success(False)
        #    return obs
        target_hosts = []
        for host in state.subnets[self.subnet].ip_addresses:
            obs.set_success(True)
            # Taken from the ConcreteActions/Pingsweep code update
            # multi homed hosts have more than 1 ip address
            hostid = state.ip_addresses[host]
            target_hosts.append(hostid)
            obs.add_interface_info(hostid=hostid, ip_address=host, subnet=self.subnet)
        return obs

    def emu_execute(self, session_handler) -> Observation:
        # there are 2 separate metasploit actions for ping sweep
        # one is a post-exploitation action (which requires a metasploit session)
        # the other is an initial reconnaissance from the attacker where there isn't a metasploit sessions
        # the second uses the passthrough nmap command to gain similar information

        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs
        if self.target_session == 0:
          output = session_handler.execute_module(mtype="passthrough", mname="fping -gaq {}".format(str(self.subnet)), opts={})
          obs.add_raw_obs(output)
          '''
          10.46.64.1
          10.46.64.100
          10.46.64.101
          '''
          if output == []:
             obs.set_success(False)
             return obs
          for line in output.split("\n"):
                # if line includes subnet gw address (defined as .1 here)
                # won't apply in cloud network settings
                if line == "" or line.split(".")[3] == "1":
                    continue
                ip_address = line
                #session_handler._log_debug(f"New IP Address found: {ip_address}")
                obs.add_interface_info(hostid=str(ip_address), ip_address=ip_address, subnet=self.subnet)
          obs.set_success(True)
          session_handler._log_debug(output)
        else:
          output = session_handler.execute_module(mtype='post', mname='multi/gather/ping_sweep',  opts={'RHOSTS': str(self.subnet), 'SESSION': self.target_session})
          obs.add_raw_obs(output)
          '''[*] Performing ping sweep for IP range 10.0.2.0/23
             [+] 	10.0.2.1 host found
             [+] 	10.0.2.164 host found
             [*] Post module execution completed'''
          if output.find("Post failed") != -1:
             obs.set_success(False)
             return obs
          for line in output.split('\n'):
            if 'host found' in line:
                obs.set_success(True)
                ip_address = line.split(' ')[1].replace('\t', '')
                #session_handler._log_debug(f"New IP Address found: {ip_address}")
                obs.add_interface_info(hostid=str(ip_address), ip_address=ip_address, subnet=self.subnet)
          session_handler._log_debug(output)
        return obs

    def __str__(self):
        return super(MSFPingsweep, self).__str__() + f", Subnet: {self.subnet}"
