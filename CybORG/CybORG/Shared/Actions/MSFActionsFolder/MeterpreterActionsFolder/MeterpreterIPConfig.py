# Copyright DST Group. Licensed under the MIT license.
import re
from ipaddress import IPv4Network

from CybORG.Shared.Actions.MSFActionsFolder.MeterpreterActionsFolder.MeterpreterAction import MeterpreterAction
from CybORG.Shared.Enums import OperatingSystemType, SessionType
from CybORG.Shared.Observation import Observation


class MeterpreterIPConfig(MeterpreterAction):
    def __init__(self, session, agent, ip_address):
        super().__init__(session, agent, ip_address)

    def sim_execute(self, state):
        obs = Observation()
        obs.set_success(False)
        # get details of the server session
        server_sessions = [ s for s in state.sessions[self.agent] if s.session_type == SessionType.MSF_SERVER ]
        if self.session not in [ s.ident for s in server_sessions]:
            # no server session found
            return obs
        server_session = server_sessions[0]
        # find session id for the host
        # identify host by ip
        target_hosts = [ h for h,v in state.hosts.items() for i in v.interfaces if i.ip_address == self.ip_address ]
        target_host = target_hosts[0]
        target_sessions = [ s for s in state.sessions[self.agent] if s.ip_addr == self.ip_address and s.session_type == SessionType.METERPRETER]
        if len(target_sessions) == 0:
            obs.set_success(False)
            return obs
        # choose first session
        self.meterpreter_session = target_sessions[0]
        if server_session.active and self.meterpreter_session.active:
            host = state.hosts[self.meterpreter_session.host]
            obs.set_success(True)
            for interface in host.interfaces:
                obs.add_interface_info(hostid=target_host, **(interface.get_state()))
        return obs

    def emu_execute(self, session_handler):
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        target_sessions = session_handler.get_session_by_remote_ip(str(self.ip_address),session_type="meterpreter")
        if len(target_sessions) == 0:
            obs.set_success(False)
            return obs
        else:
          session = list(target_sessions.keys())[0]
          output = session_handler.execute_shell_action(action='ipconfig', session=session)
          obs.add_raw_obs(output)

          """Expected output:
          Interface  1
          ============
          Name         : lo
          Hardware MAC : 00:00:00:00:00:00
          MTU          : 65536
          Flags        : UP,LOOPBACK
          IPv4 Address : 127.0.0.1
          IPv4 Netmask : 255.0.0.0
          IPv6 Address : ::1
          IPv6 Netmask : ffff:ffff:ffff:ffff:ffff:ffff::
          
           
          Interface  2
          ============
          Name         : eth0
          Hardware MAC : 06:ec:36:d0:fb:7e
          MTU          : 9001
          Flags        : UP,BROADCAST,MULTICAST
          IPv4 Address : 10.0.1.90
          IPv4 Netmask : 255.255.255.240
          IPv6 Address : fe80::4ec:36ff:fed0:fb7e
          IPv6 Netmask : ffff:ffff:ffff:ffff::
          """
          obs.set_success(False)
          try:
            for interface in output.split('============\n'):
                split = re.sub(' +', ' ', interface).split('\n')
                name = None
                mac = None
                ip = None
                mask = None
                for element in split:
                    if 'Name' in element:
                        name = element.split(': ')[1]
                    if 'Hardware MAC' in element:
                        mac = element.split(': ')[1]
                    if 'IPv4 Address' in element:
                        ip = element.split(': ')[1]
                    if 'IPv4 Netmask' in element:
                        mask = element.split(': ')[1]
                if mask is not None and ip is not None:
                    subnet = IPv4Network(f'{ip}/{mask}', False)
                else:
                    subnet = None
                if ip is not None:
                    obs.add_interface_info(hostid=str(self.ip_address), interface_name=name, ip_address=ip, subnet=subnet)
                    obs.set_success(True)
          except IndexError as ex:
            #session_handler._log_debug(output)
            raise ex

          session_handler._log_debug(output)
        return obs

