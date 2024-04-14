# Copyright DST Group. Licensed under the MIT license.

import sys
from inspect import signature
from ipaddress import IPv4Address, IPv4Network

from CybORG.Shared.Enums import SessionType

# These are the maximum for the Action Space parameter vector
MAX_SUBNETS = 3
MAX_ADDRESSES = 6
MAX_SESSIONS = 10
MAX_USERNAMES = 8
MAX_PASSWORDS = 8
MAX_PROCESSES = 10 # We will use ProcessName instead of PID
MAX_PORTS = 11 # 6 static and 5 ephermal ports
# Following not used in this Class
#MAX_GROUPS = 5
#MAX_FILES = 10
#MAX_PATHS = 10


class ActionSpace:

    def __init__(self, actions, agent, allowed_subnets, external_hosts):
        # load in the stuff that the agent is allowed to know about

        # save all params
        self.actions = {i: True for i in self.get_action_classes(actions)}
        self.action_params = {}
        for action in self.actions:
            self.action_params[action] = signature(action).parameters
        self.allowed_subnets = allowed_subnets
        self.subnet = {} # dict keys to be IPv4Network
        self.ip_address = {} # dict keys to be IPv4Address
        self.server_session = {}
        self.client_session = {i: False for i in range(MAX_SESSIONS)}
        self.username = {}
        self.password = {}
        self.process = {}
        self.port = {}
        self.hostname = {}
        self.agent = {agent: True}
        self.external_hosts = external_hosts

    def get_name(self, action: int) -> str:
        pass

    def get_action_classes(self, actions):
        action_classes = []
        action_module = sys.modules['CybORG.Shared.Actions']
        for action in actions:
            action_classes.append(getattr(action_module, action))
        return action_classes

    def get_max_action_space(self):
        max_action = {
            'action': len(self.actions),
            'subnet': MAX_SUBNETS,
            'ip_address': MAX_ADDRESSES,
            'session': MAX_SESSIONS,
            'username': MAX_USERNAMES,
            'password': MAX_PASSWORDS,
            'process': MAX_PROCESSES,
            'port': MAX_PORTS,
            'target_session': MAX_SESSIONS}
        return max_action

    def get_action_space(self):
        max_action = {
            'action': self.actions,
            'subnet': self.subnet,
            'ip_address': self.ip_address,
            'session': self.server_session,
            'username': self.username,
            'password': self.password,
            'process': self.process,
            'port': self.port,
            'target_session': self.client_session,
            'agent': self.agent,
            'hostname': self.hostname
        }
        return max_action

    def get_action_space_size(self):
        max_action = {
            'action': len(self.actions),
            'subnet': len(self.subnet),
            'ip_address': len(self.ip_address),
            'session': len(self.server_session),
            'username': len(self.username),
            'password': len(self.password),
            'process': len(self.process),
            'port': len(self.port),
            'target_session': len(self.client_session),
            'agent': len(self.agent),
            'hostname': len(self.hostname)
        }
        return max_action

    def reset(self, agent):
        self.subnet = {}
        self.ip_address = {}
        self.server_session = {}
        self.client_session = {i: False for i in range(MAX_SESSIONS)}
        self.username = {}
        self.password = {}
        self.process = {}
        self.port = {}
        self.agent = {agent: True}

    def get_max_actions(self, action):
        params = self.action_params[action]
        size = 1
        for param in params.keys():
            if param == "session":
                size *= len(self.server_session)
            elif param == "target_session":
                size *= len(self.client_session)
            elif param == "subnet":
                size *= len(self.subnet)
            elif param == "ip_address":
                size *= len(self.ip_address)
            elif param == "username":
                size *= len(self.username)
            elif param == "password":
                size *= len(self.password)
            elif param == "process":
                size *= len(self.process)
            elif param == "port":
                size *= len(self.port)
            elif param == "agent":
                size *= len(self.agent)
            else:
                raise NotImplementedError(
                    f"Param '{param}' in action '{action.__name__}' has no"
                    " code to parse its size for action space"
                )
        return size

    def update(self, observation: dict, known: bool = True, init: bool = False):
        # use init=True to set up the initial action space, as updates will depend upon
        # the initialised action_space
        if observation is None:
            return
        for key, info in observation['hosts'].items():
            if not isinstance(info, dict):
                continue
            if key in self.external_hosts:
                # only add Attacker session action space parameters
                if "Sessions" in info:
                  for session in info["Sessions"]:
                    if "ID" in session and session['Agent'] in self.agent:
                        if "Type" in session and (session["Type"] == SessionType.MSF_SERVER or session["Type"] == SessionType.RED_ABSTRACT_SESSION):
                            if session['Active']:
                               self.server_session[session["ID"]] = known
                            else:
                                self.server_session[session["ID"]] = False # remove inactive sessions from action parameter space
                        else:
                            # assume if not a server session then its a client session
                            if session['Active']:
                               self.client_session[session["ID"]] = known
                            else:
                               self.client_session[session["ID"]] = False

                continue
            if "SystemInfo" in info:
                if "Hostname" in info["SystemInfo"]:
                  # TODO:
                  # we should only ignore external host for non-blue type agents
                  # as blue agents may need to take actions against an external host
                  if info["SystemInfo"]["Hostname"] not in self.external_hosts:
                    self.hostname[info["SystemInfo"]["Hostname"]] = known
            if "Interface" in info:
                for interface in info["Interface"]:
                    if "Subnet" in interface:
                       self.subnet[interface["Subnet"]] = known
                    if "IP Address" in interface:
                        self.ip_address[interface["IP Address"]] = known

            if "Processes" in info:
                for process in info["Processes"]:
                    # only update for process entries already in the action parameter space
                    if "ProcessName" in process and (process["ProcessName"] in self.process or init):
                        self.process[process["ProcessName"]] = known
                    if "Connections" in process:
                        for connection in process["Connections"]:
                            if "local_port" in connection and (connection["local_port"] in self.port or init):
                                self.port[connection["local_port"]] = known
                            if "remote_port" in connection and (connection["remote_port"] in self.port or init):
                                self.port[connection["remote_port"]] = known

            if "UserInfo" in info:
                for user in info["UserInfo"]:
                    if "Username" in user and (user["Username"] in self.username or init):
                        self.username[user["Username"]] = known
                    if "Password" in user:
                        if user["Password"] not in self.password and not init:
                            print("password {0} not in action parameter space".format(user["Password"]))
                        else:
                            self.password[user["Password"]] = known

            if "Sessions" in info:
                for session in info["Sessions"]:
                    if "ID" in session and session['Agent'] in self.agent:
                        if "Type" in session and (session["Type"] == SessionType.MSF_SERVER or session["Type"] == SessionType.VELOCIRAPTOR_SERVER or session["Type"] == SessionType.RED_ABSTRACT_SESSION or session["Type"] == SessionType.GREY_SESSION):
                            self.server_session[session["ID"]] = known
                        else:
                            # assume if not a server session then its a client session
                            self.client_session[session["ID"]] = known
        if 'subnets' in observation['network']:
            for subnet in observation['network']['subnets']:
                self.subnet[IPv4Network(subnet)] = known
