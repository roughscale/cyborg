# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared.Actions.MSFActionsFolder.MeterpreterActionsFolder.MeterpreterAction import MeterpreterAction
from CybORG.Shared.Enums import SessionType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Environment import Environment


# Call localtime from a meterpreter session - gives the current local time of the dict
class LocalTime(MeterpreterAction):
    def __init__(self, session: int, agent: str):
        super().__init__(session=session, agent=agent)

    def sim_execute(self, environment: Environment):
        obs = Observation()
        obs.set_success(False)
        if self.session not in environment.sessions[self.agent]:
            return obs
        session = environment.sessions[self.agent][self.session]

        if session.session_type != SessionType.METERPRETER or not session.active:
            return obs

        obs.set_success(True)
        obs.add_system_info(local_time=session.host.time)
        return obs
