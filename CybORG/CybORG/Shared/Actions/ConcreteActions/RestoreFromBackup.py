from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.Environment import Environment


class RestoreFromBackup(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super(RestoreFromBackup, self).__init__(session, agent)
        self.target_session = target_session

    def sim_execute(self, environment: Environment) -> Observation:
        obs = Observation()
        if self.session not in environment.sessions[self.agent] or self.target_session not in environment.sessions[self.agent]:
            obs.set_success(False)
            return obs
        target_host: Host = environment.hosts[environment.sessions[self.agent][self.target_session].host]
        session = environment.sessions[self.agent][self.session]
        target_session = environment.sessions[self.agent][self.target_session]

        if not session.active or not target_session.active:
            obs.set_success(False)
            return obs

        old_sessions = {}
        for agent, sessions in target_host.sessions.items():
            old_sessions[agent] = {}
            for session in sessions:
                old_sessions[agent][session] = environment.sessions[agent].pop(session)
        target_host.restore()
        for agent, sessions in target_host.sessions.items():
            for session in sessions:
                environment.sessions[agent][session] = old_sessions[agent][session]
        return obs
