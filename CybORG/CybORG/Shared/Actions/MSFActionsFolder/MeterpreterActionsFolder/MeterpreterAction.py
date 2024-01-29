# Copyright DST Group. Licensed under the MIT license.
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import MSFAction


class MeterpreterAction(MSFAction):
    def __init__(self, session: int, agent: str, ip_address: str):
        super().__init__(session=session, agent=agent)
        self.ip_address = ip_address

    def __str__(self):
        return super(MeterpreterAction, self).__str__() + f", Meterpreter IPAddr: {self.ip_address}"
