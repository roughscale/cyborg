# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared.Actions.MSFActionsFolder.MeterpreterActionsFolder.MeterpreterAction import MeterpreterAction
from CybORG.Shared.Enums import SessionType, OperatingSystemType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Environment import Environment


# Call getuid from a meterpreter session - gives the username of the session
class GetUid(MeterpreterAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super().__init__(session=session, agent=agent, target_session=target_session)

    def sim_execute(self, environment: Environment):
        obs = Observation()
        obs.set_success(False)

        if self.session not in environment.sessions[self.agent] or environment.sessions[self.agent][
            self.session].session_type != SessionType.MSF_SERVER:
            return obs
        if self.meterpreter_session not in environment.sessions[self.agent] or environment.sessions[self.agent][
            self.meterpreter_session].session_type != SessionType.METERPRETER:
            return obs
        if environment.sessions[self.agent][self.session].active and environment.sessions[self.agent][self.meterpreter_session].active:
            obs.set_success(True)
            obs.add_user_info(username=environment.sessions[self.agent][self.meterpreter_session].username)
        return obs
