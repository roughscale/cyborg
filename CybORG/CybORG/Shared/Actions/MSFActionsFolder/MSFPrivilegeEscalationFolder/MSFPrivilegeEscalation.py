# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import MSFAction
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Host import Host
from CybORG.Simulator.State import State
from CybORG.Shared.Enums import OperatingSystemType, DecoyType
from CybORG.Simulator.Process import Process
from CybORG.Simulator.Session import Session
from CybORG.Simulator.State import State

from abc import abstractmethod
from typing import Tuple


class MSFPrivilegeEscalation(MSFAction):
    def __init__(self, session: int, agent: str):
        super().__init__(session, agent)

    @abstractmethod
    def sim_execute(self, state):
        raise NotImplementedError

    @abstractmethod
    def emu_execute(self):
        raise NotImplementedError

    def sim_escalate(self, state: State, target_hostname: str, target_session: Session, user: str) -> Observation:
        """
        escalate the session on the host if it works
        checks should already have determined that the target_session is
        present on the target host and is not sandboxed
        """
        target_host = state.hosts[target_hostname]
        print(target_hostname)

        obs=Observation()

        is_compatible, necessary_processes = self.test_exploit_works(target_host)
        if not is_compatible:
            obs.set_success(False)
            return obs

        for proc in necessary_processes:
            if proc.decoy_type & DecoyType.ESCALATE:
                obs.set_success(False)
                return obs

        # process is escalatable on the host
        # at the moment, this also works even if there are no necessary processes return
        # in the test_exploit_works function.
        # 

        # when escalating, re-use existing escalated session if already on host (to avoid session explosion)
        host_sessions = state.get_sessions_by_host(self.agent, target_hostname)
        for sess in host_sessions:
            if sess.username == user:
                obs=self.__reuse_session(user, target_host, existing_session=target_session, privesc_session=sess, state=state)
                return obs

        obs=self.__upgrade_session(user, target_host, target_session)

        return obs

    @abstractmethod
    def test_exploit_works(self, target_host: Host) ->\
            Tuple[bool, Tuple[Process, ...]]:
        """
        checks if OS and process information is correct for escalate to work.
        First return is True if compatible, False otherwise.
        Second return is tuple of all processes which must be valid for escalate to succeed.
        """
        raise NotImplementedError

    def __reuse_session(self, username: str, target_host: Host, existing_session: Session, privesc_session: Session, state: State):

        # when this occurs, we add the existing escalated session in the Observation, we add the existing non-escalated
        # session as "inactive" (so that this session ID will be forgotten in the ActionSpace), and we remove the existing
        # non-esclated session and process from the Simulator State space.

        # remove existing process and session from host State. This is the keep host State manageable and avoid session explosion
        # process from the Agent's State.
        print("reusing session {} for escalation session {}".format(privesc_session.ident, existing_session.ident))
        state.remove_process(hostname=str(target_host.hostname), pid=existing_session.pid)

        obs = Observation()
        # remove session from Agent's state
        obs.add_session_info(hostid=str(target_host.hostname),
                             session_id=existing_session.ident,
                             session_type=existing_session.session_type,
                             pid=existing_session.pid,
                             username=existing_session.username,
                             agent=self.agent,
                             active=False
                             )

        # return existing escalated session
        obs.add_session_info(hostid=str(target_host.hostname),
                             session_id=privesc_session.ident,
                             session_type=privesc_session.session_type,
                             pid=privesc_session.pid,
                             username=username,
                             agent=self.agent
                             )
        obs.set_success(True)
        return obs
        
    def __upgrade_session(self, username: str, target_host: Host, session: Session):
        """
        called when successful, upgrades the session privileges
        """
        if target_host.os_type == OperatingSystemType.WINDOWS:
            ext = 'exe'
            path = 'C:\\temp\\'
        elif target_host.os_type == OperatingSystemType.LINUX:
            ext = 'sh'
            path = '/tmp/'
        else:
            return Observation(False)
        obs = Observation()
        # upgrade session to new username
        session.username = username
        target_host.get_process(session.pid).user = username
        target_host.add_file(f'escalate.{ext}', path, username, 7,
                density=0.9, signed=False)
        # add in new session info to observation
        obs.add_session_info(hostid=str(target_host.hostname),
                             session_id=session.ident,
                             session_type=session.session_type,
                             pid=session.pid,
                             username=username,
                             agent=self.agent)
        obs.set_success(True)
        return obs

