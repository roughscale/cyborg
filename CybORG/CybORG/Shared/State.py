from CybORG.Shared.Observation import Observation
from pprint import pprint

class State(Observation):

    """ This manages the State space of the Agent which is a running history of all observations """
    def __init__(self):
        self.data = {"network": {}, "hosts": {}}
        self.raw = ''

    def update(self, obs: Observation):
        # convert Observation to dict`
        if isinstance(obs, Observation):
          obs = obs.data
        # remove the success key
        obs.pop('success',None)
        # merge observations
        for key, info in obs['hosts'].items():
            #if not isinstance(info, dict):
            #    self.add_key_value(key, info)
            #    continue
            if "Sessions" in info:
                for session_info in info["Sessions"]:
                    self.add_session_info(hostid=key, **session_info)
            if "Processes" in info:
                for process in info["Processes"]:
                    if 'Connections' in process:
                        for conn in process['Connections']:
                            self.add_process(hostid=key, **process, **conn)
                    else:
                        self.add_process(hostid=key, **process)
            if "UserInfo" in info:
                for user in info["UserInfo"]:
                    self.add_user_info(hostid=key, **user)
            if "Files" in info:
                for file_info in info["Files"]:
                    self.add_file_info(hostid=key, **file_info)
            if "Interface" in info:
                for interface in info["Interface"]:
                    self.add_interface_info(hostid=key, **interface)
            if "SystemInfo" in info:
                self.add_system_info(hostid=key, **info["SystemInfo"])

        if 'subnets' in obs['network']:
            for subnet in obs['network']['subnets']:
                self.add_subnet(subnet)

    def get_state(self):
        return self.data


