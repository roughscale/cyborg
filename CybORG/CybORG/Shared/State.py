from CybORG.Shared.Observation import Observation
from pprint import pprint
import copy
import hashlib

class State(Observation):

    """ This manages the State space of the Agent which is a running history of all observations """
    def __init__(self):
        self.data = {"network": {}, "hosts": {}}
        self.raw = ''

        # keep a running total of the number of each State elements (to identify MAX requirements)
        self.num_subnets = 0
        self.num_hosts = 0
        self.num_processes = 0
        self.num_sessions = 0
        self.num_connections = 0
        self.num_interfaces = 0

    """
        Initialise the state with ALL scenario hosts so that any fixed flattened State space 
        will be consistent
    """
    def initialise_state(self, scenario):

        for hostname in scenario.hosts:
            self.data["hosts"][hostname] = {}

        self.calculate_max_elements()
        #print("initialise state")
        #print(self.data)

    def calculate_max_elements(self):
        self.num_subnets = len(self.data["network"])
        self.num_hosts = len(self.data["hosts"])
        num_processes = 0 # num processes per host
        num_sessions = 0 # num sessions per host
        num_connections = 0 # num connections per process
        num_interfaces = 0 # num interfaces per host

        for host in self.data["hosts"]:
            num_host_processes = 0 
            num_host_sessions = 0
            num_proc_connections = 0
            num_host_interfaces = 0
            if "Processes" in self.data["hosts"][host]:
              num_host_processes += len(self.data["hosts"][host]["Processes"])
              for proc in self.data["hosts"][host]["Processes"]:
                  if "Connections" in proc:
                      num_proc_connections += 1
              if num_proc_connections > num_connections:
                  num_connections = num_proc_connections
              if num_host_processes > num_processes:
                  num_processes = num_host_processes
            if "Sessions" in self.data["hosts"][host]:
              num_host_sessions += len(self.data["hosts"][host]["Sessions"])
              if num_host_sessions > num_sessions:
                  num_sessions = num_host_sessions
            if "Interface" in self.data["hosts"][host]:
              num_host_interfaces += len(self.data["hosts"][host]["Interface"])
              if num_host_interfaces > num_interfaces:
                  num_interfaces = num_host_interfaces

        if num_processes > self.num_processes:
          self.num_processes = num_processes

        if num_sessions > self.num_sessions:
          self.num_sessions = num_sessions

        #if num_connections > self.num_connections:
        #  self.num_connections = num_connections

        if num_interfaces > self.num_interfaces:
          self.num_interfaces = num_interfaces

    def get_max_elements(self):
      max_elements = {}
      max_elements["subnets"] = self.num_subnets
      max_elements["hosts"] = self.num_hosts
      max_elements["processes"] = self.num_processes
      max_elements["sessions"] = self.num_sessions
      max_elements["connections"] = self.num_connections
      max_elements["interfaces"] = self.num_interfaces
      return max_elements

    # updates the State space with an Observation
    def update(self, observation: Observation, agent="Red"):
        # convert Observation to dict
        if isinstance(observation, Observation):
          obs = copy.deepcopy(observation.data)
        else:
          obs = copy.deepcopy(observation)
        # remove the success key
        obs.pop('success',None)
        #print("State update observation")
        #print(obs)
        # check that this is deterministic!
        # merge observations
        for key, info in obs["hosts"].items():
            #print("state update key")
            #print(key)
            #if not isinstance(info, dict):
            #    self.add_key_value(key, info)
            #    continue
            if "Sessions" in info:
                for session_info in info["Sessions"]:
                    self.merge_session_info(hostid=key, agent=agent, **session_info)
            if "Processes" in info:
                for process in info["Processes"]:
                    if 'Connections' in process:
                        for conn in process['Connections']:
                            self.merge_process(hostid=key, agent=agent, **process, **conn)
                    else:
                        self.merge_process(hostid=key, agent=agent, **process)
            if "UserInfo" in info:
                for user in info["UserInfo"]:
                    self.merge_user_info(hostid=key, agent=agent, **user)
            if "Files" in info:
                for file_info in info["Files"]:
                    self.merge_file_info(hostid=key, agent=agent, **file_info)
            if "Interface" in info:
                for interface in info["Interface"]:
                    self.merge_interface_info(hostid=key, agent=agent, **interface)
            if "SystemInfo" in info:
                self.merge_system_info(hostid=key, agent=agent, **info["SystemInfo"])

        if 'subnets' in obs['network']:
            for subnet in obs['network']['subnets']:
                self.add_subnet(subnet)
        #self.calculate_max_elements()
        #print("updated State")
        #pprint(self.data)

    def get_state(self):
        return copy.deepcopy(self.data)

    @staticmethod
    def get_state_hash(state_vector):
        h = hashlib.new("sha256")
        h.update(state_vector.tobytes())
        return h.hexdigest()

    def merge_session_info(self, hostid, agent, **session_info):
        self.add_session_info(hostid=hostid, agent=agent, **session_info)

    def merge_process(self, hostid, agent, **process):
        self.add_process(hostid=hostid, agent=agent, **process)

    def merge_user_info(self, hostid, agent, **user):
        self.add_user_info(hostid=hostid, agent=agent, **user)

    def merge_file_info(self, hostid, agent, **file_info):
        self.add_file_info(hostid=hostid, agent=agent, **file_info)

    def merge_interface_info(self, hostid, agent, **interface):
        self.add_interface_info(hostid=hostid, agent=agent, **interface)

    def merge_system_info(self, hostid, agent, **info):
        self.add_system_info(hostid=hostid, agent=agent, **info)

