# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared.Actions.MSFActionsFolder.MeterpreterActionsFolder.MeterpreterAction import MeterpreterAction
from CybORG.Shared.Enums import SessionType, OperatingSystemType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.State import State


# Call getuid from a meterpreter session - gives the username of the session
class GetUid(MeterpreterAction):
    def __init__(self, session: int, agent: str, ip_address: str):
        super().__init__(session=session, agent=agent, ip_address=ip_address)

    def sim_execute(self, state: State):
        obs = Observation()
        obs.set_success(False)

        if self.session not in state.sessions[self.agent] or state.sessions[self.agent][
            self.session].session_type != SessionType.MSF_SERVER:
            return obs
        #
        #if self.meterpreter_session not in state.sessions[self.agent] or state.sessions[self.agent][
        #    self.meterpreter_session].session_type != SessionType.METERPRETER:
        #    return obs
        if state.sessions[self.agent][self.session].active and state.sessions[self.agent][self.meterpreter_session].active:
            obs.set_success(True)
            obs.add_user_info(username=state.sessions[self.agent][self.meterpreter_session].username)
        return obs

    def emu_execute(self, session_handler):
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        # get meterpreter sessions for the target host
        target_sessions = session_handler.get_sessions_by_remote_ip(str(self.ip_address),"meterpreter")
        
        if len(target_sessions) == 0:
            obs.set_success(False)
        else:
          target_session = target_sessions[0]
          output = session_handler.execute_shell_action(action='getuid', session=str(target_session)).replace('\r','')
          obs.add_raw_obs(output)
          obs.set_success(False)
          try:
            for line in output.split("\n"):
              pass
          except IndexError as ex:
            session_handler._log_debug(output)
            raise ex

        session_handler._log_debug(output)
        return obs



