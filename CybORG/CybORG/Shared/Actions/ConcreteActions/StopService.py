from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Session import Session, RedAbstractSession
from CybORG.Simulator.Environment import Environment


class StopService(ConcreteAction):
    def __init__(self, agent: str, session: int, target_session: int, service: str):
        super().__init__(session, agent)
        self.service = service
        self.target_session = target_session

    def sim_execute(self, environment: Environment):
        # check that both sessions exist
        if self.session not in environment.sessions[self.agent] or self.target_session not in environment.sessions[self.agent]:
            return Observation(False)

        # check that both sessions are active
        parent_session: RedAbstractSession = environment.sessions[self.agent][self.session]
        client_session: Session = environment.sessions[self.agent][self.target_session]
        if not parent_session.active or not client_session.active:
            return Observation(False)

        # get target host
        target_host: Host = environment.hosts[client_session.host]
        # find chosen service on host
        if self.service not in target_host.services:
            return Observation(False)
        service = target_host.services[self.service]
        environment.stop_service(target_host.hostname, self.service)
        obs = Observation(True)

        return obs
