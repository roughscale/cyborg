from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.Environment import Environment


class StopProcess(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int, pid: int):
        super(StopProcess, self).__init__(session, agent)
        self.pid = pid
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
        proc = target_host.get_process(self.pid)
        if proc is not None:
            if proc.user != 'root' and proc.user != 'SYSTEM':
                obs.set_success(True)
                self.kill_process(environment, target_host, proc)
            else:
                obs.set_success(False)
        else:
            obs.set_success(False)
        return obs

    def kill_process(self, environment: Environment, host: Host, process: Process):
        agent, session = environment.get_session_from_pid(host.hostname, pid=process.pid)
        host.processes.remove(process)
        if process.pid in [i['process'] for i in host.services.values()]:
            process.pid = None
            host.add_process(**process.__dict__)
            service = True
        else:
            service = False
        if session is not None:
            host.sessions[agent].remove(session)
            environment.sessions[agent].pop(session)
            if service:
                session_reloaded = state.add_session(host=host.hostname, user=session.user,
                                                    session_type=session.session_type, agent=session.agent,
                                                    parent=session.parent, timeout=session.timeout)
