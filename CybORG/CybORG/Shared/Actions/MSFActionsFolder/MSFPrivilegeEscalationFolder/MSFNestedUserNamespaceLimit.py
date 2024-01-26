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


class MSFNestedUserNamespaceLimit(MSFPrivilegeEscalation):
    """
    Implements the NestedUserNamespaceLimit permissions escalation action
    """
    def __init__(self, session: int, agent: str, ip_address: IPv4Address):
        super().__init__(session, agent)
        self.ip_address = ip_address
    def sim_execute(self, state: State) -> Observation:
        # comment out the below and implement AbstractActions/PrivilegeEscalation logic
        #return self.sim_escalate(state, "root")

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


    def emu_execute(self) -> Observation:
        # Need to implement this in MSF 
        raise NotImplementedError

    def test_exploit_works(self, target_host: Host) -> Tuple[bool, Tuple[Process,...]]:
        # the exact patches and OS distributions are described here:
        # NOTE: doesn't implement any patch reference.
        # ie all linux hosts are exploitable
        # returns empty tuple necessary processes
        return target_host.os_type == OperatingSystemType.LINUX, ()

    def __str__(self):
        return f"{self.__class__.__name__} Target: {self.ip_address}"

