from datetime import datetime

from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Shared import Observation
from CybORG.Shared.Actions import ShellSleep
from CybORG.Shared.Enums import OperatingSystemType, SessionType, ProcessName, Path, ProcessType, ProcessVersion, \
    AppProtocol, FileType, ProcessState, Vulnerability, Vendor, PasswordHashType, BuiltInGroups, \
    OperatingSystemDistribution, OperatingSystemVersion, OperatingSystemKernelVersion, Architecture, \
    OperatingSystemPatch, FileVersion

import inspect, random


class FixedFlatWrapper(BaseWrapper):
    def __init__(self, env: BaseWrapper=None, agent=None):
        super().__init__(env, agent)
        self.MAX_HOSTS = max_params.get("MAX_HOSTS", 5)
        self.MAX_PROCESSES = max_params.get("MAX_PROCESSES", 10) #100
        self.MAX_CONNECTIONS = max_params.get("MAX_CONNECTIONS", 2)
        self.MAX_VULNERABILITIES = max_params.get("MAX_VULNERABILITIES", 1)
        self.MAX_INTERFACES = max_params.get("MAX_INTERFACES", 2) # 4
        self.MAX_SESSIONS = max_params.get("MAX_SESSIONS", 5) # 20
        self.MAX_USERS = max_params.get("MAX_USERS", 5) # 10. MAX USERS PER HOST
        # not currently used so disable
        self.MAX_FILES = max_params.get("MAX_FILES", 0) #10
        self.MAX_GROUPS = max_params.get("MAX_GROUPS", 0) #10
        self.MAX_PATCHES = max_params.get("MAX_PATCHES", 0) #10
        self.hostname = {}
        self.username = {}
        self.group_name = {}
        self.process_name = {}
        self.interface_name = {}
        self.path = {}
        self.password = {}
        self.password_hash = {}
        self.file = {}

    def get_action(self, observation, action_space):

        action = self.agent.get_action(self.observation_change(observation), self.action_space_change(action_space))

        action_class = action['action']
        params = {}
        for p in inspect.signature(action_class).parameters:
            if p in action:
                params[p] = action[p]
            else:
                action_class = ShellSleep
                params = {}
                break
        action = action_class(**params)
        return action

    # def action_space_change(self, action_space: dict) -> dict:
    #     action_space.pop('process')
    #     action_space['session'] = {0: True}
    #     action_space['username'] = {'pi': action_space['username']['pi'],
    #                                 'vagrant': action_space['username']['vagrant']}
    #     action_space['password'] = {'raspberry': action_space['password']['raspberry'],
    #                                 'vagrant': action_space['password']['vagrant']}
    #     action_space['port'] = {22: action_space['port'][22]}
    #     return action_space

    def observation_change(self, obs: dict) -> list:
        numeric_obs = obs['hosts']
        flat_obs = []
        while len(numeric_obs) < self.MAX_HOSTS:
            hostid = str(random.randint(0, self.MAX_HOSTS+1))
            if hostid not in numeric_obs.keys():
                numeric_obs[hostid] = {}

        while len(numeric_obs) > self.MAX_HOSTS:
            numeric_obs.popitem()
            # raise ValueError("Too many hosts in observation for fixed size")

        for key_name, host in numeric_obs.items():
            if key_name == 'success':
                flat_obs.append(float(host.value)/3)
            elif not isinstance(host, dict):
                raise ValueError('Host data must be a dict')
            else:
                if 'SystemInfo' in host:
                    if "Hostname" in host["SystemInfo"]:
                        element = host["SystemInfo"]["Hostname"]
                        if element not in self.hostname:
                            self.hostname[element] = len(self.hostname)
                        element = self.hostname[element]/self.MAX_HOSTS
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)
                    if "OSType" in host["SystemInfo"]:
                        if host["SystemInfo"]["OSType"] != -1:
                            element = host["SystemInfo"]["OSType"].value/len(OperatingSystemType.__members__)
                        else:
                            element = -1
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "OSDistribution" in host["SystemInfo"]:
                        if host["SystemInfo"]["OSDistribution"] != -1:
                            element = host["SystemInfo"]["OSDistribution"].value / len(OperatingSystemDistribution.__members__)
                        else:
                            element = -1
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "OSVersion" in host["SystemInfo"]:
                        if host["SystemInfo"]["OSVersion"] != -1:
                            element = host["SystemInfo"]["OSVersion"].value / len(OperatingSystemVersion.__members__)
                        else:
                            element = -1
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "OSKernelVersion" in host["SystemInfo"]:
                        if host["SystemInfo"]["OSKernelVersion"] != -1:
                            element = host["SystemInfo"]["OSKernelVersion"].value / len(OperatingSystemKernelVersion.__members__)
                        else:
                            element = -1
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Architecture" in host["SystemInfo"]:
                        if host["SystemInfo"]["Architecture"] != -1:
                            element = host["SystemInfo"]["Architecture"].value / len(Architecture.__members__)
                        else:
                            element = -1
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if 'Local Time' in host["SystemInfo"]:
                        element = (host["SystemInfo"]['Local Time'] - datetime(2020, 1, 1)).total_seconds()
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "os_patches" not in host["SystemInfo"]:
                        host["SystemInfo"]["os_patches"] = []

                    while len(host["SystemInfo"]["os_patches"]) < self.MAX_PATCHES:
                        host["SystemInfo"]["os_patches"].append(-1.0)
                    if len(host["SystemInfo"]["os_patches"]) > self.MAX_PATCHES:
                        raise ValueError("Too many processes in observation for fixed size")
                    for patch_idx, patch in enumerate(host["SystemInfo"]["os_patches"]):
                        if patch != -1:
                            element = patch.value / len(OperatingSystemPatch.__members__)
                        else:
                            element = patch
                        
                        flat_obs.append(float(element))
                else:
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    flat_obs.append(-1.0)
                    for num_patches in range(self.MAX_PATCHES):
                        flat_obs.append(-1.0)

                if 'Processes' not in host:
                    host["Processes"] = []
                while len(host["Processes"]) < self.MAX_PROCESSES:
                    host["Processes"].append({})
                while len(host["Processes"]) > self.MAX_PROCESSES:
                    host["Processes"].pop()
                    # raise ValueError("Too many processes in observation for fixed size")

                for proc_idx, process in enumerate(host['Processes']):
                    if "PID" in process:
                        flat_obs.append(float(process["PID"])/32768)
                    else:
                        flat_obs.append(-1.0)

                    if "PPID" in process:
                        flat_obs.append(float(process["PPID"])/32768)
                    else:
                            flat_obs.append(-1.0)

                    if "Process Name" in process:
                        element = process["Process Name"]
                        if element not in self.process_name:
                            self.process_name[element] = len(self.process_name)
                        element = self.process_name[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Username" in process:
                        element = process["Username"]
                        if element not in self.username:
                            self.username[element] = len(self.username)
                        element = self.username[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Path" in process:
                        element = process["Path"]
                        if element not in self.path:
                            self.path[element] = len(self.path)
                        element = self.path[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    #if "Known Process" in process:
                    #    if process["Known Process"] != -1:
                    #        element = process["Known Process"].value / len(ProcessName.__members__)
                    #    else:
                    #        element = -1.0
                    #    
                    #    flat_obs.append(float(element))
                    #else:
                    #    flat_obs.append(-1.0)

                    if "Known Path" in process:
                        if process["Known Path"] != -1:
                            element = process["Known Path"].value / len(Path.__members__)
                        else:
                            element = -1.0
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Process Type" in process:
                        if process["Process Type"] != -1:
                            element = process["Process Type"].value / len(ProcessType.__members__)
                        else:
                            element = -1.0
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Process Version" in process:
                        if process["Process Version"] != -1:
                            element = process["Process Version"].value / len(ProcessVersion.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Connections" not in process:
                        process["Connections"] = []
                    while len(process["Connections"]) < self.MAX_CONNECTIONS:
                        process["Connections"].append({})

                    for conn_idx, connection in enumerate(process["Connections"]):
                        if "local_port" in connection:
                            flat_obs.append(float(connection["local_port"])/65535)
                        else:
                            flat_obs.append(-1.0)

                        if "remote_port" in connection:
                            flat_obs.append(float(connection["remote_port"])/65535)
                        else:
                            flat_obs.append(-1.0)

                        if "local_address" in connection:
                            element = int(connection["local_address"])
                            flat_obs.append(float(element)/4294967296)
                        else:
                            flat_obs.append(-1.0)

                        if "Remote Address" in connection:
                            element = int(connection["Remote Address"])
                            flat_obs.append(float(element)/4294967296)
                        else:
                            flat_obs.append(-1.0)

                        if "Application Protocol" in connection:
                            if connection["Application Protocol"] != -1:
                                element = connection["Application Protocol"].value / len(AppProtocol.__members__)
                            else:
                                element = -1.0
                            flat_obs.append(float(element))
                        else:
                            flat_obs.append(-1.0)

                        if "Status" in connection:
                            if connection["Status"] != -1:
                                element = connection["Status"].value / len(ProcessState.__members__)
                            else:
                                element = -1.0
                            flat_obs.append(float(element))
                        else:
                                flat_obs.append(-1.0)

                    if "Vulnerability" in process:
                        for idx, element in enumerate(process["Vulnerability"]):
                            if element != -1:
                                element = element.value / len(Vulnerability.__members__)
                            flat_obs.append(float(element))
                    else:
                        for idx in range(self.MAX_VULNERABILITIES):
                            flat_obs.append(-1.0)

                if "Files" not in host:
                    host["Files"] = []
                while len(host["Files"]) < self.MAX_FILES:
                    host["Files"].append({})
                while len(host["Files"]) > self.MAX_FILES:
                    host["Files"].pop()
                    # raise ValueError("Too many files in observation for fixed size")

                for file_idx, file in enumerate(host['Files']):
                    if "Path" in file:
                        element = file["Path"]
                        if element not in self.path:
                            self.path[element] = len(self.path)
                        element = self.path[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Known Path" in file:
                        if file["Known Path"] != -1:
                            element = file["Known Path"].value / len(Path.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "File Name" in file:
                        element = file["File Name"]
                        if element not in self.file:
                            self.file[element] = len(self.file)
                        element = self.file[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Known File" in file:
                        if file["Known File"] != -1:
                            element = file["Known File"].value / len(FileType.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                            flat_obs.append(-1.0)

                    if "Type" in file:
                        if file["Type"] != -1:
                            element = file["Type"].value / len(FileType.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Vendor" in file:
                        if file["Vendor"] != -1:
                            element = file["Vendor"].value / len(Vendor.__members__)
                        else:
                            element = -1.0
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Version" in file:
                        if file["Version"] != -1:
                            element = file["Version"].value / len(FileVersion.__members__)
                        else:
                            element = -1.0
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Username" in file:
                        element = file["Username"]
                        if element not in self.username:
                            self.username[element] = len(self.username)
                        element = self.username[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Group Name" in file:
                        element = file["Group Name"]
                        if element not in self.group_name:
                            self.group_name[element] = len(self.group_name)
                        element = self.group_name[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Last Modified Time" in file:
                        #TODO work out how to normalise this value
                        element = -1 #(file["Last Modified Time"] - datetime(2020, 1, 1)).total_seconds()
                        
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "User Permissions" in file:
                        element = file["User Permissions"]
                        flat_obs.append(float(element)/7)
                    else:
                        flat_obs.append(-1.0)

                    if "Group Permissions" in file:
                        element = file["Group Permissions"]
                        flat_obs.append(float(element)/7)
                    else:
                        flat_obs.append(-1.0)

                    if "Default Permissions" in file:
                        element = file["Default Permissions"]
                        flat_obs.append(float(element)/7)
                    else:
                        flat_obs.append(-1.0)

                if "UserInfo" not in host:
                    host["UserInfo"] = []
                while len(host["UserInfo"]) < self.MAX_USERS:
                    host["UserInfo"].append({})
                while len(host["UserInfo"]) > self.MAX_USERS:
                    host["UserInfo"].pop()
                    # raise ValueError("Too many users in observation for fixed size")

                for user_idx, user in enumerate(host['UserInfo']):
                    if "Username" in user:
                        element = user["Username"]
                        if element not in self.username:
                            self.username[element] = len(self.username)
                        element = self.username[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Password" in user:
                        element = user["Password"]
                        if element not in self.password:
                            self.password[element] = len(self.password)
                        element = self.password[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Password Hash" in user:
                        element = user["Password Hash"]
                        if element not in self.password_hash:
                            self.password_hash[element] = len(self.password_hash)
                        element = self.password_hash[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Password Hash Type" in user:
                        if user["Password Hash Type"] != -1:
                            element = user["Password Hash Type"].value / len(PasswordHashType.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "UID" in user:
                        # convert Windows SIDs to usuable integer values
                        # at the moment, just extract the RID
                        flat_obs.append(float(str(user["UID"]).split('-')[-1]))
                    else:
                        flat_obs.append(-1.0)

                    if "Logged in" in user:
                        flat_obs.append(float(user["Logged in"]))
                    else:
                        flat_obs.append(-1.0)

                    if "Groups" not in user:
                        user["Groups"] = []
                    while len(user["Groups"]) < self.MAX_GROUPS:
                        user["Groups"].append({})
                    while len(user['Groups']) > self.MAX_GROUPS:
                        user['Groups'].pop()
                        # raise ValueError("Too many groups in observation for fixed size")
                    for group_idx, group in enumerate(user["Groups"]):
                        if 'Builtin Group' in group:
                            if group["Builtin Group"] != -1:  # TODO test if this is ever not true
                                element = group["Builtin Group"].value / len(BuiltInGroups.__members__)
                            else:
                                element = -1.0
                            flat_obs.append(float(element))
                        else:
                            flat_obs.append(-1.0)

                        if "Group Name" in group:
                            element = user["Group Name"]
                            if element not in self.group_name:
                                self.group_name[element] = len(self.group_name)
                            element = self.group_name[element]
                            flat_obs.append(float(element))
                        else:
                            flat_obs.append(-1.0)

                        if "GID" in group:
                            flat_obs.append(float(group["GID"]))
                        else:
                            flat_obs.append(-1.0)

                if "Sessions" not in host:
                    host["Sessions"] = []
                while len(host["Sessions"]) < self.MAX_SESSIONS:
                    host["Sessions"].append({})
                while len(host["Sessions"]) > self.MAX_SESSIONS:
                    host["Sessions"].pop()
                    # raise ValueError("Too many sessions in observation for fixed size")

                for session_idx, session in enumerate(host['Sessions']):
                    if "Username" in session:
                        element = session["Username"]
                        if element not in self.username:
                            self.username[element] = len(self.username)
                        element = self.username[element]
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "Type" in session:
                        if session["Type"] != -1:
                            element = session["Type"].value/len(SessionType.__members__)
                        else:
                            element = -1.0
                        flat_obs.append(float(element))
                    else:
                        flat_obs.append(-1.0)

                    if "ID" in session:
                        flat_obs.append(float(session["ID"])/20)
                    else:
                        flat_obs.append(-1.0)

                    if "Timeout" in session:
                        flat_obs.append(float(session["Timeout"]))
                    else:
                         flat_obs.append(-1.0)

                    if "PID" in session:
                        flat_obs.append(float(session["PID"])/32768)
                    else:
                        flat_obs.append(-1.0)

                if 'Interface' not in host:
                    host["Interface"] = []
                while len(host["Interface"]) < self.MAX_INTERFACES:
                    host["Interface"].append({})
                while len(host["Interface"]) > self.MAX_INTERFACES:
                    host["Interface"].pop()
                    # raise ValueError("Too many interfaces in observation for fixed size")

                if 'Interface' in host:
                    for interface_idx, interface in enumerate(host['Interface']):
                        if "Interface Name" in interface:
                            element = interface["Interface Name"]
                            if element not in self.interface_name:
                                self.interface_name[element] = len(self.interface_name)
                            element = self.interface_name[element]
                            flat_obs.append(float(
                                    element))
                        else:
                             flat_obs.append(-1.0)

                        if "Subnet" in interface:
                            element = interface["Subnet"]
                            flat_obs.append(float(int(element.network_address))/4294967296)
                            flat_obs.append(float(int(element.prefixlen))/4294967296)
                        else:
                             flat_obs.append(-1.0)
                             flat_obs.append(-1.0)

                        if "IP Address" in interface:
                            element = int(interface["IP Address"])
                            flat_obs.append(float(element)/4294967296)
                        else:
                             flat_obs.append(-1.0)

        return flat_obs

    def get_attr(self,attribute:str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        obs = self.get_attr('get_observation')(agent)
        return self.observation_change(obs)
