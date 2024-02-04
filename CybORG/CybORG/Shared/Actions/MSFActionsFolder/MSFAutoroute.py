# Copyright DST Group. Licensed under the MIT license.
from ipaddress import IPv4Network

from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import MSFAction
from CybORG.Shared.Enums import SessionType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.State import State


class MSFAutoroute(MSFAction):
    def __init__(self, agent, session, ip_address):
        super().__init__(session, agent)
        self.ip_address = ip_address

    def sim_execute(self, state: State):
        obs = Observation()
        if self.session not in state.sessions[self.agent] or self.meterpreter_session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs
        # NEED TO FIX
        interfaces = []
        meterpreter_session = state.sessions[self.agent][self.ip_address]
        msf_session = state.sessions[self.agent][self.session]
        if meterpreter_session in msf_session.children.values() and meterpreter_session.session_type == SessionType.METERPRETER and msf_session.session_type == SessionType.MSF_SERVER:
            obs.set_success(True)
            for interface in state.hosts[meterpreter_session.host].interfaces:
                if str(interface.ip_address) != '127.0.0.1':
                    interfaces.append(interface)
                    obs.add_interface_info(hostid=str(self.ip_address), subnet=interface.subnet)
            # routes function in Simulator MSF Session object??
            # we should perhas implement a Simulator SessionHandler (can perhaps have a 
            # simulated MSFSession handling, as well as a direct State object lookup)
            msf_session.routes[self.ip_address] = interfaces
        else:
            obs.set_success(False)
        return obs

    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        sessions = session_handler.get_session_by_remote_ip(str(self.ip_address), session_type="meterpreter")
        print(sessions)
        if len(sessions) == 0:
            print("no meterpreter session for host {}".format(str(self.ip_address)))
            obs.set_success(False)
            return obs

        session = list(sessions.keys())[0]
        output = session_handler.execute_module(mtype='post', mname='multi/manage/autoroute',
                                         opts={'SESSION': session})
        obs.add_raw_obs(output)
        """Example:
        [!] SESSION may not be compatible with this module.
        [*] Running module against 10.0.2.164
        [*] Searching for subnets to autoroute.
        [+] Route added to subnet 10.0.2.0/255.255.254.0 from host's routing table.
        [*] Post module execution completed
        """
        obs.set_success(False)
        for line in output.split('\n'):
            if '[+] Route added' in line:
                obs.set_success(True)
                subnet = line.split(' ')[5]
                obs.add_interface_info(hostid=str(self.ip_address), subnet=IPv4Network(subnet))

        return obs

    def __str__(self):
        return super(MSFAutoroute, self).__str__() + f", Meterpreter Session: {self.ip_address}"
