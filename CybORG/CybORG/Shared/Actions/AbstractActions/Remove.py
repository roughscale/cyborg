from random import choice

from CybORG.Shared import Observation
from .Monitor import Monitor
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.StopProcess import StopProcess
from CybORG.Simulator.Session import VelociraptorServer
from CybORG.Simulator.Environment import Environment


class Remove(Action):
    def __init__(self, session: int, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.hostname = hostname

    def sim_execute(self, environment: Environment) -> Observation:
        # perform monitor at start of action
        #monitor = Monitor(session=self.session, agent=self.agent)
        #obs = monitor.sim_execute(environment)

        parent_session: VelociraptorServer = environment.sessions[self.agent][self.session]
        # find relevant session on the chosen host
        sessions = [s for s in environment.sessions[self.agent].values() if s.host == self.hostname]
        if len(sessions) > 0:
            session = choice(sessions)
            obs = Observation(True)
            # remove suspicious processes
            if self.hostname in parent_session.sus_pids:
                for sus_pid in parent_session.sus_pids[self.hostname]:
                    action = StopProcess(session=self.session, agent=self.agent, target_session=session.ident, pid=sus_pid)
                    action.sim_execute(environment)
            # remove suspicious files
            return obs
        else:
            return Observation(False)

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
