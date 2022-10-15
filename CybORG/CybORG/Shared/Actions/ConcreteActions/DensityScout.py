from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Environment import Environment


class DensityScout(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super(DensityScout, self).__init__(session=session, agent=agent)
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
        obs.set_success(True)
        for file in target_host.files:
            obs.add_file_info(hostid=target_host.hostname, name=file.name, path=file.path, density=file.density)

        return obs
